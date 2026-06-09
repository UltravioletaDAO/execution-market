"""Task ↔ MPP channel lifecycle binding (Phase 2.5.1).

The Visión for the Solana demo (Master Plan §"Lifecycle binding") inverts
the usual control flow: **the channel close is the source of truth, and
the task COMPLETED state is the consequence**. That matters because pay.sh
is the only thing that knows whether `settleAndFinalize` actually landed
on-chain — EM has no path to verify it independently without indexing
Solana itself, which we explicitly don't do (D-21).

State transitions handled here:

  on_task_assigned(task_id, channel_id, cap_usdc, payer, payee)
      → upsert task_channel_bindings row (status=open)
      → does NOT change the task row (task stays ACCEPTED — the channel
        opens lazily on the worker's first request to pay.sh).

  on_session_open(channel_id, task_id?)
      → upsert binding (backfills task_id if pay.sh emitted channel_id
        without the X-EM-Task-Id header — see Phase 2.4 middleware).

  on_voucher_accepted(channel_id, cumulative_uusdc, voucher_index)
      → updates accepted_uusdc + voucher_count on the binding row.
      → does NOT change the task — vouchers are a payment progress signal,
        not a workflow signal.

  on_session_close(channel_id)
      → marks binding.status=draining. Settlement hasn't confirmed yet.

  on_settlement_complete(channel_id, settlement_tx_hash, refund_uusdc)
      → marks binding.status=settled + records tx hash + refund.
      → **transitions the task to COMPLETED**. Idempotent: if the task is
        already COMPLETED with the same tx_hash, no-op. If a different
        tx_hash arrives for an already-settled binding, log and refuse
        (that's the "double-settle" defense from the master plan).

  on_session_error(channel_id, error_message)
      → marks binding.status=errored.
      → does NOT auto-fail the task — pay.sh may recover, and a settlement
        event can still arrive after an error. Audit the binding manually.

Idempotency: every transition method tolerates being called twice for
the same input. The taxímetro relay (api/routers/taximetro.py) does NOT
filter duplicate SSE events — pay.sh occasionally re-emits across
reconnects — so this module has to be the dedupe layer.

Threading: all DB calls go through Supabase's sync client; we wrap calls
in asyncio.to_thread when invoked from async handlers (the taxímetro
relay does this implicitly via the `asyncio.create_task(...)` tee in
api/routers/taximetro.py:_persist_event).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Task statuses we care about — match the values used in api/routes.py /
# tools/core_tools.py. Kept as string literals to avoid pulling the full
# models.TaskStatus enum (which lives in a different layer).
TASK_STATUS_ACCEPTED = "accepted"
TASK_STATUS_IN_PROGRESS = "in_progress"
TASK_STATUS_VERIFYING = "verifying"
TASK_STATUS_COMPLETED = "completed"


def _get_db():
    """Lazy supabase getter — keeps test imports cheap when the real
    client isn't available."""
    import supabase_client as db

    return db.get_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uusdc_to_usdc(uusdc: Optional[int]) -> Optional[Decimal]:
    """Convert 1e6 micro-USDC → Decimal USDC. None passes through."""
    if uusdc is None:
        return None
    return (Decimal(uusdc) / Decimal(1_000_000)).quantize(Decimal("0.000001"))


def _lookup_binding(channel_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recent binding row for a channel_id, or None."""
    try:
        resp = (
            _get_db()
            .table("task_channel_bindings")
            .select("*")
            .eq("channel_id", channel_id)
            .order("opened_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.warning("lookup_binding channel=%s failed: %s", channel_id, e)
        return None


def _update_binding_status(
    channel_id: str,
    updates: Dict[str, Any],
) -> bool:
    """Apply a partial update to the binding row. Returns False on failure.

    `updates` is merged as-is — caller is responsible for matching column
    names. Never log the full updates dict (may contain payer/payee
    base58 addresses; those are not secrets but we keep audit lean).
    """
    try:
        _get_db().table("task_channel_bindings").update(updates).eq(
            "channel_id", channel_id
        ).execute()
        return True
    except Exception as e:
        logger.warning(
            "update_binding channel=%s fields=%s failed: %s",
            channel_id,
            sorted(updates.keys()),
            e,
        )
        return False


def _update_task_status(
    task_id: str, status: str, extra: Optional[Dict[str, Any]] = None
) -> bool:
    """Transition a task to `status`. Idempotent at the SQL layer."""
    try:
        update = {"status": status}
        if extra:
            update.update(extra)
        _get_db().table("tasks").update(update).eq("id", task_id).execute()
        return True
    except Exception as e:
        logger.warning("update_task task=%s status=%s failed: %s", task_id, status, e)
        return False


# ---------------------------------------------------------------------------
# Public transitions
# ---------------------------------------------------------------------------


def on_task_assigned(
    *,
    task_id: str,
    channel_id: str,
    payer: str,
    payee: str,
    cap_usdc: Decimal,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Bind a task to a pay.sh channel at assignment time.

    Idempotent. Uses the upsert_task_channel_binding SQL function
    (migration 108) so re-binding the same channel_id is a no-op and
    backfilling NULL fields works.

    Returns the binding row UUID on success, None on failure (caller
    treats failure as non-blocking — the channel can still open on
    pay.sh's side even if our mirror is offline).
    """
    try:
        resp = (
            _get_db()
            .rpc(
                "upsert_task_channel_binding",
                {
                    "p_channel_id": channel_id,
                    "p_task_id": task_id,
                    "p_payer": payer,
                    "p_payee": payee,
                    "p_cap_usdc": float(cap_usdc),
                    "p_metadata": metadata or {},
                },
            )
            .execute()
        )
        return resp.data if isinstance(resp.data, str) else None
    except Exception as e:
        logger.warning(
            "on_task_assigned task=%s channel=%s failed: %s", task_id, channel_id, e
        )
        return None


def on_session_open(
    *,
    channel_id: str,
    task_id: Optional[str] = None,
    payer: Optional[str] = None,
    payee: Optional[str] = None,
    cap_usdc: Optional[Decimal] = None,
) -> None:
    """Handle pay.sh's `session_open` SSE event.

    When the SSE event arrives, pay.sh has already locked the cap deposit
    on-chain. We just record the binding. task_id may be missing if the
    middleware (Phase 2.4) didn't capture the X-EM-Task-Id header — the
    SQL function backfills via COALESCE so a later call with task_id will
    fill it in.
    """
    try:
        _get_db().rpc(
            "upsert_task_channel_binding",
            {
                "p_channel_id": channel_id,
                "p_task_id": task_id,
                "p_payer": payer,
                "p_payee": payee,
                "p_cap_usdc": float(cap_usdc) if cap_usdc is not None else None,
                "p_metadata": {"opened_via": "sse_session_open"},
            },
        ).execute()
    except Exception as e:
        # SSE handlers must never raise — pay.sh is the source of truth.
        logger.warning("on_session_open channel=%s failed: %s", channel_id, e)


def on_voucher_accepted(
    *,
    channel_id: str,
    cumulative_uusdc: int,
    voucher_index: Optional[int] = None,
) -> None:
    """Update the cumulative accepted value on the binding row.

    No task state change — vouchers are continuous, the task is binary.
    accepted_uusdc only increases (cumulative semantics in MPP).
    """
    updates: Dict[str, Any] = {"accepted_uusdc": cumulative_uusdc}
    if voucher_index is not None:
        updates["voucher_count"] = voucher_index
    _update_binding_status(channel_id, updates)


def on_session_close(*, channel_id: str) -> None:
    """Mark the binding as draining. Settlement still pending."""
    binding = _lookup_binding(channel_id)
    if binding and binding.get("status") in ("settled", "expired"):
        # Already past draining — pay.sh occasionally re-emits close after
        # settlement-complete. Don't regress the status.
        return
    _update_binding_status(channel_id, {"status": "draining"})


def on_settlement_complete(
    *,
    channel_id: str,
    settlement_tx_hash: str,
    refund_uusdc: Optional[int] = None,
    final_cumulative_uusdc: Optional[int] = None,
) -> bool:
    """Mark binding settled + transition the bound task to COMPLETED.

    Returns True on the transition that actually happened (first time we
    see this settlement for this channel). Returns False if:
      - binding doesn't exist (unbound channel — log + ignore)
      - already settled with the SAME tx_hash (idempotent no-op)
      - already settled with a DIFFERENT tx_hash (double-settle defense
        — log loudly, return False, never overwrite)

    This is the only place where a task transitions to COMPLETED on the
    Solana payment path. Approval flow on EVM uses release_payment(), but
    on Solana the channel close IS the approval.
    """
    binding = _lookup_binding(channel_id)
    if not binding:
        logger.warning(
            "settlement_complete for unbound channel=%s tx=%s — pay.sh ahead of EM mirror",
            channel_id,
            settlement_tx_hash,
        )
        return False

    existing_tx = binding.get("settlement_tx_hash")
    if existing_tx and existing_tx != settlement_tx_hash:
        # Double-settle defense. Don't overwrite — keep the first one and
        # flag for audit. This should be impossible per pay.sh semantics
        # (settleAndFinalize is atomic), but the SSE relay may dedupe
        # incorrectly across reconnects.
        logger.error(
            "DOUBLE-SETTLE detected channel=%s existing_tx=%s new_tx=%s — refusing overwrite",
            channel_id,
            existing_tx,
            settlement_tx_hash,
        )
        return False

    if existing_tx == settlement_tx_hash:
        # Same TX seen twice — no-op success.
        return False

    updates: Dict[str, Any] = {
        "status": "settled",
        "settlement_tx_hash": settlement_tx_hash,
        "settled_at": "now()",
    }
    if refund_uusdc is not None:
        updates["refund_uusdc"] = refund_uusdc
    if final_cumulative_uusdc is not None:
        updates["accepted_uusdc"] = final_cumulative_uusdc

    if not _update_binding_status(channel_id, updates):
        return False

    task_id = binding.get("task_id")
    if task_id:
        _update_task_status(
            task_id,
            TASK_STATUS_COMPLETED,
            extra={"settlement_tx_hash": settlement_tx_hash},
        )
    else:
        logger.warning(
            "settlement_complete channel=%s settled but no task_id bound — task not transitioned",
            channel_id,
        )
    return True


def on_session_error(*, channel_id: str, error_message: str) -> None:
    """Record a pay.sh error on the binding. Does NOT fail the task.

    pay.sh may recover (e.g. RPC blip retried). If the error is terminal,
    a `session_close` + `settlement_complete` with refund_uusdc==cap will
    follow naturally. If neither arrives within the human-set timeout,
    operator intervention runs the recovery procedure in the runbook
    (docs/runbooks/payshell-ops.md §"Settlement event never arrived").
    """
    _update_binding_status(
        channel_id,
        {"status": "errored", "metadata": {"last_error": error_message[:500]}},
    )
