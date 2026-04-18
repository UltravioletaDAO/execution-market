"""
Payment Events — audit trail for all payment operations.

Non-blocking: logs warning on failure, never raises.
All payment-related code should call log_payment_event() at each step.

EIP-3009 nonce tracking (Phase 5.1):
    Every signed pre-auth carries a `nonce` (32 random bytes). When callers
    pass ``nonce=...`` and ``token_address=...`` explicitly, both fields are
    promoted into ``metadata`` and the INSERT hits the UNIQUE partial index
    ``idx_payment_events_nonce_unique`` (migration 102). A collision means
    the same authorization was replayed — we treat the 23505 as a signal,
    log an INFO, and return None rather than propagate.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Postgres error code for UNIQUE violation — see
# https://www.postgresql.org/docs/current/errcodes-appendix.html
_PG_UNIQUE_VIOLATION = "23505"


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
    nonce: Optional[str] = None,
    token_address: Optional[str] = None,
) -> Optional[str]:
    """
    Insert a payment event into the audit trail.

    Non-blocking: catches all exceptions, logs warnings, never raises.

    Args:
        task_id: Task UUID
        event_type: One of: verify, store_auth, settle, disburse_worker,
                    disburse_fee, refund, cancel, error,
                    balance_check (fase1), settle_worker_direct (fase1),
                    settle_fee_direct (fase1),
                    escrow_authorize (fase2), escrow_release (fase2),
                    escrow_refund (fase2), distribute_fees (fase2),
                    fee_sweep (admin),
                    reputation_agent_rates_worker, reputation_worker_rates_agent
        status: pending, success, or failed
        tx_hash: On-chain transaction hash (if available)
        from_address: Source wallet address
        to_address: Destination wallet address
        amount_usdc: Amount in USDC (6 decimals)
        network: Payment network (e.g., "base")
        token: Token symbol (default: USDC)
        error: Error message (if failed)
        metadata: Additional context (JSON-serializable)
        nonce: EIP-3009 nonce (hex string, 0x-prefixed). When provided
               together with ``token_address``, the UNIQUE partial index
               on ``payment_events`` will reject duplicate writes —
               we swallow that benignly (Phase 5.1).
        token_address: Stablecoin contract address. Lowercased before
                       storage so index lookups are case-insensitive.

    Returns:
        Event UUID if successful, None on failure or on benign nonce dup.
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

        # Promote nonce + token_address into metadata so the UNIQUE partial
        # index on (metadata->>nonce, metadata->>token_address) can enforce
        # uniqueness at the DB layer (migration 102).
        merged_metadata: Dict[str, Any] = dict(metadata) if metadata else {}
        if nonce:
            merged_metadata["nonce"] = nonce
        if token_address:
            merged_metadata["token_address"] = token_address.lower()
        if merged_metadata:
            record["metadata"] = merged_metadata

        result = client.table("payment_events").insert(record).execute()
        rows = result.data or []
        event_id = rows[0]["id"] if rows else None

        logger.debug(
            "payment_event: task=%s type=%s status=%s tx=%s amount=%s nonce=%s",
            task_id[:8] if task_id else "?",
            event_type,
            status,
            (tx_hash or "")[:16],
            amount_usdc,
            (nonce or "")[:12],
        )
        return event_id

    except Exception as e:
        # Treat UNIQUE-constraint failure on (nonce, token_address) as a
        # signal, not an error: the caller re-presented the same signed
        # authorization (retry, reorg, replay). We log an INFO and return
        # None so the caller keeps the original audit row.
        msg = str(e)
        if nonce and (_PG_UNIQUE_VIOLATION in msg or "duplicate key" in msg.lower()):
            logger.info(
                "payment_event: skipping duplicate nonce=%s token=%s task=%s "
                "(already audited — this is normally a retry)",
                nonce[:12],
                token_address or "?",
                task_id[:8] if task_id else "?",
            )
            return None

        # Non-blocking for all other failures: never let audit logging break
        # payment operations.
        logger.warning(
            "Failed to log payment event (task=%s, type=%s): %s",
            task_id[:8] if task_id else "?",
            event_type,
            e,
        )
        return None
