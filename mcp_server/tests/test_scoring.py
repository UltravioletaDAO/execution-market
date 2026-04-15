"""Tests for dynamic reputation scoring engine.

Tests calculate_dynamic_score and per-dimension scorers:
- Speed scoring based on deadline ratio
- Evidence completeness scoring
- AI verification scoring
- Forensic metadata scoring
- Override passthrough
- Fallback when all data missing
- Score clamping to 0-100
- Determinism (same inputs = same output)
"""

import pytest
from datetime import datetime, timezone, timedelta

pytestmark = pytest.mark.erc8004

from reputation.scoring import (
    calculate_dynamic_score,
    _score_speed,
    _score_evidence,
    _score_ai_verification,
    _score_forensic,
    SPEED_MAX,
    SPEED_NEUTRAL,
    EVIDENCE_MAX,
    EVIDENCE_NEUTRAL,
    AI_VERIFICATION_MAX,
    AI_NEUTRAL,
    FORENSIC_MAX,
    FORENSIC_NEUTRAL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 2, 11, 12, 0, 0, tzinfo=timezone.utc)


def _make_task(
    created_at=None,
    deadline=None,
    evidence_requirements=None,
):
    t = {
        "id": "task-001",
        "title": "Test task",
        "created_at": (created_at or _NOW - timedelta(hours=2)).isoformat(),
        "deadline": (deadline or _NOW + timedelta(hours=2)).isoformat(),
    }
    if evidence_requirements is not None:
        t["evidence_requirements"] = evidence_requirements
    return t


def _make_submission(
    created_at=None,
    evidence_urls=None,
    ai_verification_score=None,
    ai_verification_result=None,
    gps_latitude=None,
    gps_longitude=None,
    metadata=None,
):
    s = {
        "id": "sub-001",
        "created_at": (created_at or _NOW).isoformat(),
    }
    if evidence_urls is not None:
        s["evidence_urls"] = evidence_urls
    if ai_verification_score is not None:
        s["ai_verification_score"] = ai_verification_score
    if ai_verification_result is not None:
        s["ai_verification_result"] = ai_verification_result
    if gps_latitude is not None:
        s["gps_latitude"] = gps_latitude
    if gps_longitude is not None:
        s["gps_longitude"] = gps_longitude
    if metadata is not None:
        s["metadata"] = metadata
    return s


def _make_executor():
    return {"id": "exec-001", "wallet_address": "0xABCDEF1234567890"}


# ---------------------------------------------------------------------------
# Speed dimension
# ---------------------------------------------------------------------------


class TestSpeedScoring:
    """Tests for _score_speed."""

    def test_very_fast_delivery(self):
        """Delivered at 10% of window -> SPEED_MAX."""
        task = _make_task(
            created_at=_NOW - timedelta(hours=10),
            deadline=_NOW + timedelta(hours=10),
        )
        sub = _make_submission(created_at=_NOW - timedelta(hours=8))
        assert _score_speed(task, sub) == SPEED_MAX

    def test_half_time_delivery(self):
        """Delivered at 50% of window -> ~85% of max."""
        task = _make_task(
            created_at=_NOW - timedelta(hours=4),
            deadline=_NOW,
        )
        sub = _make_submission(created_at=_NOW - timedelta(hours=2))
        score = _score_speed(task, sub)
        assert round(SPEED_MAX * 0.80) <= score <= SPEED_MAX

    def test_late_delivery(self):
        """Delivered after deadline -> low score."""
        task = _make_task(
            created_at=_NOW - timedelta(hours=4),
            deadline=_NOW - timedelta(hours=1),
        )
        sub = _make_submission(created_at=_NOW)
        score = _score_speed(task, sub)
        assert score <= 10

    def test_missing_data_returns_none(self):
        """Missing timestamps -> None (neutral will be used)."""
        assert _score_speed({}, {}) is None
        assert _score_speed({"created_at": _NOW.isoformat()}, {}) is None

    def test_zero_window_returns_none(self):
        """Deadline equals created_at -> None (avoid division by zero)."""
        task = _make_task(created_at=_NOW, deadline=_NOW)
        sub = _make_submission(created_at=_NOW)
        assert _score_speed(task, sub) is None


# ---------------------------------------------------------------------------
# Evidence dimension
# ---------------------------------------------------------------------------


class TestEvidenceScoring:
    """Tests for _score_evidence."""

    def test_all_requirements_met(self):
        """Met all evidence requirements -> high score."""
        task = _make_task(evidence_requirements=["photo", "receipt"])
        sub = _make_submission(evidence_urls=["url1", "url2"])
        score = _score_evidence(task, sub)
        assert score >= round(EVIDENCE_MAX * 0.85)

    def test_exceeded_requirements(self):
        """Provided more evidence than required -> max score."""
        task = _make_task(evidence_requirements=["photo"])
        sub = _make_submission(evidence_urls=["url1", "url2", "url3"])
        score = _score_evidence(task, sub)
        assert score == EVIDENCE_MAX

    def test_partial_evidence(self):
        """Only half the required evidence -> proportional."""
        task = _make_task(evidence_requirements=["photo", "receipt", "video", "gps"])
        sub = _make_submission(evidence_urls=["url1", "url2"])
        score = _score_evidence(task, sub)
        assert 0 < score < round(EVIDENCE_MAX * 0.85)

    def test_no_evidence_urls_returns_none(self):
        """No evidence_urls key -> None."""
        assert _score_evidence(_make_task(), {}) is None

    def test_empty_evidence_list_returns_none(self):
        """Empty evidence_urls list -> None."""
        assert _score_evidence(_make_task(), {"evidence_urls": []}) is None


# ---------------------------------------------------------------------------
# AI verification dimension
# ---------------------------------------------------------------------------


class TestAIVerificationScoring:
    """Tests for _score_ai_verification."""

    def test_high_ai_score(self):
        """High numeric AI score -> high dimension score."""
        sub = _make_submission(ai_verification_score=95)
        score = _score_ai_verification(sub)
        assert score >= round(AI_VERIFICATION_MAX * 0.9)

    def test_low_ai_score(self):
        """Low numeric AI score -> low dimension score."""
        sub = _make_submission(ai_verification_score=20)
        score = _score_ai_verification(sub)
        assert score <= round(AI_VERIFICATION_MAX * 0.3)

    def test_structured_result_with_score(self):
        """Structured result dict with 'score' key."""
        sub = _make_submission(ai_verification_result={"score": 80})
        score = _score_ai_verification(sub)
        assert score == round(AI_VERIFICATION_MAX * 80 / 100)

    def test_structured_result_boolean_pass(self):
        """Structured result with passed=True -> max."""
        sub = _make_submission(ai_verification_result={"passed": True})
        assert _score_ai_verification(sub) == AI_VERIFICATION_MAX

    def test_structured_result_boolean_fail(self):
        """Structured result with passed=False -> low."""
        sub = _make_submission(ai_verification_result={"passed": False})
        score = _score_ai_verification(sub)
        assert score <= round(AI_VERIFICATION_MAX * 0.3)

    def test_missing_ai_data_returns_none(self):
        """No AI verification data -> None."""
        assert _score_ai_verification({}) is None
        assert _score_ai_verification({"ai_verification_score": None}) is None


# ---------------------------------------------------------------------------
# Forensic dimension
# ---------------------------------------------------------------------------


class TestForensicScoring:
    """Tests for _score_forensic."""

    def test_full_metadata(self):
        """GPS + EXIF + device -> max score."""
        sub = _make_submission(
            gps_latitude=4.6097,
            gps_longitude=-74.0817,
            metadata={"exif": {"iso": 100}, "device": "iPhone 15"},
        )
        assert _score_forensic(sub) == FORENSIC_MAX

    def test_gps_only(self):
        """Just GPS -> 1/3 of max."""
        sub = _make_submission(gps_latitude=4.6097, gps_longitude=-74.0817)
        score = _score_forensic(sub)
        assert score == round(FORENSIC_MAX / 3)

    def test_no_metadata_returns_none(self):
        """No forensic signals -> None."""
        assert _score_forensic({}) is None
        assert _score_forensic({"metadata": {}}) is None


# ---------------------------------------------------------------------------
# Integration: calculate_dynamic_score
# ---------------------------------------------------------------------------


class TestCalculateDynamicScore:
    """Tests for the main calculate_dynamic_score function."""

    def test_fast_complete_high_ai_yields_high_score(self):
        """Fast delivery + full evidence + high AI -> score > 80."""
        task = _make_task(
            created_at=_NOW - timedelta(hours=10),
            deadline=_NOW + timedelta(hours=10),
            evidence_requirements=["photo"],
        )
        sub = _make_submission(
            created_at=_NOW - timedelta(hours=8),
            evidence_urls=["url1", "url2"],
            ai_verification_score=95,
            gps_latitude=4.6097,
            gps_longitude=-74.0817,
            metadata={"exif": {}, "device": "Pixel 8"},
        )
        result = calculate_dynamic_score(task, sub, _make_executor())
        assert result["score"] > 80
        assert result["source"] == "dynamic"
        assert "speed" in result["breakdown"]

    def test_slow_incomplete_weak_ai_yields_low_score(self):
        """Late + partial evidence + low AI -> score < 50."""
        task = _make_task(
            created_at=_NOW - timedelta(hours=4),
            deadline=_NOW - timedelta(hours=1),
            evidence_requirements=["photo", "receipt", "video", "gps"],
        )
        sub = _make_submission(
            created_at=_NOW,
            evidence_urls=["url1"],
            ai_verification_score=15,
        )
        result = calculate_dynamic_score(task, sub, _make_executor())
        assert result["score"] < 50
        assert result["source"] == "dynamic"

    def test_override_returns_exact_score(self):
        """Agent override -> exact score, source='override'."""
        result = calculate_dynamic_score({}, {}, {}, override_score=42)
        assert result["score"] == 42
        assert result["source"] == "override"

    def test_override_clamped_high(self):
        """Override > 100 clamped to 100."""
        result = calculate_dynamic_score({}, {}, {}, override_score=150)
        assert result["score"] == 100

    def test_override_clamped_low(self):
        """Override < 0 clamped to 0."""
        result = calculate_dynamic_score({}, {}, {}, override_score=-5)
        assert result["score"] == 0

    def test_missing_all_data_stable_neutral(self):
        """Empty dicts -> stable neutral score using neutrals, source='fallback'."""
        result = calculate_dynamic_score({}, {}, {})
        expected_neutral = (
            SPEED_NEUTRAL + EVIDENCE_NEUTRAL + AI_NEUTRAL + FORENSIC_NEUTRAL
        )
        assert result["score"] == expected_neutral
        assert result["source"] == "fallback"

    def test_score_always_clamped_0_100(self):
        """Score is always within [0, 100]."""
        # Even with maxed-out scores the sum should not exceed 100
        task = _make_task(
            created_at=_NOW - timedelta(hours=10),
            deadline=_NOW + timedelta(hours=10),
            evidence_requirements=["photo"],
        )
        sub = _make_submission(
            created_at=_NOW - timedelta(hours=9),
            evidence_urls=["u1", "u2", "u3"],
            ai_verification_score=100,
            gps_latitude=1.0,
            gps_longitude=1.0,
            metadata={"exif": True, "device": "test"},
        )
        result = calculate_dynamic_score(task, sub, _make_executor())
        assert 0 <= result["score"] <= 100

    def test_deterministic(self):
        """Same inputs always produce the same output."""
        task = _make_task(evidence_requirements=["photo"])
        sub = _make_submission(
            evidence_urls=["url1"],
            ai_verification_score=70,
        )
        executor = _make_executor()
        r1 = calculate_dynamic_score(task, sub, executor)
        r2 = calculate_dynamic_score(task, sub, executor)
        assert r1["score"] == r2["score"]
        assert r1["source"] == r2["source"]
        assert r1["breakdown"] == r2["breakdown"]

    def test_partial_data_uses_neutrals_for_missing(self):
        """Only speed is available -> others use neutrals."""
        task = _make_task(
            created_at=_NOW - timedelta(hours=4),
            deadline=_NOW,
        )
        sub = _make_submission(created_at=_NOW - timedelta(hours=1))
        result = calculate_dynamic_score(task, sub, _make_executor())
        assert result["source"] == "dynamic"
        # Speed is real, the rest are neutrals
        computed = result["breakdown"]["computed"]
        assert computed["evidence"] == EVIDENCE_NEUTRAL
        assert computed["ai_verification"] == AI_NEUTRAL
        assert computed["forensic"] == FORENSIC_NEUTRAL
