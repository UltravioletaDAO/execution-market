"""Dynamic reputation scoring engine for ERC-8004 feedback.

Replaces hardcoded score 80 with multi-dimensional scoring based on
submission quality signals.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring dimension weights (must sum to 100)
# ---------------------------------------------------------------------------
SPEED_MAX = 30
EVIDENCE_MAX = 30
AI_VERIFICATION_MAX = 25
FORENSIC_MAX = 15

# Neutral defaults used when data for a dimension is unavailable.
SPEED_NEUTRAL = 20
EVIDENCE_NEUTRAL = 20
AI_NEUTRAL = 15
FORENSIC_NEUTRAL = 8


def _parse_iso(value: Any) -> datetime | None:
    """Best-effort parse of an ISO-8601 string into a tz-aware datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        # Python 3.11+ fromisoformat handles Z suffix
        text = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Per-dimension scorers
# ---------------------------------------------------------------------------


def _score_speed(task: dict[str, Any], submission: dict[str, Any]) -> int | None:
    """Score 0..SPEED_MAX based on how quickly the worker delivered."""
    task_created = _parse_iso(task.get("created_at"))
    deadline = _parse_iso(task.get("deadline"))
    submitted = _parse_iso(submission.get("created_at"))

    if not task_created or not deadline or not submitted:
        return None

    total_window = (deadline - task_created).total_seconds()
    if total_window <= 0:
        return None

    elapsed = (submitted - task_created).total_seconds()
    ratio = elapsed / total_window  # 0 = instant, 1 = at deadline, >1 = late

    if ratio <= 0.25:
        return SPEED_MAX  # Very fast
    if ratio <= 0.50:
        return round(SPEED_MAX * 0.85)  # ~26
    if ratio <= 0.75:
        return round(SPEED_MAX * 0.70)  # ~21
    if ratio <= 1.0:
        return round(SPEED_MAX * 0.55)  # ~17
    # Late delivery
    return round(SPEED_MAX * 0.17)  # ~5


def _score_evidence(task: dict[str, Any], submission: dict[str, Any]) -> int | None:
    """Score 0..EVIDENCE_MAX based on evidence completeness."""
    evidence_urls = submission.get("evidence_urls")
    if not isinstance(evidence_urls, list):
        return None

    submitted_count = len(evidence_urls)
    if submitted_count == 0:
        return None

    requirements = task.get("evidence_requirements")
    if isinstance(requirements, list) and len(requirements) > 0:
        required_count = len(requirements)
        ratio = submitted_count / required_count
    else:
        # No explicit requirements; any evidence is positive
        ratio = min(submitted_count / 2, 1.5)  # 2 items = 100%, extras count

    if ratio >= 1.5:
        return EVIDENCE_MAX  # Exceeded expectations
    if ratio >= 1.0:
        return round(EVIDENCE_MAX * 0.85)  # Met all
    if ratio >= 0.5:
        return round(EVIDENCE_MAX * ratio)  # Proportional
    return round(EVIDENCE_MAX * 0.2)  # Minimal evidence


def _score_ai_verification(submission: dict[str, Any]) -> int | None:
    """Score 0..AI_VERIFICATION_MAX from AI verification results."""
    # Direct numeric score (0-100 range)
    ai_score = submission.get("ai_verification_score")
    if isinstance(ai_score, (int, float)) and 0 <= ai_score <= 100:
        return round(AI_VERIFICATION_MAX * ai_score / 100)

    # Structured result
    ai_result = submission.get("ai_verification_result")
    if isinstance(ai_result, dict):
        score_val = ai_result.get("score") or ai_result.get("confidence")
        if isinstance(score_val, (int, float)) and 0 <= score_val <= 100:
            return round(AI_VERIFICATION_MAX * score_val / 100)
        # Boolean pass/fail
        passed = ai_result.get("passed")
        if passed is None:
            passed = ai_result.get("verified")
        if isinstance(passed, bool):
            return AI_VERIFICATION_MAX if passed else round(AI_VERIFICATION_MAX * 0.2)

    return None


def _score_forensic(submission: dict[str, Any]) -> int | None:
    """Score 0..FORENSIC_MAX from metadata richness (GPS, EXIF, device)."""
    signals = 0
    total_possible = 3  # GPS, timestamps/EXIF, device info

    # GPS
    if submission.get("gps_latitude") or submission.get("gps_longitude"):
        signals += 1
    elif submission.get("location"):
        signals += 1

    # Timestamps / EXIF
    metadata = submission.get("metadata") or {}
    if isinstance(metadata, dict):
        if (
            metadata.get("exif")
            or metadata.get("timestamp")
            or metadata.get("taken_at")
        ):
            signals += 1
    if submission.get("submitted_at") and submission.get("created_at"):
        # Has both timestamps (can verify timing)
        if signals < 2:
            signals += 1

    # Device info
    if (
        metadata.get("device")
        or metadata.get("user_agent")
        or metadata.get("device_info")
    ):
        signals += 1

    if signals == 0:
        return None

    return round(FORENSIC_MAX * signals / total_possible)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_dynamic_score(
    task: dict[str, Any],
    submission: dict[str, Any],
    executor: dict[str, Any],
    override_score: int | None = None,
) -> dict[str, Any]:
    """Calculate reputation score from submission quality signals.

    Returns dict with:
        score: int (0-100)
        source: str ('override' | 'dynamic' | 'fallback')
        breakdown: dict with per-dimension scores and notes
    """
    # 1. Agent override takes precedence
    if override_score is not None:
        clamped = max(0, min(100, override_score))
        return {
            "score": clamped,
            "source": "override",
            "breakdown": {"override": clamped},
        }

    # 2. Compute each dimension
    speed = _score_speed(task, submission)
    evidence = _score_evidence(task, submission)
    ai = _score_ai_verification(submission)
    forensic = _score_forensic(submission)

    breakdown: dict[str, Any] = {
        "speed": speed,
        "evidence": evidence,
        "ai_verification": ai,
        "forensic": forensic,
    }

    # 3. Determine source and fill neutrals
    computed = {
        "speed": speed if speed is not None else SPEED_NEUTRAL,
        "evidence": evidence if evidence is not None else EVIDENCE_NEUTRAL,
        "ai_verification": ai if ai is not None else AI_NEUTRAL,
        "forensic": forensic if forensic is not None else FORENSIC_NEUTRAL,
    }

    has_any_real = any(v is not None for v in [speed, evidence, ai, forensic])
    source = "dynamic" if has_any_real else "fallback"

    total = sum(computed.values())
    clamped = max(0, min(100, total))

    breakdown["computed"] = dict(computed)
    breakdown["raw_total"] = total

    logger.debug(
        "Dynamic score for submission: source=%s, score=%d, breakdown=%s",
        source,
        clamped,
        breakdown,
    )

    return {
        "score": clamped,
        "source": source,
        "breakdown": breakdown,
    }
