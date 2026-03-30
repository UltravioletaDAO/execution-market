"""
WebSocket Event Types for Execution Market Real-Time Updates

Defines all real-time event types that can be emitted through WebSocket connections.
These events complement the webhook events but are optimized for real-time delivery.

Event Categories:
- Task lifecycle events
- Application/worker events
- Submission events
- Payment events
- Notification events
- System events
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
import json


class WebSocketEventType(str, Enum):
    """
    All WebSocket event types supported by Execution Market.

    Naming convention: <Category><Action>
    These are optimized for real-time delivery and client-side handling.
    """

    # Task lifecycle events
    TASK_CREATED = "TaskCreated"
    TASK_UPDATED = "TaskUpdated"
    TASK_CANCELLED = "TaskCancelled"
    TASK_EXPIRED = "TaskExpired"
    TASK_COMPLETED = "TaskCompleted"

    # Application/worker events
    APPLICATION_RECEIVED = "ApplicationReceived"
    APPLICATION_WITHDRAWN = "ApplicationWithdrawn"
    WORKER_ASSIGNED = "WorkerAssigned"
    WORKER_UNASSIGNED = "WorkerUnassigned"

    # Submission events
    SUBMISSION_RECEIVED = "SubmissionReceived"
    SUBMISSION_APPROVED = "SubmissionApproved"
    SUBMISSION_REJECTED = "SubmissionRejected"
    SUBMISSION_REVISION_REQUESTED = "SubmissionRevisionRequested"

    # Payment events
    PAYMENT_ESCROWED = "PaymentEscrowed"
    PAYMENT_RELEASED = "PaymentReleased"
    PAYMENT_PARTIAL_RELEASED = "PaymentPartialReleased"
    PAYMENT_REFUNDED = "PaymentRefunded"
    PAYMENT_FAILED = "PaymentFailed"

    # Notification events
    NOTIFICATION_NEW = "NotificationNew"
    NOTIFICATION_READ = "NotificationRead"

    # Audit events
    CHECKPOINT_UPDATED = "CheckpointUpdated"

    # System events
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    SUBSCRIBED = "Subscribed"
    UNSUBSCRIBED = "Unsubscribed"
    ERROR = "Error"
    HEARTBEAT = "Heartbeat"


# ============== EVENT PAYLOADS ==============


@dataclass
class EventMetadata:
    """Standard metadata included in every WebSocket event."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskCreatedPayload:
    """Payload for TaskCreated event."""

    task_id: str
    title: str
    category: str
    bounty_usd: float
    deadline: str
    agent_id: str
    location_hint: Optional[str] = None
    min_reputation: int = 0
    evidence_required: List[str] = field(default_factory=list)
    payment_token: str = "USDC"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TaskUpdatedPayload:
    """Payload for TaskUpdated event."""

    task_id: str
    status: str
    previous_status: Optional[str] = None
    updated_fields: List[str] = field(default_factory=list)
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TaskCancelledPayload:
    """Payload for TaskCancelled event."""

    task_id: str
    title: str
    reason: Optional[str] = None
    cancelled_by: str = ""
    refund_initiated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ApplicationReceivedPayload:
    """Payload for ApplicationReceived event."""

    application_id: str
    task_id: str
    worker_id: str
    worker_name: Optional[str] = None
    worker_reputation: float = 0.0
    message: Optional[str] = None
    applied_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class WorkerAssignedPayload:
    """Payload for WorkerAssigned event."""

    task_id: str
    worker_id: str
    worker_name: Optional[str] = None
    worker_wallet: Optional[str] = None
    assigned_at: Optional[str] = None
    expected_completion: Optional[str] = None
    title: Optional[str] = None
    bounty_usdc: Optional[float] = None
    payment_network: Optional[str] = None
    category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SubmissionReceivedPayload:
    """Payload for SubmissionReceived event."""

    submission_id: str
    task_id: str
    task_title: str
    worker_id: str
    evidence_types: List[str] = field(default_factory=list)
    submitted_at: Optional[str] = None
    auto_verification_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SubmissionApprovedPayload:
    """Payload for SubmissionApproved event."""

    submission_id: str
    task_id: str
    worker_id: str
    approved_by: str
    notes: Optional[str] = None
    payment_initiated: bool = False
    approved_at: Optional[str] = None
    worker_wallet: Optional[str] = None
    title: Optional[str] = None
    bounty_usdc: Optional[float] = None
    payment_network: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SubmissionRejectedPayload:
    """Payload for SubmissionRejected event."""

    submission_id: str
    task_id: str
    worker_id: str
    rejected_by: str
    reason: str
    can_resubmit: bool = True
    rejected_at: Optional[str] = None
    worker_wallet: Optional[str] = None
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PaymentReleasedPayload:
    """Payload for PaymentReleased event."""

    payment_id: str
    task_id: str
    amount_usd: float
    worker_amount: float
    platform_fee: float
    recipient_wallet: str
    tx_hash: Optional[str] = None
    token: str = "USDC"
    chain: str = "base"
    released_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PaymentFailedPayload:
    """Payload for PaymentFailed event."""

    task_id: str
    amount_usd: float
    error_code: str
    error_message: str
    retry_available: bool = True
    failed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class NotificationNewPayload:
    """Payload for NotificationNew event."""

    notification_id: str
    type: str  # "task_update", "payment", "submission", "system"
    title: str
    message: str
    action_url: Optional[str] = None
    task_id: Optional[str] = None
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ============== WEBSOCKET EVENT ==============


@dataclass
class WebSocketEvent:
    """
    Complete WebSocket event with type, payload, and metadata.

    This is the structure sent over WebSocket connections.
    """

    event_type: WebSocketEventType
    payload: Dict[str, Any]
    room: Optional[str] = None  # Target room for this event
    metadata: EventMetadata = field(default_factory=EventMetadata)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event": self.event_type.value,
            "payload": self.payload,
            "room": self.room,
            "metadata": self.metadata.to_dict(),
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSocketEvent":
        """Create from dictionary."""
        event_type_str = data.get("event", "Error")
        try:
            event_type = WebSocketEventType(event_type_str)
        except ValueError:
            event_type = WebSocketEventType.ERROR

        return cls(
            event_type=event_type,
            payload=data.get("payload", {}),
            room=data.get("room"),
        )

    # Factory methods for common events

    @classmethod
    def task_created(
        cls, payload: TaskCreatedPayload, room: Optional[str] = None
    ) -> "WebSocketEvent":
        """Create TaskCreated event."""
        return cls(
            event_type=WebSocketEventType.TASK_CREATED,
            payload=payload.to_dict(),
            room=room or f"user:{payload.agent_id}",
        )

    @classmethod
    def task_updated(cls, payload: TaskUpdatedPayload, room: str) -> "WebSocketEvent":
        """Create TaskUpdated event."""
        return cls(
            event_type=WebSocketEventType.TASK_UPDATED,
            payload=payload.to_dict(),
            room=room,
        )

    @classmethod
    def task_cancelled(
        cls, payload: TaskCancelledPayload, room: str
    ) -> "WebSocketEvent":
        """Create TaskCancelled event."""
        return cls(
            event_type=WebSocketEventType.TASK_CANCELLED,
            payload=payload.to_dict(),
            room=room,
        )

    @classmethod
    def application_received(
        cls, payload: ApplicationReceivedPayload, agent_id: str
    ) -> "WebSocketEvent":
        """Create ApplicationReceived event (sent to task owner)."""
        return cls(
            event_type=WebSocketEventType.APPLICATION_RECEIVED,
            payload=payload.to_dict(),
            room=f"user:{agent_id}",
        )

    @classmethod
    def worker_assigned(
        cls, payload: WorkerAssignedPayload, rooms: List[str]
    ) -> List["WebSocketEvent"]:
        """Create WorkerAssigned events (sent to both task owner and worker)."""
        return [
            cls(
                event_type=WebSocketEventType.WORKER_ASSIGNED,
                payload=payload.to_dict(),
                room=room,
            )
            for room in rooms
        ]

    @classmethod
    def submission_received(
        cls, payload: SubmissionReceivedPayload, agent_id: str
    ) -> "WebSocketEvent":
        """Create SubmissionReceived event."""
        return cls(
            event_type=WebSocketEventType.SUBMISSION_RECEIVED,
            payload=payload.to_dict(),
            room=f"user:{agent_id}",
        )

    @classmethod
    def submission_approved(
        cls, payload: SubmissionApprovedPayload
    ) -> "WebSocketEvent":
        """Create SubmissionApproved event (sent to worker)."""
        return cls(
            event_type=WebSocketEventType.SUBMISSION_APPROVED,
            payload=payload.to_dict(),
            room=f"user:{payload.worker_id}",
        )

    @classmethod
    def submission_rejected(
        cls, payload: SubmissionRejectedPayload
    ) -> "WebSocketEvent":
        """Create SubmissionRejected event (sent to worker)."""
        return cls(
            event_type=WebSocketEventType.SUBMISSION_REJECTED,
            payload=payload.to_dict(),
            room=f"user:{payload.worker_id}",
        )

    @classmethod
    def payment_released(
        cls, payload: PaymentReleasedPayload, worker_id: str
    ) -> "WebSocketEvent":
        """Create PaymentReleased event."""
        return cls(
            event_type=WebSocketEventType.PAYMENT_RELEASED,
            payload=payload.to_dict(),
            room=f"user:{worker_id}",
        )

    @classmethod
    def payment_failed(
        cls, payload: PaymentFailedPayload, user_id: str
    ) -> "WebSocketEvent":
        """Create PaymentFailed event."""
        return cls(
            event_type=WebSocketEventType.PAYMENT_FAILED,
            payload=payload.to_dict(),
            room=f"user:{user_id}",
        )

    @classmethod
    def notification(
        cls, payload: NotificationNewPayload, user_id: str
    ) -> "WebSocketEvent":
        """Create NotificationNew event."""
        return cls(
            event_type=WebSocketEventType.NOTIFICATION_NEW,
            payload=payload.to_dict(),
            room=f"user:{user_id}",
        )

    @classmethod
    def error(cls, message: str, code: str = "UNKNOWN_ERROR") -> "WebSocketEvent":
        """Create Error event."""
        return cls(
            event_type=WebSocketEventType.ERROR,
            payload={"error": message, "code": code},
        )


# ============== ROOM UTILITIES ==============


def get_task_room(task_id: str) -> str:
    """Get the room name for a specific task."""
    return f"task:{task_id}"


def get_user_room(user_id: str) -> str:
    """Get the room name for a specific user."""
    return f"user:{user_id}"


def get_category_room(category: str) -> str:
    """Get the room name for a task category (for browsing workers)."""
    return f"category:{category}"


def get_global_room() -> str:
    """Get the global broadcast room."""
    return "global"


# ============== EXPORTS ==============


__all__ = [
    "WebSocketEventType",
    "EventMetadata",
    "TaskCreatedPayload",
    "TaskUpdatedPayload",
    "TaskCancelledPayload",
    "ApplicationReceivedPayload",
    "WorkerAssignedPayload",
    "SubmissionReceivedPayload",
    "SubmissionApprovedPayload",
    "SubmissionRejectedPayload",
    "PaymentReleasedPayload",
    "PaymentFailedPayload",
    "NotificationNewPayload",
    "WebSocketEvent",
    "get_task_room",
    "get_user_room",
    "get_category_room",
    "get_global_room",
]
