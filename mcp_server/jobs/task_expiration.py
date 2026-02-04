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
from typing import Optional

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
        client.table("tasks").update({
            "status": "expired",
        }).eq("id", task_id).execute()
        logger.info("[expiration] Task %s status set to 'expired'", task_id)
    except Exception as exc:
        logger.error("[expiration] Failed to update task %s: %s", task_id, exc)
        return  # Do not attempt refund if status update failed

    # 2. Refund escrow if applicable
    if not escrow_id:
        logger.info(
            "[expiration] Task %s has no escrow_id, skipping refund", task_id
        )
        return

    try:
        from integrations.x402.advanced_escrow_integration import (
            refund_to_agent,
            ADVANCED_ESCROW_AVAILABLE,
        )

        if not ADVANCED_ESCROW_AVAILABLE:
            logger.warning("[expiration] Advanced escrow SDK not available, cannot refund task %s", task_id)
            return

        result = refund_to_agent(task_id=task_id)

        if result.success:
            logger.info(
                "[expiration] Refund successful for task %s: tx=%s",
                task_id,
                getattr(result, 'transaction_hash', 'N/A'),
            )

            # 3. Record the refund as a payment entry
            try:
                client.table("payments").insert({
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "type": "refund",
                    "status": "confirmed",
                    "tx_hash": getattr(result, 'transaction_hash', ''),
                    "escrow_id": escrow_id,
                    "note": "Auto-refund: task expired past deadline (via SDK)",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
                logger.info(
                    "[expiration] Payment record created for task %s refund",
                    task_id,
                )
            except Exception as exc:
                # Non-fatal: the on-chain refund already succeeded
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


async def run_task_expiration_loop() -> None:
    """
    Background loop that checks for expired tasks every CHECK_INTERVAL seconds.

    Queries Supabase for tasks where:
      - status IN ('published', 'accepted')
      - deadline < NOW()

    For each matching task it expires the task and attempts a refund.
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
                .in_("status", ["published", "accepted"])
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
                    await _process_expired_task(client, task)
            else:
                logger.debug("[expiration] No expired tasks found")

        except Exception as exc:
            logger.error("[expiration] Error in expiration loop: %s", exc)

        await asyncio.sleep(CHECK_INTERVAL)
