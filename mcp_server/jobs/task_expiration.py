"""
Task Expiration & Auto-Refund Job

Periodically checks for tasks past their deadline and:
1. Updates status to 'expired'
2. Refunds escrowed funds to the agent (if escrow_id exists)
3. Records the refund as a payment record in Supabase

Runs every 60 seconds as a background asyncio task.
"""

import asyncio
import logging
import os
import time as _time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Configurable interval (seconds) via environment, default 60
CHECK_INTERVAL = int(os.environ.get("TASK_EXPIRATION_INTERVAL", "60"))

# Circuit breaker: track consecutive failures for health reporting
_consecutive_failures = 0
_MAX_CONSECUTIVE_FAILURES = 5
_last_success_time: float = 0.0


def get_expiration_health() -> dict:
    """Return health status for the expiration job (used by /health endpoint)."""
    if _consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        return {"status": "unhealthy", "consecutive_failures": _consecutive_failures}
    if _last_success_time == 0.0:
        return {"status": "starting", "consecutive_failures": 0}
    return {"status": "healthy", "consecutive_failures": _consecutive_failures}


# Payout failure reasons that are permanent and should not be retried.
# Tasks with these reasons get expired instead of retried every cycle.
_PERMANENT_FAILURE_REASONS = frozenset(
    {
        "missing_payment_header",
        "x402_unavailable",
        "missing_task",
        "self_payment_blocked",
    }
)


async def _process_expired_task(client, task: dict) -> None:
    """
    Handle a single expired task: update status, refund escrow, record payment.

    Args:
        client: Supabase client instance.
        task: Task row dict from Supabase.
    """
    task_id = task["id"]
    escrow_id = task.get("escrow_id")
    bounty = task.get("bounty_usd", 0)
    agent_id = task.get("agent_id", "unknown")

    logger.info(
        "[expiration] Expiring task %s (status=%s, agent=%s, bounty=$%.2f)",
        task_id,
        task["status"],
        agent_id,
        bounty,
    )

    # 1. Mark the task as expired
    try:
        client.table("tasks").update(
            {
                "status": "expired",
            }
        ).eq("id", task_id).execute()
        logger.info("[expiration] Task %s status set to 'expired'", task_id)
    except Exception as exc:
        logger.error("[expiration] Failed to update task %s: %s", task_id, exc)
        return  # Do not attempt refund if status update failed

    # 2. Refund escrow if applicable
    if not escrow_id:
        logger.info("[expiration] Task %s has no escrow_id, skipping refund", task_id)
        from audit import audit_log

        audit_log("preauth_expired", task_id=task_id, zero_cost=True)
        return

    escrow_mode = os.environ.get("EM_ESCROW_MODE", "platform_release")

    # Retry configuration for refund attempts
    max_retries = 3
    retry_delay_s = 5

    if escrow_mode == "direct_release":
        # Fase 5 trustless: use PaymentDispatcher
        try:
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            dispatcher = PaymentDispatcher()
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    result = await dispatcher.refund_trustless_escrow(
                        task_id=task_id,
                        reason="Auto-refund: task expired past deadline",
                    )

                    if result.get("success"):
                        logger.info(
                            "[expiration] Fase 5 refund successful for task %s (attempt %d): tx=%s",
                            task_id,
                            attempt,
                            result.get("tx_hash", "N/A"),
                        )
                        try:
                            client.table("payments").insert(
                                {
                                    "task_id": task_id,
                                    "agent_id": agent_id,
                                    "type": "refund",
                                    "status": "confirmed",
                                    "tx_hash": result.get("tx_hash", ""),
                                    "escrow_id": escrow_id,
                                    "note": "Auto-refund: task expired past deadline (Fase 5 trustless)",
                                    "created_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                }
                            ).execute()
                        except Exception as exc:
                            logger.error(
                                "[expiration] Failed to record payment for task %s: %s",
                                task_id,
                                exc,
                            )
                        last_error = None
                        break  # Success — exit retry loop
                    else:
                        last_error = result.get("error", "Refund returned failure")
                        logger.warning(
                            "[expiration] Fase 5 refund attempt %d/%d failed for task %s: %s",
                            attempt,
                            max_retries,
                            task_id,
                            last_error,
                        )
                except Exception as retry_exc:
                    last_error = str(retry_exc)
                    logger.warning(
                        "[expiration] Fase 5 refund attempt %d/%d raised exception for task %s: %s",
                        attempt,
                        max_retries,
                        task_id,
                        retry_exc,
                    )

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay_s)

            # All retries exhausted — log failure to payment_events
            if last_error:
                logger.warning(
                    "[expiration] All %d refund attempts failed for task %s: %s",
                    max_retries,
                    task_id,
                    last_error,
                )
                try:
                    from integrations.x402.payment_events import log_payment_event

                    await log_payment_event(
                        task_id=task_id,
                        event_type="refund_failed",
                        status="failed",
                        error=f"Auto-refund exhausted {max_retries} retries: {last_error}",
                        metadata={
                            "escrow_id": escrow_id,
                            "escrow_mode": "direct_release",
                            "retries": max_retries,
                        },
                    )
                except Exception as log_exc:
                    logger.error(
                        "[expiration] Could not log refund_failed event for task %s: %s",
                        task_id,
                        log_exc,
                    )

        except ImportError:
            logger.warning(
                "[expiration] PaymentDispatcher not available for Fase 5, skipping refund for task %s",
                task_id,
            )
        except Exception as exc:
            logger.error(
                "[expiration] Unexpected error in Fase 5 refund for task %s: %s",
                task_id,
                exc,
            )
    else:
        # Legacy platform_release: use advanced_escrow_integration
        try:
            from integrations.x402.advanced_escrow_integration import (
                refund_to_agent,
                ADVANCED_ESCROW_AVAILABLE,
            )

            if not ADVANCED_ESCROW_AVAILABLE:
                logger.warning(
                    "[expiration] Advanced escrow SDK not available, cannot refund task %s",
                    task_id,
                )
                return

            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    result = refund_to_agent(task_id=task_id)

                    if result.success:
                        logger.info(
                            "[expiration] Refund successful for task %s (attempt %d): tx=%s",
                            task_id,
                            attempt,
                            getattr(result, "transaction_hash", "N/A"),
                        )
                        try:
                            client.table("payments").insert(
                                {
                                    "task_id": task_id,
                                    "agent_id": agent_id,
                                    "type": "refund",
                                    "status": "confirmed",
                                    "tx_hash": getattr(result, "transaction_hash", ""),
                                    "escrow_id": escrow_id,
                                    "note": "Auto-refund: task expired past deadline (via SDK)",
                                    "created_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                }
                            ).execute()
                        except Exception as exc:
                            logger.error(
                                "[expiration] Failed to record payment for task %s: %s",
                                task_id,
                                exc,
                            )
                        last_error = None
                        break  # Success — exit retry loop
                    else:
                        last_error = str(
                            getattr(result, "error", "Refund returned failure")
                        )
                        logger.warning(
                            "[expiration] Refund attempt %d/%d failed for task %s (escrow_id=%s): %s",
                            attempt,
                            max_retries,
                            task_id,
                            escrow_id,
                            last_error,
                        )
                except Exception as retry_exc:
                    last_error = str(retry_exc)
                    logger.warning(
                        "[expiration] Refund attempt %d/%d raised exception for task %s: %s",
                        attempt,
                        max_retries,
                        task_id,
                        retry_exc,
                    )

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay_s)

            # All retries exhausted — log failure to payment_events
            if last_error:
                logger.warning(
                    "[expiration] All %d refund attempts failed for task %s: %s",
                    max_retries,
                    task_id,
                    last_error,
                )
                try:
                    from integrations.x402.payment_events import log_payment_event

                    await log_payment_event(
                        task_id=task_id,
                        event_type="refund_failed",
                        status="failed",
                        error=f"Auto-refund exhausted {max_retries} retries: {last_error}",
                        metadata={
                            "escrow_id": escrow_id,
                            "escrow_mode": "platform_release",
                            "retries": max_retries,
                        },
                    )
                except Exception as log_exc:
                    logger.error(
                        "[expiration] Could not log refund_failed event for task %s: %s",
                        task_id,
                        log_exc,
                    )

        except ImportError:
            logger.warning(
                "[expiration] x402r escrow not available, skipping refund for task %s",
                task_id,
            )
        except Exception as exc:
            logger.error(
                "[expiration] Unexpected error refunding task %s: %s",
                task_id,
                exc,
            )


async def _process_submitted_timeout_task(client, task: dict) -> bool:
    """
    Handle submitted tasks that passed deadline.

    Returns:
        bool: True when handled as submitted flow (even if retry needed),
        False when caller should fall back to normal expiration/refund flow.
    """
    task_id = task["id"]
    logger.info(
        "[expiration] Submitted task %s reached deadline; attempting auto-settlement",
        task_id,
    )

    try:
        submission_result = (
            client.table("submissions")
            .select("id,agent_verdict")
            .eq("task_id", task_id)
            .order("submitted_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error(
            "[expiration] Could not query submissions for task %s: %s", task_id, exc
        )
        return False

    rows = submission_result.data or []
    if not rows:
        logger.warning(
            "[expiration] Task %s is submitted but has no submission row; expiring task",
            task_id,
        )
        return False

    submission_id = rows[0].get("id")
    if not submission_id:
        logger.warning(
            "[expiration] Task %s submission row missing id; expiring task", task_id
        )
        return False

    try:
        import supabase_client as db
        from api import routes as api_routes

        submission = await db.get_submission(submission_id)
        if not submission:
            logger.warning(
                "[expiration] Could not load submission %s for task %s; expiring task",
                submission_id,
                task_id,
            )
            return False

        readiness = await api_routes._is_submission_ready_for_instant_payout(
            submission_id=submission_id,
            submission=submission,
        )
        if not readiness.get("ready"):
            reason = readiness.get("reason", "unknown")
            # Bug fix: permanent failures (e.g. missing_payment_header) should
            # not be retried every 60s. Mark them and fall through to expiration
            # instead of keeping the task in 'submitted' forever.
            if reason in _PERMANENT_FAILURE_REASONS:
                logger.warning(
                    "[expiration] Task %s submission %s permanently unresolvable (reason=%s). Expiring task.",
                    task_id,
                    submission_id,
                    reason,
                )
                # Note: tasks table has no metadata column — just log and expire
                logger.info(
                    "[expiration] Task %s permanently failed: %s", task_id, reason
                )
                return False  # Fall through to normal expiration
            logger.warning(
                "[expiration] Task %s submission %s not ready for payout (reason=%s). Keeping submitted for retry.",
                task_id,
                submission_id,
                reason,
            )
            return True

        settlement = await api_routes._settle_submission_payment(
            submission_id=submission_id,
            submission=submission,
            note="Auto-settlement on deadline for submitted task",
        )
        payment_tx = settlement.get("payment_tx")
        if not payment_tx:
            logger.warning(
                "[expiration] Task %s submission %s settlement did not produce tx (error=%s). Keeping submitted for retry.",
                task_id,
                submission_id,
                settlement.get("payment_error"),
            )
            return True

        try:
            await api_routes._auto_approve_submission(
                submission_id=submission_id,
                submission=submission,
                note="Auto-approved at deadline after successful payout",
            )
        except Exception as finalize_err:
            logger.error(
                "[expiration] Payment released for task %s but could not finalize completion: %s",
                task_id,
                finalize_err,
            )

        logger.info(
            "[expiration] Submitted task %s auto-settled on deadline (submission=%s, tx=%s)",
            task_id,
            submission_id,
            payment_tx,
        )
        return True
    except Exception as exc:
        logger.error(
            "[expiration] Submitted timeout processing failed for task %s: %s",
            task_id,
            exc,
        )
        return True


STALE_EVENT_THRESHOLD_SECONDS = 300  # 5 minutes

# Phase B orphan threshold for periodic re-queue (seconds).  Submissions
# stuck in phase='A' longer than this with no ai_verification_result are
# candidates for re-queuing Phase B.
ORPHAN_PHASE_B_THRESHOLD_SECONDS = 300  # 5 minutes


async def _cleanup_stale_verification_events(client) -> None:
    """Append a 'failed' event to submissions with stale 'running' verification events.

    If a Phase B verification step crashes, the last event will remain in
    ``status="running"`` forever.  This function detects events older than
    ``STALE_EVENT_THRESHOLD_SECONDS`` and marks them as failed so the
    frontend does not show a spinner indefinitely.

    Also detects orphaned Phase B submissions (phase='A', older than
    ORPHAN_PHASE_B_THRESHOLD_SECONDS, no ai_verification_result) and
    re-queues them.

    Operates on all submissions with ``auto_check_details`` containing at
    least one ``verification_events`` entry.  Runs once per expiration
    cycle and is intentionally simple (no batching).
    """
    cutoff_ts = int(_time.time()) - STALE_EVENT_THRESHOLD_SECONDS

    try:
        result = (
            client.table("submissions")
            .select(
                "id, task_id, evidence, submitted_at, auto_check_details, "
                "ai_verification_result, status"
            )
            .not_.is_("auto_check_details", "null")
            .execute()
        )
    except Exception as exc:
        logger.debug("[stale-events] Query failed: %s", exc)
        return

    rows = result.data or []
    patched = 0
    requeued = 0

    for row in rows:
        details = row.get("auto_check_details") or {}

        # ── Part 1: Stale running events ──
        events = details.get("verification_events")
        if events and isinstance(events, list):
            last_event = events[-1]
            if (
                last_event.get("status") == "running"
                and last_event.get("ts", 0) <= cutoff_ts
            ):
                # Append a failed event so the frontend stops showing a spinner
                events.append(
                    {
                        "ts": int(_time.time()),
                        "ring": last_event.get("ring", 0),
                        "step": last_event.get("step", "unknown"),
                        "status": "failed",
                        "detail": {"reason": "timeout -- verification step stalled"},
                    }
                )
                details["verification_events"] = events

                try:
                    client.table("submissions").update(
                        {"auto_check_details": details}
                    ).eq("id", row["id"]).execute()
                    patched += 1
                except Exception as exc:
                    logger.warning(
                        "[stale-events] Failed to patch submission %s: %s",
                        row["id"],
                        exc,
                    )

        # ── Part 2: Orphaned Phase B re-queue ──
        # Only re-queue if:
        #   - phase == 'A' (Phase A done, Phase B never finished)
        #   - ai_verification_result is None
        #   - status is still 'pending' or 'submitted'
        #   - submitted_at is older than ORPHAN_PHASE_B_THRESHOLD_SECONDS
        if (
            details.get("phase") == "A"
            and row.get("ai_verification_result") is None
            and row.get("status") in ("pending", "submitted")
        ):
            submitted_at = row.get("submitted_at")
            if submitted_at:
                try:
                    from datetime import datetime, timezone

                    if isinstance(submitted_at, str):
                        # Handle both ISO formats with and without Z
                        ts = submitted_at.replace("Z", "+00:00")
                        sub_dt = datetime.fromisoformat(ts)
                    else:
                        sub_dt = submitted_at
                    age_seconds = (datetime.now(timezone.utc) - sub_dt).total_seconds()
                except Exception:
                    age_seconds = 0

                if age_seconds > ORPHAN_PHASE_B_THRESHOLD_SECONDS:
                    requeued += await _requeue_orphaned_phase_b(row)

    if patched:
        logger.info("[stale-events] Patched %d stale verification event(s)", patched)
    if requeued:
        logger.info(
            "[stale-events] Re-queued %d orphaned Phase B submission(s)", requeued
        )


async def _requeue_orphaned_phase_b(row: dict) -> int:
    """Re-queue a single orphaned Phase B verification.

    Returns 1 on success, 0 on skip/failure.
    """
    submission_id = row["id"]
    task_id = row["task_id"]
    sid = submission_id[:8]

    try:
        from jobs.phase_b_recovery import is_shutting_down

        if is_shutting_down():
            return 0

        import supabase_client as sdb
        from verification.background_runner import run_phase_b_verification

        submission = await sdb.get_submission(submission_id)
        if not submission:
            logger.debug("[stale-events] Submission %s gone, skipping re-queue", sid)
            return 0

        # Double-check: if Phase B completed between the query and now, skip
        current_details = submission.get("auto_check_details") or {}
        if current_details.get("phase") != "A":
            return 0
        if submission.get("ai_verification_result") is not None:
            return 0

        task = await sdb.get_task(task_id)
        if not task:
            logger.debug(
                "[stale-events] Task %s for submission %s gone, skipping", task_id, sid
            )
            return 0

        logger.info(
            "[stale-events] Re-queuing orphaned Phase B for submission %s "
            "(submitted %s)",
            sid,
            row.get("submitted_at", "unknown"),
        )

        asyncio.create_task(
            run_phase_b_verification(
                submission_id=submission_id,
                submission=submission,
                task=task,
            )
        )
        return 1

    except Exception as exc:
        logger.warning("[stale-events] Failed to re-queue Phase B for %s: %s", sid, exc)
        return 0


async def run_task_expiration_loop() -> None:
    """
    Background loop that checks for expired tasks every CHECK_INTERVAL seconds.

    Queries Supabase for tasks where:
      - status IN ('published', 'accepted', 'submitted')
      - deadline < NOW()

    For each matching task:
      - submitted: attempts auto-settlement/completion first
      - others: expires task and attempts refund
    """
    logger.info(
        "[expiration] Task expiration job started (interval=%ds)", CHECK_INTERVAL
    )

    # Import here so the module can be loaded even if supabase is not configured
    from supabase_client import get_client

    while True:
        _cycle_start = _time.time()
        _expired_count = 0
        _skipped_count = 0
        try:
            client = get_client()
            now = datetime.now(timezone.utc).isoformat()

            # Query tasks past deadline that are still active.
            result = (
                client.table("tasks")
                .select("id, status, agent_id, bounty_usd, escrow_id, deadline")
                .in_("status", ["published", "accepted", "submitted"])
                .lt("deadline", now)
                .execute()
            )

            expired_tasks = result.data or []

            if expired_tasks:
                actionable_tasks = []
                for task in expired_tasks:
                    if task.get("status") == "submitted":
                        actionable_tasks.append(("submitted", task))
                    else:
                        actionable_tasks.append(("expire", task))

                logger.info(
                    "[expiration] Found %d expired task(s) to process",
                    len(actionable_tasks),
                )

                for action, task in actionable_tasks:
                    if action == "submitted":
                        handled = await _process_submitted_timeout_task(client, task)
                        if handled:
                            _skipped_count += 1
                            continue
                    await _process_expired_task(client, task)
                    _expired_count += 1
            else:
                logger.debug("[expiration] No expired tasks found")

            # Reset circuit breaker on success
            global _consecutive_failures, _last_success_time
            _consecutive_failures = 0
            _last_success_time = _time.time()

        except Exception as exc:
            _consecutive_failures += 1
            logger.error(
                "[expiration] Error in expiration loop (%d/%d consecutive): %s",
                _consecutive_failures,
                _MAX_CONSECUTIVE_FAILURES,
                exc,
            )
            if _consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                logger.critical(
                    "[expiration] Circuit breaker OPEN — %d consecutive failures. "
                    "Health check will report unhealthy.",
                    _consecutive_failures,
                )

        # Clean up stale verification events (safety net for Phase B crashes)
        try:
            await _cleanup_stale_verification_events(client)
        except Exception as exc:
            logger.warning("[expiration] Stale verification cleanup failed: %s", exc)

        from audit import audit_log

        audit_log(
            "expire_cycle",
            expired_count=_expired_count,
            skipped_count=_skipped_count,
            duration_ms=round((_time.time() - _cycle_start) * 1000, 1),
        )

        await asyncio.sleep(CHECK_INTERVAL)
