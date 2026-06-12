"""Phase 4 of the Rings Verification fixes — GPS/geo end to end.

Covers:
- C-20: the task's reference location reaches the AI prompt (it used to
  render "Location: Not specified" on 100% of verifications).
- C-21/U-09: the GeoMatch result survives SQS JSON serialization.
- C-24/C-25: one effective radius shared by pipeline + geo-reference endpoint.
- U-16/U-17/U-18: coordinate sanity helper + honest GPS source labels.
"""

import json
from dataclasses import asdict

import pytest

from verification.gps_utils import is_valid_coordinate
from verification.pipeline import effective_gps_radius_m
from verification.prompts.base import build_base_prompt


# ---------------------------------------------------------------------------
# C-20 — task location reaches the prompt
# ---------------------------------------------------------------------------


class TestPromptLocation:
    def test_location_renders_hint_coords_and_radius(self):
        task = {
            "title": "Photo of storefront",
            "category": "physical_presence",
            "instructions": "Take a photo",
            "location_hint": "North Miami, FL",
            "location_lat": 25.89,
            "location_lng": -80.18,
            "location_radius_m": 500,
        }
        prompt = build_base_prompt(task, {})
        assert (
            "**Location**: North Miami, FL — (25.89000, -80.18000), radius 500 m"
            in prompt
        )

    def test_location_radius_km_fallback(self):
        task = {
            "title": "t",
            "category": "physical_presence",
            "instructions": "x",
            "location_lat": 4.6,
            "location_lng": -74.08,
            "location_radius_km": 2.5,
        }
        prompt = build_base_prompt(task, {})
        assert "(4.60000, -74.08000), radius 2.5 km" in prompt

    def test_no_location_says_not_specified(self):
        task = {"title": "t", "category": "general", "instructions": "x"}
        prompt = build_base_prompt(task, {})
        assert "**Location**: Not specified" in prompt

    def test_null_island_reference_is_ignored(self):
        task = {
            "title": "t",
            "category": "general",
            "instructions": "x",
            "location_lat": 0.0,
            "location_lng": 0.0,
        }
        prompt = build_base_prompt(task, {})
        assert "**Location**: Not specified" in prompt

    def test_equator_latitude_is_rendered(self):
        """U-17: 0.0 latitude with a real longitude is a valid coordinate."""
        task = {
            "title": "t",
            "category": "general",
            "instructions": "x",
            "location_lat": 0.0,
            "location_lng": 36.82,
        }
        prompt = build_base_prompt(task, {})
        assert "(0.00000, 36.82000)" in prompt


# ---------------------------------------------------------------------------
# C-21/U-09 — GeoMatch survives the SQS round trip
# ---------------------------------------------------------------------------


class TestGeoMatchSerialization:
    def test_match_result_dict_round_trips_through_json(self):
        from verification.geo_match.resolver import MatchResult
        from verification.prompts.base import _format_match_summary

        result = MatchResult(
            passed=True,
            distance_km=23.0,
            resolved_area="Miami metro",
            radius_used_km=40.0,
            source="static_us_zip",
            prompt_summary="GPS match: PASS (23 km from Miami metro)",
        )
        # The pipeline now stashes asdict(result); simulate the SQS publish
        # (json.dumps(default=str)) + Lambda-side parse.
        message = {"evidence": {"__geo_match_result__": asdict(result)}}
        parsed = json.loads(json.dumps(message, default=str))

        stashed = parsed["evidence"]["__geo_match_result__"]
        assert stashed["passed"] is True  # not a repr string
        assert (
            _format_match_summary(parsed["evidence"])
            == "GPS match: PASS (23 km from Miami metro)"
        )

    def test_dataclass_stash_would_break(self):
        """Documents the original bug: stashing the dataclass produced a
        useless repr string after json.dumps(default=str)."""
        from verification.geo_match.resolver import MatchResult
        from verification.prompts.base import _format_match_summary

        result = MatchResult(passed=True, prompt_summary="GPS match: PASS")
        message = {"evidence": {"__geo_match_result__": result}}
        parsed = json.loads(json.dumps(message, default=str))

        assert isinstance(parsed["evidence"]["__geo_match_result__"], str)
        assert _format_match_summary(parsed["evidence"]) == ""


# ---------------------------------------------------------------------------
# C-24/C-25 — one effective radius
# ---------------------------------------------------------------------------


class TestEffectiveRadius:
    @pytest.mark.parametrize(
        ("task", "expected_m"),
        [
            ({"category": "physical_presence", "location_radius_km": 2}, 2000),
            ({"category": "physical_presence"}, 500),
            ({"category": "simple_action"}, 1000),
            ({"category": "verification"}, 500),
            ({"category": "physical_presence", "location_radius_km": 0}, 500),
            ({"category": "physical_presence", "location_radius_km": "bad"}, 500),
        ],
    )
    def test_effective_radius(self, task, expected_m):
        assert effective_gps_radius_m(task) == expected_m


# ---------------------------------------------------------------------------
# U-16/U-17 — coordinate sanity
# ---------------------------------------------------------------------------


class TestIsValidCoordinate:
    @pytest.mark.parametrize(
        ("lat", "lng", "valid"),
        [
            (25.76, -80.19, True),
            (0.0, 36.82, True),  # equator — 0.0 lat is real
            (51.48, 0.0, True),  # Greenwich — 0.0 lng is real
            (0.0, 0.0, False),  # null island
            (None, -80.19, False),
            (25.76, None, False),
            (None, None, False),
            (91.0, 0.5, False),  # out of range
            (45.0, 181.0, False),
            ("25.76", "-80.19", True),  # numeric strings coerce
            ("abc", 10.0, False),
        ],
    )
    def test_validity(self, lat, lng, valid):
        assert is_valid_coordinate(lat, lng) is valid


# ---------------------------------------------------------------------------
# U-18 — GPS source labels
# ---------------------------------------------------------------------------


class TestGpsSourceLabels:
    def test_exif_blob_with_zero_accuracy_not_labeled_browser(self):
        from verification.gps_utils import extract_gps_details

        evidence = {"photo_geo": {"lat": 25.76, "lng": -80.19, "accuracy": 0}}
        details = extract_gps_details(evidence)
        assert details is not None
        assert details["source"] == "EXIF"

    def test_zero_accuracy_not_rendered_in_prompt(self):
        from verification.gps_utils import format_gps_for_prompt

        evidence = {"photo_geo": {"lat": 25.76, "lng": -80.19, "accuracy": 0}}
        rendered = format_gps_for_prompt(evidence)
        assert "accuracy" not in rendered

    def test_real_browser_accuracy_still_labeled(self):
        from verification.gps_utils import extract_gps_details

        evidence = {"photo_geo": {"lat": 25.76, "lng": -80.19, "accuracy": 15}}
        details = extract_gps_details(evidence)
        assert details["source"] == "browser geolocation"
