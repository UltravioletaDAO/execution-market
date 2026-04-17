"""
Tests for GPS handling inside the PHOTINT prompt builder.

Context (2026-04-16, WS-1 of MASTER_PLAN_GEO_MATCHING):
A legitimate "photo of the Miami sky" submission was auto-rejected
because the Ring 2 arbiter was told "GPS coordinates: Not provided"
even though the frontend had captured browser GPS and stored it at
`evidence.photo_geo.metadata.gps`. The bug was in
`mcp_server/verification/prompts/base.py`, which did a flat
`evidence.get("gps", "Not provided")` lookup and never descended into
the nested path the frontend actually uses.

These tests pin down the fixed lookup so it can't silently regress.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Mirror the root-level conftest setup so the test can be collected
# standalone (useful for worktree agents running a single file).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from verification.prompts.base import build_base_prompt  # noqa: E402
from verification.gps_utils import (  # noqa: E402
    extract_gps_details,
    format_gps_for_prompt,
)


pytestmark = pytest.mark.verification


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIAMI_LAT = 25.7617
MIAMI_LNG = -80.1918


def _task() -> dict:
    return {
        "title": "Photo of the Miami sky",
        "category": "physical_presence",
        "description": "Stand in Miami and take a photo of the sky.",
        "location": "Miami, FL",
        "deadline": "2026-04-17T00:00:00Z",
    }


def _browser_evidence() -> dict:
    """Shape that the dashboard actually produces for photo_geo."""
    return {
        "photo_geo": {
            "url": "https://cdn.example.com/miami-sky.jpg",
            "metadata": {
                "gps": {
                    "latitude": MIAMI_LAT,
                    "longitude": MIAMI_LNG,
                    "accuracy": 15,
                },
                "capturedAt": "2026-04-16T20:00:00Z",
            },
        },
        "notes": "clear sky, no clouds",
    }


def _flat_evidence() -> dict:
    """Legacy shape — coords at the top level of `evidence.gps`."""
    return {
        "gps": {"lat": MIAMI_LAT, "lng": MIAMI_LNG},
        "notes": "legacy client",
    }


# ---------------------------------------------------------------------------
# build_base_prompt GPS injection
# ---------------------------------------------------------------------------


class TestBuildBasePromptGps:
    def test_browser_geolocation_is_rendered(self):
        """Regression: photo_geo.metadata.gps must reach the prompt."""
        prompt = build_base_prompt(_task(), _browser_evidence())

        # Coordinates must appear in the prompt.
        assert "25.761700" in prompt
        assert "-80.191800" in prompt

        # The GPS line itself must no longer say "Not provided".
        gps_line = next(
            (line for line in prompt.splitlines() if "GPS coordinates:" in line),
            "",
        )
        assert "Not provided" not in gps_line, (
            "GPS line still renders 'Not provided' despite nested browser GPS: "
            f"{gps_line!r}"
        )

        # The source note mentions the browser origin so the AI can
        # weight accordingly.
        assert "browser" in gps_line.lower()

        # Accuracy is forwarded when present.
        assert "15" in gps_line

    def test_top_level_gps_still_works(self):
        """Backward-compat: the legacy `evidence.gps = {lat, lng}` shape."""
        prompt = build_base_prompt(_task(), _flat_evidence())
        gps_line = next(
            (line for line in prompt.splitlines() if "GPS coordinates:" in line),
            "",
        )
        assert "Not provided" not in gps_line
        assert "25.761700" in gps_line
        assert "-80.191800" in gps_line

    def test_no_gps_anywhere_falls_back_to_not_provided(self):
        """Preserve the existing fallback wording when nothing is found."""
        evidence = {
            "photo": "https://cdn.example.com/x.jpg",
            "notes": "no geolocation",
        }
        prompt = build_base_prompt(_task(), evidence)
        gps_line = next(
            (line for line in prompt.splitlines() if "GPS coordinates:" in line),
            "",
        )
        assert gps_line.strip() == "- GPS coordinates: Not provided"

    def test_null_island_is_treated_as_missing(self):
        """(0, 0) is the uninitialised-GPS sentinel — reject it."""
        evidence = {
            "photo_geo": {
                "metadata": {
                    "gps": {"latitude": 0.0, "longitude": 0.0, "accuracy": 9999},
                },
            },
        }
        prompt = build_base_prompt(_task(), evidence)
        gps_line = next(
            (line for line in prompt.splitlines() if "GPS coordinates:" in line),
            "",
        )
        assert gps_line.strip() == "- GPS coordinates: Not provided", (
            f"Null island leaked into prompt: {gps_line!r}"
        )


# ---------------------------------------------------------------------------
# Direct coverage for the helpers (fast/pure unit tests)
# ---------------------------------------------------------------------------


class TestFormatGpsForPrompt:
    def test_browser_path_emits_accuracy_and_source(self):
        text = format_gps_for_prompt(_browser_evidence())
        assert "25.761700" in text
        assert "-80.191800" in text
        assert "browser" in text.lower()
        assert "accuracy: 15m" in text

    def test_altitude_passthrough(self):
        evidence = {
            "photo_geo": {
                "metadata": {
                    "gps": {
                        "latitude": MIAMI_LAT,
                        "longitude": MIAMI_LNG,
                        "accuracy": 10,
                        "altitude": 3.5,
                    },
                },
            },
        }
        text = format_gps_for_prompt(evidence)
        assert "altitude: 3.5m" in text

    def test_no_gps_returns_not_provided(self):
        assert format_gps_for_prompt({}) == "Not provided"
        assert format_gps_for_prompt({"photo": "https://cdn/x.jpg"}) == "Not provided"

    def test_null_island_returns_not_provided(self):
        assert (
            format_gps_for_prompt({"gps": {"lat": 0.0, "lng": 0.0}}) == "Not provided"
        )


class TestExtractGpsDetails:
    def test_returns_none_for_empty_evidence(self):
        assert extract_gps_details({}) is None

    def test_returns_dict_for_browser_path(self):
        details = extract_gps_details(_browser_evidence())
        assert details is not None
        assert details["lat"] == pytest.approx(MIAMI_LAT)
        assert details["lng"] == pytest.approx(MIAMI_LNG)
        assert details["accuracy"] == pytest.approx(15.0)
        assert "browser" in details["source"].lower()

    def test_rejects_null_island(self):
        assert (
            extract_gps_details({"gps": {"lat": 0.0, "lng": 0.0, "accuracy": 1}})
            is None
        )
