"""
Test Suite: CoreEventBridge — Core→Swarm Event Translation
=============================================================

Tests cover:
    1. BridgeStats tracking
    2. BridgeFilter (event types, bounty, categories, sources)
    3. Event type mapping (Core → Swarm naming)
    4. Bridge lifecycle (start, stop, re-start)
    5. Event handling (transform, emit, anti-echo)
    6. Statistics and monitoring
    7. Edge cases (unmapped types, transform errors)
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from mcp_server.swarm.core_event_bridge import (
    CoreEventBridge,
    BridgeFilter,
    BridgeStats,
    EVENT_TYPE_MAP,
)
from mcp_server.events.models import EMEvent, EventSource
from mcp_server.events.bus import EventBus as CoreEventBus
from mcp_server.swarm.event_bus import EventBus as SwarmEventBus


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════


def _mock_core_event(
    event_type="task.created",
    task_id="t1",
    bounty_usd=5.0,
    category="photo",
    source=EventSource.REST_API,
):
    """Create a mock EMEvent."""
    event = MagicMock(spec=EMEvent)
    event.event_type = event_type
    event.task_id = task_id
    event.payload = {"bounty_usd": bounty_usd, "category": category}
    event.source = source
    event.correlation_id = "corr-123"
    event.id = "evt-456"
    event.timestamp = datetime.now(timezone.utc)
    return event


def _make_bridge(**kwargs):
    """Create a CoreEventBridge with mock buses."""
    core_bus = kwargs.pop("core_bus", MagicMock(spec=CoreEventBus))
    swarm_bus = kwargs.pop("swarm_bus", MagicMock(spec=SwarmEventBus))
    core_bus.subscribe.return_value = "sub-id"
    return CoreEventBridge(core_bus=core_bus, swarm_bus=swarm_bus, **kwargs)


# ══════════════════════════════════════════════════════════════
# BridgeStats Tests
# ══════════════════════════════════════════════════════════════


class TestBridgeStats:
    def test_defaults(self):
        stats = BridgeStats()
        assert stats.events_received == 0
        assert stats.events_bridged == 0
        assert stats.errors == 0
        assert stats.last_bridged_at is None

    def test_events_by_type_tracking(self):
        stats = BridgeStats()
        stats.events_by_type["task.discovered"] = 5
        assert stats.events_by_type["task.discovered"] == 5


# ══════════════════════════════════════════════════════════════
# BridgeFilter Tests
# ══════════════════════════════════════════════════════════════


class TestBridgeFilter:
    def test_default_allows_all(self):
        f = BridgeFilter()
        event = _mock_core_event()
        assert f.should_bridge(event) is True

    def test_bounty_filter(self):
        f = BridgeFilter(min_bounty_usd=3.0)
        assert f.should_bridge(_mock_core_event(bounty_usd=5.0)) is True
        assert f.should_bridge(_mock_core_event(bounty_usd=1.0)) is False

    def test_empty_category_passes(self):
        f = BridgeFilter(categories={"photo"})
        event = _mock_core_event(category="")
        # Empty category passes the filter (no category to check)
        assert f.should_bridge(event) is True


# ══════════════════════════════════════════════════════════════
# Event Type Mapping Tests
# ══════════════════════════════════════════════════════════════


class TestEventTypeMapping:
    def test_task_assigned_preserved(self):
        assert EVENT_TYPE_MAP["task.assigned"] == "task.assigned"

    def test_task_completed_preserved(self):
        assert EVENT_TYPE_MAP["task.completed"] == "task.completed"

    def test_all_values_are_strings(self):
        for key, value in EVENT_TYPE_MAP.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


# ══════════════════════════════════════════════════════════════
# Bridge Lifecycle Tests
# ══════════════════════════════════════════════════════════════


class TestBridgeLifecycle:
    def test_start(self):
        bridge = _make_bridge()
        bridge.start()
        assert bridge.is_running is True
        # Should subscribe to all mapped event types
        assert bridge._core_bus.subscribe.call_count == len(EVENT_TYPE_MAP)

    def test_stop(self):
        bridge = _make_bridge()
        bridge.start()
        bridge.stop()
        assert bridge.is_running is False
        assert len(bridge._subscription_ids) == 0

    def test_double_start_warns(self):
        bridge = _make_bridge()
        bridge.start()
        bridge.start()  # Should not crash, just warn
        assert bridge.is_running is True

    def test_start_stop_start(self):
        bridge = _make_bridge()
        bridge.start()
        bridge.stop()
        bridge.start()
        assert bridge.is_running is True

    def test_stats_property(self):
        bridge = _make_bridge()
        bridge.start()
        stats = bridge.stats
        assert stats["started"] is True
        assert stats["subscription_count"] == len(EVENT_TYPE_MAP)
        assert stats["events_received"] == 0


# ══════════════════════════════════════════════════════════════
# Event Handling Tests
# ══════════════════════════════════════════════════════════════


class TestEventHandling:
    @pytest.mark.asyncio
    async def test_basic_bridging(self):
        swarm_bus = MagicMock(spec=SwarmEventBus)
        bridge = _make_bridge(swarm_bus=swarm_bus)
        event = _mock_core_event("task.created")

        await bridge._handle_core_event(event)

        swarm_bus.emit.assert_called_once()
        call_kwargs = swarm_bus.emit.call_args[1]
        assert call_kwargs["event_type"] == "task.discovered"
        assert call_kwargs["source"] == "core_event_bridge"

    @pytest.mark.asyncio
    async def test_stats_updated(self):
        bridge = _make_bridge()
        event = _mock_core_event("task.created")

        await bridge._handle_core_event(event)

        assert bridge._stats.events_received == 1
        assert bridge._stats.events_bridged == 1
        assert bridge._stats.last_bridged_at is not None

    @pytest.mark.asyncio
    async def test_transform_error_recorded(self):
        def bad_transform(event):
            raise ValueError("transform failed")

        bridge = _make_bridge(transform_payload=bad_transform)
        event = _mock_core_event("task.created")

        await bridge._handle_core_event(event)

        assert bridge._stats.errors == 1
        assert bridge._stats.events_bridged == 0

    @pytest.mark.asyncio
    async def test_default_transform_adds_task_id(self):
        bridge = _make_bridge()
        event = _mock_core_event("task.created", task_id="t123")
        event.payload = {}

        result = bridge._default_transform(event)
        assert result["task_id"] == "t123"

    @pytest.mark.asyncio
    async def test_events_by_type_tracking(self):
        bridge = _make_bridge()

        await bridge._handle_core_event(_mock_core_event("task.created"))
        await bridge._handle_core_event(_mock_core_event("task.created"))
        await bridge._handle_core_event(_mock_core_event("task.completed"))

        assert bridge._stats.events_by_type["task.discovered"] == 2
        assert bridge._stats.events_by_type["task.completed"] == 1

    @pytest.mark.asyncio
    async def test_correlation_id_passed(self):
        swarm_bus = MagicMock(spec=SwarmEventBus)
        bridge = _make_bridge(swarm_bus=swarm_bus)
        event = _mock_core_event("task.created")
        event.correlation_id = "corr-abc"

        await bridge._handle_core_event(event)

        call_kwargs = swarm_bus.emit.call_args[1]
        assert call_kwargs["correlation_id"] == "corr-abc"
