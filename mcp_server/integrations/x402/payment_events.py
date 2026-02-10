"""
Payment Events — audit trail for all payment operations.

Non-blocking: logs warning on failure, never raises.
All payment-related code should call log_payment_event() at each step.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def log_payment_event(
    task_id: str,
    event_type: str,
    *,
    status: str = "pending",
    tx_hash: Optional[str] = None,
    from_address: Optional[str] = None,
    to_address: Optional[str] = None,
    amount_usdc: Optional[Decimal] = None,
    network: Optional[str] = None,
    token: str = "USDC",
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Insert a payment event into the audit trail.

    Non-blocking: catches all exceptions, logs warnings, never raises.

    Args:
        task_id: Task UUID
        event_type: One of: verify, store_auth, settle, disburse_worker,
                    disburse_fee, refund, cancel, error
        status: pending, success, or failed
        tx_hash: On-chain transaction hash (if available)
        from_address: Source wallet address
        to_address: Destination wallet address
        amount_usdc: Amount in USDC (6 decimals)
        network: Payment network (e.g., "base")
        token: Token symbol (default: USDC)
        error: Error message (if failed)
        metadata: Additional context (JSON-serializable)

    Returns:
        Event UUID if successful, None on failure.
    """
    try:
        import supabase_client as db

        client = db.get_client()

        record: Dict[str, Any] = {
            "task_id": task_id,
            "event_type": event_type,
            "status": status,
            "token": token,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if tx_hash:
            record["tx_hash"] = tx_hash
        if from_address:
            record["from_address"] = from_address
        if to_address:
            record["to_address"] = to_address
        if amount_usdc is not None:
            record["amount_usdc"] = float(amount_usdc)
        if network:
            record["network"] = network
        if error:
            record["error"] = error[:2000]  # Truncate long errors
        if metadata:
            record["metadata"] = metadata

        result = client.table("payment_events").insert(record).execute()
        rows = result.data or []
        event_id = rows[0]["id"] if rows else None

        logger.debug(
            "payment_event: task=%s type=%s status=%s tx=%s amount=%s",
            task_id[:8],
            event_type,
            status,
            (tx_hash or "")[:16],
            amount_usdc,
        )
        return event_id

    except Exception as e:
        # Non-blocking: never let audit logging break payment operations
        logger.warning(
            "Failed to log payment event (task=%s, type=%s): %s",
            task_id[:8] if task_id else "?",
            event_type,
            e,
        )
        return None
