"""Pydantic v2 models for the Execution Market API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (mirror mcp_server/models.py)
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PUBLISHED = "published"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskCategory(str, Enum):
    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"
    LOCATION_BASED = "location_based"
    VERIFICATION = "verification"
    SOCIAL_PROOF = "social_proof"
    DATA_COLLECTION = "data_collection"
    SENSORY = "sensory"
    SOCIAL = "social"
    PROXY = "proxy"
    BUREAUCRATIC = "bureaucratic"
    EMERGENCY = "emergency"
    CREATIVE = "creative"
    DATA_PROCESSING = "data_processing"
    API_INTEGRATION = "api_integration"
    CONTENT_GENERATION = "content_generation"
    CODE_EXECUTION = "code_execution"
    RESEARCH = "research"
    MULTI_STEP_WORKFLOW = "multi_step_workflow"


class EvidenceType(str, Enum):
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


class TargetExecutorType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    ANY = "any"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """A task in the Execution Market."""

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
    evidence_schema: Optional[dict[str, Any]] = None
    location_hint: Optional[str] = None
    min_reputation: int = 0
    erc8004_agent_id: Optional[str] = None
    payment_network: str = "base"
    payment_token: str = "USDC"
    escrow_tx: Optional[str] = None
    refund_tx: Optional[str] = None
    target_executor_type: Optional[str] = None
    agent_name: Optional[str] = None
    skills_required: Optional[list[str]] = None
    payment_tx: Optional[str] = None
    escrow_status: Optional[str] = None


class TaskList(BaseModel):
    """Paginated list of tasks."""

    tasks: list[Task]
    total: int
    count: int
    offset: int
    has_more: bool


class Submission(BaseModel):
    """A worker's submission for a task."""

    id: str
    task_id: str
    executor_id: str
    status: str
    pre_check_score: Optional[float] = None
    submitted_at: datetime
    evidence: Optional[dict[str, Any]] = None
    agent_verdict: Optional[str] = None
    agent_notes: Optional[str] = None
    verified_at: Optional[datetime] = None


class SubmissionList(BaseModel):
    """List of submissions."""

    submissions: list[Submission]
    count: int


class Application(BaseModel):
    """A worker's application to a task."""

    id: str
    task_id: str
    executor_id: str
    message: Optional[str] = None
    status: str
    created_at: str


class ApplicationList(BaseModel):
    """List of applications."""

    applications: list[Application]
    count: int


class Executor(BaseModel):
    """An executor (worker) profile."""

    id: str
    wallet_address: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    reputation_score: Optional[float] = None
    tasks_completed: Optional[int] = None


class HealthResponse(BaseModel):
    """API health check response."""

    status: str
    version: Optional[str] = None


# ---------------------------------------------------------------------------
# Request param models (used by EMClient methods)
# ---------------------------------------------------------------------------

class CreateTaskParams(BaseModel):
    """Parameters for publishing a new task."""

    title: str = Field(..., min_length=5, max_length=255)
    instructions: str = Field(..., min_length=20, max_length=5000)
    category: TaskCategory
    bounty_usd: float = Field(..., gt=0, le=10000)
    deadline_hours: int = Field(..., ge=1, le=720)
    evidence_required: list[EvidenceType] = Field(..., min_length=1, max_length=5)
    evidence_optional: Optional[list[EvidenceType]] = None
    location_hint: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    min_reputation: int = 0
    payment_token: str = "USDC"
    payment_network: str = "base"
    agent_name: Optional[str] = None
    target_executor: Optional[TargetExecutorType] = None
    skills_required: Optional[list[str]] = None


class SubmitEvidenceParams(BaseModel):
    """Parameters for submitting evidence to a task."""

    executor_id: str
    evidence: dict[str, Any]
    notes: Optional[str] = None
    device_metadata: Optional[dict[str, Any]] = None


class ApproveParams(BaseModel):
    """Parameters for approving a submission."""

    notes: Optional[str] = None
    rating_score: Optional[int] = Field(default=None, ge=0, le=100)


class RejectParams(BaseModel):
    """Parameters for rejecting a submission."""

    notes: str = Field(..., min_length=10, max_length=1000)
    severity: str = "minor"
    reputation_score: Optional[int] = Field(default=None, ge=0, le=50)
