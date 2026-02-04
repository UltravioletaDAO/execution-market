"""
Webhook Event Types and Payloads (NOW-087)

Defines all webhook events that Execution Market can emit to registered endpoints.
Each event has a strongly-typed payload schema for validation.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
import json


class WebhookEventType(str, Enum):
    """
    All webhook event types supported by Execution Market.

    Naming convention: <resource>.<action>
    """
    # Task lifecycle events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_SUBMITTED = "task.submitted"
    TASK_COMPLETED = "task.completed"
    TASK_EXPIRED = "task.expired"
    TASK_CANCELLED = "task.cancelled"

    # Submission events
    SUBMISSION_RECEIVED = "submission.received"
    SUBMISSION_APPROVED = "submission.approved"
    SUBMISSION_REJECTED = "submission.rejected"
    SUBMISSION_REVISION_REQUESTED = "submission.revision_requested"

    # Payment events
    PAYMENT_ESCROWED = "payment.escrowed"
    PAYMENT_RELEASED = "payment.released"
    PAYMENT_PARTIAL_RELEASED = "payment.partial_released"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_FAILED = "payment.failed"

    # Dispute events
    DISPUTE_OPENED = "dispute.opened"
    DISPUTE_EVIDENCE_SUBMITTED = "dispute.evidence_submitted"
    DISPUTE_RESOLVED = "dispute.resolved"
    DISPUTE_ESCALATED = "dispute.escalated"

    # Worker events
    WORKER_APPLIED = "worker.applied"
    WORKER_ACCEPTED = "worker.accepted"
    WORKER_REJECTED = "worker.rejected"

    # Reputation events
    REPUTATION_UPDATED = "reputation.updated"

    # System events
    WEBHOOK_TEST = "webhook.test"


@dataclass
class WebhookEventMetadata:
    """
    Standard metadata included in every webhook event.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    api_version: str = "2026-01-25"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPayload:
    """Payload for task-related events."""
    task_id: str
    title: str
    status: str
    category: str
    bounty_usd: float
    agent_id: str
    executor_id: Optional[str] = None
    deadline: Optional[str] = None
    location_hint: Optional[str] = None
    evidence_required: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SubmissionPayload:
    """Payload for submission-related events."""
    submission_id: str
    task_id: str
    executor_id: str
    status: str
    evidence_types: List[str] = field(default_factory=list)
    verification_score: Optional[float] = None
    verification_details: Optional[Dict[str, Any]] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewer_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PaymentPayload:
    """Payload for payment-related events."""
    payment_id: str
    task_id: str
    amount_usd: float
    token: str = "USDC"
    chain: str = "base"
    tx_hash: Optional[str] = None
    escrow_id: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    status: str = "pending"
    timestamp: Optional[str] = None
    gas_used: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DisputePayload:
    """Payload for dispute-related events."""
    dispute_id: str
    task_id: str
    submission_id: str
    initiator_id: str
    respondent_id: str
    reason: str
    status: str
    amount_disputed: float
    evidence_count: int = 0
    opened_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class WorkerPayload:
    """Payload for worker-related events."""
    worker_id: str
    task_id: str
    wallet_address: Optional[str] = None
    reputation_score: Optional[float] = None
    completed_tasks: Optional[int] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ReputationPayload:
    """Payload for reputation update events."""
    entity_id: str
    entity_type: str  # "worker" or "agent"
    old_score: float
    new_score: float
    change_reason: str
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class WebhookEvent:
    """
    Complete webhook event with metadata and payload.

    This is the structure that gets sent to webhook endpoints.
    """
    event_type: WebhookEventType
    payload: Dict[str, Any]
    metadata: WebhookEventMetadata = field(default_factory=WebhookEventMetadata)

    def __post_init__(self):
        self.metadata.event_type = self.event_type.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event": self.event_type.value,
            "data": self.payload,
            "metadata": self.metadata.to_dict(),
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def task_created(cls, task: TaskPayload) -> "WebhookEvent":
        """Factory for task.created event."""
        return cls(
            event_type=WebhookEventType.TASK_CREATED,
            payload=task.to_dict(),
        )

    @classmethod
    def task_assigned(cls, task: TaskPayload, worker: WorkerPayload) -> "WebhookEvent":
        """Factory for task.assigned event."""
        return cls(
            event_type=WebhookEventType.TASK_ASSIGNED,
            payload={
                "task": task.to_dict(),
                "worker": worker.to_dict(),
            },
        )

    @classmethod
    def submission_received(cls, submission: SubmissionPayload, task: TaskPayload) -> "WebhookEvent":
        """Factory for submission.received event."""
        return cls(
            event_type=WebhookEventType.SUBMISSION_RECEIVED,
            payload={
                "submission": submission.to_dict(),
                "task": task.to_dict(),
            },
        )

    @classmethod
    def payment_released(cls, payment: PaymentPayload, task: TaskPayload) -> "WebhookEvent":
        """Factory for payment.released event."""
        return cls(
            event_type=WebhookEventType.PAYMENT_RELEASED,
            payload={
                "payment": payment.to_dict(),
                "task": task.to_dict(),
            },
        )

    @classmethod
    def dispute_opened(cls, dispute: DisputePayload) -> "WebhookEvent":
        """Factory for dispute.opened event."""
        return cls(
            event_type=WebhookEventType.DISPUTE_OPENED,
            payload=dispute.to_dict(),
        )

    @classmethod
    def test_event(cls) -> "WebhookEvent":
        """Factory for webhook.test event (ping)."""
        return cls(
            event_type=WebhookEventType.WEBHOOK_TEST,
            payload={"message": "Webhook test successful"},
        )


# Event type to payload type mapping for validation
EVENT_PAYLOAD_SCHEMAS: Dict[WebhookEventType, type] = {
    WebhookEventType.TASK_CREATED: TaskPayload,
    WebhookEventType.TASK_UPDATED: TaskPayload,
    WebhookEventType.TASK_ASSIGNED: TaskPayload,
    WebhookEventType.TASK_STARTED: TaskPayload,
    WebhookEventType.TASK_SUBMITTED: TaskPayload,
    WebhookEventType.TASK_COMPLETED: TaskPayload,
    WebhookEventType.TASK_EXPIRED: TaskPayload,
    WebhookEventType.TASK_CANCELLED: TaskPayload,
    WebhookEventType.SUBMISSION_RECEIVED: SubmissionPayload,
    WebhookEventType.SUBMISSION_APPROVED: SubmissionPayload,
    WebhookEventType.SUBMISSION_REJECTED: SubmissionPayload,
    WebhookEventType.SUBMISSION_REVISION_REQUESTED: SubmissionPayload,
    WebhookEventType.PAYMENT_ESCROWED: PaymentPayload,
    WebhookEventType.PAYMENT_RELEASED: PaymentPayload,
    WebhookEventType.PAYMENT_PARTIAL_RELEASED: PaymentPayload,
    WebhookEventType.PAYMENT_REFUNDED: PaymentPayload,
    WebhookEventType.PAYMENT_FAILED: PaymentPayload,
    WebhookEventType.DISPUTE_OPENED: DisputePayload,
    WebhookEventType.DISPUTE_EVIDENCE_SUBMITTED: DisputePayload,
    WebhookEventType.DISPUTE_RESOLVED: DisputePayload,
    WebhookEventType.DISPUTE_ESCALATED: DisputePayload,
    WebhookEventType.WORKER_APPLIED: WorkerPayload,
    WebhookEventType.WORKER_ACCEPTED: WorkerPayload,
    WebhookEventType.WORKER_REJECTED: WorkerPayload,
    WebhookEventType.REPUTATION_UPDATED: ReputationPayload,
}
