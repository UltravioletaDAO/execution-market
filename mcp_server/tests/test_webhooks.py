"""
Tests for Webhook Notification System (NOW-087)
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock

from ..webhooks import (
    # Events
    WebhookEventType,
    WebhookEvent,
    TaskPayload,
    SubmissionPayload,
    PaymentPayload,
    DisputePayload,
    WorkerPayload,
    # Sender
    WebhookSender,
    WebhookConfig,
    WebhookSignature,
    DeliveryStatus,
    # Registry
    WebhookRegistry,
    WebhookStatus,
)


# ============== Event Tests ==============


class TestWebhookEventType:
    """Test WebhookEventType enum."""

    def test_event_type_values(self):
        """All event types should have string values."""
        assert WebhookEventType.TASK_CREATED.value == "task.created"
        assert WebhookEventType.PAYMENT_RELEASED.value == "payment.released"
        assert WebhookEventType.DISPUTE_OPENED.value == "dispute.opened"

    def test_event_type_from_string(self):
        """Should be able to create from string value."""
        event_type = WebhookEventType("task.created")
        assert event_type == WebhookEventType.TASK_CREATED


class TestTaskPayload:
    """Test TaskPayload dataclass."""

    def test_minimal_payload(self):
        """Should create payload with required fields."""
        payload = TaskPayload(
            task_id="task_123",
            title="Test Task",
            status="published",
            category="physical_presence",
            bounty_usd=10.0,
            agent_id="agent_456",
        )

        data = payload.to_dict()
        assert data["task_id"] == "task_123"
        assert data["bounty_usd"] == 10.0
        assert "executor_id" not in data  # None values excluded

    def test_full_payload(self):
        """Should include all fields when provided."""
        payload = TaskPayload(
            task_id="task_123",
            title="Test Task",
            status="assigned",
            category="physical_presence",
            bounty_usd=10.0,
            agent_id="agent_456",
            executor_id="worker_789",
            location_hint="Downtown",
        )

        data = payload.to_dict()
        assert data["executor_id"] == "worker_789"
        assert data["location_hint"] == "Downtown"


class TestWebhookEvent:
    """Test WebhookEvent dataclass."""

    def test_event_creation(self):
        """Should create event with metadata."""
        task = TaskPayload(
            task_id="task_123",
            title="Test",
            status="published",
            category="physical_presence",
            bounty_usd=5.0,
            agent_id="agent_1",
        )

        event = WebhookEvent.task_created(task)

        assert event.event_type == WebhookEventType.TASK_CREATED
        assert event.metadata.event_type == "task.created"
        assert event.metadata.api_version == "2026-01-25"
        assert event.metadata.event_id is not None

    def test_event_to_json(self):
        """Should serialize to valid JSON."""
        task = TaskPayload(
            task_id="task_123",
            title="Test",
            status="published",
            category="physical_presence",
            bounty_usd=5.0,
            agent_id="agent_1",
        )

        event = WebhookEvent.task_created(task)
        json_str = event.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["event"] == "task.created"
        assert "metadata" in data
        assert "data" in data

    def test_factory_methods(self):
        """Test all factory methods."""
        # task_created
        task = TaskPayload(
            task_id="t1", title="T", status="s", category="c",
            bounty_usd=1.0, agent_id="a",
        )
        event = WebhookEvent.task_created(task)
        assert event.event_type == WebhookEventType.TASK_CREATED

        # task_assigned
        worker = WorkerPayload(worker_id="w1", task_id="t1")
        event = WebhookEvent.task_assigned(task, worker)
        assert event.event_type == WebhookEventType.TASK_ASSIGNED

        # test_event
        event = WebhookEvent.test_event()
        assert event.event_type == WebhookEventType.WEBHOOK_TEST


# ============== Signature Tests ==============


class TestWebhookSignature:
    """Test HMAC signature generation and verification."""

    def test_generate_signature(self):
        """Should generate valid signature format."""
        payload = '{"test": "data"}'
        secret = "test_secret_key"
        timestamp = 1706189000

        signature = WebhookSignature.generate(payload, secret, timestamp)

        assert signature.startswith("t=1706189000,v1=")
        assert len(signature.split(",")) == 2

    def test_verify_valid_signature(self):
        """Should verify a valid signature."""
        payload = '{"test": "data"}'
        secret = "test_secret_key"
        timestamp = int(time.time())

        signature = WebhookSignature.generate(payload, secret, timestamp)

        assert WebhookSignature.verify(payload, signature, secret)

    def test_verify_invalid_signature(self):
        """Should reject invalid signature."""
        payload = '{"test": "data"}'
        secret = "test_secret_key"
        timestamp = int(time.time())

        signature = WebhookSignature.generate(payload, secret, timestamp)

        # Wrong secret
        assert not WebhookSignature.verify(payload, signature, "wrong_secret")

    def test_verify_expired_signature(self):
        """Should reject expired signature."""
        payload = '{"test": "data"}'
        secret = "test_secret_key"
        # Timestamp 10 minutes ago
        timestamp = int(time.time()) - 600

        signature = WebhookSignature.generate(payload, secret, timestamp)

        with pytest.raises(ValueError, match="Signature timestamp too old"):
            WebhookSignature.verify(payload, signature, secret)

    def test_verify_invalid_format(self):
        """Should reject malformed signature."""
        payload = '{"test": "data"}'
        secret = "test_secret_key"

        with pytest.raises(ValueError, match="Invalid signature format"):
            WebhookSignature.verify(payload, "invalid_signature", secret)


# ============== Sender Tests ==============


class TestWebhookConfig:
    """Test WebhookConfig."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = WebhookConfig()

        assert config.max_retries == 5
        assert config.initial_delay_seconds == 1.0
        assert config.timeout_seconds == 30.0

    def test_calculate_delay_exponential(self):
        """Should calculate exponential backoff."""
        config = WebhookConfig(
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0,
            jitter_factor=0.0,  # Disable jitter for testing
        )

        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
        assert config.calculate_delay(3) == 8.0

    def test_max_delay_cap(self):
        """Should cap delay at max_delay_seconds."""
        config = WebhookConfig(
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0,
            max_delay_seconds=10.0,
            jitter_factor=0.0,
        )

        # 2^10 = 1024, but should be capped at 10
        assert config.calculate_delay(10) == 10.0


class TestWebhookSender:
    """Test WebhookSender."""

    @pytest.fixture
    def sender(self):
        """Create a sender with test config."""
        config = WebhookConfig(
            max_retries=2,
            initial_delay_seconds=0.01,  # Fast retries for tests
            timeout_seconds=5.0,
        )
        return WebhookSender(config=config)

    @pytest.fixture
    def test_event(self):
        """Create a test event."""
        task = TaskPayload(
            task_id="task_123",
            title="Test Task",
            status="published",
            category="physical_presence",
            bounty_usd=10.0,
            agent_id="agent_456",
        )
        return WebhookEvent.task_created(task)

    @pytest.mark.asyncio
    async def test_successful_delivery(self, sender, test_event):
        """Should deliver successfully on 2xx response."""
        with patch.object(sender, "_send_request") as mock_send:
            mock_send.return_value = (200, '{"ok": true}', None, 50)

            result = await sender.send(
                url="https://example.com/webhook",
                event=test_event,
                secret="test_secret",
                webhook_id="wh_123",
            )

        assert result.status == DeliveryStatus.DELIVERED
        assert len(result.attempts) == 1
        assert result.attempts[0].status_code == 200
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, sender, test_event):
        """Should retry on failure."""
        with patch.object(sender, "_send_request") as mock_send:
            # Fail twice, then succeed
            mock_send.side_effect = [
                (500, "Internal Error", None, 100),
                (503, "Service Unavailable", None, 100),
                (200, '{"ok": true}', None, 50),
            ]

            result = await sender.send(
                url="https://example.com/webhook",
                event=test_event,
                secret="test_secret",
                webhook_id="wh_123",
            )

        assert result.status == DeliveryStatus.DELIVERED
        assert len(result.attempts) == 3
        assert result.attempts[0].status_code == 500
        assert result.attempts[1].status_code == 503
        assert result.attempts[2].status_code == 200

    @pytest.mark.asyncio
    async def test_dead_letter_after_max_retries(self, sender, test_event):
        """Should move to dead letter after max retries."""
        dead_letter_called = []

        def dead_letter_callback(result, event):
            dead_letter_called.append((result, event))

        sender.dead_letter_callback = dead_letter_callback

        with patch.object(sender, "_send_request") as mock_send:
            # Always fail
            mock_send.return_value = (500, "Error", None, 100)

            result = await sender.send(
                url="https://example.com/webhook",
                event=test_event,
                secret="test_secret",
                webhook_id="wh_123",
            )

        assert result.status == DeliveryStatus.DEAD_LETTER
        assert len(result.attempts) == 3  # 1 initial + 2 retries
        assert len(dead_letter_called) == 1

    @pytest.mark.asyncio
    async def test_no_retry_when_disabled(self, sender, test_event):
        """Should not retry when retry=False."""
        with patch.object(sender, "_send_request") as mock_send:
            mock_send.return_value = (500, "Error", None, 100)

            result = await sender.send(
                url="https://example.com/webhook",
                event=test_event,
                secret="test_secret",
                webhook_id="wh_123",
                retry=False,
            )

        assert result.status == DeliveryStatus.DEAD_LETTER
        assert len(result.attempts) == 1


# ============== Registry Tests ==============


class TestWebhookRegistry:
    """Test WebhookRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry."""
        return WebhookRegistry()

    def test_register_webhook(self, registry):
        """Should register a new webhook."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
            description="Test webhook",
        )

        assert registration.webhook.webhook_id is not None
        assert registration.webhook.owner_id == "agent_123"
        assert registration.webhook.url == "https://example.com/webhook"
        assert registration.secret is not None
        assert len(registration.secret) > 20  # Should be a long secret

    def test_register_requires_https(self, registry):
        """Should reject non-HTTPS URLs."""
        with pytest.raises(ValueError, match="HTTPS"):
            registry.register(
                owner_id="agent_123",
                url="http://example.com/webhook",
                events=[WebhookEventType.TASK_CREATED],
            )

    def test_register_requires_events(self, registry):
        """Should require at least one event."""
        with pytest.raises(ValueError, match="event type"):
            registry.register(
                owner_id="agent_123",
                url="https://example.com/webhook",
                events=[],
            )

    def test_get_by_owner(self, registry):
        """Should retrieve webhooks by owner."""
        registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook1",
            events=[WebhookEventType.TASK_CREATED],
        )
        registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook2",
            events=[WebhookEventType.PAYMENT_RELEASED],
        )
        registry.register(
            owner_id="agent_456",
            url="https://example.com/webhook3",
            events=[WebhookEventType.TASK_CREATED],
        )

        webhooks = registry.get_by_owner("agent_123")
        assert len(webhooks) == 2

        webhooks = registry.get_by_owner("agent_456")
        assert len(webhooks) == 1

    def test_get_by_event(self, registry):
        """Should retrieve webhooks by event type."""
        registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook1",
            events=[WebhookEventType.TASK_CREATED, WebhookEventType.TASK_COMPLETED],
        )
        registry.register(
            owner_id="agent_456",
            url="https://example.com/webhook2",
            events=[WebhookEventType.TASK_CREATED],
        )
        registry.register(
            owner_id="agent_789",
            url="https://example.com/webhook3",
            events=[WebhookEventType.PAYMENT_RELEASED],
        )

        # Should get both webhooks subscribed to TASK_CREATED
        webhooks = registry.get_by_event(WebhookEventType.TASK_CREATED)
        assert len(webhooks) == 2

        # Should get only one for PAYMENT_RELEASED
        webhooks = registry.get_by_event(WebhookEventType.PAYMENT_RELEASED)
        assert len(webhooks) == 1

    def test_update_webhook(self, registry):
        """Should update webhook fields."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        updated = registry.update(
            webhook_id=registration.webhook.webhook_id,
            owner_id="agent_123",
            description="Updated description",
            events=[WebhookEventType.TASK_CREATED, WebhookEventType.PAYMENT_RELEASED],
        )

        assert updated.description == "Updated description"
        assert WebhookEventType.PAYMENT_RELEASED in updated.events

    def test_update_unauthorized(self, registry):
        """Should reject update from non-owner."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        with pytest.raises(ValueError, match="Not authorized"):
            registry.update(
                webhook_id=registration.webhook.webhook_id,
                owner_id="agent_456",  # Wrong owner
                description="Hacked",
            )

    def test_delete_webhook(self, registry):
        """Should delete webhook."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        result = registry.delete(
            webhook_id=registration.webhook.webhook_id,
            owner_id="agent_123",
        )

        assert result is True
        assert registry.get(registration.webhook.webhook_id) is None

    def test_delete_unauthorized(self, registry):
        """Should reject delete from non-owner."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        result = registry.delete(
            webhook_id=registration.webhook.webhook_id,
            owner_id="agent_456",  # Wrong owner
        )

        assert result is False
        assert registry.get(registration.webhook.webhook_id) is not None

    def test_rotate_secret(self, registry):
        """Should rotate webhook secret."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        old_secret = registration.secret
        new_secret = registry.rotate_secret(
            webhook_id=registration.webhook.webhook_id,
            owner_id="agent_123",
        )

        assert new_secret is not None
        assert new_secret != old_secret

    def test_record_delivery_success(self, registry):
        """Should track successful deliveries."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        webhook_id = registration.webhook.webhook_id

        registry.record_delivery(webhook_id, success=True)
        registry.record_delivery(webhook_id, success=True)

        webhook = registry.get(webhook_id)
        assert webhook.total_deliveries == 2
        assert webhook.successful_deliveries == 2
        assert webhook.failure_count == 0
        assert webhook.last_triggered_at is not None

    def test_auto_disable_on_failures(self, registry):
        """Should auto-disable after max failures."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        webhook_id = registration.webhook.webhook_id

        # Simulate 10 consecutive failures
        for _ in range(10):
            registry.record_delivery(webhook_id, success=False)

        webhook = registry.get(webhook_id)
        assert webhook.status == WebhookStatus.FAILED
        assert webhook.failure_count == 10

    def test_failure_count_resets_on_success(self, registry):
        """Should reset failure count on success."""
        registration = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        webhook_id = registration.webhook.webhook_id

        # 5 failures
        for _ in range(5):
            registry.record_delivery(webhook_id, success=False)

        webhook = registry.get(webhook_id)
        assert webhook.failure_count == 5

        # Then a success
        registry.record_delivery(webhook_id, success=True)

        webhook = registry.get(webhook_id)
        assert webhook.failure_count == 0
        assert webhook.status == WebhookStatus.ACTIVE

    def test_no_duplicate_url_for_owner(self, registry):
        """Should reject duplicate URL for same owner."""
        registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                owner_id="agent_123",
                url="https://example.com/webhook",  # Same URL
                events=[WebhookEventType.PAYMENT_RELEASED],
            )

    def test_same_url_different_owners(self, registry):
        """Should allow same URL for different owners."""
        reg1 = registry.register(
            owner_id="agent_123",
            url="https://example.com/webhook",
            events=[WebhookEventType.TASK_CREATED],
        )

        reg2 = registry.register(
            owner_id="agent_456",
            url="https://example.com/webhook",  # Same URL, different owner
            events=[WebhookEventType.TASK_CREATED],
        )

        assert reg1.webhook.webhook_id != reg2.webhook.webhook_id
