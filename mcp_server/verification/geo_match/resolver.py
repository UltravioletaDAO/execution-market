"""
GeoMatcher — main entry point for geographic matching.

Resolution order (per master plan, Layer B):
    1. In-process cache (future: Supabase geo_cache table — out of scope here).
    2. Static US ZIP dataset (if the submission coords are inside the US bbox).
    3. Static GeoNames cities500 dataset.
    4. Nominatim forward-geocode fallback.

Design choices worth flagging:

- **Haversine hand-rolled** — not `geopy`. The formula is six lines; an extra
  dependency in `mcp_server/` isn't worth its upkeep. `geopy` also pulls in
  optional C extensions and a Nominatim client that differs from ours.
  (The plan explicitly says: "implement haversine manually; no geopy".)
- **Sync API** — the matcher must be callable from both the sync prompt
  builder (`verification/prompts/base.py`) and the async pipeline
  (`verification/pipeline.py`). Async code can always call a sync function;
  making the matcher async would force the prompt builder to become async.
- **Graceful degradation** — a missing dataset or a Nominatim timeout must
  never raise. Callers get `MatchResult(passed=False, source="unresolved")`.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .nominatim import NominatimClient, NominatimPlace
from .static_global import GlobalCity, lookup_global_city
from .static_us import USZipEntry, coords_inside_us, lookup_us_city

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088

# Default radius for MatchMode.STRICT when caller omits `location_radius_m`.
DEFAULT_STRICT_RADIUS_M = 500


class MatchMode(str, Enum):
    STRICT = "strict"
    CITY = "city"
    REGION = "region"
    COUNTRY = "country"
    ANY = "any"


@dataclass
class MatchResult:
    """Outcome of a geo match evaluation."""

    passed: bool
    distance_km: Optional[float] = None
    resolved_area: Optional[str] = None
    radius_used_km: Optional[float] = None
    source: str = "unresolved"  # cache | static_us_zip | static_global | nominatim | strict | any | unresolved
    reason: Optional[str] = None
    prompt_summary: str = ""
    # Optional structured hints for downstream consumers (not part of the
    # documented contract — kept as extras).
    resolved_country_code: Optional[str] = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Radius table — master plan, Layer C
# ---------------------------------------------------------------------------


def radius_km_for_population(pop: Optional[int]) -> float:
    if pop is None or pop <= 0:
        return 10.0
    if pop > 5_000_000:
        return 40.0
    if pop >= 1_000_000:
        return 25.0
    if pop >= 100_000:
        return 15.0
    if pop >= 10_000:
        return 8.0
    return 3.0


# ---------------------------------------------------------------------------
# Haversine — hand-rolled per plan
# ---------------------------------------------------------------------------


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres. Manual implementation, not geopy."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


# ---------------------------------------------------------------------------
# Null-island / missing-coord handling
# ---------------------------------------------------------------------------


def _is_missing(lat: Optional[float], lng: Optional[float]) -> bool:
    """Treat (None, None) and (0, 0) — 'null island' — as missing coordinates."""
    if lat is None or lng is None:
        return True
    # Use a tight tolerance: real submissions are never sub-meter from 0,0
    # (there is ocean there) but GPS noise won't place a real reading at 0,0
    # either. The iPhone geolocation API returns 0,0 only on permission denial.
    return abs(lat) < 1e-9 and abs(lng) < 1e-9


# ---------------------------------------------------------------------------
# Location-hint parser
# ---------------------------------------------------------------------------

_US_STATE_TO_CODE = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}

_COUNTRY_ALIASES = {
    "usa": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    "united states": "US",
    "united states of america": "US",
    "uk": "GB",
    "u.k.": "GB",
    "united kingdom": "GB",
    "great britain": "GB",
    "mexico": "MX",
    "méxico": "MX",
    "canada": "CA",
    "japan": "JP",
    "germany": "DE",
    "france": "FR",
    "spain": "ES",
    "italy": "IT",
    "brazil": "BR",
    "argentina": "AR",
    "colombia": "CO",
    "china": "CN",
    "india": "IN",
    "australia": "AU",
}


@dataclass
class ParsedHint:
    city: Optional[str]
    state: Optional[str]  # Two-letter code if US; else raw token
    country: Optional[str]  # Two-letter ISO code when we can infer it


def parse_location_hint(hint: str) -> ParsedHint:
    """Parse a hint like "Miami, FL, USA" into city/state/country components.

    Very forgiving: missing commas, missing country, or extra whitespace all
    produce a best-effort parse. Unknown countries fall through as None.
    """
    if not hint:
        return ParsedHint(None, None, None)
    parts = [p.strip() for p in hint.split(",") if p.strip()]
    if not parts:
        return ParsedHint(None, None, None)

    country_code: Optional[str] = None
    state_code: Optional[str] = None
    city: Optional[str] = None

    # Strip country from the tail if recognisable.
    if len(parts) >= 1:
        tail = parts[-1].lower()
        if tail in _COUNTRY_ALIASES:
            country_code = _COUNTRY_ALIASES[tail]
            parts = parts[:-1]
        elif len(tail) == 2 and tail.isalpha():
            # Heuristic: a bare 2-letter trailing token on a 3+ part hint
            # is likely a country code. On a 2-part hint it's ambiguous —
            # could be "Miami, FL" (state) — so only treat as country when
            # there are 3+ parts or when it doesn't match a US state.
            maybe_state = tail.upper()
            is_us_state_code = maybe_state in _US_STATE_TO_CODE.values()
            if len(parts) >= 3 and not is_us_state_code:
                country_code = maybe_state
                parts = parts[:-1]
            elif len(parts) >= 3 and is_us_state_code:
                # 3+ parts where tail matches a US state code — ambiguous.
                # Conservatively, treat as country code only if it's clearly
                # non-US (handled above); otherwise leave it as a state.
                pass

    # Now peel the state from the (new) tail.
    if len(parts) >= 2:
        tail = parts[-1].strip()
        tail_lc = tail.lower()
        if len(tail) == 2 and tail.isalpha():
            state_code = tail.upper()
            parts = parts[:-1]
            if country_code is None and state_code in _US_STATE_TO_CODE.values():
                country_code = "US"
        elif tail_lc in _US_STATE_TO_CODE:
            state_code = _US_STATE_TO_CODE[tail_lc]
            parts = parts[:-1]
            if country_code is None:
                country_code = "US"

    if parts:
        city = parts[0]

    return ParsedHint(city=city, state=state_code, country=country_code)


# ---------------------------------------------------------------------------
# Match sources — uniform adapter over (lat, lng, radius_km, resolved_area)
# ---------------------------------------------------------------------------


@dataclass
class _Resolved:
    lat: float
    lng: float
    radius_km: float
    display: str
    country_code: Optional[str]
    source: str
    admin_code: Optional[str] = None  # e.g. "FL" for US state


def _from_us(entry: USZipEntry) -> _Resolved:
    return _Resolved(
        lat=entry.lat,
        lng=entry.lng,
        radius_km=radius_km_for_population(entry.population),
        display=f"{entry.city}, {entry.state_id}, US",
        country_code="US",
        source="static_us_zip",
        admin_code=entry.state_id,
    )


def _from_global(entry: GlobalCity) -> _Resolved:
    display_parts = [entry.name]
    if entry.admin1_code:
        display_parts.append(entry.admin1_code)
    if entry.country_code:
        display_parts.append(entry.country_code)
    return _Resolved(
        lat=entry.lat,
        lng=entry.lng,
        radius_km=radius_km_for_population(entry.population),
        display=", ".join(display_parts),
        country_code=entry.country_code,
        source="static_global",
        admin_code=entry.admin1_code or None,
    )


def _from_nominatim(place: NominatimPlace) -> _Resolved:
    # Nominatim gives no population, so we pick a radius heuristically from
    # the `place_type` / `place_class`. These map roughly to GeoNames feature
    # classes; a city-typed result gets the same default as a mid-size
    # metro (25 km) so submissions from the city's outskirts still match.
    ptype = (place.place_type or "").lower()
    pclass = (place.place_class or "").lower()
    if ptype in {"country"} or pclass == "country":
        radius_km = 2000.0
    elif ptype in {"state", "region", "administrative"}:
        radius_km = 200.0
    elif ptype in {"county"}:
        radius_km = 50.0
    elif ptype in {"city", "metropolis"}:
        radius_km = 25.0
    elif ptype in {"town", "municipality"}:
        radius_km = 15.0
    elif ptype in {"village", "suburb", "neighbourhood"}:
        radius_km = 5.0
    else:
        # Unknown type — err on the side of accepting nearby submissions.
        radius_km = 25.0
    display = place.display_name
    if place.city and place.country_code:
        display = f"{place.city}, {(place.state or '').strip() or place.country_code.upper()}, {place.country_code.upper()}"
    return _Resolved(
        lat=place.lat,
        lng=place.lng,
        radius_km=radius_km,
        display=display,
        country_code=(place.country_code or "").upper() or None,
        source="nominatim",
    )


# ---------------------------------------------------------------------------
# GeoMatcher
# ---------------------------------------------------------------------------


class GeoMatcher:
    """Stateful matcher — holds the Nominatim client + in-process cache.

    Construct once per process (or per request handler) and reuse.
    """

    def __init__(
        self,
        nominatim_client: Optional[NominatimClient] = None,
        us_lookup=lookup_us_city,
        global_lookup=lookup_global_city,
    ) -> None:
        self._nominatim = nominatim_client or NominatimClient()
        self._us_lookup = us_lookup
        self._global_lookup = global_lookup

    # ------------------------------------------------------------------ public

    def match(
        self,
        submission_lat: Optional[float],
        submission_lng: Optional[float],
        mode: MatchMode,
        *,
        location_hint: Optional[str] = None,
        location_lat: Optional[float] = None,
        location_lng: Optional[float] = None,
        location_radius_m: Optional[int] = None,
    ) -> MatchResult:
        # Normalise `mode` to the enum — accept strings too.
        try:
            mode = MatchMode(mode) if not isinstance(mode, MatchMode) else mode
        except ValueError:
            return MatchResult(
                passed=False,
                source="unresolved",
                reason=f"unknown match mode: {mode!r}",
                prompt_summary="GPS match: UNKNOWN (invalid match mode)",
            )

        if mode is MatchMode.ANY:
            return MatchResult(
                passed=True,
                source="any",
                reason=None,
                prompt_summary="GPS match: SKIPPED (mode=any)",
            )

        if _is_missing(submission_lat, submission_lng):
            return MatchResult(
                passed=False,
                source="unresolved",
                reason="submission GPS missing or invalid (null island / absent)",
                prompt_summary="GPS match: FAIL (submission GPS missing)",
            )

        # Type narrowing — checked by _is_missing above.
        sub_lat = float(submission_lat)  # type: ignore[arg-type]
        sub_lng = float(submission_lng)  # type: ignore[arg-type]

        if mode is MatchMode.STRICT:
            return self._match_strict(
                sub_lat, sub_lng, location_lat, location_lng, location_radius_m
            )

        # CITY / REGION / COUNTRY all need a resolved reference area.
        resolved = self._resolve_hint(sub_lat, sub_lng, location_hint)
        if resolved is None:
            return MatchResult(
                passed=False,
                source="unresolved",
                reason="location not resolved from hint",
                prompt_summary=(
                    f"GPS match: FAIL (hint {location_hint!r} could not be resolved)"
                    if location_hint
                    else "GPS match: FAIL (no location hint provided)"
                ),
            )

        radius_km = _apply_mode_radius(resolved, mode)
        distance = haversine_km(sub_lat, sub_lng, resolved.lat, resolved.lng)
        passed = distance <= radius_km

        summary = self._format_prompt(passed, distance, radius_km, resolved, mode)
        reason = (
            None
            if passed
            else (
                f"submission {distance:.1f}km from {resolved.display} center "
                f"(> {radius_km:.1f}km {mode.value} radius)"
            )
        )

        return MatchResult(
            passed=passed,
            distance_km=round(distance, 3),
            resolved_area=resolved.display,
            radius_used_km=round(radius_km, 3),
            source=resolved.source,
            reason=reason,
            prompt_summary=summary,
            resolved_country_code=resolved.country_code,
        )

    # ------------------------------------------------------------------ strict

    def _match_strict(
        self,
        sub_lat: float,
        sub_lng: float,
        loc_lat: Optional[float],
        loc_lng: Optional[float],
        radius_m: Optional[int],
    ) -> MatchResult:
        # For the TASK reference, only missing (None) counts as absent — an
        # intentionally-specified (0,0) is a legal point (null-island test).
        # The null-island heuristic applies to the submission only, since
        # that's the iPhone "permission denied" sentinel.
        if loc_lat is None or loc_lng is None:
            return MatchResult(
                passed=False,
                source="unresolved",
                reason="strict mode requires location_lat and location_lng",
                prompt_summary="GPS match: FAIL (strict mode needs task lat/lng)",
            )
        if radius_m is None or radius_m <= 0:
            logger.warning(
                "geo_match: strict mode called without location_radius_m — falling back to %dm",
                DEFAULT_STRICT_RADIUS_M,
            )
            radius_m = DEFAULT_STRICT_RADIUS_M
        radius_km = radius_m / 1000.0
        distance = haversine_km(sub_lat, sub_lng, float(loc_lat), float(loc_lng))  # type: ignore[arg-type]
        passed = distance <= radius_km
        summary = (
            f"GPS match: {'PASS' if passed else 'FAIL'} ("
            f"{distance * 1000:.0f} m from task point — "
            f"{'within' if passed else 'outside'} {radius_m} m strict radius)"
        )
        return MatchResult(
            passed=passed,
            distance_km=round(distance, 4),
            resolved_area=f"{loc_lat:.5f}, {loc_lng:.5f}",
            radius_used_km=round(radius_km, 4),
            source="strict",
            reason=None
            if passed
            else (
                f"submission {distance * 1000:.0f}m from task point (> {radius_m}m strict radius)"
            ),
            prompt_summary=summary,
        )

    # ------------------------------------------------------------------ resolvers

    def _resolve_hint(
        self,
        sub_lat: float,
        sub_lng: float,
        hint: Optional[str],
    ) -> Optional[_Resolved]:
        if not hint or not hint.strip():
            return None
        parsed = parse_location_hint(hint)

        # Layer 1: static US ZIP — only if the submission coords look US-ish
        # OR the hint explicitly names a US state/country.
        us_applicable = (
            coords_inside_us(sub_lat, sub_lng)
            or (parsed.country == "US")
            or (parsed.state in _US_STATE_TO_CODE.values())
        )
        if us_applicable and parsed.city:
            us_entry = self._us_lookup(parsed.city, parsed.state)
            if us_entry is not None:
                return _from_us(us_entry)

        # Layer 2: static global cities.
        if parsed.city:
            global_entry = self._global_lookup(parsed.city, parsed.country)
            if global_entry is not None:
                return _from_global(global_entry)

        # Layer 3: Nominatim forward geocode.
        place = self._nominatim.forward(hint)
        if place is not None:
            return _from_nominatim(place)
        return None

    # ------------------------------------------------------------------ format

    @staticmethod
    def _format_prompt(
        passed: bool,
        distance_km: float,
        radius_km: float,
        resolved: _Resolved,
        mode: MatchMode,
    ) -> str:
        verdict = "PASS" if passed else "FAIL"
        within = "within" if passed else "outside"
        return (
            f"GPS match: {verdict} ({distance_km:.1f} km from {resolved.display} "
            f"center — {within} {radius_km:.1f} km {mode.value} radius)"
        )


def _apply_mode_radius(resolved: _Resolved, mode: MatchMode) -> float:
    """Scale the city-level radius for broader modes (region, country)."""
    if mode is MatchMode.CITY:
        return resolved.radius_km
    if mode is MatchMode.REGION:
        # State/admin1 level — rough tolerance; good enough until real
        # polygon boundaries land.
        return max(resolved.radius_km, 200.0)
    if mode is MatchMode.COUNTRY:
        return max(resolved.radius_km, 2000.0)
    return resolved.radius_km


# Re-export for test convenience
__all__ = [
    "GeoMatcher",
    "MatchMode",
    "MatchResult",
    "haversine_km",
    "radius_km_for_population",
    "parse_location_hint",
    "ParsedHint",
]
