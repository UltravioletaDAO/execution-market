"""
ERC-8004 Side Effects Processor (Outbox Pattern)

Manages the lifecycle of reputation and identity side effects:
- Enqueue effects into the outbox table on task lifecycle events
- Mark effects as success/failed with tx_hash tracking
- Retrieve pending effects respecting exponential retry schedule

Uses the Supabase client pattern from existing codebase (supabase_client module).
All sync Supabase calls are wrapped in asyncio.to_thread() for non-blocking IO.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Exponential backoff: 1m, 5m, 15m, 1h, 6h, 24h
RETRY_SCHEDULE_MINUTES = [1, 5, 15, 60, 360, 1440]
MAX_ATTEMPTS = 6

VALID_EFFECT_TYPES = {
    "register_worker_identity",
    "rate_worker_from_agent",
    "rate_agent_from_worker",
    "rate_worker_on_rejection",
}

VALID_STATUSES = {"pending", "success", "failed", "skipped"}


async def enqueue_side_effect(
    supabase,
    submission_id: str,
    effect_type: str,
    payload: Optional[dict] = None,
    score: Optional[int] = None,
) -> Optional[dict]:
    """Insert side effect into outbox with dedup (unique submission_id + effect_type).

    Args:
        supabase: Supabase client instance.
        submission_id: UUID of the submission triggering this effect.
        effect_type: One of the valid effect types.
        payload: Effect-specific data (task_id, worker_wallet, agent_id, etc.).
        score: Reputation score 0-100 (for rate_* effects).

    Returns:
        The created record dict, or None if duplicate (dedup).
    """
    if effect_type not in VALID_EFFECT_TYPES:
        raise ValueError(f"Invalid effect_type: {effect_type}")

    if score is not None and not (0 <= score <= 100):
        raise ValueError(f"Score must be 0-100, got {score}")

    row = {
        "submission_id": submission_id,
        "effect_type": effect_type,
        "status": "pending",
        "attempts": 0,
        "payload": payload or {},
    }
    if score is not None:
        row["score"] = score

    try:
        result = await asyncio.to_thread(
            lambda: (
                supabase.table("erc8004_side_effects")
                .upsert(
                    row, on_conflict="submission_id,effect_type", ignore_duplicates=True
                )
                .execute()
            )
        )
        if result.data:
            created = result.data[0]
            _log_side_effect(created, {"action": "enqueued"})
            return created
        return None
    except Exception as e:
        logger.error(
            "Failed to enqueue side effect",
            extra={
                "event": "erc8004_side_effect_enqueue_error",
                "submission_id": submission_id,
                "effect_type": effect_type,
                "error": str(e),
            },
        )
        raise


async def mark_side_effect(
    supabase,
    effect_id: str,
    status: str,
    tx_hash: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Update side effect status, increment attempts, set tx_hash/error.

    Args:
        supabase: Supabase client instance.
        effect_id: UUID of the side effect record.
        status: New status (success, failed, skipped).
        tx_hash: On-chain transaction hash (for successful effects).
        error: Error message (for failed effects).
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    update = {"status": status}
    if tx_hash is not None:
        update["tx_hash"] = tx_hash
    if error is not None:
        update["last_error"] = error

    try:
        # Fetch current to increment attempts
        current = await asyncio.to_thread(
            lambda: (
                supabase.table("erc8004_side_effects")
                .select("attempts, submission_id, effect_type, payload")
                .eq("id", effect_id)
                .single()
                .execute()
            )
        )
        if current.data:
            update["attempts"] = current.data["attempts"] + 1

        await asyncio.to_thread(
            lambda: (
                supabase.table("erc8004_side_effects")
                .update(update)
                .eq("id", effect_id)
                .execute()
            )
        )

        log_data = {
            "action": "marked",
            "effect_id": effect_id,
        }
        if current.data:
            _log_side_effect(
                {
                    **current.data,
                    "status": status,
                    "tx_hash": tx_hash,
                    "last_error": error,
                },
                log_data,
            )
    except Exception as e:
        logger.error(
            "Failed to mark side effect",
            extra={
                "event": "erc8004_side_effect_mark_error",
                "effect_id": effect_id,
                "status": status,
                "error": str(e),
            },
        )
        raise


async def get_pending_effects(
    supabase,
    limit: int = 50,
) -> list[dict]:
    """Get effects ready for retry based on exponential backoff schedule.

    Only returns effects where enough time has passed since the last attempt
    according to RETRY_SCHEDULE_MINUTES, and attempts < MAX_ATTEMPTS.

    Args:
        supabase: Supabase client instance.
        limit: Maximum number of effects to return.

    Returns:
        List of effect dicts ready for processing.
    """
    try:
        result = await asyncio.to_thread(
            lambda: (
                supabase.table("erc8004_side_effects")
                .select("*")
                .in_("status", ["pending", "failed"])
                .lt("attempts", MAX_ATTEMPTS)
                .order("created_at")
                .limit(limit)
                .execute()
            )
        )

        if not result.data:
            return []

        now = datetime.now(timezone.utc)
        ready = []
        for effect in result.data:
            attempts = effect.get("attempts", 0)
            if attempts == 0:
                # Never attempted, ready immediately
                ready.append(effect)
                continue

            # Check if enough time has passed since last update
            updated_at = effect.get("updated_at")
            if updated_at:
                if isinstance(updated_at, str):
                    # Parse ISO timestamp from Supabase
                    updated_at = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                schedule_idx = min(attempts - 1, len(RETRY_SCHEDULE_MINUTES) - 1)
                wait_minutes = RETRY_SCHEDULE_MINUTES[schedule_idx]
                next_retry = updated_at + timedelta(minutes=wait_minutes)
                if now >= next_retry:
                    ready.append(effect)
            else:
                ready.append(effect)

        return ready
    except Exception as e:
        logger.error(
            "Failed to get pending effects",
            extra={
                "event": "erc8004_side_effect_query_error",
                "error": str(e),
            },
        )
        raise


def _log_side_effect(effect: dict, extra: Optional[dict] = None) -> None:
    """Structured log per spec section 6.2."""
    logger.info(
        "erc8004_side_effect",
        extra={
            "event": "erc8004_side_effect",
            "submission_id": effect.get("submission_id"),
            "task_id": effect.get("payload", {}).get("task_id"),
            "effect_type": effect.get("effect_type"),
            "status": effect.get("status"),
            "attempt": effect.get("attempts"),
            "tx_hash": effect.get("tx_hash"),
            "error": effect.get("last_error"),
            **(extra or {}),
        },
    )
