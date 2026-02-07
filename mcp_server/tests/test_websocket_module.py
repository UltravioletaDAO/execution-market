"""
Tests for the Execution Market WebSocket Module (New Modular Structure)

Tests the websocket/ directory components:
- server.py: Connection manager and WebSocket endpoint
- events.py: Event types and payloads
- handlers.py: Event broadcasting
- client.py: Python client
- integration.py: Integration helpers

Run with: pytest mcp_server/tests/test_websocket_module.py -v
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

# Import from the new websocket module
from websocket import (
    # Server
    WebSocketManager,
    ServerMessage,
    ServerMessageType,
    WebSocketEventType,
    WebSocketEvent,
    TaskCreatedPayload,
    TaskUpdatedPayload,
    SubmissionReceivedPayload,
    PaymentReleasedPayload,
    NotificationNewPayload,
    get_task_room,
    get_user_room,
    get_category_room,
    # Handlers
    EventHandlers,
    EventRateLimiter,
    EventEmitter,
    emit_event,
    is_websocket_available,
)


# ============== FIXTURES ==============


@pytest.fixture
def ws_manager_instance():
    """Create a fresh WebSocket manager for each test."""
    manager = WebSocketManager(
        heartbeat_interval=5.0,
        heartbeat_timeout=10.0,
        max_connections_per_user=3,
        max_subscriptions_per_connection=10,
        rate_limit_messages=50,
        rate_limit_window_seconds=60,
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


@pytest.fixture
def sample_task():
    """Sample task data for testing."""
    return {
        "id": "task-123-uuid",
        "title": "Verify Store Hours",
        "category": "physical_presence",
        "bounty_usd": 10.0,
        "deadline": "2026-01-26T18:00:00Z",
        "agent_id": "agent-456",
        "executor_id": None,
        "status": "published",
        "location_hint": "123 Main St, Miami",
        "min_reputation": 0,
        "evidence_required": ["photo_geo", "text_response"],
        "payment_token": "USDC",
    }


@pytest.fixture
def sample_submission():
    """Sample submission data for testing."""
    return {
        "id": "sub-789-uuid",
        "task_id": "task-123-uuid",
        "executor_id": "worker-111",
        "evidence": {
            "photo_geo": "ipfs://Qm...",
            "text_response": "Store is open, 5 people in line",
        },
        "submitted_at": "2026-01-25T14:00:00Z",
        "agent_verdict": "pending",
        "verification_score": 0.85,
    }


# ============== EVENT TESTS ==============


class TestWebSocketEvents:
    """Tests for WebSocket event types and payloads."""

    def test_task_created_payload(self, sample_task):
        """Test creating TaskCreatedPayload."""
        payload = TaskCreatedPayload(
            task_id=sample_task["id"],
            title=sample_task["title"],
            category=sample_task["category"],
            bounty_usd=sample_task["bounty_usd"],
            deadline=sample_task["deadline"],
            agent_id=sample_task["agent_id"],
            location_hint=sample_task["location_hint"],
        )

        data = payload.to_dict()
        assert data["task_id"] == "task-123-uuid"
        assert data["bounty_usd"] == 10.0
        assert data["category"] == "physical_presence"

    def test_websocket_event_to_json(self, sample_task):
        """Test WebSocketEvent JSON serialization."""
        payload = TaskCreatedPayload(
            task_id=sample_task["id"],
            title=sample_task["title"],
            category=sample_task["category"],
            bounty_usd=sample_task["bounty_usd"],
            deadline=sample_task["deadline"],
            agent_id=sample_task["agent_id"],
        )

        event = WebSocketEvent.task_created(payload)

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["event"] == "TaskCreated"
        assert "payload" in data
        assert "metadata" in data
        assert data["metadata"]["version"] == "1.0"

    def test_event_from_dict(self):
        """Test creating WebSocketEvent from dictionary."""
        data = {
            "event": "TaskUpdated",
            "payload": {"task_id": "123", "status": "completed"},
            "room": "task:123",
        }

        event = WebSocketEvent.from_dict(data)

        assert event.event_type == WebSocketEventType.TASK_UPDATED
        assert event.payload["status"] == "completed"
        assert event.room == "task:123"

    def test_room_utilities(self):
        """Test room name generation utilities."""
        assert get_task_room("123") == "task:123"
        assert get_user_room("agent-456") == "user:agent-456"
        assert get_category_room("physical_presence") == "category:physical_presence"


# ============== SERVER TESTS ==============


class TestWebSocketManager:
    """Tests for the new WebSocketManager."""

    @pytest.mark.asyncio
    async def test_connect(self, ws_manager_instance, mock_websocket):
        """Test accepting a new connection."""
        connection = await ws_manager_instance.connect(
            mock_websocket, user_id="agent-123", user_type="agent"
        )

        assert connection.connection_id in ws_manager_instance._connections
        assert ws_manager_instance.connection_count == 1
        assert ws_manager_instance.user_count == 1
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_text.assert_called_once()  # Welcome message

    @pytest.mark.asyncio
    async def test_connect_auto_subscribes_to_user_room(
        self, ws_manager_instance, mock_websocket
    ):
        """Test that authenticated connections auto-subscribe to user room."""
        connection = await ws_manager_instance.connect(
            mock_websocket, user_id="agent-123", user_type="agent"
        )

        assert "user:agent-123" in connection.subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_to_room(self, ws_manager_instance, mock_websocket):
        """Test subscribing to a room."""
        connection = await ws_manager_instance.connect(
            mock_websocket, user_id="agent-123"
        )

        await ws_manager_instance.subscribe(connection.connection_id, "task:456")

        assert "task:456" in connection.subscriptions
        assert (
            connection.connection_id
            in ws_manager_instance._room_connections["task:456"]
        )

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, ws_manager_instance):
        """Test broadcasting to room subscribers."""
        # Create two connections subscribed to same room
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_text = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_text = AsyncMock()

        conn1 = await ws_manager_instance.connect(mock_ws1, user_id="agent-1")
        conn2 = await ws_manager_instance.connect(mock_ws2, user_id="agent-2")

        await ws_manager_instance.subscribe(conn1.connection_id, "task:123")
        await ws_manager_instance.subscribe(conn2.connection_id, "task:123")

        # Reset to clear previous messages
        mock_ws1.send_text.reset_mock()
        mock_ws2.send_text.reset_mock()

        # Create and broadcast event
        payload = TaskUpdatedPayload(task_id="123", status="completed")
        event = WebSocketEvent.task_updated(payload, "task:123")

        sent = await ws_manager_instance.broadcast_to_room("task:123", event)

        assert sent == 2
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_user(self, ws_manager_instance):
        """Test sending event to specific user."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        await ws_manager_instance.connect(mock_ws, user_id="agent-123")
        mock_ws.send_text.reset_mock()

        payload = NotificationNewPayload(
            notification_id="notif-1",
            type="task_update",
            title="Task Completed",
            message="Your task has been completed",
        )
        event = WebSocketEvent.notification(payload, "agent-123")

        sent = await ws_manager_instance.send_to_user("agent-123", event)

        assert sent == 1
        mock_ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, ws_manager_instance, mock_websocket):
        """Test that rate limiting works."""
        # Set very low rate limit for testing
        ws_manager_instance.rate_limit_messages = 3
        ws_manager_instance.rate_limit_window_seconds = 60

        connection = await ws_manager_instance.connect(mock_websocket)

        # Should allow first few messages
        for i in range(3):
            await ws_manager_instance.handle_message(
                connection.connection_id, json.dumps({"type": "ping", "payload": {}})
            )

        # Next message should be rate limited
        mock_websocket.send_text.reset_mock()
        await ws_manager_instance.handle_message(
            connection.connection_id, json.dumps({"type": "ping", "payload": {}})
        )

        # Should receive error message about rate limiting
        calls = mock_websocket.send_text.call_args_list
        last_call = json.loads(calls[-1][0][0])
        assert last_call["type"] == "error"
        assert "rate" in last_call["payload"]["error"].lower()

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, ws_manager_instance, mock_websocket):
        """Test that disconnect cleans up properly."""
        connection = await ws_manager_instance.connect(
            mock_websocket, user_id="agent-123"
        )
        await ws_manager_instance.subscribe(connection.connection_id, "task:456")

        conn_id = connection.connection_id

        await ws_manager_instance.disconnect(conn_id)

        assert conn_id not in ws_manager_instance._connections
        assert "agent-123" not in ws_manager_instance._user_connections
        assert conn_id not in ws_manager_instance._room_connections.get(
            "task:456", set()
        )


# ============== HANDLER TESTS ==============


class TestEventHandlers:
    """Tests for event handlers."""

    @pytest.fixture
    def handlers_instance(self):
        """Create fresh handlers instance."""
        return EventHandlers()

    @pytest.mark.asyncio
    async def test_task_created_handler(
        self, handlers_instance, sample_task, ws_manager_instance, mock_websocket
    ):
        """Test task_created handler broadcasts correctly."""
        # Need to patch the global ws_manager
        with patch("websocket.handlers.ws_manager", ws_manager_instance):
            # Connect a user
            await ws_manager_instance.connect(
                mock_websocket, user_id=sample_task["agent_id"]
            )
            mock_websocket.send_text.reset_mock()

            # Emit task created event
            sent = await handlers_instance.task_created(sample_task)

            # Should have sent to agent's user room
            assert sent >= 1

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test event rate limiter."""
        limiter = EventRateLimiter()
        limiter._config.cooldown_seconds = 0

        user_id = "agent-123"
        event_type = "TaskCreated"

        # First events should be allowed
        for _ in range(5):
            assert limiter.check_and_record(user_id, event_type) is True

        # After hitting limit, should be blocked
        limiter._minute_counts[user_id][event_type] = 100
        assert limiter.check_and_record(user_id, event_type) is False


# ============== INTEGRATION TESTS ==============


class TestIntegration:
    """Tests for integration module."""

    def test_event_emitter_lazy_loading(self):
        """Test that EventEmitter loads handlers lazily."""
        emitter = EventEmitter()
        assert emitter._initialized is False

        # Calling available triggers initialization
        _ = emitter.available
        assert emitter._initialized is True

    @pytest.mark.asyncio
    async def test_emit_event_function(self, sample_task):
        """Test emit_event convenience function."""
        # This will use the global events emitter
        sent = await emit_event("task_created", task=sample_task)

        # Should return 0 or more depending on connections
        assert isinstance(sent, int)

    def test_is_websocket_available(self):
        """Test availability check."""
        result = is_websocket_available()
        # Should be True since we can import the module
        assert isinstance(result, bool)


# ============== MESSAGE FORMAT TESTS ==============


class TestMessageFormats:
    """Tests for message serialization formats."""

    def test_server_message_format(self):
        """Test ServerMessage serialization."""
        msg = ServerMessage(
            type=ServerMessageType.EVENT,
            payload={"task_id": "123", "status": "completed"},
        )

        data = msg.to_dict()

        assert data["type"] == "event"
        assert data["payload"]["task_id"] == "123"
        assert "id" in data
        assert "timestamp" in data

    def test_server_message_json(self):
        """Test ServerMessage JSON output."""
        msg = ServerMessage(
            type=ServerMessageType.SUBSCRIBED,
            payload={"room": "task:123", "total_subscriptions": 2},
        )

        json_str = msg.to_json()
        data = json.loads(json_str)

        assert data["type"] == "subscribed"
        assert data["payload"]["room"] == "task:123"


# ============== PAYLOAD TESTS ==============


class TestPayloads:
    """Tests for various event payloads."""

    def test_submission_received_payload(self, sample_submission, sample_task):
        """Test SubmissionReceivedPayload."""
        payload = SubmissionReceivedPayload(
            submission_id=sample_submission["id"],
            task_id=sample_submission["task_id"],
            task_title=sample_task["title"],
            worker_id=sample_submission["executor_id"],
            evidence_types=list(sample_submission["evidence"].keys()),
            submitted_at=sample_submission["submitted_at"],
            auto_verification_score=sample_submission["verification_score"],
        )

        data = payload.to_dict()

        assert data["submission_id"] == "sub-789-uuid"
        assert data["evidence_types"] == ["photo_geo", "text_response"]
        assert data["auto_verification_score"] == 0.85

    def test_payment_released_payload(self):
        """Test PaymentReleasedPayload."""
        payload = PaymentReleasedPayload(
            payment_id="pay-001",
            task_id="task-123",
            amount_usd=10.0,
            worker_amount=9.2,
            platform_fee=0.8,
            recipient_wallet="0x1234...",
            tx_hash="0xabcd...",
            token="USDC",
            chain="base",
        )

        data = payload.to_dict()

        assert data["amount_usd"] == 10.0
        assert data["worker_amount"] == 9.2
        assert data["platform_fee"] == 0.8
        assert data["tx_hash"] == "0xabcd..."

    def test_notification_payload(self):
        """Test NotificationNewPayload."""
        payload = NotificationNewPayload(
            notification_id="notif-001",
            type="payment",
            title="Payment Received",
            message="You received $9.20 for completing 'Verify Store Hours'",
            task_id="task-123",
            priority="high",
        )

        data = payload.to_dict()

        assert data["type"] == "payment"
        assert data["priority"] == "high"
        assert data["task_id"] == "task-123"
