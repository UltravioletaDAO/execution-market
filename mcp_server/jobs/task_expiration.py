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
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Configurable interval (seconds) via environment, default 60
CHECK_INTERVAL = int(os.environ.get("TASK_EXPIRATION_INTERVAL", "60"))


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
        return

    escrow_mode = os.environ.get("EM_ESCROW_MODE", "platform_release")

    if escrow_mode == "direct_release":
        # Fase 5 trustless: use PaymentDispatcher
        try:
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            dispatcher = PaymentDispatcher()
            result = await dispatcher.refund_trustless_escrow(
                task_id=task_id,
                reason="Auto-refund: task expired past deadline",
            )

            if result.get("success"):
                logger.info(
                    "[expiration] Fase 5 refund successful for task %s: tx=%s",
                    task_id,
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
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).execute()
                except Exception as exc:
                    logger.error(
                        "[expiration] Failed to record payment for task %s: %s",
                        task_id,
                        exc,
                    )
            else:
                logger.warning(
                    "[expiration] Fase 5 refund failed for task %s: %s",
                    task_id,
                    result.get("error"),
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

            result = refund_to_agent(task_id=task_id)

            if result.success:
                logger.info(
                    "[expiration] Refund successful for task %s: tx=%s",
                    task_id,
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
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).execute()
                except Exception as exc:
                    logger.error(
                        "[expiration] Failed to record payment for task %s: %s",
                        task_id,
                        exc,
                    )
            else:
                logger.warning(
                    "[expiration] Refund failed for task %s (escrow_id=%s): %s",
                    task_id,
                    escrow_id,
                    result.error,
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
            logger.warning(
                "[expiration] Task %s submission %s not ready for payout (reason=%s). Keeping submitted for retry.",
                task_id,
                submission_id,
                readiness.get("reason"),
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
        try:
            client = get_client()
            now = datetime.now(timezone.utc).isoformat()

            # Query tasks past deadline that are still active
            result = (
                client.table("tasks")
                .select("id, status, agent_id, bounty_usd, escrow_id, deadline")
                .in_("status", ["published", "accepted", "submitted"])
                .lt("deadline", now)
                .execute()
            )

            expired_tasks = result.data or []

            if expired_tasks:
                logger.info(
                    "[expiration] Found %d expired task(s) to process",
                    len(expired_tasks),
                )

                for task in expired_tasks:
                    if task.get("status") == "submitted":
                        handled = await _process_submitted_timeout_task(client, task)
                        if handled:
                            continue
                    await _process_expired_task(client, task)
            else:
                logger.debug("[expiration] No expired tasks found")

        except Exception as exc:
            logger.error("[expiration] Error in expiration loop: %s", exc)

        await asyncio.sleep(CHECK_INTERVAL)
