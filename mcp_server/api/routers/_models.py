"""
Pydantic request/response models for the Execution Market API.

Extracted from api/routes.py — all models used by route handlers.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict

from models import TaskCategory, EvidenceType


# =============================================================================
# TASK MODELS
# =============================================================================


class CreateTaskRequest(BaseModel):
    """Request model for creating a new task."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(
        ...,
        description="Short, descriptive title for the task",
        min_length=5,
        max_length=255,
        examples=["Verify store is open", "Take photo of product display"],
    )
    instructions: str = Field(
        ...,
        description="Detailed instructions for the human executor",
        min_length=20,
        max_length=5000,
    )
    category: TaskCategory = Field(..., description="Category of the task")
    bounty_usd: float = Field(..., description="Bounty amount in USD", gt=0, le=10000)
    deadline_hours: int = Field(
        ...,
        description="Hours from now until deadline",
        ge=1,
        le=720,  # Max 30 days
    )
    evidence_required: List[EvidenceType] = Field(
        ..., description="List of required evidence types", min_length=1, max_length=5
    )
    evidence_optional: Optional[List[EvidenceType]] = Field(
        default=None, description="List of optional evidence types", max_length=5
    )
    location_hint: Optional[str] = Field(
        default=None,
        description="Human-readable location hint (e.g., 'Mexico City downtown')",
        max_length=255,
    )
    location_lat: Optional[float] = Field(
        default=None,
        description="Expected latitude for GPS verification",
        ge=-90,
        le=90,
    )
    location_lng: Optional[float] = Field(
        default=None,
        description="Expected longitude for GPS verification",
        ge=-180,
        le=180,
    )
    min_reputation: int = Field(
        default=0, description="Minimum reputation score required to apply", ge=0
    )
    payment_token: str = Field(
        default="USDC", description="Payment token symbol", max_length=10
    )
    payment_network: str = Field(
        default="base",
        description="Payment network (e.g., base, ethereum, polygon, arbitrum)",
        max_length=30,
    )

    @field_validator("evidence_required")
    @classmethod
    def validate_evidence_unique(cls, v: List[EvidenceType]) -> List[EvidenceType]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate evidence types not allowed")
        return v


class TaskResponse(BaseModel):
    """Response model for task data."""

    id: str = Field(..., description="Unique task identifier (UUID)")
    title: str = Field(..., description="Short descriptive title of the task")
    status: str = Field(
        ...,
        description="Current task status (published, accepted, in_progress, submitted, completed, cancelled, expired)",
    )
    category: str = Field(
        ...,
        description="Task category (physical_presence, knowledge_access, human_authority, simple_action, digital_physical)",
    )
    bounty_usd: float = Field(..., description="Bounty amount in USD")
    deadline: datetime = Field(..., description="Task deadline (ISO 8601)")
    created_at: datetime = Field(..., description="Task creation timestamp (ISO 8601)")
    agent_id: str = Field(
        ..., description="Agent identifier (wallet address or API key agent_id)"
    )
    executor_id: Optional[str] = Field(
        None, description="Assigned worker's executor ID"
    )
    instructions: Optional[str] = Field(
        None, description="Detailed task instructions for the worker"
    )
    evidence_schema: Optional[Dict] = Field(
        None, description="Required and optional evidence types"
    )
    location_hint: Optional[str] = Field(
        None, description="Human-readable location hint"
    )
    min_reputation: int = Field(
        0, description="Minimum reputation score required to apply"
    )
    erc8004_agent_id: Optional[str] = Field(
        None, description="ERC-8004 on-chain agent identity token ID"
    )
    payment_network: str = Field(
        "base",
        description="Blockchain network for payment (e.g. base, ethereum, polygon)",
    )
    payment_token: str = Field(
        "USDC", description="Payment token symbol (USDC, EURC, USDT, PYUSD)"
    )
    escrow_tx: Optional[str] = Field(
        None, description="Escrow deposit transaction hash or payment reference"
    )
    refund_tx: Optional[str] = Field(
        None, description="Refund transaction hash (if cancelled/refunded)"
    )


class TaskListResponse(BaseModel):
    """Response model for paginated task list."""

    tasks: List[TaskResponse] = Field(..., description="List of task objects")
    total: int = Field(..., description="Total number of matching tasks")
    count: int = Field(..., description="Number of tasks in this page")
    offset: int = Field(..., description="Current pagination offset")
    has_more: bool = Field(..., description="Whether more results are available")


# =============================================================================
# SUBMISSION MODELS
# =============================================================================


class SubmissionResponse(BaseModel):
    """Response model for submission data."""

    id: str = Field(..., description="Unique submission identifier (UUID)")
    task_id: str = Field(..., description="Associated task ID")
    executor_id: str = Field(..., description="Worker's executor ID")
    status: str = Field(
        ...,
        description="Current verdict status (pending, accepted, rejected, more_info_requested, disputed)",
    )
    pre_check_score: Optional[float] = Field(
        None, description="AI pre-check score (0.0-1.0) if evidence was auto-verified"
    )
    submitted_at: datetime = Field(..., description="Submission timestamp (ISO 8601)")
    evidence: Optional[Dict] = Field(
        None, description="Submitted evidence data (photos, text, documents)"
    )
    agent_verdict: Optional[str] = Field(
        None, description="Agent's verdict on the submission"
    )
    agent_notes: Optional[str] = Field(
        None, description="Agent's notes explaining the verdict"
    )
    verified_at: Optional[datetime] = Field(
        None, description="Timestamp when submission was verified"
    )


class SubmissionListResponse(BaseModel):
    """Response model for submission list."""

    submissions: List[SubmissionResponse] = Field(
        ..., description="List of submission objects"
    )
    count: int = Field(..., description="Total number of submissions")


class ApprovalRequest(BaseModel):
    """Request model for approving a submission."""

    notes: Optional[str] = Field(
        default=None, description="Optional notes about the approval", max_length=1000
    )
    rating_score: Optional[int] = Field(
        default=None,
        description="Optional reputation score override (0-100). "
        "When omitted, score is computed dynamically from submission quality signals.",
        ge=0,
        le=100,
    )


class RejectionRequest(BaseModel):
    """Request model for rejecting a submission."""

    notes: str = Field(
        ..., description="Required reason for rejection", min_length=10, max_length=1000
    )
    severity: str = Field(
        default="minor",
        description="Rejection severity: 'minor' (no on-chain effect) or 'major' (records negative reputation)",
        pattern="^(minor|major)$",
    )
    reputation_score: Optional[int] = Field(
        default=None,
        description="Reputation score for major rejections (0-50). Defaults to 30 if omitted.",
        ge=0,
        le=50,
    )


class RequestMoreInfoRequest(BaseModel):
    """Request model for requesting more info on a submission."""

    notes: str = Field(
        ..., description="Required clarification request", min_length=5, max_length=1000
    )


# =============================================================================
# TASK ACTIONS
# =============================================================================


class CancelRequest(BaseModel):
    """Request model for cancelling a task."""

    reason: Optional[str] = Field(
        default=None, description="Optional reason for cancellation", max_length=500
    )


class WorkerAssignRequest(BaseModel):
    """Request model for assigning a task to a worker."""

    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional assignment notes for the worker",
        max_length=500,
    )


# =============================================================================
# WORKER MODELS
# =============================================================================


class WorkerApplicationRequest(BaseModel):
    """Request model for worker applying to a task."""

    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    message: Optional[str] = Field(
        default=None, description="Optional message to the agent", max_length=500
    )


class WorkerSubmissionRequest(BaseModel):
    """Request model for worker submitting work."""

    executor_id: str = Field(
        ...,
        description="Worker's executor ID",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    evidence: Dict[str, Any] = Field(
        ..., description="Evidence dictionary with required fields"
    )
    notes: Optional[str] = Field(
        default=None, description="Optional notes about the submission", max_length=1000
    )


# =============================================================================
# ANALYTICS & CONFIG
# =============================================================================


class AnalyticsResponse(BaseModel):
    """Response model for agent analytics."""

    totals: Dict[str, Any] = Field(
        ..., description="Aggregate totals (total_tasks, total_bounty, completed, etc.)"
    )
    by_status: Dict[str, int] = Field(..., description="Task count breakdown by status")
    by_category: Dict[str, int] = Field(
        ..., description="Task count breakdown by category"
    )
    average_times: Dict[str, str] = Field(
        ..., description="Average times (time_to_accept, time_to_complete, etc.)"
    )
    top_workers: List[Dict] = Field(
        ..., description="Top performing workers for this agent"
    )
    period_days: int = Field(..., description="Number of days covered by this analysis")


class PublicConfigResponse(BaseModel):
    """Public platform configuration (readable by anyone)."""

    min_bounty_usd: float = Field(..., description="Minimum bounty amount in USD")
    max_bounty_usd: float = Field(..., description="Maximum bounty amount in USD")
    supported_networks: List[str] = Field(
        ..., description="Currently enabled payment networks"
    )
    supported_tokens: List[str] = Field(..., description="Supported stablecoin tokens")
    preferred_network: str = Field(..., description="Default payment network")


class PublicPlatformMetricsResponse(BaseModel):
    """Public high-level platform metrics for landing/dashboard surfaces."""

    users: Dict[str, int] = Field(
        ...,
        description="User counts (registered_workers, registered_agents, active, etc.)",
    )
    tasks: Dict[str, int] = Field(..., description="Task counts by status and total")
    activity: Dict[str, int] = Field(
        ..., description="Activity metrics (active workers, agents with live tasks)"
    )
    payments: Dict[str, float] = Field(
        ..., description="Payment aggregates (total_volume_usd, total_fees_usd)"
    )
    generated_at: datetime = Field(
        ..., description="Timestamp when these metrics were generated"
    )


class ConfigUpdateRequest(BaseModel):
    """Request to update a config value (admin only)."""

    value: Any = Field(..., description="New value for the config key")
    reason: Optional[str] = Field(None, description="Reason for the change (for audit)")


# =============================================================================
# AVAILABLE TASKS (WORKER VIEW)
# =============================================================================


class AvailableTasksResponse(BaseModel):
    """Response model for available tasks (worker view)."""

    tasks: List[Dict[str, Any]] = Field(
        ..., description="List of published tasks available for workers"
    )
    count: int = Field(..., description="Number of tasks returned")
    offset: int = Field(..., description="Current pagination offset")
    filters_applied: Dict[str, Any] = Field(
        ..., description="Filters that were applied to this query"
    )


# =============================================================================
# GENERIC RESPONSES
# =============================================================================


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = Field(True, description="Whether the operation succeeded")
    message: str = Field(..., description="Human-readable result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(
        ..., description="Error code (e.g. TASK_NOT_FOUND, UNAUTHORIZED)"
    )
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context"
    )


# =============================================================================
# PAYMENT TIMELINE
# =============================================================================


class TaskPaymentEventResponse(BaseModel):
    """Canonical payment timeline event for a task."""

    id: str = Field(..., description="Unique event identifier")
    type: str = Field(
        ...,
        description="Event type (escrow_created, final_release, refund, partial_release, etc.)",
    )
    actor: str = Field(
        ..., description="Who triggered the event (agent, system, arbitrator)"
    )
    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    network: str = Field(..., description="Blockchain network for this event")
    amount: Optional[float] = Field(None, description="Amount in USDC (if applicable)")
    tx_hash: Optional[str] = Field(
        None, description="On-chain transaction hash (0x-prefixed, 66 chars)"
    )
    note: Optional[str] = Field(None, description="Human-readable note about the event")


class TaskPaymentResponse(BaseModel):
    """Canonical payment timeline and status for a task."""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(
        ...,
        description="Derived payment status (pending, escrowed, completed, refunded, partial_released)",
    )
    total_amount: float = Field(
        ..., description="Total amount escrowed or paid in USDC"
    )
    released_amount: float = Field(
        ..., description="Amount released to the worker in USDC"
    )
    currency: str = Field("USDC", description="Payment currency")
    escrow_tx: Optional[str] = Field(
        None, description="Initial escrow deposit transaction hash"
    )
    escrow_contract: Optional[str] = Field(
        None, description="Escrow contract address (if applicable)"
    )
    network: str = Field("base", description="Primary payment network")
    events: List[TaskPaymentEventResponse] = Field(
        ..., description="Chronological list of payment events"
    )
    created_at: str = Field(..., description="When the payment timeline started")
    updated_at: str = Field(..., description="Last event timestamp")


class TransactionEventResponse(BaseModel):
    """Single on-chain transaction event from the payment_events audit trail."""

    id: str = Field(..., description="Event UUID")
    event_type: str = Field(
        ...,
        description="Event type: escrow_authorize, escrow_release, escrow_refund, balance_check, settle_worker_direct, settle_fee_direct, disburse_worker, disburse_fee, fee_collect, reputation_agent_rates_worker, reputation_worker_rates_agent",
    )
    tx_hash: Optional[str] = Field(
        None, description="On-chain transaction hash (0x-prefixed)"
    )
    amount_usdc: Optional[float] = Field(None, description="Amount in USDC")
    from_address: Optional[str] = Field(None, description="Source wallet address")
    to_address: Optional[str] = Field(None, description="Destination wallet address")
    network: Optional[str] = Field(None, description="Blockchain network")
    token: str = Field("USDC", description="Token symbol")
    status: str = Field(..., description="Event status: pending, success, failed")
    explorer_url: Optional[str] = Field(
        None, description="Block explorer URL for this transaction"
    )
    label: Optional[str] = Field(None, description="Human-readable label in Spanish")
    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional event context"
    )


class TaskTransactionsResponse(BaseModel):
    """Chronological transaction history for a task from the payment_events audit trail."""

    task_id: str = Field(..., description="Task UUID")
    transactions: List[TransactionEventResponse] = Field(
        ..., description="Chronological list of transaction events"
    )
    total_count: int = Field(..., description="Total number of events")
    summary: Dict[str, Any] = Field(
        ...,
        description="Summary: total_locked, total_released, total_refunded, fee_collected",
    )


# =============================================================================
# EVIDENCE VERIFICATION
# =============================================================================


class VerifyEvidenceRequest(BaseModel):
    """Request to verify evidence against task requirements."""

    task_id: str = Field(..., description="UUID of the task")
    evidence_url: str = Field(
        ..., description="Public URL of the uploaded evidence file"
    )
    evidence_type: str = Field(
        default="photo", description="Type of evidence being verified"
    )


class VerifyEvidenceResponse(BaseModel):
    """Result of AI evidence verification."""

    verified: bool
    confidence: float = Field(..., ge=0, le=1)
    decision: str  # approved, rejected, needs_human
    explanation: str
    issues: List[str] = []


# =============================================================================
# WORKER IDENTITY (ERC-8004)
# =============================================================================


class IdentityCheckResponse(BaseModel):
    """Response for worker identity check."""

    status: str = Field(..., description="registered, not_registered, or error")
    agent_id: Optional[int] = Field(None, description="ERC-8004 token ID if registered")
    wallet_address: Optional[str] = None
    network: str = "base"
    chain_id: int = 8453
    registry_address: Optional[str] = None
    error: Optional[str] = None


class RegisterIdentityRequest(BaseModel):
    """Request to prepare an identity registration transaction."""

    agent_uri: Optional[str] = Field(
        None,
        description="Metadata URI for the identity (defaults to execution.market profile URL)",
        max_length=500,
    )


class RegisterIdentityResponse(BaseModel):
    """Response with unsigned transaction data for identity registration."""

    status: str = Field(..., description="Current identity status before registration")
    agent_id: Optional[int] = Field(
        None, description="Existing agent ID if already registered"
    )
    transaction: Optional[Dict[str, Any]] = Field(
        None,
        description="Unsigned transaction data (to, data, chainId, value, estimated_gas)",
    )
    message: str


class ConfirmIdentityRequest(BaseModel):
    """Request to confirm a registration transaction."""

    tx_hash: str = Field(
        ...,
        description="Transaction hash of the registration tx",
        min_length=66,
        max_length=66,
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
        ..., description="List of tasks to create", min_length=1, max_length=50
    )
    payment_token: str = Field(
        default="USDC", description="Payment token for all tasks"
    )


class BatchCreateResponse(BaseModel):
    """Response model for batch task creation."""

    created: int
    failed: int
    tasks: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    total_bounty: float
