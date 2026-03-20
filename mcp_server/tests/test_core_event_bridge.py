"""
Tests for CoreEventBridge — bridges EM Core EventBus → Swarm EventBus.
"""
import asyncio
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

os.environ.setdefault("TESTING", "1")

from mcp_server.events.bus import EventBus as CoreEventBus
from mcp_server.events.models import EMEvent, EventSource
from mcp_server.swarm.event_bus import EventBus as SwarmEventBus
from mcp_server.swarm.core_event_bridge import (
    CoreEventBridge,
    BridgeFilter,
    EVENT_TYPE_MAP,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def core_bus():
    return CoreEventBus()


@pytest.fixture
def swarm_bus():
    return SwarmEventBus()


@pytest.fixture
def bridge(core_bus, swarm_bus):
    return CoreEventBridge(core_bus, swarm_bus)


@pytest.fixture
def sample_task_event():
    return EMEvent(
        event_type="task.created",
        task_id="task_123",
        source=EventSource.REST_API,
        payload={
            "title": "Verify storefront sign",
            "category": "physical_verification",
            "bounty_usd": 5.00,
            "worker_wallet": "0xABC",
        },
    )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class TestBridgeLifecycle:
    def test_start_subscribes_to_core_events(self, bridge, core_bus):
        bridge.start()
        assert bridge.is_running
        assert len(bridge._subscription_ids) == len(EVENT_TYPE_MAP)

    def test_start_idempotent(self, bridge):
        bridge.start()
        bridge.start()  # Should warn but not error
        assert bridge.is_running

    def test_stop_unsubscribes(self, bridge):
        bridge.start()
        assert bridge.is_running
        bridge.stop()
        assert not bridge.is_running
        assert len(bridge._subscription_ids) == 0

    def test_stats_initial(self, bridge):
        stats = bridge.stats
        assert stats["events_received"] == 0
        assert stats["events_bridged"] == 0
        assert stats["started"] is False


# ---------------------------------------------------------------------------
# Event Mapping
# ---------------------------------------------------------------------------

class TestEventMapping:
    def test_all_core_types_have_swarm_mapping(self):
        """Verify every mapped core type has a valid swarm destination."""
        for core_type, swarm_type in EVENT_TYPE_MAP.items():
            assert isinstance(core_type, str)
            assert isinstance(swarm_type, str)
            assert "." in swarm_type, f"{swarm_type} should be dotted notation"

    def test_task_created_maps_to_discovered(self):
        assert EVENT_TYPE_MAP["task.created"] == "task.discovered"

    def test_task_completed_maps_directly(self):
        assert EVENT_TYPE_MAP["task.completed"] == "task.completed"

    def test_submission_approved_maps_to_completed(self):
        assert EVENT_TYPE_MAP["submission.approved"] == "task.completed"

    def test_submission_rejected_maps_to_failed(self):
        assert EVENT_TYPE_MAP["submission.rejected"] == "task.failed"


# ---------------------------------------------------------------------------
# Event Bridging
# ---------------------------------------------------------------------------

class TestEventBridging:
    @pytest.mark.asyncio
    async def test_bridge_task_created(self, bridge, core_bus, swarm_bus, sample_task_event):
        # Track what the swarm bus receives
        received = []
        swarm_bus.on("task.discovered", lambda e: received.append(e), source="test")

        bridge.start()
        await core_bus.publish(sample_task_event)

        assert len(received) == 1
        event = received[0]
        assert event.type == "task.discovered"
        assert event.data["task_id"] == "task_123"
        assert event.source == "core_event_bridge"

    @pytest.mark.asyncio
    async def test_bridge_task_completed(self, bridge, core_bus, swarm_bus):
        received = []
        swarm_bus.on("task.completed", lambda e: received.append(e), source="test")

        bridge.start()
        event = EMEvent(
            event_type="task.completed",
            task_id="task_456",
            source=EventSource.REST_API,
            payload={"worker_wallet": "0xDEF", "rating": 5},
        )
        await core_bus.publish(event)

        assert len(received) == 1
        assert received[0].data["rating"] == 5

    @pytest.mark.asyncio
    async def test_bridge_preserves_payload(self, bridge, core_bus, swarm_bus, sample_task_event):
        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()
        await core_bus.publish(sample_task_event)

        assert len(received) == 1
        data = received[0].data
        assert data["title"] == "Verify storefront sign"
        assert data["category"] == "physical_verification"
        assert data["bounty_usd"] == 5.00

    @pytest.mark.asyncio
    async def test_bridge_adds_metadata(self, bridge, core_bus, swarm_bus, sample_task_event):
        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()
        await core_bus.publish(sample_task_event)

        data = received[0].data
        assert "_bridge" in data
        assert data["_bridge"]["core_event_type"] == "task.created"
        assert data["_bridge"]["core_source"] == "rest_api"

    @pytest.mark.asyncio
    async def test_bridge_sets_correlation_id(self, bridge, core_bus, swarm_bus):
        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()
        event = EMEvent(
            event_type="task.assigned",
            task_id="task_789",
            source=EventSource.SYSTEM,
            correlation_id="corr-abc",
            payload={},
        )
        await core_bus.publish(event)

        assert received[0].correlation_id == "corr-abc"

    @pytest.mark.asyncio
    async def test_bridge_stats_update(self, bridge, core_bus, swarm_bus, sample_task_event):
        bridge.start()
        await core_bus.publish(sample_task_event)

        stats = bridge.stats
        assert stats["events_received"] == 1
        assert stats["events_bridged"] == 1
        assert stats["last_bridged_at"] is not None

    @pytest.mark.asyncio
    async def test_unmapped_events_skipped(self, bridge, core_bus, swarm_bus):
        received = []
        swarm_bus.on("*", lambda e: received.append(e), source="test")

        bridge.start()
        event = EMEvent(
            event_type="unknown.custom.event",
            source=EventSource.SYSTEM,
            payload={},
        )
        # This won't match any subscription since the bridge only subscribes
        # to mapped event types
        await core_bus.publish(event)

        # The bridge shouldn't have received it (no subscription for unmapped types)
        assert len(received) == 0


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

class TestBridgeFiltering:
    @pytest.mark.asyncio
    async def test_filter_by_min_bounty(self, core_bus, swarm_bus):
        filter_ = BridgeFilter(min_bounty_usd=3.00)
        bridge = CoreEventBridge(core_bus, swarm_bus, bridge_filter=filter_)

        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()

        # Low bounty — should be filtered
        low = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"bounty_usd": 1.00},
        )
        await core_bus.publish(low)

        # High bounty — should pass
        high = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"bounty_usd": 5.00},
        )
        await core_bus.publish(high)

        assert len(received) == 1
        assert received[0].data["bounty_usd"] == 5.00
        assert bridge.stats["events_filtered"] == 1

    @pytest.mark.asyncio
    async def test_filter_by_category(self, core_bus, swarm_bus):
        filter_ = BridgeFilter(categories={"physical_verification"})
        bridge = CoreEventBridge(core_bus, swarm_bus, bridge_filter=filter_)

        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()

        # Wrong category — filtered
        wrong = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"category": "data_collection"},
        )
        await core_bus.publish(wrong)

        # Right category — passes
        right = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"category": "physical_verification"},
        )
        await core_bus.publish(right)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_filter_by_source_anti_echo(self, core_bus, swarm_bus):
        filter_ = BridgeFilter(exclude_sources={EventSource.SYSTEM})
        bridge = CoreEventBridge(core_bus, swarm_bus, bridge_filter=filter_)

        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()

        # System source — should be filtered (anti-echo)
        sys_event = EMEvent(
            event_type="task.created",
            source=EventSource.SYSTEM,
            payload={},
        )
        await core_bus.publish(sys_event)

        # API source — should pass
        api_event = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={},
        )
        await core_bus.publish(api_event)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_filter_by_event_types(self, core_bus, swarm_bus):
        filter_ = BridgeFilter(event_types={"task.completed", "task.assigned"})
        bridge = CoreEventBridge(core_bus, swarm_bus, bridge_filter=filter_)

        received = []
        swarm_bus.on("*", lambda e: received.append(e), source="test")

        bridge.start()

        # task.created — filtered (not in allowed set)
        await core_bus.publish(EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={},
        ))

        # task.completed — passes
        await core_bus.publish(EMEvent(
            event_type="task.completed",
            source=EventSource.REST_API,
            payload={},
        ))

        assert len(received) == 1
        assert received[0].type == "task.completed"

    def test_filter_should_bridge_default(self):
        """Default filter should pass everything."""
        filter_ = BridgeFilter()
        event = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"bounty_usd": 0.01, "category": "test"},
        )
        assert filter_.should_bridge(event) is True

    def test_filter_combined(self):
        """Multiple filter criteria are AND-ed."""
        filter_ = BridgeFilter(
            min_bounty_usd=2.0,
            categories={"physical_verification"},
        )

        # Fails bounty
        e1 = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"bounty_usd": 1.0, "category": "physical_verification"},
        )
        assert filter_.should_bridge(e1) is False

        # Fails category
        e2 = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"bounty_usd": 5.0, "category": "data_collection"},
        )
        assert filter_.should_bridge(e2) is False

        # Passes both
        e3 = EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={"bounty_usd": 5.0, "category": "physical_verification"},
        )
        assert filter_.should_bridge(e3) is True


# ---------------------------------------------------------------------------
# Custom Payload Transform
# ---------------------------------------------------------------------------

class TestCustomTransform:
    @pytest.mark.asyncio
    async def test_custom_transform_function(self, core_bus, swarm_bus):
        def custom_transform(event):
            return {
                "task_id": event.task_id,
                "simplified": True,
                "custom_field": "hello",
            }

        bridge = CoreEventBridge(
            core_bus, swarm_bus, transform_payload=custom_transform
        )

        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()
        await core_bus.publish(EMEvent(
            event_type="task.completed",
            task_id="task_custom",
            source=EventSource.REST_API,
            payload={"ignored": True},
        ))

        assert len(received) == 1
        data = received[0].data
        assert data["simplified"] is True
        assert data["custom_field"] == "hello"
        assert "ignored" not in data


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_transform_error_counted(self, core_bus, swarm_bus):
        def bad_transform(event):
            raise ValueError("transform failed!")

        bridge = CoreEventBridge(
            core_bus, swarm_bus, transform_payload=bad_transform
        )

        bridge.start()
        await core_bus.publish(EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={},
        ))

        assert bridge.stats["errors"] == 1
        assert bridge.stats["events_bridged"] == 0

    @pytest.mark.asyncio
    async def test_bridge_continues_after_error(self, core_bus, swarm_bus):
        """One bad event shouldn't break subsequent events."""
        call_count = 0

        def flaky_transform(event):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first one fails!")
            return {"ok": True}

        bridge = CoreEventBridge(
            core_bus, swarm_bus, transform_payload=flaky_transform
        )

        received = []
        swarm_bus.on("task.*", lambda e: received.append(e), source="test")

        bridge.start()

        # First event errors
        await core_bus.publish(EMEvent(
            event_type="task.created",
            source=EventSource.REST_API,
            payload={},
        ))

        # Second event succeeds
        await core_bus.publish(EMEvent(
            event_type="task.completed",
            source=EventSource.REST_API,
            payload={},
        ))

        assert len(received) == 1
        assert bridge.stats["errors"] == 1
        assert bridge.stats["events_bridged"] == 1


# ---------------------------------------------------------------------------
# Multiple Event Types
# ---------------------------------------------------------------------------

class TestMultipleEventTypes:
    @pytest.mark.asyncio
    async def test_full_task_lifecycle_bridged(self, bridge, core_bus, swarm_bus):
        received = []
        swarm_bus.on("*", lambda e: received.append(e), source="test")

        bridge.start()

        lifecycle = [
            ("task.created", {"title": "Test"}),
            ("task.assigned", {"worker": "0x1"}),
            ("task.submitted", {"evidence": []}),
            ("task.completed", {"rating": 5}),
        ]

        for event_type, payload in lifecycle:
            await core_bus.publish(EMEvent(
                event_type=event_type,
                task_id="task_lifecycle",
                source=EventSource.REST_API,
                payload=payload,
            ))

        assert len(received) == 4
        types = [e.type for e in received]
        assert "task.discovered" in types
        assert "task.assigned" in types
        assert "task.submitted" in types
        assert "task.completed" in types

    @pytest.mark.asyncio
    async def test_payment_events_bridged(self, bridge, core_bus, swarm_bus):
        received = []
        swarm_bus.on("payment.*", lambda e: received.append(e), source="test")

        bridge.start()

        await core_bus.publish(EMEvent(
            event_type="payment.escrowed",
            source=EventSource.REST_API,
            payload={"amount": 5.00, "token": "USDC"},
        ))
        await core_bus.publish(EMEvent(
            event_type="payment.released",
            source=EventSource.REST_API,
            payload={"amount": 4.35, "worker": "0x1"},
        ))

        assert len(received) == 2
