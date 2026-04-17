"""
Static US ZIP code dataset loader (Simple Maps free tier).

The CSV is expected at:
    mcp_server/verification/geo_match/data/us_zips.csv

Columns we consume (case-insensitive, from Simple Maps' "uszips" free CSV):
    zip, lat, lng, city, state_id, state_name, county_name, population

If the file is missing we log a WARNING and return None from every lookup.
Never raise — the module must import and degrade gracefully (see plan
rollout: operators populate data files separately, module must boot in
any environment including CI where these are absent).
"""

from __future__ import annotations

import csv
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
US_ZIPS_CSV = DATA_DIR / "us_zips.csv"

# Conservative US mainland + Alaska + Hawaii bounding box.
# Used to short-circuit this layer for non-US coordinates.
US_BBOX_LAT = (15.0, 72.0)
US_BBOX_LNG = (-180.0, -65.0)


@dataclass(frozen=True)
class USZipEntry:
    """A single normalized US ZIP record."""

    zip: str
    lat: float
    lng: float
    city: str
    state_id: str  # Two-letter code (e.g. "FL")
    state_name: str
    county: str
    population: int  # 0 when unknown


class _USZipIndex:
    """Lazy-loaded in-memory index keyed by lowercased (city, state_id).

    Implemented as a singleton because the CSV (~40k rows) should only be
    parsed once per process.
    """

    _instance: Optional["_USZipIndex"] = None
    _instance_lock = threading.Lock()

    def __init__(self, csv_path: Optional[Path] = None) -> None:
        # Resolve the path at instantiation time so the module-level
        # US_ZIPS_CSV can be swapped by tests.
        self._csv_path = csv_path if csv_path is not None else US_ZIPS_CSV
        self._by_city_state: dict[tuple[str, str], USZipEntry] = {}
        self._by_city: dict[str, list[USZipEntry]] = {}
        self._loaded = False
        self._load_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "_USZipIndex":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Test hook: drop the singleton so a new CSV path can be picked up."""
        with cls._instance_lock:
            cls._instance = None

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            self._loaded = True  # Mark loaded even on failure (don't re-try)
            if not self._csv_path.exists():
                logger.warning(
                    "geo_match.static_us: CSV not found at %s — US ZIP layer disabled. "
                    "See mcp_server/verification/geo_match/data/README.md to populate.",
                    self._csv_path,
                )
                return
            try:
                count = 0
                with self._csv_path.open("r", encoding="utf-8", newline="") as fh:
                    reader = csv.DictReader(fh)
                    # Normalize header names to lower-case for lookup.
                    field_map = {
                        (f or "").lower().strip(): f for f in (reader.fieldnames or [])
                    }
                    for row in reader:
                        entry = self._parse_row(row, field_map)
                        if entry is None:
                            continue
                        key = (entry.city.lower(), entry.state_id.lower())
                        # Keep the entry with the largest population as the
                        # canonical representative of that (city, state).
                        existing = self._by_city_state.get(key)
                        if existing is None or entry.population > existing.population:
                            self._by_city_state[key] = entry
                        self._by_city.setdefault(entry.city.lower(), []).append(entry)
                        count += 1
                logger.info(
                    "geo_match.static_us: loaded %d ZIP entries (%d unique city/state pairs) from %s",
                    count,
                    len(self._by_city_state),
                    self._csv_path,
                )
            except Exception as exc:
                logger.warning(
                    "geo_match.static_us: failed to load %s: %s — layer disabled",
                    self._csv_path,
                    exc,
                )
                # Leave indexes empty; subsequent lookups return None.

    @staticmethod
    def _parse_row(row: dict, field_map: dict[str, str]) -> Optional[USZipEntry]:
        def field(name: str) -> str:
            key = field_map.get(name)
            if key is None:
                return ""
            val = row.get(key) or ""
            return val.strip()

        try:
            lat = float(field("lat"))
            lng = float(field("lng"))
        except (TypeError, ValueError):
            return None
        city = field("city")
        if not city:
            return None
        state_id = field("state_id") or field("state")
        state_name = field("state_name") or state_id
        population_raw = field("population")
        try:
            population = int(float(population_raw)) if population_raw else 0
        except (TypeError, ValueError):
            population = 0
        return USZipEntry(
            zip=field("zip"),
            lat=lat,
            lng=lng,
            city=city,
            state_id=state_id.upper(),
            state_name=state_name,
            county=field("county_name") or field("county"),
            population=population,
        )

    def lookup_city(
        self, city: str, state: Optional[str] = None
    ) -> Optional[USZipEntry]:
        """Lookup by city name; if ``state`` is given (2-letter or full), narrows match."""
        self._ensure_loaded()
        city_key = (city or "").strip().lower()
        if not city_key:
            return None
        state_key = (state or "").strip().lower()
        if state_key:
            # Try 2-letter match first.
            direct = self._by_city_state.get((city_key, state_key))
            if direct is not None:
                return direct
            # Try full state name match by scanning the per-city list.
            candidates = self._by_city.get(city_key, [])
            for c in candidates:
                if c.state_name.lower() == state_key:
                    return c
        candidates = self._by_city.get(city_key, [])
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.population)

    def iter_all(self) -> Iterable[USZipEntry]:
        self._ensure_loaded()
        return self._by_city_state.values()


def coords_inside_us(lat: float, lng: float) -> bool:
    """Quick bbox test — short-circuits the US layer for clearly-foreign coordinates."""
    return (US_BBOX_LAT[0] <= lat <= US_BBOX_LAT[1]) and (
        US_BBOX_LNG[0] <= lng <= US_BBOX_LNG[1]
    )


def lookup_us_city(city: str, state: Optional[str] = None) -> Optional[USZipEntry]:
    """Public API: look up a US city by name (optionally narrowed by state)."""
    return _USZipIndex.instance().lookup_city(city, state)


def reset_index_for_tests(csv_path: Optional[Path] = None) -> None:
    """Test hook: reset the singleton and optionally point at a different CSV."""
    _USZipIndex.reset()
    if csv_path is not None:
        # Swap the module-level default so the next .instance() call uses it.
        global US_ZIPS_CSV
        US_ZIPS_CSV = csv_path
