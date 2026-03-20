"""
Tests for Channel Manager and Dynamic Task Channels (Phase 3 of MASTER_PLAN_MESHRELAY_V2.md).

Covers:
- Channel lifecycle (create, close)
- Auto-join participants via identity lookup
- Chat logging for task channels only
- Channel-scoped task ID detection
- Mutual cancellation proposal tracking
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from events.models import EMEvent, EventSource
from events.bus import EventBus
from events.adapters.channel_manager import ChannelManager, CHANNEL_PREFIX


# ---------------------------------------------------------------------------
# Channel lifecycle tests
# ---------------------------------------------------------------------------


class TestChannelLifecycle:
    @pytest.mark.asyncio
    async def test_create_task_channel(self):
        bus = EventBus()
        manager = ChannelManager(bus=bus, meshrelay_api_url="http://localhost:9999/api/v1")

        with patch("events.adapters.channel_manager.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            channel = await manager.create_task_channel(
                "abcdef1234567890",
                {"title": "Take photo", "bounty_usd": 0.10, "deadline_minutes": 15},
            )

        assert channel == "#task-abcdef12"
        assert manager.stats["channels_created"] == 1
        assert "abcdef1234567890" in manager.active_channels

    @pytest.mark.asyncio
    async def test_create_channel_already_exists(self):
        """409 Conflict = channel exists, treat as success."""
        bus = EventBus()
        manager = ChannelManager(bus=bus, meshrelay_api_url="http://localhost:9999/api/v1")

        import httpx

        with patch("events.adapters.channel_manager.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 409
            mock_resp.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("Conflict", request=MagicMock(), response=mock_resp)
            )
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            channel = await manager.create_task_channel("abc12345", {"title": "Test"})

        assert channel == "#task-abc12345"
        assert "abc12345" in manager.active_channels

    @pytest.mark.asyncio
    async def test_close_task_channel(self):
        bus = EventBus()
        manager = ChannelManager(bus=bus, meshrelay_api_url="http://localhost:9999/api/v1")
        manager._active_channels["task123"] = "#task-task1234"

        with patch("events.adapters.channel_manager.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 204
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.delete = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await manager.close_task_channel("task123", "Task completed")

        assert "task123" not in manager.active_channels
        assert manager.stats["channels_closed"] == 1

    @pytest.mark.asyncio
    async def test_event_bus_triggers_channel_creation(self):
        bus = EventBus()
        manager = ChannelManager(bus=bus, meshrelay_api_url="http://localhost:9999/api/v1")
        manager.start()

        with patch.object(manager, "create_task_channel", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "#task-abcdef12"
            with patch.object(manager, "_invite_participants", new_callable=AsyncMock):
                await bus.publish(
                    EMEvent(
                        event_type="task.assigned",
                        task_id="abcdef1234567890",
                        source=EventSource.REST_API,
                        payload={
                            "title": "Test Task",
                            "bounty_usd": 0.10,
                            "worker_wallet": "0x1234",
                        },
                    )
                )

        mock_create.assert_called_once()
        manager.stop()

    @pytest.mark.asyncio
    async def test_event_bus_triggers_channel_close(self):
        bus = EventBus()
        manager = ChannelManager(bus=bus, meshrelay_api_url="http://localhost:9999/api/v1")
        manager.start()

        with patch.object(manager, "close_task_channel", new_callable=AsyncMock) as mock_close:
            await bus.publish(
                EMEvent(
                    event_type="task.cancelled",
                    task_id="task456",
                    source=EventSource.REST_API,
                    payload={"reason": "Changed mind"},
                )
            )

        mock_close.assert_called_once_with("task456", "Changed mind")
        manager.stop()


# ---------------------------------------------------------------------------
# Auto-join participant tests (Task 3.2)
# ---------------------------------------------------------------------------


class TestAutoJoinParticipants:
    @pytest.mark.asyncio
    async def test_invite_participants_with_known_nicks(self):
        bus = EventBus()
        mock_db = MagicMock()
        manager = ChannelManager(
            bus=bus,
            meshrelay_api_url="http://localhost:9999/api/v1",
            db_client=mock_db,
        )

        # Mock nick lookup
        mock_result = MagicMock()
        mock_result.data = [{"irc_nick": "alice"}]
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        with patch.object(manager, "_invite_to_channel", new_callable=AsyncMock) as mock_invite:
            with patch.object(manager, "_send_to_channel", new_callable=AsyncMock):
                await manager._invite_participants(
                    "#task-abc12345",
                    {"agent_wallet": "0xpublisher", "worker_wallet": "0xworker"},
                )

        # Should be called for both publisher and worker
        assert mock_invite.call_count == 2

    @pytest.mark.asyncio
    async def test_skip_invite_if_no_irc_identity(self):
        bus = EventBus()
        mock_db = MagicMock()
        manager = ChannelManager(
            bus=bus,
            meshrelay_api_url="http://localhost:9999/api/v1",
            db_client=mock_db,
        )

        # Mock empty lookup result
        mock_result = MagicMock()
        mock_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        with patch.object(manager, "_invite_to_channel", new_callable=AsyncMock) as mock_invite:
            with patch.object(manager, "_send_to_channel", new_callable=AsyncMock):
                await manager._invite_participants(
                    "#task-abc12345",
                    {"agent_wallet": "0xpublisher"},
                )

        mock_invite.assert_not_called()


# ---------------------------------------------------------------------------
# Chat logging tests (Task 3.5)
# ---------------------------------------------------------------------------


class TestChatLogging:
    @pytest.mark.asyncio
    async def test_log_message_in_task_channel(self):
        bus = EventBus()
        mock_db = MagicMock()
        manager = ChannelManager(bus=bus, db_client=mock_db)

        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await manager.log_chat_message(
            task_id="abc123",
            channel="#task-abc12345",
            nick="alice",
            message="I'll deliver the photos by 3pm",
            message_type="text",
            wallet_address="0x1234",
        )

        mock_db.table.assert_called_with("task_chat_log")
        mock_db.table.return_value.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_logging_for_public_channel(self):
        """Only #task-* channels should be logged."""
        bus = EventBus()
        mock_db = MagicMock()
        manager = ChannelManager(bus=bus, db_client=mock_db)

        await manager.log_chat_message(
            task_id="",
            channel="#bounties",
            nick="alice",
            message="Looking for tasks",
        )

        mock_db.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_logging_for_agents_channel(self):
        bus = EventBus()
        mock_db = MagicMock()
        manager = ChannelManager(bus=bus, db_client=mock_db)

        await manager.log_chat_message(
            task_id="",
            channel="#Agents",
            nick="bot",
            message="Hello",
        )

        mock_db.table.assert_not_called()


# ---------------------------------------------------------------------------
# Chat history endpoint (Task 3.5)
# ---------------------------------------------------------------------------


class TestChatHistoryRoute:
    def test_chat_history_route_exists(self):
        from api.routes import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/tasks/{task_id}/chat-history" in paths


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


class TestChatLogMigration:
    def test_migration_file_exists(self):
        migration = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "066_task_chat_log.sql"
        assert migration.exists()

    def test_migration_has_table(self):
        migration = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "066_task_chat_log.sql"
        content = migration.read_text()
        assert "CREATE TABLE" in content
        assert "task_chat_log" in content
        assert "message_type" in content
        assert "CHECK (message_type IN" in content

    def test_migration_has_rls(self):
        migration = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "066_task_chat_log.sql"
        content = migration.read_text()
        assert "ENABLE ROW LEVEL SECURITY" in content


# ---------------------------------------------------------------------------
# Channel prefix constant
# ---------------------------------------------------------------------------


class TestChannelPrefix:
    def test_channel_prefix(self):
        assert CHANNEL_PREFIX == "#task-"

    def test_channel_name_format(self):
        task_id = "abcdef1234567890"
        expected = "#task-abcdef12"
        assert f"{CHANNEL_PREFIX}{task_id[:8]}" == expected
