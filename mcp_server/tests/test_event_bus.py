"""
Tests for EventBus — unified event system for KK V2 Swarm.
"""

import pytest
from unittest.mock import MagicMock, patch

from mcp_server.swarm.event_bus import (
    EventBus,
    Event,
    Subscription,
    TASK_ASSIGNED,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_EXPIRED,
    AGENT_REGISTERED,
    AGENT_ACTIVATED,
    AGENT_ERROR,
    WORKER_REGISTERED,
    WORKER_APPLIED,
    SWARM_CYCLE_START,
    SWARM_CYCLE_END,
    NOTIFICATION_SENT,
    REPUTATION_UPDATED,
    PAYMENT_CONFIRMED,
    SKILL_DNA_UPDATED,
)


@pytest.fixture
def bus():
    return EventBus(history_size=100, error_threshold=3)


# ─── Basic Pub/Sub ────────────────────────────────────────────────────────────


class TestBasicPubSub:
    def test_emit_with_no_subscribers(self, bus):
        event = bus.emit("task.discovered", {"task_id": "t1"})
        assert event.type == "task.discovered"
        assert event.data["task_id"] == "t1"

    def test_subscribe_and_receive(self, bus):
        received = []
        bus.on("task.assigned", lambda e: received.append(e))
        bus.emit(TASK_ASSIGNED, {"task_id": "t1", "agent_id": 42})
        assert len(received) == 1
        assert received[0].data["task_id"] == "t1"

    def test_multiple_subscribers(self, bus):
        calls = []
        bus.on(TASK_COMPLETED, lambda e: calls.append("A"))
        bus.on(TASK_COMPLETED, lambda e: calls.append("B"))
        bus.emit(TASK_COMPLETED, {"task_id": "t1"})
        assert calls == ["A", "B"]

    def test_no_cross_event_delivery(self, bus):
        received = []
        bus.on(TASK_ASSIGNED, lambda e: received.append(e))
        bus.emit(TASK_COMPLETED, {"task_id": "t1"})
        assert len(received) == 0

    def test_event_source_preserved(self, bus):
        received = []
        bus.on("*", lambda e: received.append(e))
        bus.emit(TASK_ASSIGNED, {"x": 1}, source="coordinator")
        assert received[0].source == "coordinator"

    def test_correlation_id_preserved(self, bus):
        received = []
        bus.on("*", lambda e: received.append(e))
        bus.emit(TASK_ASSIGNED, {}, correlation_id="trace-123")
        assert received[0].correlation_id == "trace-123"


# ─── Wildcard Pattern Matching ────────────────────────────────────────────────


class TestPatternMatching:
    def test_exact_match(self, bus):
        received = []
        bus.on("task.assigned", lambda e: received.append(e))
        bus.emit("task.assigned")
        bus.emit("task.completed")
        assert len(received) == 1

    def test_star_wildcard_prefix(self, bus):
        received = []
        bus.on("task.*", lambda e: received.append(e))
        bus.emit("task.assigned")
        bus.emit("task.completed")
        bus.emit("task.failed")
        bus.emit("agent.registered")  # Should NOT match
        assert len(received) == 3

    def test_star_wildcard_suffix(self, bus):
        received = []
        bus.on("*.completed", lambda e: received.append(e))
        bus.emit("task.completed")
        bus.emit("agent.completed")  # Not a real event but matches
        bus.emit("task.assigned")  # Should NOT match
        assert len(received) == 2

    def test_catch_all_wildcard(self, bus):
        received = []
        bus.on("*", lambda e: received.append(e))
        bus.emit("task.assigned")
        bus.emit("agent.error")
        bus.emit("notification.sent")
        assert len(received) == 3

    def test_static_matches_method(self):
        assert EventBus._matches("task.assigned", "task.assigned") is True
        assert EventBus._matches("task.*", "task.assigned") is True
        assert EventBus._matches("task.*", "agent.assigned") is False
        assert EventBus._matches("*", "anything") is True
        assert EventBus._matches("*.error", "agent.error") is True
        assert EventBus._matches("*.error", "agent.registered") is False


# ─── Unsubscribe ──────────────────────────────────────────────────────────────


class TestUnsubscribe:
    def test_off_removes_subscription(self, bus):
        received = []
        sub = bus.on(TASK_ASSIGNED, lambda e: received.append(e))
        bus.emit(TASK_ASSIGNED)
        assert len(received) == 1

        bus.off(sub)
        bus.emit(TASK_ASSIGNED)
        assert len(received) == 1  # No new events

    def test_off_returns_false_for_unknown(self, bus):
        sub = Subscription(pattern="x", handler=lambda e: None)
        assert bus.off(sub) is False


# ─── Once (single-fire) ──────────────────────────────────────────────────────


class TestOnce:
    def test_once_fires_once(self, bus):
        received = []
        bus.once(TASK_ASSIGNED, lambda e: received.append(e))
        bus.emit(TASK_ASSIGNED)
        bus.emit(TASK_ASSIGNED)
        bus.emit(TASK_ASSIGNED)
        assert len(received) == 1

    def test_once_removes_itself(self, bus):
        bus.once("task.done", lambda e: None)
        assert len(bus._subscriptions) == 1
        bus.emit("task.done")
        assert len(bus._subscriptions) == 0


# ─── Error Handling ───────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_handler_error_doesnt_crash_bus(self, bus):
        def bad_handler(event):
            raise ValueError("boom")

        bus.on(TASK_ASSIGNED, bad_handler)
        # Should not raise
        bus.emit(TASK_ASSIGNED, {"task_id": "t1"})

    def test_handler_error_tracked(self, bus):
        def bad_handler(event):
            raise RuntimeError("fail")

        sub = bus.on(TASK_ASSIGNED, bad_handler, source="broken")
        bus.emit(TASK_ASSIGNED)
        assert sub.errors == 1
        assert bus._total_errors == 1

    def test_handler_disabled_after_threshold(self, bus):
        """Handler removed after error_threshold (3) errors."""

        def bad_handler(event):
            raise RuntimeError("fail")

        bus.on(TASK_ASSIGNED, bad_handler, source="fragile")
        initial_subs = len(bus._subscriptions)

        for _ in range(3):
            bus.emit(TASK_ASSIGNED)

        assert len(bus._subscriptions) == initial_subs - 1

    def test_other_handlers_still_work_after_one_fails(self, bus):
        received = []

        def bad_handler(event):
            raise RuntimeError("fail")

        def good_handler(event):
            received.append(event)

        bus.on(TASK_ASSIGNED, bad_handler, source="bad")
        bus.on(TASK_ASSIGNED, good_handler, source="good")

        bus.emit(TASK_ASSIGNED, {"task_id": "t1"})
        assert len(received) == 1


# ─── Event History ────────────────────────────────────────────────────────────


class TestEventHistory:
    def test_events_recorded_in_history(self, bus):
        bus.emit("task.a")
        bus.emit("task.b")
        bus.emit("task.c")
        history = bus.get_history()
        assert len(history) == 3
        assert history[0]["type"] == "task.a"

    def test_history_limit(self, bus):
        history = bus.get_history(limit=2)
        assert len(history) <= 2

    def test_history_filter_by_type(self, bus):
        bus.emit("task.assigned")
        bus.emit("agent.error")
        bus.emit("task.completed")
        history = bus.get_history(event_type="task.*")
        assert len(history) == 2

    def test_history_filter_by_correlation(self, bus):
        bus.emit("task.a", correlation_id="trace-1")
        bus.emit("task.b", correlation_id="trace-2")
        bus.emit("task.c", correlation_id="trace-1")
        history = bus.get_history(correlation_id="trace-1")
        assert len(history) == 2

    def test_clear_history(self, bus):
        bus.emit("task.a")
        bus.clear_history()
        assert len(bus.get_history()) == 0

    def test_history_max_size(self):
        bus = EventBus(history_size=5)
        for i in range(10):
            bus.emit(f"event.{i}")
        assert len(bus.get_history(limit=100)) == 5


# ─── Metrics ──────────────────────────────────────────────────────────────────


class TestMetrics:
    def test_total_events_counted(self, bus):
        bus.emit("a")
        bus.emit("b")
        bus.emit("c")
        status = bus.get_status()
        assert status["total_events"] == 3

    def test_deliveries_counted(self, bus):
        bus.on("task.*", lambda e: None)
        bus.emit("task.assigned")
        bus.emit("task.completed")
        status = bus.get_status()
        assert status["total_deliveries"] == 2

    def test_events_by_type_tracked(self, bus):
        bus.emit("task.assigned")
        bus.emit("task.assigned")
        bus.emit("task.completed")
        status = bus.get_status()
        assert status["top_events"]["task.assigned"] == 2
        assert status["top_events"]["task.completed"] == 1

    def test_subscription_details(self, bus):
        bus.on("task.*", lambda e: None, source="coordinator")
        bus.on("agent.*", lambda e: None, source="lifecycle")
        status = bus.get_status()
        assert status["subscriptions"] == 2
        assert len(status["subscription_details"]) == 2
        assert status["subscription_details"][0]["source"] == "coordinator"

    def test_reset_metrics(self, bus):
        bus.on("task.*", lambda e: None)
        bus.emit("task.a")
        bus.reset_metrics()
        status = bus.get_status()
        assert status["total_events"] == 0
        assert status["total_deliveries"] == 0


# ─── Component Wiring ─────────────────────────────────────────────────────────


class TestComponentWiring:
    def test_wire_xmtp_bridge(self, bus):
        bridge = MagicMock()
        subs = bus.wire_xmtp_bridge(bridge)
        assert len(subs) == 3

        # Emit task assigned
        bus.emit(TASK_ASSIGNED, {
            "task_id": "t1",
            "worker_wallet": "0xW",
            "task_data": {"title": "Test", "bounty_usdc": 5},
        })
        bridge.notify_task_assigned.assert_called_once()

        # Emit payment confirmed
        bus.emit(PAYMENT_CONFIRMED, {
            "worker_wallet": "0xW",
            "task_id": "t1",
            "amount": 5.0,
            "chain": "base",
            "tx_hash": "0xABC",
        })
        bridge.notify_payment_confirmed.assert_called_once()

        # Emit reputation updated
        bus.emit(REPUTATION_UPDATED, {
            "worker_wallet": "0xW",
            "task_id": "t1",
            "score": 80,
            "new_average": 4.2,
            "total_ratings": 10,
        })
        bridge.notify_reputation_update.assert_called_once()

    def test_wire_xmtp_bridge_error_isolation(self, bus):
        bridge = MagicMock()
        bridge.notify_task_assigned.side_effect = Exception("XMTP down")
        bus.wire_xmtp_bridge(bridge)

        # Should not raise
        bus.emit(TASK_ASSIGNED, {
            "task_id": "t1",
            "worker_wallet": "0xW",
            "task_data": {},
        })

    def test_wire_analytics(self, bus):
        events = []
        bus.wire_analytics(lambda e: events.append(e))
        bus.emit("task.assigned")
        bus.emit("agent.error")
        assert len(events) == 2


# ─── Event Constants ──────────────────────────────────────────────────────────


class TestEventConstants:
    def test_task_events_prefixed(self):
        assert TASK_ASSIGNED.startswith("task.")
        assert TASK_COMPLETED.startswith("task.")
        assert TASK_FAILED.startswith("task.")
        assert TASK_EXPIRED.startswith("task.")

    def test_agent_events_prefixed(self):
        assert AGENT_REGISTERED.startswith("agent.")
        assert AGENT_ACTIVATED.startswith("agent.")
        assert AGENT_ERROR.startswith("agent.")

    def test_worker_events_prefixed(self):
        assert WORKER_REGISTERED.startswith("worker.")
        assert WORKER_APPLIED.startswith("worker.")

    def test_swarm_events_prefixed(self):
        assert SWARM_CYCLE_START.startswith("swarm.")
        assert SWARM_CYCLE_END.startswith("swarm.")


# ─── Event Dataclass ─────────────────────────────────────────────────────────


class TestEventDataclass:
    def test_to_dict(self):
        event = Event(
            type="task.assigned",
            data={"task_id": "t1"},
            source="coordinator",
            correlation_id="trace-1",
        )
        d = event.to_dict()
        assert d["type"] == "task.assigned"
        assert d["data"]["task_id"] == "t1"
        assert d["source"] == "coordinator"
        assert d["correlation_id"] == "trace-1"
        assert "timestamp" in d

    def test_defaults(self):
        event = Event(type="test")
        assert event.data == {}
        assert event.source == ""
        assert event.correlation_id is None
        assert event.timestamp is not None
