"""
Unit tests for verdict message builder (V3-B).

Tests:
- Grade assignment from 0.0-1.0 scores
- Pass / fail / inconclusive message generation
- Message character limit (500 chars for mobile)
- Check detail extraction from ring scores
- Fix suggestion generation
- Scoring field extraction for API responses
- Edge cases: empty ring scores, skipped verdicts

Run:
    pytest tests/test_verdict_messages.py -v
    pytest -m arbiter  # included in arbiter marker
"""

import pytest

from integrations.arbiter.messages import (
    MAX_MESSAGE_LENGTH,
    _extract_check_details,
    _generate_fix_suggestions,
    build_fail_message,
    build_inconclusive_message,
    build_pass_message,
    build_verdict_message,
    extract_scoring_fields,
    score_to_grade,
    score_to_pct,
)
from integrations.arbiter.types import (
    ArbiterDecision,
    ArbiterTier,
    ArbiterVerdict,
    RingScore,
)

pytestmark = pytest.mark.arbiter


# ============================================================================
# Fixtures
# ============================================================================


def _make_verdict(
    decision: ArbiterDecision = ArbiterDecision.PASS,
    score: float = 0.85,
    confidence: float = 0.90,
    ring_scores: list | None = None,
    reason: str | None = None,
) -> ArbiterVerdict:
    """Factory for test verdicts."""
    if ring_scores is None:
        ring_scores = [
            RingScore(
                ring="ring1",
                score=0.90,
                decision="pass",
                confidence=0.85,
                provider="photint",
                model="phase_a+b",
                reason="PHOTINT A+B combined: A=0.88, B=0.92",
            ),
            RingScore(
                ring="ring2_primary",
                score=0.80,
                decision="pass",
                confidence=0.75,
                provider="anthropic",
                model="claude-haiku-4-5-20251001",
                reason="Task completion confirmed",
            ),
        ]
    return ArbiterVerdict(
        decision=decision,
        tier=ArbiterTier.STANDARD,
        aggregate_score=score,
        confidence=confidence,
        evidence_hash="0xabc123",
        commitment_hash="0xdef456",
        ring_scores=ring_scores,
        reason=reason,
        disagreement=False,
        cost_usd=0.001,
        latency_ms=1500,
    )


# ============================================================================
# Grade Assignment
# ============================================================================


class TestScoreToGrade:
    """Grade boundaries: A>=90, B>=80, C>=70, D>=60, F<60."""

    def test_grade_a(self):
        assert score_to_grade(0.95) == "A"
        assert score_to_grade(0.90) == "A"

    def test_grade_b(self):
        assert score_to_grade(0.89) == "B"
        assert score_to_grade(0.80) == "B"

    def test_grade_c(self):
        assert score_to_grade(0.79) == "C"
        assert score_to_grade(0.70) == "C"

    def test_grade_d(self):
        assert score_to_grade(0.69) == "D"
        assert score_to_grade(0.60) == "D"

    def test_grade_f(self):
        assert score_to_grade(0.59) == "F"
        assert score_to_grade(0.10) == "F"
        assert score_to_grade(0.0) == "F"

    def test_grade_perfect(self):
        assert score_to_grade(1.0) == "A"

    def test_grade_boundary_rounding(self):
        """0.895 rounds to 90 -> A."""
        assert score_to_grade(0.895) == "A"

    def test_grade_negative_clamps(self):
        """Negative scores should still produce F."""
        assert score_to_grade(-0.1) == "F"


class TestScoreToPct:
    def test_normal(self):
        assert score_to_pct(0.85) == 85

    def test_zero(self):
        assert score_to_pct(0.0) == 0

    def test_one(self):
        assert score_to_pct(1.0) == 100

    def test_clamp_above(self):
        assert score_to_pct(1.5) == 100

    def test_clamp_below(self):
        assert score_to_pct(-0.5) == 0

    def test_rounding(self):
        assert score_to_pct(0.855) == 86


# ============================================================================
# Pass Messages
# ============================================================================


class TestBuildPassMessage:
    def test_contains_score_and_grade(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.92)
        msg = build_pass_message(verdict)
        assert "Evidence Verified" in msg
        assert "Score: 92/100" in msg
        assert "Grade: A" in msg

    def test_contains_ok_prefixes(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.85)
        msg = build_pass_message(verdict)
        assert "OK" in msg

    def test_no_emojis(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS)
        msg = build_pass_message(verdict)
        # Check no common emoji codepoints
        for char in msg:
            assert ord(char) < 0x1F600 or ord(char) > 0x1F64F, (
                f"Found emoji {char!r} in message"
            )

    def test_within_char_limit(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS)
        msg = build_pass_message(verdict)
        assert len(msg) <= MAX_MESSAGE_LENGTH

    def test_ring_labels_present(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS)
        msg = build_pass_message(verdict)
        assert "PHOTINT" in msg


# ============================================================================
# Fail Messages
# ============================================================================


class TestBuildFailMessage:
    def test_contains_rejected_header(self):
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.25)
        msg = build_fail_message(verdict)
        assert "Evidence Rejected" in msg
        assert "Score: 25/100" in msg
        assert "Grade: F" in msg

    def test_contains_issues_section(self):
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.30)
        msg = build_fail_message(verdict)
        assert "Issues found:" in msg

    def test_contains_how_to_fix(self):
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.30)
        msg = build_fail_message(verdict)
        assert "How to fix:" in msg

    def test_fail_with_gps_issue_suggests_location_fix(self):
        ring_scores = [
            RingScore(
                ring="ring1",
                score=0.20,
                decision="fail",
                confidence=0.90,
                provider="photint",
                reason="GPS mismatch: photo taken 2.3km from task location",
            ),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.FAIL,
            score=0.20,
            ring_scores=ring_scores,
        )
        msg = build_fail_message(verdict)
        assert "location" in msg.lower()

    def test_fail_with_deadline_issue_suggests_timing_fix(self):
        ring_scores = [
            RingScore(
                ring="ring1",
                score=0.30,
                decision="fail",
                confidence=0.85,
                provider="photint",
                reason="Photo taken 3 hours after deadline",
            ),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.FAIL,
            score=0.30,
            ring_scores=ring_scores,
        )
        msg = build_fail_message(verdict)
        assert "deadline" in msg.lower()

    def test_no_emojis(self):
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.20)
        msg = build_fail_message(verdict)
        for char in msg:
            assert ord(char) < 0x1F600 or ord(char) > 0x1F64F

    def test_within_char_limit(self):
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.20)
        msg = build_fail_message(verdict)
        assert len(msg) <= MAX_MESSAGE_LENGTH


# ============================================================================
# Inconclusive Messages
# ============================================================================


class TestBuildInconclusiveMessage:
    def test_contains_under_review_header(self):
        verdict = _make_verdict(decision=ArbiterDecision.INCONCLUSIVE, score=0.55)
        msg = build_inconclusive_message(verdict)
        assert "Evidence Under Review" in msg
        assert "Score: 55/100" in msg

    def test_contains_manual_review_note(self):
        verdict = _make_verdict(decision=ArbiterDecision.INCONCLUSIVE, score=0.55)
        msg = build_inconclusive_message(verdict)
        assert "manual review" in msg.lower()

    def test_contains_partial_verification(self):
        verdict = _make_verdict(decision=ArbiterDecision.INCONCLUSIVE, score=0.55)
        msg = build_inconclusive_message(verdict)
        assert "Partial verification:" in msg

    def test_within_char_limit(self):
        verdict = _make_verdict(decision=ArbiterDecision.INCONCLUSIVE, score=0.55)
        msg = build_inconclusive_message(verdict)
        assert len(msg) <= MAX_MESSAGE_LENGTH


# ============================================================================
# Verdict Message Router
# ============================================================================


class TestBuildVerdictMessage:
    def test_routes_pass(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.92)
        msg = build_verdict_message(verdict)
        assert "Evidence Verified" in msg

    def test_routes_fail(self):
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.20)
        msg = build_verdict_message(verdict)
        assert "Evidence Rejected" in msg

    def test_routes_inconclusive(self):
        verdict = _make_verdict(decision=ArbiterDecision.INCONCLUSIVE, score=0.55)
        msg = build_verdict_message(verdict)
        assert "Evidence Under Review" in msg

    def test_routes_skipped(self):
        verdict = _make_verdict(decision=ArbiterDecision.SKIPPED, score=0.0)
        verdict.reason = "PHOTINT not available"
        msg = build_verdict_message(verdict)
        assert "Verification Skipped" in msg
        assert "PHOTINT not available" in msg


# ============================================================================
# Check Details Extraction
# ============================================================================


class TestExtractCheckDetails:
    def test_extracts_ring1_and_ring2(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.85)
        checks = _extract_check_details(verdict)
        assert len(checks) == 2
        assert checks[0]["ring"] == "ring1"
        assert checks[1]["ring"] == "ring2_primary"

    def test_pass_decision_maps_to_ok(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.85)
        checks = _extract_check_details(verdict)
        assert checks[0]["status"] == "OK"

    def test_fail_decision_maps_to_fail(self):
        ring_scores = [
            RingScore(ring="ring1", score=0.20, decision="fail", confidence=0.9),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.FAIL, score=0.20, ring_scores=ring_scores
        )
        checks = _extract_check_details(verdict)
        assert checks[0]["status"] == "FAIL"

    def test_inconclusive_maps_to_warn(self):
        ring_scores = [
            RingScore(
                ring="ring1", score=0.50, decision="inconclusive", confidence=0.5
            ),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.INCONCLUSIVE, score=0.50, ring_scores=ring_scores
        )
        checks = _extract_check_details(verdict)
        assert checks[0]["status"] == "WARN"

    def test_empty_ring_scores(self):
        verdict = _make_verdict(
            decision=ArbiterDecision.SKIPPED, score=0.0, ring_scores=[]
        )
        checks = _extract_check_details(verdict)
        assert checks == []


# ============================================================================
# Fix Suggestions
# ============================================================================


class TestFixSuggestions:
    def test_gps_related_fix(self):
        checks = [
            {"status": "FAIL", "detail": "GPS mismatch detected", "ring": "ring1"}
        ]
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.20)
        fixes = _generate_fix_suggestions(checks, verdict)
        assert any("location" in f.lower() for f in fixes)

    def test_deadline_related_fix(self):
        checks = [
            {"status": "FAIL", "detail": "Photo taken after deadline", "ring": "ring1"}
        ]
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.20)
        fixes = _generate_fix_suggestions(checks, verdict)
        assert any("deadline" in f.lower() for f in fixes)

    def test_tampering_related_fix(self):
        checks = [
            {"status": "FAIL", "detail": "Image tampering detected", "ring": "ring1"}
        ]
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.20)
        fixes = _generate_fix_suggestions(checks, verdict)
        assert any("original" in f.lower() or "unedited" in f.lower() for f in fixes)

    def test_generic_fallback_fix(self):
        checks = [
            {"status": "FAIL", "detail": "something unrecognized", "ring": "ring1"}
        ]
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.20)
        fixes = _generate_fix_suggestions(checks, verdict)
        assert len(fixes) >= 1

    def test_max_three_fixes(self):
        ring_scores = [
            RingScore(
                ring="ring1",
                score=0.10,
                decision="fail",
                confidence=0.9,
                reason="GPS mismatch detected",
            ),
            RingScore(
                ring="ring2_primary",
                score=0.10,
                decision="fail",
                confidence=0.8,
                reason="Photo taken after deadline expired",
            ),
            RingScore(
                ring="ring2_secondary",
                score=0.10,
                decision="fail",
                confidence=0.7,
                reason="Image tampering detected in metadata",
            ),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.FAIL, score=0.10, ring_scores=ring_scores
        )
        msg = build_fail_message(verdict)
        # Count "How to fix" numbered items (at most 3)
        fix_lines = [
            line
            for line in msg.split("\n")
            if line.strip().startswith(("1.", "2.", "3.", "4."))
        ]
        assert len(fix_lines) <= 3


# ============================================================================
# Scoring Fields Extraction (for API response)
# ============================================================================


class TestExtractScoringFields:
    def test_returns_grade(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.92)
        fields = extract_scoring_fields(verdict)
        assert fields["grade"] == "A"

    def test_returns_authenticity_score(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.85)
        fields = extract_scoring_fields(verdict)
        assert fields["authenticity_score"] == 0.90

    def test_returns_completion_score(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.85)
        fields = extract_scoring_fields(verdict)
        assert fields["completion_score"] == 0.80

    def test_returns_summary(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.85)
        fields = extract_scoring_fields(verdict)
        assert "Evidence Verified" in fields["summary"]

    def test_returns_check_details(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.85)
        fields = extract_scoring_fields(verdict)
        assert len(fields["check_details"]) == 2

    def test_no_ring2_returns_none_completion(self):
        ring_scores = [
            RingScore(ring="ring1", score=0.85, decision="pass", confidence=0.9),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.PASS, score=0.85, ring_scores=ring_scores
        )
        fields = extract_scoring_fields(verdict)
        assert fields["authenticity_score"] == 0.85
        assert fields["completion_score"] is None

    def test_multiple_ring2_averages(self):
        ring_scores = [
            RingScore(ring="ring1", score=0.90, decision="pass", confidence=0.9),
            RingScore(
                ring="ring2_primary", score=0.80, decision="pass", confidence=0.8
            ),
            RingScore(
                ring="ring2_secondary", score=0.70, decision="pass", confidence=0.7
            ),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.PASS, score=0.80, ring_scores=ring_scores
        )
        fields = extract_scoring_fields(verdict)
        assert fields["completion_score"] == 0.75  # avg(0.80, 0.70)

    def test_empty_ring_scores(self):
        verdict = _make_verdict(
            decision=ArbiterDecision.SKIPPED, score=0.0, ring_scores=[]
        )
        fields = extract_scoring_fields(verdict)
        assert fields["authenticity_score"] is None
        assert fields["completion_score"] is None
        assert fields["grade"] == "F"


# ============================================================================
# Character Limit (mobile display)
# ============================================================================


class TestCharacterLimit:
    def test_pass_message_limit(self):
        verdict = _make_verdict(decision=ArbiterDecision.PASS, score=0.92)
        msg = build_pass_message(verdict)
        assert len(msg) <= MAX_MESSAGE_LENGTH

    def test_fail_message_limit(self):
        verdict = _make_verdict(decision=ArbiterDecision.FAIL, score=0.15)
        msg = build_fail_message(verdict)
        assert len(msg) <= MAX_MESSAGE_LENGTH

    def test_inconclusive_message_limit(self):
        verdict = _make_verdict(decision=ArbiterDecision.INCONCLUSIVE, score=0.55)
        msg = build_inconclusive_message(verdict)
        assert len(msg) <= MAX_MESSAGE_LENGTH

    def test_very_long_ring_reasons_truncated(self):
        """Even with very long reasons, message stays under limit."""
        long_reason = "x" * 200
        ring_scores = [
            RingScore(
                ring="ring1",
                score=0.15,
                decision="fail",
                confidence=0.9,
                reason=long_reason,
            ),
            RingScore(
                ring="ring2_primary",
                score=0.10,
                decision="fail",
                confidence=0.8,
                reason=long_reason,
            ),
            RingScore(
                ring="ring2_secondary",
                score=0.12,
                decision="fail",
                confidence=0.7,
                reason=long_reason,
            ),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.FAIL,
            score=0.12,
            ring_scores=ring_scores,
        )
        msg = build_fail_message(verdict)
        assert len(msg) <= MAX_MESSAGE_LENGTH


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    def test_verdict_with_no_ring_scores(self):
        verdict = _make_verdict(
            decision=ArbiterDecision.PASS, score=0.85, ring_scores=[]
        )
        msg = build_pass_message(verdict)
        assert "Evidence Verified" in msg
        assert len(msg) <= MAX_MESSAGE_LENGTH

    def test_verdict_with_none_reason_on_ring(self):
        ring_scores = [
            RingScore(ring="ring1", score=0.85, decision="pass", confidence=0.9),
        ]
        verdict = _make_verdict(
            decision=ArbiterDecision.PASS, score=0.85, ring_scores=ring_scores
        )
        msg = build_pass_message(verdict)
        assert "Evidence Verified" in msg

    def test_zero_score_verdict(self):
        verdict = _make_verdict(
            decision=ArbiterDecision.FAIL, score=0.0, ring_scores=[]
        )
        msg = build_fail_message(verdict)
        assert "Score: 0/100" in msg
        assert "Grade: F" in msg

    def test_perfect_score_verdict(self):
        verdict = _make_verdict(
            decision=ArbiterDecision.PASS, score=1.0, ring_scores=[]
        )
        msg = build_pass_message(verdict)
        assert "Score: 100/100" in msg
        assert "Grade: A" in msg
