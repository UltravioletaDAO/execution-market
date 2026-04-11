"""
Verdict Message Builder -- Human-readable verdict summaries.

Translates an ArbiterVerdict into clear, actionable messages for workers
and agents. Three variants: pass, fail, inconclusive.

Design constraints:
- NO emojis (encoding issues in CloudWatch, mobile rendering)
- Use OK / FAIL / WARN prefixes for scan-ability
- Include numeric score AND letter grade
- Keep under 500 chars for mobile display
- Include actionable "How to fix" for rejections
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .types import ArbiterVerdict


# ---------------------------------------------------------------------------
# Grade assignment
# ---------------------------------------------------------------------------

_GRADE_BOUNDARIES = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
]


def score_to_grade(score_0_to_1: float) -> str:
    """Convert a 0.0-1.0 score to a letter grade (A/B/C/D/F).

    A: >= 90  |  B: >= 80  |  C: >= 70  |  D: >= 60  |  F: < 60
    """
    pct = int(round(score_0_to_1 * 100))
    for threshold, grade in _GRADE_BOUNDARIES:
        if pct >= threshold:
            return grade
    return "F"


def score_to_pct(score_0_to_1: float) -> int:
    """Convert a 0.0-1.0 score to an integer percentage (0-100)."""
    return max(0, min(100, int(round(score_0_to_1 * 100))))


# ---------------------------------------------------------------------------
# Check detail extraction from ring scores
# ---------------------------------------------------------------------------


def _extract_check_details(verdict: ArbiterVerdict) -> List[Dict[str, Any]]:
    """Extract individual check results from ring scores.

    Returns a list of dicts with keys: status, label, detail.
    status is one of "OK", "FAIL", "WARN".
    """
    checks: List[Dict[str, Any]] = []

    for rs in verdict.ring_scores:
        if rs.decision == "pass":
            status = "OK"
        elif rs.decision == "fail":
            status = "FAIL"
        else:
            status = "WARN"

        label = _ring_label(rs.ring)
        detail = rs.reason or f"Score: {score_to_pct(rs.score)}/100"

        checks.append(
            {
                "status": status,
                "label": label,
                "detail": detail,
                "ring": rs.ring,
                "score": round(float(rs.score), 4),
            }
        )

    return checks


def _ring_label(ring: str) -> str:
    """Human-readable label for a ring identifier."""
    labels = {
        "ring1": "PHOTINT (authenticity)",
        "ring2_primary": "Semantic check (primary)",
        "ring2_secondary": "Semantic check (secondary)",
        "ring2_a": "Semantic check A",
        "ring2_b": "Semantic check B",
    }
    return labels.get(ring, ring)


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

# Maximum message length for mobile display
MAX_MESSAGE_LENGTH = 500


def build_verdict_message(verdict: ArbiterVerdict) -> str:
    """Build a clear, human-readable verdict message.

    Routes to the appropriate sub-builder based on the verdict decision.
    """
    from .types import ArbiterDecision

    if verdict.decision == ArbiterDecision.PASS:
        return build_pass_message(verdict)
    elif verdict.decision == ArbiterDecision.FAIL:
        return build_fail_message(verdict)
    elif verdict.decision == ArbiterDecision.INCONCLUSIVE:
        return build_inconclusive_message(verdict)
    elif verdict.decision == ArbiterDecision.SKIPPED:
        return _build_skipped_message(verdict)
    else:
        pct = score_to_pct(verdict.aggregate_score)
        grade = score_to_grade(verdict.aggregate_score)
        return f"Evidence Review (Score: {pct}/100, Grade: {grade})"


def build_pass_message(verdict: ArbiterVerdict) -> str:
    """Build message for a PASS verdict.

    Example output:

    Evidence Verified (Score: 92/100, Grade: A)

      OK  PHOTINT (authenticity): score 95/100
      OK  Semantic check (primary): score 87/100
    """
    pct = score_to_pct(verdict.aggregate_score)
    grade = score_to_grade(verdict.aggregate_score)
    checks = _extract_check_details(verdict)

    lines = [f"Evidence Verified (Score: {pct}/100, Grade: {grade})"]
    lines.append("")

    for c in checks:
        line = f"  {c['status']}  {c['label']}: {_short_detail(c)}"
        lines.append(line)

    msg = "\n".join(lines)
    return _truncate(msg)


def build_fail_message(verdict: ArbiterVerdict) -> str:
    """Build message for a FAIL verdict.

    Example output:

    Evidence Rejected (Score: 34/100, Grade: F)

    Issues found:
      FAIL  PHOTINT (authenticity): GPS mismatch detected
      WARN  Semantic check (primary): cannot confirm completion

    How to fix:
      1. Take the photo at the exact task location
      2. Submit before the deadline
    """
    pct = score_to_pct(verdict.aggregate_score)
    grade = score_to_grade(verdict.aggregate_score)
    checks = _extract_check_details(verdict)

    lines = [f"Evidence Rejected (Score: {pct}/100, Grade: {grade})"]
    lines.append("")
    lines.append("Issues found:")

    for c in checks:
        line = f"  {c['status']}  {c['label']}: {_short_detail(c)}"
        lines.append(line)

    # Generate fix suggestions from failed checks
    fixes = _generate_fix_suggestions(checks, verdict)
    if fixes:
        lines.append("")
        lines.append("How to fix:")
        for i, fix in enumerate(fixes[:3], 1):
            lines.append(f"  {i}. {fix}")

    msg = "\n".join(lines)
    return _truncate(msg)


def build_inconclusive_message(verdict: ArbiterVerdict) -> str:
    """Build message for an INCONCLUSIVE verdict.

    Example output:

    Evidence Under Review (Score: 55/100, Grade: C)

    Partial verification:
      OK  PHOTINT (authenticity): score 72/100
      WARN  Semantic check (primary): cannot determine completion

    This submission has been queued for manual review.
    """
    pct = score_to_pct(verdict.aggregate_score)
    grade = score_to_grade(verdict.aggregate_score)
    checks = _extract_check_details(verdict)

    lines = [f"Evidence Under Review (Score: {pct}/100, Grade: {grade})"]
    lines.append("")
    lines.append("Partial verification:")

    for c in checks:
        line = f"  {c['status']}  {c['label']}: {_short_detail(c)}"
        lines.append(line)

    lines.append("")
    lines.append("This submission has been queued for manual review.")

    msg = "\n".join(lines)
    return _truncate(msg)


def _build_skipped_message(verdict: ArbiterVerdict) -> str:
    """Build message for a SKIPPED verdict (arbiter did not run)."""
    reason = verdict.reason or "Arbiter evaluation was not performed"
    return f"Verification Skipped: {reason}"


# ---------------------------------------------------------------------------
# Fix suggestion generation
# ---------------------------------------------------------------------------


def _generate_fix_suggestions(
    checks: List[Dict[str, Any]],
    verdict: ArbiterVerdict,
) -> List[str]:
    """Generate actionable fix suggestions from failed/warning checks.

    Returns a list of short, actionable sentences.
    """
    suggestions: List[str] = []

    for c in checks:
        if c["status"] == "FAIL":
            suggestion = _suggest_fix_for_check(c)
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)

    # If no specific suggestions, provide a generic one
    if not suggestions:
        for c in checks:
            if c["status"] == "WARN":
                suggestion = _suggest_fix_for_check(c)
                if suggestion and suggestion not in suggestions:
                    suggestions.append(suggestion)

    if not suggestions:
        suggestions.append(
            "Review the task requirements and resubmit with clearer evidence"
        )

    return suggestions


def _suggest_fix_for_check(check: Dict[str, Any]) -> Optional[str]:
    """Generate a fix suggestion for a single failed check."""
    detail_lower = check.get("detail", "").lower()
    ring = check.get("ring", "")

    # GPS-related
    if (
        "gps" in detail_lower
        or "location" in detail_lower
        or "distance" in detail_lower
    ):
        return "Take the photo at the exact task location"

    # Time-related
    if "time" in detail_lower or "deadline" in detail_lower or "late" in detail_lower:
        return "Submit before the deadline"

    # Tampering / authenticity
    if (
        "tamper" in detail_lower
        or "manipulat" in detail_lower
        or "fake" in detail_lower
    ):
        return "Submit unedited, original photos without filters or modifications"

    # Low confidence / unclear
    if (
        "cannot" in detail_lower
        or "unclear" in detail_lower
        or "confidence" in detail_lower
    ):
        return "Capture the subject clearly from a closer angle"

    # Generic ring-specific
    if ring.startswith("ring1"):
        return "Ensure photo metadata (EXIF, GPS, timestamp) is preserved"
    elif ring.startswith("ring2"):
        return "Make sure the evidence clearly shows task completion"

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _short_detail(check: Dict[str, Any]) -> str:
    """Produce a short detail string for a check result."""
    detail = check.get("detail", "")
    # If the detail is just a score reference, format as percentage
    if detail.startswith("Score:"):
        return detail.lower()
    # Truncate long details
    if len(detail) > 80:
        return detail[:77] + "..."
    return detail


def _truncate(msg: str, limit: int = MAX_MESSAGE_LENGTH) -> str:
    """Truncate message to fit mobile display limit."""
    if len(msg) <= limit:
        return msg
    return msg[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# Convenience: extract structured scoring data from verdict
# ---------------------------------------------------------------------------


def extract_scoring_fields(verdict: ArbiterVerdict) -> Dict[str, Any]:
    """Extract unified scoring fields from an ArbiterVerdict.

    Returns a dict suitable for enriching API responses:
        grade: str          "A" | "B" | "C" | "D" | "F"
        authenticity_score: float | None   Ring 1 score (0-1)
        completion_score: float | None     Ring 2 avg score (0-1)
        summary: str                       Human-readable message
        check_details: list[dict]          Per-check results
    """
    grade = score_to_grade(verdict.aggregate_score)
    summary = build_verdict_message(verdict)
    check_details = _extract_check_details(verdict)

    # Split Ring 1 (authenticity) vs Ring 2 (completion) scores
    authenticity_score: Optional[float] = None
    completion_scores: List[float] = []

    for rs in verdict.ring_scores:
        if rs.ring == "ring1":
            authenticity_score = round(float(rs.score), 4)
        elif rs.ring.startswith("ring2"):
            completion_scores.append(float(rs.score))

    completion_score: Optional[float] = None
    if completion_scores:
        completion_score = round(sum(completion_scores) / len(completion_scores), 4)

    return {
        "grade": grade,
        "authenticity_score": authenticity_score,
        "completion_score": completion_score,
        "summary": summary,
        "check_details": check_details,
    }
