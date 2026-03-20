"""
Tests for Chat Relay module (Phase 1 — IRC Task Chat).

Covers:
- Pydantic message models and validation
- Guardrail action blocking
- Platform config chat defaults
- IRCPool channel subscription logic
- EventInjector message formatting
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.infrastructure


# =========================================================================
# Task 1.4: Chat Message Schema Tests
# =========================================================================


class TestChatMessageModels:
    """Test Pydantic chat message schemas."""

    def test_chat_message_in_valid(self):
        from chat.models import ChatMessageIn

        msg = ChatMessageIn(text="Hello world")
        assert msg.type == "message"
        assert msg.text == "Hello world"

    def test_chat_message_in_max_length(self):
        from chat.models import ChatMessageIn

        with pytest.raises(Exception):
            ChatMessageIn(text="x" * 2001)

    def test_chat_message_in_exactly_max(self):
        from chat.models import ChatMessageIn

        msg = ChatMessageIn(text="x" * 2000)
        assert len(msg.text) == 2000

    def test_chat_message_out_defaults(self):
        from chat.models import ChatMessageOut

        msg = ChatMessageOut(text="test")
        assert msg.type == "message"
        assert msg.nick == ""
        assert msg.source == "system"
        assert msg.task_id == ""
        assert isinstance(msg.timestamp, datetime)

    def test_chat_message_out_all_fields(self):
        from chat.models import ChatMessageOut

        now = datetime.now(timezone.utc)
        msg = ChatMessageOut(
            type="system",
            nick="bot",
            text="hello",
            source="irc",
            timestamp=now,
            task_id="abc123",
        )
        assert msg.type == "system"
        assert msg.nick == "bot"
        assert msg.source == "irc"
        assert msg.task_id == "abc123"

    def test_chat_message_out_serialization(self):
        from chat.models import ChatMessageOut

        msg = ChatMessageOut(text="hello", nick="user1", source="mobile")
        data = msg.model_dump(mode="json")
        assert data["text"] == "hello"
        assert data["nick"] == "user1"
        assert "timestamp" in data

    def test_chat_error_model(self):
        from chat.models import ChatError

        err = ChatError(code="action_blocked", text="Not allowed")
        assert err.type == "error"
        assert err.code == "action_blocked"
        assert err.text == "Not allowed"

    def test_chat_history_model(self):
        from chat.models import ChatHistory, ChatMessageOut

        msgs = [ChatMessageOut(text="hi"), ChatMessageOut(text="bye")]
        history = ChatHistory(
            messages=msgs,
            channel="#task-abcd1234",
            task_id="abcd1234-full-uuid",
            connected_users=2,
        )
        assert len(history.messages) == 2
        assert history.channel == "#task-abcd1234"
        assert history.connected_users == 2

    def test_chat_history_empty(self):
        from chat.models import ChatHistory

        history = ChatHistory(
            messages=[],
            channel="#task-test",
            task_id="test",
        )
        assert len(history.messages) == 0
        assert history.connected_users == 0

    def test_chat_status_model(self):
        from chat.models import ChatStatus

        status = ChatStatus(
            enabled=True,
            irc_connected=True,
            active_channels=3,
            connected_clients=5,
        )
        assert status.enabled is True
        assert status.active_channels == 3


# =========================================================================
# Guardrail Tests
# =========================================================================


class TestGuardrails:
    """Test action-blocking guardrails."""

    def test_blocked_approve(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("/approve") == "/approve"

    def test_blocked_cancel(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("/cancel this task") == "/cancel"

    def test_blocked_pay(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("/pay 100") == "/pay"

    def test_blocked_case_insensitive(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("/APPROVE") == "/approve"

    def test_allowed_normal_message(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("Hello, how is the task going?") is None

    def test_allowed_slash_in_middle(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("Use https://example.com/approve for info") is None

    def test_allowed_empty_string(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("") is None

    def test_blocked_dispute(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("/dispute bad quality") == "/dispute"

    def test_blocked_release(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("/release funds") == "/release"

    def test_blocked_with_whitespace(self):
        from chat.models import is_blocked_action

        assert is_blocked_action("  /approve  ") == "/approve"


# =========================================================================
# Task 1.7: Platform Config Chat Defaults
# =========================================================================


class TestChatConfig:
    """Test chat configuration defaults in platform_config."""

    def test_task_chat_feature_flag_default(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["feature.task_chat_enabled"] is False

    def test_chat_irc_host_default(self):
        from config.platform_config import PlatformConfig

        host = PlatformConfig._defaults["chat.irc_host"]
        assert "meshrelay" in host

    def test_chat_irc_port_default(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["chat.irc_port"] == 6697

    def test_chat_irc_tls_default(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["chat.irc_tls"] is True

    def test_chat_max_message_length(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["chat.max_message_length"] == 2000

    def test_chat_history_limit(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["chat.history_limit"] == 50

    def test_chat_agent_join_mode_default(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["chat.agent_join_mode"] == "optional"

    def test_chat_retention_days(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["chat.retention_days"] == 90

    def test_chat_channel_prefix(self):
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["chat.channel_prefix"] == "#task-"


# =========================================================================
# Task 1.2: IRC Pool Tests
# =========================================================================


class TestIRCPool:
    """Test IRCPool subscription and channel management."""

    def setup_method(self):
        from chat.irc_pool import IRCPool

        IRCPool.reset_instance()

    def teardown_method(self):
        from chat.irc_pool import IRCPool

        IRCPool.reset_instance()

    def test_singleton_instance(self):
        from chat.irc_pool import IRCPool

        pool1 = IRCPool.get_instance()
        pool2 = IRCPool.get_instance()
        assert pool1 is pool2

    def test_reset_instance(self):
        from chat.irc_pool import IRCPool

        pool1 = IRCPool.get_instance()
        IRCPool.reset_instance()
        pool2 = IRCPool.get_instance()
        assert pool1 is not pool2

    def test_nick_generation(self):
        from chat.irc_pool import _generate_nick

        nick = _generate_nick("em-relay")
        assert nick.startswith("em-relay-")
        assert len(nick) == len("em-relay-") + 4

    def test_nick_uniqueness(self):
        from chat.irc_pool import _generate_nick

        nicks = {_generate_nick("test") for _ in range(20)}
        # Should generate mostly unique nicks (probabilistic but very likely)
        assert len(nicks) > 15

    @pytest.mark.asyncio
    async def test_subscribe_adds_channel(self):
        from chat.irc_pool import IRCPool

        pool = IRCPool(host="localhost", port=6667)
        pool._connected = True
        pool._writer = MagicMock()
        pool._writer.write = MagicMock()
        pool._writer.drain = AsyncMock()

        callback = AsyncMock()
        await pool.subscribe("#task-abc", "sub1", callback)

        assert "#task-abc" in pool._subscriptions
        assert "sub1" in pool._subscriptions["#task-abc"]

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_channel(self):
        from chat.irc_pool import IRCPool

        pool = IRCPool(host="localhost", port=6667)
        pool._connected = True
        pool._writer = MagicMock()
        pool._writer.write = MagicMock()
        pool._writer.drain = AsyncMock()

        callback = AsyncMock()
        await pool.subscribe("#task-abc", "sub1", callback)
        await pool.unsubscribe("#task-abc", "sub1")

        assert "#task-abc" not in pool._subscriptions

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_channel(self):
        from chat.irc_pool import IRCPool

        pool = IRCPool(host="localhost", port=6667)
        pool._connected = True
        pool._writer = MagicMock()
        pool._writer.write = MagicMock()
        pool._writer.drain = AsyncMock()

        cb1 = AsyncMock()
        cb2 = AsyncMock()
        await pool.subscribe("#task-abc", "sub1", cb1)
        await pool.subscribe("#task-abc", "sub2", cb2)

        assert len(pool._subscriptions["#task-abc"]) == 2

        # Unsubscribe one — channel should stay
        await pool.unsubscribe("#task-abc", "sub1")
        assert "#task-abc" in pool._subscriptions
        assert len(pool._subscriptions["#task-abc"]) == 1

    @pytest.mark.asyncio
    async def test_message_dispatch(self):
        from chat.irc_pool import IRCPool

        pool = IRCPool(host="localhost", port=6667)
        pool._connected = True
        pool._nick = "em-relay-test"

        cb = AsyncMock()
        pool._subscriptions["#task-abc"] = {"sub1"}
        pool._callbacks["sub1"] = cb

        # Simulate a PRIVMSG from IRC
        line = ":agent!user@host PRIVMSG #task-abc :Hello from IRC"
        await pool._handle_line(line)

        cb.assert_awaited_once_with("#task-abc", "agent", "Hello from IRC")

    @pytest.mark.asyncio
    async def test_skip_own_messages(self):
        from chat.irc_pool import IRCPool

        pool = IRCPool(host="localhost", port=6667)
        pool._connected = True
        pool._nick = "em-relay-test"

        cb = AsyncMock()
        pool._subscriptions["#task-abc"] = {"sub1"}
        pool._callbacks["sub1"] = cb

        # Message from ourselves — should be skipped
        line = ":em-relay-test!user@host PRIVMSG #task-abc :echo"
        await pool._handle_line(line)

        cb.assert_not_awaited()

    def test_stats(self):
        from chat.irc_pool import IRCPool

        pool = IRCPool(host="localhost", port=6667)
        stats = pool.stats
        assert stats["connected"] is False
        assert stats["messages_relayed"] == 0
        assert stats["active_channels"] == 0


# =========================================================================
# Task 1.1: Chat Relay Tests
# =========================================================================


class TestChatRelay:
    """Test the chat relay endpoint helpers."""

    def test_task_channel_derivation(self):
        from chat.relay import _task_channel

        assert _task_channel("ABCD1234-5678-9012-3456-789012345678") == "#task-abcd1234"

    def test_task_channel_short_id(self):
        from chat.relay import _task_channel

        assert _task_channel("abc") == "#task-abc"


# =========================================================================
# Task 1.6: Event Injector Tests
# =========================================================================


class TestEventInjector:
    """Test event-to-chat system message formatting."""

    def test_format_submission_received(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(event_type="submission.received", task_id="test")
        msg = _format_system_message(event)
        assert msg is not None
        assert "Evidence submitted" in msg

    def test_format_submission_approved(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(event_type="submission.approved", task_id="test")
        msg = _format_system_message(event)
        assert "approved" in msg.lower()

    def test_format_submission_rejected(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(
            event_type="submission.rejected",
            task_id="test",
            payload={"reason": "Blurry photo"},
        )
        msg = _format_system_message(event)
        assert "Blurry photo" in msg

    def test_format_payment_released(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(
            event_type="payment.released",
            task_id="test",
            payload={"amount_usd": 5.50},
        )
        msg = _format_system_message(event)
        assert "$5.5" in msg

    def test_format_task_cancelled_with_reason(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(
            event_type="task.cancelled",
            task_id="test",
            payload={"reason": "Timeout"},
        )
        msg = _format_system_message(event)
        assert "Timeout" in msg

    def test_format_task_cancelled_no_reason(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(event_type="task.cancelled", task_id="test")
        msg = _format_system_message(event)
        assert "cancelled" in msg.lower()

    def test_format_unknown_event(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(event_type="something.unknown", task_id="test")
        msg = _format_system_message(event)
        assert msg is None

    def test_format_task_assigned(self):
        from chat.event_injector import _format_system_message
        from events.models import EMEvent

        event = EMEvent(event_type="task.assigned", task_id="test")
        msg = _format_system_message(event)
        assert "assigned" in msg.lower()

    def test_injector_start_stop(self):
        from chat.event_injector import EventInjector
        from events.bus import EventBus

        bus = EventBus()
        injector = EventInjector(bus=bus)
        injector.start()
        assert bus.subscription_count > 0

        injector.stop()
        assert bus.subscription_count == 0


# =========================================================================
# Integration: __init__.py exports
# =========================================================================


class TestChatModuleExports:
    """Verify the chat module exports are accessible."""

    def test_imports(self):
        from chat import ChatMessageIn, chat_router, setup_chat

        assert ChatMessageIn is not None
        assert chat_router is not None
        assert setup_chat is not None
