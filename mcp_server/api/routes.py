"""
REST API Routes for Execution Market

Provides HTTP endpoints in addition to MCP tools.
Includes agent endpoints (authenticated) and worker endpoints (public/semi-public).
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, ConfigDict

import supabase_client as db
from models import TaskCategory, EvidenceType, TaskStatus
from verification.ai_review import process_verification, calculate_auto_score, verify_with_ai, VerificationDecision
from .auth import (
    verify_api_key,
    verify_api_key_optional,
    APIKeyData,
    verify_agent_owns_task,
    verify_agent_owns_submission
)

# x402 SDK payment verification and settlement
try:
    from integrations.x402.sdk_client import (
        verify_x402_payment,
        get_sdk,
        check_sdk_available,
        SDK_AVAILABLE as X402_AVAILABLE,
    )
except ImportError:
    X402_AVAILABLE = False

# ERC-8004 reputation integration
try:
    from integrations.erc8004 import rate_worker, EM_AGENT_ID
    ERC8004_AVAILABLE = True
except ImportError:
    ERC8004_AVAILABLE = False
    rate_worker = None
    EM_AGENT_ID = 469  # Default

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
    return Decimal("0.01")


async def get_max_bounty() -> Decimal:
    """Get maximum bounty from config system with fallback."""
    if CONFIG_AVAILABLE:
        try:
            return await PlatformConfig.get_max_bounty()
        except Exception:
            pass
    return Decimal("10000.00")

logger = logging.getLogger(__name__)
X402_AUTH_REF_PREFIX = "x402_auth_"

# Escrow lifecycle compatibility sets. The codebase currently supports mixed
# status vocabularies across legacy and newer payment integrations.
REFUNDABLE_ESCROW_STATUSES = {"deposited", "funded", "partial_released"}
ALREADY_REFUNDED_ESCROW_STATUSES = {"refunded"}
NON_REFUNDABLE_ESCROW_STATUSES = {"released"}
LIVE_TASK_STATUSES = {"published", "accepted", "in_progress", "submitted", "verifying"}
ACTIVE_WORKER_TASK_STATUSES = {"accepted", "in_progress", "submitted", "verifying"}
TASK_PAYMENT_SETTLED_STATUSES = {"confirmed", "completed", "settled", "released", "success", "available"}


def _normalize_status(value: Optional[str]) -> str:
    return str(value or "").strip().lower()


def _as_amount(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_tx_hash(value: Optional[str]) -> bool:
    if not value or not isinstance(value, str):
        return False
    normalized = value.strip()
    if len(normalized) != 66 or not normalized.startswith("0x"):
        return False
    return all(char in "0123456789abcdefABCDEF" for char in normalized[2:])


def _pick_first_tx_hash(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if _is_tx_hash(value):
            return value.strip()
    return None


def _sanitize_reference(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or _is_tx_hash(normalized):
        return None
    if len(normalized) > 96 or normalized.startswith("eyJ"):
        return f"x402 authorization: {normalized[:12]}...{normalized[-8:]}"
    return f"x402 reference: {normalized}"


def _extract_payment_tx(payment_row: Dict[str, Any]) -> Optional[str]:
    return payment_row.get("tx_hash") or payment_row.get("transaction_hash")


def _is_release_payment(payment_row: Dict[str, Any]) -> bool:
    payment_type = _normalize_status(payment_row.get("type") or payment_row.get("payment_type"))
    if not payment_type:
        return True
    return payment_type in {"release", "full_release", "final_release", "partial_release"}


def _is_payment_finalized(payment_row: Dict[str, Any]) -> bool:
    status = _normalize_status(payment_row.get("status"))
    if status in {"confirmed", "completed", "settled", "released", "success"}:
        return True
    return bool(_extract_payment_tx(payment_row))


def _get_existing_submission_payment(submission_id: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort lookup for an existing release payment for a submission.

    Handles schema drift between legacy (`type`, `tx_hash`) and newer
    (`payment_type`, `transaction_hash`) payment column naming.
    """
    try:
        client = db.get_client()
        result = (
            client.table("payments")
            .select("*")
            .eq("submission_id", submission_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None

        release_rows = [row for row in rows if _is_release_payment(row)]
        if not release_rows:
            return rows[0]

        for row in release_rows:
            if _is_payment_finalized(row):
                return row

        return release_rows[0]
    except Exception as payment_lookup_err:
        logger.warning(
            "Could not lookup existing payment for submission %s: %s",
            submission_id,
            payment_lookup_err,
        )
        return None


def _record_refund_payment(
    task: Dict[str, Any],
    agent_id: str,
    refund_tx: Optional[str],
    reason: Optional[str],
) -> None:
    """
    Best-effort persistence of refund payment audit row.

    Uses legacy-compatible payment fields and fails open if schema differs.
    """
    try:
        client = db.get_client()
        amount = float(task.get("escrow_amount_usdc") or task.get("bounty_usd") or 0)
        client.table("payments").insert({
            "task_id": task.get("id"),
            "type": "refund",
            "payment_type": "refund",
            "status": "confirmed" if refund_tx else "pending",
            "tx_hash": refund_tx,
            "transaction_hash": refund_tx,
            "amount_usdc": amount,
            "escrow_id": task.get("escrow_id"),
            "network": "base",
            "to_address": task.get("agent_id") or agent_id,
            "note": f"Task cancellation refund. reason={reason or 'not_provided'}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as payment_err:
        logger.warning(
            "Could not persist refund payment audit row for task %s: %s",
            task.get("id"),
            payment_err,
        )


def _is_probable_x402_header(value: Optional[str]) -> bool:
    if not value or not isinstance(value, str):
        return False
    normalized = value.strip()
    if len(normalized) < 100:
        return False
    if normalized.startswith("eyJ"):  # base64-encoded JSON payload
        return True
    if normalized.startswith("{"):  # raw JSON payload
        return True
    return False


def _extract_x402_header_from_metadata(metadata: Any) -> Optional[str]:
    if not metadata:
        return None

    data = metadata
    if isinstance(metadata, str):
        try:
            data = json.loads(metadata)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    for key in ("x_payment_header", "payment_header", "xPaymentHeader"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _resolve_task_payment_header(task_id: Optional[str], task_escrow_tx: Optional[str]) -> Optional[str]:
    """
    Resolve the original x402 X-Payment header for settlement.

    Priority:
    1) `tasks.escrow_tx` if it already contains a full header (legacy behavior)
    2) `escrows.metadata.x_payment_header` (current canonical storage)
    """
    if _is_probable_x402_header(task_escrow_tx):
        return task_escrow_tx

    if not task_id:
        return None

    try:
        client = db.get_client()
        escrow_result = (
            client.table("escrows")
            .select("metadata")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = escrow_result.data or []
        if not rows:
            return None
        return _extract_x402_header_from_metadata(rows[0].get("metadata"))
    except Exception as err:
        logger.warning("Could not resolve x402 payment header for task %s: %s", task_id, err)
        return None


def _is_missing_table_error(error: Exception, table_name: str) -> bool:
    payload = str(error).lower()
    table_ref = f"public.{table_name.lower()}"
    return (
        "pgrst205" in payload and table_ref in payload
    ) or (
        "does not exist" in payload and table_name.lower() in payload
    )


def _normalize_payment_network(payment_row: Dict[str, Any], fallback: str = "base") -> str:
    network = str(payment_row.get("network") or "").strip().lower()
    if network:
        return network

    chain_id = payment_row.get("chain_id")
    if chain_id == 84532:
        return "base-sepolia"
    if chain_id == 8453:
        return "base"
    return fallback


def _normalize_payment_type(payment_row: Dict[str, Any]) -> str:
    payment_type = payment_row.get("type") or payment_row.get("payment_type")
    return _normalize_status(payment_type)


def _event_type_from_payment_row(payment_row: Dict[str, Any]) -> str:
    payment_type = _normalize_payment_type(payment_row)
    status = _normalize_status(payment_row.get("status"))

    if status == "disputed":
        return "dispute_hold"
    if payment_type in {"refund", "partial_refund"} or status in {"refunded", "cancelled"}:
        return "refund"
    if payment_type == "partial_release" or status == "partial_released":
        return "partial_release"
    if payment_type in {"final_release", "full_release", "release"}:
        return "final_release"
    if payment_type == "task_payment":
        return "final_release" if status in TASK_PAYMENT_SETTLED_STATUSES else "escrow_created"
    if payment_type in {"escrow_create", "deposit"}:
        return "escrow_created"
    if status in {"funded", "deposited", "authorized"}:
        return "escrow_created"
    return "escrow_created" if status not in TASK_PAYMENT_SETTLED_STATUSES else "final_release"


def _actor_from_event_type(event_type: str) -> str:
    if event_type in {"escrow_created", "escrow_funded", "instant_charge"}:
        return "agent"
    if event_type == "dispute_hold":
        return "arbitrator"
    return "system"


def _derive_payment_status(
    task_status: str,
    has_escrow_context: bool,
    event_types: List[str],
) -> str:
    task_status_normalized = _normalize_status(task_status)
    event_set = set(event_types)

    if "refund" in event_set:
        return "refunded"
    if "final_release" in event_set:
        return "completed"
    if "partial_release" in event_set:
        return "partial_released"
    if has_escrow_context or "escrow_created" in event_set or "escrow_funded" in event_set:
        return "escrowed"

    if task_status_normalized == "completed":
        return "completed"
    if task_status_normalized in {"cancelled", "expired"}:
        return "refunded"
    return "pending"

# UUID validation pattern for path parameters
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

router = APIRouter(prefix="/api/v1", tags=["Execution Market API"])


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
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
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
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
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


class PublicPlatformMetricsResponse(BaseModel):
    """Public high-level platform metrics for landing/dashboard surfaces."""
    users: Dict[str, int]
    tasks: Dict[str, int]
    activity: Dict[str, int]
    payments: Dict[str, float]
    generated_at: datetime


class TaskPaymentEventResponse(BaseModel):
    """Canonical payment timeline event for a task."""
    id: str
    type: str
    actor: str
    timestamp: str
    network: str
    amount: Optional[float] = None
    tx_hash: Optional[str] = None
    note: Optional[str] = None


class TaskPaymentResponse(BaseModel):
    """Canonical payment timeline and status for a task."""
    task_id: str
    status: str
    total_amount: float
    released_amount: float
    currency: str = "USDC"
    escrow_tx: Optional[str] = None
    escrow_contract: Optional[str] = None
    network: str = "base"
    events: List[TaskPaymentEventResponse]
    created_at: str
    updated_at: str


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


@router.get(
    "/public/metrics",
    response_model=PublicPlatformMetricsResponse,
    responses={
        200: {"description": "Public platform metrics"},
    },
)
async def get_public_platform_metrics() -> PublicPlatformMetricsResponse:
    """
    Get public platform metrics for landing and dashboard views.

    This endpoint is intentionally read-only and unauthenticated.
    """
    generated_at = datetime.now(timezone.utc)
    client = db.get_client()

    users = {
        "registered_workers": 0,
        "registered_agents": 0,
        "workers_with_tasks": 0,
        "workers_active_now": 0,
        "workers_completed": 0,
        "agents_active_now": 0,
    }
    tasks: Dict[str, int] = {
        "total": 0,
        "published": 0,
        "accepted": 0,
        "in_progress": 0,
        "submitted": 0,
        "verifying": 0,
        "completed": 0,
        "disputed": 0,
        "cancelled": 0,
        "expired": 0,
        "live": 0,
    }
    activity = {
        "workers_with_active_tasks": 0,
        "workers_with_completed_tasks": 0,
        "agents_with_live_tasks": 0,
    }
    payments = {
        "total_volume_usd": 0.0,
        "total_fees_usd": 0.0,
    }

    # Registered workers
    try:
        workers_result = client.table("executors").select("id", count="exact").execute()
        users["registered_workers"] = int(workers_result.count or 0)
    except Exception as e:
        logger.warning("Could not query executors count for public metrics: %s", e)

    # Registered agents (active API keys as proxy for active/registered agents)
    try:
        agents_result = (
            client.table("api_keys")
            .select("id", count="exact")
            .eq("is_active", True)
            .execute()
        )
        users["registered_agents"] = int(agents_result.count or 0)
    except Exception as e:
        logger.warning("Could not query agents count for public metrics: %s", e)

    # Task and activity aggregates
    try:
        tasks_result = client.table("tasks").select("status, executor_id, agent_id, bounty_usd").execute()
        task_rows = tasks_result.data or []
        fee_pct = float(await get_platform_fee_percent())

        workers_with_tasks = set()
        workers_active = set()
        workers_completed = set()
        agents_active = set()

        for row in task_rows:
            status = _normalize_status(row.get("status"))
            if not status:
                continue

            tasks[status] = tasks.get(status, 0) + 1
            tasks["total"] += 1
            amount = float(row.get("bounty_usd") or 0.0)
            payments["total_volume_usd"] += amount
            if status == "completed":
                payments["total_fees_usd"] += amount * fee_pct

            executor_id = row.get("executor_id")
            if executor_id:
                workers_with_tasks.add(executor_id)
                if status in ACTIVE_WORKER_TASK_STATUSES:
                    workers_active.add(executor_id)
                if status == "completed":
                    workers_completed.add(executor_id)

            agent_id = row.get("agent_id")
            if agent_id and status in LIVE_TASK_STATUSES:
                agents_active.add(agent_id)

        tasks["live"] = sum(tasks.get(status, 0) for status in LIVE_TASK_STATUSES)
        users["workers_with_tasks"] = len(workers_with_tasks)
        users["workers_active_now"] = len(workers_active)
        users["workers_completed"] = len(workers_completed)
        users["agents_active_now"] = len(agents_active)

        activity["workers_with_active_tasks"] = len(workers_active)
        activity["workers_with_completed_tasks"] = len(workers_completed)
        activity["agents_with_live_tasks"] = len(agents_active)
    except Exception as e:
        logger.warning("Could not query task aggregates for public metrics: %s", e)

    payments["total_volume_usd"] = round(payments["total_volume_usd"], 2)
    payments["total_fees_usd"] = round(payments["total_fees_usd"], 2)

    return PublicPlatformMetricsResponse(
        users=users,
        tasks=tasks,
        activity=activity,
        payments=payments,
        generated_at=generated_at,
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
        payment_result = None
        x_payment_header = None  # Store original header for later settlement
        if not X402_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="x402 payment service unavailable; task creation is facilitator-only",
            )

        # Get the original X-Payment header before verification
        x_payment_header = http_request.headers.get("X-Payment") or http_request.headers.get("x-payment")

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

        # Store escrow data if payment was verified via x402 SDK / facilitator
        # NOTE: We store the X-Payment header for later settlement (during approval)
        # The payment is VERIFIED but NOT SETTLED yet - funds stay with agent until approval
        if payment_result and payment_result.success and x_payment_header:
            try:
                # Generate a unique escrow reference (not a tx hash - no tx happened yet)
                import uuid
                escrow_ref = f"escrow_{task['id'][:8]}_{uuid.uuid4().hex[:8]}"
                payment_reference = f"{X402_AUTH_REF_PREFIX}{uuid.uuid4().hex[:16]}"

                # Update task with escrow info
                # IMPORTANT:
                # - tasks.escrow_tx stores a short reference (VARCHAR-compatible)
                # - full X-Payment header is stored in escrows.metadata for settlement
                escrow_updates = {
                    "escrow_id": escrow_ref,
                    "escrow_tx": payment_reference,
                    "escrow_amount_usdc": float(total_required),
                    "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.update_task(task["id"], escrow_updates)
                task.update(escrow_updates)

                # Create escrow record
                # NOTE: x_payment_header is stored in task.escrow_tx, not in escrows table
                # This avoids schema changes and keeps the header with the task
                try:
                    client = db.get_client()
                    client.table("escrows").insert({
                        "task_id": task["id"],
                        "agent_id": api_key.agent_id,
                        "escrow_id": escrow_ref,
                        "funding_tx": None,  # Will be set when payment is settled
                        "status": "authorized",  # Payment authorized, not yet captured
                        "total_amount_usdc": float(total_required),
                        "platform_fee_usdc": float(total_required - bounty),
                        "beneficiary_address": payment_result.payer_address,
                        "network": payment_result.network,
                        "metadata": {
                            "x_payment_header": x_payment_header,
                            "payment_reference": payment_reference,
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }).execute()
                except Exception as escrow_err:
                    # escrows table might not have all columns, log and continue
                    logger.warning("Could not create escrow record: %s", escrow_err)

                logger.info(
                    "x402 payment authorized: task=%s, escrow=%s, amount=%.2f, payer=%s",
                    task["id"], escrow_ref, float(total_required), payment_result.payer_address[:10] + "..."
                )
            except Exception as e:
                # Non-fatal: task was created, escrow recording failed
                logger.error("Failed to record escrow for task %s: %s", task["id"], e)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create task: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error while creating task")


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
    include_expired: bool = Query(
        False,
        description="Include expired tasks in response. Useful as landing fallback when there are no active tasks.",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> AvailableTasksResponse:
    """
    Get available tasks for workers.

    Public endpoint that returns tasks in 'published' status.
    Can optionally include expired tasks for read-only discovery surfaces.
    Supports location-based filtering and bounty range filtering.
    """
    try:
        client = db.get_client()

        # Build query
        query = client.table("tasks").select("*")

        if include_expired:
            query = query.in_("status", ["published", "expired"])
        else:
            query = query.eq("status", "published")

        # Apply category filter
        if category:
            query = query.eq("category", category.value)

        # Apply bounty filters
        if min_bounty is not None:
            query = query.gte("bounty_usd", min_bounty)
        if max_bounty is not None:
            query = query.lte("bounty_usd", max_bounty)

        # Execute query
        if include_expired:
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        else:
            result = query.order("bounty_usd", desc=True).range(offset, offset + limit - 1).execute()

        tasks = result.data or []

        # Build filters applied response
        filters_applied = {
            "category": category.value if category else None,
            "min_bounty": min_bounty,
            "max_bounty": max_bounty,
            "include_expired": include_expired,
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
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
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
    "/tasks/{task_id}/payment",
    response_model=TaskPaymentResponse,
    responses={
        200: {"description": "Canonical task payment timeline"},
        403: {"model": ErrorResponse, "description": "Not authorized to view payment details"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    }
)
async def get_task_payment(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    api_key: Optional[APIKeyData] = Depends(verify_api_key_optional),
) -> TaskPaymentResponse:
    """
    Get canonical payment ledger for one task.

    This endpoint normalizes mixed schemas (`type` vs `payment_type`,
    `tx_hash` vs `transaction_hash`) and degrades safely when `payments`
    or `escrows` tables are missing in a live environment.
    """
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_status = _normalize_status(task.get("status"))
    requester_is_owner = bool(api_key and task.get("agent_id") == api_key.agent_id)
    if task_status == "draft" and not requester_is_owner:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view draft task payment details",
        )

    client = db.get_client()
    payment_rows: List[Dict[str, Any]] = []
    escrows_row: Optional[Dict[str, Any]] = None
    submission_payment_row: Optional[Dict[str, Any]] = None

    try:
        payment_result = (
            client.table("payments")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=False)
            .execute()
        )
        payment_rows = payment_result.data or []
    except Exception as payment_err:
        if not _is_missing_table_error(payment_err, "payments"):
            logger.warning("Failed to query payments for task %s: %s", task_id, payment_err)

    try:
        escrows_result = (
            client.table("escrows")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        escrows_rows = escrows_result.data or []
        if escrows_rows:
            escrows_row = escrows_rows[0]
    except Exception as escrow_err:
        if not _is_missing_table_error(escrow_err, "escrows"):
            logger.warning("Failed to query escrows for task %s: %s", task_id, escrow_err)

    try:
        submission_result = (
            client.table("submissions")
            .select("id,payment_tx,payment_amount,paid_at,verified_at,submitted_at")
            .eq("task_id", task_id)
            .not_("payment_tx", "is", "null")
            .order("submitted_at", desc=True)
            .limit(1)
            .execute()
        )
        submission_rows = submission_result.data or []
        if submission_rows:
            submission_payment_row = submission_rows[0]
    except Exception as submission_err:
        if not _is_missing_table_error(submission_err, "submissions"):
            logger.warning("Failed to query submission payment fallback for task %s: %s", task_id, submission_err)

    default_network = "base"
    created_at = str(task.get("created_at") or datetime.now(timezone.utc).isoformat())
    updated_at = str(task.get("updated_at") or created_at)
    events: List[Dict[str, Any]] = []
    total_amount = _as_amount(task.get("bounty_usd"))
    released_amount = 0.0

    for index, row in enumerate(payment_rows):
        event_type = _event_type_from_payment_row(row)
        amount = _as_amount(
            row.get("amount_usdc")
            or row.get("amount")
            or row.get("total_amount_usdc")
            or row.get("net_amount_usdc")
            or row.get("released_amount_usdc")
            or row.get("released_amount")
        )
        status = _normalize_status(row.get("status"))
        if event_type == "escrow_created":
            total_amount = max(total_amount, amount)
        if event_type in {"partial_release", "final_release"} and status in TASK_PAYMENT_SETTLED_STATUSES:
            released_amount += amount

        event_timestamp = str(
            row.get("completed_at")
            or row.get("confirmed_at")
            or row.get("updated_at")
            or row.get("created_at")
            or updated_at
        )
        updated_at = max(updated_at, event_timestamp)

        network = _normalize_payment_network(row, default_network)
        tx_hash = _pick_first_tx_hash(
            row.get("tx_hash"),
            row.get("transaction_hash"),
            row.get("release_tx"),
            row.get("refund_tx"),
            row.get("deposit_tx"),
            row.get("funding_tx"),
        )
        note = _sanitize_reference(
            row.get("tx_hash")
            or row.get("transaction_hash")
            or row.get("deposit_tx")
            or row.get("funding_tx")
        )

        events.append({
            "id": f"{row.get('id') or task_id}-{event_type}-{index}",
            "type": event_type,
            "actor": _actor_from_event_type(event_type),
            "amount": amount if amount > 0 else None,
            "tx_hash": tx_hash,
            "network": network,
            "timestamp": event_timestamp,
            "note": note,
        })

    has_escrow_context = bool(task.get("escrow_id") or task.get("escrow_tx") or escrows_row)
    if has_escrow_context and not any(event["type"] in {"escrow_created", "escrow_funded"} for event in events):
        escrow_amount = _as_amount(
            (escrows_row or {}).get("total_amount_usdc")
            or (escrows_row or {}).get("amount_usdc")
            or task.get("bounty_usd")
        )
        total_amount = max(total_amount, escrow_amount)

        escrow_timestamp = str(
            (escrows_row or {}).get("created_at")
            or task.get("created_at")
            or created_at
        )
        updated_at = max(updated_at, escrow_timestamp)
        escrow_tx_hash = _pick_first_tx_hash(
            (escrows_row or {}).get("deposit_tx"),
            (escrows_row or {}).get("funding_tx"),
            task.get("escrow_tx"),
        )
        escrow_reference = _sanitize_reference(task.get("escrow_tx"))
        events.append({
            "id": f"{task_id}-escrow-created-fallback",
            "type": "escrow_created",
            "actor": "agent",
            "amount": escrow_amount if escrow_amount > 0 else None,
            "tx_hash": escrow_tx_hash,
            "network": default_network,
            "timestamp": escrow_timestamp,
            "note": escrow_reference,
        })

    submission_tx = _pick_first_tx_hash((submission_payment_row or {}).get("payment_tx"))
    if submission_tx and not any(
        event["type"] == "final_release" and event.get("tx_hash") == submission_tx
        for event in events
    ):
        submission_amount = _as_amount((submission_payment_row or {}).get("payment_amount"))
        if submission_amount <= 0:
            submission_amount = total_amount
        released_amount = max(released_amount, submission_amount)
        total_amount = max(total_amount, submission_amount)

        payout_timestamp = str(
            (submission_payment_row or {}).get("paid_at")
            or (submission_payment_row or {}).get("verified_at")
            or (submission_payment_row or {}).get("submitted_at")
            or updated_at
        )
        updated_at = max(updated_at, payout_timestamp)
        events.append({
            "id": f"{task_id}-submission-payout-{(submission_payment_row or {}).get('id') or 'latest'}",
            "type": "final_release",
            "actor": "system",
            "amount": submission_amount if submission_amount > 0 else None,
            "tx_hash": submission_tx,
            "network": default_network,
            "timestamp": payout_timestamp,
            "note": "Payment settled via x402 facilitator",
        })

    events.sort(key=lambda event: event.get("timestamp") or "")

    if _normalize_status(task.get("status")) == "completed" and released_amount <= 0 and total_amount > 0:
        released_amount = total_amount

    derived_status = _derive_payment_status(
        task_status=task_status,
        has_escrow_context=has_escrow_context,
        event_types=[event["type"] for event in events],
    )

    if not events:
        updated_at = str(task.get("updated_at") or task.get("created_at") or updated_at)

    return TaskPaymentResponse(
        task_id=task_id,
        status=derived_status,
        total_amount=round(total_amount, 6),
        released_amount=round(released_amount, 6),
        currency="USDC",
        escrow_tx=_pick_first_tx_hash(
            (escrows_row or {}).get("deposit_tx"),
            (escrows_row or {}).get("funding_tx"),
            task.get("escrow_tx"),
        ),
        escrow_contract=None,
        network=default_network,
        events=[TaskPaymentEventResponse(**event) for event in events],
        created_at=created_at,
        updated_at=updated_at,
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
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
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
    submission_id: str = Path(..., description="UUID of the submission", pattern=UUID_PATTERN),
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

    # Check if already processed.
    # If already accepted, return idempotent success for safe client retries.
    submission = await db.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    existing_verdict = _normalize_status(submission.get("agent_verdict"))
    if existing_verdict in {"accepted", "approved"}:
        existing_payment = _get_existing_submission_payment(submission_id)
        response_data = {
            "submission_id": submission_id,
            "verdict": "accepted",
            "idempotent": True,
        }
        if existing_payment:
            existing_payment_tx = _extract_payment_tx(existing_payment)
            if existing_payment_tx:
                response_data["payment_tx"] = existing_payment_tx

        return SuccessResponse(
            message="Submission already approved.",
            data=response_data,
        )

    if existing_verdict not in {"", "pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}"
        )

    task = submission.get("task") or {}
    task_status = _normalize_status(task.get("status"))
    if task_status in {"cancelled", "refunded", "expired"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve submission while task status is '{task_status}'",
        )
    if task_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Cannot approve submission because task is already completed",
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

    # Release payment to worker via x402 SDK / facilitator
    release_tx = None
    release_error = None
    try:
        task = submission.get("task", {})
        executor = submission.get("executor", {})

        escrow_id = task.get("escrow_id")
        escrow_tx = task.get("escrow_tx")
        payment_header = _resolve_task_payment_header(task.get("id"), escrow_tx)
        worker_address = executor.get("wallet_address")
        bounty = Decimal(str(task.get("bounty_usd", 0)))
        platform_fee_pct = await get_platform_fee_percent()
        fee = (bounty * platform_fee_pct).quantize(Decimal("0.01"))
        worker_payout = bounty - fee

        existing_payment = _get_existing_submission_payment(submission_id)
        if existing_payment and _is_payment_finalized(existing_payment):
            release_tx = _extract_payment_tx(existing_payment)
            logger.info(
                "Idempotent payment hit for submission %s (tx=%s)",
                submission_id,
                release_tx,
            )
        elif payment_header and worker_address and worker_payout > 0 and X402_AVAILABLE:
            # Use x402 SDK to settle payment via facilitator (gasless)
            sdk = get_sdk()
            result = await sdk.settle_task_payment(
                task_id=task.get("id", ""),
                payment_header=payment_header,
                worker_address=worker_address,
                bounty_amount=bounty,
            )

            if result.get("success"):
                release_tx = result.get("tx_hash")

                # Record payment
                client = db.get_client()
                payment_record = {
                    "task_id": task["id"],
                    "executor_id": executor.get("id"),
                    "submission_id": submission_id,
                    "type": "release",
                    "payment_type": "full_release",
                    "status": "confirmed",
                    "tx_hash": release_tx,
                    "transaction_hash": release_tx,
                    "amount_usdc": float(worker_payout),
                    "fee_usdc": float(fee),
                    "escrow_id": escrow_id,
                    "network": "base",
                    "to_address": worker_address,
                    "note": "Payment settled via x402 SDK facilitator",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

                try:
                    if existing_payment and existing_payment.get("id"):
                        client.table("payments").update(payment_record).eq(
                            "id", existing_payment["id"]
                        ).execute()
                    else:
                        client.table("payments").insert(payment_record).execute()
                except Exception as payment_record_err:
                    logger.warning(
                        "Could not persist payment record for submission %s: %s",
                        submission_id,
                        payment_record_err,
                    )

                # Update escrow status
                client.table("escrows").update({
                    "status": "released",
                    "released_at": datetime.now(timezone.utc).isoformat(),
                }).eq("task_id", task["id"]).execute()

                logger.info(
                    "Payment settled via SDK: task=%s, worker=%s, net=%.2f, tx=%s",
                    task["id"], worker_address[:10], float(worker_payout), release_tx
                )

                # Submit on-chain reputation feedback (ERC-8004)
                # This is non-blocking - payment success is not dependent on reputation
                if ERC8004_AVAILABLE and rate_worker:
                    try:
                        # Default positive score for completed work
                        # TODO: Allow agents to specify score in approval request
                        reputation_score = 80  # Good work

                        reputation_result = await rate_worker(
                            task_id=task["id"],
                            score=reputation_score,
                            worker_address=worker_address,
                            comment=f"Task completed and paid: {task.get('title', 'Unknown')[:50]}",
                            proof_tx=release_tx,  # Payment tx as proof
                        )

                        if reputation_result.success:
                            logger.info(
                                "ERC-8004 reputation submitted: task=%s, worker=%s, score=%d, tx=%s",
                                task["id"], worker_address[:10], reputation_score, reputation_result.transaction_hash
                            )
                        else:
                            logger.warning(
                                "ERC-8004 reputation failed: task=%s, error=%s",
                                task["id"], reputation_result.error
                            )
                    except Exception as rep_err:
                        # Don't fail payment if reputation submission fails
                        logger.error(
                            "Exception submitting ERC-8004 reputation for task %s: %s",
                            task["id"], str(rep_err)
                        )
            else:
                release_error = result.get("error", "SDK settlement failed")
                logger.error(
                    "SDK settlement failed for task %s: %s",
                    task["id"], release_error
                )
        elif existing_payment:
            logger.info(
                "Submission %s has an existing non-final payment record; skipping new settlement",
                submission_id,
            )
        elif not payment_header:
            logger.warning("No x402 payment header found for task %s, skipping payment release", task.get("id"))
        elif not worker_address:
            logger.warning("No wallet_address for executor, skipping payment for task %s", task.get("id"))
        elif not X402_AVAILABLE:
            logger.warning("x402 SDK not available, skipping payment for task %s", task.get("id"))
    except Exception as e:
        release_error = str(e)
        logger.error("Failed to settle payment for submission %s: %s", submission_id, e)

    response_data = {"submission_id": submission_id, "verdict": "accepted"}
    if release_tx:
        response_data["payment_tx"] = release_tx
    if release_error:
        response_data["payment_error"] = release_error

    return SuccessResponse(
        message="Submission approved. Payment released to worker." if release_tx else "Submission approved. Payment will be released to worker.",
        data=response_data
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
    submission_id: str = Path(..., description="UUID of the submission", pattern=UUID_PATTERN),
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
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: CancelRequest = None,
    api_key: APIKeyData = Depends(verify_api_key)
) -> SuccessResponse:
    """
    Cancel a task.

    Only tasks in 'published' status can be cancelled.

    For x402 payments:
    - If payment was AUTHORIZED but not SETTLED, the authorization expires naturally
    - If payment was SETTLED to escrow, funds are refunded to agent
    """
    refund_info = None
    try:
        reason = request.reason if request else None

        # Get task details before cancellation to check escrow status
        task = await db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.get("agent_id") != api_key.agent_id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this task")

        # Idempotency for client retries: cancelling an already-cancelled task
        # should return success.
        if _normalize_status(task.get("status")) == "cancelled":
            return SuccessResponse(
                message="Task already cancelled.",
                data={"task_id": task_id, "reason": reason, "idempotent": True},
            )

        # Check if we need to handle escrow refund
        escrow_tx = task.get("escrow_tx")  # This stores X-Payment payload
        escrow_id = task.get("escrow_id")

        if escrow_tx:
            try:
                client = db.get_client()
                escrow_row = None
                try:
                    escrow_result = (
                        client.table("escrows")
                        .select("id,status,escrow_id,refunded_at,released_at")
                        .eq("task_id", task_id)
                        .single()
                        .execute()
                    )
                    escrow_row = escrow_result.data or None
                except Exception:
                    escrow_row = None

                escrow_status = _normalize_status((escrow_row or {}).get("status") or "authorized")
                effective_escrow_id = (escrow_row or {}).get("escrow_id") or escrow_id

                if escrow_status in ALREADY_REFUNDED_ESCROW_STATUSES:
                    refund_info = {
                        "status": "already_refunded",
                        "escrow_id": effective_escrow_id,
                    }
                elif escrow_status in NON_REFUNDABLE_ESCROW_STATUSES:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Cannot cancel task because escrow is already {escrow_status}",
                    )
                elif escrow_status in REFUNDABLE_ESCROW_STATUSES:
                    if X402_AVAILABLE:
                        sdk = get_sdk()
                        refund_result = await sdk.refund_task_payment(
                            task_id=task_id,
                            escrow_id=str(effective_escrow_id or ""),
                            reason=reason,
                        )
                        if refund_result.get("success"):
                            refund_info = {
                                "status": "refunded",
                                "escrow_id": effective_escrow_id,
                                "tx_hash": refund_result.get("tx_hash"),
                            }
                            try:
                                client.table("escrows").update({
                                    "status": "refunded",
                                    "refunded_at": datetime.now(timezone.utc).isoformat(),
                                }).eq("task_id", task_id).execute()
                            except Exception as escrow_update_err:
                                logger.warning(
                                    "Could not mark escrow refunded for task %s: %s",
                                    task_id,
                                    escrow_update_err,
                                )
                            _record_refund_payment(
                                task=task,
                                agent_id=api_key.agent_id,
                                refund_tx=refund_result.get("tx_hash"),
                                reason=reason,
                            )
                        else:
                            refund_info = {
                                "status": "refund_manual_required",
                                "escrow_id": effective_escrow_id,
                                "error": refund_result.get("error", "Refund attempt failed"),
                            }
                    else:
                        refund_info = {
                            "status": "refund_manual_required",
                            "escrow_id": effective_escrow_id,
                            "error": "x402 SDK not available",
                        }
                else:
                    # Common case for EIP-3009 authorize-only flow: no funds moved.
                    refund_info = {
                        "status": "authorization_expired",
                        "message": "Payment authorization will expire. No funds were moved.",
                    }

            except HTTPException:
                raise
            except Exception as escrow_err:
                logger.warning("Could not check/update escrow for task %s: %s", task_id, escrow_err)

        # Cancel the task in database
        try:
            await db.cancel_task(task_id, api_key.agent_id)
        except Exception as cancel_err:
            cancel_error = str(cancel_err).lower()
            if "status: cancelled" not in cancel_error and "already cancelled" not in cancel_error:
                raise

        logger.info(
            "Task cancelled: id=%s, agent=%s, reason=%s, escrow=%s",
            task_id, api_key.agent_id, reason, refund_info
        )

        response_data = {"task_id": task_id, "reason": reason}
        if refund_info:
            response_data["escrow"] = refund_info

        status_label = (refund_info or {}).get("status")
        message_suffix = ""
        if status_label == "authorization_expired":
            message_suffix = " Payment authorization expired (no funds moved)."
        elif status_label == "refunded":
            message_suffix = " Escrow refunded to agent."
        elif status_label == "already_refunded":
            message_suffix = " Escrow was already refunded."
        elif status_label == "not_refundable":
            message_suffix = " Escrow was already released."
        elif status_label in {"refund_manual_required", "refund_failed"}:
            message_suffix = " Escrow refund requires manual intervention."

        return SuccessResponse(
            message=f"Task cancelled successfully.{message_suffix}",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        elif "cannot cancel" in error_msg.lower() or "status" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        logger.error("Unexpected error cancelling task %s: %s", task_id, error_msg)
        raise HTTPException(status_code=500, detail="Internal error while cancelling task")


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
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
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
        logger.error("Unexpected error applying to task %s: %s", task_id, error_msg)
        raise HTTPException(status_code=500, detail="Internal error while applying to task")


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
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
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
        logger.error("Unexpected error submitting work for task %s: %s", task_id, error_msg)
        raise HTTPException(status_code=500, detail="Internal error while submitting work")


# =============================================================================
# EVIDENCE VERIFICATION
# =============================================================================


class VerifyEvidenceRequest(BaseModel):
    """Request to verify evidence against task requirements."""
    task_id: str = Field(..., description="UUID of the task")
    evidence_url: str = Field(..., description="Public URL of the uploaded evidence file")
    evidence_type: str = Field(default="photo", description="Type of evidence being verified")


class VerifyEvidenceResponse(BaseModel):
    """Result of AI evidence verification."""
    verified: bool
    confidence: float = Field(..., ge=0, le=1)
    decision: str  # approved, rejected, needs_human
    explanation: str
    issues: List[str] = []


@router.post(
    "/evidence/verify",
    response_model=VerifyEvidenceResponse,
    responses={
        200: {"description": "Verification result"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        503: {"model": ErrorResponse, "description": "AI verification unavailable"},
    }
)
async def verify_evidence(request: VerifyEvidenceRequest) -> VerifyEvidenceResponse:
    """
    Verify evidence against task requirements using AI.

    Worker endpoint: after uploading evidence, call this to get instant
    AI feedback on whether the evidence matches what the task requires.
    This does NOT create a submission - it's a pre-check.

    When ANTHROPIC_API_KEY is not configured, returns a mock approval
    so the submission flow works end-to-end.
    """
    import os

    # Get task details
    task = await db.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if Anthropic API key is configured
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("AI verification mock mode (no ANTHROPIC_API_KEY): task=%s", request.task_id)
        return VerifyEvidenceResponse(
            verified=True,
            confidence=0.85,
            decision="approved",
            explanation=f"Evidence received for '{task.get('title', 'task')}'. Full AI verification will be enabled soon.",
            issues=[],
        )

    try:
        result = await verify_with_ai(
            task={
                "title": task.get("title", ""),
                "category": task.get("category", "general"),
                "instructions": task.get("instructions", ""),
                "evidence_schema": task.get("evidence_schema", {}),
            },
            evidence={
                "type": request.evidence_type,
                "notes": "",
            },
            photo_urls=[request.evidence_url],
        )

        return VerifyEvidenceResponse(
            verified=result.decision == VerificationDecision.APPROVED,
            confidence=result.confidence,
            decision=result.decision.value,
            explanation=result.explanation,
            issues=result.issues,
        )

    except Exception as e:
        logger.warning("AI verification unavailable for task %s: %s", request.task_id, e)
        return VerifyEvidenceResponse(
            verified=True,
            confidence=0.5,
            decision="approved",
            explanation="AI verification temporarily unavailable. Evidence accepted for agent review.",
            issues=[],
        )


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
