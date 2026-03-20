"""
Tests for Chat Relay module (Phase 1-4 — IRC Task Chat).

Covers:
- Pydantic message models and validation
- Guardrail action blocking (Layer 1 slash commands + Layer 2 NLP)
- Platform config chat defaults
- IRCPool channel subscription logic
- EventInjector message formatting
- GuardrailFilter (enhanced, bilingual NLP patterns)
- ChatLogService singleton and interface
- Rate limiter (per-second and per-hour)
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

    def test_phase4_imports(self):
        from chat import GuardrailFilter, ChatLogService, get_log_service

        assert GuardrailFilter is not None
        assert ChatLogService is not None
        assert get_log_service is not None


# =========================================================================
# Phase 4 — Task 4.1: GuardrailFilter Tests
# =========================================================================


class TestGuardrailFilter:
    """Test enhanced guardrail with NLP patterns (bilingual)."""

    def setup_method(self):
        from chat.guardrail import GuardrailFilter

        self.gf = GuardrailFilter()

    # -- Layer 1: Slash commands --

    def test_blocks_slash_approve(self):
        result = self.gf.check("/approve")
        assert not result.allowed
        assert result.matched_pattern == "/approve"

    def test_blocks_slash_cancel(self):
        result = self.gf.check("/cancel this task")
        assert not result.allowed
        assert result.matched_pattern == "/cancel"

    def test_blocks_slash_close(self):
        result = self.gf.check("/close")
        assert not result.allowed
        assert result.matched_pattern == "/close"

    def test_blocks_slash_case_insensitive(self):
        result = self.gf.check("/REFUND now")
        assert not result.allowed
        assert result.matched_pattern == "/refund"

    def test_blocks_slash_with_whitespace(self):
        result = self.gf.check("  /dispute  ")
        assert not result.allowed

    # -- Layer 2: NLP patterns (English) --

    def test_blocks_cancel_my_task(self):
        result = self.gf.check("cancel my task please")
        assert not result.allowed
        assert result.matched_pattern == "cancel_task"

    def test_blocks_cancel_this_task(self):
        result = self.gf.check("Can you cancel this task?")
        assert not result.allowed
        assert result.matched_pattern == "cancel_task"

    def test_blocks_approve_this(self):
        result = self.gf.check("approve this submission")
        assert not result.allowed
        assert result.matched_pattern == "approve_request"

    def test_blocks_pay_me(self):
        result = self.gf.check("pay me now")
        assert not result.allowed
        assert result.matched_pattern == "pay_request"

    def test_blocks_release_payment(self):
        result = self.gf.check("please release payment")
        assert not result.allowed
        assert result.matched_pattern == "release_request"

    def test_blocks_reject_this(self):
        result = self.gf.check("reject this evidence")
        assert not result.allowed
        assert result.matched_pattern == "reject_request"

    def test_blocks_dispute_this(self):
        result = self.gf.check("I want to dispute this")
        assert not result.allowed
        assert result.matched_pattern == "dispute_request"

    def test_blocks_refund_my(self):
        result = self.gf.check("refund my money")
        assert not result.allowed
        assert result.matched_pattern == "refund_request"

    # -- Layer 2: NLP patterns (Spanish) --

    def test_blocks_cancelar_mi_tarea(self):
        result = self.gf.check("cancelar mi tarea por favor")
        assert not result.allowed
        assert result.matched_pattern == "cancel_task"

    def test_blocks_cancela_esta_tarea(self):
        result = self.gf.check("cancela esta tarea")
        assert not result.allowed
        assert result.matched_pattern == "cancel_task"

    def test_blocks_aprueba_esto(self):
        result = self.gf.check("aprueba esto")
        assert not result.allowed
        assert result.matched_pattern == "approve_request"

    def test_blocks_pagame(self):
        result = self.gf.check("pagame ahora")
        assert not result.allowed
        assert result.matched_pattern == "pay_request"

    def test_blocks_libera_pago(self):
        result = self.gf.check("libera el pago")
        assert not result.allowed
        assert result.matched_pattern == "release_request"

    def test_blocks_rechaza_esto(self):
        result = self.gf.check("rechaza esto")
        assert not result.allowed
        assert result.matched_pattern == "reject_request"

    def test_blocks_devuelve_mi(self):
        result = self.gf.check("devuelve mi dinero")
        assert not result.allowed
        assert result.matched_pattern == "refund_request"

    # -- Allowed messages --

    def test_allows_normal_message(self):
        result = self.gf.check("Hello! How is the task going?")
        assert result.allowed

    def test_allows_empty_string(self):
        result = self.gf.check("")
        assert result.allowed

    def test_allows_question_about_payment(self):
        result = self.gf.check("When will the payment be processed?")
        assert result.allowed

    def test_allows_cancel_word_in_context(self):
        # "cancel" not followed by my/this/the + task
        result = self.gf.check("I had to cancel my dinner plans")
        assert result.allowed

    def test_allows_approve_word_in_context(self):
        # "approve" not followed by this/the/my/it
        result = self.gf.check("I hope they approve our proposal")
        assert result.allowed

    def test_allows_url_with_action_word(self):
        result = self.gf.check("Check https://example.com/approve-docs for info")
        assert result.allowed

    # -- Config: disable NLP --

    def test_nlp_disabled(self):
        from chat.guardrail import GuardrailFilter

        gf = GuardrailFilter(enable_nlp=False)
        result = gf.check("cancel my task")
        assert result.allowed  # NLP disabled, only slash commands blocked

    def test_nlp_disabled_still_blocks_slash(self):
        from chat.guardrail import GuardrailFilter

        gf = GuardrailFilter(enable_nlp=False)
        result = gf.check("/cancel task")
        assert not result.allowed

    # -- Stats --

    def test_stats_tracking(self):
        from chat.guardrail import GuardrailFilter

        gf = GuardrailFilter()
        gf.check("hello")
        gf.check("/approve")
        gf.check("cancel my task")
        stats = gf.stats
        assert stats["checked"] == 3
        assert stats["blocked_command"] == 1
        assert stats["blocked_nlp"] == 1
        assert stats["allowed"] == 1


# =========================================================================
# Phase 4 — Task 4.3: ChatLogService Tests
# =========================================================================


class TestChatLogService:
    """Test ChatLogService singleton and interface."""

    def test_singleton(self):
        from chat.log_service import get_log_service

        svc1 = get_log_service()
        svc2 = get_log_service()
        assert svc1 is svc2

    def test_stats_initial(self):
        from chat.log_service import ChatLogService

        svc = ChatLogService()
        assert svc.stats["logged"] == 0
        assert svc.stats["errors"] == 0

    def test_service_has_required_methods(self):
        from chat.log_service import ChatLogService

        svc = ChatLogService()
        assert hasattr(svc, "log_message")
        assert hasattr(svc, "get_history")
        assert hasattr(svc, "get_blocked_attempts")
        assert callable(svc.log_message)
        assert callable(svc.get_history)
        assert callable(svc.get_blocked_attempts)


# =========================================================================
# Phase 4 — Task 4.4: Rate Limiter Tests
# =========================================================================


class TestRateLimiter:
    """Test per-user rate limiting."""

    def test_first_message_allowed(self):
        from chat.relay import _RateLimiter

        rl = _RateLimiter(per_second=1, per_hour=100)
        result = rl.check("user1", "task1")
        assert result is None

    def test_rapid_messages_blocked(self):
        from chat.relay import _RateLimiter

        rl = _RateLimiter(per_second=1, per_hour=100)
        rl.check("user1", "task1")  # first — allowed
        result = rl.check("user1", "task1")  # immediate second — blocked
        assert result is not None
        assert "wait" in result.lower()

    def test_different_users_independent(self):
        from chat.relay import _RateLimiter

        rl = _RateLimiter(per_second=1, per_hour=100)
        rl.check("user1", "task1")
        result = rl.check("user2", "task1")  # different user — allowed
        assert result is None

    def test_hourly_limit(self):
        from chat.relay import _RateLimiter

        rl = _RateLimiter(per_second=999, per_hour=3)  # high per-sec, low per-hour
        # Manually set timestamps to bypass per-second
        for i in range(3):
            rl._last_msg["user1"] = 0  # reset per-sec
            result = rl.check("user1", "task1")
            assert result is None, f"Message {i + 1} should be allowed"

        rl._last_msg["user1"] = 0  # reset per-sec
        result = rl.check("user1", "task1")  # 4th — blocked by hourly
        assert result is not None
        assert "limit" in result.lower()

    def test_hourly_limit_different_tasks_independent(self):
        from chat.relay import _RateLimiter

        rl = _RateLimiter(per_second=999, per_hour=2)
        for _ in range(2):
            rl._last_msg["user1"] = 0
            rl.check("user1", "task1")

        rl._last_msg["user1"] = 0
        result = rl.check("user1", "task2")  # different task — allowed
        assert result is None
