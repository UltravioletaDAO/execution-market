"""
H2A (Human-to-Agent) API Routes

Endpoints for the H2A marketplace direction where humans publish tasks
for AI agents to execute. Uses JWT auth for humans and separate
/api/v1/h2a/* endpoints to avoid breaking existing A2H flows.

Endpoints:
  POST   /api/v1/h2a/tasks                    - Human publishes task
  GET    /api/v1/h2a/tasks                    - List human's published tasks
  GET    /api/v1/h2a/tasks/{task_id}          - View task details
  GET    /api/v1/h2a/tasks/{task_id}/submissions - View agent submissions
  POST   /api/v1/h2a/tasks/{task_id}/approve  - Approve + pay
  POST   /api/v1/h2a/tasks/{task_id}/reject   - Reject submission
  POST   /api/v1/h2a/tasks/{task_id}/cancel   - Cancel task
  GET    /api/v1/agents/directory              - Browse AI agents (public)
  POST   /api/v1/agents/register-executor      - Register agent executor
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Header, Request
from pydantic import BaseModel

import supabase_client as db
from models import (
    PublishH2ATaskRequest,
    ApproveH2ASubmissionRequest,
    H2ATaskResponse,
    H2AApprovalResponse,
    AgentDirectoryEntry,
    AgentDirectoryResponse,
)

# Payment event audit trail
from integrations.x402.payment_events import log_payment_event

# Platform configuration
try:
    from config import PlatformConfig

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default fee (overridden by config system when available)
DEFAULT_PLATFORM_FEE_PERCENT = Decimal("0.13")
TREASURY_ADDRESS = os.environ.get(
    "EM_TREASURY_ADDRESS", "0xae07B067934975cF3DA0aa1D09cF373b0FED3661"
)


async def get_platform_fee_percent() -> Decimal:
    """Get platform fee from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_fee_pct()
        except Exception:
            pass
    return DEFAULT_PLATFORM_FEE_PERCENT


# ---------------------------------------------------------------------------
# JWT Auth for Humans
# ---------------------------------------------------------------------------


class JWTData(BaseModel):
    """Validated JWT token data for human publishers."""

    user_id: str
    wallet_address: Optional[str] = None
    email: Optional[str] = None
    is_human: bool = True


async def verify_jwt_auth(
    authorization: Optional[str] = Header(None),
) -> JWTData:
    """
    Verify Supabase JWT for human publisher authentication.

    Humans authenticate via their browser session (Dynamic.xyz / Supabase).
    The JWT contains user_id and wallet_address claims.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header required (Bearer <jwt_token>)",
        )

    token = authorization[7:].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    # Try Supabase JWT verification
    try:
        import jwt as pyjwt

        jwt_secret = os.environ.get(
            "SUPABASE_JWT_SECRET",
            os.environ.get("EM_JWT_SECRET", ""),
        )

        if not jwt_secret:
            raise HTTPException(status_code=500, detail="JWT secret not configured")

        payload = pyjwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": True},
        )

        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")

        # Try to get wallet from the token or from Supabase user metadata
        wallet_address = payload.get("wallet_address")
        email = payload.get("email")

        # If wallet not in JWT, look it up from the executor profile
        if not wallet_address:
            try:
                client = db.get_client()
                result = (
                    client.table("executors")
                    .select("wallet_address")
                    .eq("user_id", user_id)
                    .limit(1)
                    .execute()
                )
                if result.data and len(result.data) > 0:
                    wallet_address = result.data[0].get("wallet_address")
            except Exception as e:
                logger.warning("Could not look up wallet for user %s: %s", user_id, e)

        return JWTData(
            user_id=user_id,
            wallet_address=wallet_address,
            email=email,
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="JWT library not available")
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def verify_auth_method(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Accept either API key (agents) or Supabase JWT (humans).

    This dual-auth helper allows endpoints that both humans and agents
    can access (e.g., viewing task details).
    """
    from .auth import verify_api_key

    # Try API key first (agents)
    if x_api_key and x_api_key.startswith("em_"):
        return await verify_api_key(authorization=None, x_api_key=x_api_key)

    if authorization:
        bearer_token = (
            authorization[7:].strip() if authorization.startswith("Bearer ") else ""
        )

        # API key via Bearer
        if bearer_token.startswith("em_") or bearer_token.startswith("sk_em_"):
            return await verify_api_key(authorization=authorization, x_api_key=None)

        # JWT via Bearer
        if bearer_token.startswith("ey"):
            return await verify_jwt_auth(authorization)

    raise HTTPException(status_code=401, detail="API key or JWT token required")


# ---------------------------------------------------------------------------
# Feature flag helpers
# ---------------------------------------------------------------------------


async def _check_h2a_enabled():
    """Check if H2A feature is enabled."""
    try:
        client = db.get_client()
        result = (
            client.table("platform_config")
            .select("value")
            .eq("key", "feature.h2a_enabled")
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("value") == "false":
            raise HTTPException(
                status_code=403,
                detail="H2A marketplace is not currently enabled",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable — unable to verify feature status",
        )


async def _get_h2a_bounty_limits() -> tuple[Decimal, Decimal]:
    """Get H2A bounty limits from config."""
    min_bounty = Decimal("0.50")
    max_bounty = Decimal("500.00")
    try:
        client = db.get_client()
        result = (
            client.table("platform_config")
            .select("key, value")
            .in_("key", ["feature.h2a_min_bounty", "feature.h2a_max_bounty"])
            .execute()
        )
        if result.data:
            for row in result.data:
                if row["key"] == "feature.h2a_min_bounty":
                    min_bounty = Decimal(row["value"])
                elif row["key"] == "feature.h2a_max_bounty":
                    max_bounty = Decimal(row["value"])
    except Exception:
        pass
    return min_bounty, max_bounty


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["H2A Marketplace"])


# ---------------------------------------------------------------------------
# H2A Task Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/h2a/tasks",
    response_model=H2ATaskResponse,
    status_code=201,
    summary="Publish H2A Task",
    description="Human publishes a task for AI agents to execute.",
    tags=["H2A Marketplace"],
)
async def create_h2a_task(
    request: PublishH2ATaskRequest,
    auth: JWTData = Depends(verify_jwt_auth),
):
    """
    Human publishes a task for AI agents to execute.

    Creates a task with publisher_type='human' and target_executor_type='agent'.
    The task appears in the agent task board for agents to browse and accept.

    Payment uses sign-on-approval: the human signs EIP-3009 authorizations
    only when approving the agent's completed work (no upfront funds locked).
    """
    await _check_h2a_enabled()

    # Resolve human's wallet
    wallet = auth.wallet_address
    if not wallet:
        raise HTTPException(
            status_code=400,
            detail="No wallet address linked to your account. Please connect a wallet first.",
        )

    # Validate bounty against H2A limits
    bounty = Decimal(str(request.bounty_usd))
    min_bounty, max_bounty = await _get_h2a_bounty_limits()

    if bounty < min_bounty:
        raise HTTPException(
            status_code=400,
            detail=f"Bounty ${bounty} is below H2A minimum ${min_bounty}",
        )
    if bounty > max_bounty:
        raise HTTPException(
            status_code=400,
            detail=f"Bounty ${bounty} exceeds H2A maximum ${max_bounty}",
        )

    # Calculate fees
    platform_fee_pct = await get_platform_fee_percent()
    fee_usd = float(bounty * platform_fee_pct)
    total_required = float(bounty) + fee_usd

    # Calculate deadline
    deadline = datetime.now(timezone.utc) + timedelta(hours=request.deadline_hours)

    # Build evidence schema
    evidence_schema = {
        "required": request.evidence_required,
        "optional": [],
    }

    # Create task in database
    try:
        client = db.get_client()
        task_data = {
            "agent_id": f"human:{auth.user_id}",  # Tag for H2A identification
            "title": request.title,
            "instructions": request.instructions,
            "category": request.category.value
            if hasattr(request.category, "value")
            else request.category,
            "bounty_usd": float(bounty),
            "deadline": deadline.isoformat(),
            "evidence_schema": evidence_schema,
            "payment_token": "USDC",
            "payment_network": request.payment_network,
            "status": "published",
            "min_reputation": 0,
            "publisher_type": "human",
            "human_wallet": wallet,
            "human_user_id": auth.user_id,
            "target_executor_type": "agent",
            "required_capabilities": request.required_capabilities,
            "verification_mode": request.verification_mode or "manual",
        }

        result = client.table("tasks").insert(task_data).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to create task")

        task = result.data[0]

        logger.info(
            "H2A task created: task_id=%s, user=%s, bounty=$%s",
            task["id"],
            auth.user_id,
            bounty,
        )

        return H2ATaskResponse(
            task_id=task["id"],
            status="published",
            bounty_usd=float(bounty),
            fee_usd=round(fee_usd, 2),
            total_required_usd=round(total_required, 2),
            deadline=deadline.isoformat(),
            publisher_type="human",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create H2A task: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")


@router.get(
    "/api/v1/h2a/tasks",
    summary="List H2A Tasks",
    description="List tasks published by the authenticated human, or all published H2A tasks.",
    tags=["H2A Marketplace"],
)
async def list_h2a_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    my_tasks: bool = Query(
        False, description="Only show my published tasks (requires auth)"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    """
    List H2A tasks. Can be filtered by status and category.

    If my_tasks=true, requires JWT auth and returns only the caller's tasks.
    Otherwise returns all published H2A tasks (public, for agents to browse).
    """
    try:
        client = db.get_client()
        query = (
            client.table("tasks")
            .select(
                "*, executor:executors(id, display_name, reputation_score, capabilities, executor_type)"
            )
            .eq("publisher_type", "human")
        )

        if my_tasks:
            auth = await verify_jwt_auth(authorization)
            query = query.eq("human_user_id", auth.user_id)

        if status:
            query = query.eq("status", status)
        else:
            if not my_tasks:
                # For public listing, show only published tasks
                query = query.eq("status", "published")

        if category:
            query = query.eq("category", category)

        # Count
        count_query = (
            client.table("tasks")
            .select("id", count="exact")
            .eq("publisher_type", "human")
        )
        if my_tasks and authorization:
            try:
                auth_data = await verify_jwt_auth(authorization)
                count_query = count_query.eq("human_user_id", auth_data.user_id)
            except Exception:
                pass
        if status:
            count_query = count_query.eq("status", status)
        elif not my_tasks:
            count_query = count_query.eq("status", "published")
        if category:
            count_query = count_query.eq("category", category)

        count_result = count_query.execute()
        total = count_result.count if count_result.count else 0

        # Paginated results
        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        tasks = result.data or []

        # Strip PII from public listings (non-owner views)
        if not my_tasks:
            for t in tasks:
                t.pop("human_wallet", None)
                t.pop("human_user_id", None)

        return {
            "tasks": tasks,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": total > offset + len(tasks),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list H2A tasks: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/v1/h2a/tasks/{task_id}",
    summary="Get H2A Task Details",
    description="View details of an H2A task.",
    tags=["H2A Marketplace"],
)
async def get_h2a_task(
    task_id: str = Path(..., min_length=36, max_length=36),
):
    """Get details of an H2A task (public)."""
    try:
        client = db.get_client()
        result = (
            client.table("tasks")
            .select(
                "*, executor:executors(id, display_name, wallet_address, reputation_score, capabilities)"
            )
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")

        # Strip PII from public view
        task.pop("human_wallet", None)
        task.pop("human_user_id", None)

        return task

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get H2A task %s: %s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/v1/h2a/tasks/{task_id}/submissions",
    summary="View Agent Submissions",
    description="View submissions from agents for an H2A task.",
    tags=["H2A Marketplace"],
)
async def get_h2a_submissions(
    task_id: str = Path(..., min_length=36, max_length=36),
    auth: JWTData = Depends(verify_jwt_auth),
):
    """View agent submissions for a task owned by the authenticated human."""
    try:
        # Verify task ownership
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select("id, human_user_id, publisher_type")
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if task.get("human_user_id") != auth.user_id:
            raise HTTPException(status_code=403, detail="Not your task")

        # Get submissions
        submissions_result = (
            client.table("submissions")
            .select(
                "*, executor:executors(id, display_name, wallet_address, reputation_score, capabilities)"
            )
            .eq("task_id", task_id)
            .order("submitted_at", desc=True)
            .execute()
        )

        return {
            "task_id": task_id,
            "submissions": submissions_result.data or [],
            "count": len(submissions_result.data or []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get submissions for H2A task %s: %s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/v1/h2a/tasks/{task_id}/approve",
    response_model=H2AApprovalResponse,
    summary="Approve Agent Submission",
    description="Human approves agent's work and provides signed payment authorizations.",
    tags=["H2A Marketplace"],
)
async def approve_h2a_submission(
    task_id: str,
    request: ApproveH2ASubmissionRequest,
    auth: JWTData = Depends(verify_jwt_auth),
):
    """
    Human approves agent's work and provides signed payment authorizations.

    For verdict='accepted':
    - settlement_auth_worker: EIP-3009 auth (human → agent, bounty amount)
    - settlement_auth_fee: EIP-3009 auth (human → treasury, 13% fee)

    Both signatures are settled via the Facilitator for gasless on-chain transfer.
    """
    try:
        # Validate task ownership
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select(
                "id, human_user_id, human_wallet, publisher_type, bounty_usd, status"
            )
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if task.get("human_user_id") != auth.user_id:
            raise HTTPException(status_code=403, detail="Not your task")

        # Validate task is in an approvable status
        approvable_statuses = {"submitted", "in_progress"}
        current_status = task.get("status")
        if current_status not in approvable_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve task in status '{current_status}'. "
                f"Only tasks in {approvable_statuses} can be approved.",
            )

        # Get submission
        sub_result = (
            client.table("submissions")
            .select("*, executor:executors(id, wallet_address, display_name)")
            .eq("id", request.submission_id)
            .eq("task_id", task_id)
            .single()
            .execute()
        )

        if not sub_result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        submission = sub_result.data
        executor = submission.get("executor", {})
        agent_wallet = executor.get("wallet_address")

        if request.verdict == "accepted":
            # Validate signatures are provided
            if not request.settlement_auth_worker or not request.settlement_auth_fee:
                raise HTTPException(
                    status_code=400,
                    detail="Payment signatures required for approval "
                    "(settlement_auth_worker and settlement_auth_fee)",
                )

            # Settlement via Facilitator
            worker_tx = None
            fee_tx = None

            try:
                from integrations.x402.sdk_client import get_sdk, SDK_AVAILABLE

                if SDK_AVAILABLE:
                    sdk = get_sdk()
                    if sdk:
                        # Settle bounty: human → agent
                        worker_result = await sdk.settle_payment(
                            request.settlement_auth_worker
                        )
                        worker_tx = (
                            worker_result.get("tx_hash")
                            or worker_result.get("transaction_hash")
                            if worker_result
                            else None
                        )

                        # Settle fee: human → treasury
                        fee_result = await sdk.settle_payment(
                            request.settlement_auth_fee
                        )
                        fee_tx = (
                            fee_result.get("tx_hash")
                            or fee_result.get("transaction_hash")
                            if fee_result
                            else None
                        )
            except Exception as e:
                logger.error("H2A payment settlement failed: %s", str(e))
                # Log the failure as a payment event
                try:
                    await log_payment_event(
                        event_type="h2a_settle_error",
                        task_id=task_id,
                        tx_hash=None,
                        amount_usdc=task.get("bounty_usd"),
                        from_address=task.get("human_wallet"),
                        to_address=agent_wallet,
                        metadata={
                            "submission_id": request.submission_id,
                            "error": str(e),
                        },
                    )
                except Exception:
                    pass
                # Settlement failed — do NOT update task/submission status
                raise HTTPException(
                    status_code=502,
                    detail=f"Payment settlement failed: {str(e)}. Task status unchanged.",
                )

            # Log payment events
            try:
                await log_payment_event(
                    event_type="h2a_settle_worker",
                    task_id=task_id,
                    tx_hash=worker_tx,
                    amount_usdc=task.get("bounty_usd"),
                    from_address=task.get("human_wallet"),
                    to_address=agent_wallet,
                    metadata={
                        "submission_id": request.submission_id,
                        "publisher_type": "human",
                    },
                )
                await log_payment_event(
                    event_type="h2a_settle_fee",
                    task_id=task_id,
                    tx_hash=fee_tx,
                    amount_usdc=float(
                        Decimal(str(task.get("bounty_usd", 0)))
                        * await get_platform_fee_percent()
                    ),
                    from_address=task.get("human_wallet"),
                    to_address=TREASURY_ADDRESS,
                    metadata={
                        "submission_id": request.submission_id,
                        "publisher_type": "human",
                    },
                )
            except Exception as e:
                logger.warning("Failed to log H2A payment events: %s", e)

            # Update task + submission status
            try:
                client.table("tasks").update(
                    {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", task_id).execute()

                client.table("submissions").update(
                    {
                        "agent_verdict": "accepted",
                        "agent_notes": request.notes,
                        "payment_tx": worker_tx,
                        "paid_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", request.submission_id).execute()
            except Exception as e:
                logger.error("Failed to update H2A task/submission status: %s", e)

            logger.info(
                "H2A submission approved: task=%s, submission=%s, worker_tx=%s",
                task_id,
                request.submission_id,
                worker_tx,
            )

            return H2AApprovalResponse(
                status="accepted",
                worker_tx=worker_tx,
                fee_tx=fee_tx,
            )

        elif request.verdict == "rejected":
            client.table("submissions").update(
                {
                    "agent_verdict": "rejected",
                    "agent_notes": request.notes,
                }
            ).eq("id", request.submission_id).execute()

            logger.info(
                "H2A submission rejected: task=%s, submission=%s",
                task_id,
                request.submission_id,
            )

            return H2AApprovalResponse(
                status="rejected",
                notes=request.notes,
            )

        elif request.verdict == "needs_revision":
            client.table("submissions").update(
                {
                    "agent_verdict": "more_info_requested",
                    "agent_notes": request.notes,
                }
            ).eq("id", request.submission_id).execute()

            # Move task back to in_progress so agent can resubmit
            client.table("tasks").update({"status": "in_progress"}).eq(
                "id", task_id
            ).execute()

            logger.info(
                "H2A submission needs revision: task=%s, submission=%s",
                task_id,
                request.submission_id,
            )

            return H2AApprovalResponse(
                status="needs_revision",
                notes=request.notes,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("H2A approval failed: task=%s, error=%s", task_id, str(e))
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.post(
    "/api/v1/h2a/tasks/{task_id}/cancel",
    summary="Cancel H2A Task",
    description="Cancel a published H2A task.",
    tags=["H2A Marketplace"],
)
async def cancel_h2a_task(
    task_id: str = Path(..., min_length=36, max_length=36),
    auth: JWTData = Depends(verify_jwt_auth),
):
    """Cancel a published H2A task. Only works for published/accepted tasks."""
    try:
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select("id, human_user_id, publisher_type, status")
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if task.get("human_user_id") != auth.user_id:
            raise HTTPException(status_code=403, detail="Not your task")

        cancellable = {"published", "accepted"}
        if task.get("status") not in cancellable:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in status '{task.get('status')}'. "
                f"Only tasks in {cancellable} can be cancelled.",
            )

        client.table("tasks").update({"status": "cancelled"}).eq(
            "id", task_id
        ).execute()

        logger.info("H2A task cancelled: task=%s, user=%s", task_id, auth.user_id)

        return {"status": "cancelled", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("H2A cancel failed: task=%s, error=%s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Agent Directory Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/agents/directory",
    response_model=AgentDirectoryResponse,
    summary="Agent Directory",
    description="Browse AI agents available for H2A task execution. Public endpoint.",
    tags=["Agent Directory"],
)
async def get_agent_directory(
    capability: Optional[str] = Query(
        None, description="Filter by capability (comma-separated)"
    ),
    min_rating: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query(
        "rating", description="Sort by: rating, tasks_completed, display_name"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Browse the public AI agent directory.

    Returns agents registered as executor_type='agent' with aggregated stats.
    No authentication required — discovery drives adoption.
    """
    try:
        client = db.get_client()
        offset = (page - 1) * limit

        # Query executors with executor_type='agent'
        query = (
            client.table("executors")
            .select("*", count="exact")
            .eq("executor_type", "agent")
            .not_.is_("display_name", "null")
        )

        # Capability filter (check array overlap)
        if capability:
            caps = [c.strip() for c in capability.split(",")]
            query = query.overlaps("capabilities", caps)

        # Rating filter
        if min_rating is not None:
            query = query.gte("reputation_score", min_rating)

        # Sort
        if sort == "tasks_completed":
            query = query.order("tasks_completed", desc=True)
        elif sort == "display_name":
            query = query.order("display_name")
        else:
            query = query.order("reputation_score", desc=True)

        # Paginate
        result = query.range(offset, offset + limit - 1).execute()

        agents = []
        for row in result.data or []:
            agents.append(
                AgentDirectoryEntry(
                    executor_id=row["id"],
                    display_name=row.get("display_name", "Unknown Agent"),
                    capabilities=row.get("capabilities"),
                    rating=row.get("reputation_score", 0),
                    tasks_completed=row.get("tasks_completed", 0),
                    avg_rating=row.get("avg_rating", 0) or 0,
                    agent_card_url=row.get("agent_card_url"),
                    mcp_endpoint_url=row.get("mcp_endpoint_url"),
                    erc8004_agent_id=row.get("erc8004_agent_id"),
                    verified=row.get("is_verified", False) or False,
                    bio=row.get("bio"),
                    avatar_url=row.get("avatar_url"),
                    pricing=row.get("pricing"),
                )
            )

        total = result.count if result.count else len(agents)

        return AgentDirectoryResponse(
            agents=agents,
            total=total,
            page=page,
            limit=limit,
        )

    except Exception as e:
        logger.error("Agent directory query failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/v1/agents/register-executor",
    summary="Register Agent Executor",
    description="Register an AI agent as an executor on the marketplace.",
    tags=["Agent Directory"],
    status_code=201,
)
async def register_agent_executor(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Register an AI agent as an executor on the marketplace.

    The agent must provide a wallet address and capabilities.
    Requires API key authentication.
    """
    from .auth import verify_api_key

    # Require API key for registration
    try:
        await verify_api_key(authorization, x_api_key)
    except HTTPException:
        raise HTTPException(
            status_code=401, detail="API key required for agent registration"
        )

    body = await request.json()

    wallet_address = body.get("wallet_address")
    display_name = body.get("display_name")
    capabilities = body.get("capabilities", [])

    if not wallet_address or not display_name or not capabilities:
        raise HTTPException(
            status_code=400,
            detail="wallet_address, display_name, and capabilities are required",
        )

    try:
        client = db.get_client()

        # Check if executor already exists with this wallet
        existing = (
            client.table("executors")
            .select("id")
            .eq("wallet_address", wallet_address)
            .execute()
        )

        if existing.data and len(existing.data) > 0:
            # Update existing
            executor_id = existing.data[0]["id"]
            client.table("executors").update(
                {
                    "display_name": display_name,
                    "capabilities": capabilities,
                    "executor_type": "agent",
                    "agent_card_url": body.get("agent_card_url"),
                    "mcp_endpoint_url": body.get("mcp_endpoint_url"),
                    "erc8004_agent_id": body.get("erc8004_agent_id"),
                    "pricing": body.get("pricing"),
                    "bio": body.get("bio"),
                    "is_verified": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", executor_id).execute()

            logger.info("Agent executor updated: %s (%s)", display_name, executor_id)

            return {
                "executor_id": executor_id,
                "display_name": display_name,
                "status": "updated",
            }
        else:
            # Create new executor
            executor_data = {
                "wallet_address": wallet_address,
                "display_name": display_name,
                "capabilities": capabilities,
                "executor_type": "agent",
                "agent_card_url": body.get("agent_card_url"),
                "mcp_endpoint_url": body.get("mcp_endpoint_url"),
                "erc8004_agent_id": body.get("erc8004_agent_id"),
                "pricing": body.get("pricing"),
                "bio": body.get("bio"),
                "is_verified": False,
                "reputation_score": 0,
                "tasks_completed": 0,
            }

            result = client.table("executors").insert(executor_data).execute()

            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=500, detail="Failed to register agent executor"
                )

            executor = result.data[0]
            logger.info(
                "Agent executor registered: %s (%s)",
                display_name,
                executor["id"],
            )

            return {
                "executor_id": executor["id"],
                "display_name": display_name,
                "status": "registered",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent registration failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
