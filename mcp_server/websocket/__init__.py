"""
Execution Market WebSocket Module for Real-Time Updates

This module provides WebSocket-based real-time communication for the Execution Market
human execution layer. It enables AI agents and workers to receive instant
notifications about task lifecycle events, submissions, and payments.

Components:
- server.py: WebSocket server and connection manager
- events.py: Event type definitions and payloads
- handlers.py: Event broadcasting handlers
- client.py: Python client for testing

Usage:

    # In FastAPI app
    from websocket import ws_router, ws_manager, handlers

    app.include_router(ws_router)

    # Emit events when state changes
    await handlers.task_created(task_data)
    await handlers.submission_received(submission, task)
    await handlers.payment_released(payment, task, worker_id)

Room Types:
- user:<user_id> - Personal notifications for a user
- task:<task_id> - Updates for a specific task
- category:<category> - New tasks in a category (for workers browsing)
- global - System-wide announcements

Event Types:
- TaskCreated, TaskUpdated, TaskCancelled
- ApplicationReceived, WorkerAssigned
- SubmissionReceived, SubmissionApproved, SubmissionRejected
- PaymentReleased, PaymentFailed
- NotificationNew
"""

# Server components
from .server import (
    WebSocketManager,
    Connection,
    ConnectionState,
    ServerMessage,
    ServerMessageType,
    ClientMessageType,
    ws_manager,
    ws_router,
)

# Event types and payloads
from .events import (
    WebSocketEventType,
    WebSocketEvent,
    EventMetadata,
    TaskCreatedPayload,
    TaskUpdatedPayload,
    TaskCancelledPayload,
    ApplicationReceivedPayload,
    WorkerAssignedPayload,
    SubmissionReceivedPayload,
    SubmissionApprovedPayload,
    SubmissionRejectedPayload,
    PaymentReleasedPayload,
    PaymentFailedPayload,
    NotificationNewPayload,
    get_task_room,
    get_user_room,
    get_category_room,
    get_global_room,
)

# Event handlers
from .handlers import (
    EventHandlers,
    EventRateLimiter,
    handlers,
    rate_limiter,
)

# Integration helpers
from .integration import (
    EventEmitter,
    events,
    emit_event,
    is_websocket_available,
)

# Client (optional, for testing)
try:
    from .client import (
        EMWebSocketClient,
        ClientConfig,
        ReceivedMessage,
        connect_and_subscribe,
    )
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    EMWebSocketClient = None
    ClientConfig = None
    ReceivedMessage = None
    connect_and_subscribe = None


__all__ = [
    # Server
    "WebSocketManager",
    "Connection",
    "ConnectionState",
    "ServerMessage",
    "ServerMessageType",
    "ClientMessageType",
    "ws_manager",
    "ws_router",
    # Events
    "WebSocketEventType",
    "WebSocketEvent",
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
    "get_task_room",
    "get_user_room",
    "get_category_room",
    "get_global_room",
    # Handlers
    "EventHandlers",
    "EventRateLimiter",
    "handlers",
    "rate_limiter",
    # Integration
    "EventEmitter",
    "events",
    "emit_event",
    "is_websocket_available",
    # Client (conditional)
    "EMWebSocketClient",
    "ClientConfig",
    "ReceivedMessage",
    "connect_and_subscribe",
    "CLIENT_AVAILABLE",
]
