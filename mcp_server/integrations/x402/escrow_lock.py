"""Shared escrow lock — single chokepoint for assignment-time locks.

Every transition published -> accepted of an escrow-mode task must lock
through one of the helpers here:

- ``lock_with_fresh_auth()`` — CANONICAL (sign-on-assignment). The publisher
  signs the EIP-3009 ``ReceiveWithAuthorization`` at assignment time, when the
  worker is known. This is required by the x402r protocol: the EIP-3009 nonce
  is ``AuthCaptureEscrow.getHash(paymentInfo)`` which INCLUDES the receiver,
  so the signature cryptographically commits to the worker. A pre-auth signed
  before the worker is chosen cannot produce a valid on-chain lock.
- ``lock_stored_preauth()`` — legacy Mode B (stored pre-auth from creation,
  receiver filled at assignment). Kept for the existing A2A branch; note the
  on-chain soundness caveat above (EC-15): it only works when the stored
  payload already committed to the final receiver.
- ``create_escrow_marker()`` — publish-time marker row (NO signature) that
  tags a task as escrow-mode so assign/approve/cancel can distinguish it from
  legacy sign-on-approval tasks.

Extracted from the Mode B branch of ``api/routers/tasks.py`` (assign endpoint)
so that REST assign, MCP ``em_assign_task``, MCP ``em_accept_agent_task`` and
the H2A assign endpoint share one implementation instead of drifting copies.

The helpers perform the full success-side effects (escrows row update,
``tasks.escrow_tx``, audit event, release-capable ``payment_info`` metadata).
They do NOT roll back the assignment on failure — each caller decides how to
undo its own state transition.
"""

import json
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

import supabase_client as db

logger = logging.getLogger(__name__)

# Escrow-mode marker written at publish time (no signature involved).
SIGN_ON_ASSIGNMENT = "sign_on_assignment"


async def create_escrow_marker(
    task_id: str,
    bounty_usd: Any,
    network: str,
    payer_wallet: str,
) -> Dict[str, Any]:
    """Insert the publish-time ``escrows`` marker row for an escrow-mode task.

    status='pending_assignment' with escrow_timing='sign_on_assignment' and NO
    ``preauth_signature``: funds stay in the publisher's wallet and the signed
    authorization arrives later, at assignment (see ``lock_with_fresh_auth``).
    """
    client = db.get_client()
    result = (
        client.table("escrows")
        .insert(
            {
                "task_id": task_id,
                "status": "pending_assignment",
                "total_amount_usdc": float(bounty_usd),
                "metadata": {
                    "payment_mode": "fase2",
                    "escrow_mode": "direct_release",
                    "escrow_timing": SIGN_ON_ASSIGNMENT,
                    "network": network,
                    "payer": (payer_wallet or "").lower(),
                },
            }
        )
        .execute()
    )
    row = (result.data or [{}])[0]
    logger.info(
        "Escrow marker created (sign_on_assignment): task=%s, network=%s",
        task_id,
        network,
    )
    return row


def _payment_info_to_metadata(pi: Dict[str, Any], payer_wallet: str) -> Dict[str, Any]:
    """Convert a signed payload's camelCase paymentInfo into the snake_case
    ``payment_info`` metadata shape that ``_reconstruct_fase2_state`` needs
    for release/refund."""
    return {
        "mode": "fase2",
        "escrow_mode": "direct_release",
        "payer": (payer_wallet or "").lower(),
        "operator": pi.get("operator"),
        "receiver": pi.get("receiver"),
        "token": pi.get("token"),
        "max_amount": int(pi.get("maxAmount", 0)),
        "pre_approval_expiry": int(pi.get("preApprovalExpiry", 0)),
        "authorization_expiry": int(pi.get("authorizationExpiry", 0)),
        "refund_expiry": int(pi.get("refundExpiry", 0)),
        "min_fee_bps": int(pi.get("minFeeBps", 0)),
        "max_fee_bps": int(pi.get("maxFeeBps", 0)),
        "fee_receiver": pi.get("feeReceiver"),
        "salt": pi.get("salt"),
    }


async def lock_with_fresh_auth(
    task_id: str,
    task: Dict[str, Any],
    worker_wallet: Optional[str],
    raw_auth: str,
    dispatcher: Any,
    expected_payer: str,
) -> Dict[str, Any]:
    """Lock escrow with an authorization signed AT assignment (canonical path).

    The publisher signed the EIP-3009 ``ReceiveWithAuthorization`` knowing the
    worker: ``paymentInfo.receiver`` MUST equal ``worker_wallet`` (the nonce =
    ``getHash(paymentInfo)`` commits to it; any mismatch reverts on-chain).

    Args:
        task_id: Task UUID.
        task: Task row (needs ``payment_network`` and ``bounty_usd``).
        worker_wallet: Executor wallet address (escrow receiver).
        raw_auth: Raw X-Payment-Auth header value (JSON string).
        dispatcher: PaymentDispatcher instance (fase2).
        expected_payer: Wallet that must have signed (publisher wallet).

    Returns:
        Same contract as ``lock_stored_preauth``:
        ``{"status": "locked", "escrow_tx", "network"}`` |
        ``{"status": "invalid_auth", "error"}`` (validation failed — caller
        maps to HTTP 400) |
        ``{"status": "lock_failed", "error"}`` (Facilitator refused — caller
        rolls back, HTTP 402) |
        ``{"status": "error", "error"}`` (unexpected exception).
    """
    if not worker_wallet:
        return {"status": "invalid_auth", "error": "Worker has no wallet address"}
    if not dispatcher:
        return {"status": "error", "error": "Payment dispatcher unavailable"}

    network = task.get("payment_network") or "base"
    bounty = Decimal(str(task.get("bounty_usd", 0)))

    try:
        parsed = dispatcher.validate_agent_preauth(
            raw_auth,
            network=network,
            expected_payer=expected_payer,
            expected_amount_atomic=str(int(bounty * 1_000_000)),
        )
    except ValueError as ve:
        return {"status": "invalid_auth", "error": str(ve)}

    # On-chain soundness gate: the signed paymentInfo must already commit to
    # this worker (nonce = getHash(paymentInfo) includes the receiver).
    pi = (parsed.get("payload") or {}).get("paymentInfo") or {}
    signed_receiver = (pi.get("receiver") or "").lower()
    if signed_receiver != worker_wallet.lower():
        return {
            "status": "invalid_auth",
            "error": (
                "paymentInfo.receiver does not match the assigned worker "
                f"({signed_receiver or 'empty'} != {worker_wallet.lower()}). "
                "The escrow authorization must be signed for the chosen worker."
            ),
        }

    try:
        lock_result = await dispatcher.relay_agent_auth_to_facilitator(
            parsed,
            worker_address=worker_wallet,
            network=network,
        )
        if not lock_result.get("success"):
            return {
                "status": "lock_failed",
                "error": lock_result.get("error", "Lock failed"),
            }

        escrow_tx = lock_result.get("tx_hash")
        payer = expected_payer or pi.get("payer") or ""
        metadata = {
            "payment_mode": "fase2",
            "escrow_mode": "direct_release",
            "escrow_timing": SIGN_ON_ASSIGNMENT,
            "agent_signed": True,
            "payer": payer.lower(),
            "agent_address": payer.lower(),
            "worker_address": worker_wallet,
            "lock_tx": escrow_tx,
            "network": network,
            "payment_info": _payment_info_to_metadata(pi, payer),
        }

        client = db.get_client()
        upd = (
            client.table("escrows")
            .update(
                {
                    "status": "deposited",
                    "funding_tx": escrow_tx,
                    "metadata": metadata,
                }
            )
            .eq("task_id", task_id)
            .eq("status", "pending_assignment")
            .execute()
        )
        if not (upd.data or []):
            # No marker row (e.g. caller without publish-time marker) — insert.
            client.table("escrows").insert(
                {
                    "task_id": task_id,
                    "status": "deposited",
                    "total_amount_usdc": float(bounty),
                    "funding_tx": escrow_tx,
                    "metadata": metadata,
                }
            ).execute()

        await db.update_task(task_id, {"escrow_tx": escrow_tx})

        from audit import audit_log

        audit_log(
            "escrow_locked",
            task_id=task_id,
            tx_hash=escrow_tx,
            amount_usd=float(bounty),
            escrow_contract="sign_on_assignment",
        )

        logger.info(
            "Fresh-auth escrow locked at assignment: task=%s, worker=%s, tx=%s",
            task_id,
            worker_wallet[:10] + "...",
            escrow_tx,
        )
        return {"status": "locked", "escrow_tx": escrow_tx, "network": network}

    except Exception as e:
        logger.error(
            "lock_with_fresh_auth: unexpected error for task %s: %s", task_id, e
        )
        return {"status": "error", "error": str(e)}


async def get_escrow_marker(task_id: str) -> Optional[Dict[str, Any]]:
    """Return the pending_assignment escrows row for a task, or None.

    Used by assign/accept paths to decide: escrow-mode task (row exists) vs
    legacy task (no row -> drain through the old behavior).
    """
    try:
        client = db.get_client()
        result = (
            client.table("escrows")
            .select("id, status, metadata")
            .eq("task_id", task_id)
            .eq("status", "pending_assignment")
            .limit(1)
            .execute()
        )
        # isinstance guard is load-bearing: mocked DB clients return truthy
        # MagicMocks for .data — only a real non-empty list counts as a marker.
        data = getattr(result, "data", None)
        if not isinstance(data, list) or not data:
            return None
        return data[0]
    except Exception as e:
        logger.warning("get_escrow_marker failed for task %s: %s", task_id, e)
        return None


async def lock_stored_preauth(
    task_id: str,
    task: Dict[str, Any],
    worker_wallet: Optional[str],
    dispatcher: Any,
) -> Dict[str, Any]:
    """Execute a stored pre-auth (Mode B) for an assignment, if one exists.

    Args:
        task_id: Task UUID.
        task: Task row (needs ``payment_network`` and ``bounty_usd``).
        worker_wallet: Executor wallet address (escrow receiver).
        dispatcher: PaymentDispatcher instance (fase2).

    Returns:
        One of:
        - ``{"status": "locked", "escrow_tx": str, "network": str}`` — funds
          locked on-chain; escrows row updated to 'deposited', tasks.escrow_tx
          set, 'escrow_locked' audit event emitted.
        - ``{"status": "no_preauth"}`` — no pending_assignment escrow row or
          no stored signature; caller falls through to its next strategy.
        - ``{"status": "lock_failed", "error": str}`` — Facilitator relay
          returned failure; caller must roll back its assignment.
        - ``{"status": "error", "error": str}`` — unexpected exception during
          lookup/relay/update; logged at debug, caller falls through
          (mirrors the historical swallow-and-continue behavior).
    """
    if not (worker_wallet and dispatcher):
        return {"status": "no_preauth"}

    try:
        client = db.get_client()
        esc_row = (
            client.table("escrows")
            .select("metadata")
            .eq("task_id", task_id)
            .eq("status", "pending_assignment")
            .limit(1)
            .execute()
        )
        if not esc_row.data:
            return {"status": "no_preauth"}

        esc_meta = esc_row.data[0].get("metadata") or {}
        stored_preauth = esc_meta.get("preauth_signature")
        if not stored_preauth:
            return {"status": "no_preauth"}

        network = task.get("payment_network") or esc_meta.get("network", "base")
        lock_result = await dispatcher.relay_agent_auth_to_facilitator(
            json.loads(stored_preauth),
            worker_address=worker_wallet,
            network=network,
        )
        if not lock_result.get("success"):
            return {
                "status": "lock_failed",
                "error": lock_result.get("error", "Lock failed"),
            }

        escrow_tx = lock_result.get("tx_hash")
        client.table("escrows").update(
            {
                "status": "deposited",
                "funding_tx": escrow_tx,
                "metadata": {
                    **esc_meta,
                    "escrow_timing": "lock_on_assignment",
                    "worker_address": worker_wallet,
                    "lock_tx": escrow_tx,
                },
            }
        ).eq("task_id", task_id).execute()

        await db.update_task(task_id, {"escrow_tx": escrow_tx})

        from audit import audit_log

        audit_log(
            "escrow_locked",
            task_id=task_id,
            tx_hash=escrow_tx,
            amount_usd=float(task.get("bounty_usd", 0)),
            escrow_contract="preauth_deferred",
        )

        logger.info(
            "Stored pre-auth executed at assignment: task=%s, worker=%s, tx=%s",
            task_id,
            worker_wallet[:10] + "...",
            escrow_tx,
        )
        return {"status": "locked", "escrow_tx": escrow_tx, "network": network}

    except Exception as e:
        logger.debug(
            "lock_stored_preauth: no stored pre-auth executed for task %s: %s",
            task_id,
            e,
        )
        return {"status": "error", "error": str(e)}
