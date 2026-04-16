"""Dynamic reputation scoring engine for ERC-8004 feedback.

Replaces hardcoded score 80 with multi-dimensional scoring based on
submission quality signals.

Weight design (v2, 2026-04-14):
  AI_VERIFICATION: 45 pts — primary quality signal (arbiter > ring1 > pre_check)
  SPEED:           20 pts — delivery promptness
  EVIDENCE:        20 pts — completeness of submitted evidence
  FORENSIC:        15 pts — metadata richness (GPS, timestamps, device)
  Total:          100 pts

Minimum floor: approved tasks always score ≥ 75.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring dimension weights (must sum to 100)
# ---------------------------------------------------------------------------
SPEED_MAX = 20  # Reduced: short-deadline tasks shouldn't be penalised
EVIDENCE_MAX = 20  # Reduced: evidence dict format now handled correctly
AI_VERIFICATION_MAX = 45  # Increased: arbiter + ring1 are the primary quality signal
FORENSIC_MAX = 15  # Unchanged: GPS, timestamps, device

# Neutral defaults used when data for a dimension is unavailable.
SPEED_NEUTRAL = 13
EVIDENCE_NEUTRAL = 14
AI_NEUTRAL = 27  # ~60 % of max: moderate quality assumed when no signal
FORENSIC_NEUTRAL = 10

# Minimum reputation score for any APPROVED/COMPLETED task.
# A task the agent chose to approve and pay must always reflect at least this.
APPROVED_FLOOR = 75


def _parse_iso(value: Union[str, datetime, None]) -> datetime | None:
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
        return round(SPEED_MAX * 0.85)
    if ratio <= 0.75:
        return round(SPEED_MAX * 0.70)
    if ratio <= 1.0:
        return round(SPEED_MAX * 0.55)  # Near deadline — still valid
    # Late delivery
    return round(SPEED_MAX * 0.20)


def _score_evidence(task: dict[str, Any], submission: dict[str, Any]) -> int | None:
    """Score 0..EVIDENCE_MAX based on evidence completeness."""
    evidence_urls = submission.get("evidence_urls")

    # Support the nested evidence dict format: {type: {fileUrl, ...}}
    if not isinstance(evidence_urls, list):
        evidence_dict = submission.get("evidence")
        if isinstance(evidence_dict, dict) and evidence_dict:
            evidence_urls = [
                (v.get("fileUrl") or v) if isinstance(v, dict) else v
                for v in evidence_dict.values()
                if v
            ]

    if not isinstance(evidence_urls, list) or len(evidence_urls) == 0:
        return None

    submitted_count = len(evidence_urls)

    requirements = task.get("evidence_requirements")
    if isinstance(requirements, list) and len(requirements) > 0:
        required_count = len(requirements)
        ratio = submitted_count / required_count
    else:
        # No explicit requirements; 1 item = 50 %, 2+ items = 100 %+
        ratio = min(submitted_count / 2, 1.5)

    if ratio >= 1.5:
        return EVIDENCE_MAX  # Exceeded expectations
    if ratio >= 1.0:
        return round(EVIDENCE_MAX * 0.85)  # Met all
    if ratio >= 0.5:
        return round(EVIDENCE_MAX * ratio)  # Proportional
    return round(EVIDENCE_MAX * 0.2)  # Minimal evidence


def _score_ai_verification(submission: dict[str, Any]) -> int | None:
    """Score 0..AI_VERIFICATION_MAX from AI/arbiter verification results.

    Priority (highest → lowest):
      1. Ring 2 Arbiter aggregate_score (0–1 float, most authoritative)
      2. Ring 1 PHOTINT auto_check_details.score (0–1 float)
      3. pre_check_score top-level field (0–1 float)
      4. ai_verification_score direct field (0–100)
      5. ai_verification_result dict (auto-detects 0–1 or 0–100 range)
    """
    # Priority 1: Ring 2 Arbiter verdict (aggregate_score is 0–1)
    arbiter = submission.get("arbiter_verdict_data")
    if isinstance(arbiter, dict):
        agg = arbiter.get("aggregate_score")
        if isinstance(agg, (int, float)) and 0.0 <= agg <= 1.0:
            return round(AI_VERIFICATION_MAX * agg)

    # Priority 2: Ring 1 PHOTINT auto_check_details.score (0–1)
    auto_check = submission.get("auto_check_details")
    if isinstance(auto_check, dict):
        auto_score = auto_check.get("score")
        if isinstance(auto_score, (int, float)) and 0.0 <= auto_score <= 1.0:
            return round(AI_VERIFICATION_MAX * auto_score)

    # Priority 3: pre_check_score top-level (0–1 float from DB)
    pre_check = submission.get("pre_check_score")
    if isinstance(pre_check, (int, float)) and 0.0 <= pre_check <= 1.0:
        return round(AI_VERIFICATION_MAX * pre_check)

    # Priority 4: direct ai_verification_score (0–100)
    ai_score = submission.get("ai_verification_score")
    if isinstance(ai_score, (int, float)) and 0 <= ai_score <= 100:
        return round(AI_VERIFICATION_MAX * ai_score / 100)

    # Priority 5: ai_verification_result dict (detect scale)
    ai_result = submission.get("ai_verification_result")
    if isinstance(ai_result, dict):
        score_val = ai_result.get("score") or ai_result.get("confidence")
        if isinstance(score_val, (int, float)):
            if 0.0 < score_val <= 1.0:
                # 0–1 float scale
                return round(AI_VERIFICATION_MAX * score_val)
            if 1.0 < score_val <= 100:
                # 0–100 int scale
                return round(AI_VERIFICATION_MAX * score_val / 100)
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

    # GPS — check top-level and evidence.screenshot.metadata.forensic.gps
    has_gps = (
        submission.get("gps_latitude")
        or submission.get("gps_longitude")
        or submission.get("location")
    )
    if not has_gps:
        # Try nested evidence format
        evidence = submission.get("evidence") or {}
        for ev in evidence.values() if isinstance(evidence, dict) else []:
            if isinstance(ev, dict):
                forensic = (ev.get("metadata") or {}).get("forensic") or {}
                gps = forensic.get("gps") or {}
                if gps.get("latitude") or gps.get("longitude"):
                    has_gps = True
                    break
    if has_gps:
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
        if signals < 2:
            signals += 1

    # Device info — check top-level and nested forensic
    has_device = bool(
        metadata.get("device")
        or metadata.get("user_agent")
        or metadata.get("device_info")
    )
    if not has_device:
        evidence = submission.get("evidence") or {}
        for ev in evidence.values() if isinstance(evidence, dict) else []:
            if isinstance(ev, dict):
                forensic = (ev.get("metadata") or {}).get("forensic") or {}
                if forensic.get("device"):
                    has_device = True
                    break
    if has_device:
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

    # 4. Minimum floor for approved tasks.
    # A task the agent approved and paid must always earn at least APPROVED_FLOOR.
    # This ensures reputation is coherent with the verification pipeline decision.
    task_status = str(task.get("status", "")).lower()
    submission_status = str(submission.get("status", "")).lower()
    is_approved = task_status == "completed" or submission_status in {
        "approved",
        "verifying",
    }
    if is_approved:
        clamped = max(APPROVED_FLOOR, clamped)

    breakdown["computed"] = dict(computed)
    breakdown["raw_total"] = total
    breakdown["approved_floor_applied"] = is_approved and total < APPROVED_FLOOR

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
