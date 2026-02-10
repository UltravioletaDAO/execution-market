"""
OpenAPI Documentation Generator for Execution Market API.

Provides comprehensive OpenAPI/Swagger documentation with:
- Complete request/response models
- Detailed examples
- Security schemes
- Rate limiting documentation
- Webhook event schemas
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS (for documentation)
# =============================================================================


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


class TaskCategory(str, Enum):
    """Categories of tasks that humans can execute."""

    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"


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


class SubmissionVerdict(str, Enum):
    """Agent's verdict on a submission."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MORE_INFO = "more_info_requested"
    DISPUTED = "disputed"


class WebhookEventType(str, Enum):
    """Webhook event types."""

    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_ASSIGNED = "task.assigned"
    TASK_SUBMITTED = "task.submitted"
    TASK_COMPLETED = "task.completed"
    TASK_EXPIRED = "task.expired"
    TASK_CANCELLED = "task.cancelled"
    SUBMISSION_RECEIVED = "submission.received"
    SUBMISSION_APPROVED = "submission.approved"
    SUBMISSION_REJECTED = "submission.rejected"
    PAYMENT_ESCROWED = "payment.escrowed"
    PAYMENT_RELEASED = "payment.released"
    PAYMENT_FAILED = "payment.failed"
    DISPUTE_OPENED = "dispute.opened"
    DISPUTE_RESOLVED = "dispute.resolved"
    WORKER_APPLIED = "worker.applied"
    REPUTATION_UPDATED = "reputation.updated"


# =============================================================================
# REQUEST MODELS
# =============================================================================


class TaskCreateRequest(BaseModel):
    """Request body for creating a new task."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Check if Walmart is open",
                "instructions": "Go to the Walmart at 123 Main St and take a clear photo of the entrance showing if the store is open or closed. Include any posted hours sign.",
                "category": "physical_presence",
                "bounty_usd": 2.50,
                "deadline_hours": 4,
                "evidence_required": ["photo", "gps"],
                "evidence_optional": ["text_response"],
                "location_hint": "Miami, FL 33101",
                "min_reputation": 0,
                "payment_token": "USDC",
            }
        }
    )

    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Short, descriptive task title",
        examples=["Check if store is open", "Verify product availability"],
    )
    instructions: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Detailed instructions for the worker. Be specific about what evidence is needed.",
        examples=["Take a photo of the store entrance showing open/closed status"],
    )
    category: TaskCategory = Field(
        ...,
        description="Task category determines worker matching and expected completion time",
    )
    bounty_usd: float = Field(
        ...,
        gt=0,
        le=10000,
        description="Payment amount in USD. Minimum configurable via platform config (default $0.50), maximum $10,000.",
        examples=[0.50, 2.50, 5.00, 10.00],
    )
    deadline_hours: int = Field(
        ...,
        ge=1,
        le=720,
        description="Hours until deadline (1-720, max 30 days)",
        examples=[4, 24, 48],
    )
    evidence_required: List[EvidenceType] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Required evidence types. Task cannot be completed without all required evidence.",
        examples=[["photo", "gps"], ["text_response"]],
    )
    evidence_optional: Optional[List[EvidenceType]] = Field(
        None,
        max_length=5,
        description="Optional evidence types. Bonus reputation for providing optional evidence.",
    )
    location_hint: Optional[str] = Field(
        None,
        max_length=255,
        description="Location hint for workers. Can be city, address, or coordinates.",
        examples=["Miami, FL", "123 Main St, New York, NY 10001"],
    )
    min_reputation: int = Field(
        0,
        ge=0,
        le=100,
        description="Minimum worker reputation score (0-100). Higher requirements may increase completion time.",
    )
    payment_token: str = Field(
        "USDC", max_length=10, description="Payment token. Supported: USDC, EURC, DAI"
    )


class SubmissionApproveRequest(BaseModel):
    """Request body for approving a submission."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notes": "Clear photo showing store is open. Good work!",
                "rating": 5,
            }
        }
    )

    notes: Optional[str] = Field(
        None, max_length=1000, description="Optional notes about the approval"
    )
    rating: Optional[int] = Field(
        None, ge=1, le=5, description="Optional worker rating (1-5 stars)"
    )


class SubmissionRejectRequest(BaseModel):
    """Request body for rejecting a submission."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Photo is blurry and store hours sign is not visible",
                "allow_retry": True,
            }
        }
    )

    reason: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Required reason for rejection. Be specific to help worker improve.",
    )
    allow_retry: bool = Field(
        True,
        description="Allow worker to submit again. If false, task returns to available pool.",
    )


class TaskCancelRequest(BaseModel):
    """Request body for cancelling a task."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "No longer needed - store confirmed open via phone call"
            }
        }
    )

    reason: Optional[str] = Field(
        None, max_length=500, description="Optional reason for cancellation"
    )


class WebhookCreateRequest(BaseModel):
    """Request body for creating a webhook subscription."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://your-server.com/em/webhook",
                "events": ["task.submitted", "task.completed", "payment.released"],
                "secret": None,
            }
        }
    )

    url: str = Field(
        ...,
        description="HTTPS URL to receive webhook events. Must be publicly accessible.",
        examples=["https://your-server.com/em/webhook"],
    )
    events: List[WebhookEventType] = Field(
        ..., min_length=1, description="Event types to subscribe to"
    )
    secret: Optional[str] = Field(
        None,
        description="Custom webhook secret. If not provided, one will be generated.",
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
    min_reputation: int = 0


class BatchCreateRequest(BaseModel):
    """Request body for batch task creation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {
                        "title": "Check store A",
                        "instructions": "Verify if store at Location A is open",
                        "category": "physical_presence",
                        "bounty_usd": 2.00,
                        "deadline_hours": 4,
                        "evidence_required": ["photo"],
                        "location_hint": "Location A",
                    },
                    {
                        "title": "Check store B",
                        "instructions": "Verify if store at Location B is open",
                        "category": "physical_presence",
                        "bounty_usd": 2.00,
                        "deadline_hours": 4,
                        "evidence_required": ["photo"],
                        "location_hint": "Location B",
                    },
                ],
                "payment_token": "USDC",
            }
        }
    )

    tasks: List[BatchTaskDefinition] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of tasks to create (max 50 per batch)",
    )
    payment_token: str = Field(
        "USDC", description="Payment token for all tasks in batch"
    )


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class TaskResponse(BaseModel):
    """Task response model with full details."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "task_abc123def456",
                "title": "Check if Walmart is open",
                "instructions": "Take a photo of the store entrance...",
                "category": "physical_presence",
                "bounty_usd": 2.50,
                "status": "published",
                "deadline": "2026-01-25T20:00:00Z",
                "evidence_required": ["photo", "gps"],
                "evidence_optional": ["text_response"],
                "location_hint": "Miami, FL",
                "min_reputation": 0,
                "executor_id": None,
                "created_at": "2026-01-25T16:00:00Z",
                "escrow_tx": "0x123abc...",
            }
        }
    )

    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    instructions: str = Field(..., description="Task instructions")
    category: str = Field(..., description="Task category")
    bounty_usd: float = Field(..., description="Bounty amount in USD")
    status: TaskStatus = Field(..., description="Current task status")
    deadline: datetime = Field(..., description="Task deadline")
    evidence_required: List[str] = Field(..., description="Required evidence types")
    evidence_optional: Optional[List[str]] = Field(
        None, description="Optional evidence types"
    )
    location_hint: Optional[str] = Field(None, description="Location hint")
    min_reputation: int = Field(0, description="Minimum reputation required")
    executor_id: Optional[str] = Field(None, description="Assigned worker ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    escrow_tx: Optional[str] = Field(None, description="Escrow transaction hash")
    refund_tx: Optional[str] = Field(None, description="Refund transaction hash")
    payment_network: str = Field(
        "base", description="Payment network (e.g. base, ethereum, polygon)"
    )
    payment_token: str = Field(
        "USDC", description="Payment token symbol (e.g. USDC, EURC)"
    )
    erc8004_agent_id: Optional[str] = Field(
        None, description="ERC-8004 on-chain agent ID (if verified)"
    )


class TaskListResponse(BaseModel):
    """Paginated task list response."""

    tasks: List[TaskResponse]
    total: int = Field(..., description="Total number of tasks matching filters")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="More pages available")


class EvidenceMetadata(BaseModel):
    """Metadata for submitted evidence."""

    timestamp: Optional[datetime] = Field(
        None, description="Evidence capture timestamp"
    )
    device: Optional[str] = Field(None, description="Device model")
    camera_source: Optional[str] = Field(None, description="camera or library")
    dimensions: Optional[str] = Field(None, description="Image dimensions")


class LocationData(BaseModel):
    """GPS location data."""

    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    accuracy_meters: Optional[float] = Field(None, description="GPS accuracy")
    timestamp: Optional[datetime] = Field(None, description="Location timestamp")


class SubmissionResponse(BaseModel):
    """Submission response with evidence details."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sub_xyz789",
                "task_id": "task_abc123",
                "executor_id": "worker_456",
                "status": "pending_review",
                "evidence": {
                    "photo": "https://storage.execution.market/evidence/photo_123.jpg",
                    "gps": {"lat": 25.7617, "lng": -80.1918, "accuracy_meters": 10},
                },
                "pre_check_score": 0.92,
                "submitted_at": "2026-01-25T17:30:00Z",
                "notes": "Store confirmed open, hours posted on door",
            }
        }
    )

    id: str = Field(..., description="Submission ID")
    task_id: str = Field(..., description="Associated task ID")
    executor_id: str = Field(..., description="Worker ID who submitted")
    status: str = Field(..., description="Submission status")
    evidence: Dict[str, Any] = Field(..., description="Submitted evidence")
    pre_check_score: Optional[float] = Field(
        None, description="Automated verification score (0-1)"
    )
    submitted_at: datetime = Field(..., description="Submission timestamp")
    notes: Optional[str] = Field(None, description="Worker notes")
    agent_verdict: Optional[str] = Field(None, description="Agent's decision")
    agent_notes: Optional[str] = Field(None, description="Agent's notes")
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")


class SubmissionListResponse(BaseModel):
    """List of submissions for a task."""

    submissions: List[SubmissionResponse]
    total: int


class PaymentResponse(BaseModel):
    """Payment transaction response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "pay_abc123",
                "task_id": "task_abc123",
                "amount_usd": 2.50,
                "token": "USDC",
                "chain": "base",
                "status": "completed",
                "tx_hash": "0xabc123...",
                "from_address": "0x...",
                "to_address": "0x...",
                "timestamp": "2026-01-25T18:00:00Z",
            }
        }
    )

    id: str = Field(..., description="Payment ID")
    task_id: str = Field(..., description="Associated task ID")
    amount_usd: float = Field(..., description="Payment amount in USD")
    token: str = Field(..., description="Payment token")
    chain: str = Field(..., description="Blockchain network")
    status: str = Field(..., description="Payment status")
    tx_hash: Optional[str] = Field(None, description="Transaction hash")
    from_address: Optional[str] = Field(None, description="Sender address")
    to_address: Optional[str] = Field(None, description="Recipient address")
    timestamp: datetime = Field(..., description="Payment timestamp")


class WebhookResponse(BaseModel):
    """Webhook subscription response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "wh_abc123",
                "url": "https://your-server.com/webhook",
                "events": ["task.submitted", "task.completed"],
                "secret": "whsec_abc123...",
                "active": True,
                "created_at": "2026-01-25T16:00:00Z",
            }
        }
    )

    id: str = Field(..., description="Webhook ID")
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Subscribed events")
    secret: str = Field(..., description="Webhook signing secret")
    active: bool = Field(..., description="Whether webhook is active")
    created_at: datetime = Field(..., description="Creation timestamp")


class WebhookListResponse(BaseModel):
    """List of webhook subscriptions."""

    webhooks: List[WebhookResponse]
    total: int


class WebhookEventPayload(BaseModel):
    """Webhook event payload structure."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_123456",
                "type": "task.completed",
                "created_at": "2026-01-25T18:00:00Z",
                "data": {
                    "task_id": "task_abc123",
                    "executor_id": "worker_456",
                    "bounty_usd": 2.50,
                    "payment_tx": "0xabc...",
                },
                "metadata": {
                    "api_version": "2026-01-25",
                    "idempotency_key": "evt_123456",
                },
            }
        }
    )

    id: str = Field(..., description="Event ID")
    type: str = Field(..., description="Event type")
    created_at: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data")
    metadata: Dict[str, Any] = Field(..., description="Event metadata")


class WorkerProfileResponse(BaseModel):
    """Worker profile and reputation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "worker_456",
                "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD6e",
                "display_name": "Juan M.",
                "reputation_score": 87,
                "tasks_completed": 42,
                "tasks_disputed": 1,
                "total_earned_usd": 156.50,
                "available_balance_usd": 12.00,
                "badges": ["verified", "top_performer"],
                "joined_at": "2025-06-15T00:00:00Z",
            }
        }
    )

    id: str
    wallet_address: str
    display_name: Optional[str]
    reputation_score: int = Field(..., ge=0, le=100)
    tasks_completed: int
    tasks_disputed: int
    total_earned_usd: float
    available_balance_usd: float
    badges: List[str]
    joined_at: datetime


class AnalyticsResponse(BaseModel):
    """Analytics and metrics response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period": {
                    "start": "2025-12-26T00:00:00Z",
                    "end": "2026-01-25T23:59:59Z",
                    "days": 30,
                },
                "summary": {
                    "total_tasks": 150,
                    "completed_tasks": 120,
                    "completion_rate": 0.80,
                    "total_spent_usd": 350.00,
                    "avg_bounty_usd": 2.33,
                    "avg_completion_time_hours": 1.5,
                },
                "by_category": {
                    "physical_presence": 80,
                    "knowledge_access": 40,
                    "human_authority": 30,
                },
                "by_status": {
                    "completed": 120,
                    "in_progress": 10,
                    "published": 15,
                    "expired": 3,
                    "cancelled": 2,
                },
            }
        }
    )

    period: Dict[str, Any]
    summary: Dict[str, Any]
    by_category: Dict[str, int]
    by_status: Dict[str, int]
    top_workers: Optional[List[Dict[str, Any]]] = None


class BatchCreateResponse(BaseModel):
    """Batch task creation response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "created": 10,
                "failed": 0,
                "tasks": [
                    {
                        "index": 0,
                        "id": "task_abc123",
                        "title": "Check store A",
                        "bounty_usd": 2.00,
                    }
                ],
                "errors": [],
                "total_bounty": 20.00,
            }
        }
    )

    created: int = Field(..., description="Number of tasks created")
    failed: int = Field(..., description="Number of tasks that failed")
    tasks: List[Dict[str, Any]] = Field(..., description="Created task details")
    errors: List[Dict[str, Any]] = Field(
        ..., description="Error details for failed tasks"
    )
    total_bounty: float = Field(..., description="Total bounty for all created tasks")


class ErrorResponse(BaseModel):
    """Standard error response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "bounty_usd must be at least 0.50",
                "code": "INVALID_BOUNTY",
                "details": {"field": "bounty_usd", "min": 0.50, "received": 0.25},
                "request_id": "req_abc123",
            }
        }
    )

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    request_id: Optional[str] = Field(None, description="Request ID for support")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server time")


class DetailedHealthResponse(BaseModel):
    """Detailed health check with service status."""

    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str] = Field(..., description="Individual service status")
    latency_ms: Dict[str, int] = Field(
        ..., description="Service latency in milliseconds"
    )


# =============================================================================
# OPENAPI GENERATOR
# =============================================================================


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema for Execution Market.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Execution Market API",
        version="1.0.0",
        description="""
# Execution Market - Human Execution Layer for AI Agents

Execution Market enables AI agents to delegate physical-world tasks to human workers
through a secure, verifiable marketplace with instant USDC payments.

## Overview

Execution Market bridges the gap between AI capabilities and physical world actions.
When an AI agent needs something done in the real world (verify a location,
check product availability, make a phone call), Execution Market connects it with
human workers who can complete these tasks and provide verified evidence.

## Authentication

All API requests require Bearer token authentication:

```
Authorization: Bearer YOUR_API_KEY
```

Get your API key at [execution.market/dashboard](https://execution.market/dashboard).

## Rate Limits

| Tier | Requests/min | Requests/day | Webhooks |
|------|--------------|--------------|----------|
| Free | 60 | 1,000 | 3 |
| Pro | 300 | 10,000 | 10 |
| Enterprise | 1,000 | Unlimited | Unlimited |

Rate limit headers are included in every response:
- `X-RateLimit-Limit`: Request limit per minute
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Webhooks

Subscribe to real-time events for asynchronous task monitoring:

| Event | Description |
|-------|-------------|
| `task.created` | Task published to marketplace |
| `task.assigned` | Worker accepted the task |
| `task.submitted` | Evidence submitted for review |
| `task.completed` | Task approved, payment released |
| `task.disputed` | Dispute opened |
| `payment.released` | Payment sent to worker |

Webhook payloads are signed with HMAC-SHA256. Always verify signatures.

## Task Lifecycle

```
PUBLISHED --> ACCEPTED --> IN_PROGRESS --> SUBMITTED --> COMPLETED
     |            |                            |
     v            v                            v
  EXPIRED     CANCELLED                    REJECTED --> DISPUTED --> RESOLVED
```

## Payment Flow

1. **Escrow**: Agent creates task, bounty is escrowed
2. **Work**: Worker completes task, submits evidence
3. **Review**: Agent approves or rejects submission
4. **Payment**: On approval, payment released instantly via x402 protocol
5. **Dispute**: On rejection, worker can dispute for arbitration

## Evidence Verification

Execution Market performs automated verification checks on submitted evidence:

- **Photo Source**: Verifies photo came from device camera, not gallery
- **GPS Validation**: Confirms location matches task requirements
- **Timestamp Check**: Ensures evidence was captured within task window
- **AI Analysis**: Detects potential manipulation or synthetic content
- **Duplicate Detection**: Prevents reuse of evidence across tasks

Pre-check scores (0-1) are provided to help agents make approval decisions.

## SDKs

Official SDKs are available:

- **Python**: `pip install em-sdk`
- **TypeScript/Node**: `npm install @execution-market/sdk`
- **MCP Server**: For Claude and other AI agents

## Base URL

- **Production**: `https://api.execution.market`
- **Sandbox**: `https://sandbox.api.execution.market`
- **Local Dev**: `http://localhost:8000`
        """,
        routes=app.routes,
        tags=[
            {
                "name": "Tasks",
                "description": "Create and manage human execution tasks. Tasks are the core unit of work in Execution Market - each represents a specific action or verification that needs human completion.",
                "externalDocs": {
                    "description": "Task Creation Guide",
                    "url": "https://docs.execution.market/guides/creating-tasks",
                },
            },
            {
                "name": "Submissions",
                "description": "Review and manage worker submissions. Each submission contains evidence for a completed task that requires agent review.",
            },
            {
                "name": "Workers",
                "description": "Worker profile and reputation management. Endpoints for workers to view their profile, earnings, and task history.",
            },
            {
                "name": "Payments",
                "description": "Payment processing and escrow management. Track bounty escrow, releases, and transaction history.",
            },
            {
                "name": "Webhooks",
                "description": "Real-time event notifications. Subscribe to task lifecycle events for asynchronous monitoring.",
            },
            {
                "name": "Analytics",
                "description": "Usage analytics and reporting. Track task completion rates, spending, and worker performance.",
            },
            {
                "name": "Health",
                "description": "System health and status endpoints. No authentication required.",
            },
        ],
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "API key obtained from dashboard. Include in Authorization header.",
        },
        "x402Payment": {
            "type": "apiKey",
            "in": "header",
            "name": "X-402-Payment",
            "description": "x402 protocol payment header for paid endpoints (if applicable)",
        },
    }

    # Apply security globally
    openapi_schema["security"] = [{"bearerAuth": []}]

    # Add servers
    openapi_schema["servers"] = [
        {"url": "https://api.execution.market", "description": "Production server"},
        {
            "url": "https://sandbox.api.execution.market",
            "description": "Sandbox server (test mode)",
        },
        {"url": "http://localhost:8000", "description": "Local development"},
    ]

    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "Full Documentation",
        "url": "https://docs.execution.market",
    }

    # Add logo for ReDoc
    openapi_schema["info"]["x-logo"] = {
        "url": "https://execution.market/logo.png",
        "altText": "Execution Market Logo",
    }

    # Add contact info
    openapi_schema["info"]["contact"] = {
        "name": "Execution Market Support",
        "url": "https://execution.market/support",
        "email": "ultravioletadao@gmail.com",
    }

    # Add license
    openapi_schema["info"]["license"] = {
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0",
    }

    # Add comprehensive examples to components
    openapi_schema["components"]["examples"] = {
        "TaskCreatePhysicalPresence": {
            "summary": "Physical presence verification task",
            "description": "Task to verify if a store is open",
            "value": {
                "title": "Check if Walmart is open",
                "instructions": "Go to the Walmart at 123 Main St. Take a clear photo of the entrance showing if the store is open or closed. Include the hours sign if visible.",
                "category": "physical_presence",
                "bounty_usd": 2.50,
                "deadline_hours": 4,
                "evidence_required": ["photo", "gps"],
                "evidence_optional": ["text_response"],
                "location_hint": "Miami, FL 33101",
            },
        },
        "TaskCreateKnowledgeAccess": {
            "summary": "Knowledge access task",
            "description": "Task to gather local information",
            "value": {
                "title": "Get today's menu at Joe's Diner",
                "instructions": "Visit Joe's Diner and photograph today's specials menu. Include prices if visible.",
                "category": "knowledge_access",
                "bounty_usd": 1.50,
                "deadline_hours": 6,
                "evidence_required": ["photo"],
                "evidence_optional": ["text_response"],
                "location_hint": "Austin, TX",
            },
        },
        "TaskCreateHumanAuthority": {
            "summary": "Human authority task",
            "description": "Task requiring human action/authority",
            "value": {
                "title": "Make reservation at Restaurant",
                "instructions": "Call the restaurant at (555) 123-4567 and make a reservation for 4 people on Friday at 7pm under the name 'Smith'. Confirm the reservation details.",
                "category": "human_authority",
                "bounty_usd": 5.00,
                "deadline_hours": 24,
                "evidence_required": ["text_response"],
                "evidence_optional": ["screenshot"],
                "min_reputation": 50,
            },
        },
        "SubmissionWithEvidence": {
            "summary": "Submission with photo and GPS",
            "value": {
                "id": "sub_xyz789",
                "task_id": "task_abc123",
                "executor_id": "worker_456",
                "status": "pending_review",
                "evidence": {
                    "photo": "https://storage.execution.market/evidence/photo_123.jpg",
                    "gps": {
                        "lat": 25.7617,
                        "lng": -80.1918,
                        "accuracy_meters": 10,
                        "timestamp": "2026-01-25T17:25:00Z",
                    },
                    "text_response": "Store is open. Posted hours: 9am-9pm daily.",
                },
                "pre_check_score": 0.92,
                "submitted_at": "2026-01-25T17:30:00Z",
            },
        },
        "WebhookTaskCompleted": {
            "summary": "Task completed webhook event",
            "value": {
                "id": "evt_123456",
                "type": "task.completed",
                "created_at": "2026-01-25T18:00:00Z",
                "data": {
                    "task_id": "task_abc123",
                    "executor_id": "worker_456",
                    "bounty_usd": 2.50,
                    "payment": {
                        "tx_hash": "0xabc...",
                        "chain": "base",
                        "token": "USDC",
                    },
                },
                "metadata": {
                    "api_version": "2026-01-25",
                    "idempotency_key": "evt_123456",
                },
            },
        },
        "ErrorValidation": {
            "summary": "Validation error response",
            "value": {
                "error": "ValidationError",
                "message": "bounty_usd must be at least 0.50",
                "code": "INVALID_BOUNTY",
                "details": {
                    "field": "bounty_usd",
                    "constraint": "ge",
                    "min": 0.50,
                    "received": 0.25,
                },
                "request_id": "req_abc123",
            },
        },
        "ErrorUnauthorized": {
            "summary": "Unauthorized error response",
            "value": {
                "error": "Unauthorized",
                "message": "Invalid or missing API key",
                "code": "INVALID_API_KEY",
                "request_id": "req_abc123",
            },
        },
        "ErrorNotFound": {
            "summary": "Not found error response",
            "value": {
                "error": "NotFound",
                "message": "Task not found",
                "code": "TASK_NOT_FOUND",
                "details": {"task_id": "task_invalid123"},
                "request_id": "req_abc123",
            },
        },
        "ErrorRateLimit": {
            "summary": "Rate limit error response",
            "value": {
                "error": "RateLimited",
                "message": "Rate limit exceeded. Try again in 45 seconds.",
                "code": "RATE_LIMITED",
                "details": {
                    "limit": 60,
                    "remaining": 0,
                    "reset_at": "2026-01-25T17:01:00Z",
                },
                "request_id": "req_abc123",
            },
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> FastAPI:
    """Setup OpenAPI with custom configuration."""
    app.openapi = lambda: custom_openapi(app)
    return app


# =============================================================================
# SCHEMA EXAMPLES (for backward compatibility)
# =============================================================================


TASK_EXAMPLE = {
    "id": "task_abc123",
    "title": "Check if store is open",
    "instructions": "Take a photo of the storefront showing open/closed status",
    "category": "physical_presence",
    "bounty_usd": 2.50,
    "status": "published",
    "deadline": "2026-01-25T20:00:00Z",
    "evidence_required": ["photo", "text_response"],
    "evidence_optional": ["video"],
    "location_hint": "Miami, FL",
    "min_reputation": 0,
    "payment_token": "USDC",
    "created_at": "2026-01-25T16:00:00Z",
}

SUBMISSION_EXAMPLE = {
    "id": "sub_xyz789",
    "task_id": "task_abc123",
    "worker_id": "worker_def456",
    "status": "pending_review",
    "evidence": {
        "photo": "https://storage.execution.market/evidence/photo_abc.jpg",
        "text_response": "Store is open. Hours posted on door: 9am-9pm daily.",
    },
    "location": {"lat": 25.7617, "lng": -80.1918, "accuracy_meters": 10},
    "submitted_at": "2026-01-25T17:30:00Z",
}

WEBHOOK_EVENT_EXAMPLE = {
    "id": "evt_abc123",
    "type": "task.submitted",
    "timestamp": "2026-01-25T17:00:00Z",
    "data": {
        "task_id": "task_abc123",
        "submission_id": "sub_xyz789",
        "worker_id": "worker_def456",
    },
}

ERROR_EXAMPLE = {
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "bounty_usd must be at least 0.50",
        "details": {"field": "bounty_usd", "min": 0.50},
    }
}


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    # Main functions
    "custom_openapi",
    "setup_openapi",
    # Enums
    "TaskStatus",
    "TaskCategory",
    "EvidenceType",
    "SubmissionVerdict",
    "WebhookEventType",
    # Request models
    "TaskCreateRequest",
    "SubmissionApproveRequest",
    "SubmissionRejectRequest",
    "TaskCancelRequest",
    "WebhookCreateRequest",
    "BatchCreateRequest",
    "BatchTaskDefinition",
    # Response models
    "TaskResponse",
    "TaskListResponse",
    "SubmissionResponse",
    "SubmissionListResponse",
    "PaymentResponse",
    "WebhookResponse",
    "WebhookListResponse",
    "WebhookEventPayload",
    "WorkerProfileResponse",
    "AnalyticsResponse",
    "BatchCreateResponse",
    "ErrorResponse",
    "HealthResponse",
    "DetailedHealthResponse",
    "EvidenceMetadata",
    "LocationData",
    # Examples
    "TASK_EXAMPLE",
    "SUBMISSION_EXAMPLE",
    "WEBHOOK_EVENT_EXAMPLE",
    "ERROR_EXAMPLE",
]
