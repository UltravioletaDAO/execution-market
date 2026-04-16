"""
Unit tests for `mcp_server/verification/geo_match`.

Covers:
- Miami golden path (CITY mode, static resolver).
- Out-of-country hint (Tokyo) with Miami coords.
- Nominatim fallback returning None.
- MatchMode.ANY always passes and does not hit the resolvers.
- MatchMode.STRICT inside + outside radius.
- Null-island (0, 0) treated as missing.
- Haversine correctness against a known reference (NYC<->LA).

No live network calls: Nominatim is always mocked. Static datasets are
monkey-patched via `us_lookup=` / `global_lookup=` constructor args so we
don't depend on any CSV being present.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mirror the root-level conftest setup so the test can be collected
# standalone (useful for worktree agents running a single file).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from verification.geo_match import GeoMatcher, MatchMode, MatchResult  # noqa: E402
from verification.geo_match.resolver import (  # noqa: E402
    haversine_km,
    parse_location_hint,
    radius_km_for_population,
)
from verification.geo_match.static_global import GlobalCity  # noqa: E402
from verification.geo_match.static_us import USZipEntry  # noqa: E402


pytestmark = pytest.mark.verification


# --------------------------------------------------------------------------- fixtures

MIAMI_CENTER = (25.7617, -80.1918)
MIAMI_ENTRY = USZipEntry(
    zip="33101",
    lat=MIAMI_CENTER[0],
    lng=MIAMI_CENTER[1],
    city="Miami",
    state_id="FL",
    state_name="Florida",
    county="Miami-Dade",
    population=6_200_000,  # Miami metro — triggers 40 km radius
)

TOKYO_ENTRY = GlobalCity(
    geonameid=1850147,
    name="Tokyo",
    asciiname="Tokyo",
    lat=35.6895,
    lng=139.69171,
    country_code="JP",
    admin1_code="40",
    population=8_336_599,
)

NYC_ENTRY = USZipEntry(
    zip="10001",
    lat=40.7128,
    lng=-74.0060,
    city="New York",
    state_id="NY",
    state_name="New York",
    county="New York",
    population=8_500_000,
)


def _us_lookup_factory(*entries):
    registry = {(e.city.lower(), (e.state_id or "").lower()): e for e in entries}
    registry.update({(e.city.lower(), ""): e for e in entries})

    def _lookup(city, state=None):
        if not city:
            return None
        key_city = city.strip().lower()
        key_state = (state or "").strip().lower()
        return registry.get((key_city, key_state)) or registry.get((key_city, ""))

    return _lookup


def _global_lookup_factory(*entries):
    registry = {(e.name.lower(), (e.country_code or "").lower()): e for e in entries}
    registry.update({(e.name.lower(), ""): e for e in entries})
    registry.update({(e.asciiname.lower(), ""): e for e in entries})

    def _lookup(name, country=None):
        if not name:
            return None
        key_name = name.strip().lower()
        key_country = (country or "").strip().lower()
        return registry.get((key_name, key_country)) or registry.get((key_name, ""))

    return _lookup


@pytest.fixture
def nominatim_never_called():
    """Nominatim client whose `.forward()` fails the test if hit."""
    client = MagicMock()
    client.forward.side_effect = AssertionError(
        "Nominatim must not be called in this test"
    )
    client.reverse.side_effect = AssertionError(
        "Nominatim must not be called in this test"
    )
    return client


@pytest.fixture
def nominatim_returns_none():
    """Nominatim client whose `.forward()` always yields None (simulates 404/timeout)."""
    client = MagicMock()
    client.forward.return_value = None
    client.reverse.return_value = None
    return client


# --------------------------------------------------------------------------- haversine


def test_haversine_zero_distance():
    assert haversine_km(40.7128, -74.0060, 40.7128, -74.0060) == pytest.approx(
        0.0, abs=1e-9
    )


def test_haversine_nyc_to_la_matches_known_reference():
    # Reference distance NYC -> LA is ~3935 km.
    nyc = (40.7128, -74.0060)
    la = (34.0522, -118.2437)
    d = haversine_km(*nyc, *la)
    assert d == pytest.approx(3935.0, rel=0.01)  # within 1 percent of reference


def test_haversine_symmetric():
    d1 = haversine_km(25.97, -80.19, 25.76, -80.19)
    d2 = haversine_km(25.76, -80.19, 25.97, -80.19)
    assert d1 == pytest.approx(d2, rel=1e-12)


def test_haversine_tiny_meter_scale():
    # 0.00001 degree of latitude at the equator is ~1.1 m.
    d_km = haversine_km(0.0, 0.0, 0.00001, 0.0)
    assert d_km == pytest.approx(0.00111, abs=2e-4)


# --------------------------------------------------------------------------- radius table


def test_radius_by_population_buckets():
    assert radius_km_for_population(10_000_000) == 40.0
    assert radius_km_for_population(6_000_000) == 40.0
    assert radius_km_for_population(2_000_000) == 25.0
    assert radius_km_for_population(500_000) == 15.0
    assert radius_km_for_population(50_000) == 8.0
    assert radius_km_for_population(5_000) == 3.0
    assert radius_km_for_population(0) == 10.0
    assert radius_km_for_population(None) == 10.0


# --------------------------------------------------------------------------- hint parser


def test_parse_hint_city_state_country():
    parsed = parse_location_hint("Miami, FL, USA")
    assert parsed.city == "Miami"
    assert parsed.state == "FL"
    assert parsed.country == "US"


def test_parse_hint_city_only():
    parsed = parse_location_hint("Tokyo")
    assert parsed.city == "Tokyo"
    assert parsed.state is None
    assert parsed.country is None


def test_parse_hint_with_full_state_name():
    parsed = parse_location_hint("Miami, Florida")
    assert parsed.city == "Miami"
    assert parsed.state == "FL"
    assert parsed.country == "US"


def test_parse_hint_empty():
    parsed = parse_location_hint("")
    assert parsed.city is None
    assert parsed.state is None
    assert parsed.country is None


# --------------------------------------------------------------------------- MatchMode.ANY


def test_mode_any_always_passes(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=0.0,
        submission_lng=0.0,  # even null island is fine under ANY
        mode=MatchMode.ANY,
    )
    assert isinstance(result, MatchResult)
    assert result.passed is True
    assert result.source == "any"
    assert "SKIPPED" in result.prompt_summary


def test_mode_any_also_accepts_real_coords(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(25.97, -80.19, MatchMode.ANY, location_hint="Tokyo")
    assert result.passed is True


# --------------------------------------------------------------------------- Miami golden path


def test_miami_city_match_via_static_us(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(MIAMI_ENTRY),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode=MatchMode.CITY,
        location_hint="Miami, FL, USA",
    )
    assert result.passed is True, result.reason
    assert result.source == "static_us_zip"
    assert result.resolved_area == "Miami, FL, US"
    assert result.radius_used_km == pytest.approx(40.0)
    # Distance from 25.97, -80.19 to 25.76, -80.19 is ~23 km.
    assert result.distance_km == pytest.approx(23.0, abs=1.0)
    assert "PASS" in result.prompt_summary
    assert "Miami" in result.prompt_summary


def test_miami_city_match_falls_through_to_global_when_us_csv_absent(
    nominatim_never_called,
):
    """Simulates CI environment with no US ZIP CSV — must still succeed via GeoNames."""
    miami_global = GlobalCity(
        geonameid=4164138,
        name="Miami",
        asciiname="Miami",
        lat=25.7617,
        lng=-80.1918,
        country_code="US",
        admin1_code="FL",
        population=6_200_000,
    )
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),  # empty
        global_lookup=_global_lookup_factory(miami_global),
    )
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode=MatchMode.CITY,
        location_hint="Miami, FL, USA",
    )
    assert result.passed is True, result.reason
    assert result.source == "static_global"
    assert result.radius_used_km == pytest.approx(40.0)


# --------------------------------------------------------------------------- cross-country


def test_miami_coords_with_tokyo_hint_fails(nominatim_never_called):
    """Cross-country: Miami submission + Tokyo hint should reject."""
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(MIAMI_ENTRY),
        global_lookup=_global_lookup_factory(TOKYO_ENTRY),
    )
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode=MatchMode.CITY,
        location_hint="Tokyo, Japan",
    )
    assert result.passed is False
    assert result.source == "static_global"
    assert result.distance_km is not None and result.distance_km > 10_000
    assert "Tokyo" in (result.resolved_area or "")
    assert "FAIL" in result.prompt_summary


# --------------------------------------------------------------------------- unknown hint -> Nominatim None


def test_unknown_hint_falls_to_nominatim_and_fails_when_none(nominatim_returns_none):
    matcher = GeoMatcher(
        nominatim_client=nominatim_returns_none,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode=MatchMode.CITY,
        location_hint="Xyzzy-Not-A-Place, QQ",
    )
    assert result.passed is False
    assert result.source == "unresolved"
    assert result.reason is not None
    assert "resolved" in result.reason.lower()
    nominatim_returns_none.forward.assert_called_once()


def test_unknown_hint_resolved_by_nominatim():
    """Nominatim returns a valid place — matcher uses it as the reference area."""
    from verification.geo_match.nominatim import NominatimPlace

    place = NominatimPlace(
        lat=25.7617,
        lng=-80.1918,
        display_name="Miami, Florida, USA",
        country_code="us",
        city="Miami",
        state="Florida",
        place_type="city",
        place_class="place",
        raw={},
    )
    client = MagicMock()
    client.forward.return_value = place
    matcher = GeoMatcher(
        nominatim_client=client,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode=MatchMode.CITY,
        location_hint="Somewhere Nominatim Understands",
    )
    assert result.passed is True
    assert result.source == "nominatim"
    client.forward.assert_called_once()


# --------------------------------------------------------------------------- STRICT


def test_strict_inside_radius(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    # 500m radius around (0,1) — small offset
    result = matcher.match(
        submission_lat=0.001,  # ~111m north of (0, 1)
        submission_lng=1.0,
        mode=MatchMode.STRICT,
        location_lat=0.0,
        location_lng=1.0,
        location_radius_m=500,
    )
    assert result.passed is True
    assert result.source == "strict"
    assert result.distance_km is not None and result.distance_km < 0.5


def test_strict_outside_radius(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=0.01,  # ~1.1 km north
        submission_lng=1.0,
        mode=MatchMode.STRICT,
        location_lat=0.0,
        location_lng=1.0,
        location_radius_m=500,
    )
    assert result.passed is False
    assert result.source == "strict"
    assert result.reason is not None
    assert "500" in result.reason  # radius surfaced in the reason


def test_strict_missing_coords(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=25.97,
        submission_lng=-80.19,
        mode=MatchMode.STRICT,
        location_lat=None,
        location_lng=None,
        location_radius_m=500,
    )
    assert result.passed is False
    assert "requires" in (result.reason or "").lower()


def test_strict_default_radius_when_missing(caplog, nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    # Without radius, fallback is 500 m. 400 m offset should pass.
    # (We use a non-null-island anchor so the submission coords aren't
    # mistaken for the "GPS missing" sentinel (0,0).)
    result = matcher.match(
        submission_lat=40.0036,  # ~400 m north of (40, -74)
        submission_lng=-74.0,
        mode=MatchMode.STRICT,
        location_lat=40.0,
        location_lng=-74.0,
        location_radius_m=None,
    )
    assert result.passed is True
    assert result.radius_used_km == pytest.approx(0.5)


# --------------------------------------------------------------------------- null-island / missing


def test_null_island_submission_rejected(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(MIAMI_ENTRY),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=0.0,
        submission_lng=0.0,
        mode=MatchMode.CITY,
        location_hint="Miami, FL, USA",
    )
    assert result.passed is False
    assert result.source == "unresolved"
    assert "missing" in (result.reason or "").lower()


def test_none_submission_coords_rejected(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(MIAMI_ENTRY),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=None,
        submission_lng=None,
        mode=MatchMode.CITY,
        location_hint="Miami, FL, USA",
    )
    assert result.passed is False


# --------------------------------------------------------------------------- module import robustness


def test_module_imports_without_data_files(tmp_path, monkeypatch):
    """Guard: resetting both indexes to non-existent paths must not crash imports."""
    from verification.geo_match import static_global, static_us

    bogus_us = tmp_path / "nope_us.csv"
    bogus_global = tmp_path / "nope_global.txt"
    static_us.reset_index_for_tests(bogus_us)
    static_global.reset_index_for_tests(bogus_global)
    try:
        assert static_us.lookup_us_city("Miami", "FL") is None
        assert static_global.lookup_global_city("Miami") is None
    finally:
        static_us.reset_index_for_tests(None)
        static_global.reset_index_for_tests(None)


def test_static_us_csv_parse_roundtrip(tmp_path):
    """Real-format Simple Maps CSV header is parsed correctly."""
    from verification.geo_match import static_us

    csv_path = tmp_path / "us.csv"
    csv_path.write_text(
        "zip,lat,lng,city,state_id,state_name,county_name,population\n"
        "33101,25.76,-80.19,Miami,FL,Florida,Miami-Dade,6200000\n"
        "10001,40.7128,-74.0060,New York,NY,New York,New York,8500000\n",
        encoding="utf-8",
    )
    static_us.reset_index_for_tests(csv_path)
    try:
        miami = static_us.lookup_us_city("Miami", "FL")
        nyc = static_us.lookup_us_city("new york")  # case-insensitive
        assert miami is not None and miami.population == 6_200_000
        assert nyc is not None and nyc.state_id == "NY"
    finally:
        static_us.reset_index_for_tests(None)


def test_static_global_geonames_parse_roundtrip(tmp_path):
    """Real-format GeoNames tab-separated file is parsed correctly."""
    from verification.geo_match import static_global

    tsv_path = tmp_path / "cities.txt"
    tsv_path.write_text(
        # Columns: geonameid, name, asciiname, alternatenames, lat, lng,
        #          feature_class, feature_code, country_code, cc2, admin1,
        #          admin2, admin3, admin4, population, elevation, dem,
        #          timezone, modification_date
        "1850147\tTokyo\tTokyo\t\t35.6895\t139.6917\tP\tPPLC\tJP\t\t40\t"
        "\t\t\t8336599\t40\t40\tAsia/Tokyo\t2021-01-01\n",
        encoding="utf-8",
    )
    static_global.reset_index_for_tests(tsv_path)
    try:
        city = static_global.lookup_global_city("Tokyo", "JP")
        assert city is not None
        assert city.population == 8_336_599
        assert city.country_code == "JP"
    finally:
        static_global.reset_index_for_tests(None)


# --------------------------------------------------------------------------- input normalisation


def test_string_mode_is_accepted(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(MIAMI_ENTRY),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode="city",  # string, not enum
        location_hint="Miami, FL, USA",
    )
    assert result.passed is True


def test_unknown_mode_returns_error(nominatim_never_called):
    matcher = GeoMatcher(
        nominatim_client=nominatim_never_called,
        us_lookup=_us_lookup_factory(),
        global_lookup=_global_lookup_factory(),
    )
    result = matcher.match(
        submission_lat=25.97,
        submission_lng=-80.19,
        mode="galactic",
    )
    assert result.passed is False
    assert "match mode" in (result.reason or "")
