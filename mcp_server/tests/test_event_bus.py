"""
Tests for Event Bus core (models, bus, adapters).

Phase 1 validation tests for MASTER_PLAN_MESHRELAY_V2.md.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from events.models import EMEvent, EventSource
from events.bus import EventBus


# ---------------------------------------------------------------------------
# EMEvent model tests
# ---------------------------------------------------------------------------


class TestEMEvent:
    def test_create_event(self):
        event = EMEvent(
            event_type="task.created",
            task_id="abc123",
            source=EventSource.REST_API,
            payload={"title": "Test Task"},
        )
        assert event.event_type == "task.created"
        assert event.task_id == "abc123"
        assert event.source == EventSource.REST_API
        assert event.payload["title"] == "Test Task"
        assert event.id  # auto-generated
        assert event.version == "1.0"

    def test_event_matches_exact(self):
        event = EMEvent(event_type="task.created", payload={})
        assert event.matches("task.created")
        assert not event.matches("task.assigned")

    def test_event_matches_wildcard(self):
        event = EMEvent(event_type="task.created", payload={})
        assert event.matches("task.*")
        assert not event.matches("submission.*")

    def test_event_matches_all(self):
        event = EMEvent(event_type="task.created", payload={})
        assert event.matches("*")

    def test_event_serialization(self):
        event = EMEvent(
            event_type="task.created",
            source=EventSource.MCP_TOOL,
            payload={"bounty_usd": 0.10},
        )
        data = event.model_dump()
        assert data["event_type"] == "task.created"
        assert data["source"] == "mcp_tool"
        assert data["payload"]["bounty_usd"] == 0.10

    def test_all_event_sources(self):
        sources = list(EventSource)
        assert len(sources) >= 6
        assert EventSource.MESHRELAY in sources
        assert EventSource.XMTP in sources
        assert EventSource.REST_API in sources


# ---------------------------------------------------------------------------
# EventBus tests
# ---------------------------------------------------------------------------


class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        bus = EventBus()
        received = []

        async def handler(event: EMEvent):
            received.append(event)

        bus.subscribe("task.created", handler)
        event = EMEvent(event_type="task.created", payload={"title": "Test"})
        count = await bus.publish(event)

        assert count == 1
        assert len(received) == 1
        assert received[0].payload["title"] == "Test"

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self):
        bus = EventBus()
        received = []

        async def handler(event: EMEvent):
            received.append(event.event_type)

        bus.subscribe("task.*", handler)

        await bus.publish(EMEvent(event_type="task.created", payload={}))
        await bus.publish(EMEvent(event_type="task.assigned", payload={}))
        await bus.publish(EMEvent(event_type="submission.approved", payload={}))

        assert received == ["task.created", "task.assigned"]

    @pytest.mark.asyncio
    async def test_all_subscription(self):
        bus = EventBus()
        received = []

        async def handler(event: EMEvent):
            received.append(event.event_type)

        bus.subscribe("*", handler)

        await bus.publish(EMEvent(event_type="task.created", payload={}))
        await bus.publish(EMEvent(event_type="payment.released", payload={}))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_anti_echo(self):
        """Events from a source are skipped by subscribers filtering that source."""
        bus = EventBus()
        received = []

        async def handler(event: EMEvent):
            received.append(event)

        # Subscribe with anti-echo for MESHRELAY
        bus.subscribe("task.*", handler, source_filter=EventSource.MESHRELAY)

        # Event from REST_API should be delivered
        await bus.publish(
            EMEvent(
                event_type="task.created",
                source=EventSource.REST_API,
                payload={},
            )
        )
        assert len(received) == 1

        # Event from MESHRELAY should be skipped (anti-echo)
        await bus.publish(
            EMEvent(
                event_type="task.created",
                source=EventSource.MESHRELAY,
                payload={},
            )
        )
        assert len(received) == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        async def handler(event: EMEvent):
            received.append(event)

        sub_id = bus.subscribe("task.*", handler)
        await bus.publish(EMEvent(event_type="task.created", payload={}))
        assert len(received) == 1

        bus.unsubscribe(sub_id)
        await bus.publish(EMEvent(event_type="task.created", payload={}))
        assert len(received) == 1  # No new delivery

    @pytest.mark.asyncio
    async def test_handler_error_does_not_break_others(self):
        bus = EventBus()
        received = []

        async def bad_handler(event: EMEvent):
            raise ValueError("Boom")

        async def good_handler(event: EMEvent):
            received.append(event)

        bus.subscribe("task.*", bad_handler)
        bus.subscribe("task.*", good_handler)

        count = await bus.publish(EMEvent(event_type="task.created", payload={}))
        assert count == 1  # Only good_handler succeeded
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_stats(self):
        bus = EventBus()

        async def handler(event: EMEvent):
            pass

        bus.subscribe("*", handler)
        await bus.publish(EMEvent(event_type="task.created", payload={}))
        await bus.publish(EMEvent(event_type="task.assigned", payload={}))

        assert bus.stats["events_published"] == 2
        assert bus.stats["events_delivered"] == 2

    def test_subscription_count(self):
        bus = EventBus()

        async def handler(event: EMEvent):
            pass

        bus.subscribe("task.*", handler)
        bus.subscribe("payment.*", handler)
        assert bus.subscription_count == 2


# ---------------------------------------------------------------------------
# WebhookRegistry.get_by_owner_and_event tests (BUG-1 fix)
# ---------------------------------------------------------------------------


class TestWebhookRegistryBug1Fix:
    def test_get_by_owner_and_event(self):
        from webhooks.registry import WebhookRegistry
        from webhooks.events import WebhookEventType

        registry = WebhookRegistry()

        # Register webhook for owner_a: task.created + task.assigned
        registry.register(
            owner_id="owner_a",
            url="https://example.com/a",
            events=[WebhookEventType.TASK_CREATED, WebhookEventType.TASK_ASSIGNED],
        )

        # Register webhook for owner_b: task.created only
        registry.register(
            owner_id="owner_b",
            url="https://example.com/b",
            events=[WebhookEventType.TASK_CREATED],
        )

        # owner_a + TASK_CREATED → should find 1
        results = registry.get_by_owner_and_event(
            "owner_a", WebhookEventType.TASK_CREATED
        )
        assert len(results) == 1
        assert results[0].owner_id == "owner_a"

        # owner_a + TASK_ASSIGNED → should find 1
        results = registry.get_by_owner_and_event(
            "owner_a", WebhookEventType.TASK_ASSIGNED
        )
        assert len(results) == 1

        # owner_b + TASK_CREATED → should find 1
        results = registry.get_by_owner_and_event(
            "owner_b", WebhookEventType.TASK_CREATED
        )
        assert len(results) == 1
        assert results[0].owner_id == "owner_b"

        # owner_b + TASK_ASSIGNED → should find 0
        results = registry.get_by_owner_and_event(
            "owner_b", WebhookEventType.TASK_ASSIGNED
        )
        assert len(results) == 0

        # unknown_owner → should find 0
        results = registry.get_by_owner_and_event(
            "unknown", WebhookEventType.TASK_CREATED
        )
        assert len(results) == 0

    def test_get_by_owner_and_event_only_active(self):
        from webhooks.registry import WebhookRegistry
        from webhooks.events import WebhookEventType

        registry = WebhookRegistry()

        reg = registry.register(
            owner_id="owner_x",
            url="https://example.com/x",
            events=[WebhookEventType.TASK_CREATED],
        )

        # Active → should find
        results = registry.get_by_owner_and_event(
            "owner_x", WebhookEventType.TASK_CREATED
        )
        assert len(results) == 1

        # Pause it → should not find
        registry.pause(reg.webhook.webhook_id, "owner_x")
        results = registry.get_by_owner_and_event(
            "owner_x", WebhookEventType.TASK_CREATED
        )
        assert len(results) == 0


# ---------------------------------------------------------------------------
# MeshRelay adapter tests
# ---------------------------------------------------------------------------


class TestMeshRelayAdapter:
    def test_format_irc_line_task_created(self):
        from events.adapters.meshrelay import _format_irc_line

        event = EMEvent(
            event_type="task.created",
            task_id="abcdef1234567890",
            payload={
                "title": "Take photo of storefront",
                "bounty_usd": 0.10,
                "category": "physical_presence",
                "payment_network": "base",
                "task_id": "abcdef1234567890",
            },
        )
        line = _format_irc_line(event)
        assert "[NEW TASK]" in line
        assert "Take photo of storefront" in line
        assert "$0.10" in line
        assert "physical_presence" in line
        assert "/claim abcdef12" in line

    def test_format_irc_line_payment_released(self):
        from events.adapters.meshrelay import _format_irc_line

        event = EMEvent(
            event_type="payment.released",
            task_id="abc12345",
            payload={
                "amount_usd": 0.10,
                "tx_hash": "0x1234567890abcdef1234567890abcdef",
                "chain": "base",
            },
        )
        line = _format_irc_line(event)
        assert "[PAID]" in line
        assert "$0.10" in line
        assert "TX:" in line

    def test_format_irc_line_submission_approved(self):
        from events.adapters.meshrelay import _format_irc_line

        event = EMEvent(
            event_type="submission.approved",
            task_id="abc12345",
            payload={"bounty_usd": 0.05},
        )
        line = _format_irc_line(event)
        assert "[APPROVED]" in line

    @pytest.mark.asyncio
    async def test_adapter_anti_echo(self):
        from events.adapters.meshrelay import MeshRelayAdapter

        bus = EventBus()
        adapter = MeshRelayAdapter(bus=bus)
        adapter.start()

        # Event from REST_API should be forwarded
        await bus.publish(
            EMEvent(
                event_type="task.created",
                source=EventSource.REST_API,
                payload={"title": "Test", "bounty_usd": 0.10, "category": "test"},
            )
        )
        assert adapter.stats["forwarded"] == 1

        # Event from MESHRELAY should be skipped (anti-echo)
        await bus.publish(
            EMEvent(
                event_type="task.created",
                source=EventSource.MESHRELAY,
                payload={"title": "Test", "bounty_usd": 0.10, "category": "test"},
            )
        )
        assert adapter.stats["forwarded"] == 1  # Still 1

        adapter.stop()
