"""
L2 Escalation — INCONCLUSIVE verdicts go to human arbiters.

When the dual-ring consensus produces an INCONCLUSIVE verdict (rings disagree
or scores fall in the middle band), this module creates a `disputes` row that
human arbiters can pick up and resolve.

The disputes table was created in migration 004 with full support for:
- Multi-arbitrator voting (arbitrators table, arbitration_votes table)
- 3-arbitrator quorum with escalate_to_arbitration() function
- Resolution split (agent/executor/split percentage)
- Timeline + audit trail

Phase 1 of arbiter integration: minimal escalation -- creates dispute row,
populates arbiter_verdict_data, sets escalation_tier=2.

Phase 5 of arbiter master plan: wires this to the existing arbitrator pool
+ MCP tools for resolution.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from .config import get_escalation_settings
from .types import ArbiterVerdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def escalate_to_human(
    verdict: ArbiterVerdict,
    task: Dict[str, Any],
    submission: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Create a dispute row for L2 human arbiter review.

    Phase 1 implementation: creates the dispute, sets metadata, returns it.
    Notification + arbiter assignment lives in Phase 5.

    Args:
        verdict: The INCONCLUSIVE verdict that triggered escalation
        task: Task row from DB
        submission: Submission row from DB

    Returns:
        The created dispute row, or None on failure.
    """
    submission_id = submission.get("id", "")
    task_id = task.get("id", "")
    agent_id = task.get("agent_id", "")
    executor_id = (submission.get("executor") or {}).get("id")

    if not task_id or not submission_id:
        logger.error(
            "escalate_to_human: missing task_id or submission_id (task=%s sub=%s)",
            task_id,
            submission_id,
        )
        return None

    settings = await get_escalation_settings()
    timeout_hours = settings.get("timeout_hours", 24)

    # Map arbiter verdict reason to dispute reason enum from mig 004
    # Valid values: incomplete_work, poor_quality, wrong_deliverable, late_delivery,
    #               fake_evidence, no_response, payment_issue, unfair_rejection, other
    dispute_reason = _infer_dispute_reason(verdict)

    description = (
        f"Auto-escalated by Ring 2 arbiter. Verdict: INCONCLUSIVE "
        f"(score={verdict.aggregate_score:.3f}, confidence={verdict.confidence:.3f}, "
        f"tier={verdict.tier.value}). Reason: {verdict.reason or 'mid-band score'}"
    )

    if verdict.disagreement:
        description += " [ring disagreement detected]"

    try:
        import supabase_client as db

        client = db.get_client()

        dispute_row = {
            "task_id": task_id,
            "submission_id": submission_id,
            "agent_id": agent_id,
            "executor_id": executor_id,
            "reason": dispute_reason,
            "description": description,
            "status": "open",
            "priority": _compute_priority(task, verdict),
            "disputed_amount_usdc": float(task.get("bounty_usd", 0) or 0),
            # Migration 091 columns
            "escalation_tier": 2,
            "arbiter_verdict_data": verdict.to_dict(),
            # Set explicit deadline for L2 review
            "response_deadline": (
                datetime.now(timezone.utc) + timedelta(hours=timeout_hours)
            ).isoformat(),
            # Stored in metadata for forward-compat
            "metadata": {
                "source": "arbiter_auto_escalation",
                "ring2_disagreement": verdict.disagreement,
                "evidence_hash": verdict.evidence_hash,
                "commitment_hash": verdict.commitment_hash,
                "escalated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        result = client.table("disputes").insert(dispute_row).execute()

        if result.data and len(result.data) > 0:
            dispute = result.data[0]
            logger.info(
                "Created L2 dispute %s for submission %s (timeout %dh)",
                dispute.get("id"),
                submission_id,
                timeout_hours,
            )

            # INC-2026-04-22: Do NOT mutate agent_verdict here -- that column
            # belongs to the publisher's decision. Only update agent_notes for
            # visibility. Setting agent_verdict="disputed" locked publishers
            # out of /approve with HTTP 409 and required service-role patches.
            try:
                client.table("submissions").update(
                    {
                        "agent_notes": (
                            f"Dispute opened (id={dispute.get('id')}). "
                            f"Ring 2 verdict: {verdict.decision.value}."
                        ),
                    }
                ).eq("id", submission_id).execute()
            except Exception as e:
                logger.warning(
                    "Failed to annotate submission %s after dispute creation: %s",
                    submission_id,
                    e,
                )

            return dispute
        else:
            logger.error(
                "Failed to insert dispute row for submission %s -- empty result",
                submission_id,
            )
            return None
    except Exception as e:
        logger.exception(
            "Exception creating dispute for submission %s: %s", submission_id, e
        )
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_dispute_reason(verdict: ArbiterVerdict) -> str:
    """Map an arbiter verdict to a `dispute_reason` enum value from mig 004.

    Heuristic: if the score is in the middle (uncertainty), use 'poor_quality'.
    If the rings strongly disagreed, use 'fake_evidence' (conservative).
    Otherwise default to 'other'.
    """
    if verdict.disagreement and verdict.aggregate_score < 0.5:
        return "fake_evidence"
    if verdict.aggregate_score < 0.5:
        return "poor_quality"
    return "other"


def _compute_priority(task: Dict[str, Any], verdict: ArbiterVerdict) -> int:
    """Higher bounty + higher disagreement = higher priority (1-10).

    The disputes table priority column accepts 1-10. Defaults to 5.
    """
    base = 5
    bounty = float(task.get("bounty_usd", 0) or 0)

    # Boost priority for high-bounty tasks
    if bounty >= 10:
        base += 3
    elif bounty >= 1:
        base += 1

    # Boost priority for ring disagreement (more uncertain -> needs faster review)
    if verdict.disagreement:
        base += 1

    return min(10, max(1, base))
