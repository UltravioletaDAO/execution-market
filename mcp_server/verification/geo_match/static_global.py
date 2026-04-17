"""
Static GeoNames global cities dataset loader (cities500.txt).

Source: https://download.geonames.org/export/dump/cities500.zip
Format: tab-separated, no header. Columns (1-indexed per GeoNames spec):

    1  geonameid         integer id of record
    2  name              name of geographical point (utf-8)
    3  asciiname         name of geographical point in ASCII
    4  alternatenames    comma-separated list of alternate names
    5  latitude          float
    6  longitude         float
    7  feature class     char(1)
    8  feature code      varchar(10)
    9  country_code      ISO-3166 2-letter
   10  cc2               alternate country codes
   11  admin1_code       FIPS / ISO state code
   12  admin2_code       county-level code
   13  admin3_code       fourth-level subdivision
   14  admin4_code       fifth-level subdivision
   15  population        integer
   16  elevation         integer meters
   17  dem               digital elevation model, integer meters
   18  timezone
   19  modification_date yyyy-MM-dd

Expected path: mcp_server/verification/geo_match/data/cities500.txt

If absent: log WARNING and return None from lookups. Never crash.
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
CITIES500_TXT = DATA_DIR / "cities500.txt"


@dataclass(frozen=True)
class GlobalCity:
    """A single normalized GeoNames cities500 record."""

    geonameid: int
    name: str  # UTF-8 name
    asciiname: str
    lat: float
    lng: float
    country_code: str  # ISO-3166-1 alpha-2
    admin1_code: str
    population: int


class _GlobalCityIndex:
    """Lazy-loaded in-memory index for GeoNames cities500."""

    _instance: Optional["_GlobalCityIndex"] = None
    _instance_lock = threading.Lock()

    def __init__(self, tsv_path: Optional[Path] = None) -> None:
        # Resolve the path at instantiation time so the module-level
        # CITIES500_TXT can be swapped by tests.
        self._tsv_path = tsv_path if tsv_path is not None else CITIES500_TXT
        # Index by lowercased ascii-name -> list of cities (disambiguate later).
        self._by_name: dict[str, list[GlobalCity]] = {}
        # Index by (name, country_code) -> best (highest-population) city.
        self._by_name_country: dict[tuple[str, str], GlobalCity] = {}
        self._loaded = False
        self._load_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "_GlobalCityIndex":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            self._loaded = True
            if not self._tsv_path.exists():
                logger.warning(
                    "geo_match.static_global: cities500.txt not found at %s — global layer disabled. "
                    "See mcp_server/verification/geo_match/data/README.md to populate.",
                    self._tsv_path,
                )
                return
            try:
                count = 0
                with self._tsv_path.open("r", encoding="utf-8", newline="") as fh:
                    # GeoNames files have no quoting — use QUOTE_NONE to preserve apostrophes.
                    reader = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
                    for row in reader:
                        entry = self._parse_row(row)
                        if entry is None:
                            continue
                        self._register(entry)
                        count += 1
                logger.info(
                    "geo_match.static_global: loaded %d cities from %s",
                    count,
                    self._tsv_path,
                )
            except Exception as exc:
                logger.warning(
                    "geo_match.static_global: failed to load %s: %s — layer disabled",
                    self._tsv_path,
                    exc,
                )

    def _register(self, entry: GlobalCity) -> None:
        for name in {entry.name.lower(), entry.asciiname.lower()}:
            if not name:
                continue
            self._by_name.setdefault(name, []).append(entry)
            key = (name, entry.country_code.lower())
            existing = self._by_name_country.get(key)
            if existing is None or entry.population > existing.population:
                self._by_name_country[key] = entry

    @staticmethod
    def _parse_row(row: list[str]) -> Optional[GlobalCity]:
        if len(row) < 15:
            return None
        try:
            geonameid = int(row[0])
        except (TypeError, ValueError):
            return None
        name = (row[1] or "").strip()
        asciiname = (row[2] or "").strip()
        try:
            lat = float(row[4])
            lng = float(row[5])
        except (TypeError, ValueError):
            return None
        country_code = (row[8] or "").strip().upper()
        admin1_code = (row[10] or "").strip()
        try:
            population = int(row[14]) if row[14] else 0
        except (TypeError, ValueError):
            population = 0
        if not name and not asciiname:
            return None
        return GlobalCity(
            geonameid=geonameid,
            name=name or asciiname,
            asciiname=asciiname or name,
            lat=lat,
            lng=lng,
            country_code=country_code,
            admin1_code=admin1_code,
            population=population,
        )

    def lookup(self, name: str, country: Optional[str] = None) -> Optional[GlobalCity]:
        """Lookup a city by (ascii or utf-8) name, optionally narrowed by country code."""
        self._ensure_loaded()
        key = (name or "").strip().lower()
        if not key:
            return None
        country_key = (country or "").strip().lower()
        if country_key:
            direct = self._by_name_country.get((key, country_key))
            if direct is not None:
                return direct
        candidates = self._by_name.get(key, [])
        if not candidates:
            return None
        if country_key:
            narrowed = [c for c in candidates if c.country_code.lower() == country_key]
            if narrowed:
                return max(narrowed, key=lambda c: c.population)
        return max(candidates, key=lambda c: c.population)

    def iter_all(self) -> Iterable[GlobalCity]:
        self._ensure_loaded()
        for entries in self._by_name.values():
            yield from entries


def lookup_global_city(
    name: str, country: Optional[str] = None
) -> Optional[GlobalCity]:
    """Public API: look up a global city by name (optionally narrowed by ISO country code)."""
    return _GlobalCityIndex.instance().lookup(name, country)


def reset_index_for_tests(tsv_path: Optional[Path] = None) -> None:
    _GlobalCityIndex.reset()
    if tsv_path is not None:
        global CITIES500_TXT
        CITIES500_TXT = tsv_path
