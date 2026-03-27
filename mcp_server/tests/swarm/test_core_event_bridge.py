"""
Tests for CoreEventBridge — Core → Swarm event bridging.

Covers:
  1. Event type mapping
  2. BridgeFilter
  3. BridgeStats tracking
  4. CoreEventBridge lifecycle (start/stop)
  5. Event transformation
  6. Anti-echo filtering
  7. Error handling
  8. Stats reporting
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from mcp_server.swarm.core_event_bridge import (
    CoreEventBridge,
    BridgeFilter,
    BridgeStats,
    EVENT_TYPE_MAP,
)


# ─── Mocks ────────────────────────────────────────────────────


class MockEMEvent:
    """Minimal EMEvent mock."""

    def __init__(
        self,
        event_type="task.created",
        task_id="t1",
        payload=None,
        source=None,
        correlation_id=None,
        timestamp=None,
    ):
        self.id = f"evt_{id(self)}"
        self.event_type = event_type
        self.task_id = task_id
        self.payload = payload or {}
        self.source = source or "test"
        self.correlation_id = correlation_id
        self.timestamp = timestamp or datetime.now(timezone.utc)


class MockCoreBus:
    """Minimal core EventBus mock."""

    def __init__(self):
        self._handlers = {}
        self._sub_counter = 0

    def subscribe(self, pattern, handler):
        self._sub_counter += 1
        sub_id = f"sub_{self._sub_counter}"
        self._handlers[sub_id] = (pattern, handler)
        return sub_id

    def unsubscribe(self, sub_id):
        self._handlers.pop(sub_id, None)

    async def emit_event(self, event):
        """Simulate event emission for testing."""
        for sub_id, (pattern, handler) in list(self._handlers.items()):
            if pattern == event.event_type:
                await handler(event)


class MockSwarmBus:
    """Minimal swarm EventBus mock."""

    def __init__(self):
        self.events = []

    def emit(self, event_type, data, source=None, correlation_id=None):
        self.events.append(
            {
                "type": event_type,
                "data": data,
                "source": source,
                "correlation_id": correlation_id,
            }
        )


# ─── Section 1: Event Type Mapping ───────────────────────────


class TestEventTypeMapping:
    def test_task_created_maps_to_discovered(self):
        assert EVENT_TYPE_MAP["task.created"] == "task.discovered"

    def test_task_completed_maps_directly(self):
        assert EVENT_TYPE_MAP["task.completed"] == "task.completed"

    def test_submission_approved_maps_to_completed(self):
        assert EVENT_TYPE_MAP["submission.approved"] == "task.completed"

    def test_submission_rejected_maps_to_failed(self):
        assert EVENT_TYPE_MAP["submission.rejected"] == "task.failed"

    def test_payment_events_mapped(self):
        assert "payment.escrowed" in EVENT_TYPE_MAP
        assert "payment.released" in EVENT_TYPE_MAP

    def test_worker_events_mapped(self):
        assert EVENT_TYPE_MAP["worker.registered"] == "worker.registered"
        assert EVENT_TYPE_MAP["worker.application"] == "worker.applied"

    def test_all_mapped_types_are_strings(self):
        for core_type, swarm_type in EVENT_TYPE_MAP.items():
            assert isinstance(core_type, str)
            assert isinstance(swarm_type, str)

    def test_total_mapped_types(self):
        assert len(EVENT_TYPE_MAP) >= 14  # At minimum


# ─── Section 2: BridgeFilter ─────────────────────────────────


class TestBridgeFilter:
    def test_default_filter_passes_all(self):
        f = BridgeFilter()
        event = MockEMEvent(event_type="task.created")
        assert f.should_bridge(event) is True

    def test_event_type_filter(self):
        f = BridgeFilter(event_types={"task.created", "task.completed"})
        assert f.should_bridge(MockEMEvent(event_type="task.created")) is True
        assert f.should_bridge(MockEMEvent(event_type="task.assigned")) is False

    def test_min_bounty_filter(self):
        f = BridgeFilter(min_bounty_usd=5.0)
        assert f.should_bridge(MockEMEvent(payload={"bounty_usd": 10.0})) is True
        assert f.should_bridge(MockEMEvent(payload={"bounty_usd": 3.0})) is False
        assert f.should_bridge(MockEMEvent(payload={})) is False  # Missing bounty = 0

    def test_category_filter(self):
        f = BridgeFilter(categories={"delivery", "photo"})
        assert f.should_bridge(MockEMEvent(payload={"category": "delivery"})) is True
        assert f.should_bridge(MockEMEvent(payload={"category": "coding"})) is False
        # No category in payload → passes (empty string not in filter but category is optional)
        assert f.should_bridge(MockEMEvent(payload={})) is True

    def test_source_exclusion(self):
        f = BridgeFilter(exclude_sources={"swarm_coordinator"})
        assert f.should_bridge(MockEMEvent(source="swarm_coordinator")) is False
        assert f.should_bridge(MockEMEvent(source="api")) is True

    def test_combined_filters(self):
        f = BridgeFilter(
            event_types={"task.created"},
            min_bounty_usd=2.0,
            categories={"delivery"},
        )
        # Passes all filters
        assert (
            f.should_bridge(
                MockEMEvent(
                    event_type="task.created",
                    payload={"bounty_usd": 5.0, "category": "delivery"},
                )
            )
            is True
        )
        # Wrong event type
        assert (
            f.should_bridge(
                MockEMEvent(
                    event_type="task.completed",
                    payload={"bounty_usd": 5.0, "category": "delivery"},
                )
            )
            is False
        )


# ─── Section 3: BridgeStats ──────────────────────────────────


class TestBridgeStats:
    def test_default_stats(self):
        s = BridgeStats()
        assert s.events_received == 0
        assert s.events_bridged == 0
        assert s.errors == 0
        assert s.last_bridged_at is None

    def test_stats_mutation(self):
        s = BridgeStats()
        s.events_received = 10
        s.events_bridged = 8
        s.events_skipped = 2
        assert s.events_received == 10

    def test_events_by_type(self):
        s = BridgeStats()
        s.events_by_type["task.discovered"] = 5
        s.events_by_type["task.completed"] = 3
        assert len(s.events_by_type) == 2


# ─── Section 4: CoreEventBridge Lifecycle ─────────────────────


class TestBridgeLifecycle:
    def test_start_subscribes_to_all_types(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)

        bridge.start()
        assert bridge.is_running is True
        assert len(core_bus._handlers) == len(EVENT_TYPE_MAP)

    def test_stop_unsubscribes(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)

        bridge.start()
        assert len(core_bus._handlers) > 0

        bridge.stop()
        assert bridge.is_running is False
        assert len(core_bus._handlers) == 0

    def test_double_start_warning(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)

        bridge.start()
        initial_subs = len(core_bus._handlers)
        bridge.start()  # Should warn but not double-subscribe
        assert len(core_bus._handlers) == initial_subs

    def test_stop_when_not_started(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)
        bridge.stop()  # Should not raise
        assert bridge.is_running is False


# ─── Section 5: Event Transformation ─────────────────────────


class TestEventTransformation:
    def test_default_transform_preserves_payload(self):
        event = MockEMEvent(
            event_type="task.created",
            task_id="t123",
            payload={"title": "Test task", "bounty_usd": 5.0},
        )
        result = CoreEventBridge._default_transform(event)
        assert result["title"] == "Test task"
        assert result["bounty_usd"] == 5.0
        assert result["task_id"] == "t123"

    def test_default_transform_adds_bridge_metadata(self):
        event = MockEMEvent(event_type="task.created")
        result = CoreEventBridge._default_transform(event)
        assert "_bridge" in result
        assert result["_bridge"]["core_event_type"] == "task.created"

    def test_default_transform_no_task_id(self):
        event = MockEMEvent(event_type="payment.released", task_id=None)
        result = CoreEventBridge._default_transform(event)
        assert "task_id" not in result  # Only added when present

    def test_custom_transform(self):
        def custom(event):
            return {"custom": True, "type": event.event_type}

        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus, transform_payload=custom)

        # The bridge stores the custom transform
        assert bridge._transform is custom


# ─── Section 6: Event Bridging (async) ────────────────────────


class TestEventBridging:
    @pytest.mark.asyncio
    async def test_bridge_task_created(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)
        bridge.start()

        event = MockEMEvent(
            event_type="task.created",
            task_id="t1",
            payload={"title": "Test", "bounty_usd": 5.0},
        )
        await core_bus.emit_event(event)

        assert len(swarm_bus.events) == 1
        assert swarm_bus.events[0]["type"] == "task.discovered"
        assert swarm_bus.events[0]["source"] == "core_event_bridge"

    @pytest.mark.asyncio
    async def test_bridge_multiple_events(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)
        bridge.start()

        await core_bus.emit_event(MockEMEvent(event_type="task.created"))
        await core_bus.emit_event(MockEMEvent(event_type="task.completed"))

        assert len(swarm_bus.events) == 2
        assert swarm_bus.events[0]["type"] == "task.discovered"
        assert swarm_bus.events[1]["type"] == "task.completed"

    @pytest.mark.asyncio
    async def test_unmapped_event_skipped(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)
        bridge.start()

        # Manually call handler with unmapped type
        handler = bridge._handle_core_event
        event = MockEMEvent(event_type="unknown.event")
        await handler(event)

        assert len(swarm_bus.events) == 0

    @pytest.mark.asyncio
    async def test_filtered_event_not_bridged(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge_filter = BridgeFilter(min_bounty_usd=10.0)
        bridge = CoreEventBridge(core_bus, swarm_bus, bridge_filter=bridge_filter)
        bridge.start()

        event = MockEMEvent(
            event_type="task.created",
            payload={"bounty_usd": 3.0},
        )
        await core_bus.emit_event(event)

        assert len(swarm_bus.events) == 0


# ─── Section 7: Stats Reporting ───────────────────────────────


class TestStatsReporting:
    @pytest.mark.asyncio
    async def test_stats_after_bridging(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)
        bridge.start()

        await core_bus.emit_event(MockEMEvent(event_type="task.created"))
        await core_bus.emit_event(MockEMEvent(event_type="task.completed"))

        stats = bridge.stats
        assert stats["events_received"] == 2
        assert stats["events_bridged"] == 2
        assert stats["errors"] == 0
        assert stats["started"] is True

    @pytest.mark.asyncio
    async def test_stats_tracks_event_types(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)
        bridge.start()

        await core_bus.emit_event(MockEMEvent(event_type="task.created"))
        await core_bus.emit_event(MockEMEvent(event_type="task.created"))
        await core_bus.emit_event(MockEMEvent(event_type="task.completed"))

        stats = bridge.stats
        assert stats["events_by_type"]["task.discovered"] == 2
        assert stats["events_by_type"]["task.completed"] == 1

    def test_stats_initial_state(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus)

        stats = bridge.stats
        assert stats["events_received"] == 0
        assert stats["started"] is False
        assert stats["subscription_count"] == 0

    @pytest.mark.asyncio
    async def test_stats_tracks_filtered_events(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge_filter = BridgeFilter(min_bounty_usd=100.0)
        bridge = CoreEventBridge(core_bus, swarm_bus, bridge_filter=bridge_filter)
        bridge.start()

        event = MockEMEvent(event_type="task.created", payload={"bounty_usd": 1.0})
        await bridge._handle_core_event(event)

        stats = bridge.stats
        assert stats["events_received"] == 1
        assert stats["events_filtered"] == 1
        assert stats["events_bridged"] == 0


# ─── Section 8: Error Handling ────────────────────────────────


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_swarm_bus_error_counted(self):
        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        swarm_bus.emit = MagicMock(side_effect=RuntimeError("bus error"))
        bridge = CoreEventBridge(core_bus, swarm_bus)
        bridge.start()

        event = MockEMEvent(event_type="task.created")
        await bridge._handle_core_event(event)

        stats = bridge.stats
        assert stats["errors"] == 1
        assert stats["events_bridged"] == 0

    @pytest.mark.asyncio
    async def test_transform_error_counted(self):
        def bad_transform(event):
            raise ValueError("bad transform")

        core_bus = MockCoreBus()
        swarm_bus = MockSwarmBus()
        bridge = CoreEventBridge(core_bus, swarm_bus, transform_payload=bad_transform)
        bridge.start()

        event = MockEMEvent(event_type="task.created")
        await bridge._handle_core_event(event)

        assert bridge.stats["errors"] == 1
