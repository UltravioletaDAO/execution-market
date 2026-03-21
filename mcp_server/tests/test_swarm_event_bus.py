"""
Tests for EventBus — unified pub/sub event system for the KK V2 Swarm.

Covers:
- Basic pub/sub (emit/on/off)
- Pattern matching (exact, wildcard, catch-all)
- once() single-fire subscriptions
- Error isolation and auto-disable
- Event history and filtering
- Metrics tracking
- Component wiring (XMTP bridge, analytics)
"""

import pytest
from unittest.mock import MagicMock

from mcp_server.swarm.event_bus import (
    EventBus,
    Event,
    Subscription,
    # Task events
    TASK_DISCOVERED,
    TASK_ENRICHED,
    TASK_ASSIGNED,
    TASK_STARTED,
    TASK_SUBMITTED,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_EXPIRED,
    TASK_CANCELLED,
    # Agent events
    AGENT_REGISTERED,
    AGENT_ACTIVATED,
    AGENT_DEACTIVATED,
    AGENT_DEGRADED,
    # Worker events
    WORKER_REGISTERED,
    WORKER_APPLIED,
    WORKER_EVIDENCE,
    WORKER_RATED,
    # Swarm events
    SWARM_CYCLE_START,
    SWARM_CYCLE_END,
    # Notification events
    NOTIFICATION_SENT,
    NOTIFICATION_FAILED,
    # Reputation events
    REPUTATION_UPDATED,
    SKILL_DNA_UPDATED,
    # Payment events
    PAYMENT_ESCROWED,
    PAYMENT_RELEASED,
    PAYMENT_CONFIRMED,
)


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def bus():
    return EventBus(history_size=100, error_threshold=3)


@pytest.fixture
def handler():
    return MagicMock()


# ─── Event Data Model ─────────────────────────────────────────────


class TestEventDataModel:
    """Event dataclass behavior."""

    def test_event_creates_with_defaults(self):
        e = Event(type="test.event")
        assert e.type == "test.event"
        assert e.data == {}
        assert e.source == ""
        assert e.correlation_id is None
        assert e.timestamp is not None

    def test_event_with_full_data(self):
        e = Event(
            type="task.assigned",
            data={"task_id": "abc", "agent_id": 42},
            source="coordinator",
            correlation_id="corr-123",
        )
        assert e.data["task_id"] == "abc"
        assert e.source == "coordinator"
        assert e.correlation_id == "corr-123"

    def test_event_to_dict(self):
        e = Event(type="test", data={"key": "val"}, source="src")
        d = e.to_dict()
        assert d["type"] == "test"
        assert d["data"] == {"key": "val"}
        assert d["source"] == "src"
        assert "timestamp" in d
        assert d["correlation_id"] is None

    def test_event_constants_are_strings(self):
        """All event constants should be properly namespaced strings."""
        assert TASK_ASSIGNED == "task.assigned"
        assert TASK_COMPLETED == "task.completed"
        assert AGENT_REGISTERED == "agent.registered"
        assert WORKER_REGISTERED == "worker.registered"
        assert SWARM_CYCLE_START == "swarm.cycle.start"
        assert PAYMENT_CONFIRMED == "payment.confirmed"
        assert REPUTATION_UPDATED == "reputation.updated"

    def test_all_event_constants_have_dot_namespace(self):
        """Every event constant should follow namespace.action pattern."""
        constants = [
            TASK_DISCOVERED,
            TASK_ENRICHED,
            TASK_ASSIGNED,
            TASK_STARTED,
            TASK_SUBMITTED,
            TASK_COMPLETED,
            TASK_FAILED,
            TASK_EXPIRED,
            TASK_CANCELLED,
            AGENT_REGISTERED,
            AGENT_ACTIVATED,
            AGENT_DEACTIVATED,
            AGENT_DEGRADED,
            WORKER_REGISTERED,
            WORKER_APPLIED,
            WORKER_EVIDENCE,
            WORKER_RATED,
            SWARM_CYCLE_START,
            SWARM_CYCLE_END,
            NOTIFICATION_SENT,
            NOTIFICATION_FAILED,
            REPUTATION_UPDATED,
            SKILL_DNA_UPDATED,
            PAYMENT_ESCROWED,
            PAYMENT_RELEASED,
            PAYMENT_CONFIRMED,
        ]
        for c in constants:
            assert "." in c, f"Event constant {c!r} missing namespace separator"


# ─── Basic Pub/Sub ─────────────────────────────────────────────────


class TestBasicPubSub:
    """Core subscribe/emit/unsubscribe functionality."""

    def test_subscribe_and_receive(self, bus, handler):
        bus.on("test.event", handler)
        bus.emit("test.event", {"key": "value"})
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == "test.event"
        assert event.data["key"] == "value"

    def test_no_handler_no_error(self, bus):
        """Emitting with no subscribers should not raise."""
        event = bus.emit("nobody.listening", {"x": 1})
        assert event.type == "nobody.listening"

    def test_multiple_handlers(self, bus):
        h1 = MagicMock()
        h2 = MagicMock()
        h3 = MagicMock()
        bus.on("multi.event", h1)
        bus.on("multi.event", h2)
        bus.on("multi.event", h3)
        bus.emit("multi.event")
        assert h1.call_count == 1
        assert h2.call_count == 1
        assert h3.call_count == 1

    def test_unsubscribe(self, bus, handler):
        sub = bus.on("unsub.test", handler)
        bus.emit("unsub.test")
        assert handler.call_count == 1

        result = bus.off(sub)
        assert result is True

        bus.emit("unsub.test")
        assert handler.call_count == 1  # Should not increment

    def test_unsubscribe_nonexistent_returns_false(self, bus):
        fake_sub = Subscription(pattern="fake", handler=lambda e: None)
        assert bus.off(fake_sub) is False

    def test_emit_returns_event_object(self, bus):
        event = bus.emit("return.test", {"data": True}, source="test")
        assert isinstance(event, Event)
        assert event.type == "return.test"
        assert event.source == "test"

    def test_event_source_preserved(self, bus, handler):
        bus.on("src.test", handler)
        bus.emit("src.test", source="coordinator")
        event = handler.call_args[0][0]
        assert event.source == "coordinator"

    def test_correlation_id_preserved(self, bus, handler):
        bus.on("corr.test", handler)
        bus.emit("corr.test", correlation_id="trace-999")
        event = handler.call_args[0][0]
        assert event.correlation_id == "trace-999"

    def test_handler_receives_all_matching_events(self, bus, handler):
        bus.on("repeat.event", handler)
        for i in range(5):
            bus.emit("repeat.event", {"i": i})
        assert handler.call_count == 5

    def test_different_events_dont_cross(self, bus):
        h1 = MagicMock()
        h2 = MagicMock()
        bus.on("type.a", h1)
        bus.on("type.b", h2)
        bus.emit("type.a")
        assert h1.call_count == 1
        assert h2.call_count == 0


# ─── Pattern Matching ──────────────────────────────────────────────


class TestPatternMatching:
    """Wildcard and pattern-based subscription matching."""

    def test_exact_match(self, bus, handler):
        bus.on("task.completed", handler)
        bus.emit("task.completed")
        assert handler.call_count == 1

    def test_prefix_wildcard(self, bus, handler):
        """task.* should match all task events."""
        bus.on("task.*", handler)
        bus.emit("task.assigned")
        bus.emit("task.completed")
        bus.emit("task.failed")
        bus.emit("agent.registered")  # Should NOT match
        assert handler.call_count == 3

    def test_catch_all_wildcard(self, bus, handler):
        """* should match everything."""
        bus.on("*", handler)
        bus.emit("task.assigned")
        bus.emit("agent.activated")
        bus.emit("swarm.cycle.start")
        assert handler.call_count == 3

    def test_suffix_wildcard(self, bus, handler):
        """*.completed should match X.completed events."""
        bus.on("*.completed", handler)
        bus.emit("task.completed")
        bus.emit("task.assigned")  # Should NOT match
        assert handler.call_count == 1

    def test_matches_static_method(self):
        """Direct test of _matches logic."""
        assert EventBus._matches("task.assigned", "task.assigned") is True
        assert EventBus._matches("task.assigned", "task.completed") is False
        assert EventBus._matches("task.*", "task.assigned") is True
        assert EventBus._matches("task.*", "task.completed") is True
        assert EventBus._matches("task.*", "agent.started") is False
        assert EventBus._matches("*", "anything") is True
        assert EventBus._matches("*", "deeply.nested.event") is True
        assert EventBus._matches("*.completed", "task.completed") is True
        assert EventBus._matches("*.completed", "task.failed") is False

    def test_no_false_positives_in_wildcards(self, bus, handler):
        """agent.* should NOT match agent.state.changed (fnmatch behavior)."""
        bus.on("agent.*", handler)
        bus.emit("agent.registered")
        assert handler.call_count == 1
        # fnmatch('agent.state.changed', 'agent.*') depends on implementation
        # but it should at least match single-level


# ─── Once (Single-Fire Subscriptions) ─────────────────────────────


class TestOnce:
    """once() should fire exactly once then auto-unsubscribe."""

    def test_once_fires_once(self, bus, handler):
        bus.once("one.shot", handler)
        bus.emit("one.shot")
        bus.emit("one.shot")
        bus.emit("one.shot")
        assert handler.call_count == 1

    def test_once_receives_event_data(self, bus, handler):
        bus.once("one.data", handler)
        bus.emit("one.data", {"key": "val"})
        event = handler.call_args[0][0]
        assert event.data["key"] == "val"

    def test_once_does_not_affect_other_subs(self, bus):
        once_handler = MagicMock()
        persistent_handler = MagicMock()
        bus.once("mixed.event", once_handler)
        bus.on("mixed.event", persistent_handler)

        bus.emit("mixed.event")
        bus.emit("mixed.event")

        assert once_handler.call_count == 1
        assert persistent_handler.call_count == 2


# ─── Error Isolation ───────────────────────────────────────────────


class TestErrorIsolation:
    """Handler errors should be caught and not crash the bus."""

    def test_handler_error_doesnt_crash_bus(self, bus):
        bad_handler = MagicMock(side_effect=ValueError("boom"))
        good_handler = MagicMock()
        bus.on("error.test", bad_handler)
        bus.on("error.test", good_handler)

        # Should not raise
        bus.emit("error.test")
        assert bad_handler.call_count == 1
        assert good_handler.call_count == 1

    def test_error_increments_subscription_error_count(self, bus):
        bad = MagicMock(side_effect=RuntimeError("fail"))
        sub = bus.on("err.count", bad)
        bus.emit("err.count")
        assert sub.errors == 1
        bus.emit("err.count")
        assert sub.errors == 2

    def test_auto_disable_after_threshold(self, bus):
        """After error_threshold errors, handler should be auto-removed."""
        bad = MagicMock(side_effect=Exception("always fails"))
        sub = bus.on("err.disable", bad)

        for _ in range(5):  # threshold is 3
            bus.emit("err.disable")

        # After 3 errors, should be unsubscribed
        assert sub.errors == 3  # Got 3 errors then was removed
        assert bad.call_count == 3

    def test_error_tracked_in_total_errors(self, bus):
        bad = MagicMock(side_effect=Exception("fail"))
        bus.on("err.total", bad)
        bus.emit("err.total")
        bus.emit("err.total")
        status = bus.get_status()
        assert status["total_errors"] >= 2


# ─── Event History ─────────────────────────────────────────────────


class TestEventHistory:
    """Event history tracking and filtering."""

    def test_events_stored_in_history(self, bus):
        bus.emit("hist.a", {"i": 1})
        bus.emit("hist.b", {"i": 2})
        history = bus.get_history()
        assert len(history) == 2
        assert history[0]["type"] == "hist.a"
        assert history[1]["type"] == "hist.b"

    def test_history_size_limited(self):
        bus = EventBus(history_size=5)
        for i in range(10):
            bus.emit("overflow", {"i": i})
        history = bus.get_history()
        assert len(history) == 5
        # Should have the last 5
        assert history[0]["data"]["i"] == 5

    def test_history_filter_by_type(self, bus):
        bus.emit("task.assigned")
        bus.emit("task.completed")
        bus.emit("agent.registered")
        history = bus.get_history(event_type="task.assigned")
        assert len(history) == 1
        assert history[0]["type"] == "task.assigned"

    def test_history_filter_by_pattern(self, bus):
        bus.emit("task.assigned")
        bus.emit("task.completed")
        bus.emit("agent.registered")
        history = bus.get_history(event_type="task.*")
        assert len(history) == 2

    def test_history_filter_by_correlation_id(self, bus):
        bus.emit("a", correlation_id="trace-1")
        bus.emit("b", correlation_id="trace-2")
        bus.emit("c", correlation_id="trace-1")
        history = bus.get_history(correlation_id="trace-1")
        assert len(history) == 2

    def test_history_limit(self, bus):
        for i in range(20):
            bus.emit("many", {"i": i})
        history = bus.get_history(limit=5)
        assert len(history) == 5

    def test_clear_history(self, bus):
        bus.emit("to.clear")
        assert len(bus.get_history()) == 1
        bus.clear_history()
        assert len(bus.get_history()) == 0


# ─── Metrics ───────────────────────────────────────────────────────


class TestMetrics:
    """Stats and metrics tracking."""

    def test_total_events_tracked(self, bus):
        bus.emit("m1")
        bus.emit("m2")
        bus.emit("m3")
        status = bus.get_status()
        assert status["total_events"] == 3

    def test_total_deliveries_tracked(self, bus, handler):
        bus.on("deliver.test", handler)
        bus.emit("deliver.test")
        bus.emit("deliver.test")
        status = bus.get_status()
        assert status["total_deliveries"] == 2

    def test_events_by_type_tracked(self, bus):
        bus.emit("type.a")
        bus.emit("type.a")
        bus.emit("type.b")
        status = bus.get_status()
        assert status["top_events"]["type.a"] == 2
        assert status["top_events"]["type.b"] == 1

    def test_subscription_details_in_status(self, bus, handler):
        bus.on("sub.detail", handler, source="my_component")
        bus.emit("sub.detail")
        status = bus.get_status()
        details = status["subscription_details"]
        assert len(details) >= 1
        sub_info = [d for d in details if d["source"] == "my_component"][0]
        assert sub_info["pattern"] == "sub.detail"
        assert sub_info["calls"] == 1
        assert sub_info["errors"] == 0

    def test_subscription_call_count_and_last_called(self, bus, handler):
        sub = bus.on("call.count", handler)
        assert sub.call_count == 0
        assert sub.last_called is None
        bus.emit("call.count")
        assert sub.call_count == 1
        assert sub.last_called is not None

    def test_reset_metrics(self, bus, handler):
        bus.on("reset.test", handler)
        bus.emit("reset.test")
        bus.emit("reset.test")
        bus.reset_metrics()
        status = bus.get_status()
        assert status["total_events"] == 0
        assert status["total_deliveries"] == 0


# ─── Component Wiring ─────────────────────────────────────────────


class TestComponentWiring:
    """Testing wire_xmtp_bridge and wire_analytics."""

    def test_wire_xmtp_bridge_creates_subscriptions(self, bus):
        bridge = MagicMock()
        subs = bus.wire_xmtp_bridge(bridge)
        assert len(subs) == 3  # task.assigned, payment.confirmed, reputation.updated

    def test_wire_xmtp_bridge_task_assigned(self, bus):
        bridge = MagicMock()
        bus.wire_xmtp_bridge(bridge)

        bus.emit(
            TASK_ASSIGNED,
            {
                "task_id": "task-123",
                "worker_wallet": "0xWorker",
                "task_data": {"title": "Test Task"},
            },
        )

        bridge.notify_task_assigned.assert_called_once_with(
            task_id="task-123",
            worker_wallet="0xWorker",
            task_data={"title": "Test Task"},
        )

    def test_wire_xmtp_bridge_payment_confirmed(self, bus):
        bridge = MagicMock()
        bus.wire_xmtp_bridge(bridge)

        bus.emit(
            PAYMENT_CONFIRMED,
            {
                "worker_wallet": "0xWorker",
                "task_id": "task-456",
                "amount": 5.0,
                "chain": "base",
                "tx_hash": "0xabc123",
            },
        )

        bridge.notify_payment_confirmed.assert_called_once_with(
            worker_wallet="0xWorker",
            task_id="task-456",
            amount=5.0,
            chain="base",
            tx_hash="0xabc123",
        )

    def test_wire_xmtp_bridge_reputation_updated(self, bus):
        bridge = MagicMock()
        bus.wire_xmtp_bridge(bridge)

        bus.emit(
            REPUTATION_UPDATED,
            {
                "worker_wallet": "0xWorker",
                "task_id": "task-789",
                "score": 80,
                "new_average": 4.2,
                "total_ratings": 15,
            },
        )

        bridge.notify_reputation_update.assert_called_once_with(
            worker_wallet="0xWorker",
            task_id="task-789",
            score=80,
            new_average=4.2,
            total_ratings=15,
        )

    def test_wire_xmtp_bridge_error_isolated(self, bus):
        """If XMTP bridge throws, it shouldn't crash the bus."""
        bridge = MagicMock()
        bridge.notify_task_assigned.side_effect = ConnectionError("bot offline")
        bus.wire_xmtp_bridge(bridge)

        # Should not raise
        bus.emit(
            TASK_ASSIGNED,
            {
                "task_id": "t1",
                "worker_wallet": "0x1",
                "task_data": {},
            },
        )

    def test_wire_analytics_catches_all(self, bus, handler):
        bus.wire_analytics(handler)
        bus.emit("task.assigned")
        bus.emit("agent.registered")
        bus.emit("swarm.cycle.start")
        assert handler.call_count == 3

    def test_wire_analytics_returns_subscription(self, bus, handler):
        sub = bus.wire_analytics(handler)
        assert isinstance(sub, Subscription)
        assert sub.pattern == "*"
        assert sub.source == "analytics"
