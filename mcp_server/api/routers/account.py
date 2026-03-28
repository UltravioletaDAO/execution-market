"""
Account management endpoints: deletion and data export.

Required for Apple App Store (guideline 5.1.1) and GDPR compliance.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

import supabase_client as db

from ..auth import verify_worker_auth, WorkerAuth

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
