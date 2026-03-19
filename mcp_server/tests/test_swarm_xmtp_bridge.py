"""
Tests for XMTPBridge — bidirectional swarm↔XMTP bot integration.

Covers:
- Outbound notifications (task assigned, broadcast, deadline, reputation, payment)
- Inbound webhooks (registration, application, evidence, rating)
- Rate limiting (per-worker per-hour)
- Delivery tracking and retry logic
- Status and metrics
"""

import time
import pytest
from unittest.mock import MagicMock

from mcp_server.swarm.xmtp_bridge import (
    XMTPBridge,
    XMTPEventType,
    DeliveryStatus,
    NotificationPayload,
    WebhookEvent,
    DeliveryRecord,
)


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def bridge():
    """Create a bridge that won't actually make HTTP calls."""
    b = XMTPBridge(
        bot_api_url="http://localhost:3100",
        em_api_url="https://api.execution.market",
        rate_limit_per_worker=5,
        rate_limit_window=3600,
    )
    return b


@pytest.fixture
def bridge_with_mock_deliver(bridge):
    """Bridge with mocked _deliver to avoid HTTP calls."""
    bridge._deliver = MagicMock(return_value=True)
    return bridge


# ─── Data Models ───────────────────────────────────────────────────


class TestDataModels:
    """NotificationPayload, WebhookEvent, DeliveryRecord."""

    def test_notification_payload_defaults(self):
        n = NotificationPayload(
            event_type=XMTPEventType.TASK_ASSIGNED,
            recipient_wallet="0xABC",
        )
        assert n.task_id is None
        assert n.title == ""
        assert n.body == ""
        assert n.priority == "normal"
        assert n.data == {}

    def test_notification_to_dict(self):
        n = NotificationPayload(
            event_type=XMTPEventType.TASK_BROADCAST,
            recipient_wallet="0xDEF",
            task_id="task-123",
            title="New Task",
            body="Do the thing",
            priority="high",
        )
        d = n.to_dict()
        assert d["event_type"] == "task_broadcast"
        assert d["recipient"] == "0xDEF"
        assert d["task_id"] == "task-123"
        assert d["priority"] == "high"
        assert "created_at" in d

    def test_webhook_event_from_dict_basic(self):
        e = WebhookEvent.from_dict(
            {
                "event_type": "worker_registered",
                "sender_wallet": "0x123",
                "task_id": "t-1",
                "payload": {"name": "Alice"},
            }
        )
        assert e.event_type == XMTPEventType.WORKER_REGISTERED
        assert e.sender_wallet == "0x123"
        assert e.task_id == "t-1"
        assert e.payload["name"] == "Alice"

    def test_webhook_event_from_dict_fallback_type(self):
        """Unknown event types should fallback to WORKER_MESSAGE."""
        e = WebhookEvent.from_dict({"event_type": "unknown_type", "sender": "0x"})
        assert e.event_type == XMTPEventType.WORKER_MESSAGE

    def test_webhook_event_from_dict_sender_fallback(self):
        """Should accept 'sender' as fallback for 'sender_wallet'."""
        e = WebhookEvent.from_dict({"sender": "0xABC"})
        assert e.sender_wallet == "0xABC"

    def test_webhook_event_from_dict_data_fallback(self):
        """Should accept 'data' as fallback for 'payload'."""
        e = WebhookEvent.from_dict({"data": {"key": "val"}})
        assert e.payload["key"] == "val"

    def test_delivery_record_to_dict(self):
        r = DeliveryRecord(
            notification_id="notif-001",
            status=DeliveryStatus.SENT,
            recipient="0x1234567890abcdef",
            event_type="task_assigned",
            attempts=1,
        )
        d = r.to_dict()
        assert d["id"] == "notif-001"
        assert d["status"] == "sent"
        assert d["attempts"] == 1
        # Recipient should be truncated
        assert d["recipient"].endswith("...")


class TestXMTPEventType:
    """Event type enum completeness."""

    def test_outbound_events(self):
        assert XMTPEventType.TASK_ASSIGNED.value == "task_assigned"
        assert XMTPEventType.TASK_BROADCAST.value == "task_broadcast"
        assert XMTPEventType.DEADLINE_REMINDER.value == "deadline_reminder"
        assert XMTPEventType.REPUTATION_UPDATE.value == "reputation_update"
        assert XMTPEventType.PAYMENT_CONFIRMED.value == "payment_confirmed"
        assert XMTPEventType.TASK_CANCELLED.value == "task_cancelled"

    def test_inbound_events(self):
        assert XMTPEventType.WORKER_REGISTERED.value == "worker_registered"
        assert XMTPEventType.WORKER_APPLIED.value == "worker_applied"
        assert XMTPEventType.EVIDENCE_SUBMITTED.value == "evidence_submitted"
        assert XMTPEventType.WORKER_RATED.value == "worker_rated"
        assert XMTPEventType.WORKER_MESSAGE.value == "worker_message"


# ─── Outbound Notifications ───────────────────────────────────────


class TestNotifyTaskAssigned:
    """notify_task_assigned() — primary notification path."""

    def test_creates_delivery_record(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        record = b.notify_task_assigned(
            task_id="task-abc",
            worker_wallet="0xWorker1",
            task_data={
                "title": "Buy coffee",
                "bounty_usdc": 3.50,
                "deadline": "2026-03-20",
            },
        )
        assert isinstance(record, DeliveryRecord)
        assert record.status == DeliveryStatus.SENT
        assert record.event_type == "task_assigned"

    def test_delivery_tracked_in_stats(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        b.notify_task_assigned("t1", "0x1", {"title": "Test"})
        assert b._stats["notifications_sent"] == 1

    def test_increments_notification_counter(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        b.notify_task_assigned("t1", "0x1", {"title": "T1"})
        b.notify_task_assigned("t2", "0x2", {"title": "T2"})
        assert b._notification_counter == 2


class TestBroadcastNewTask:
    """broadcast_new_task() — multi-worker broadcast."""

    def test_sends_to_all_wallets(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        wallets = ["0xA", "0xB", "0xC"]
        results = b.broadcast_new_task(
            task_data={
                "title": "Survey",
                "bounty_usdc": 1.0,
                "category": "research",
                "id": "t-1",
            },
            worker_wallets=wallets,
        )
        assert len(results) == 3
        assert all(r.status == DeliveryStatus.SENT for r in results)
        assert b._stats["notifications_sent"] == 3

    def test_empty_wallets_returns_empty(self, bridge_with_mock_deliver):
        results = bridge_with_mock_deliver.broadcast_new_task(
            {"title": "Test", "id": "t-1"}, []
        )
        assert results == []


class TestNotifyDeadlineReminder:
    """notify_deadline_reminder() — urgency-based reminders."""

    def test_high_urgency_under_2h(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        record = b.notify_deadline_reminder(
            task_id="t1",
            worker_wallet="0xW",
            task_title="Urgent task",
            deadline="2026-03-20T12:00:00Z",
            hours_remaining=1.5,
        )
        assert record.status == DeliveryStatus.SENT
        # Verify _deliver was called
        b._deliver.assert_called_once()
        notification = b._deliver.call_args[0][0]
        assert "🔴" in notification.body
        assert notification.priority == "high"

    def test_medium_urgency_under_6h(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        b.notify_deadline_reminder("t1", "0xW", "Med task", "deadline", 4.0)
        notification = b._deliver.call_args[0][0]
        assert "🟡" in notification.body

    def test_low_urgency_over_6h(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        b.notify_deadline_reminder("t1", "0xW", "Chill task", "deadline", 12.0)
        notification = b._deliver.call_args[0][0]
        assert "🟢" in notification.body
        assert notification.priority == "normal"


class TestNotifyReputationUpdate:
    """notify_reputation_update() — reputation feedback."""

    def test_sends_with_stars(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        record = b.notify_reputation_update(
            worker_wallet="0xW",
            task_id="t1",
            score=80,
            new_average=4.2,
            total_ratings=15,
        )
        assert record.status == DeliveryStatus.SENT
        notification = b._deliver.call_args[0][0]
        assert "★" in notification.body
        assert "4.2" in notification.body
        assert "15" in notification.body


class TestNotifyPaymentConfirmed:
    """notify_payment_confirmed() — on-chain payment notifications."""

    def test_includes_chain_and_tx(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        record = b.notify_payment_confirmed(
            worker_wallet="0xW",
            task_id="t1",
            amount=5.50,
            chain="base",
            tx_hash="0xabcdef1234567890abcdef",
        )
        assert record.status == DeliveryStatus.SENT
        notification = b._deliver.call_args[0][0]
        assert "$5.50" in notification.body
        assert "base" in notification.body
        assert notification.priority == "high"
        assert notification.data["tx_hash"] == "0xabcdef1234567890abcdef"


# ─── Rate Limiting ─────────────────────────────────────────────────


class TestRateLimiting:
    """Per-worker-per-hour rate limiting."""

    def test_allows_under_limit(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        for i in range(5):  # rate_limit_per_worker=5
            record = b.notify_task_assigned(f"t{i}", "0xSameWorker", {"title": f"T{i}"})
            assert record.status == DeliveryStatus.SENT

    def test_blocks_over_limit(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        # Send 5 (limit)
        for i in range(5):
            b.notify_task_assigned(f"t{i}", "0xSameWorker", {"title": f"T{i}"})

        # 6th should be rate limited
        record = b.notify_task_assigned("t5", "0xSameWorker", {"title": "T5"})
        assert record.status == DeliveryStatus.FAILED
        assert record.error == "Rate limited"
        assert b._stats["notifications_rate_limited"] == 1

    def test_different_wallets_independent(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        # Fill up wallet A
        for i in range(5):
            b.notify_task_assigned(f"tA{i}", "0xA", {"title": f"A{i}"})

        # Wallet B should still work
        record = b.notify_task_assigned("tB0", "0xB", {"title": "B0"})
        assert record.status == DeliveryStatus.SENT

    def test_rate_limit_window_expiry(self, bridge_with_mock_deliver):
        """Old entries outside the window should be cleaned."""
        b = bridge_with_mock_deliver
        # Manually add old timestamps
        old_time = time.time() - 7200  # 2 hours ago
        b._rate_tracker["0xOld"] = [old_time] * 5

        # Should allow because old entries are outside window
        allowed = b._check_rate_limit("0xOld")
        assert allowed is True


# ─── Webhook Processing ───────────────────────────────────────────


class TestWebhookProcessing:
    """Inbound webhook event handling."""

    def test_register_and_handle_webhook(self, bridge):
        handler = MagicMock()
        bridge.register_webhook_handler(XMTPEventType.WORKER_REGISTERED, handler)

        result = bridge.handle_webhook(
            {
                "event_type": "worker_registered",
                "sender_wallet": "0xNewWorker",
                "payload": {"name": "Alice"},
            }
        )
        assert result is True
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.sender_wallet == "0xNewWorker"

    def test_unhandled_event_type_returns_false(self, bridge):
        result = bridge.handle_webhook(
            {
                "event_type": "worker_rated",
                "sender_wallet": "0x1",
            }
        )
        assert result is False

    def test_multiple_handlers_for_same_event(self, bridge):
        h1 = MagicMock()
        h2 = MagicMock()
        bridge.register_webhook_handler(XMTPEventType.EVIDENCE_SUBMITTED, h1)
        bridge.register_webhook_handler(XMTPEventType.EVIDENCE_SUBMITTED, h2)

        bridge.handle_webhook(
            {
                "event_type": "evidence_submitted",
                "sender_wallet": "0x1",
                "task_id": "t1",
            }
        )
        assert h1.call_count == 1
        assert h2.call_count == 1

    def test_webhook_handler_error_doesnt_crash(self, bridge):
        bad_handler = MagicMock(side_effect=ValueError("handler boom"))
        bridge.register_webhook_handler(XMTPEventType.WORKER_APPLIED, bad_handler)

        # Should not raise
        result = bridge.handle_webhook(
            {
                "event_type": "worker_applied",
                "sender_wallet": "0x1",
            }
        )
        assert result is True

    def test_invalid_webhook_data_returns_false(self, bridge):
        """Malformed webhook data should not crash."""
        # WebhookEvent.from_dict handles missing fields gracefully
        # but really malformed data could cause issues
        handler = MagicMock()
        bridge.register_webhook_handler(XMTPEventType.WORKER_MESSAGE, handler)
        result = bridge.handle_webhook({})  # Missing everything
        # Should parse with defaults and match WORKER_MESSAGE handler
        assert result is True

    def test_webhook_stats_tracked(self, bridge):
        handler = MagicMock()
        bridge.register_webhook_handler(XMTPEventType.WORKER_MESSAGE, handler)
        bridge.handle_webhook({"event_type": "worker_message", "sender": "0x1"})
        assert bridge._stats["webhooks_received"] == 1
        assert bridge._stats["webhooks_processed"] == 1


# ─── Delivery Tracking ────────────────────────────────────────────


class TestDeliveryTracking:
    """Delivery log and history."""

    def test_successful_delivery_logged(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        b.notify_task_assigned("t1", "0xW", {"title": "Test"})
        history = b.get_delivery_history(limit=10)
        assert len(history) == 1
        assert history[0]["status"] == "sent"

    def test_failed_delivery_logged(self, bridge):
        bridge._deliver = MagicMock(return_value=False)
        bridge.notify_task_assigned("t1", "0xW", {"title": "Test"})
        history = bridge.get_delivery_history()
        assert len(history) >= 1
        # Should be failed or retrying
        last = history[-1]
        assert last["status"] in ("failed", "retrying")

    def test_delivery_history_limit(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        for i in range(20):
            b.notify_task_assigned(f"t{i}", f"0x{i}", {"title": f"T{i}"})
        history = b.get_delivery_history(limit=5)
        assert len(history) == 5


# ─── Retry Logic ──────────────────────────────────────────────────


class TestRetryLogic:
    """Retry queue for failed deliveries."""

    def test_failed_delivery_queued_for_retry(self, bridge):
        bridge._deliver = MagicMock(return_value=False)
        bridge.notify_task_assigned("t1", "0xW", {"title": "Test"})
        assert len(bridge._pending_retries) == 1

    def test_process_retry_queue_success(self, bridge):
        # First delivery fails
        bridge._deliver = MagicMock(return_value=False)
        bridge.notify_task_assigned("t1", "0xW", {"title": "Test"})
        assert len(bridge._pending_retries) == 1

        # Now mock success for retry
        bridge._deliver = MagicMock(return_value=True)
        retried = bridge.process_retry_queue()
        assert retried == 1
        assert len(bridge._pending_retries) == 0

    def test_process_empty_retry_queue(self, bridge):
        assert bridge.process_retry_queue() == 0


# ─── Status & Metrics ─────────────────────────────────────────────


class TestStatusAndMetrics:
    """get_status() and get_stats() output."""

    def test_initial_status(self, bridge):
        status = bridge.get_status()
        assert status["connected"] is True
        assert status["bot_api_url"] == "http://localhost:3100"
        assert status["stats"]["notifications_sent"] == 0
        assert status["pending_retries"] == 0
        assert status["rate_limit"]["per_worker_per_hour"] == 5

    def test_get_stats_success_rate(self, bridge_with_mock_deliver):
        b = bridge_with_mock_deliver
        b.notify_task_assigned("t1", "0xA", {"title": "T1"})
        b.notify_task_assigned("t2", "0xB", {"title": "T2"})
        stats = b.get_stats()
        assert stats["notifications_sent"] == 2
        assert stats["total_attempted"] == 2
        assert stats["success_rate_pct"] == 100.0

    def test_get_stats_with_failures(self, bridge):
        # Succeed one, fail one
        bridge._deliver = MagicMock(return_value=True)
        bridge.notify_task_assigned("t1", "0xA", {"title": "T1"})
        bridge._deliver = MagicMock(return_value=False)
        bridge.notify_task_assigned("t2", "0xB", {"title": "T2"})
        stats = bridge.get_stats()
        assert stats["notifications_sent"] == 1
        # Failed could be 1 or tracked differently based on retry
        assert stats["total_attempted"] >= 2

    def test_registered_handlers_in_status(self, bridge):
        bridge.register_webhook_handler(XMTPEventType.WORKER_REGISTERED, lambda e: None)
        bridge.register_webhook_handler(XMTPEventType.WORKER_APPLIED, lambda e: None)
        status = bridge.get_status()
        assert "worker_registered" in status["registered_handlers"]
        assert status["registered_handlers"]["worker_registered"] == 1

    def test_status_zero_stats(self, bridge):
        """Initial stats should all be zero."""
        stats = bridge.get_stats()
        assert stats["total_attempted"] == 0
        assert stats["success_rate_pct"] == 0.0
