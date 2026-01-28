"""
REST API Routes for Chamba

Provides HTTP endpoints in addition to MCP tools.
Includes agent endpoints (authenticated) and worker endpoints (public/semi-public).
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, ConfigDict

import supabase_client as db
from models import TaskCategory, EvidenceType, TaskStatus
from verification.ai_review import process_verification, calculate_auto_score
from .auth import (
    verify_api_key,
    verify_api_key_optional,
    APIKeyData,
    verify_agent_owns_task,
    verify_agent_owns_submission
)

# x402 payment verification
try:
    from integrations.x402.sdk_client import (
        verify_x402_payment,
        SDK_AVAILABLE as X402_AVAILABLE,
    )
except ImportError:
    X402_AVAILABLE = False

# Platform configuration
try:
    from config import PlatformConfig
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Default fee (overridden by config system when available)
DEFAULT_PLATFORM_FEE_PERCENT = Decimal("0.08")


async def get_platform_fee_percent() -> Decimal:
    """Get platform fee from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_fee_pct()
        except Exception:
            pass
    return DEFAULT_PLATFORM_FEE_PERCENT


async def get_min_bounty() -> Decimal:
    """Get minimum bounty from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_min_bounty()
        except Exception:
            pass
    return Decimal("0.25")


async def get_max_bounty() -> Decimal:
    """Get maximum bounty from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_max_bounty()
        except Exception:
            pass
    return Decimal("10000.00")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Chamba API"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class CreateTaskRequest(BaseModel):
    """Request model for creating a new task."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(
        ...,
        description="Short, descriptive title for the task",
        min_length=5,
        max_length=255,
        examples=["Verify store is open", "Take photo of product display"]
    )
    instructions: str = Field(
        ...,
        description="Detailed instructions for the human executor",
        min_length=20,
        max_length=5000
    )
    category: TaskCategory = Field(
        ...,
        description="Category of the task"
    )
    bounty_usd: float = Field(
        ...,
        description="Bounty amount in USD",
        gt=0,
        le=10000
    )
    deadline_hours: int = Field(
        ...,
        description="Hours from now until deadline",
        ge=1,
        le=720  # Max 30 days
    )
    evidence_required: List[EvidenceType] = Field(
        ...,
        description="List of required evidence types",
        min_length=1,
        max_length=5
    )
    evidence_optional: Optional[List[EvidenceType]] = Field(
        default=None,
        description="List of optional evidence types",
        max_length=5
    )
    location_hint: Optional[str] = Field(
        default=None,
        description="Human-readable location hint (e.g., 'Mexico City downtown')",
        max_length=255
    )
    location_lat: Optional[float] = Field(
        default=None,
        description="Expected latitude for GPS verification",
        ge=-90,
        le=90
    )
    location_lng: Optional[float] = Field(
        default=None,
        description="Expected longitude for GPS verification",
        ge=-180,
        le=180
    )
    min_reputation: int = Field(
        default=0,
        description="Minimum reputation score required to apply",
        ge=0
    )
    payment_token: str = Field(
        default="USDC",
        description="Payment token symbol",
        max_length=10
    )

    @field_validator("evidence_required")
    @classmethod
    def validate_evidence_unique(cls, v: List[EvidenceType]) -> List[EvidenceType]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate evidence types not allowed")
        return v


class TaskResponse(BaseModel):
    """Response model for task data."""
    id: str
    title: str
    status: str
    category: str
    bounty_usd: float
    deadline: datetime
    created_at: datetime
    agent_id: str
    executor_id: Optional[str] = None
    instructions: Optional[str] = None
    evidence_schema: Optional[Dict] = None
    location_hint: Optional[str] = None
    min_reputation: int = 0


class TaskListResponse(BaseModel):
    """Response model for paginated task list."""
    tasks: List[TaskResponse]
    total: int
    count: int
    offset: int
    has_more: bool


class SubmissionResponse(BaseModel):
    """Response model for submission data."""
    id: str
    task_id: str
    executor_id: str
    status: str
    pre_check_score: Optional[float] = None
    submitted_at: datetime
    evidence: Optional[Dict] = None
    agent_verdict: Optional[str] = None
    agent_notes: Optional[str] = None
    verified_at: Optional[datetime] = None


class SubmissionListResponse(BaseModel):
    """Response model for submission list."""
    submissions: List[SubmissionResponse]
    count: int


class ApprovalRequest(BaseModel):
    """Request model for approving a submission."""
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes about the approval",
        max_length=1000
    )


class RejectionRequest(BaseModel):
    """Request model for rejecting a submission."""
    notes: str = Field(
        ...,
        description="Required reason for rejection",
        min_length=10,
        max_length=1000
    )


class CancelRequest(BaseModel):
    """Request model for cancelling a task."""
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for cancellation",
        max_length=500
    )


class AnalyticsResponse(BaseModel):
    """Response model for agent analytics."""
    totals: Dict[str, Any]
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    average_times: Dict[str, str]
    top_workers: List[Dict]
    period_days: int


class WorkerApplicationRequest(BaseModel):
    """Request model for worker applying to a task."""
    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        min_length=36,
        max_length=36
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional message to the agent",
        max_length=500
    )


class WorkerSubmissionRequest(BaseModel):
    """Request model for worker submitting work."""
    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        min_length=36,
        max_length=36
    )
    evidence: Dict[str, Any] = Field(
        ...,
        description="Evidence dictionary with required fields"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes about the submission",
        max_length=1000
    )


class AvailableTasksResponse(BaseModel):
    """Response model for available tasks (worker view)."""
    tasks: List[Dict[str, Any]]
    count: int
    offset: int
    filters_applied: Dict[str, Any]


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class PublicConfigResponse(BaseModel):
    """Public platform configuration (readable by anyone)."""
    min_bounty_usd: float
    max_bounty_usd: float
    supported_networks: List[str]
    supported_tokens: List[str]
    preferred_network: str


class ConfigUpdateRequest(BaseModel):
    """Request to update a config value (admin only)."""
    value: Any = Field(..., description="New value for the config key")
    reason: Optional[str] = Field(None, description="Reason for the change (for audit)")


# =============================================================================
# CONFIG ENDPOINTS (PUBLIC)
# =============================================================================


@router.get(
    "/config",
    response_model=PublicConfigResponse,
    responses={
        200: {"description": "Public platform configuration"},
    }
)
async def get_public_config() -> PublicConfigResponse:
    """
    Get public platform configuration.

    Returns publicly available configuration like bounty limits,
    supported payment networks, and tokens. Does not expose
    internal settings like fees or feature flags.
    """
    if CONFIG_AVAILABLE:
        try:
            config = await PlatformConfig.get_public_config()
            return PublicConfigResponse(
                min_bounty_usd=float(config.get("min_usd", 0.25)),
                max_bounty_usd=float(config.get("max_usd", 10000.00)),
                supported_networks=config.get("supported_networks", ["base"]),
                supported_tokens=config.get("supported_tokens", ["USDC"]),
                preferred_network=config.get("preferred_network", "base"),
            )
        except Exception as e:
            logger.warning(f"Error loading public config: {e}")

    # Fallback defaults
    return PublicConfigResponse(
        min_bounty_usd=0.25,
        max_bounty_usd=10000.00,
        supported_networks=["base", "ethereum", "polygon", "optimism", "arbitrum"],
        supported_tokens=["USDC", "USDT", "DAI"],
        preferred_network="base",
    )


# =============================================================================
# AGENT ENDPOINTS (AUTHENTICATED)
# =============================================================================


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
    responses={
        201: {"description": "Task created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        402: {"description": "Payment required. Include X-Payment header with x402 payment."},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    }
)
async def create_task(
    http_request: Request,
    request: CreateTaskRequest,
    api_key: APIKeyData = Depends(verify_api_key)
) -> TaskResponse:
    """
    Create a new task.

    Requires authenticated API key AND x402 payment (bounty + 6-8% platform fee).
    The task will be created in 'published' status and visible to workers.

    **Payment**: Include `X-Payment` header with x402 protocol payment.
    Total required = bounty_usd × 1.08 (8% platform fee).

    Example for $10 bounty: Pay $10.80 via x402.
    """
    try:
        # Get configurable platform fee
        platform_fee_pct = await get_platform_fee_percent()
        min_bounty = await get_min_bounty()
        max_bounty = await get_max_bounty()

        # Calculate total payment required (bounty + platform fee)
        bounty = Decimal(str(request.bounty_usd))

        # Validate bounty against config limits
        if bounty < min_bounty:
            raise HTTPException(
                status_code=400,
                detail=f"Bounty ${bounty} is below minimum ${min_bounty}"
            )
        if bounty > max_bounty:
            raise HTTPException(
                status_code=400,
                detail=f"Bounty ${bounty} exceeds maximum ${max_bounty}"
            )

        total_required = bounty * (1 + platform_fee_pct)
        total_required = total_required.quantize(Decimal("0.01"))

        # Verify x402 payment
        if X402_AVAILABLE:
            payment_result = await verify_x402_payment(http_request, total_required)

            if not payment_result.success:
                # Return 402 Payment Required
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment required",
                        "message": f"Task creation requires x402 payment of ${total_required} (bounty ${bounty} + {platform_fee_pct * 100}% platform fee)",
                        "required_amount_usd": str(total_required),
                        "bounty_usd": str(bounty),
                        "platform_fee_percent": str(platform_fee_pct * 100),
                        "platform_fee_usd": str(total_required - bounty),
                        "payment_error": payment_result.error,
                        "x402_info": {
                            "facilitator": "https://facilitator.ultravioletadao.xyz",
                            "networks": ["base", "ethereum", "polygon", "optimism", "arbitrum"],
                            "tokens": ["USDC", "USDT", "DAI"]
                        }
                    },
                    headers={
                        "X-402-Price": str(total_required),
                        "X-402-Currency": "USD",
                        "X-402-Description": f"Create task: {request.title[:50]}",
                    }
                )

            logger.info(
                "x402 payment verified: payer=%s, amount=%.2f, tx=%s",
                payment_result.payer_address,
                payment_result.amount_usd,
                payment_result.tx_hash
            )

        # Calculate deadline
        deadline = datetime.now(timezone.utc) + timedelta(hours=request.deadline_hours)

        # Create task
        task = await db.create_task(
            agent_id=api_key.agent_id,
            title=request.title,
            instructions=request.instructions,
            category=request.category.value,
            bounty_usd=request.bounty_usd,
            deadline=deadline,
            evidence_required=[e.value for e in request.evidence_required],
            evidence_optional=[e.value for e in (request.evidence_optional or [])],
            location_hint=request.location_hint,
            min_reputation=request.min_reputation,
            payment_token=request.payment_token,
        )

        logger.info(
            "Task created: id=%s, agent=%s, bounty=%.2f, paid_via_x402=%s",
            task["id"], api_key.agent_id, request.bounty_usd, X402_AVAILABLE
        )

        return TaskResponse(
            id=task["id"],
            title=task["title"],
            status=task["status"],
            category=task["category"],
            bounty_usd=task["bounty_usd"],
            deadline=datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")),
            agent_id=task["agent_id"],
            instructions=task["instructions"],
            evidence_schema=task.get("evidence_schema"),
            location_hint=task.get("location_hint"),
            min_reputation=task.get("min_reputation", 0),
        )

    except Exception as e:
        logger.error("Failed to create task: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    responses={
        200: {"description": "Task found"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Not authorized to view this task"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    }
)
async def get_task(
    task_id: str = Path(..., description="UUID of the task", min_length=36, max_length=36),
    api_key: APIKeyData = Depends(verify_api_key)
) -> TaskResponse:
    """
    Get task by ID.

    Only returns tasks owned by the authenticated agent.
    """
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["agent_id"] != api_key.agent_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this task")

    return TaskResponse(
        id=task["id"],
        title=task["title"],
        status=task["status"],
        category=task["category"],
        bounty_usd=task["bounty_usd"],
        deadline=datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")),
        created_at=datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")),
        agent_id=task["agent_id"],
        executor_id=task.get("executor_id"),
        instructions=task["instructions"],
        evidence_schema=task.get("evidence_schema"),
        location_hint=task.get("location_hint"),
        min_reputation=task.get("min_reputation", 0),
    )


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    responses={
        200: {"description": "Tasks retrieved"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    }
)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    category: Optional[TaskCategory] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    api_key: APIKeyData = Depends(verify_api_key)
) -> TaskListResponse:
    """
    List tasks for the authenticated agent.

    Supports filtering by status and category, with pagination.
    """
    result = await db.get_tasks(
        agent_id=api_key.agent_id,
        status=status.value if status else None,
        category=category.value if category else None,
        limit=limit,
        offset=offset,
    )

    tasks = []
    for task in result.get("tasks", []):
        tasks.append(TaskResponse(
            id=task["id"],
            title=task["title"],
            status=task["status"],
            category=task["category"],
            bounty_usd=task["bounty_usd"],
            deadline=datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")),
            agent_id=task["agent_id"],
            executor_id=task.get("executor_id"),
            min_reputation=task.get("min_reputation", 0),
        ))

    return TaskListResponse(
        tasks=tasks,
        total=result["total"],
        count=result["count"],
        offset=offset,
        has_more=result["has_more"],
    )


@router.get(
    "/tasks/{task_id}/submissions",
    response_model=SubmissionListResponse,
    responses={
        200: {"description": "Submissions retrieved"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Not authorized"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    }
)
async def get_submissions(
    task_id: str = Path(..., description="UUID of the task", min_length=36, max_length=36),
    api_key: APIKeyData = Depends(verify_api_key)
) -> SubmissionListResponse:
    """
    Get submissions for a task.

    Only returns submissions for tasks owned by the authenticated agent.
    """
    # Verify ownership
    if not await verify_agent_owns_task(api_key.agent_id, task_id):
        task = await db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=403, detail="Not authorized to view submissions")

    submissions = await db.get_submissions_for_task(task_id)

    result = []
    for sub in submissions:
        # Calculate pre-check score if evidence exists
        pre_check_score = None
        if sub.get("evidence"):
            # Get auto-check results if available
            auto_checks = sub.get("auto_checks", {})
            if auto_checks:
                pre_check_score = calculate_auto_score(auto_checks)

        result.append(SubmissionResponse(
            id=sub["id"],
            task_id=sub["task_id"],
            executor_id=sub["executor_id"],
            status=sub.get("agent_verdict", "pending"),
            pre_check_score=pre_check_score,
            submitted_at=datetime.fromisoformat(sub["submitted_at"].replace("Z", "+00:00")),
            evidence=sub.get("evidence"),
            agent_verdict=sub.get("agent_verdict"),
            agent_notes=sub.get("agent_notes"),
            verified_at=datetime.fromisoformat(sub["verified_at"].replace("Z", "+00:00")) if sub.get("verified_at") else None,
        ))

    return SubmissionListResponse(
        submissions=result,
        count=len(result),
    )


@router.post(
    "/submissions/{submission_id}/approve",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Submission approved"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Not authorized"},
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {"model": ErrorResponse, "description": "Submission already processed"},
    }
)
async def approve_submission(
    submission_id: str = Path(..., description="UUID of the submission", min_length=36, max_length=36),
    request: ApprovalRequest = None,
    api_key: APIKeyData = Depends(verify_api_key)
) -> SuccessResponse:
    """
    Approve a submission.

    Triggers payment release to the worker and updates task status to completed.
    """
    # Verify ownership
    if not await verify_agent_owns_submission(api_key.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(status_code=403, detail="Not authorized to approve this submission")

    # Check if already processed
    submission = await db.get_submission(submission_id)
    if submission.get("agent_verdict") not in [None, "pending"]:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}"
        )

    # Update submission
    notes = request.notes if request else None
    await db.update_submission(
        submission_id=submission_id,
        agent_id=api_key.agent_id,
        verdict="accepted",
        notes=notes,
    )

    logger.info(
        "Submission approved: id=%s, agent=%s",
        submission_id, api_key.agent_id
    )

    return SuccessResponse(
        message="Submission approved. Payment will be released to worker.",
        data={"submission_id": submission_id, "verdict": "accepted"}
    )


@router.post(
    "/submissions/{submission_id}/reject",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Submission rejected"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Not authorized"},
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {"model": ErrorResponse, "description": "Submission already processed"},
    }
)
async def reject_submission(
    submission_id: str = Path(..., description="UUID of the submission", min_length=36, max_length=36),
    request: RejectionRequest = ...,
    api_key: APIKeyData = Depends(verify_api_key)
) -> SuccessResponse:
    """
    Reject a submission.

    The task will be returned to 'published' status for other workers.
    """
    # Verify ownership
    if not await verify_agent_owns_submission(api_key.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(status_code=403, detail="Not authorized to reject this submission")

    # Check if already processed
    submission = await db.get_submission(submission_id)
    if submission.get("agent_verdict") not in [None, "pending"]:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}"
        )

    # Update submission
    await db.update_submission(
        submission_id=submission_id,
        agent_id=api_key.agent_id,
        verdict="rejected",
        notes=request.notes,
    )

    logger.info(
        "Submission rejected: id=%s, agent=%s, reason=%s",
        submission_id, api_key.agent_id, request.notes[:50]
    )

    return SuccessResponse(
        message="Submission rejected. Task returned to available pool.",
        data={"submission_id": submission_id, "verdict": "rejected"}
    )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Task cancelled"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Not authorized"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task cannot be cancelled"},
    }
)
async def cancel_task(
    task_id: str = Path(..., description="UUID of the task", min_length=36, max_length=36),
    request: CancelRequest = None,
    api_key: APIKeyData = Depends(verify_api_key)
) -> SuccessResponse:
    """
    Cancel a task.

    Only tasks in 'published' status can be cancelled. Escrow will be returned.
    """
    try:
        reason = request.reason if request else None
        await db.cancel_task(task_id, api_key.agent_id)

        logger.info(
            "Task cancelled: id=%s, agent=%s, reason=%s",
            task_id, api_key.agent_id, reason
        )

        return SuccessResponse(
            message="Task cancelled successfully. Escrow will be returned.",
            data={"task_id": task_id, "reason": reason}
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        elif "cannot cancel" in error_msg.lower() or "status" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    responses={
        200: {"description": "Analytics retrieved"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    }
)
async def get_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    api_key: APIKeyData = Depends(verify_api_key)
) -> AnalyticsResponse:
    """
    Get agent analytics.

    Provides task completion rates, spending, and top workers.
    """
    result = await db.get_agent_analytics(
        agent_id=api_key.agent_id,
        days=days,
    )

    return AnalyticsResponse(
        totals=result["totals"],
        by_status=result["by_status"],
        by_category=result["by_category"],
        average_times=result["average_times"],
        top_workers=result["top_workers"],
        period_days=result["period_days"],
    )


# =============================================================================
# WORKER ENDPOINTS (PUBLIC/SEMI-PUBLIC)
# =============================================================================


@router.get(
    "/tasks/available",
    response_model=AvailableTasksResponse,
    responses={
        200: {"description": "Available tasks retrieved"},
    }
)
async def get_available_tasks(
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for location filtering"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for location filtering"),
    radius_km: int = Query(50, ge=1, le=500, description="Search radius in kilometers"),
    category: Optional[TaskCategory] = Query(None, description="Filter by category"),
    min_bounty: Optional[float] = Query(None, ge=0, description="Minimum bounty USD"),
    max_bounty: Optional[float] = Query(None, le=10000, description="Maximum bounty USD"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> AvailableTasksResponse:
    """
    Get available tasks for workers.

    Public endpoint that returns tasks in 'published' status.
    Supports location-based filtering and bounty range filtering.
    """
    try:
        client = db.get_client()

        # Build query
        query = client.table("tasks").select(
            "id, title, category, bounty_usd, deadline, location_hint, min_reputation, created_at"
        ).eq("status", "published")

        # Apply category filter
        if category:
            query = query.eq("category", category.value)

        # Apply bounty filters
        if min_bounty is not None:
            query = query.gte("bounty_usd", min_bounty)
        if max_bounty is not None:
            query = query.lte("bounty_usd", max_bounty)

        # Execute query
        result = query.order("bounty_usd", desc=True).range(offset, offset + limit - 1).execute()

        tasks = result.data or []

        # Build filters applied response
        filters_applied = {
            "category": category.value if category else None,
            "min_bounty": min_bounty,
            "max_bounty": max_bounty,
            "location": {"lat": lat, "lng": lng, "radius_km": radius_km} if lat and lng else None,
        }

        return AvailableTasksResponse(
            tasks=tasks,
            count=len(tasks),
            offset=offset,
            filters_applied={k: v for k, v in filters_applied.items() if v is not None},
        )

    except Exception as e:
        logger.error("Failed to get available tasks: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to get available tasks")


@router.post(
    "/tasks/{task_id}/apply",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Application submitted"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Not eligible"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Already applied"},
    }
)
async def apply_to_task(
    task_id: str = Path(..., description="UUID of the task", min_length=36, max_length=36),
    request: WorkerApplicationRequest = ...,
) -> SuccessResponse:
    """
    Apply to a task.

    Worker endpoint for submitting task applications. Checks reputation requirements.
    """
    try:
        result = await db.apply_to_task(
            task_id=task_id,
            executor_id=request.executor_id,
            message=request.message,
        )

        logger.info(
            "Application submitted: task=%s, executor=%s",
            task_id, request.executor_id[:8]
        )

        return SuccessResponse(
            message="Application submitted successfully",
            data={
                "application_id": result["application"]["id"],
                "task_id": task_id,
                "status": "pending"
            }
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            if "executor" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Executor not found")
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not available" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Task is not available for applications")
        elif "insufficient reputation" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        elif "already applied" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Already applied to this task")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post(
    "/tasks/{task_id}/submit",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Work submitted"},
        400: {"model": ErrorResponse, "description": "Invalid request or missing evidence"},
        403: {"model": ErrorResponse, "description": "Not assigned to this task"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task not in submittable state"},
    }
)
async def submit_work(
    task_id: str = Path(..., description="UUID of the task", min_length=36, max_length=36),
    request: WorkerSubmissionRequest = ...,
) -> SuccessResponse:
    """
    Submit work for a task.

    Worker endpoint for submitting completed work with evidence.
    Only assigned workers can submit.
    """
    try:
        result = await db.submit_work(
            task_id=task_id,
            executor_id=request.executor_id,
            evidence=request.evidence,
            notes=request.notes,
        )

        logger.info(
            "Work submitted: task=%s, executor=%s, submission=%s",
            task_id, request.executor_id[:8], result["submission"]["id"]
        )

        return SuccessResponse(
            message="Work submitted successfully. Awaiting agent review.",
            data={
                "submission_id": result["submission"]["id"],
                "task_id": task_id,
                "status": "submitted"
            }
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not assigned" in error_msg.lower():
            raise HTTPException(status_code=403, detail="You are not assigned to this task")
        elif "not in a submittable state" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        elif "missing required evidence" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


# =============================================================================
# BATCH OPERATIONS
# =============================================================================


class BatchTaskDefinition(BaseModel):
    """Single task definition for batch creation."""
    title: str = Field(..., min_length=5, max_length=255)
    instructions: str = Field(..., min_length=20, max_length=5000)
    category: TaskCategory
    bounty_usd: float = Field(..., gt=0, le=10000)
    deadline_hours: int = Field(..., ge=1, le=720)
    evidence_required: List[EvidenceType] = Field(..., min_length=1, max_length=5)
    evidence_optional: Optional[List[EvidenceType]] = None
    location_hint: Optional[str] = None
    min_reputation: int = 0


class BatchCreateRequest(BaseModel):
    """Request model for batch task creation."""
    tasks: List[BatchTaskDefinition] = Field(
        ...,
        description="List of tasks to create",
        min_length=1,
        max_length=50
    )
    payment_token: str = Field(default="USDC", description="Payment token for all tasks")


class BatchCreateResponse(BaseModel):
    """Response model for batch task creation."""
    created: int
    failed: int
    tasks: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    total_bounty: float


@router.post(
    "/tasks/batch",
    response_model=BatchCreateResponse,
    status_code=201,
    responses={
        201: {"description": "Batch created"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    }
)
async def batch_create_tasks(
    request: BatchCreateRequest,
    api_key: APIKeyData = Depends(verify_api_key)
) -> BatchCreateResponse:
    """
    Create multiple tasks in a single request.

    Useful for agents that need to create many similar tasks.
    Maximum 50 tasks per batch.
    """
    created_tasks = []
    errors = []
    total_bounty = 0.0

    for i, task_def in enumerate(request.tasks):
        try:
            deadline = datetime.now(timezone.utc) + timedelta(hours=task_def.deadline_hours)

            task = await db.create_task(
                agent_id=api_key.agent_id,
                title=task_def.title,
                instructions=task_def.instructions,
                category=task_def.category.value,
                bounty_usd=task_def.bounty_usd,
                deadline=deadline,
                evidence_required=[e.value for e in task_def.evidence_required],
                evidence_optional=[e.value for e in (task_def.evidence_optional or [])],
                location_hint=task_def.location_hint,
                min_reputation=task_def.min_reputation,
                payment_token=request.payment_token,
            )

            created_tasks.append({
                "index": i,
                "id": task["id"],
                "title": task["title"],
                "bounty_usd": task["bounty_usd"],
            })
            total_bounty += task_def.bounty_usd

        except Exception as e:
            errors.append({
                "index": i,
                "title": task_def.title,
                "error": str(e),
            })

    logger.info(
        "Batch create: agent=%s, created=%d, failed=%d, total_bounty=%.2f",
        api_key.agent_id, len(created_tasks), len(errors), total_bounty
    )

    return BatchCreateResponse(
        created=len(created_tasks),
        failed=len(errors),
        tasks=created_tasks,
        errors=errors,
        total_bounty=total_bounty,
    )


# =============================================================================
# HEALTH & INFO ENDPOINTS
# =============================================================================


@router.get("/health")
async def api_health():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "api_version": "v1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
