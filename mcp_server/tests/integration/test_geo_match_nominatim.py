"""
Integration smoke test — ONE real Nominatim call.

Skipped by default in CI. To run explicitly:
    pytest -m integration tests/integration/test_geo_match_nominatim.py

Rationale: Nominatim is a public free service with strict rate limits.
The unit test suite mocks it; this file exists to catch drift in their
response shape or our User-Agent policy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from verification.geo_match import GeoMatcher, MatchMode  # noqa: E402
from verification.geo_match.nominatim import NominatimClient  # noqa: E402


@pytest.mark.integration
def test_nominatim_reverse_miami_real_network():
    """A single real Nominatim forward-geocode of 'Miami, FL, USA'.

    Honours Nominatim's 1 req/s policy via the built-in rate limiter.
    """
    client = NominatimClient()
    place = client.forward("Miami, FL, USA")
    assert place is not None, "Nominatim returned no result for 'Miami, FL, USA'"
    assert place.country_code == "us"
    # Miami downtown is ~25.76, -80.19
    assert 25.0 < place.lat < 26.5
    assert -81.0 < place.lng < -79.5


@pytest.mark.integration
def test_matcher_end_to_end_with_live_nominatim():
    """Full match against live Nominatim — no static datasets required."""
    matcher = GeoMatcher(
        # Point the static layers at lookups that always miss, forcing Nominatim.
        us_lookup=lambda city, state=None: None,
        global_lookup=lambda name, country=None: None,
    )
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode=MatchMode.CITY,
        location_hint="Miami, Florida",
    )
    assert result.source == "nominatim"
    assert result.passed is True, result.reason
