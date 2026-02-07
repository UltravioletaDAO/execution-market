"""
Compatibility smoke tests for the current modular WebSocket API.

This file intentionally keeps a compact set of checks so collection does not
drift when the websocket package evolves.
"""

import json
from unittest.mock import AsyncMock

import pytest

from websocket import (
    WebSocketManager,
    ConnectionState,
    WebSocketEvent,
    TaskUpdatedPayload,
)


@pytest.fixture
def manager() -> WebSocketManager:
    return WebSocketManager(
        heartbeat_interval=5.0,
        heartbeat_timeout=10.0,
        max_connections_per_user=3,
        max_subscriptions_per_connection=10,
    )


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_establishes_authenticated_state(
    manager: WebSocketManager, mock_websocket
):
    conn = await manager.connect(mock_websocket, user_id="agent-123", user_type="agent")

    assert conn.state == ConnectionState.AUTHENTICATED
    assert conn.connection_id in manager._connections
    assert "user:agent-123" in conn.subscriptions


@pytest.mark.asyncio
async def test_subscribe_task_room_and_broadcast(manager: WebSocketManager):
    ws_1 = AsyncMock()
    ws_1.accept = AsyncMock()
    ws_1.send_text = AsyncMock()
    ws_1.close = AsyncMock()

    ws_2 = AsyncMock()
    ws_2.accept = AsyncMock()
    ws_2.send_text = AsyncMock()
    ws_2.close = AsyncMock()

    conn_1 = await manager.connect(ws_1, user_id="agent-1", user_type="agent")
    conn_2 = await manager.connect(ws_2, user_id="agent-2", user_type="agent")

    await manager.subscribe(conn_1.connection_id, "task:demo-room")
    await manager.subscribe(conn_2.connection_id, "task:demo-room")

    payload = TaskUpdatedPayload(task_id="demo-room", status="accepted")
    event = WebSocketEvent.task_updated(payload, "task:demo-room")
    sent = await manager.broadcast_to_room("task:demo-room", event)

    assert sent == 2


@pytest.mark.asyncio
async def test_handle_ping_message_sends_pong(
    manager: WebSocketManager, mock_websocket
):
    conn = await manager.connect(mock_websocket)
    mock_websocket.send_text.reset_mock()

    await manager.handle_message(
        conn.connection_id,
        json.dumps({"type": "ping", "payload": {}, "id": "ping-1"}),
    )

    mock_websocket.send_text.assert_called_once()
    body = json.loads(mock_websocket.send_text.call_args[0][0])
    assert body["type"] == "pong"
    assert body["correlation_id"] == "ping-1"
