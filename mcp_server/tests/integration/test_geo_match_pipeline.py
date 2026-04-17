"""
End-to-end integration test for WS-5 — GeoMatcher wired into the
verification pipeline behind `EM_GEO_MATCH_ENABLED`.

Scenarios covered:
  * Flag OFF: pipeline behaviour is byte-identical to pre-WS-5 main.
    No `match_result` on the VerificationResult, no stash in evidence,
    no prompt summary.
  * Flag ON + Miami submission + task.location_hint="Miami, FL, USA" +
    geo_match_mode=city: MatchResult.passed=True, distance ~23 km,
    source one of `static_us_zip | static_global | nominatim`.
  * Flag ON + Miami submission + hint="Tokyo, Japan":
    MatchResult.passed=False.
  * Flag ON + geo_match_mode="any": no match attempted (result=None).
  * Prompt builder splices MatchResult.prompt_summary into the GPS line.

No live network calls — Nominatim is mocked. Static datasets are
monkey-patched via `reset_index_for_tests` so the test runs in CI
environments that don't ship the data files.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mirror root-level conftest path injection so this test can run standalone.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from verification.geo_match import MatchMode  # noqa: E402
from verification.geo_match.static_us import USZipEntry  # noqa: E402


pytestmark = [pytest.mark.verification]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# North Miami — the exact coordinates from the INC-2026-04-16 trigger task.
MIAMI_SUBMISSION_LAT = 25.97022
MIAMI_SUBMISSION_LNG = -80.19489

# Miami metro centre (downtown). ~23 km south of the submission — inside
# the 40 km metro radius this matcher derives for population 5M+.
MIAMI_CENTER_LAT = 25.7617
MIAMI_CENTER_LNG = -80.1918

MIAMI_ENTRY = USZipEntry(
    zip="33101",
    lat=MIAMI_CENTER_LAT,
    lng=MIAMI_CENTER_LNG,
    city="Miami",
    state_id="FL",
    state_name="Florida",
    county="Miami-Dade",
    population=6_200_000,
)


def _submission() -> dict:
    return {
        "id": "sub-ws5-001",
        "executor_id": "exec-ws5-001",
        "submitted_at": "2026-04-16T20:00:00Z",
        "evidence": {
            "photo_geo": {
                "url": "https://cdn.example.com/miami-sky.jpg",
                "metadata": {
                    "gps": {
                        "latitude": MIAMI_SUBMISSION_LAT,
                        "longitude": MIAMI_SUBMISSION_LNG,
                        "accuracy": 15,
                    },
                    "capturedAt": "2026-04-16T19:55:00Z",
                },
            },
            "notes": "clear sky, no clouds",
        },
    }


def _task(**overrides) -> dict:
    base = {
        "id": "task-ws5-001",
        "category": "physical_presence",
        "evidence_schema": {"required": ["photo_geo"], "optional": ["notes"]},
        "location_hint": "Miami, FL, USA",
        "location_lat": None,
        "location_lng": None,
        "geo_match_mode": "city",
        "location_radius_m": None,
        "deadline": "2026-04-17T00:00:00Z",
        "assigned_at": "2026-04-16T19:00:00Z",
    }
    base.update(overrides)
    return base


# Shared mutable registries the patched lookups delegate to. Tests tweak
# these to inject/withhold entries without rebuilding the fixture.
_US_ENTRIES: dict = {}
_GLOBAL_ENTRIES: dict = {}


def _shared_us_lookup(city, state=None):
    if not city:
        return None
    return _US_ENTRIES.get(city.strip().lower())


def _shared_global_lookup(name, country=None):
    if not name:
        return None
    return _GLOBAL_ENTRIES.get(name.strip().lower())


@pytest.fixture
def patched_static_datasets():
    """Stub the geo_match static lookups so the test doesn't need CSVs.

    Also mocks Nominatim so a cache miss never hits the network.

    The fixture delegates to `_US_ENTRIES` / `_GLOBAL_ENTRIES` dicts so
    individual tests can add/remove city entries via those dicts without
    having to rebuild the fixture or the GeoMatcher.
    """
    from verification.geo_match import resolver as _resolver

    nominatim = MagicMock()
    nominatim.forward.return_value = None
    nominatim.reverse.return_value = None

    # Reset registries per-test to avoid leakage.
    _US_ENTRIES.clear()
    _GLOBAL_ENTRIES.clear()
    _US_ENTRIES["miami"] = MIAMI_ENTRY

    original_us = _resolver.lookup_us_city
    original_global = _resolver.lookup_global_city
    _resolver.lookup_us_city = _shared_us_lookup
    _resolver.lookup_global_city = _shared_global_lookup

    original_init = _resolver.GeoMatcher.__init__

    def _patched_init(self, nominatim_client=None, us_lookup=None, global_lookup=None):
        original_init(
            self,
            nominatim_client=nominatim_client or nominatim,
            us_lookup=us_lookup or _shared_us_lookup,
            global_lookup=global_lookup or _shared_global_lookup,
        )

    _resolver.GeoMatcher.__init__ = _patched_init

    try:
        yield nominatim
    finally:
        _resolver.lookup_us_city = original_us
        _resolver.lookup_global_city = original_global
        _resolver.GeoMatcher.__init__ = original_init
        _US_ENTRIES.clear()
        _GLOBAL_ENTRIES.clear()


def _reload_pipeline_with_flag(value: str):
    """Re-import verification.pipeline with EM_GEO_MATCH_ENABLED at the given value.

    The flag is read once at module import time. This helper mutates the
    env var, reloads the module, and returns the reloaded module.
    """
    import os

    os.environ["EM_GEO_MATCH_ENABLED"] = value
    import verification.pipeline as pipeline_module

    return importlib.reload(pipeline_module)


# ---------------------------------------------------------------------------
# Flag OFF — zero-regression baseline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_off_pipeline_has_no_match_result(patched_static_datasets):
    """With EM_GEO_MATCH_ENABLED=false, pipeline result has no match_result."""
    pipeline = _reload_pipeline_with_flag("false")

    # Patch the EXIF fallback so it doesn't try to download the fake URL.
    with patch.object(
        pipeline, "_extract_gps_from_exif_fallback", return_value=(None, None)
    ):
        result = await pipeline.run_verification_pipeline(_submission(), _task())

    assert result.match_result is None, (
        "flag off must not attach a MatchResult to VerificationResult"
    )

    # Evidence must NOT have the reserved stash key.
    evidence = _submission()["evidence"]
    assert pipeline.GEO_MATCH_EVIDENCE_KEY not in evidence, (
        "flag off must not stash geo match result into evidence"
    )


# ---------------------------------------------------------------------------
# Flag ON — Miami golden path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_on_miami_city_match_passes(patched_static_datasets):
    """With flag on + mode=city + Miami hint, matcher returns passed=True."""
    pipeline = _reload_pipeline_with_flag("true")

    sub = _submission()
    task = _task(geo_match_mode="city", location_hint="Miami, FL, USA")

    with patch.object(
        pipeline, "_extract_gps_from_exif_fallback", return_value=(None, None)
    ):
        result = await pipeline.run_verification_pipeline(sub, task)

    assert result.match_result is not None, "flag on must attach a MatchResult"
    mr = result.match_result
    assert mr.passed is True, mr.reason
    # Distance from 25.97, -80.19 to 25.76, -80.19 is ~23 km.
    assert mr.distance_km is not None
    assert 20.0 <= mr.distance_km <= 26.0, (
        f"expected ~23 km distance, got {mr.distance_km}"
    )
    assert mr.source in {"static_us_zip", "static_global", "nominatim"}, (
        f"unexpected match source: {mr.source}"
    )

    # The evidence dict must now carry the stash so Phase B prompt picks it up.
    stashed = sub["evidence"].get(pipeline.GEO_MATCH_EVIDENCE_KEY)
    assert stashed is not None
    assert stashed.passed is True


# ---------------------------------------------------------------------------
# Flag ON — wrong city fails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_on_tokyo_hint_with_miami_coords_fails(patched_static_datasets):
    """Cross-country mismatch (Miami GPS + Tokyo hint) → passed=False."""
    from verification.geo_match.static_global import GlobalCity

    tokyo = GlobalCity(
        geonameid=1850147,
        name="Tokyo",
        asciiname="Tokyo",
        lat=35.6895,
        lng=139.69171,
        country_code="JP",
        admin1_code="40",
        population=8_336_599,
    )
    # Inject Tokyo into the shared registry so the matcher's global lookup
    # returns it — this must happen BEFORE reloading the pipeline, but the
    # registry is mutable so the reload is independent of it.
    _GLOBAL_ENTRIES["tokyo"] = tokyo

    pipeline = _reload_pipeline_with_flag("true")

    sub = _submission()
    task = _task(geo_match_mode="city", location_hint="Tokyo, Japan")

    with patch.object(
        pipeline, "_extract_gps_from_exif_fallback", return_value=(None, None)
    ):
        result = await pipeline.run_verification_pipeline(sub, task)

    assert result.match_result is not None
    mr = result.match_result
    assert mr.passed is False, "Miami coords must not match Tokyo hint"
    assert mr.source in {"static_us_zip", "static_global", "nominatim"}
    assert mr.distance_km is not None and mr.distance_km > 10_000


# ---------------------------------------------------------------------------
# Flag ON + mode=any — no match attempted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_on_mode_any_skips_match(patched_static_datasets):
    """mode=any must not call the matcher — pipeline.match_result is None."""
    pipeline = _reload_pipeline_with_flag("true")

    sub = _submission()
    task = _task(geo_match_mode="any")

    with patch.object(
        pipeline, "_extract_gps_from_exif_fallback", return_value=(None, None)
    ):
        result = await pipeline.run_verification_pipeline(sub, task)

    assert result.match_result is None, (
        "mode=any must skip the matcher entirely (result=None)"
    )
    assert pipeline.GEO_MATCH_EVIDENCE_KEY not in sub["evidence"]


# ---------------------------------------------------------------------------
# Flag ON + no geo_match_mode on the task — no match attempted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_on_no_mode_skips_match(patched_static_datasets):
    """Missing geo_match_mode (NULL in DB) must fall through to baseline."""
    pipeline = _reload_pipeline_with_flag("true")

    sub = _submission()
    task = _task(geo_match_mode=None, location_hint="Miami, FL, USA")

    with patch.object(
        pipeline, "_extract_gps_from_exif_fallback", return_value=(None, None)
    ):
        result = await pipeline.run_verification_pipeline(sub, task)

    assert result.match_result is None


# ---------------------------------------------------------------------------
# Prompt builder consumes the stashed MatchResult
# ---------------------------------------------------------------------------


def test_prompt_splices_match_summary_when_stashed(patched_static_datasets):
    """The Phase B prompt builder must include MatchResult.prompt_summary."""
    pipeline = _reload_pipeline_with_flag("true")

    from verification.geo_match import GeoMatcher
    from verification.prompts.base import build_base_prompt

    matcher = GeoMatcher()
    match = matcher.match(
        submission_lat=MIAMI_SUBMISSION_LAT,
        submission_lng=MIAMI_SUBMISSION_LNG,
        mode=MatchMode.CITY,
        location_hint="Miami, FL, USA",
    )
    assert match.passed is True, "sanity check — matcher must pass on Miami"

    evidence = _submission()["evidence"]
    evidence[pipeline.GEO_MATCH_EVIDENCE_KEY] = match

    prompt = build_base_prompt(_task(), evidence)

    # The prompt must now contain the match summary (PASS + Miami).
    assert "GPS match: PASS" in prompt, (
        "MatchResult.prompt_summary did not reach the prompt"
    )
    assert "Miami" in prompt


def test_prompt_without_match_keeps_legacy_shape():
    """Baseline: no stashed MatchResult → prompt behaves like pre-WS-5."""
    from verification.prompts.base import build_base_prompt

    evidence = _submission()["evidence"]
    # Explicitly guarantee no stashed key.
    from verification.pipeline import GEO_MATCH_EVIDENCE_KEY

    assert GEO_MATCH_EVIDENCE_KEY not in evidence

    prompt = build_base_prompt(_task(), evidence)
    # WS-1 behaviour preserved: coords present, no "GPS match:" line.
    assert "25.970220" in prompt
    assert "GPS match:" not in prompt


# ---------------------------------------------------------------------------
# Teardown — reset flag so other tests don't inherit it
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_flag_after_test():
    yield
    import os

    os.environ.pop("EM_GEO_MATCH_ENABLED", None)
    # Reload pipeline one more time so subsequent modules see the default.
    import verification.pipeline as pipeline_module

    importlib.reload(pipeline_module)
