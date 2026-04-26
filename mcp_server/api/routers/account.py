"""
Account management endpoints: deletion, data export, and wallet change.

Required for Apple App Store (guideline 5.1.1) and GDPR compliance.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

import supabase_client as db

from ..auth import verify_worker_auth, WorkerAuth
from ._models import UpdateWalletRequest
from utils.pii import truncate_wallet

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Account"])


@router.delete(
    "/account",
    status_code=200,
    summary="Delete account",
    description=(
        "Anonymize the current user's account. Nulls out personal data "
        "(display_name, bio, avatar_url, email, wallet_address) and removes "
        "block records. Tasks and submissions are kept anonymized for audit."
    ),
    tags=["Account"],
)
async def delete_account(
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
):
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to delete account"
        )

    executor_id = worker_auth.executor_id

    try:
        client = db.get_client()

        # Anonymize executor record
        client.table("executors").update(
            {
                "display_name": "[deleted]",
                "bio": None,
                "avatar_url": None,
                "email": None,
                "wallet_address": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", executor_id).execute()

        # Remove block records (both directions)
        client.table("blocked_users").delete().eq("user_id", executor_id).execute()
        client.table("blocked_users").delete().eq(
            "blocked_user_id", executor_id
        ).execute()

        logger.info("Account anonymized: executor=%s", executor_id[:8])

        return {"message": "Account deleted and personal data anonymized"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting account %s: %s", executor_id[:8], e)
        raise HTTPException(status_code=500, detail="Internal error deleting account")


@router.get(
    "/account/export",
    summary="Export account data",
    description=(
        "Export all user data as JSON (GDPR Article 20 - Right to data portability). "
        "Returns executor profile, tasks, submissions, and reports."
    ),
    tags=["Account"],
)
async def export_account_data(
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
):
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to export data"
        )

    executor_id = worker_auth.executor_id

    try:
        client = db.get_client()

        # Fetch executor profile
        profile_result = (
            client.table("executors")
            .select("*")
            .eq("id", executor_id)
            .single()
            .execute()
        )

        # Fetch submissions by this executor
        submissions_result = (
            client.table("submissions")
            .select("*")
            .eq("executor_id", executor_id)
            .execute()
        )

        # Fetch task applications
        applications_result = (
            client.table("task_applications")
            .select("*")
            .eq("executor_id", executor_id)
            .execute()
        )

        # Fetch reports filed by this user
        reports_result = (
            client.table("reports").select("*").eq("reporter_id", executor_id).execute()
        )

        # Fetch blocked users
        blocked_result = (
            client.table("blocked_users")
            .select("*")
            .eq("user_id", executor_id)
            .execute()
        )

        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "executor_id": executor_id,
            "profile": profile_result.data if profile_result.data else None,
            "submissions": submissions_result.data or [],
            "applications": applications_result.data or [],
            "reports": reports_result.data or [],
            "blocked_users": blocked_result.data or [],
        }

        logger.info("Account data exported: executor=%s", executor_id[:8])

        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f'attachment; filename="account-export-{executor_id[:8]}.json"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exporting account %s: %s", executor_id[:8], e)
        raise HTTPException(
            status_code=500, detail="Internal error exporting account data"
        )


# Statuses where the worker still owns an in-flight escrow lock pointing at
# their CURRENT wallet_address. Changing the wallet during these states would
# orphan the payout, since the on-chain receiver is locked at assignment time
# but the off-chain settlement reads executor.wallet_address. Block the change
# until the worker either submits, gets paid, or releases the assignment.
_WALLET_CHANGE_BLOCKING_STATUSES = ["accepted", "in_progress", "submitted", "verifying"]

# Lifetime of the signed challenge before it is considered replay material.
# 10 minutes is generous enough for slow signers (hardware wallets) but tight
# enough that a leaked signature can't sit in someone's clipboard for hours.
_WALLET_CHALLENGE_MAX_AGE_SECONDS = 600
_WALLET_CHALLENGE_FUTURE_SKEW_SECONDS = 60


@router.patch(
    "/account/wallet",
    status_code=200,
    summary="Change wallet address",
    description=(
        "Change the executor's wallet address. The new wallet must sign a "
        "challenge message to prove ownership. The challenge MUST be:\n\n"
        "```\n"
        "Execution Market: change wallet to <new_wallet> for executor <executor_id> at <ISO8601 UTC>\n"
        "```\n\n"
        "Timestamp must be within the last 10 minutes. The change is rejected "
        "if the executor has any in-flight task assignments (accepted, "
        "in_progress, submitted, verifying), to avoid losing escrow payouts. "
        "ERC-8004 identity is automatically re-registered on the next task "
        "application via the gasless Facilitator path."
    ),
    tags=["Account"],
)
async def update_wallet_address(
    raw_request: Request,
    request: UpdateWalletRequest,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
):
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to change wallet"
        )

    executor_id = worker_auth.executor_id
    new_wallet = request.new_wallet_address.lower()

    # 1. Verify signature recovers to the new wallet (proves ownership).
    try:
        from eth_account.messages import encode_defunct
        from eth_account import Account
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Signature verification unavailable on this server",
        )

    try:
        encoded = encode_defunct(text=request.message)
        recovered = Account.recover_message(
            encoded, signature=request.signature
        ).lower()
    except Exception as e:
        logger.warning(
            "SECURITY_AUDIT action=wallet_change.signature_decode_failed "
            "executor=%s error=%s",
            executor_id[:8],
            type(e).__name__,
        )
        raise HTTPException(status_code=400, detail="Invalid signature format")

    if recovered != new_wallet:
        logger.warning(
            "SECURITY_AUDIT action=wallet_change.signature_mismatch "
            "executor=%s recovered=%s expected=%s",
            executor_id[:8],
            truncate_wallet(recovered),
            truncate_wallet(new_wallet),
        )
        raise HTTPException(
            status_code=403,
            detail="Signature does not match the new wallet address",
        )

    # 2. Validate message format and freshness (replay protection).
    expected_prefix = (
        f"Execution Market: change wallet to {new_wallet} "
        f"for executor {executor_id} at "
    )
    if not request.message.startswith(expected_prefix):
        raise HTTPException(
            status_code=400,
            detail="Challenge message format does not match expected schema",
        )
    ts_raw = request.message[len(expected_prefix) :].strip()
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid timestamp in challenge message"
        )
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    if age > _WALLET_CHALLENGE_MAX_AGE_SECONDS:
        raise HTTPException(
            status_code=400,
            detail="Challenge expired — sign a fresh message and retry",
        )
    if age < -_WALLET_CHALLENGE_FUTURE_SKEW_SECONDS:
        raise HTTPException(
            status_code=400, detail="Challenge timestamp is in the future"
        )

    client = db.get_client()

    # 3. Read current state. Treat missing executor as 404 to avoid leaking
    # JWT validity vs. row existence.
    current_row = (
        client.table("executors")
        .select("id, wallet_address")
        .eq("id", executor_id)
        .limit(1)
        .execute()
    )
    if not current_row.data:
        raise HTTPException(status_code=404, detail="Executor profile not found")

    current_wallet = (current_row.data[0].get("wallet_address") or "").lower()
    if current_wallet == new_wallet:
        # No-op: idempotent return so the UI can recover from a partial flow.
        return {
            "message": "Wallet is already set to that address",
            "wallet_address": new_wallet,
            "executor_id": executor_id,
            "changed": False,
        }

    # 4. Uniqueness — another executor cannot already own this wallet.
    other = (
        client.table("executors")
        .select("id")
        .eq("wallet_address", new_wallet)
        .neq("id", executor_id)
        .limit(1)
        .execute()
    )
    if other.data:
        raise HTTPException(
            status_code=409,
            detail="This wallet is already linked to another executor profile",
        )

    # 5. Block change while in-flight assignments exist. We don't want to
    # change the off-chain receiver while the on-chain receiver is still the
    # old wallet — the worker would lose the payout.
    blocking = (
        client.table("tasks")
        .select("id, status")
        .eq("executor_id", executor_id)
        .in_("status", _WALLET_CHANGE_BLOCKING_STATUSES)
        .limit(1)
        .execute()
    )
    if blocking.data:
        raise HTTPException(
            status_code=409,
            detail=(
                "You have an active task assignment. Finish, cancel, or "
                "release it before changing your wallet — the new wallet "
                "would not be able to claim the locked escrow."
            ),
        )

    # 6. Apply the change. Clear ERC-8004 cache + ENS so they re-resolve from
    # the new wallet on next interaction.
    now = datetime.now(timezone.utc).isoformat()
    client.table("executors").update(
        {
            "wallet_address": new_wallet,
            "erc8004_agent_id": None,
            "ens_name": None,
            "ens_avatar": None,
            "ens_resolved_at": None,
            "updated_at": now,
        }
    ).eq("id", executor_id).execute()

    logger.info(
        "Wallet changed: executor=%s old=%s new=%s",
        executor_id[:8],
        truncate_wallet(current_wallet),
        truncate_wallet(new_wallet),
    )

    return {
        "message": "Wallet updated. Future task rewards will be sent here.",
        "wallet_address": new_wallet,
        "previous_wallet_address": current_wallet or None,
        "executor_id": executor_id,
        "changed": True,
    }
