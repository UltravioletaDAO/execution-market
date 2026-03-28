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

    Supports both ES256 (JWKS, new Supabase default) and HS256 (legacy).
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

    try:
        import jwt as pyjwt

        payload = _decode_supabase_jwt(token, pyjwt)

        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")

        wallet_address = payload.get("wallet_address")
        email = payload.get("email")

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
    except HTTPException:
        raise
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# Cache the JWKS client to avoid fetching keys on every request
_jwks_client: object | None = None


def _get_jwks_client():
    """Lazy-init a PyJWKClient for the Supabase JWKS endpoint."""
    global _jwks_client
    if _jwks_client is None:
        from jwt import PyJWKClient

        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        if supabase_url:
            _jwks_client = PyJWKClient(
                f"{supabase_url}/auth/v1/.well-known/jwks.json",
                cache_keys=True,
                lifespan=3600,
            )
    return _jwks_client


def _decode_supabase_jwt(token: str, pyjwt) -> dict:
    """
    Decode a Supabase JWT, trying ES256 (JWKS) first, then HS256 fallback.
    """
    decode_opts = {"verify_exp": True, "verify_aud": False}

    # --- Attempt 1: ES256 via JWKS (new Supabase default) ---
    jwks = _get_jwks_client()
    if jwks is not None:
        try:
            signing_key = jwks.get_signing_key_from_jwt(token)
            return pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                options=decode_opts,
            )
        except (pyjwt.InvalidTokenError, Exception) as e:
            logger.debug("ES256/JWKS decode failed, trying HS256: %s", e)

    # --- Attempt 2: HS256 with shared secret (legacy) ---
    jwt_secret = os.environ.get(
        "SUPABASE_JWT_SECRET",
        os.environ.get("EM_JWT_SECRET", ""),
    )
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")

    return pyjwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"],
        options=decode_opts,
    )


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
    min_bounty = Decimal("0.01")
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


def _format_wallet_display(wallet: str) -> str:
    """Format wallet as 'Agent 0x857f...3a2B'."""
    if not wallet or len(wallet) < 10:
        return f"Agent {wallet}"
    return f"Agent {wallet[:6]}...{wallet[-4:]}"


def _parse_int_safe(val) -> int:
    """Parse value to int, returning 0 on failure."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


@router.get(
    "/api/v1/agents/directory",
    response_model=AgentDirectoryResponse,
    summary="Agent Directory",
    description="Browse AI agents: publishers and executors. Public endpoint.",
    tags=["Agent Directory"],
)
async def get_agent_directory(
    capability: Optional[str] = Query(
        None, description="Filter by capability (comma-separated)"
    ),
    min_rating: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query(
        "rating",
        description="Sort by: rating, tasks_completed, display_name, tasks_published, total_bounty",
    ),
    role: Optional[str] = Query(
        None, description="Filter by role: publisher, executor, both"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Browse the public AI agent directory.

    Returns agents that are registered executors AND/OR task publishers.
    Merges both datasets by wallet address. No authentication required.
    """
    try:
        client = db.get_client()

        # --- 1. Query executor agents ---
        executor_map: dict = {}  # wallet_lower -> entry_dict
        try:
            eq_query = (
                client.table("executors")
                .select("*")
                .eq("executor_type", "agent")
                .not_.is_("display_name", "null")
            )
            exec_result = eq_query.execute()
            for row in exec_result.data or []:
                wallet = (row.get("wallet_address") or "").lower()
                if not wallet:
                    wallet = row["id"].lower()
                executor_map[wallet] = {
                    "executor_id": row["id"],
                    "display_name": row.get("display_name", "Unknown Agent"),
                    "capabilities": row.get("capabilities"),
                    "rating": row.get("reputation_score", 0) or 0,
                    "tasks_completed": row.get("tasks_completed", 0) or 0,
                    "avg_rating": row.get("avg_rating", 0) or 0,
                    "agent_card_url": row.get("agent_card_url"),
                    "mcp_endpoint_url": row.get("mcp_endpoint_url"),
                    "erc8004_agent_id": row.get("erc8004_agent_id"),
                    "verified": row.get("is_verified", False) or False,
                    "bio": row.get("bio"),
                    "avatar_url": row.get("avatar_url"),
                    "pricing": row.get("pricing"),
                    "is_executor": True,
                    "is_publisher": False,
                    "tasks_published": 0,
                    "total_bounty_usd": 0.0,
                    "active_tasks": 0,
                }
        except Exception as e:
            logger.warning("Failed to query executor agents: %s", e)

        # --- 2. Query publisher agents from tasks ---
        # We query ALL tasks that have an agent_id, regardless of publisher_type.
        # This catches AI agents that published tasks but aren't registered as executors.
        # Deduplication is done by erc8004_agent_id when available, falling back to agent_id.
        publisher_map: dict = {}  # dedup_key -> stats
        _erc8004_to_key: dict = {}  # erc8004_agent_id -> dedup_key (for cross-source dedup)
        try:
            pub_query = client.table("tasks").select(
                "agent_id, bounty_usd, status, agent_name, erc8004_agent_id, publisher_type"
            )
            pub_result = pub_query.execute()
            for row in pub_result.data or []:
                agent_id = (row.get("agent_id") or "").lower()
                if not agent_id:
                    continue
                # Skip human-published tasks
                pub_type = row.get("publisher_type")
                if pub_type == "human":
                    continue

                erc_id = _parse_int_safe(row.get("erc8004_agent_id")) or None

                # Determine dedup key: prefer erc8004_agent_id to merge
                # tasks from the same on-chain agent across different wallets
                if erc_id and erc_id in _erc8004_to_key:
                    dedup_key = _erc8004_to_key[erc_id]
                elif erc_id:
                    dedup_key = agent_id
                    _erc8004_to_key[erc_id] = dedup_key
                else:
                    dedup_key = agent_id

                if dedup_key not in publisher_map:
                    publisher_map[dedup_key] = {
                        "tasks_published": 0,
                        "total_bounty_usd": 0.0,
                        "active_tasks": 0,
                        "agent_name": row.get("agent_name"),
                        "erc8004_agent_id": erc_id,
                    }
                publisher_map[dedup_key]["tasks_published"] += 1
                publisher_map[dedup_key]["total_bounty_usd"] += float(
                    row.get("bounty_usd", 0) or 0
                )
                # Prefer a non-None agent_name over existing
                if row.get("agent_name") and not publisher_map[dedup_key].get(
                    "agent_name"
                ):
                    publisher_map[dedup_key]["agent_name"] = row["agent_name"]
                # Backfill erc8004_agent_id if we didn't have it
                if erc_id and not publisher_map[dedup_key].get("erc8004_agent_id"):
                    publisher_map[dedup_key]["erc8004_agent_id"] = erc_id
                status = row.get("status", "")
                if status in ("published", "accepted", "in_progress"):
                    publisher_map[dedup_key]["active_tasks"] += 1
        except Exception as e:
            logger.warning("Failed to query publisher tasks: %s", e)

        # --- 3. Merge datasets ---
        # Dedup across both sources using erc8004_agent_id when available.
        merged: dict = {}
        _erc8004_to_merged_key: dict = {}  # erc8004_agent_id -> merged key

        # Add executors
        for wallet, data in executor_map.items():
            erc_id = _parse_int_safe(data.get("erc8004_agent_id")) or None
            merged[wallet] = data.copy()
            if erc_id:
                _erc8004_to_merged_key[erc_id] = wallet

        # Add/merge publishers — match by wallet key OR erc8004_agent_id
        for agent_id, stats in publisher_map.items():
            erc_id = stats.get("erc8004_agent_id")

            # Find existing merged entry: direct key match or erc8004 cross-match
            merge_target = None
            if agent_id in merged:
                merge_target = agent_id
            elif erc_id and erc_id in _erc8004_to_merged_key:
                merge_target = _erc8004_to_merged_key[erc_id]

            if merge_target is not None:
                # Agent exists as executor — merge publisher stats
                merged[merge_target]["is_publisher"] = True
                merged[merge_target]["tasks_published"] = stats["tasks_published"]
                merged[merge_target]["total_bounty_usd"] = stats["total_bounty_usd"]
                merged[merge_target]["active_tasks"] = stats["active_tasks"]
                if erc_id and not merged[merge_target].get("erc8004_agent_id"):
                    merged[merge_target]["erc8004_agent_id"] = erc_id
            else:
                # Publisher-only agent — create entry from task data
                display = stats.get("agent_name") or (
                    f"Agent #{erc_id}" if erc_id else _format_wallet_display(agent_id)
                )
                merged[agent_id] = {
                    "executor_id": agent_id,
                    "display_name": display,
                    "capabilities": None,
                    "rating": 0,
                    "tasks_completed": 0,
                    "avg_rating": 0,
                    "agent_card_url": None,
                    "mcp_endpoint_url": None,
                    "erc8004_agent_id": erc_id,
                    "verified": False,
                    "bio": None,
                    "avatar_url": None,
                    "pricing": None,
                    "is_executor": False,
                    "is_publisher": True,
                    "tasks_published": stats["tasks_published"],
                    "total_bounty_usd": stats["total_bounty_usd"],
                    "active_tasks": stats["active_tasks"],
                }
                if erc_id:
                    _erc8004_to_merged_key[erc_id] = agent_id

        # --- 4. Assign roles ---
        for wallet, data in merged.items():
            if data.get("is_executor") and data.get("is_publisher"):
                data["role"] = "both"
            elif data.get("is_publisher"):
                data["role"] = "publisher"
            else:
                data["role"] = "executor"

        # --- 5. Apply filters ---
        entries = list(merged.values())

        if role and isinstance(role, str) and role != "all":
            entries = [e for e in entries if e["role"] == role]

        if capability:
            caps = [c.strip() for c in capability.split(",")]
            entries = [
                e
                for e in entries
                if e.get("capabilities") and any(c in e["capabilities"] for c in caps)
            ]

        if min_rating is not None:
            entries = [e for e in entries if e.get("rating", 0) >= min_rating]

        # --- 6. Sort ---
        if sort == "tasks_completed":
            entries.sort(key=lambda e: e.get("tasks_completed", 0), reverse=True)
        elif sort == "display_name":
            entries.sort(key=lambda e: (e.get("display_name") or "").lower())
        elif sort == "tasks_published":
            entries.sort(key=lambda e: e.get("tasks_published", 0), reverse=True)
        elif sort == "total_bounty":
            entries.sort(key=lambda e: e.get("total_bounty_usd", 0), reverse=True)
        else:
            entries.sort(key=lambda e: e.get("rating", 0), reverse=True)

        # --- 7. Paginate ---
        total_count = len(entries)
        offset = (page - 1) * limit
        page_entries = entries[offset : offset + limit]

        agents = []
        for data in page_entries:
            agents.append(
                AgentDirectoryEntry(
                    executor_id=data["executor_id"],
                    display_name=data["display_name"],
                    capabilities=data.get("capabilities"),
                    rating=data.get("rating", 0),
                    tasks_completed=data.get("tasks_completed", 0),
                    avg_rating=data.get("avg_rating", 0) or 0,
                    agent_card_url=data.get("agent_card_url"),
                    mcp_endpoint_url=data.get("mcp_endpoint_url"),
                    erc8004_agent_id=data.get("erc8004_agent_id"),
                    verified=data.get("verified", False),
                    bio=data.get("bio"),
                    avatar_url=data.get("avatar_url"),
                    pricing=data.get("pricing"),
                    role=data.get("role", "executor"),
                    tasks_published=data.get("tasks_published", 0),
                    total_bounty_usd=data.get("total_bounty_usd", 0.0),
                    active_tasks=data.get("active_tasks", 0),
                )
            )

        return AgentDirectoryResponse(
            agents=agents,
            total=total_count,
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
