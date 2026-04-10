"""
Content moderation endpoints: reports and user blocking.

Required for Apple App Store (guideline 1.2) and Google Play UGC policies.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, ConfigDict, Field

import supabase_client as db

from ..auth import (
    verify_worker_auth,
    WorkerAuth,
)
from ..admin import verify_admin_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Moderation"])


# =============================================================================
# MODELS
# =============================================================================


class CreateReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: str = Field(
        ...,
        description="Type of content being reported",
        pattern="^(task|submission|message|user)$",
    )
    target_id: str = Field(
        ..., description="ID of the reported content", min_length=1, max_length=255
    )
    reason_category: str = Field(
        ...,
        description="Category of the report reason",
        pattern="^(spam|abuse|fraud|inappropriate|harassment|other)$",
    )
    reason_text: Optional[str] = Field(
        default=None, description="Additional details", max_length=2000
    )


class ReportResponse(BaseModel):
    id: str
    reporter_id: str
    target_type: str
    target_id: str
    reason_category: str
    reason_text: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None


class UpdateReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        ...,
        description="New report status",
        pattern="^(reviewed|actioned|dismissed)$",
    )
    admin_notes: Optional[str] = Field(
        default=None, description="Admin notes", max_length=5000
    )


class BlockUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocked_user_id: str = Field(
        ..., description="UUID of the user to block", min_length=36, max_length=36
    )


class BlockedUserResponse(BaseModel):
    id: str
    blocked_user_id: str
    created_at: str


# =============================================================================
# REPORT ENDPOINTS
# =============================================================================


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=201,
    summary="Submit a report",
    description="Report content for moderation review. Requires worker authentication.",
    tags=["Moderation"],
)
async def create_report(
    request: CreateReportRequest,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
):
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to submit reports"
        )

    try:
        client = db.get_client()
        result = (
            client.table("reports")
            .insert(
                {
                    "reporter_id": worker_auth.executor_id,
                    "target_type": request.target_type,
                    "target_id": request.target_id,
                    "reason_category": request.reason_category,
                    "reason_text": request.reason_text,
                }
            )
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create report")

        row = result.data[0]
        logger.info(
            "Report created: id=%s type=%s target=%s by=%s",
            row["id"][:8],
            request.target_type,
            request.target_id[:8],
            worker_auth.executor_id[:8],
        )
        return ReportResponse(**row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating report: %s", e)
        raise HTTPException(status_code=500, detail="Internal error creating report")


@router.get(
    "/reports",
    response_model=List[ReportResponse],
    summary="List reports (admin)",
    description="List all reports with pagination. Admin only.",
    tags=["Moderation"],
)
async def list_reports(
    _admin=Depends(verify_admin_key),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        client = db.get_client()
        query = client.table("reports").select("*").order("created_at", desc=True)

        if status:
            query = query.eq("status", status)

        result = query.limit(limit).offset(offset).execute()
        return [ReportResponse(**row) for row in (result.data or [])]

    except Exception as e:
        logger.error("Error listing reports: %s", e)
        raise HTTPException(status_code=500, detail="Internal error listing reports")


@router.patch(
    "/reports/{report_id}",
    response_model=ReportResponse,
    summary="Update report (admin)",
    description="Update report status and add admin notes. Admin only.",
    tags=["Moderation"],
)
async def update_report(
    request: UpdateReportRequest,
    report_id: str = Path(..., description="Report UUID"),
    _admin=Depends(verify_admin_key),
):
    try:
        client = db.get_client()
        update_data = {"status": request.status}
        if request.admin_notes is not None:
            update_data["admin_notes"] = request.admin_notes
        if request.status in ("actioned", "dismissed"):
            from datetime import datetime, timezone

            update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            client.table("reports").update(update_data).eq("id", report_id).execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Report not found")

        logger.info("Report updated: id=%s status=%s", report_id[:8], request.status)
        return ReportResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating report %s: %s", report_id[:8], e)
        raise HTTPException(status_code=500, detail="Internal error updating report")


# =============================================================================
# BLOCK ENDPOINTS
# =============================================================================


@router.post(
    "/users/block",
    response_model=BlockedUserResponse,
    status_code=201,
    summary="Block a user",
    description="Block another user. Requires worker authentication.",
    tags=["Moderation"],
)
async def block_user(
    request: BlockUserRequest,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
):
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to block users"
        )

    if request.blocked_user_id == worker_auth.executor_id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    try:
        client = db.get_client()
        result = (
            client.table("blocked_users")
            .insert(
                {
                    "user_id": worker_auth.executor_id,
                    "blocked_user_id": request.blocked_user_id,
                }
            )
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to block user")

        row = result.data[0]
        logger.info(
            "User blocked: %s blocked %s",
            worker_auth.executor_id[:8],
            request.blocked_user_id[:8],
        )
        return BlockedUserResponse(**row)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
            raise HTTPException(status_code=409, detail="User already blocked")
        logger.error("Error blocking user: %s", e)
        raise HTTPException(status_code=500, detail="Internal error blocking user")


@router.delete(
    "/users/block/{blocked_user_id}",
    status_code=204,
    summary="Unblock a user",
    description="Remove a user block. Requires worker authentication.",
    tags=["Moderation"],
)
async def unblock_user(
    blocked_user_id: str = Path(..., description="UUID of the user to unblock"),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
):
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to unblock users"
        )

    try:
        client = db.get_client()
        result = (
            client.table("blocked_users")
            .delete()
            .eq("user_id", worker_auth.executor_id)
            .eq("blocked_user_id", blocked_user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Block not found")

        logger.info(
            "User unblocked: %s unblocked %s",
            worker_auth.executor_id[:8],
            blocked_user_id[:8],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error unblocking user: %s", e)
        raise HTTPException(status_code=500, detail="Internal error unblocking user")


@router.get(
    "/users/blocked",
    response_model=List[BlockedUserResponse],
    summary="List blocked users",
    description="List all users blocked by the current user. Requires worker authentication.",
    tags=["Moderation"],
)
async def list_blocked_users(
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
):
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to list blocked users"
        )

    try:
        client = db.get_client()
        result = (
            client.table("blocked_users")
            .select("id, blocked_user_id, created_at")
            .eq("user_id", worker_auth.executor_id)
            .order("created_at", desc=True)
            .execute()
        )

        return [BlockedUserResponse(**row) for row in (result.data or [])]

    except Exception as e:
        logger.error("Error listing blocked users: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal error listing blocked users"
        )
