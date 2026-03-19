"""
Tests for XMTPBridge — Swarm ↔ XMTP Bot integration.
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import URLError

from mcp_server.swarm.xmtp_bridge import (
    XMTPBridge,
    XMTPEventType,
    DeliveryStatus,
    NotificationPayload,
    WebhookEvent,
    DeliveryRecord,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def bridge():
    """Create a test bridge instance."""
    return XMTPBridge(
        bot_api_url="http://localhost:3100",
        em_api_url="https://api.execution.market",
        max_retries=2,
        retry_delay_seconds=1,
        rate_limit_per_worker=5,
        rate_limit_window=60,
    )


@pytest.fixture
def mock_urlopen():
    """Mock urlopen for HTTP requests."""
    with patch("mcp_server.swarm.xmtp_bridge.urlopen") as mock:
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        mock.return_value = resp
        yield mock


# ─── NotificationPayload Tests ───────────────────────────────────────────────


class TestNotificationPayload:
    def test_to_dict(self):
        payload = NotificationPayload(
            event_type=XMTPEventType.TASK_ASSIGNED,
            recipient_wallet="0xABC123",
            task_id="task-uuid",
            title="Test Task",
            body="Task body",
            data={"bounty": 5.0},
            priority="high",
        )
        d = payload.to_dict()
        assert d["event_type"] == "task_assigned"
        assert d["recipient"] == "0xABC123"
        assert d["task_id"] == "task-uuid"
        assert d["priority"] == "high"
        assert d["data"]["bounty"] == 5.0

    def test_defaults(self):
        payload = NotificationPayload(
            event_type=XMTPEventType.TASK_BROADCAST,
            recipient_wallet="0x123",
        )
        assert payload.task_id is None
        assert payload.priority == "normal"
        assert payload.data == {}
        assert payload.created_at is not None


# ─── WebhookEvent Tests ──────────────────────────────────────────────────────


class TestWebhookEvent:
    def test_from_dict_valid(self):
        event = WebhookEvent.from_dict({
            "event_type": "evidence_submitted",
            "sender_wallet": "0xWORKER",
            "task_id": "task-123",
            "payload": {"photo_url": "https://..."},
        })
        assert event.event_type == XMTPEventType.EVIDENCE_SUBMITTED
        assert event.sender_wallet == "0xWORKER"
        assert event.task_id == "task-123"

    def test_from_dict_unknown_event_type(self):
        event = WebhookEvent.from_dict({
            "event_type": "unknown_event",
            "sender": "0x123",
        })
        assert event.event_type == XMTPEventType.WORKER_MESSAGE

    def test_from_dict_sender_fallback(self):
        event = WebhookEvent.from_dict({
            "event_type": "worker_registered",
            "sender": "0xFALLBACK",
        })
        assert event.sender_wallet == "0xFALLBACK"

    def test_from_dict_data_fallback(self):
        event = WebhookEvent.from_dict({
            "event_type": "worker_applied",
            "sender_wallet": "0x",
            "data": {"key": "value"},
        })
        assert event.payload == {"key": "value"}


# ─── Task Assignment Notification Tests ───────────────────────────────────────


class TestNotifyTaskAssigned:
    def test_sends_notification(self, bridge, mock_urlopen):
        record = bridge.notify_task_assigned(
            task_id="task-uuid-123",
            worker_wallet="0xWORKER",
            task_data={
                "title": "Deliver coffee",
                "bounty_usdc": 5.0,
                "deadline": "2026-03-20T12:00:00Z",
            },
        )
        assert record.status == DeliveryStatus.SENT
        assert record.recipient == "0xWORKER"
        assert record.event_type == "task_assigned"
        assert mock_urlopen.called

    def test_includes_task_details_in_body(self, bridge, mock_urlopen):
        bridge.notify_task_assigned(
            task_id="task-abc",
            worker_wallet="0xW",
            task_data={"title": "Photo verification", "bounty_usdc": 3.0},
        )
        # Verify the request body was sent correctly
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        assert "Photo verification" in body["body"]
        assert "$3.00" in body["body"]

    def test_high_priority(self, bridge, mock_urlopen):
        bridge.notify_task_assigned(
            "task-id", "0xW", {"title": "Urgent", "bounty": 10}
        )
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["priority"] == "high"


# ─── Task Broadcast Tests ────────────────────────────────────────────────────


class TestBroadcastNewTask:
    def test_broadcasts_to_multiple_workers(self, bridge, mock_urlopen):
        results = bridge.broadcast_new_task(
            task_data={
                "id": "task-xyz",
                "title": "Survey",
                "bounty_usdc": 2.0,
                "category": "research",
            },
            worker_wallets=["0xA", "0xB", "0xC"],
        )
        assert len(results) == 3
        assert all(r.status == DeliveryStatus.SENT for r in results)

    def test_broadcast_includes_apply_command(self, bridge, mock_urlopen):
        bridge.broadcast_new_task(
            task_data={"id": "task-full-uuid", "title": "T", "bounty_usdc": 1},
            worker_wallets=["0xA"],
        )
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "/apply task-ful" in body["body"]

    def test_empty_worker_list(self, bridge, mock_urlopen):
        results = bridge.broadcast_new_task(
            task_data={"id": "t", "title": "T", "bounty": 1},
            worker_wallets=[],
        )
        assert results == []
        assert not mock_urlopen.called


# ─── Deadline Reminder Tests ─────────────────────────────────────────────────


class TestDeadlineReminder:
    def test_urgent_reminder(self, bridge, mock_urlopen):
        record = bridge.notify_deadline_reminder(
            task_id="task-1",
            worker_wallet="0xW",
            task_title="Take photo",
            deadline="2026-03-20T12:00:00Z",
            hours_remaining=1.5,
        )
        assert record.status == DeliveryStatus.SENT
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "🔴" in body["body"]
        assert body["priority"] == "high"

    def test_warning_reminder(self, bridge, mock_urlopen):
        bridge.notify_deadline_reminder(
            "t", "0xW", "Task", "deadline", hours_remaining=4.0
        )
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "🟡" in body["body"]

    def test_normal_reminder(self, bridge, mock_urlopen):
        bridge.notify_deadline_reminder(
            "t", "0xW", "Task", "deadline", hours_remaining=12.0
        )
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "🟢" in body["body"]
        assert body["priority"] == "normal"


# ─── Reputation Update Tests ─────────────────────────────────────────────────


class TestReputationUpdate:
    def test_sends_reputation_notification(self, bridge, mock_urlopen):
        record = bridge.notify_reputation_update(
            worker_wallet="0xWORKER",
            task_id="task-done",
            score=80.0,
            new_average=4.2,
            total_ratings=15,
        )
        assert record.status == DeliveryStatus.SENT
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "4.2" in body["body"]
        assert "15" in body["body"]

    def test_star_visualization(self, bridge, mock_urlopen):
        bridge.notify_reputation_update(
            "0xW", "t", score=60.0, new_average=3.0, total_ratings=5
        )
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "★★★" in body["body"]


# ─── Payment Confirmed Tests ─────────────────────────────────────────────────


class TestPaymentConfirmed:
    def test_sends_payment_notification(self, bridge, mock_urlopen):
        record = bridge.notify_payment_confirmed(
            worker_wallet="0xWORKER",
            task_id="task-paid",
            amount=5.50,
            chain="base",
            tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        )
        assert record.status == DeliveryStatus.SENT
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "$5.50" in body["body"]
        assert "base" in body["body"]
        assert body["priority"] == "high"
        assert body["data"]["tx_hash"].startswith("0x")


# ─── Rate Limiting Tests ─────────────────────────────────────────────────────


class TestRateLimiting:
    def test_allows_within_limit(self, bridge, mock_urlopen):
        for i in range(5):  # Rate limit is 5
            record = bridge.notify_task_assigned(
                f"task-{i}", "0xSAME", {"title": "T", "bounty": 1}
            )
            assert record.status == DeliveryStatus.SENT

    def test_blocks_over_limit(self, bridge, mock_urlopen):
        for i in range(5):
            bridge.notify_task_assigned(
                f"task-{i}", "0xSAME", {"title": "T", "bounty": 1}
            )

        # 6th should be rate limited
        record = bridge.notify_task_assigned(
            "task-6", "0xSAME", {"title": "T", "bounty": 1}
        )
        assert record.status == DeliveryStatus.FAILED
        assert record.error == "Rate limited"
        assert bridge._stats["notifications_rate_limited"] == 1

    def test_different_wallets_independent(self, bridge, mock_urlopen):
        for i in range(5):
            bridge.notify_task_assigned(
                f"task-a{i}", "0xWALLET_A", {"title": "T", "bounty": 1}
            )

        # Different wallet should still work
        record = bridge.notify_task_assigned(
            "task-b1", "0xWALLET_B", {"title": "T", "bounty": 1}
        )
        assert record.status == DeliveryStatus.SENT


# ─── Delivery Failure & Retry Tests ──────────────────────────────────────────


class TestDeliveryFailure:
    def test_handles_network_error(self, bridge):
        with patch("mcp_server.swarm.xmtp_bridge.urlopen") as mock:
            mock.side_effect = URLError("Connection refused")
            record = bridge.notify_task_assigned(
                "task-1", "0xW", {"title": "T", "bounty": 1}
            )
            # Should be retrying (under max_retries=2)
            assert record.status == DeliveryStatus.RETRYING
            assert "Connection refused" in (record.error or "")

    def test_retry_queue_populated(self, bridge):
        with patch("mcp_server.swarm.xmtp_bridge.urlopen") as mock:
            mock.side_effect = URLError("Timeout")
            bridge.notify_task_assigned(
                "task-1", "0xW", {"title": "T", "bounty": 1}
            )
            assert len(bridge._pending_retries) == 1

    def test_process_retry_queue_success(self, bridge, mock_urlopen):
        # Manually add a pending retry
        notification = NotificationPayload(
            event_type=XMTPEventType.TASK_ASSIGNED,
            recipient_wallet="0xW",
            task_id="task-retry",
            title="Retry",
            body="body",
        )
        bridge._pending_retries.append(notification)

        successes = bridge.process_retry_queue()
        assert successes == 1
        assert len(bridge._pending_retries) == 0

    def test_process_empty_retry_queue(self, bridge):
        successes = bridge.process_retry_queue()
        assert successes == 0


# ─── Webhook Handling Tests ──────────────────────────────────────────────────


class TestWebhookHandling:
    def test_register_and_handle(self, bridge):
        received = []

        def handler(event):
            received.append(event)

        bridge.register_webhook_handler(
            XMTPEventType.EVIDENCE_SUBMITTED, handler
        )

        result = bridge.handle_webhook({
            "event_type": "evidence_submitted",
            "sender_wallet": "0xWORKER",
            "task_id": "task-123",
            "payload": {"photo": "url"},
        })

        assert result is True
        assert len(received) == 1
        assert received[0].task_id == "task-123"

    def test_unhandled_event_type(self, bridge):
        result = bridge.handle_webhook({
            "event_type": "worker_registered",
            "sender_wallet": "0xW",
        })
        assert result is False

    def test_multiple_handlers(self, bridge):
        calls = []

        bridge.register_webhook_handler(
            XMTPEventType.WORKER_APPLIED, lambda e: calls.append("h1")
        )
        bridge.register_webhook_handler(
            XMTPEventType.WORKER_APPLIED, lambda e: calls.append("h2")
        )

        bridge.handle_webhook({
            "event_type": "worker_applied",
            "sender_wallet": "0xW",
        })

        assert calls == ["h1", "h2"]

    def test_handler_error_doesnt_crash(self, bridge):
        def bad_handler(event):
            raise ValueError("boom")

        bridge.register_webhook_handler(
            XMTPEventType.WORKER_MESSAGE, bad_handler
        )

        # Should not raise
        bridge.handle_webhook({
            "event_type": "worker_message",
            "sender_wallet": "0xW",
        })

    def test_stats_updated(self, bridge):
        bridge.register_webhook_handler(
            XMTPEventType.WORKER_RATED, lambda e: None
        )

        bridge.handle_webhook({
            "event_type": "worker_rated",
            "sender_wallet": "0xW",
        })

        assert bridge._stats["webhooks_received"] == 1
        assert bridge._stats["webhooks_processed"] == 1


# ─── Status & Metrics Tests ──────────────────────────────────────────────────


class TestStatusMetrics:
    def test_get_status(self, bridge):
        status = bridge.get_status()
        assert status["bot_api_url"] == "http://localhost:3100"
        assert "stats" in status
        assert "pending_retries" in status
        assert status["rate_limit"]["per_worker_per_hour"] == 5

    def test_get_stats(self, bridge, mock_urlopen):
        bridge.notify_task_assigned(
            "t1", "0xW", {"title": "T", "bounty": 1}
        )
        stats = bridge.get_stats()
        assert stats["notifications_sent"] == 1
        assert stats["total_attempted"] == 1
        assert stats["success_rate_pct"] == 100.0

    def test_delivery_history(self, bridge, mock_urlopen):
        bridge.notify_task_assigned(
            "t1", "0xW1", {"title": "T1", "bounty": 1}
        )
        bridge.notify_task_assigned(
            "t2", "0xW2", {"title": "T2", "bounty": 2}
        )

        history = bridge.get_delivery_history(limit=10)
        assert len(history) == 2
        assert history[0]["event"] == "task_assigned"

    def test_stats_with_failures(self, bridge):
        with patch("mcp_server.swarm.xmtp_bridge.urlopen") as mock:
            mock.side_effect = URLError("fail")
            bridge.notify_task_assigned(
                "t1", "0xW", {"title": "T", "bounty": 1}
            )

        stats = bridge.get_stats()
        # First attempt fails → notifications_failed incremented in _send_notification
        # even though it goes to retry queue. The retry queue processes separately.
        assert stats["notifications_sent"] == 0
        assert stats["notifications_failed"] == 1
        assert stats["total_attempted"] == 1
        assert stats["success_rate_pct"] == 0.0


# ─── DeliveryRecord Tests ────────────────────────────────────────────────────


class TestDeliveryRecord:
    def test_to_dict(self):
        record = DeliveryRecord(
            notification_id="notif-001",
            status=DeliveryStatus.SENT,
            recipient="0x1234567890abcdef",
            event_type="task_assigned",
            attempts=1,
        )
        d = record.to_dict()
        assert d["id"] == "notif-001"
        assert d["status"] == "sent"
        assert "0x12345678" in d["recipient"]  # Truncated
        assert d["attempts"] == 1

    def test_to_dict_with_error(self):
        record = DeliveryRecord(
            notification_id="notif-002",
            status=DeliveryStatus.FAILED,
            recipient="0xABC",
            event_type="deadline_reminder",
            error="Connection refused",
        )
        d = record.to_dict()
        assert d["error"] == "Connection refused"
