"""
WebSocket Server for Execution Market Real-Time Updates

Provides a FastAPI WebSocket endpoint with:
- Connection management for multiple clients
- Room-based subscriptions (task:123, user:456)
- Heartbeat/ping-pong for connection health
- Reconnection handling
- Rate limiting per connection

Usage:
    from websocket.server import ws_router, ws_manager
    app.include_router(ws_router)
"""

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any, Callable, Awaitable, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from .events import WebSocketEvent, WebSocketEventType, get_user_room, get_task_room

# Configure logging
logger = logging.getLogger(__name__)


# ============== ENUMS & TYPES ==============


class ConnectionState(str, Enum):
    """State of a WebSocket connection."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class ClientMessageType(str, Enum):
    """Types of messages clients can send."""
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    PONG = "pong"
    AUTH = "auth"


class ServerMessageType(str, Enum):
    """Types of messages server sends."""
    WELCOME = "welcome"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    PING = "ping"
    PONG = "pong"
    EVENT = "event"
    ERROR = "error"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"


# ============== DATA MODELS ==============


@dataclass
class Connection:
    """Represents a single WebSocket connection."""
    websocket: WebSocket
    connection_id: str
    user_id: Optional[str] = None
    user_type: Optional[str] = None  # "agent" or "worker"
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_pong: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    rate_limit_window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    messages_in_window: int = 0

    @property
    def is_authenticated(self) -> bool:
        """Check if connection is authenticated."""
        return self.state == ConnectionState.AUTHENTICATED and self.user_id is not None

    @property
    def latency_ms(self) -> float:
        """Calculate latency from last ping/pong."""
        return (self.last_pong - self.last_ping).total_seconds() * 1000

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)


@dataclass
class ServerMessage:
    """Standard server message format."""
    type: ServerMessageType
    payload: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: secrets.token_hex(8))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "payload": self.payload,
            "id": self.id,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


# ============== WEBSOCKET MANAGER ==============


class WebSocketManager:
    """
    Manages WebSocket connections for the Execution Market MCP server.

    Features:
    - Connection lifecycle management
    - Room-based subscriptions (task:123, user:456, category:physical)
    - Heartbeat monitoring
    - Rate limiting
    - Authentication validation
    - Event broadcasting
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0,
        max_connections_per_user: int = 5,
        max_subscriptions_per_connection: int = 50,
        rate_limit_messages: int = 100,
        rate_limit_window_seconds: int = 60,
    ):
        """
        Initialize the WebSocket manager.

        Args:
            heartbeat_interval: Seconds between ping messages
            heartbeat_timeout: Seconds before considering connection dead
            max_connections_per_user: Max concurrent connections per user
            max_subscriptions_per_connection: Max rooms a connection can subscribe to
            rate_limit_messages: Max messages per rate limit window
            rate_limit_window_seconds: Rate limit window size in seconds
        """
        # Connection storage
        self._connections: Dict[str, Connection] = {}
        self._user_connections: Dict[str, Set[str]] = defaultdict(set)
        self._room_connections: Dict[str, Set[str]] = defaultdict(set)

        # Configuration
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_connections_per_user = max_connections_per_user
        self.max_subscriptions_per_connection = max_subscriptions_per_connection
        self.rate_limit_messages = rate_limit_messages
        self.rate_limit_window_seconds = rate_limit_window_seconds
        self.require_auth_token = os.environ.get("WS_REQUIRE_AUTH_TOKEN", "false").lower() == "true"

        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)

        logger.info("WebSocketManager initialized")

    # ============== LIFECYCLE ==============

    async def start(self) -> None:
        """Start the manager and background tasks."""
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("WebSocketManager started")

    async def stop(self) -> None:
        """Stop the manager and cleanup."""
        self._running = False

        # Cancel background tasks
        for task in [self._heartbeat_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close all connections
        for conn_id in list(self._connections.keys()):
            await self.disconnect(conn_id, reason="Server shutdown")

        logger.info("WebSocketManager stopped")

    @asynccontextmanager
    async def connection_context(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None,
    ):
        """Context manager for handling connection lifecycle."""
        connection = await self.connect(websocket, user_id, user_type)
        try:
            yield connection
        finally:
            await self.disconnect(connection.connection_id)

    # ============== CONNECTION MANAGEMENT ==============

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Connection:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket instance
            user_id: Optional user identifier (can be set later via auth)
            user_type: Optional user type ("agent" or "worker")
            metadata: Optional connection metadata

        Returns:
            Connection object for the new connection
        """
        # Generate connection ID
        connection_id = f"ws_{secrets.token_hex(12)}"

        # Check connection limits for user
        if user_id:
            existing = self._user_connections.get(user_id, set())
            if len(existing) >= self.max_connections_per_user:
                await websocket.close(code=4002, reason="Too many connections")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Max {self.max_connections_per_user} connections per user"
                )

        # Accept the WebSocket connection
        await websocket.accept()

        # Create connection record
        connection = Connection(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            user_type=user_type,
            state=ConnectionState.CONNECTED if not user_id else ConnectionState.AUTHENTICATED,
            metadata=metadata or {},
        )

        # Store connection
        self._connections[connection_id] = connection
        if user_id:
            self._user_connections[user_id].add(connection_id)
            # Auto-subscribe to user's personal room
            await self._subscribe_internal(connection_id, get_user_room(user_id))

        # Send welcome message
        await self._send(connection_id, ServerMessage(
            type=ServerMessageType.WELCOME,
            payload={
                "connection_id": connection_id,
                "user_id": user_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "heartbeat_interval": self.heartbeat_interval,
                "max_subscriptions": self.max_subscriptions_per_connection,
            }
        ))

        logger.info(f"Connection established: {connection_id} (user: {user_id})")
        return connection

    async def disconnect(
        self,
        connection_id: str,
        code: int = 1000,
        reason: str = "Normal closure",
    ) -> None:
        """
        Disconnect and cleanup a WebSocket connection.

        Args:
            connection_id: The connection to disconnect
            code: WebSocket close code
            reason: Close reason message
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return

        connection.state = ConnectionState.DISCONNECTING

        # Remove from user connections
        if connection.user_id:
            user_conns = self._user_connections.get(connection.user_id, set())
            user_conns.discard(connection_id)
            if not user_conns:
                self._user_connections.pop(connection.user_id, None)

        # Remove from all rooms
        for room in list(connection.subscriptions):
            await self._unsubscribe_internal(connection_id, room)

        # Remove from connections
        self._connections.pop(connection_id, None)

        # Close WebSocket
        try:
            await connection.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.warning(f"Error closing WebSocket {connection_id}: {e}")

        connection.state = ConnectionState.DISCONNECTED
        logger.info(f"Connection closed: {connection_id} ({reason})")

    @staticmethod
    def _normalize_auth_token(token: Optional[str]) -> str:
        """Normalize token value by stripping optional Bearer prefix."""
        normalized = (token or "").strip()
        if normalized.lower().startswith("bearer "):
            normalized = normalized[7:].strip()
        return normalized

    async def _validate_api_token(
        self,
        token: str,
        expected_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """
        Validate API token via shared API auth module.

        Returns dict with user metadata when valid, None otherwise.
        """
        normalized = self._normalize_auth_token(token)
        if not normalized:
            return None

        try:
            # Lazy import to avoid module-level coupling.
            from api.auth import verify_api_key
            key_data = await verify_api_key(f"Bearer {normalized}")
        except Exception as e:
            logger.warning("WebSocket API token validation failed: %s", e)
            return None

        if expected_user_id and key_data.agent_id != expected_user_id:
            logger.warning(
                "WebSocket token user mismatch: expected=%s actual=%s",
                expected_user_id,
                key_data.agent_id,
            )
            return None

        return {"user_id": key_data.agent_id, "user_type": "agent", "tier": key_data.tier}

    async def authenticate(
        self,
        connection_id: str,
        user_id: str,
        user_type: str = "agent",
        token: Optional[str] = None,
    ) -> bool:
        """
        Authenticate a connection with a user ID.

        Args:
            connection_id: The connection to authenticate
            user_id: The user identifier
            user_type: Type of user ("agent" or "worker")
            token: Optional auth token for validation

        Returns:
            True if authentication successful
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        requested_user_type = (user_type or "agent").strip().lower()
        if requested_user_type not in {"agent", "worker"}:
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.AUTH_FAILED,
                payload={"error": "Invalid user_type. Expected 'agent' or 'worker'"}
            ))
            return False

        auth_user_id = user_id
        if token:
            token_data = await self._validate_api_token(token, expected_user_id=user_id)
            if not token_data:
                await self._send(connection_id, ServerMessage(
                    type=ServerMessageType.AUTH_FAILED,
                    payload={"error": "Invalid authentication token"}
                ))
                return False
            auth_user_id = token_data["user_id"]
            requested_user_type = token_data.get("user_type", requested_user_type)
        elif self.require_auth_token and requested_user_type == "agent":
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.AUTH_FAILED,
                payload={"error": "Authentication token required"}
            ))
            return False

        # Check connection limits
        existing = self._user_connections.get(auth_user_id, set())
        if len(existing) >= self.max_connections_per_user:
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.AUTH_FAILED,
                payload={"error": "Too many connections for this user"}
            ))
            return False

        # Cleanup previous user mapping if connection is being re-authenticated.
        if connection.user_id and connection.user_id != auth_user_id:
            prev_conns = self._user_connections.get(connection.user_id, set())
            prev_conns.discard(connection_id)
            if not prev_conns:
                self._user_connections.pop(connection.user_id, None)

        # Update connection
        connection.user_id = auth_user_id
        connection.user_type = requested_user_type
        connection.state = ConnectionState.AUTHENTICATED

        # Update user connections
        self._user_connections[auth_user_id].add(connection_id)

        # Auto-subscribe to user's personal room
        await self._subscribe_internal(connection_id, get_user_room(auth_user_id))

        # Send acknowledgment
        await self._send(connection_id, ServerMessage(
            type=ServerMessageType.AUTH_SUCCESS,
            payload={"user_id": auth_user_id, "user_type": requested_user_type}
        ))

        logger.info(
            "Connection authenticated: %s -> %s (%s, token=%s)",
            connection_id,
            auth_user_id,
            requested_user_type,
            "yes" if token else "no",
        )
        return True

    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get a connection by ID."""
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> List[Connection]:
        """Get all connections for a user."""
        conn_ids = self._user_connections.get(user_id, set())
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    @property
    def connection_count(self) -> int:
        """Total number of active connections."""
        return len(self._connections)

    @property
    def user_count(self) -> int:
        """Number of unique connected users."""
        return len(self._user_connections)

    @property
    def room_count(self) -> int:
        """Number of active rooms."""
        return len(self._room_connections)

    # ============== SUBSCRIPTIONS ==============

    async def subscribe(self, connection_id: str, room: str) -> bool:
        """
        Subscribe a connection to a room.

        Args:
            connection_id: The connection ID
            room: Room name (e.g., "task:123", "user:456")

        Returns:
            True if subscription successful
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        # Check subscription limit
        if len(connection.subscriptions) >= self.max_subscriptions_per_connection:
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.ERROR,
                payload={"error": f"Max {self.max_subscriptions_per_connection} subscriptions reached"}
            ))
            return False

        # Validate room access (e.g., check if user can subscribe to task room)
        if not await self._validate_room_access(connection, room):
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.ERROR,
                payload={"error": f"Access denied to room: {room}"}
            ))
            return False

        await self._subscribe_internal(connection_id, room)

        await self._send(connection_id, ServerMessage(
            type=ServerMessageType.SUBSCRIBED,
            payload={"room": room, "total_subscriptions": len(connection.subscriptions)}
        ))

        logger.debug(f"Connection {connection_id} subscribed to {room}")
        return True

    async def unsubscribe(self, connection_id: str, room: str) -> bool:
        """
        Unsubscribe a connection from a room.

        Args:
            connection_id: The connection ID
            room: Room name to unsubscribe from

        Returns:
            True if unsubscription successful
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        await self._unsubscribe_internal(connection_id, room)

        await self._send(connection_id, ServerMessage(
            type=ServerMessageType.UNSUBSCRIBED,
            payload={"room": room, "total_subscriptions": len(connection.subscriptions)}
        ))

        logger.debug(f"Connection {connection_id} unsubscribed from {room}")
        return True

    async def _subscribe_internal(self, connection_id: str, room: str) -> None:
        """Internal subscription without sending confirmation."""
        connection = self._connections.get(connection_id)
        if connection:
            connection.subscriptions.add(room)
            self._room_connections[room].add(connection_id)

    async def _unsubscribe_internal(self, connection_id: str, room: str) -> None:
        """Internal unsubscription without sending confirmation."""
        connection = self._connections.get(connection_id)
        if connection:
            connection.subscriptions.discard(room)
            room_conns = self._room_connections.get(room, set())
            room_conns.discard(connection_id)
            if not room_conns:
                self._room_connections.pop(room, None)

    async def _validate_room_access(self, connection: Connection, room: str) -> bool:
        """
        Validate if a connection can access a room.

        Override this method for custom access control.
        """
        # For now, allow all authenticated users to subscribe to any room
        # In production, add validation:
        # - task:123 -> check if user owns or is assigned to task
        # - user:456 -> check if user matches
        # - category:X -> allow workers only

        if not connection.is_authenticated:
            return False

        # Users can always subscribe to their own room
        if room == get_user_room(connection.user_id):
            return True

        # Allow task subscriptions (in production, verify ownership/assignment)
        if room.startswith("task:"):
            return True

        # Allow category subscriptions for workers
        if room.startswith("category:") and connection.user_type == "worker":
            return True

        # Allow global room
        if room == "global":
            return True

        return True  # Permissive by default

    # ============== MESSAGING ==============

    async def _send(self, connection_id: str, message: ServerMessage) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection ID
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        connection = self._connections.get(connection_id)
        if not connection or connection.state == ConnectionState.DISCONNECTED:
            return False

        try:
            await connection.websocket.send_text(message.to_json())
            connection.message_count += 1
            connection.update_activity()
            return True
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            await self.disconnect(connection_id, code=1011, reason="Send error")
            return False

    async def send_to_user(self, user_id: str, event: WebSocketEvent) -> int:
        """
        Send an event to all connections of a user.

        Args:
            user_id: Target user ID
            event: Event to send

        Returns:
            Number of connections that received the event
        """
        conn_ids = self._user_connections.get(user_id, set())
        sent = 0

        message = ServerMessage(
            type=ServerMessageType.EVENT,
            payload=event.to_dict(),
        )

        for conn_id in list(conn_ids):
            if await self._send(conn_id, message):
                sent += 1

        return sent

    async def broadcast_to_room(self, room: str, event: WebSocketEvent) -> int:
        """
        Broadcast an event to all connections in a room.

        Args:
            room: Room name
            event: Event to broadcast

        Returns:
            Number of connections that received the event
        """
        conn_ids = self._room_connections.get(room, set())
        sent = 0

        message = ServerMessage(
            type=ServerMessageType.EVENT,
            payload=event.to_dict(),
        )

        for conn_id in list(conn_ids):
            if await self._send(conn_id, message):
                sent += 1

        logger.debug(f"Broadcast {event.event_type.value} to room {room}: {sent} recipients")
        return sent

    async def broadcast(
        self,
        event: WebSocketEvent,
        exclude_users: Optional[Set[str]] = None,
        filter_fn: Optional[Callable[[Connection], bool]] = None,
    ) -> int:
        """
        Broadcast an event to all connections.

        Args:
            event: Event to broadcast
            exclude_users: Set of user IDs to exclude
            filter_fn: Optional filter function for connections

        Returns:
            Number of connections that received the event
        """
        exclude_users = exclude_users or set()
        sent = 0

        message = ServerMessage(
            type=ServerMessageType.EVENT,
            payload=event.to_dict(),
        )

        for conn_id, connection in list(self._connections.items()):
            if connection.user_id in exclude_users:
                continue
            if filter_fn and not filter_fn(connection):
                continue
            if await self._send(conn_id, message):
                sent += 1

        logger.info(f"Broadcast {event.event_type.value} to {sent} connections")
        return sent

    # ============== MESSAGE HANDLING ==============

    async def handle_message(self, connection_id: str, raw_message: str) -> None:
        """
        Process an incoming message from a client.

        Args:
            connection_id: Source connection ID
            raw_message: Raw JSON message string
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return

        # Rate limiting
        if not self._check_rate_limit(connection):
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.ERROR,
                payload={"error": "Rate limit exceeded", "code": "RATE_LIMITED"}
            ))
            return

        connection.update_activity()

        try:
            data = json.loads(raw_message)
            msg_type = data.get("type", "")
            payload = data.get("payload", {})
            msg_id = data.get("id")
        except json.JSONDecodeError:
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.ERROR,
                payload={"error": "Invalid JSON"}
            ))
            return

        # Handle different message types
        if msg_type == ClientMessageType.PING.value:
            connection.last_ping = datetime.now(timezone.utc)
            await self._send(connection_id, ServerMessage(
                type=ServerMessageType.PONG,
                correlation_id=msg_id,
            ))

        elif msg_type == ClientMessageType.PONG.value:
            connection.last_pong = datetime.now(timezone.utc)

        elif msg_type == ClientMessageType.SUBSCRIBE.value:
            room = payload.get("room")
            if room:
                await self.subscribe(connection_id, room)

        elif msg_type == ClientMessageType.UNSUBSCRIBE.value:
            room = payload.get("room")
            if room:
                await self.unsubscribe(connection_id, room)

        elif msg_type == ClientMessageType.AUTH.value:
            user_id = payload.get("user_id")
            user_type = payload.get("user_type", "agent")
            token = payload.get("token")
            if user_id:
                await self.authenticate(connection_id, user_id, user_type, token)

        else:
            # Dispatch to registered handlers
            handlers = self._event_handlers.get(msg_type, [])
            for handler in handlers:
                try:
                    await handler(connection, data)
                except Exception as e:
                    logger.error(f"Handler error for {msg_type}: {e}")
                    await self._send(connection_id, ServerMessage(
                        type=ServerMessageType.ERROR,
                        payload={"error": str(e)},
                        correlation_id=msg_id,
                    ))

    def on(self, message_type: str, handler: Callable[[Connection, Dict], Awaitable[None]]) -> None:
        """
        Register a handler for a message type.

        Args:
            message_type: The message type to handle
            handler: Async function(connection, data) -> None
        """
        self._event_handlers[message_type].append(handler)

    def _check_rate_limit(self, connection: Connection) -> bool:
        """Check if connection is within rate limits."""
        now = datetime.now(timezone.utc)
        window_elapsed = (now - connection.rate_limit_window_start).total_seconds()

        if window_elapsed > self.rate_limit_window_seconds:
            # Reset window
            connection.rate_limit_window_start = now
            connection.messages_in_window = 1
            return True

        connection.messages_in_window += 1
        return connection.messages_in_window <= self.rate_limit_messages

    # ============== BACKGROUND TASKS ==============

    async def _heartbeat_loop(self) -> None:
        """Background task for connection health monitoring."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _check_connections(self) -> None:
        """Check all connections and cleanup stale ones."""
        now = datetime.now(timezone.utc)

        for conn_id, connection in list(self._connections.items()):
            # Check for timeout
            time_since_activity = (now - connection.last_activity).total_seconds()
            if time_since_activity > self.heartbeat_timeout:
                logger.warning(f"Connection {conn_id} timed out ({time_since_activity:.1f}s inactive)")
                await self.disconnect(conn_id, code=4000, reason="Heartbeat timeout")
                continue

            # Send ping
            await self._send(conn_id, ServerMessage(type=ServerMessageType.PING))

    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                self._cleanup_empty_rooms()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    def _cleanup_empty_rooms(self) -> None:
        """Remove empty rooms."""
        empty_rooms = [room for room, conns in self._room_connections.items() if not conns]
        for room in empty_rooms:
            self._room_connections.pop(room, None)
        if empty_rooms:
            logger.debug(f"Cleaned up {len(empty_rooms)} empty rooms")

    # ============== STATISTICS ==============

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "total_connections": self.connection_count,
            "unique_users": self.user_count,
            "active_rooms": self.room_count,
            "connections_by_state": {
                state.value: sum(1 for c in self._connections.values() if c.state == state)
                for state in ConnectionState
            },
            "connections_by_type": {
                "agent": sum(1 for c in self._connections.values() if c.user_type == "agent"),
                "worker": sum(1 for c in self._connections.values() if c.user_type == "worker"),
                "unknown": sum(1 for c in self._connections.values() if c.user_type is None),
            },
            "running": self._running,
        }


# ============== GLOBAL INSTANCE ==============


# Global manager instance
ws_manager = WebSocketManager()


# ============== FASTAPI ROUTER ==============


ws_router = APIRouter(tags=["websocket"])


@ws_router.on_event("startup")
async def startup_websocket():
    """Start WebSocket manager on app startup."""
    await ws_manager.start()


@ws_router.on_event("shutdown")
async def shutdown_websocket():
    """Stop WebSocket manager on app shutdown."""
    await ws_manager.stop()


@ws_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None, alias="api_key"),
    user_id: Optional[str] = Query(None, alias="user_id"),
    user_type: Optional[str] = Query(None, alias="user_type"),
):
    """
    WebSocket endpoint for real-time updates.

    Connect with optional authentication:
    - ws://host/ws?api_key=YOUR_KEY&user_id=YOUR_ID&user_type=agent

    Or authenticate after connection via message:
    {"type": "auth", "payload": {"user_id": "...", "user_type": "agent", "token": "..."}}

    Subscribe to rooms:
    {"type": "subscribe", "payload": {"room": "task:123"}}

    Unsubscribe from rooms:
    {"type": "unsubscribe", "payload": {"room": "task:123"}}

    Room types:
    - user:<user_id> - User's personal notifications
    - task:<task_id> - Updates for a specific task
    - category:<category> - New tasks in a category (for workers)
    - global - System-wide announcements
    """
    # Validate API key if provided and optionally pre-authenticate.
    authenticated_user = None
    authenticated_type = None
    if api_key:
        token_data = await ws_manager._validate_api_token(
            api_key,
            expected_user_id=user_id if user_id else None,
        )
        if not token_data:
            await websocket.close(code=1008, reason="Invalid API key")
            return
        authenticated_user = token_data["user_id"]
        authenticated_type = user_type or token_data.get("user_type", "agent")
    elif user_id and ws_manager.require_auth_token:
        await websocket.close(code=1008, reason="API key required")
        return

    try:
        async with ws_manager.connection_context(websocket, authenticated_user, authenticated_type) as connection:
            while True:
                try:
                    raw_message = await websocket.receive_text()
                    await ws_manager.handle_message(connection.connection_id, raw_message)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    await ws_manager._send(
                        connection.connection_id,
                        ServerMessage(
                            type=ServerMessageType.ERROR,
                            payload={"error": str(e)}
                        )
                    )
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")


@ws_router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket server statistics."""
    return ws_manager.get_stats()


@ws_router.get("/ws/rooms")
async def websocket_rooms():
    """Get list of active rooms and their subscriber counts."""
    return {
        room: len(conns)
        for room, conns in ws_manager._room_connections.items()
    }


# ============== EXPORTS ==============


__all__ = [
    "WebSocketManager",
    "Connection",
    "ConnectionState",
    "ServerMessage",
    "ServerMessageType",
    "ClientMessageType",
    "ws_manager",
    "ws_router",
]
