"""
Tests for the Chamba MCP WebSocket Server.

Run with: pytest mcp_server/tests/test_websocket.py -v
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from websocket import (
    WebSocketManager,
    WebSocketMessage,
    Connection,
    MessageType,
    ConnectionState,
    TaskNotifier,
)


# ============== FIXTURES ==============


@pytest.fixture
def ws_manager():
    """Create a fresh WebSocket manager for each test."""
    manager = WebSocketManager(
        heartbeat_interval=5.0,
        heartbeat_timeout=10.0,
        max_connections_per_agent=3,
    )
    return manager


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ============== MESSAGE TESTS ==============


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_create_message(self):
        """Test creating a basic message."""
        msg = WebSocketMessage(
            type=MessageType.PING,
            payload={"test": "data"}
        )
        assert msg.type == MessageType.PING
        assert msg.payload == {"test": "data"}
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = WebSocketMessage(
            type=MessageType.TASK_CREATED,
            payload={"task_id": "123"},
            id="test-id",
            correlation_id="corr-id"
        )
        data = msg.to_dict()

        assert data["type"] == "task_created"
        assert data["payload"]["task_id"] == "123"
        assert data["id"] == "test-id"
        assert data["correlation_id"] == "corr-id"

    def test_message_to_json(self):
        """Test converting message to JSON."""
        msg = WebSocketMessage(
            type=MessageType.PING,
            payload={}
        )
        json_str = msg.to_json()
        data = json.loads(json_str)

        assert data["type"] == "ping"
        assert "timestamp" in data

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "type": "pong",
            "payload": {"latency": 50},
            "id": "msg-123",
            "timestamp": "2026-01-25T10:00:00Z",
            "correlation_id": "req-456"
        }
        msg = WebSocketMessage.from_dict(data)

        assert msg.type == MessageType.PONG
        assert msg.payload["latency"] == 50
        assert msg.id == "msg-123"
        assert msg.correlation_id == "req-456"

    def test_message_from_dict_unknown_type(self):
        """Test handling unknown message type."""
        data = {"type": "unknown_type", "payload": {}}
        msg = WebSocketMessage.from_dict(data)

        assert msg.type == MessageType.ERROR


# ============== CONNECTION TESTS ==============


class TestConnection:
    """Tests for Connection dataclass."""

    def test_connection_creation(self, mock_websocket):
        """Test creating a connection."""
        conn = Connection(
            websocket=mock_websocket,
            connection_id="conn-123",
            agent_id="agent-456"
        )

        assert conn.connection_id == "conn-123"
        assert conn.agent_id == "agent-456"
        assert conn.state == ConnectionState.CONNECTING

    def test_is_authenticated(self, mock_websocket):
        """Test authentication check."""
        conn = Connection(
            websocket=mock_websocket,
            connection_id="conn-123",
        )
        assert not conn.is_authenticated

        conn.agent_id = "agent-456"
        conn.state = ConnectionState.AUTHENTICATED
        assert conn.is_authenticated


# ============== MANAGER TESTS ==============


class TestWebSocketManager:
    """Tests for WebSocketManager."""

    @pytest.mark.asyncio
    async def test_connect(self, ws_manager, mock_websocket):
        """Test accepting a new connection."""
        connection = await ws_manager.connect(mock_websocket, agent_id="agent-123")

        assert connection.connection_id in ws_manager._connections
        assert ws_manager.connection_count == 1
        assert ws_manager.agent_count == 1
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_without_agent(self, ws_manager, mock_websocket):
        """Test connection without initial authentication."""
        connection = await ws_manager.connect(mock_websocket)

        assert connection.agent_id is None
        assert connection.state == ConnectionState.CONNECTED
        assert not connection.is_authenticated

    @pytest.mark.asyncio
    async def test_disconnect(self, ws_manager, mock_websocket):
        """Test disconnecting a connection."""
        connection = await ws_manager.connect(mock_websocket, agent_id="agent-123")
        conn_id = connection.connection_id

        await ws_manager.disconnect(conn_id)

        assert conn_id not in ws_manager._connections
        assert ws_manager.connection_count == 0
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate(self, ws_manager, mock_websocket):
        """Test authenticating a connection."""
        connection = await ws_manager.connect(mock_websocket)
        conn_id = connection.connection_id

        result = await ws_manager.authenticate(conn_id, "agent-456")

        assert result is True
        assert connection.agent_id == "agent-456"
        assert connection.state == ConnectionState.AUTHENTICATED
        assert connection.is_authenticated

    @pytest.mark.asyncio
    async def test_max_connections_per_agent(self, ws_manager):
        """Test connection limit per agent."""
        agent_id = "agent-123"

        # Create max connections
        connections = []
        for _ in range(ws_manager.max_connections_per_agent):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            conn = await ws_manager.connect(mock_ws, agent_id=agent_id)
            connections.append(conn)

        # Try to create one more
        extra_ws = AsyncMock()
        extra_ws.accept = AsyncMock()
        extra_ws.send_text = AsyncMock()
        extra_ws.close = AsyncMock()

        with pytest.raises(Exception):  # HTTPException
            await ws_manager.connect(extra_ws, agent_id=agent_id)

        extra_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message(self, ws_manager, mock_websocket):
        """Test sending a message to a connection."""
        connection = await ws_manager.connect(mock_websocket)
        conn_id = connection.connection_id

        message = WebSocketMessage(
            type=MessageType.TASK_CREATED,
            payload={"task_id": "task-123"}
        )

        result = await ws_manager.send(conn_id, message)

        assert result is True
        # One for welcome, one for our message
        assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_send_to_agent(self, ws_manager):
        """Test sending to all connections of an agent."""
        agent_id = "agent-123"

        # Create two connections for same agent
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_text = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_text = AsyncMock()

        await ws_manager.connect(mock_ws1, agent_id=agent_id)
        await ws_manager.connect(mock_ws2, agent_id=agent_id)

        message = WebSocketMessage(
            type=MessageType.TASK_UPDATED,
            payload={"task_id": "task-456"}
        )

        sent = await ws_manager.send_to_agent(agent_id, message)

        assert sent == 2

    @pytest.mark.asyncio
    async def test_broadcast(self, ws_manager):
        """Test broadcasting to all connections."""
        # Create multiple connections
        connections = []
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            conn = await ws_manager.connect(mock_ws, agent_id=f"agent-{i}")
            connections.append(conn)

        message = WebSocketMessage(
            type=MessageType.BROADCAST,
            payload={"announcement": "Server update"}
        )

        sent = await ws_manager.broadcast(message)

        assert sent == 3

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self, ws_manager):
        """Test broadcasting with exclusions."""
        connections = []
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            conn = await ws_manager.connect(mock_ws, agent_id=f"agent-{i}")
            connections.append(conn)

        message = WebSocketMessage(type=MessageType.BROADCAST, payload={})
        exclude = {connections[0].connection_id}

        sent = await ws_manager.broadcast(message, exclude=exclude)

        assert sent == 2

    @pytest.mark.asyncio
    async def test_subscriptions(self, ws_manager, mock_websocket):
        """Test subscription management."""
        connection = await ws_manager.connect(mock_websocket)
        conn_id = connection.connection_id

        # Subscribe
        result = await ws_manager.subscribe(conn_id, "task:updates")
        assert result is True
        assert "task:updates" in connection.subscriptions

        # Unsubscribe
        result = await ws_manager.unsubscribe(conn_id, "task:updates")
        assert result is True
        assert "task:updates" not in connection.subscriptions

    @pytest.mark.asyncio
    async def test_broadcast_to_subscribers(self, ws_manager):
        """Test broadcasting to topic subscribers."""
        # Create connections with different subscriptions
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_text = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_text = AsyncMock()

        mock_ws3 = AsyncMock()
        mock_ws3.accept = AsyncMock()
        mock_ws3.send_text = AsyncMock()

        conn1 = await ws_manager.connect(mock_ws1, agent_id="agent-1")
        conn2 = await ws_manager.connect(mock_ws2, agent_id="agent-2")
        conn3 = await ws_manager.connect(mock_ws3, agent_id="agent-3")

        # Subscribe only first two to topic
        await ws_manager.subscribe(conn1.connection_id, "premium:updates")
        await ws_manager.subscribe(conn2.connection_id, "premium:updates")

        message = WebSocketMessage(
            type=MessageType.TASK_CREATED,
            payload={"premium": True}
        )

        sent = await ws_manager.broadcast_to_subscribers("premium:updates", message)

        assert sent == 2

    @pytest.mark.asyncio
    async def test_handle_ping_message(self, ws_manager, mock_websocket):
        """Test handling ping messages."""
        connection = await ws_manager.connect(mock_websocket)
        conn_id = connection.connection_id

        # Reset mock to clear welcome message
        mock_websocket.send_text.reset_mock()

        ping_message = json.dumps({
            "type": "ping",
            "payload": {},
            "id": "ping-123"
        })

        await ws_manager.handle_message(conn_id, ping_message)

        # Should have sent pong
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "pong"
        assert sent_data["correlation_id"] == "ping-123"

    @pytest.mark.asyncio
    async def test_handle_invalid_message(self, ws_manager, mock_websocket):
        """Test handling invalid messages."""
        connection = await ws_manager.connect(mock_websocket)
        conn_id = connection.connection_id

        mock_websocket.send_text.reset_mock()

        await ws_manager.handle_message(conn_id, "not valid json")

        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "error"

    @pytest.mark.asyncio
    async def test_event_handler_registration(self, ws_manager, mock_websocket):
        """Test registering and calling event handlers."""
        handler_called = []

        async def test_handler(conn: Connection, msg: WebSocketMessage):
            handler_called.append((conn.connection_id, msg.type))

        ws_manager.on(MessageType.MCP_REQUEST, test_handler)

        connection = await ws_manager.connect(mock_websocket, agent_id="agent-123")
        conn_id = connection.connection_id

        mcp_message = json.dumps({
            "type": "mcp_request",
            "payload": {"method": "test"}
        })

        await ws_manager.handle_message(conn_id, mcp_message)

        assert len(handler_called) == 1
        assert handler_called[0][0] == conn_id
        assert handler_called[0][1] == MessageType.MCP_REQUEST

    @pytest.mark.asyncio
    async def test_get_stats(self, ws_manager, mock_websocket):
        """Test getting manager statistics."""
        await ws_manager.connect(mock_websocket, agent_id="agent-123")

        stats = ws_manager.get_stats()

        assert stats["total_connections"] == 1
        assert stats["unique_agents"] == 1
        assert "connections_by_state" in stats

    @pytest.mark.asyncio
    async def test_start_stop(self, ws_manager):
        """Test starting and stopping the manager."""
        await ws_manager.start()
        assert ws_manager._running is True
        assert ws_manager._heartbeat_task is not None

        await ws_manager.stop()
        assert ws_manager._running is False


# ============== TASK NOTIFIER TESTS ==============


class TestTaskNotifier:
    """Tests for TaskNotifier helper."""

    @pytest.fixture
    def notifier(self, ws_manager):
        """Create a task notifier."""
        return TaskNotifier(ws_manager)

    @pytest.mark.asyncio
    async def test_task_created_notification(self, notifier, ws_manager):
        """Test task created notification."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        # Create authenticated connection
        await ws_manager.connect(mock_ws, agent_id="agent-123")

        task = {"id": "task-123", "title": "Test Task", "bounty_usd": 10.0}
        sent = await notifier.task_created(task)

        assert sent == 1

    @pytest.mark.asyncio
    async def test_task_updated_notification(self, notifier, ws_manager):
        """Test task updated notification to specific agent."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        await ws_manager.connect(mock_ws, agent_id="agent-123")
        mock_ws.send_text.reset_mock()

        task = {"id": "task-123", "title": "Updated Task"}
        sent = await notifier.task_updated(task, "agent-123")

        assert sent == 1
        sent_data = json.loads(mock_ws.send_text.call_args[0][0])
        assert sent_data["type"] == "task_updated"

    @pytest.mark.asyncio
    async def test_submission_received_notification(self, notifier, ws_manager):
        """Test submission notification."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        await ws_manager.connect(mock_ws, agent_id="agent-123")
        mock_ws.send_text.reset_mock()

        task = {"id": "task-123", "title": "Test Task"}
        submission = {"id": "sub-456", "evidence": {}}

        sent = await notifier.submission_received(task, submission, "agent-123")

        assert sent == 1
        sent_data = json.loads(mock_ws.send_text.call_args[0][0])
        assert sent_data["type"] == "submission_received"
        assert sent_data["payload"]["task"]["id"] == "task-123"


# ============== INTEGRATION TESTS ==============


class TestIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, ws_manager):
        """Test complete connection lifecycle."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()

        # Connect
        connection = await ws_manager.connect(mock_ws)
        assert ws_manager.connection_count == 1

        # Authenticate
        await ws_manager.authenticate(connection.connection_id, "agent-123")
        assert connection.is_authenticated

        # Subscribe
        await ws_manager.subscribe(connection.connection_id, "tasks:new")
        assert "tasks:new" in connection.subscriptions

        # Send message
        msg = WebSocketMessage(type=MessageType.TASK_CREATED, payload={})
        await ws_manager.send(connection.connection_id, msg)

        # Disconnect
        await ws_manager.disconnect(connection.connection_id)
        assert ws_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_multiple_agents_isolation(self, ws_manager):
        """Test that agents are properly isolated."""
        # Create connections for two different agents
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_text = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_text = AsyncMock()

        conn1 = await ws_manager.connect(mock_ws1, agent_id="agent-1")
        conn2 = await ws_manager.connect(mock_ws2, agent_id="agent-2")

        # Reset mocks
        mock_ws1.send_text.reset_mock()
        mock_ws2.send_text.reset_mock()

        # Send to agent-1 only
        msg = WebSocketMessage(type=MessageType.TASK_UPDATED, payload={})
        await ws_manager.send_to_agent("agent-1", msg)

        # Only agent-1 should receive
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_not_called()
