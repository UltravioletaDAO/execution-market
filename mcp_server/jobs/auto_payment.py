"""
Auto-Payment Background Job

Processes pending payment records created by the auto-approve trigger.
For each pending full_release/final_release payment:
1. Attempts to release funds via advanced escrow (SDK → Facilitator → on-chain)
2. Updates payment record with transaction_hash and status
3. Falls back to demo mode (marks completed without on-chain tx) if escrow unavailable

Runs every 15 seconds as a background asyncio task.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CHECK_INTERVAL = int(os.environ.get("AUTO_PAYMENT_INTERVAL", "15"))


async def _process_pending_payment(client, payment: dict) -> None:
    """Process a single pending payment record."""
    payment_id = payment["id"]
    task_id = payment.get("task_id")
    amount = payment.get("amount_usdc", 0)

    logger.info(
        "[auto-payment] Processing payment %s for task %s ($%.2f)",
        payment_id, task_id, float(amount),
    )

    tx_hash = None
    release_success = False

    # Try advanced escrow release via SDK
    try:
        from integrations.x402.advanced_escrow_integration import (
            release_to_worker,
            ADVANCED_ESCROW_AVAILABLE,
        )

        if ADVANCED_ESCROW_AVAILABLE and task_id:
            result = release_to_worker(task_id=task_id)
            if getattr(result, 'success', False):
                tx_hash = getattr(result, 'transaction_hash', None)
                release_success = True
                logger.info(
                    "[auto-payment] Escrow release OK for task %s: tx=%s",
                    task_id, tx_hash,
                )
            else:
                logger.warning(
                    "[auto-payment] Escrow release returned non-success for task %s: %s",
                    task_id, getattr(result, 'error', 'unknown'),
                )
    except ImportError:
        logger.debug("[auto-payment] Advanced escrow not available")
    except Exception as exc:
        logger.warning("[auto-payment] Escrow release failed for task %s: %s", task_id, exc)

    # Update payment record
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "status": "completed",
        "completed_at": now,
    }

    if tx_hash:
        update_data["transaction_hash"] = tx_hash
        update_data["memo"] = "Payment released via SDK/facilitator"
    else:
        update_data["memo"] = (
            "Auto-completed (demo mode — escrow release unavailable or not configured)"
        )

    try:
        client.table("payments").update(update_data).eq("id", payment_id).execute()
        logger.info(
            "[auto-payment] Payment %s marked completed (on-chain=%s)",
            payment_id, release_success,
        )
    except Exception as exc:
        logger.error("[auto-payment] Failed to update payment %s: %s", payment_id, exc)


async def run_auto_payment_loop() -> None:
    """
    Background loop that processes pending payments every CHECK_INTERVAL seconds.

    Queries the payments table for records where:
      - status = 'pending'
      - payment_type IN ('full_release', 'final_release')
    """
    logger.info(
        "[auto-payment] Auto-payment job started (interval=%ds)", CHECK_INTERVAL
    )

    from supabase_client import get_client

    while True:
        try:
            client = get_client()

            result = (
                client.table("payments")
                .select("id, task_id, executor_id, amount_usdc, payment_type, status")
                .eq("status", "pending")
                .in_("payment_type", ["full_release", "final_release"])
                .order("created_at", desc=False)
                .limit(10)
                .execute()
            )

            pending = result.data or []

            if pending:
                logger.info(
                    "[auto-payment] Found %d pending payment(s) to process",
                    len(pending),
                )
                for payment in pending:
                    await _process_pending_payment(client, payment)
            else:
                logger.debug("[auto-payment] No pending payments")

        except Exception as exc:
            logger.error("[auto-payment] Error in payment loop: %s", exc)

        await asyncio.sleep(CHECK_INTERVAL)
