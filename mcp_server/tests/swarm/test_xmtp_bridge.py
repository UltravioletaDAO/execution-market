"""
Tests for XMTPBridge — Connects the KK V2 Swarm to the XMTP Worker Bot.

Covers:
    - XMTPEventType enum
    - DeliveryStatus enum
    - NotificationPayload construction and serialization
    - WebhookEvent construction and from_dict parsing
    - DeliveryRecord tracking and serialization
    - XMTPBridge initialization and configuration
    - Outbound notifications (all types)
    - Rate limiting (per-worker, window-based)
    - Webhook handler registration and dispatching
    - Delivery tracking and history
    - Retry queue processing
    - Stats and metrics
    - Error handling (network errors, timeouts)
"""

import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


from mcp_server.swarm.xmtp_bridge import (
    XMTPEventType,
    DeliveryStatus,
    NotificationPayload,
    WebhookEvent,
    DeliveryRecord,
    XMTPBridge,
)


# ─── XMTPEventType Enum ──────────────────────────────────────────


class TestXMTPEventType:
    def test_outbound_events(self):
        assert XMTPEventType.TASK_ASSIGNED == "task_assigned"
        assert XMTPEventType.TASK_BROADCAST == "task_broadcast"
        assert XMTPEventType.DEADLINE_REMINDER == "deadline_reminder"
        assert XMTPEventType.REPUTATION_UPDATE == "reputation_update"
        assert XMTPEventType.PAYMENT_CONFIRMED == "payment_confirmed"
        assert XMTPEventType.TASK_CANCELLED == "task_cancelled"

    def test_inbound_events(self):
        assert XMTPEventType.WORKER_REGISTERED == "worker_registered"
        assert XMTPEventType.WORKER_APPLIED == "worker_applied"
        assert XMTPEventType.EVIDENCE_SUBMITTED == "evidence_submitted"
        assert XMTPEventType.WORKER_RATED == "worker_rated"
        assert XMTPEventType.WORKER_MESSAGE == "worker_message"


# ─── DeliveryStatus Enum ─────────────────────────────────────────


class TestDeliveryStatus:
    def test_statuses(self):
        assert DeliveryStatus.PENDING == "pending"
        assert DeliveryStatus.SENT == "sent"
        assert DeliveryStatus.DELIVERED == "delivered"
        assert DeliveryStatus.FAILED == "failed"
        assert DeliveryStatus.RETRYING == "retrying"


# ─── NotificationPayload ─────────────────────────────────────────


class TestNotificationPayload:
    def test_basic_creation(self):
        payload = NotificationPayload(
            event_type=XMTPEventType.TASK_ASSIGNED,
            recipient_wallet="0xWallet123",
            task_id="task-001",
            title="New Task",
            body="You've been assigned!",
        )
        assert payload.event_type == XMTPEventType.TASK_ASSIGNED
        assert payload.recipient_wallet == "0xWallet123"
        assert payload.priority == "normal"
        assert isinstance(payload.created_at, datetime)

    def test_to_dict(self):
        payload = NotificationPayload(
            event_type=XMTPEventType.PAYMENT_CONFIRMED,
            recipient_wallet="0xABC",
            task_id="t1",
            title="Payment",
            body="$5 USDC received",
            data={"amount": 5.0},
            priority="high",
        )
        d = payload.to_dict()
        assert d["event_type"] == "payment_confirmed"
        assert d["recipient"] == "0xABC"
        assert d["task_id"] == "t1"
        assert d["data"]["amount"] == 5.0
        assert d["priority"] == "high"
        assert "created_at" in d

    def test_default_values(self):
        payload = NotificationPayload(
            event_type=XMTPEventType.TASK_BROADCAST,
            recipient_wallet="0x000",
        )
        assert payload.task_id is None
        assert payload.title == ""
        assert payload.body == ""
        assert payload.data == {}


# ─── WebhookEvent ────────────────────────────────────────────────


class TestWebhookEvent:
    def test_from_dict_valid(self):
        event = WebhookEvent.from_dict(
            {
                "event_type": "worker_applied",
                "sender_wallet": "0xWorker1",
                "task_id": "task-001",
                "payload": {"message": "I can do this!"},
            }
        )
        assert event.event_type == XMTPEventType.WORKER_APPLIED
        assert event.sender_wallet == "0xWorker1"
        assert event.task_id == "task-001"

    def test_from_dict_unknown_event(self):
        event = WebhookEvent.from_dict(
            {
                "event_type": "totally_unknown",
                "sender_wallet": "0xX",
            }
        )
        assert event.event_type == XMTPEventType.WORKER_MESSAGE  # fallback

    def test_from_dict_missing_fields(self):
        event = WebhookEvent.from_dict({})
        assert event.event_type == XMTPEventType.WORKER_MESSAGE
        assert event.sender_wallet == ""
        assert event.task_id is None

    def test_from_dict_sender_field_alias(self):
        event = WebhookEvent.from_dict(
            {
                "event_type": "worker_registered",
                "sender": "0xAlias",
            }
        )
        assert event.sender_wallet == "0xAlias"

    def test_from_dict_data_field_alias(self):
        event = WebhookEvent.from_dict(
            {
                "event_type": "evidence_submitted",
                "sender_wallet": "0x1",
                "data": {"evidence_url": "https://example.com/photo.jpg"},
            }
        )
        assert event.payload["evidence_url"] == "https://example.com/photo.jpg"


# ─── DeliveryRecord ──────────────────────────────────────────────


class TestDeliveryRecord:
    def test_basic_creation(self):
        record = DeliveryRecord(
            notification_id="notif-001",
            status=DeliveryStatus.PENDING,
            recipient="0xWallet",
            event_type="task_assigned",
        )
        assert record.attempts == 0
        assert record.error is None

    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        record = DeliveryRecord(
            notification_id="notif-002",
            status=DeliveryStatus.SENT,
            recipient="0xLongWalletAddress123456",
            event_type="payment_confirmed",
            attempts=2,
            last_attempt=now,
        )
        d = record.to_dict()
        assert d["id"] == "notif-002"
        assert d["status"] == "sent"
        assert d["recipient"] == "0xLongWall..."  # truncated
        assert d["attempts"] == 2

    def test_to_dict_no_last_attempt(self):
        record = DeliveryRecord(
            notification_id="n",
            status=DeliveryStatus.PENDING,
            recipient="0x",
            event_type="test",
        )
        d = record.to_dict()
        assert d["last_attempt"] is None


# ─── XMTPBridge Initialization ───────────────────────────────────


class TestXMTPBridgeInit:
    def test_default_init(self):
        bridge = XMTPBridge()
        assert bridge.bot_api_url == "http://localhost:3100"
        assert bridge.em_api_url == "https://api.execution.market"
        assert bridge.max_retries == 3
        assert bridge.rate_limit_per_worker == 10

    def test_custom_init(self):
        bridge = XMTPBridge(
            bot_api_url="http://custom:5000/",
            em_api_url="https://staging.api.com/",
            max_retries=5,
            retry_delay_seconds=10,
            rate_limit_per_worker=20,
            rate_limit_window=7200,
        )
        assert bridge.bot_api_url == "http://custom:5000"  # trailing slash stripped
        assert bridge.em_api_url == "https://staging.api.com"
        assert bridge.max_retries == 5
        assert bridge.rate_limit_per_worker == 20
        assert bridge.rate_limit_window == 7200

    def test_initial_stats(self):
        bridge = XMTPBridge()
        assert bridge._stats["notifications_sent"] == 0
        assert bridge._stats["notifications_failed"] == 0
        assert bridge._stats["notifications_rate_limited"] == 0
        assert bridge._stats["webhooks_received"] == 0


# ─── Outbound Notifications ──────────────────────────────────────


class TestNotifyTaskAssigned:
    def _mock_urlopen(self, success=True):
        mock_resp = MagicMock()
        mock_resp.status = 200 if success else 500
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_successful_notification(self):
        bridge = XMTPBridge()
        with patch(
            "mcp_server.swarm.xmtp_bridge.urlopen",
            return_value=self._mock_urlopen(True),
        ):
            record = bridge.notify_task_assigned(
                task_id="task-001",
                worker_wallet="0xWorker123",
                task_data={
                    "title": "Buy coffee",
                    "bounty_usdc": 5.0,
                    "deadline": "2026-03-28",
                },
            )
        assert record.status == DeliveryStatus.SENT
        assert record.delivered_at is not None
        assert bridge._stats["notifications_sent"] == 1

    def test_failed_notification(self):
        from urllib.error import URLError

        bridge = XMTPBridge()
        with patch(
            "mcp_server.swarm.xmtp_bridge.urlopen", side_effect=URLError("refused")
        ):
            record = bridge.notify_task_assigned(
                task_id="task-001",
                worker_wallet="0xWorker",
                task_data={"title": "Test"},
            )
        # Should be RETRYING since attempts < max_retries
        assert record.status == DeliveryStatus.RETRYING
        assert record.error is not None

    def test_notification_body_content(self):
        bridge = XMTPBridge()
        with patch("mcp_server.swarm.xmtp_bridge.urlopen") as mock_url:
            mock_resp = self._mock_urlopen(True)
            mock_url.return_value = mock_resp
            bridge.notify_task_assigned(
                task_id="abcdef12-3456-7890",
                worker_wallet="0xW",
                task_data={
                    "title": "Deliver package",
                    "bounty_usdc": 10.50,
                    "deadline": "Tomorrow",
                },
            )
            # Verify the request payload
            call_args = mock_url.call_args
            req = call_args[0][0]
            assert req.data is not None
            body = json.loads(req.data)
            assert body["event_type"] == "task_assigned"
            assert body["recipient"] == "0xW"


class TestBroadcastNewTask:
    def test_broadcast_to_multiple(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            results = bridge.broadcast_new_task(
                task_data={
                    "id": "t1",
                    "title": "Test",
                    "bounty_usdc": 5,
                    "category": "general",
                },
                worker_wallets=["0xA", "0xB", "0xC"],
            )
        assert len(results) == 3
        assert all(r.status == DeliveryStatus.SENT for r in results)
        assert bridge._stats["notifications_sent"] == 3

    def test_broadcast_empty_wallets(self):
        bridge = XMTPBridge()
        results = bridge.broadcast_new_task(
            task_data={"title": "Test"},
            worker_wallets=[],
        )
        assert results == []


class TestNotifyDeadlineReminder:
    def test_urgent_reminder(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            record = bridge.notify_deadline_reminder(
                task_id="t1",
                worker_wallet="0xW",
                task_title="Urgent delivery",
                deadline="2026-03-27T10:00:00Z",
                hours_remaining=1.5,
            )
        assert record.status == DeliveryStatus.SENT


class TestNotifyReputationUpdate:
    def test_reputation_notification(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            record = bridge.notify_reputation_update(
                worker_wallet="0xW",
                task_id="t1",
                score=85.0,
                new_average=4.2,
                total_ratings=10,
            )
        assert record.status == DeliveryStatus.SENT


class TestNotifyPaymentConfirmed:
    def test_payment_notification(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            record = bridge.notify_payment_confirmed(
                worker_wallet="0xW",
                task_id="t1",
                amount=25.50,
                chain="base",
                tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            )
        assert record.status == DeliveryStatus.SENT


# ─── Rate Limiting ───────────────────────────────────────────────


class TestRateLimiting:
    def test_under_limit_allowed(self):
        bridge = XMTPBridge(rate_limit_per_worker=5)
        for _ in range(4):
            assert bridge._check_rate_limit("0xWallet") is True

    def test_over_limit_denied(self):
        bridge = XMTPBridge(rate_limit_per_worker=3, rate_limit_window=3600)
        for _ in range(3):
            bridge._check_rate_limit("0xWallet")
        assert bridge._check_rate_limit("0xWallet") is False

    def test_different_wallets_independent(self):
        bridge = XMTPBridge(rate_limit_per_worker=2)
        bridge._check_rate_limit("0xA")
        bridge._check_rate_limit("0xA")
        assert bridge._check_rate_limit("0xA") is False
        assert bridge._check_rate_limit("0xB") is True  # Different wallet

    def test_expired_entries_cleaned(self):
        bridge = XMTPBridge(rate_limit_per_worker=2, rate_limit_window=1)
        bridge._rate_tracker["0xW"] = [time.time() - 2, time.time() - 2]  # Expired
        assert bridge._check_rate_limit("0xW") is True

    def test_rate_limited_notification(self):
        bridge = XMTPBridge(rate_limit_per_worker=1)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            # First notification succeeds
            r1 = bridge.notify_task_assigned("t1", "0xW", {"title": "T1"})
            assert r1.status == DeliveryStatus.SENT

            # Second notification rate-limited
            r2 = bridge.notify_task_assigned("t2", "0xW", {"title": "T2"})
            assert r2.status == DeliveryStatus.FAILED
            assert r2.error == "Rate limited"
            assert bridge._stats["notifications_rate_limited"] == 1


# ─── Webhook Handling ────────────────────────────────────────────


class TestWebhookHandling:
    def test_register_and_dispatch(self):
        bridge = XMTPBridge()
        received = []
        bridge.register_webhook_handler(
            XMTPEventType.WORKER_APPLIED,
            lambda event: received.append(event),
        )

        result = bridge.handle_webhook(
            {
                "event_type": "worker_applied",
                "sender_wallet": "0xWorker",
                "task_id": "t1",
            }
        )

        assert result is True
        assert len(received) == 1
        assert received[0].sender_wallet == "0xWorker"

    def test_no_handler_returns_false(self):
        bridge = XMTPBridge()
        result = bridge.handle_webhook(
            {
                "event_type": "worker_registered",
                "sender_wallet": "0x",
            }
        )
        assert result is False

    def test_multiple_handlers(self):
        bridge = XMTPBridge()
        results = []
        bridge.register_webhook_handler(
            XMTPEventType.EVIDENCE_SUBMITTED,
            lambda e: results.append("a"),
        )
        bridge.register_webhook_handler(
            XMTPEventType.EVIDENCE_SUBMITTED,
            lambda e: results.append("b"),
        )

        bridge.handle_webhook(
            {
                "event_type": "evidence_submitted",
                "sender_wallet": "0x",
            }
        )
        assert results == ["a", "b"]

    def test_handler_error_doesnt_crash(self):
        bridge = XMTPBridge()
        bridge.register_webhook_handler(
            XMTPEventType.WORKER_MESSAGE,
            lambda e: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        # This would need actual invocation to trigger the generator
        # Let's use a proper function:
        def bad_handler(event):
            raise RuntimeError("handler exploded")

        bridge._webhook_handlers[XMTPEventType.WORKER_MESSAGE] = [bad_handler]
        bridge.handle_webhook(
            {
                "event_type": "worker_message",
                "sender_wallet": "0x",
            }
        )
        # Should still return True (handlers were registered)
        # but errors logged

    def test_invalid_webhook_data(self):
        bridge = XMTPBridge()
        # Shouldn't crash with weird data
        result = bridge.handle_webhook({"weird_field": 123})
        assert result is False  # No handlers

    def test_webhook_stats(self):
        bridge = XMTPBridge()
        bridge.handle_webhook({"event_type": "unknown", "sender_wallet": "0x"})
        assert bridge._stats["webhooks_received"] == 1


# ─── Retry Queue ─────────────────────────────────────────────────


class TestRetryQueue:
    def test_process_empty_queue(self):
        bridge = XMTPBridge()
        result = bridge.process_retry_queue()
        assert result == 0

    def test_successful_retry(self):
        bridge = XMTPBridge()
        # Add a pending retry
        notification = NotificationPayload(
            event_type=XMTPEventType.TASK_ASSIGNED,
            recipient_wallet="0xRetryWallet",
            task_id="t1",
        )
        bridge._pending_retries.append(notification)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            result = bridge.process_retry_queue()
        assert result == 1
        assert len(bridge._pending_retries) == 0

    def test_failed_retry(self):
        from urllib.error import URLError

        bridge = XMTPBridge()
        notification = NotificationPayload(
            event_type=XMTPEventType.TASK_ASSIGNED,
            recipient_wallet="0xFail",
        )
        bridge._pending_retries.append(notification)

        with patch(
            "mcp_server.swarm.xmtp_bridge.urlopen", side_effect=URLError("still down")
        ):
            result = bridge.process_retry_queue()
        assert result == 0
        assert bridge._stats["notifications_failed"] >= 1


# ─── Status & Metrics ────────────────────────────────────────────


class TestStatusAndMetrics:
    def test_get_status(self):
        bridge = XMTPBridge()
        status = bridge.get_status()
        assert status["connected"] is True
        assert status["bot_api_url"] == "http://localhost:3100"
        assert "stats" in status
        assert "pending_retries" in status
        assert "rate_limit" in status

    def test_get_delivery_history(self):
        bridge = XMTPBridge()
        # Should work with empty log
        history = bridge.get_delivery_history()
        assert history == []

    def test_get_delivery_history_with_records(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            bridge.notify_task_assigned("t1", "0xA", {"title": "T1"})
            bridge.notify_task_assigned("t2", "0xB", {"title": "T2"})

        history = bridge.get_delivery_history(limit=10)
        assert len(history) == 2

    def test_get_stats(self):
        bridge = XMTPBridge()
        stats = bridge.get_stats()
        assert stats["total_attempted"] == 0
        assert stats["success_rate_pct"] == 0.0

    def test_stats_after_operations(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            bridge.notify_task_assigned("t1", "0xA", {"title": "T"})

        stats = bridge.get_stats()
        assert stats["notifications_sent"] == 1
        assert stats["total_attempted"] == 1
        assert stats["success_rate_pct"] == 100.0

    def test_delivery_log_capped(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            for i in range(1100):
                bridge.notify_task_assigned(f"t{i}", f"0x{i}", {"title": f"T{i}"})

        assert len(bridge._delivery_log) == 1000  # maxlen cap

    def test_registered_handlers_in_status(self):
        bridge = XMTPBridge()
        bridge.register_webhook_handler(XMTPEventType.WORKER_APPLIED, lambda e: None)
        bridge.register_webhook_handler(XMTPEventType.WORKER_APPLIED, lambda e: None)

        status = bridge.get_status()
        assert status["registered_handlers"]["worker_applied"] == 2


# ─── Error Handling ──────────────────────────────────────────────


class TestErrorHandling:
    def test_timeout_error(self):
        bridge = XMTPBridge()
        with patch(
            "mcp_server.swarm.xmtp_bridge.urlopen", side_effect=TimeoutError("timeout")
        ):
            record = bridge.notify_task_assigned("t1", "0xW", {"title": "T"})
        assert record.status in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING)
        assert "timeout" in record.error.lower()

    def test_unexpected_error(self):
        bridge = XMTPBridge()
        with patch(
            "mcp_server.swarm.xmtp_bridge.urlopen", side_effect=Exception("weird")
        ):
            record = bridge.notify_task_assigned("t1", "0xW", {"title": "T"})
        assert record.status in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING)

    def test_http_error(self):
        from urllib.error import HTTPError

        bridge = XMTPBridge()
        with patch(
            "mcp_server.swarm.xmtp_bridge.urlopen",
            side_effect=HTTPError("url", 503, "Service Unavailable", {}, None),
        ):
            record = bridge.notify_task_assigned("t1", "0xW", {"title": "T"})
        assert record.status in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING)

    def test_max_retries_exceeded_stays_failed(self):
        from urllib.error import URLError

        bridge = XMTPBridge(max_retries=0)  # No retries
        with patch(
            "mcp_server.swarm.xmtp_bridge.urlopen", side_effect=URLError("down")
        ):
            record = bridge.notify_task_assigned("t1", "0xW", {"title": "T"})
        assert record.status == DeliveryStatus.FAILED
        assert len(bridge._pending_retries) == 0


# ─── Edge Cases ──────────────────────────────────────────────────


class TestXMTPBridgeEdgeCases:
    def test_notification_counter(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            bridge.notify_task_assigned("t1", "0xA", {"title": "T"})
            bridge.notify_task_assigned("t2", "0xB", {"title": "T"})
        assert bridge._notification_counter == 2

    def test_empty_task_data(self):
        bridge = XMTPBridge()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.xmtp_bridge.urlopen", return_value=mock_resp):
            record = bridge.notify_task_assigned("t1", "0xW", {})
        assert record.status == DeliveryStatus.SENT

    def test_rate_tracker_cleanup(self):
        """Rate tracker should clean old entries on check."""
        bridge = XMTPBridge(rate_limit_per_worker=5, rate_limit_window=1)
        bridge._rate_tracker["0xW"] = [time.time() - 10] * 10  # 10 old entries
        # Should clean all old entries
        assert bridge._check_rate_limit("0xW") is True
        assert len(bridge._rate_tracker["0xW"]) == 1  # Only the new one
