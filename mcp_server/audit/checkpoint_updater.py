"""
Checkpoint Updater — non-blocking lifecycle checkpoint tracking.

Every lifecycle event calls the corresponding mark_* function.
All functions are non-blocking: they catch exceptions and log warnings,
never raising errors that could disrupt business logic.

The checkpoint row is created at task creation via init_checkpoint(),
and subsequent mark_* calls update individual columns.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("em.audit.checkpoints")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _emit_ws_checkpoint(task_id: str, fields: Dict[str, Any]) -> None:
    """Emit a WebSocket CheckpointUpdated event. Non-blocking."""
    try:
        from websocket.events import WebSocketEvent, WebSocketEventType

        # Extract boolean checkpoint keys that are True
        changed = {k: v for k, v in fields.items() if isinstance(v, bool) and v is True}
        if not changed:
            return

        event = WebSocketEvent(
            event_type=WebSocketEventType.CHECKPOINT_UPDATED,
            payload={
                "task_id": task_id,
                "checkpoints": changed,
                "updated_at": fields.get("updated_at", _now()),
            },
            room=f"task:{task_id}",
        )

        from websocket.server import ws_manager

        if ws_manager:
            await ws_manager.broadcast_to_room(f"task:{task_id}", event)
    except Exception:
        pass  # Non-blocking — WS is optional


async def _upsert_checkpoint(task_id: str, fields: Dict[str, Any]) -> bool:
    """Upsert checkpoint fields for a task. Returns True on success."""
    try:
        import supabase_client as db

        client = db.get_client()
        fields["updated_at"] = _now()
        fields["task_id"] = task_id

        client.table("task_lifecycle_checkpoints").upsert(
            fields, on_conflict="task_id"
        ).execute()

        # Emit WS event for real-time grid updates
        await _emit_ws_checkpoint(task_id, fields)

        return True
    except Exception as e:
        logger.warning(
            "Checkpoint update failed (task=%s): %s",
            task_id[:8] if task_id else "?",
            e,
        )
        return False


# ── Initialization ──────────────────────────────────────────────────


async def init_checkpoint(
    task_id: str,
    *,
    skill_version: Optional[str] = None,
    network: Optional[str] = None,
    token: Optional[str] = None,
    bounty_usdc: Optional[float] = None,
) -> bool:
    """Create initial checkpoint row when a task is created."""
    return await _upsert_checkpoint(
        task_id,
        {
            "task_created": True,
            "task_created_at": _now(),
            "skill_version": skill_version,
            "network": network,
            "token": token,
            "bounty_usdc": bounty_usdc,
            "created_at": _now(),
        },
    )


# ── Authentication & Identity ───────────────────────────────────────


async def mark_auth_erc8128(task_id: str) -> bool:
    """Mark that the agent authenticated via ERC-8128 wallet signing."""
    return await _upsert_checkpoint(
        task_id,
        {"auth_erc8128": True, "auth_erc8128_at": _now()},
    )


async def mark_identity_erc8004(task_id: str, agent_id: Optional[str] = None) -> bool:
    """Mark that ERC-8004 identity was verified for the agent."""
    fields: Dict[str, Any] = {
        "identity_erc8004": True,
        "identity_erc8004_at": _now(),
    }
    if agent_id:
        fields["agent_id_resolved"] = str(agent_id)[:20]
    return await _upsert_checkpoint(task_id, fields)


# ── Balance & Payment Auth ──────────────────────────────────────────


async def mark_balance_checked(
    task_id: str, amount_usdc: Optional[float] = None
) -> bool:
    """Mark that the agent's balance was checked and sufficient."""
    fields: Dict[str, Any] = {
        "balance_sufficient": True,
        "balance_checked_at": _now(),
    }
    if amount_usdc is not None:
        fields["balance_amount_usdc"] = float(amount_usdc)
    return await _upsert_checkpoint(task_id, fields)


async def mark_payment_auth(task_id: str) -> bool:
    """Mark that the agent signed payment authorization (EIP-3009 or pre-auth)."""
    return await _upsert_checkpoint(
        task_id,
        {"payment_auth_signed": True, "payment_auth_at": _now()},
    )


# ── Escrow ──────────────────────────────────────────────────────────


async def mark_escrow_locked(task_id: str, tx_hash: Optional[str] = None) -> bool:
    """Mark that escrow has been locked on-chain."""
    fields: Dict[str, Any] = {
        "escrow_locked": True,
        "escrow_locked_at": _now(),
    }
    if tx_hash:
        fields["escrow_tx"] = tx_hash[:66]
    return await _upsert_checkpoint(task_id, fields)


# ── Assignment ──────────────────────────────────────────────────────


async def mark_worker_assigned(
    task_id: str,
    worker_id: Optional[str] = None,
    has_erc8004: bool = False,
) -> bool:
    """Mark that a worker has been assigned to the task."""
    fields: Dict[str, Any] = {
        "worker_assigned": True,
        "worker_assigned_at": _now(),
        "worker_erc8004": has_erc8004,
    }
    if worker_id:
        fields["worker_id"] = worker_id
    return await _upsert_checkpoint(task_id, fields)


# ── Evidence ────────────────────────────────────────────────────────


async def mark_evidence_submitted(task_id: str, evidence_count: int = 1) -> bool:
    """Mark that evidence has been submitted for the task."""
    return await _upsert_checkpoint(
        task_id,
        {
            "evidence_submitted": True,
            "evidence_submitted_at": _now(),
            "evidence_count": evidence_count,
        },
    )


# ── Verification ────────────────────────────────────────────────────


async def mark_ai_verified(task_id: str, verdict: Optional[str] = None) -> bool:
    """Mark that AI verification has been completed."""
    fields: Dict[str, Any] = {
        "ai_verified": True,
        "ai_verified_at": _now(),
    }
    if verdict:
        fields["ai_verdict"] = verdict[:20]
    return await _upsert_checkpoint(task_id, fields)


# ── Approval & Payment ─────────────────────────────────────────────


async def mark_approved(task_id: str) -> bool:
    """Mark that the submission has been approved."""
    return await _upsert_checkpoint(
        task_id,
        {"approved": True, "approved_at": _now()},
    )


async def mark_payment_released(
    task_id: str,
    tx_hash: Optional[str] = None,
    worker_amount: Optional[float] = None,
    fee_amount: Optional[float] = None,
) -> bool:
    """Mark that payment has been released to the worker."""
    fields: Dict[str, Any] = {
        "payment_released": True,
        "payment_released_at": _now(),
    }
    if tx_hash:
        fields["payment_tx"] = tx_hash[:66]
    if worker_amount is not None:
        fields["worker_amount_usdc"] = float(worker_amount)
    if fee_amount is not None:
        fields["fee_amount_usdc"] = float(fee_amount)
    return await _upsert_checkpoint(task_id, fields)


# ── Reputation ──────────────────────────────────────────────────────


async def mark_reputation(task_id: str, direction: str) -> bool:
    """
    Mark a reputation event.

    Args:
        direction: "agent_to_worker" or "worker_to_agent"
    """
    if direction == "agent_to_worker":
        return await _upsert_checkpoint(
            task_id,
            {"agent_rated_worker": True, "agent_rated_worker_at": _now()},
        )
    elif direction == "worker_to_agent":
        return await _upsert_checkpoint(
            task_id,
            {"worker_rated_agent": True, "worker_rated_agent_at": _now()},
        )
    else:
        logger.warning("Unknown reputation direction: %s", direction)
        return False


# ── Fee Distribution ────────────────────────────────────────────────


async def mark_fees_distributed(task_id: str, tx_hash: Optional[str] = None) -> bool:
    """Mark that platform fees have been distributed to treasury."""
    fields: Dict[str, Any] = {
        "fees_distributed": True,
        "fees_distributed_at": _now(),
    }
    if tx_hash:
        fields["fees_tx"] = tx_hash[:66]
    return await _upsert_checkpoint(task_id, fields)


# ── Terminal States ─────────────────────────────────────────────────


async def mark_cancelled(task_id: str) -> bool:
    """Mark that the task has been cancelled."""
    return await _upsert_checkpoint(
        task_id,
        {"cancelled": True, "cancelled_at": _now()},
    )


async def mark_refunded(task_id: str, tx_hash: Optional[str] = None) -> bool:
    """Mark that the escrow has been refunded."""
    fields: Dict[str, Any] = {
        "refunded": True,
        "refunded_at": _now(),
    }
    if tx_hash:
        fields["refund_tx"] = tx_hash[:66]
    return await _upsert_checkpoint(task_id, fields)


async def mark_expired(task_id: str) -> bool:
    """Mark that the task has expired."""
    return await _upsert_checkpoint(
        task_id,
        {"expired": True, "expired_at": _now()},
    )


# ── Query ───────────────────────────────────────────────────────────


async def get_checkpoint(task_id: str) -> Optional[Dict[str, Any]]:
    """Get checkpoint data for a task. Returns None if not found."""
    try:
        import supabase_client as db

        client = db.get_client()
        result = (
            client.table("task_lifecycle_checkpoints")
            .select("*")
            .eq("task_id", task_id)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.warning("Checkpoint query failed (task=%s): %s", task_id[:8], e)
        return None


async def get_checkpoints_batch(
    task_ids: list,
) -> Dict[str, Dict[str, Any]]:
    """Get checkpoints for multiple tasks. Returns {task_id: checkpoint_data}."""
    if not task_ids:
        return {}
    try:
        import supabase_client as db

        client = db.get_client()
        result = (
            client.table("task_lifecycle_checkpoints")
            .select("*")
            .in_("task_id", task_ids)
            .execute()
        )
        rows = result.data or []
        return {row["task_id"]: row for row in rows}
    except Exception as e:
        logger.warning("Batch checkpoint query failed: %s", e)
        return {}
