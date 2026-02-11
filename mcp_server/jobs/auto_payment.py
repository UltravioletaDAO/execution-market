"""
Payment Retry Background Job

Retries settlement for orphaned submissions: accepted/approved but missing payment_tx.

For each orphaned submission:
1. Resolves the x402 X-Payment header from task.escrow_tx or escrows table
2. Checks payment_mode — only retries auth-based settlement for 'preauth' mode
3. Calls EMX402SDK.settle_task_payment() via the facilitator
4. Updates submission.payment_tx, paid_at, payment_amount on success

Modes that are NOT retryable via auth re-settlement:
- fase1: No auth signed at creation — approval creates fresh EIP-3009 inline.
- fase2: Auth nonce consumed on-chain at escrow lock — re-settle causes 60s timeout.
- x402r (deprecated): Same nonce issue as fase2.

Only 'preauth' mode stores a valid, unsettled EIP-3009 auth header.

Runs every RETRY_INTERVAL seconds (default: 60).
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

RETRY_INTERVAL = int(os.environ.get("PAYMENT_RETRY_INTERVAL", "60"))
MAX_BATCH = int(os.environ.get("PAYMENT_RETRY_BATCH_SIZE", "5"))
MAX_RETRIES_PER_SUBMISSION = int(os.environ.get("PAYMENT_RETRY_MAX_ATTEMPTS", "10"))

# Task statuses where payment retry should NOT proceed
TERMINAL_TASK_STATUSES = {"cancelled", "expired", "failed"}

# Payment modes where auth re-settlement is valid
RETRYABLE_PAYMENT_MODES = {"preauth"}


def _is_tx_hash(value: Optional[str]) -> bool:
    """Check if a string looks like a valid 0x-prefixed tx hash."""
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    return v.startswith("0x") and len(v) == 66


def _is_probable_x402_header(value: Optional[str]) -> bool:
    """Check if a string is likely a base64-encoded x402 X-Payment header."""
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    return len(v) > 64 and (v.startswith("eyJ") or v.startswith("{"))


def _resolve_payment_header(
    task_id: Optional[str], task_escrow_tx: Optional[str]
) -> Optional[str]:
    """
    Resolve the original x402 X-Payment header for settlement retry.

    Priority:
    1) tasks.escrow_tx if it contains a full header
    2) escrows.metadata.x_payment_header
    """
    if _is_probable_x402_header(task_escrow_tx):
        return task_escrow_tx

    if not task_id:
        return None

    try:
        from supabase_client import get_client

        client = get_client()
        escrow_result = (
            client.table("escrows")
            .select("metadata")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = escrow_result.data or []
        if not rows:
            return None
        metadata = rows[0].get("metadata")
        if isinstance(metadata, dict):
            return metadata.get("x_payment_header")
        return None
    except Exception as err:
        logger.debug("Could not resolve x402 header for task %s: %s", task_id, err)
        return None


def _resolve_payment_mode(task_id: Optional[str]) -> Optional[str]:
    """
    Resolve the payment_mode used when a task was created.
    Reads from escrows.metadata.payment_mode.
    Returns None if not found.
    """
    if not task_id:
        return None
    try:
        from supabase_client import get_client

        client = get_client()
        result = (
            client.table("escrows")
            .select("metadata")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        metadata = rows[0].get("metadata")
        if isinstance(metadata, dict):
            return metadata.get("payment_mode")
        return None
    except Exception:
        return None


async def _fetch_orphaned_submissions(client) -> list:
    """
    Query submissions that are accepted/approved but lack payment_tx.
    Returns list of submission dicts with joined task and executor data.

    Post-fetch filtering:
    - Skips submissions that exceeded MAX_RETRIES_PER_SUBMISSION
    - Skips submissions whose task is in a terminal status (cancelled/expired)
    """
    try:
        result = (
            client.table("submissions")
            .select(
                "id, task_id, executor_id, agent_verdict, payment_tx, retry_count, task:tasks(id, bounty_usd, escrow_tx, escrow_id, status), executor:executors(id, wallet_address)"
            )
            .in_("agent_verdict", ["accepted", "approved"])
            .is_("payment_tx", "null")
            .order("updated_at", desc=False)
            .limit(MAX_BATCH * 2)  # Fetch extra to account for post-fetch filtering
            .execute()
        )
        raw = result.data or []
    except Exception as err:
        # Fallback: try without retry_count column (may not exist)
        if "retry_count" in str(err):
            try:
                result = (
                    client.table("submissions")
                    .select(
                        "id, task_id, executor_id, agent_verdict, payment_tx, task:tasks(id, bounty_usd, escrow_tx, escrow_id, status), executor:executors(id, wallet_address)"
                    )
                    .in_("agent_verdict", ["accepted", "approved"])
                    .is_("payment_tx", "null")
                    .order("updated_at", desc=False)
                    .limit(MAX_BATCH * 2)
                    .execute()
                )
                raw = result.data or []
            except Exception as fallback_err:
                logger.error(
                    "[payment-retry] Fallback query also failed: %s", fallback_err
                )
                return []
        else:
            logger.error(
                "[payment-retry] Failed to fetch orphaned submissions: %s", err
            )
            return []

    # Post-fetch filtering
    filtered = []
    for sub in raw:
        if len(filtered) >= MAX_BATCH:
            break

        # Skip if retry_count exceeded
        retry_count = sub.get("retry_count") or 0
        if retry_count >= MAX_RETRIES_PER_SUBMISSION:
            logger.debug(
                "[payment-retry] Submission %s exceeded max retries (%d/%d), skipping",
                sub.get("id"),
                retry_count,
                MAX_RETRIES_PER_SUBMISSION,
            )
            continue

        # Skip if task is in terminal status
        task = sub.get("task")
        if isinstance(task, list):
            task = task[0] if task else {}
        task_status = (task.get("status") or "").lower() if task else ""
        if task_status in TERMINAL_TASK_STATUSES:
            logger.debug(
                "[payment-retry] Submission %s has terminal task status '%s', skipping",
                sub.get("id"),
                task_status,
            )
            continue

        filtered.append(sub)

    return filtered


async def _retry_settlement(client, submission: dict) -> bool:
    """
    Attempt to settle payment for a single orphaned submission.
    Returns True if settlement produced a tx hash.

    IMPORTANT: Only retries auth-based settlement for 'preauth' mode.
    Other modes (fase1, fase2, x402r) use different settlement mechanisms
    that cannot be retried by re-submitting the original auth header.
    """
    submission_id = submission["id"]

    # Extract nested task/executor
    task = submission.get("task")
    executor = submission.get("executor")

    if isinstance(task, list):
        task = task[0] if task else {}
    if isinstance(executor, list):
        executor = executor[0] if executor else {}

    if not task or not executor:
        logger.warning(
            "[payment-retry] Submission %s missing task or executor data, skipping",
            submission_id,
        )
        return False

    task_id = task.get("id")
    worker_address = executor.get("wallet_address")
    bounty = Decimal(str(task.get("bounty_usd", 0)))

    if bounty <= 0:
        logger.warning(
            "[payment-retry] Submission %s has zero bounty, skipping", submission_id
        )
        return False

    if not worker_address:
        logger.warning(
            "[payment-retry] Submission %s has no worker wallet, skipping",
            submission_id,
        )
        return False

    # Check payment mode — only preauth is retryable via auth re-settlement
    payment_mode = _resolve_payment_mode(task_id)
    if payment_mode and payment_mode not in RETRYABLE_PAYMENT_MODES:
        logger.info(
            "[payment-retry] Submission %s uses payment_mode='%s' "
            "(not retryable via auth re-settlement), skipping. "
            "Modes fase2/x402r: EIP-3009 nonce already consumed on-chain. "
            "Mode fase1: no stored auth header — approval creates fresh auths inline.",
            submission_id,
            payment_mode,
        )
        # Mark as max-retried so we don't re-evaluate every cycle
        _mark_non_retryable(client, submission_id, payment_mode)
        return False

    # Resolve X-Payment header
    payment_header = _resolve_payment_header(task_id, task.get("escrow_tx"))
    if not payment_header:
        logger.warning(
            "[payment-retry] No x402 payment header for submission %s (task %s), skipping",
            submission_id,
            task_id,
        )
        return False

    # Attempt settlement via SDK
    try:
        from integrations.x402.sdk_client import get_sdk, SDK_AVAILABLE

        if not SDK_AVAILABLE:
            logger.warning("[payment-retry] x402 SDK not available, skipping")
            return False

        sdk = get_sdk()
        result = await sdk.settle_task_payment(
            task_id=task_id or "",
            payment_header=payment_header,
            worker_address=worker_address,
            bounty_amount=bounty,
        )

        if not result.get("success"):
            error = result.get("error", "unknown")
            logger.warning(
                "[payment-retry] Settlement failed for submission %s: %s",
                submission_id,
                error,
            )
            # Increment retry count if column exists
            _increment_retry_count(client, submission_id)
            return False

        # Extract tx hash from result
        tx_hash = None
        for key in ("tx_hash", "transaction_hash", "transaction", "hash"):
            candidate = result.get(key)
            if _is_tx_hash(candidate):
                tx_hash = candidate
                break

        if not tx_hash:
            logger.warning(
                "[payment-retry] Settlement succeeded but no tx hash for submission %s",
                submission_id,
            )
            _increment_retry_count(client, submission_id)
            return False

        # Calculate worker net amount
        platform_fee_pct = Decimal(os.environ.get("EM_PLATFORM_FEE", "0.08"))
        fee = (bounty * platform_fee_pct).quantize(Decimal("0.01"))
        worker_payout = float(bounty - fee)

        # Update submission with payment data
        now = datetime.now(timezone.utc).isoformat()
        try:
            client.table("submissions").update(
                {
                    "payment_tx": tx_hash,
                    "payment_amount": round(worker_payout, 6),
                    "paid_at": now,
                }
            ).eq("id", submission_id).execute()
        except Exception as update_err:
            logger.warning(
                "[payment-retry] Could not update submission %s paid fields: %s",
                submission_id,
                update_err,
            )

        # Try to persist payment record (best effort, table may not exist)
        _persist_payment_record(
            client,
            submission_id=submission_id,
            task_id=task_id,
            executor_id=executor.get("id"),
            escrow_id=task.get("escrow_id"),
            tx_hash=tx_hash,
            worker_payout=worker_payout,
            fee=float(fee),
            worker_address=worker_address,
        )

        logger.info(
            "[payment-retry] Settlement OK: submission=%s, task=%s, tx=%s, net=%.2f",
            submission_id,
            task_id,
            tx_hash,
            worker_payout,
        )
        return True

    except ImportError:
        logger.warning("[payment-retry] x402 SDK not importable, skipping")
        return False
    except Exception as exc:
        logger.error(
            "[payment-retry] Unexpected error settling submission %s: %s",
            submission_id,
            exc,
        )
        _increment_retry_count(client, submission_id)
        return False


def _increment_retry_count(client, submission_id: str) -> None:
    """Best-effort increment of retry_count on submissions (column may not exist)."""
    try:
        # Fetch current count
        result = (
            client.table("submissions")
            .select("retry_count")
            .eq("id", submission_id)
            .limit(1)
            .execute()
        )
        current = 0
        if result.data:
            current = result.data[0].get("retry_count") or 0
        client.table("submissions").update(
            {
                "retry_count": current + 1,
            }
        ).eq("id", submission_id).execute()
    except Exception:
        pass  # Column may not exist yet


def _mark_non_retryable(client, submission_id: str, payment_mode: str) -> None:
    """
    Mark a submission as non-retryable by setting retry_count to MAX.
    This prevents re-evaluating it every cycle when the payment mode
    is inherently incompatible with auth re-settlement.
    """
    try:
        client.table("submissions").update(
            {
                "retry_count": MAX_RETRIES_PER_SUBMISSION,
            }
        ).eq("id", submission_id).execute()
        logger.debug(
            "[payment-retry] Marked submission %s as non-retryable (mode=%s)",
            submission_id,
            payment_mode,
        )
    except Exception:
        pass  # Column may not exist


def _persist_payment_record(
    client,
    submission_id: str,
    task_id: Optional[str],
    executor_id: Optional[str],
    escrow_id: Optional[str],
    tx_hash: str,
    worker_payout: float,
    fee: float,
    worker_address: str,
) -> None:
    """Best-effort insert/update payment record (table may not exist)."""
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "task_id": task_id,
        "executor_id": executor_id,
        "submission_id": submission_id,
        "type": "release",
        "payment_type": "full_release",
        "status": "confirmed",
        "tx_hash": tx_hash,
        "transaction_hash": tx_hash,
        "amount_usdc": worker_payout,
        "fee_usdc": fee,
        "escrow_id": escrow_id,
        "network": "base",
        "to_address": worker_address,
        "settlement_method": "facilitator_retry",
        "note": "Settled via payment retry job",
        "created_at": now,
    }
    try:
        client.table("payments").insert(record).execute()
    except Exception:
        pass  # Table may not exist


async def run_auto_payment_loop() -> None:
    """
    Background loop that retries settlement for orphaned submissions.

    Queries submissions where agent_verdict IN ('accepted', 'approved')
    but payment_tx IS NULL, then attempts settlement via the x402 SDK.

    Only retries auth-based settlement for 'preauth' mode. Other modes
    use mechanisms where the EIP-3009 nonce is already consumed or no
    auth header exists.
    """
    logger.info(
        "[payment-retry] Payment retry job started (interval=%ds, batch=%d, max_retries=%d)",
        RETRY_INTERVAL,
        MAX_BATCH,
        MAX_RETRIES_PER_SUBMISSION,
    )

    from supabase_client import get_client

    # Wait a bit on startup to let other services initialize
    await asyncio.sleep(10)

    # Verify submissions table is accessible
    try:
        client = get_client()
        client.table("submissions").select("id").limit(1).execute()
    except Exception as exc:
        logger.warning("[payment-retry] Cannot access submissions table: %s", exc)
        return

    while True:
        try:
            client = get_client()
            orphaned = await _fetch_orphaned_submissions(client)

            if orphaned:
                logger.info(
                    "[payment-retry] Found %d orphaned submission(s) to retry",
                    len(orphaned),
                )
                settled = 0
                for submission in orphaned:
                    success = await _retry_settlement(client, submission)
                    if success:
                        settled += 1
                    # Small delay between retries to avoid rate limits
                    await asyncio.sleep(2)

                if settled > 0:
                    logger.info(
                        "[payment-retry] Settled %d/%d orphaned submissions",
                        settled,
                        len(orphaned),
                    )
            else:
                logger.debug("[payment-retry] No orphaned submissions")

        except Exception as exc:
            logger.error("[payment-retry] Error in retry loop: %s", exc)

        await asyncio.sleep(RETRY_INTERVAL)
