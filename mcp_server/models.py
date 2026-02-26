"""
Execution Market MCP Server - Pydantic Models

Input validation models for all MCP tools.
"""

from typing import Optional, List, Dict, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ExecutorType(str, Enum):
    """Type of executor."""

    HUMAN = "human"
    AGENT = "agent"


class TargetExecutorType(str, Enum):
    """Who can execute."""

    HUMAN = "human"
    AGENT = "agent"
    ANY = "any"


class VerificationMode(str, Enum):
    """How submissions are verified."""

    MANUAL = "manual"
    AUTO = "auto"
    ORACLE = "oracle"


class TaskCategory(str, Enum):
    """Categories of tasks that humans can execute."""

    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"
    DATA_PROCESSING = "data_processing"
    API_INTEGRATION = "api_integration"
    CONTENT_GENERATION = "content_generation"
    CODE_EXECUTION = "code_execution"
    RESEARCH = "research"
    MULTI_STEP_WORKFLOW = "multi_step_workflow"


class TaskStatus(str, Enum):
    """Status of a task in the Execution Market system."""

    PUBLISHED = "published"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EvidenceType(str, Enum):
    """Types of evidence that can be required for task completion."""

    PHOTO = "photo"
    PHOTO_GEO = "photo_geo"
    VIDEO = "video"
    DOCUMENT = "document"
    RECEIPT = "receipt"
    SIGNATURE = "signature"
    NOTARIZED = "notarized"
    TIMESTAMP_PROOF = "timestamp_proof"
    TEXT_RESPONSE = "text_response"
    MEASUREMENT = "measurement"
    SCREENSHOT = "screenshot"
    JSON_RESPONSE = "json_response"
    API_RESPONSE = "api_response"
    CODE_OUTPUT = "code_output"
    FILE_ARTIFACT = "file_artifact"
    URL_REFERENCE = "url_reference"
    STRUCTURED_DATA = "structured_data"
    TEXT_REPORT = "text_report"


class PaymentStrategy(str, Enum):
    """Payment strategy for task escrow (matches PaymentOperator 5 modes)."""

    ESCROW_CAPTURE = "escrow_capture"  # Scenario 1: AUTHORIZE → RELEASE
    ESCROW_CANCEL = "escrow_cancel"  # Scenario 2: AUTHORIZE → REFUND IN ESCROW
    INSTANT_PAYMENT = "instant_payment"  # Scenario 3: CHARGE (direct, no escrow)
    PARTIAL_PAYMENT = (
        "partial_payment"  # Scenario 4: AUTHORIZE → partial RELEASE + REFUND
    )
    DISPUTE_RESOLUTION = (
        "dispute_resolution"  # Scenario 5: AUTHORIZE → RELEASE → REFUND POST ESCROW
    )


class SubmissionVerdict(str, Enum):
    """Agent's verdict on a submission."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PARTIAL = "partial"
    DISPUTED = "disputed"
    MORE_INFO = "more_info_requested"


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


# ============== TOOL INPUT MODELS ==============


class PublishTaskInput(BaseModel):
    """Input model for publishing a new task."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    agent_id: str = Field(
        ...,
        description="Agent's identifier (wallet address or ERC-8004 ID)",
        min_length=1,
        max_length=255,
    )
    title: str = Field(
        ...,
        description="Short, descriptive title for the task",
        min_length=5,
        max_length=255,
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
        description="Location hint for the task (e.g., 'Mexico City downtown')",
        max_length=255,
    )
    min_reputation: Optional[int] = Field(
        default=0, description="Minimum reputation required", ge=0
    )
    payment_token: Optional[str] = Field(
        default="USDC", description="Payment token symbol", max_length=10
    )
    payment_network: Optional[str] = Field(
        default="base",
        description="Payment network (e.g., base, ethereum, polygon, arbitrum)",
        max_length=30,
    )
    payment_strategy: Optional[PaymentStrategy] = Field(
        default=None,
        description=(
            "Payment strategy. Auto-selected if not specified. "
            "Options: escrow_capture (default $5-$200), escrow_cancel (cancellable), "
            "instant_payment (micro <$5, rep >90%), partial_payment (proof-of-attempt), "
            "dispute_resolution (high-value $50+)"
        ),
    )

    @field_validator("evidence_required")
    @classmethod
    def validate_evidence(cls, v: List[EvidenceType]) -> List[EvidenceType]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate evidence types not allowed")
        return v


class GetTasksInput(BaseModel):
    """Input model for getting tasks."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    agent_id: Optional[str] = Field(
        default=None,
        description="Filter by agent ID (get tasks created by this agent)",
        max_length=255,
    )
    status: Optional[TaskStatus] = Field(
        default=None, description="Filter by task status"
    )
    category: Optional[TaskCategory] = Field(
        default=None, description="Filter by category"
    )
    limit: int = Field(
        default=20, description="Maximum number of results", ge=1, le=100
    )
    offset: int = Field(default=0, description="Offset for pagination", ge=0)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class GetTaskInput(BaseModel):
    """Input model for getting a single task."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ..., description="UUID of the task", min_length=36, max_length=36
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class CheckSubmissionInput(BaseModel):
    """Input model for checking submission status."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ...,
        description="UUID of the task to check submissions for",
        min_length=36,
        max_length=36,
    )
    agent_id: str = Field(
        ..., description="Agent ID (for authorization)", min_length=1, max_length=255
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class ApproveSubmissionInput(BaseModel):
    """Input model for approving or rejecting a submission."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    submission_id: str = Field(
        ..., description="UUID of the submission", min_length=36, max_length=36
    )
    agent_id: str = Field(
        ..., description="Agent ID (for authorization)", min_length=1, max_length=255
    )
    verdict: SubmissionVerdict = Field(
        ...,
        description=(
            "Agent's verdict: accepted (full release), rejected (no additional release), "
            "partial (proof-of-attempt release + refund), disputed, or more_info_requested"
        ),
    )
    notes: Optional[str] = Field(
        default=None, description="Notes explaining the verdict", max_length=1000
    )
    release_percent: Optional[int] = Field(
        default=15,
        description="For 'partial' verdict: percentage to release to worker (default 15%)",
        ge=5,
        le=50,
    )
    payment_auth_worker: Optional[str] = Field(
        default=None,
        description="X-Payment header for worker payment (EIP-3009 auth: agent->worker). "
        "Required for external agents in fase1 mode. Server-managed agents omit this.",
    )
    payment_auth_fee: Optional[str] = Field(
        default=None,
        description="X-Payment header for platform fee (EIP-3009 auth: agent->treasury). "
        "Required for external agents in fase1 mode. Server-managed agents omit this.",
    )
    rating_score: Optional[int] = Field(
        default=None,
        description="Optional agent-provided reputation score override (0-100). "
        "When omitted, score is computed dynamically from submission quality signals.",
        ge=0,
        le=100,
    )


class CancelTaskInput(BaseModel):
    """Input model for cancelling a task."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ..., description="UUID of the task to cancel", min_length=36, max_length=36
    )
    agent_id: str = Field(
        ..., description="Agent ID (for authorization)", min_length=1, max_length=255
    )
    reason: Optional[str] = Field(
        default=None, description="Reason for cancellation", max_length=500
    )


# ============== WORKER TOOL INPUT MODELS ==============


class ApplyToTaskInput(BaseModel):
    """Input model for worker applying to a task."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ..., description="UUID of the task to apply for", min_length=36, max_length=36
    )
    executor_id: str = Field(
        ..., description="Worker's executor ID", min_length=36, max_length=36
    )
    message: Optional[str] = Field(
        default=None, description="Optional message to the agent", max_length=500
    )


class SubmitWorkInput(BaseModel):
    """Input model for submitting completed work."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ..., description="UUID of the task", min_length=36, max_length=36
    )
    executor_id: str = Field(
        ..., description="Worker's executor ID", min_length=36, max_length=36
    )
    evidence: Dict = Field(..., description="Evidence dictionary with required fields")
    notes: Optional[str] = Field(
        default=None, description="Optional notes about the submission", max_length=1000
    )


class GetMyTasksInput(BaseModel):
    """Input model for getting worker's tasks."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    executor_id: str = Field(
        ..., description="Worker's executor ID", min_length=36, max_length=36
    )
    status: Optional[TaskStatus] = Field(default=None, description="Filter by status")
    include_applications: bool = Field(
        default=True, description="Include pending applications"
    )
    limit: int = Field(
        default=20, description="Maximum number of results", ge=1, le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class WithdrawEarningsInput(BaseModel):
    """Input model for withdrawing earnings."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    executor_id: str = Field(
        ..., description="Worker's executor ID", min_length=36, max_length=36
    )
    amount_usdc: Optional[float] = Field(
        default=None,
        description="Amount to withdraw in USDC (None = withdraw all)",
        gt=0,
    )
    destination_address: Optional[str] = Field(
        default=None,
        description="Destination wallet address (default: executor's wallet)",
        min_length=42,
        max_length=42,
    )


class AssignTaskInput(BaseModel):
    """Input model for agent assigning a task to a worker."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ..., description="UUID of the task", min_length=36, max_length=36
    )
    agent_id: str = Field(
        ..., description="Agent ID (for authorization)", min_length=1, max_length=255
    )
    executor_id: str = Field(
        ..., description="Worker's executor ID to assign", min_length=36, max_length=36
    )
    notes: Optional[str] = Field(
        default=None, description="Notes for the worker", max_length=500
    )


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
    min_reputation: Optional[int] = 0


class BatchCreateTasksInput(BaseModel):
    """Input model for batch task creation."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    agent_id: str = Field(
        ..., description="Agent's identifier", min_length=1, max_length=255
    )
    tasks: List[BatchTaskDefinition] = Field(
        ..., description="List of tasks to create", min_length=1, max_length=50
    )
    payment_token: Optional[str] = Field(
        default="USDC", description="Payment token for all tasks"
    )


class GetTaskAnalyticsInput(BaseModel):
    """Input model for task analytics."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    agent_id: str = Field(
        ..., description="Agent ID to get analytics for", min_length=1, max_length=255
    )
    days: int = Field(default=30, description="Number of days to analyze", ge=1, le=365)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


# ============== REPUTATION TOOL INPUT MODELS ==============


class RateWorkerInput(BaseModel):
    """Input model for rating a worker after task completion."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    submission_id: str = Field(
        ..., description="UUID of the submission to rate", min_length=36, max_length=36
    )
    score: Optional[int] = Field(
        default=None,
        description="Rating score 0-100. If omitted, computed dynamically.",
        ge=0,
        le=100,
    )
    comment: Optional[str] = Field(
        default=None, description="Optional comment about the worker", max_length=1000
    )


class RateAgentInput(BaseModel):
    """Input model for a worker rating an agent."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ..., description="UUID of the completed task", min_length=36, max_length=36
    )
    score: int = Field(..., description="Rating score 0-100", ge=0, le=100)
    comment: Optional[str] = Field(
        default=None, description="Optional comment about the agent", max_length=1000
    )


class GetReputationInput(BaseModel):
    """Input model for getting on-chain reputation."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    agent_id: Optional[int] = Field(
        default=None, description="ERC-8004 agent token ID", ge=1
    )
    wallet_address: Optional[str] = Field(
        default=None, description="Agent's wallet address", max_length=42
    )
    network: str = Field(default="base", description="ERC-8004 network", max_length=30)


class CheckIdentityInput(BaseModel):
    """Input model for checking ERC-8004 identity."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    wallet_address: str = Field(
        ..., description="Wallet address to check", min_length=42, max_length=42
    )
    network: str = Field(default="base", description="Network to check", max_length=30)


class RegisterIdentityInput(BaseModel):
    """Input model for gasless ERC-8004 identity registration."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    wallet_address: str = Field(
        ..., description="Wallet address to register", min_length=42, max_length=42
    )
    mode: str = Field(
        default="gasless", description="Registration mode (only 'gasless' supported)"
    )
    network: str = Field(default="base", description="ERC-8004 network", max_length=30)


class RegisterAgentExecutorInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    wallet_address: str = Field(..., min_length=42, max_length=42)
    capabilities: List[str] = Field(..., min_length=1, max_length=20)
    display_name: str = Field(..., min_length=2, max_length=100)
    agent_card_url: Optional[str] = Field(default=None, max_length=500)
    mcp_endpoint_url: Optional[str] = Field(default=None, max_length=500)
    a2a_protocol_version: Optional[str] = Field(default=None, max_length=10)


class BrowseAgentTasksInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    executor_id: Optional[str] = Field(default=None, max_length=36)
    category: Optional[TaskCategory] = Field(default=None)
    capabilities: Optional[List[str]] = Field(default=None, max_length=20)
    min_bounty: Optional[float] = Field(default=None, ge=0)
    max_bounty: Optional[float] = Field(default=None, le=100000)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class AcceptAgentTaskInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    task_id: str = Field(..., min_length=36, max_length=36)
    executor_id: str = Field(..., min_length=36, max_length=36)
    estimated_completion_hours: Optional[float] = Field(default=None, gt=0, le=720)
    message: Optional[str] = Field(default=None, max_length=500)


class SubmitAgentWorkInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    task_id: str = Field(..., min_length=36, max_length=36)
    executor_id: str = Field(..., min_length=36, max_length=36)
    result_data: Dict = Field(...)
    result_type: str = Field(default="json_response", max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)


class GetAgentExecutionsInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    executor_id: str = Field(..., min_length=36, max_length=36)
    status: Optional[TaskStatus] = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# ============== H2A (HUMAN-TO-AGENT) MODELS ==============


class PublisherType(str, Enum):
    AGENT = "agent"
    HUMAN = "human"


class DigitalEvidenceType(str, Enum):
    JSON_RESPONSE = "json_response"
    CODE = "code"
    REPORT = "report"
    API_RESPONSE = "api_response"
    DATA_FILE = "data_file"
    SCREENSHOT = "screenshot"
    TEXT_RESPONSE = "text_response"


class PublishH2ATaskRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    title: str = Field(..., min_length=5, max_length=255)
    instructions: str = Field(..., min_length=20, max_length=10000)
    category: TaskCategory = Field(...)
    bounty_usd: float = Field(..., gt=0, le=500)
    deadline_hours: int = Field(default=24, ge=1, le=720)
    required_capabilities: Optional[List[str]] = Field(default=None, max_length=10)
    verification_mode: Optional[str] = Field(default="manual")
    evidence_required: List[str] = Field(
        default=["json_response"], min_length=1, max_length=5
    )
    payment_network: str = Field(default="base", max_length=30)
    target_agent_id: Optional[str] = Field(default=None, max_length=255)

    @field_validator("bounty_usd")
    @classmethod
    def validate_bounty(cls, v: float) -> float:
        if v < 0.01:
            raise ValueError("Bounty must be at least $0.01")
        return round(v, 2)


class H2ATaskResponse(BaseModel):
    task_id: str
    status: str = "published"
    bounty_usd: float
    fee_usd: float
    total_required_usd: float
    deadline: str
    publisher_type: str = "human"


class ApproveH2ASubmissionRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    submission_id: str = Field(..., min_length=36, max_length=36)
    verdict: Literal["accepted", "rejected", "needs_revision"] = Field(...)
    notes: Optional[str] = Field(default=None, max_length=2000)
    settlement_auth_worker: Optional[str] = Field(default=None)
    settlement_auth_fee: Optional[str] = Field(default=None)


class H2AApprovalResponse(BaseModel):
    status: str
    worker_tx: Optional[str] = None
    fee_tx: Optional[str] = None
    notes: Optional[str] = None


class AgentDirectoryEntry(BaseModel):
    executor_id: str
    display_name: str
    capabilities: Optional[List[str]] = None
    rating: float = 0
    tasks_completed: int = 0
    avg_rating: float = 0
    agent_card_url: Optional[str] = None
    mcp_endpoint_url: Optional[str] = None
    erc8004_agent_id: Optional[int] = None
    verified: bool = False
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    pricing: Optional[Dict] = None
    role: str = "executor"
    tasks_published: int = 0
    total_bounty_usd: float = 0.0
    active_tasks: int = 0


class AgentDirectoryResponse(BaseModel):
    agents: List[AgentDirectoryEntry]
    total: int
    page: int = 1
    limit: int = 20
