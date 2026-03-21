"""
Tests for Phase 7: XMTP ↔ MeshRelay Bridge (MASTER_PLAN_MESHRELAY_V2.md).

Validates:
- XMTP Event Bus adapter (xmtp.py)
- XMTP ↔ IRC bridge (xmtp-to-irc.ts)
- Cross-protocol identity (identity-store.ts extensions)
- Group auto-creation (group-manager.ts)
- Notification router (notification-router.ts)
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

XMTP_BOT_ROOT = Path(__file__).parent.parent.parent / "xmtp-bot" / "src"
BRIDGES_ROOT = XMTP_BOT_ROOT / "bridges"
SERVICES_ROOT = XMTP_BOT_ROOT / "services"
ADAPTERS_ROOT = Path(__file__).parent.parent / "events" / "adapters"


# ---------------------------------------------------------------------------
# Task 7.1: XMTP Event Bus Adapter
# ---------------------------------------------------------------------------


class TestXMTPAdapter:
    def test_file_exists(self):
        assert (ADAPTERS_ROOT / "xmtp.py").exists()

    def test_has_xmtp_adapter_class(self):
        content = (ADAPTERS_ROOT / "xmtp.py").read_text()
        assert "class XMTPAdapter" in content

    def test_subscribes_to_events(self):
        content = (ADAPTERS_ROOT / "xmtp.py").read_text()
        assert "task.created" in content
        assert "task.assigned" in content
        assert "submission.approved" in content
        assert "payment.released" in content

    def test_has_anti_echo(self):
        content = (ADAPTERS_ROOT / "xmtp.py").read_text()
        assert "EventSource.XMTP" in content
        assert "source_filter" in content

    def test_resolves_targets(self):
        content = (ADAPTERS_ROOT / "xmtp.py").read_text()
        assert "_resolve_targets" in content
        assert "target_users" in content
        assert "worker_wallet" in content

    def test_formats_messages(self):
        content = (ADAPTERS_ROOT / "xmtp.py").read_text()
        assert "_format_message" in content
        assert "[New Task]" in content
        assert "[Assigned]" in content
        assert "[Paid]" in content

    def test_sends_via_http(self):
        content = (ADAPTERS_ROOT / "xmtp.py").read_text()
        assert "httpx" in content
        assert "/api/notify" in content

    def test_has_stats(self):
        content = (ADAPTERS_ROOT / "xmtp.py").read_text()
        assert "notifications_sent" in content
        assert "errors" in content


class TestXMTPAdapterUnit:
    """Unit tests for XMTPAdapter logic."""

    def test_format_task_created(self):
        from events.adapters.xmtp import XMTPAdapter
        from events.bus import EventBus
        from events.models import EMEvent

        adapter = XMTPAdapter(bus=EventBus())
        event = EMEvent(
            event_type="task.created",
            payload={"title": "Take photo", "bounty_usdc": 0.10},
        )
        msg = adapter._format_message(event)
        assert "[New Task]" in msg
        assert "Take photo" in msg

    def test_format_payment_released(self):
        from events.adapters.xmtp import XMTPAdapter
        from events.bus import EventBus
        from events.models import EMEvent

        adapter = XMTPAdapter(bus=EventBus())
        event = EMEvent(
            event_type="payment.released",
            payload={"task_id": "abc12345", "amount_usd": 0.10},
        )
        msg = adapter._format_message(event)
        assert "[Paid]" in msg

    def test_resolve_targets_from_payload(self):
        from events.adapters.xmtp import XMTPAdapter
        from events.bus import EventBus
        from events.models import EMEvent

        adapter = XMTPAdapter(bus=EventBus())
        event = EMEvent(
            event_type="task.assigned",
            payload={
                "worker_wallet": "0xWorker123",
                "publisher_wallet": "0xPub456",
            },
        )
        targets = adapter._resolve_targets(event)
        assert "0xWorker123" in targets
        assert "0xPub456" in targets

    def test_resolve_targets_deduplicates(self):
        from events.adapters.xmtp import XMTPAdapter
        from events.bus import EventBus
        from events.models import EMEvent

        adapter = XMTPAdapter(bus=EventBus())
        event = EMEvent(
            event_type="task.assigned",
            payload={"worker_wallet": "0xSame"},
            target_users=["0xSame"],
        )
        targets = adapter._resolve_targets(event)
        assert len(targets) == 1


# ---------------------------------------------------------------------------
# Task 7.2: XMTP ↔ IRC Bridge
# ---------------------------------------------------------------------------


class TestXmtpToIrcBridge:
    def test_file_exists(self):
        assert (BRIDGES_ROOT / "xmtp-to-irc.ts").exists()

    def test_has_link_function(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert "linkChannelToGroup" in content

    def test_has_forward_xmtp_to_irc(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert "forwardXmtpToIrc" in content

    def test_has_forward_irc_to_xmtp(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert "forwardIrcToXmtp" in content

    def test_has_rate_limiter(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert "RATE_LIMIT_MS" in content
        assert "isRateLimited" in content

    def test_only_bridges_task_channels(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert 'startsWith("#task-")' in content

    def test_prevents_bridge_loops(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert "<XMTP:" in content
        assert "<IRC:" in content

    def test_has_unlink_function(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert "unlinkChannel" in content

    def test_has_stats(self):
        content = (BRIDGES_ROOT / "xmtp-to-irc.ts").read_text()
        assert "getBridgeStats" in content


# ---------------------------------------------------------------------------
# Task 7.3: Cross-Protocol Identity
# ---------------------------------------------------------------------------


class TestCrossProtocolIdentity:
    def test_identity_store_has_sync_lookup(self):
        content = (BRIDGES_ROOT / "identity-store.ts").read_text()
        assert "getNickByWalletSync" in content

    def test_identity_store_has_preferred_channel(self):
        content = (BRIDGES_ROOT / "identity-store.ts").read_text()
        assert "setPreferredChannel" in content
        assert "preferred_channel" in content

    def test_irc_identity_interface_has_preferred_channel(self):
        content = (BRIDGES_ROOT / "identity-store.ts").read_text()
        assert 'preferred_channel: "irc" | "xmtp" | "both"' in content


# ---------------------------------------------------------------------------
# Task 7.4: Group Manager (already exists, check for task-channel linking)
# ---------------------------------------------------------------------------


class TestGroupManagerExtension:
    def test_group_manager_exists(self):
        assert (SERVICES_ROOT / "group-manager.ts").exists()

    def test_has_create_task_group(self):
        content = (SERVICES_ROOT / "group-manager.ts").read_text()
        assert "createTaskGroup" in content

    def test_has_task_group_interface(self):
        content = (SERVICES_ROOT / "group-manager.ts").read_text()
        assert "TaskGroup" in content
        assert "groupId" in content


# ---------------------------------------------------------------------------
# Task 7.5: Notification Router
# ---------------------------------------------------------------------------


class TestNotificationRouter:
    def test_file_exists(self):
        assert (SERVICES_ROOT / "notification-router.ts").exists()

    def test_has_priority_levels(self):
        content = (SERVICES_ROOT / "notification-router.ts").read_text()
        assert "critical" in content
        assert "important" in content
        assert '"info"' in content

    def test_has_event_priorities(self):
        content = (SERVICES_ROOT / "notification-router.ts").read_text()
        assert "EVENT_PRIORITIES" in content
        assert "payment.released" in content
        assert "task.assigned" in content

    def test_has_route_notification(self):
        content = (SERVICES_ROOT / "notification-router.ts").read_text()
        assert "routeNotification" in content

    def test_critical_goes_to_all(self):
        content = (SERVICES_ROOT / "notification-router.ts").read_text()
        assert 'priority === "critical"' in content

    def test_has_channel_preference(self):
        content = (SERVICES_ROOT / "notification-router.ts").read_text()
        assert "ChannelPreference" in content
        assert '"irc"' in content
        assert '"xmtp"' in content
        assert '"both"' in content

    def test_has_notification_handlers(self):
        content = (SERVICES_ROOT / "notification-router.ts").read_text()
        assert "setNotificationHandlers" in content
