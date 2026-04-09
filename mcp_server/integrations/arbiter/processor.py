"""
Arbiter Verdict Processor — Phase 2 dispatch layer.

Translates an ArbiterVerdict into actual payment actions:
- PASS  -> trigger Facilitator /settle (release worker payment)
- FAIL  -> trigger Facilitator /refund (refund agent)
- INCONCLUSIVE -> escalate to L2 human arbiter (escalation.py)
- SKIPPED -> no-op, log only

This is the bridge between Ring 2 (off-chain decision) and the on-chain
payment flow. It NEVER signs anything itself -- it always delegates to
the existing PaymentDispatcher / _settle_submission_payment paths which
ultimately call the Facilitator HTTP API.

Idempotency: relies on _settle_submission_payment's existing idempotency
check (line 1266 of _helpers.py). Multiple calls with the same submission_id
are safe -- only the first one moves funds.

Architecture:
    background_runner.py
        |
        | (after Phase B)
        v
    ArbiterService.evaluate(task, submission)  ----> ArbiterVerdict
        |
        v
    process_arbiter_verdict(verdict, task, submission)  <-- THIS FILE
        |
        +--> PASS (auto):    _settle_submission_payment() -> Facilitator /settle
        +--> PASS (hybrid):  store verdict, notify agent, wait
        +--> FAIL (auto):    dispatcher.refund_trustless_escrow() -> Facilitator /refund
        +--> FAIL (hybrid):  store verdict, notify agent, wait
        +--> INCONCLUSIVE:   escalation_manager.escalate() -> create dispute row
        +--> SKIPPED:        no-op, log
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import resolve_arbiter_mode
from .types import ArbiterDecision, ArbiterVerdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Process result (returned to caller for logging/observability)
# ---------------------------------------------------------------------------


class ProcessResult:
    """Outcome of process_arbiter_verdict.

    Lightweight wrapper -- not a dataclass to avoid Pydantic-style imports.
    Convertible to dict for logging.
    """

    def __init__(
        self,
        action: str,  # 'released', 'refunded', 'escalated', 'stored', 'skipped', 'noop'
        success: bool,
        payment_tx: Optional[str] = None,
        refund_tx: Optional[str] = None,
        dispute_id: Optional[str] = None,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.action = action
        self.success = success
        self.payment_tx = payment_tx
        self.refund_tx = refund_tx
        self.dispute_id = dispute_id
        self.error = error
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "success": self.success,
            "payment_tx": self.payment_tx,
            "refund_tx": self.refund_tx,
            "dispute_id": self.dispute_id,
            "error": self.error,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def process_arbiter_verdict(
    verdict: ArbiterVerdict,
    task: Dict[str, Any],
    submission: Dict[str, Any],
) -> ProcessResult:
    """Dispatch an arbiter verdict to the appropriate payment action.

    This is the Phase 2 entry point. Called from background_runner.py
    after Phase B + ArbiterService.evaluate() complete.

    Args:
        verdict: The ArbiterVerdict produced by ArbiterService
        task: Task row from DB (must have id, arbiter_mode, bounty_usd)
        submission: Submission row from DB (must have id, task, executor)

    Returns:
        ProcessResult describing what happened (and any tx hashes).
    """
    submission_id = submission.get("id", "")
    task_id = task.get("id", "")

    # ---- Step 1: Persist the verdict to submissions.arbiter_* columns ----
    persist_ok = await _persist_verdict(submission_id, verdict)
    if not persist_ok:
        logger.error(
            "Failed to persist arbiter verdict for submission %s -- aborting dispatch",
            submission_id,
        )
        return ProcessResult(
            action="noop",
            success=False,
            error="Failed to persist verdict to DB",
        )

    # ---- Step 2: Resolve mode through master switch + fallback ----
    requested_mode = (task.get("arbiter_mode") or "manual").lower()
    effective_mode = await resolve_arbiter_mode(requested_mode)

    logger.info(
        "process_arbiter_verdict: task=%s submission=%s decision=%s mode=%s (requested=%s)",
        task_id,
        submission_id,
        verdict.decision.value,
        effective_mode,
        requested_mode,
    )

    # ---- Step 3: SKIPPED verdicts are no-ops ----
    if verdict.decision == ArbiterDecision.SKIPPED:
        logger.info("Arbiter SKIPPED for submission %s -- no action", submission_id)
        return ProcessResult(action="skipped", success=True)

    # ---- Step 4: Manual mode never auto-acts (verdict stored only) ----
    if effective_mode == "manual":
        logger.info(
            "Arbiter mode is 'manual' for submission %s -- verdict stored, awaiting agent",
            submission_id,
        )
        return ProcessResult(action="stored", success=True)

    # ---- Step 5: INCONCLUSIVE always escalates regardless of mode ----
    if verdict.decision == ArbiterDecision.INCONCLUSIVE:
        return await _handle_inconclusive(verdict, task, submission)

    # ---- Step 6: Hybrid mode stores verdict, doesn't auto-act ----
    if effective_mode == "hybrid":
        logger.info(
            "Hybrid mode: verdict %s stored for submission %s, awaiting agent confirmation",
            verdict.decision.value,
            submission_id,
        )
        await _notify_hybrid_verdict(task, submission, verdict)
        return ProcessResult(action="stored", success=True)

    # ---- Step 7: AUTO mode -- act on verdict ----
    if effective_mode == "auto":
        if verdict.decision == ArbiterDecision.PASS:
            return await _handle_auto_pass(verdict, task, submission)
        elif verdict.decision == ArbiterDecision.FAIL:
            return await _handle_auto_fail(verdict, task, submission)

    # Unknown mode -- safe fallback
    logger.warning(
        "Unknown effective mode '%s' for submission %s -- treating as stored",
        effective_mode,
        submission_id,
    )
    return ProcessResult(action="stored", success=True)


# ---------------------------------------------------------------------------
# AUTO mode handlers
# ---------------------------------------------------------------------------


async def _handle_auto_pass(
    verdict: ArbiterVerdict,
    task: Dict[str, Any],
    submission: Dict[str, Any],
) -> ProcessResult:
    """Arbiter PASS in auto mode -> trigger Facilitator /settle release."""
    submission_id = submission.get("id", "")
    task_id = task.get("id", "")

    try:
        # Lazy import to avoid circular deps and to keep arbiter module
        # importable in tests without the api/ package init.
        from api.routers._helpers import _settle_submission_payment

        result = await _settle_submission_payment(
            submission_id=submission_id,
            submission=submission,
            note=f"Auto-released by arbiter (verdict={verdict.decision.value}, score={verdict.aggregate_score:.3f})",
        )

        # Defensive: _settle_submission_payment may return None on certain
        # short-circuits. Treat None as failure rather than crashing on .get().
        if not isinstance(result, dict):
            err = f"Settle returned non-dict: {type(result).__name__}"
            logger.error(
                "Arbiter PASS but settle returned invalid type for submission %s: %s",
                submission_id,
                err,
            )
            await _mark_submission_payment_failed(submission_id, err)
            return ProcessResult(action="released", success=False, error=err)

        if result.get("payment_tx"):
            # Update submission verdict + agent_verdict in DB
            await _mark_submission_accepted(submission_id, verdict)
            logger.info(
                "Arbiter auto-released task %s submission %s tx=%s",
                task_id,
                submission_id,
                result["payment_tx"],
            )
            # Emit success event + webhook
            await _emit_arbiter_event(
                "submission.arbiter_pass",
                task,
                submission,
                verdict,
                extra_payload={"payment_tx": result["payment_tx"]},
            )
            await _dispatch_arbiter_webhook(
                "submission.arbiter_pass", task, submission, verdict
            )
            return ProcessResult(
                action="released",
                success=True,
                payment_tx=result["payment_tx"],
                details={"verdict_score": verdict.aggregate_score},
            )
        else:
            err = result.get("payment_error") or "unknown payment error"
            logger.error(
                "Arbiter PASS but settle failed for submission %s: %s",
                submission_id,
                err,
            )
            await _mark_submission_payment_failed(submission_id, err)
            # Emit failure event so ops gets alerted
            await _emit_arbiter_event(
                "submission.arbiter_payment_failed",
                task,
                submission,
                verdict,
                extra_payload={"error": err},
            )
            return ProcessResult(
                action="released",
                success=False,
                error=f"Settlement failed: {err}",
            )
    except Exception as e:
        logger.exception(
            "Exception during auto-release for submission %s", submission_id
        )
        return ProcessResult(
            action="released",
            success=False,
            error=f"Exception: {type(e).__name__}: {e}",
        )


async def _handle_auto_fail(
    verdict: ArbiterVerdict,
    task: Dict[str, Any],
    submission: Dict[str, Any],
) -> ProcessResult:
    """Arbiter FAIL in auto mode -> trigger Facilitator /refund."""
    submission_id = submission.get("id", "")
    task_id = task.get("id", "")

    try:
        from integrations.x402.payment_dispatcher import get_payment_dispatcher

        dispatcher = get_payment_dispatcher()
        if not dispatcher:
            return ProcessResult(
                action="refunded",
                success=False,
                error="Payment dispatcher not available",
            )

        refund_result = await dispatcher.refund_trustless_escrow(
            task_id=task_id,
            reason=f"Auto-refunded by arbiter (verdict=fail, score={verdict.aggregate_score:.3f}, reason={verdict.reason})",
        )

        # Defensive: refund_trustless_escrow may return None or non-dict on errors.
        if not isinstance(refund_result, dict):
            err = f"Refund returned non-dict: {type(refund_result).__name__}"
            logger.error("Arbiter FAIL but refund returned invalid type: %s", err)
            return ProcessResult(action="refunded", success=False, error=err)

        if refund_result.get("success"):
            await _mark_submission_rejected(submission_id, verdict)
            await _mark_escrow_refunded(task_id)
            logger.info(
                "Arbiter auto-refunded task %s submission %s tx=%s",
                task_id,
                submission_id,
                refund_result.get("tx_hash"),
            )
            # Emit refund event + webhook
            await _emit_arbiter_event(
                "submission.arbiter_fail",
                task,
                submission,
                verdict,
                extra_payload={"refund_tx": refund_result.get("tx_hash")},
            )
            await _dispatch_arbiter_webhook(
                "submission.arbiter_fail", task, submission, verdict
            )
            return ProcessResult(
                action="refunded",
                success=True,
                refund_tx=refund_result.get("tx_hash"),
                details={"verdict_score": verdict.aggregate_score},
            )
        else:
            err = refund_result.get("error") or "unknown refund error"
            logger.error("Arbiter FAIL but refund failed for task %s: %s", task_id, err)
            return ProcessResult(
                action="refunded",
                success=False,
                error=f"Refund failed: {err}",
            )
    except Exception as e:
        logger.exception("Exception during auto-refund for task %s", task_id)
        return ProcessResult(
            action="refunded",
            success=False,
            error=f"Exception: {type(e).__name__}: {e}",
        )


# ---------------------------------------------------------------------------
# INCONCLUSIVE -> escalation
# ---------------------------------------------------------------------------


async def _handle_inconclusive(
    verdict: ArbiterVerdict,
    task: Dict[str, Any],
    submission: Dict[str, Any],
) -> ProcessResult:
    """Arbiter INCONCLUSIVE -> escalate to L2 human arbiter via escalation.py."""
    try:
        from .escalation import escalate_to_human

        dispute = await escalate_to_human(verdict, task, submission)
        # Emit escalation event + webhook
        await _emit_arbiter_event(
            "submission.escalated",
            task,
            submission,
            verdict,
            extra_payload={"dispute_id": dispute.get("id") if dispute else None},
        )
        await _dispatch_arbiter_webhook(
            "submission.escalated", task, submission, verdict
        )
        return ProcessResult(
            action="escalated",
            success=True,
            dispute_id=dispute.get("id") if dispute else None,
            details={
                "verdict_score": verdict.aggregate_score,
                "disagreement": verdict.disagreement,
                "reason": verdict.reason,
            },
        )
    except Exception as e:
        logger.exception("Exception during escalation")
        return ProcessResult(
            action="escalated",
            success=False,
            error=f"Escalation failed: {e}",
        )


# ---------------------------------------------------------------------------
# Hybrid mode notification
# ---------------------------------------------------------------------------


async def _notify_hybrid_verdict(
    task: Dict[str, Any],
    submission: Dict[str, Any],
    verdict: ArbiterVerdict,
) -> None:
    """Notify agent that arbiter has a verdict awaiting their confirmation."""
    logger.info(
        "[hybrid notify] task=%s submission=%s verdict=%s -- agent must confirm",
        task.get("id"),
        submission.get("id"),
        verdict.decision.value,
    )
    # Emit event + webhook so the agent dashboard / external listeners pick it up
    await _emit_arbiter_event(
        "submission.arbiter_stored",
        task,
        submission,
        verdict,
        extra_payload={"mode": "hybrid", "awaiting_confirmation": True},
    )
    await _dispatch_arbiter_webhook(
        "submission.arbiter_stored", task, submission, verdict
    )


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------


async def _persist_verdict(
    submission_id: str,
    verdict: ArbiterVerdict,
) -> bool:
    """Write the verdict to submissions.arbiter_* columns.

    Idempotency: if a verdict is already persisted for this submission,
    we DO NOT overwrite it. This protects against duplicate processing
    if process_arbiter_verdict is invoked twice concurrently.

    Returns True if persisted (or already up-to-date), False on error.
    """
    try:
        import supabase_client as db

        client = db.get_client()

        # Idempotency check: skip update if verdict already persisted.
        existing = (
            client.table("submissions")
            .select("arbiter_verdict")
            .eq("id", submission_id)
            .execute()
        )
        if existing.data and existing.data[0].get("arbiter_verdict") is not None:
            existing_verdict = existing.data[0]["arbiter_verdict"]
            logger.info(
                "Submission %s already has arbiter_verdict=%s -- skipping persist",
                submission_id,
                existing_verdict,
            )
            # Return True so caller still proceeds with the dispatch logic
            # (the underlying _settle_submission_payment has its own idempotency).
            return True

        update_data = {
            "arbiter_verdict": verdict.decision.value,
            "arbiter_tier": verdict.tier.value,
            "arbiter_score": round(float(verdict.aggregate_score), 4),
            "arbiter_confidence": round(float(verdict.confidence), 4),
            "arbiter_evidence_hash": verdict.evidence_hash,
            "arbiter_commitment_hash": verdict.commitment_hash,
            "arbiter_verdict_data": verdict.to_dict(),
            "arbiter_cost_usd": round(float(verdict.cost_usd), 6),
            "arbiter_latency_ms": int(verdict.latency_ms),
            "arbiter_evaluated_at": verdict.evaluated_at.isoformat(),
        }
        client.table("submissions").update(update_data).eq(
            "id", submission_id
        ).execute()
        return True
    except Exception as e:
        logger.error("Failed to persist arbiter verdict for %s: %s", submission_id, e)
        return False


async def _mark_submission_accepted(
    submission_id: str,
    verdict: ArbiterVerdict,
) -> None:
    """Mark submission as accepted (called after successful auto-release)."""
    try:
        import supabase_client as db

        client = db.get_client()
        client.table("submissions").update(
            {
                "agent_verdict": "accepted",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "agent_notes": (
                    f"Auto-accepted by arbiter (Ring 2 score={verdict.aggregate_score:.3f}, "
                    f"tier={verdict.tier.value})"
                ),
            }
        ).eq("id", submission_id).execute()
    except Exception as e:
        logger.warning("Failed to mark submission %s as accepted: %s", submission_id, e)


async def _mark_submission_rejected(
    submission_id: str,
    verdict: ArbiterVerdict,
) -> None:
    """Mark submission as rejected (called after successful auto-refund)."""
    try:
        import supabase_client as db

        client = db.get_client()
        client.table("submissions").update(
            {
                "agent_verdict": "rejected",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "agent_notes": (
                    f"Auto-rejected by arbiter (Ring 2 score={verdict.aggregate_score:.3f}, "
                    f"reason={verdict.reason or 'fail threshold'})"
                ),
            }
        ).eq("id", submission_id).execute()
    except Exception as e:
        logger.warning("Failed to mark submission %s as rejected: %s", submission_id, e)


async def _mark_submission_payment_failed(
    submission_id: str,
    error: str,
) -> None:
    """Mark submission as payment_failed when arbiter said PASS but TX failed.

    Critical: do NOT auto-retry. Ops needs to investigate manually.
    """
    try:
        import supabase_client as db

        client = db.get_client()
        client.table("submissions").update(
            {
                "agent_notes": f"[ARBITER PASS but PAYMENT FAILED] {error[:500]}",
            }
        ).eq("id", submission_id).execute()
    except Exception as e:
        logger.warning(
            "Failed to mark submission %s as payment_failed: %s", submission_id, e
        )


async def _mark_escrow_refunded(task_id: str) -> None:
    """Update escrows.status = 'refunded' after a successful refund TX."""
    try:
        import supabase_client as db

        client = db.get_client()
        client.table("escrows").update(
            {
                "status": "refunded",
                "refunded_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("task_id", task_id).execute()
    except Exception as e:
        logger.warning("Failed to mark escrow %s as refunded: %s", task_id, e)


# ---------------------------------------------------------------------------
# Event bus + webhook dispatch
# ---------------------------------------------------------------------------


async def _emit_arbiter_event(
    event_type: str,
    task: Dict[str, Any],
    submission: Dict[str, Any],
    verdict: ArbiterVerdict,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Publish an arbiter-related event to the event bus.

    Event types emitted:
    - submission.arbiter_pass     -- Ring 2 verdict PASS (auto mode)
    - submission.arbiter_fail     -- Ring 2 verdict FAIL (auto mode)
    - submission.arbiter_stored   -- Verdict stored, awaiting agent (manual/hybrid)
    - submission.escalated        -- INCONCLUSIVE -> L2 dispute created
    - submission.arbiter_payment_failed -- PASS but settlement TX failed

    Failures here NEVER raise -- event bus is best-effort.
    """
    try:
        from events.bus import get_event_bus
        from events.models import EMEvent, EventSource

        payload = {
            "task_id": task.get("id"),
            "submission_id": submission.get("id"),
            "agent_id": task.get("agent_id"),
            "executor_id": (submission.get("executor") or {}).get("id"),
            "bounty_usd": float(task.get("bounty_usd", 0) or 0),
            "verdict": verdict.decision.value,
            "tier": verdict.tier.value,
            "score": float(verdict.aggregate_score),
            "confidence": float(verdict.confidence),
            "evidence_hash": verdict.evidence_hash,
            "commitment_hash": verdict.commitment_hash,
            "disagreement": verdict.disagreement,
            "cost_usd": float(verdict.cost_usd),
            "latency_ms": int(verdict.latency_ms),
        }
        if extra_payload:
            payload.update(extra_payload)

        event = EMEvent(
            event_type=event_type,
            task_id=task.get("id"),
            source=EventSource.SYSTEM,
            payload=payload,
        )
        await get_event_bus().publish(event)
        logger.debug("Emitted arbiter event %s for task %s", event_type, task.get("id"))
    except Exception as e:
        logger.warning(
            "Failed to emit arbiter event %s: %s -- continuing", event_type, e
        )


async def _dispatch_arbiter_webhook(
    event_type: str,
    task: Dict[str, Any],
    submission: Dict[str, Any],
    verdict: ArbiterVerdict,
) -> None:
    """Dispatch arbiter webhook to the agent's registered endpoints.

    Best-effort: failures are logged but never block the dispatch flow.
    Reuses the existing dispatch_webhook helper from _helpers.py.
    """
    try:
        from api.routers._helpers import dispatch_webhook

        agent_id = task.get("agent_id")
        if not agent_id:
            return

        await dispatch_webhook(
            owner_id=agent_id,
            event_type=event_type,
            payload={
                "task_id": task.get("id"),
                "submission_id": submission.get("id"),
                "verdict": verdict.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        logger.warning(
            "Failed to dispatch arbiter webhook %s: %s -- continuing", event_type, e
        )
