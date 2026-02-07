"""
Focused tests for WebSocket auth hardening.
"""

from unittest.mock import AsyncMock

import pytest

from ..websocket.server import WebSocketManager, ConnectionState


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.messages = []
        self.close_code = None
        self.close_reason = None

    async def accept(self):
        self.accepted = True

    async def send_text(self, message: str):
        self.messages.append(message)

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True
        self.close_code = code
        self.close_reason = reason


@pytest.mark.asyncio
async def test_connection_context_accepts_user_type_argument():
    manager = WebSocketManager()
    ws = FakeWebSocket()

    async with manager.connection_context(
        ws, user_id="agent_1", user_type="agent"
    ) as conn:
        assert conn.user_id == "agent_1"
        assert conn.user_type == "agent"
        assert conn.state == ConnectionState.AUTHENTICATED


@pytest.mark.asyncio
async def test_authenticate_rejects_invalid_token():
    manager = WebSocketManager()
    ws = FakeWebSocket()
    conn = await manager.connect(ws)
    manager._validate_api_token = AsyncMock(return_value=None)

    ok = await manager.authenticate(
        connection_id=conn.connection_id,
        user_id="agent_1",
        user_type="agent",
        token="bad-token",
    )

    assert ok is False
    assert conn.state != ConnectionState.AUTHENTICATED


@pytest.mark.asyncio
async def test_authenticate_accepts_valid_token_and_prevents_spoofing():
    manager = WebSocketManager()
    ws = FakeWebSocket()
    conn = await manager.connect(ws)
    manager._validate_api_token = AsyncMock(
        return_value={"user_id": "agent_real", "user_type": "agent", "tier": "free"}
    )

    ok = await manager.authenticate(
        connection_id=conn.connection_id,
        user_id="spoofed_user",
        user_type="agent",
        token="valid-token",
    )

    assert ok is True
    assert conn.user_id == "agent_real"
    assert conn.user_type == "agent"
    assert conn.state == ConnectionState.AUTHENTICATED


@pytest.mark.asyncio
async def test_authenticate_requires_token_when_strict_mode_enabled():
    manager = WebSocketManager()
    manager.require_auth_token = True
    ws = FakeWebSocket()
    conn = await manager.connect(ws)

    ok = await manager.authenticate(
        connection_id=conn.connection_id,
        user_id="agent_1",
        user_type="agent",
        token=None,
    )

    assert ok is False
    assert conn.state == ConnectionState.CONNECTED


@pytest.mark.asyncio
async def test_validate_room_access_blocks_other_user_room():
    manager = WebSocketManager()
    ws = FakeWebSocket()
    conn = await manager.connect(ws, user_id="agent_1", user_type="agent")

    allowed = await manager._validate_room_access(conn, "user:agent_2")

    assert allowed is False


@pytest.mark.asyncio
async def test_validate_room_access_checks_task_acl_for_uuid_rooms():
    manager = WebSocketManager()
    ws = FakeWebSocket()
    conn = await manager.connect(ws, user_id="agent_1", user_type="agent")
    manager._can_access_task_room = AsyncMock(return_value=False)

    allowed = await manager._validate_room_access(
        conn,
        "task:77777777-7777-7777-7777-777777777777",
    )

    assert allowed is False
    manager._can_access_task_room.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_room_access_allows_non_uuid_task_room_for_compat():
    manager = WebSocketManager()
    ws = FakeWebSocket()
    conn = await manager.connect(ws, user_id="agent_1", user_type="agent")

    allowed = await manager._validate_room_access(conn, "task:demo-room")

    assert allowed is True
