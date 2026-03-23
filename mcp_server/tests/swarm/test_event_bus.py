"""
Tests for EventBus — Unified pub/sub event system for the KK V2 Swarm.

Covers:
- Subscription (exact, wildcard, category)
- Emission and delivery
- Handler error isolation
- Error threshold auto-disable
- Once (single-fire) subscriptions
- Unsubscription
- Event history and filtering
- Metrics tracking
- Component wiring (XMTP, analytics)
- Status reporting
- Edge cases (no handlers, empty patterns)
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from mcp_server.swarm.event_bus import (
    EventBus,
    Event,
    Subscription,
    # Event type constants
    TASK_ASSIGNED,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_EXPIRED,
    AGENT_REGISTERED,
    AGENT_DEGRADED,
    WORKER_APPLIED,
    SWARM_CYCLE_START,
    SWARM_CYCLE_END,
    PAYMENT_CONFIRMED,
    REPUTATION_UPDATED,
    NOTIFICATION_SENT,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def bus():
    """Fresh EventBus."""
    return EventBus()


@pytest.fixture
def recording_bus():
    """EventBus with a recording handler attached."""
    bus = EventBus()
    recorded = []
    bus.on("*", lambda e: recorded.append(e), source="recorder")
    return bus, recorded


# ─── Subscription ─────────────────────────────────────────────────────────────


class TestSubscription:
    def test_subscribe_exact(self, bus):
        handler = MagicMock()
        sub = bus.on(TASK_ASSIGNED, handler)
        assert isinstance(sub, Subscription)
        assert sub.pattern == TASK_ASSIGNED
        assert sub.call_count == 0

    def test_subscribe_wildcard(self, bus):
        handler = MagicMock()
        sub = bus.on("task.*", handler)
        bus.emit(TASK_ASSIGNED, {"task_id": "t1"})
        bus.emit(TASK_COMPLETED, {"task_id": "t2"})
        assert handler.call_count == 2

    def test_subscribe_star_all(self, bus):
        handler = MagicMock()
        bus.on("*", handler)
        bus.emit(TASK_ASSIGNED)
        bus.emit(AGENT_REGISTERED)
        bus.emit(WORKER_APPLIED)
        assert handler.call_count == 3

    def test_subscribe_with_source(self, bus):
        handler = MagicMock()
        sub = bus.on("task.*", handler, source="my_component")
        assert sub.source == "my_component"

    def test_subscribe_suffix_wildcard(self, bus):
        handler = MagicMock()
        bus.on("*.completed", handler)
        bus.emit(TASK_COMPLETED)
        assert handler.call_count == 1

    def test_unsubscribe(self, bus):
        handler = MagicMock()
        sub = bus.on(TASK_ASSIGNED, handler)
        removed = bus.off(sub)
        assert removed is True
        bus.emit(TASK_ASSIGNED)
        handler.assert_not_called()

    def test_unsubscribe_nonexistent(self, bus):
        fake = Subscription(pattern="x", handler=lambda e: None)
        removed = bus.off(fake)
        assert removed is False


# ─── Emission ─────────────────────────────────────────────────────────────────


class TestEmission:
    def test_emit_returns_event(self, bus):
        event = bus.emit(TASK_ASSIGNED, {"task_id": "t1"})
        assert isinstance(event, Event)
        assert event.type == TASK_ASSIGNED
        assert event.data["task_id"] == "t1"

    def test_emit_with_source(self, bus):
        event = bus.emit(TASK_ASSIGNED, source="coordinator")
        assert event.source == "coordinator"

    def test_emit_with_correlation_id(self, bus):
        event = bus.emit(TASK_ASSIGNED, correlation_id="corr-123")
        assert event.correlation_id == "corr-123"

    def test_emit_no_data(self, bus):
        event = bus.emit(SWARM_CYCLE_START)
        assert event.data == {}

    def test_emit_no_handlers(self, bus):
        """Emitting with no handlers should not raise."""
        event = bus.emit("nonexistent.event", {"data": "test"})
        assert event.type == "nonexistent.event"

    def test_emit_delivers_to_matching_only(self, bus):
        task_handler = MagicMock()
        agent_handler = MagicMock()
        bus.on("task.*", task_handler)
        bus.on("agent.*", agent_handler)

        bus.emit(TASK_ASSIGNED)
        task_handler.assert_called_once()
        agent_handler.assert_not_called()

    def test_emit_delivers_to_multiple_handlers(self, bus):
        handler1 = MagicMock()
        handler2 = MagicMock()
        bus.on(TASK_ASSIGNED, handler1)
        bus.on(TASK_ASSIGNED, handler2)

        bus.emit(TASK_ASSIGNED)
        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_handler_receives_event_data(self, bus):
        received = []
        bus.on(TASK_ASSIGNED, lambda e: received.append(e.data))
        bus.emit(TASK_ASSIGNED, {"task_id": "t1", "agent_id": 42})
        assert received[0]["task_id"] == "t1"
        assert received[0]["agent_id"] == 42


# ─── Once (Single-Fire) ──────────────────────────────────────────────────────


class TestOnce:
    def test_once_fires_once(self, bus):
        handler = MagicMock()
        bus.once(TASK_COMPLETED, handler)

        bus.emit(TASK_COMPLETED, {"task_id": "t1"})
        bus.emit(TASK_COMPLETED, {"task_id": "t2"})

        handler.assert_called_once()

    def test_once_returns_subscription(self, bus):
        sub = bus.once(TASK_COMPLETED, lambda e: None)
        assert isinstance(sub, Subscription)

    def test_once_with_source(self, bus):
        sub = bus.once(TASK_COMPLETED, lambda e: None, source="test")
        assert sub.source == "test"


# ─── Error Handling ───────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_handler_error_does_not_crash(self, bus):
        def bad_handler(e):
            raise ValueError("Handler crashed!")

        bus.on(TASK_ASSIGNED, bad_handler)
        # Should not raise
        event = bus.emit(TASK_ASSIGNED)
        assert event.type == TASK_ASSIGNED

    def test_handler_error_increments_count(self, bus):
        def bad_handler(e):
            raise RuntimeError("fail")

        sub = bus.on(TASK_ASSIGNED, bad_handler)
        bus.emit(TASK_ASSIGNED)
        assert sub.errors == 1

    def test_handler_error_counted_in_metrics(self, bus):
        def bad_handler(e):
            raise RuntimeError("fail")

        bus.on(TASK_ASSIGNED, bad_handler)
        bus.emit(TASK_ASSIGNED)
        status = bus.get_status()
        assert status["total_errors"] == 1

    def test_error_threshold_disables_handler(self):
        bus = EventBus(error_threshold=3)

        def bad_handler(e):
            raise RuntimeError("fail")

        bus.on(TASK_ASSIGNED, bad_handler)

        # Emit 3 times to hit threshold
        for _ in range(3):
            bus.emit(TASK_ASSIGNED)

        # Handler should be auto-removed
        assert len(bus._subscriptions) == 0

    def test_good_handlers_survive_bad_handler(self, bus):
        good_handler = MagicMock()

        def bad_handler(e):
            raise RuntimeError("fail")

        bus.on(TASK_ASSIGNED, bad_handler)
        bus.on(TASK_ASSIGNED, good_handler)

        bus.emit(TASK_ASSIGNED)
        good_handler.assert_called_once()


# ─── Event History ────────────────────────────────────────────────────────────


class TestHistory:
    def test_history_records_events(self, bus):
        bus.emit(TASK_ASSIGNED, {"task_id": "t1"})
        bus.emit(TASK_COMPLETED, {"task_id": "t2"})
        history = bus.get_history()
        assert len(history) == 2

    def test_history_filtered_by_type(self, bus):
        bus.emit(TASK_ASSIGNED)
        bus.emit(TASK_COMPLETED)
        bus.emit(TASK_ASSIGNED)
        history = bus.get_history(event_type=TASK_ASSIGNED)
        assert len(history) == 2

    def test_history_filtered_by_pattern(self, bus):
        bus.emit(TASK_ASSIGNED)
        bus.emit(TASK_COMPLETED)
        bus.emit(AGENT_REGISTERED)
        history = bus.get_history(event_type="task.*")
        assert len(history) == 2

    def test_history_filtered_by_correlation(self, bus):
        bus.emit(TASK_ASSIGNED, correlation_id="flow-1")
        bus.emit(TASK_COMPLETED, correlation_id="flow-1")
        bus.emit(TASK_ASSIGNED, correlation_id="flow-2")
        history = bus.get_history(correlation_id="flow-1")
        assert len(history) == 2

    def test_history_limited(self, bus):
        for i in range(10):
            bus.emit(TASK_ASSIGNED, {"i": i})
        history = bus.get_history(limit=3)
        assert len(history) == 3

    def test_history_max_size(self):
        bus = EventBus(history_size=5)
        for i in range(10):
            bus.emit(TASK_ASSIGNED, {"i": i})
        history = bus.get_history()
        assert len(history) == 5

    def test_clear_history(self, bus):
        bus.emit(TASK_ASSIGNED)
        bus.clear_history()
        history = bus.get_history()
        assert len(history) == 0

    def test_history_event_format(self, bus):
        bus.emit(TASK_ASSIGNED, {"task_id": "t1"}, source="coord", correlation_id="c1")
        entry = bus.get_history()[0]
        assert entry["type"] == TASK_ASSIGNED
        assert entry["data"]["task_id"] == "t1"
        assert entry["source"] == "coord"
        assert entry["correlation_id"] == "c1"
        assert "timestamp" in entry


# ─── Pattern Matching ─────────────────────────────────────────────────────────


class TestPatternMatching:
    def test_exact_match(self):
        assert EventBus._matches("task.assigned", "task.assigned") is True
        assert EventBus._matches("task.assigned", "task.completed") is False

    def test_star_matches_all(self):
        assert EventBus._matches("*", "task.assigned") is True
        assert EventBus._matches("*", "anything.at.all") is True

    def test_prefix_wildcard(self):
        assert EventBus._matches("task.*", "task.assigned") is True
        assert EventBus._matches("task.*", "task.completed") is True
        assert EventBus._matches("task.*", "agent.registered") is False

    def test_suffix_wildcard(self):
        assert EventBus._matches("*.completed", "task.completed") is True
        assert EventBus._matches("*.completed", "agent.completed") is True
        assert EventBus._matches("*.completed", "task.assigned") is False


# ─── Metrics ──────────────────────────────────────────────────────────────────


class TestMetrics:
    def test_total_events_counted(self, bus):
        bus.emit(TASK_ASSIGNED)
        bus.emit(TASK_COMPLETED)
        status = bus.get_status()
        assert status["total_events"] == 2

    def test_deliveries_counted(self, bus):
        handler = MagicMock()
        bus.on(TASK_ASSIGNED, handler)
        bus.emit(TASK_ASSIGNED)
        status = bus.get_status()
        assert status["total_deliveries"] == 1

    def test_events_by_type(self, bus):
        bus.emit(TASK_ASSIGNED)
        bus.emit(TASK_ASSIGNED)
        bus.emit(TASK_COMPLETED)
        status = bus.get_status()
        assert status["top_events"][TASK_ASSIGNED] == 2
        assert status["top_events"][TASK_COMPLETED] == 1

    def test_subscription_count(self, bus):
        bus.on("task.*", lambda e: None)
        bus.on("agent.*", lambda e: None)
        status = bus.get_status()
        assert status["subscriptions"] == 2

    def test_subscription_details(self, bus):
        bus.on("task.*", lambda e: None, source="monitor")
        bus.emit(TASK_ASSIGNED)
        status = bus.get_status()
        details = status["subscription_details"]
        assert len(details) == 1
        assert details[0]["pattern"] == "task.*"
        assert details[0]["source"] == "monitor"
        assert details[0]["calls"] == 1

    def test_reset_metrics(self, bus):
        handler = MagicMock()
        bus.on(TASK_ASSIGNED, handler)
        bus.emit(TASK_ASSIGNED)
        bus.reset_metrics()
        status = bus.get_status()
        assert status["total_events"] == 0
        assert status["total_deliveries"] == 0
        assert status["top_events"] == {}

    def test_subscription_call_tracking(self, bus):
        handler = MagicMock()
        sub = bus.on(TASK_ASSIGNED, handler)
        assert sub.call_count == 0
        assert sub.last_called is None

        bus.emit(TASK_ASSIGNED)
        assert sub.call_count == 1
        assert sub.last_called is not None


# ─── Component Wiring ─────────────────────────────────────────────────────────


class TestComponentWiring:
    def test_wire_xmtp_bridge(self, bus):
        bridge = MagicMock()
        subs = bus.wire_xmtp_bridge(bridge)
        assert len(subs) == 3  # task_assigned, payment_confirmed, reputation_updated

    def test_xmtp_task_assigned(self, bus):
        bridge = MagicMock()
        bus.wire_xmtp_bridge(bridge)
        bus.emit(
            TASK_ASSIGNED,
            {
                "task_id": "t1",
                "worker_wallet": "0x123",
                "task_data": {"title": "Test"},
            },
        )
        bridge.notify_task_assigned.assert_called_once_with(
            task_id="t1",
            worker_wallet="0x123",
            task_data={"title": "Test"},
        )

    def test_xmtp_payment_confirmed(self, bus):
        bridge = MagicMock()
        bus.wire_xmtp_bridge(bridge)
        bus.emit(
            PAYMENT_CONFIRMED,
            {
                "worker_wallet": "0x123",
                "task_id": "t1",
                "amount": 0.50,
                "chain": "base",
                "tx_hash": "0xabc",
            },
        )
        bridge.notify_payment_confirmed.assert_called_once()

    def test_xmtp_reputation_updated(self, bus):
        bridge = MagicMock()
        bus.wire_xmtp_bridge(bridge)
        bus.emit(
            REPUTATION_UPDATED,
            {
                "worker_wallet": "0x123",
                "task_id": "t1",
                "score": 5,
                "new_average": 4.5,
                "total_ratings": 10,
            },
        )
        bridge.notify_reputation_update.assert_called_once()

    def test_xmtp_bridge_error_resilience(self, bus):
        bridge = MagicMock()
        bridge.notify_task_assigned.side_effect = Exception("XMTP down")
        bus.wire_xmtp_bridge(bridge)
        # Should not raise
        bus.emit(TASK_ASSIGNED, {"task_id": "t1"})

    def test_wire_analytics(self, bus):
        events = []
        sub = bus.wire_analytics(lambda e: events.append(e))
        bus.emit(TASK_ASSIGNED)
        bus.emit(AGENT_REGISTERED)
        assert len(events) == 2
        assert sub.source == "analytics"


# ─── Event Dataclass ──────────────────────────────────────────────────────────


class TestEvent:
    def test_event_to_dict(self):
        event = Event(
            type=TASK_ASSIGNED,
            data={"task_id": "t1"},
            source="coordinator",
            correlation_id="flow-1",
        )
        d = event.to_dict()
        assert d["type"] == TASK_ASSIGNED
        assert d["data"]["task_id"] == "t1"
        assert d["source"] == "coordinator"
        assert d["correlation_id"] == "flow-1"
        assert "timestamp" in d

    def test_event_defaults(self):
        event = Event(type="test")
        assert event.data == {}
        assert event.source == ""
        assert event.correlation_id is None
        assert event.timestamp is not None


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_emit_empty_type(self, bus):
        handler = MagicMock()
        bus.on("", handler)
        bus.emit("")
        handler.assert_called_once()

    def test_many_subscriptions(self, bus):
        handlers = [MagicMock() for _ in range(100)]
        for h in handlers:
            bus.on(TASK_ASSIGNED, h)
        bus.emit(TASK_ASSIGNED)
        for h in handlers:
            h.assert_called_once()

    def test_emit_during_handler(self, bus):
        """Handler that emits another event."""
        inner_calls = []

        def outer_handler(e):
            if e.data.get("depth", 0) == 0:
                bus.emit("inner.event", {"depth": 1})

        bus.on(TASK_ASSIGNED, outer_handler)
        bus.on("inner.event", lambda e: inner_calls.append(e))

        bus.emit(TASK_ASSIGNED, {"depth": 0})
        assert len(inner_calls) == 1

    def test_subscription_created_at(self):
        sub = Subscription(pattern="test", handler=lambda e: None)
        assert sub.created_at is not None
        assert isinstance(sub.created_at, datetime)
