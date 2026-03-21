"""WebSocket event type constants and room helpers."""

from __future__ import annotations


class EventType:
    """All WebSocket event types emitted by the EM server."""

    # Task lifecycle
    TASK_CREATED = "TaskCreated"
    TASK_UPDATED = "TaskUpdated"
    TASK_CANCELLED = "TaskCancelled"
    TASK_EXPIRED = "TaskExpired"
    TASK_COMPLETED = "TaskCompleted"

    # Applications / workers
    APPLICATION_RECEIVED = "ApplicationReceived"
    APPLICATION_WITHDRAWN = "ApplicationWithdrawn"
    WORKER_ASSIGNED = "WorkerAssigned"
    WORKER_UNASSIGNED = "WorkerUnassigned"

    # Submissions
    SUBMISSION_RECEIVED = "SubmissionReceived"
    SUBMISSION_APPROVED = "SubmissionApproved"
    SUBMISSION_REJECTED = "SubmissionRejected"
    SUBMISSION_REVISION_REQUESTED = "SubmissionRevisionRequested"

    # Payments
    PAYMENT_ESCROWED = "PaymentEscrowed"
    PAYMENT_RELEASED = "PaymentReleased"
    PAYMENT_PARTIAL_RELEASED = "PaymentPartialReleased"
    PAYMENT_REFUNDED = "PaymentRefunded"
    PAYMENT_FAILED = "PaymentFailed"

    # Notifications
    NOTIFICATION_NEW = "NotificationNew"
    NOTIFICATION_READ = "NotificationRead"

    # System
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    ERROR = "Error"
    HEARTBEAT = "Heartbeat"


def task_room(task_id: str) -> str:
    """Room name for a specific task: ``task:<id>``."""
    return f"task:{task_id}"


def user_room(user_id: str) -> str:
    """Room name for a specific user: ``user:<id>``."""
    return f"user:{user_id}"


def category_room(category: str) -> str:
    """Room name for a task category: ``category:<cat>``."""
    return f"category:{category}"


GLOBAL_ROOM = "global"
