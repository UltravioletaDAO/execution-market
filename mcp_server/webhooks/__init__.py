"""
Chamba Webhook Notification System (NOW-087)

Production-ready webhook system with:
- Strongly-typed event payloads
- HMAC-SHA256 signature verification
- Exponential backoff retry logic
- Webhook endpoint registration and management
- Auto-disable for failing endpoints
- Delivery tracking and metrics

Usage:
    from webhooks import (
        WebhookEventType,
        WebhookEvent,
        TaskPayload,
        WebhookRegistry,
        WebhookSender,
        send_webhook,
        get_webhook_registry,
    )

    # Register a webhook
    registry = get_webhook_registry()
    registration = registry.register(
        owner_id="agent_123",
        url="https://example.com/webhooks/chamba",
        events=[WebhookEventType.TASK_CREATED, WebhookEventType.PAYMENT_RELEASED],
        description="My webhook endpoint",
    )

    # Store the secret securely - it's only returned at registration time
    secret = registration.secret

    # Send a webhook event
    event = WebhookEvent.task_created(
        TaskPayload(
            task_id="task_456",
            title="Take photo of storefront",
            status="published",
            category="physical_presence",
            bounty_usd=10.0,
            agent_id="agent_123",
        )
    )

    # Dispatch to all subscribed webhooks
    for webhook in registry.get_by_event(WebhookEventType.TASK_CREATED):
        result = await send_webhook(
            url=webhook.url,
            event=event,
            secret=registry.get_secret(webhook.webhook_id),
            webhook_id=webhook.webhook_id,
        )

        # Record delivery result
        registry.record_delivery(webhook.webhook_id, result.status == "delivered")
"""

# Event types and payloads
from .events import (
    WebhookEventType,
    WebhookEventMetadata,
    WebhookEvent,
    TaskPayload,
    SubmissionPayload,
    PaymentPayload,
    DisputePayload,
    WorkerPayload,
    ReputationPayload,
    EVENT_PAYLOAD_SCHEMAS,
)

# Webhook sender
from .sender import (
    WebhookSender,
    WebhookConfig,
    WebhookSignature,
    DeliveryStatus,
    DeliveryAttempt,
    DeliveryResult,
    send_webhook,
    get_webhook_sender,
)

# Webhook registry
from .registry import (
    WebhookRegistry,
    WebhookEndpoint,
    WebhookRegistration,
    WebhookStatus,
    get_webhook_registry,
)


__all__ = [
    # Events
    "WebhookEventType",
    "WebhookEventMetadata",
    "WebhookEvent",
    "TaskPayload",
    "SubmissionPayload",
    "PaymentPayload",
    "DisputePayload",
    "WorkerPayload",
    "ReputationPayload",
    "EVENT_PAYLOAD_SCHEMAS",
    # Sender
    "WebhookSender",
    "WebhookConfig",
    "WebhookSignature",
    "DeliveryStatus",
    "DeliveryAttempt",
    "DeliveryResult",
    "send_webhook",
    "get_webhook_sender",
    # Registry
    "WebhookRegistry",
    "WebhookEndpoint",
    "WebhookRegistration",
    "WebhookStatus",
    "get_webhook_registry",
]


# Version
__version__ = "1.0.0"
