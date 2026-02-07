"""
WebSocket Client for Execution Market

A Python client for connecting to and testing the Execution Market WebSocket server.

Features:
- Connect and authenticate
- Subscribe to rooms
- Send and receive messages
- Automatic reconnection
- Event callbacks

Usage:
    from websocket.client import EMWebSocketClient

    async def on_task_created(event):
        print(f"New task: {event['payload']['title']}")

    client = EMWebSocketClient(
        url="ws://localhost:8000/ws",
        user_id="agent_123",
        user_type="agent",
    )
    client.on("TaskCreated", on_task_created)

    await client.connect()
    await client.subscribe("category:physical_verification")

    # Keep receiving events
    async for event in client.events():
        print(f"Event: {event}")
"""

import asyncio
import json
import logging
import ssl
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Awaitable, AsyncIterator, List
from dataclasses import dataclass, field
from enum import Enum
import secrets

try:
    import websockets
    from websockets.client import WebSocketClientProtocol

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = Any

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """Client connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"


@dataclass
class ClientConfig:
    """WebSocket client configuration."""

    url: str = "ws://localhost:8000/ws"
    user_id: Optional[str] = None
    user_type: str = "agent"  # "agent" or "worker"
    api_key: Optional[str] = None
    reconnect_enabled: bool = True
    reconnect_delay: float = 1.0  # Initial delay in seconds
    reconnect_max_delay: float = 60.0  # Max delay between reconnects
    reconnect_max_attempts: int = 10  # 0 = infinite
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    ssl_verify: bool = True


@dataclass
class ReceivedMessage:
    """Represents a message received from the server."""

    type: str
    payload: Dict[str, Any]
    id: str
    timestamp: str
    correlation_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReceivedMessage":
        """Create from server message dict."""
        return cls(
            type=data.get("type", "unknown"),
            payload=data.get("payload", {}),
            id=data.get("id", ""),
            timestamp=data.get("timestamp", ""),
            correlation_id=data.get("correlation_id"),
            raw=data,
        )


class EMWebSocketClient:
    """
    WebSocket client for the Execution Market real-time server.

    Provides an async interface for connecting to and interacting
    with the Execution Market WebSocket server.
    """

    def __init__(
        self,
        url: str = "ws://localhost:8000/ws",
        user_id: Optional[str] = None,
        user_type: str = "agent",
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the WebSocket client.

        Args:
            url: WebSocket server URL
            user_id: User identifier for authentication
            user_type: Type of user ("agent" or "worker")
            api_key: API key for authentication
            **kwargs: Additional configuration options
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library required. Install with: pip install websockets"
            )

        self.config = ClientConfig(
            url=url,
            user_id=user_id,
            user_type=user_type,
            api_key=api_key,
            **{k: v for k, v in kwargs.items() if hasattr(ClientConfig, k)},
        )

        self._ws: Optional[WebSocketClientProtocol] = None
        self._state = ConnectionState.DISCONNECTED
        self._connection_id: Optional[str] = None
        self._subscriptions: set = set()
        self._reconnect_attempts = 0
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    # ============== PROPERTIES ==============

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED)

    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self._state == ConnectionState.AUTHENTICATED

    @property
    def connection_id(self) -> Optional[str]:
        """Get connection ID assigned by server."""
        return self._connection_id

    @property
    def subscriptions(self) -> set:
        """Get current subscriptions."""
        return self._subscriptions.copy()

    # ============== CONNECTION ==============

    async def connect(self) -> bool:
        """
        Connect to the WebSocket server.

        Returns:
            True if connection successful
        """
        if self.is_connected:
            logger.warning("Already connected")
            return True

        self._state = ConnectionState.CONNECTING
        self._running = True

        try:
            # Build URL with query params
            url = self.config.url
            params = []
            if self.config.api_key:
                params.append(f"api_key={self.config.api_key}")
            if self.config.user_id:
                params.append(f"user_id={self.config.user_id}")
            if self.config.user_type:
                params.append(f"user_type={self.config.user_type}")
            if params:
                url = f"{url}?{'&'.join(params)}"

            # SSL context
            ssl_context = None
            if url.startswith("wss://"):
                ssl_context = ssl.create_default_context()
                if not self.config.ssl_verify:
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

            # Connect
            self._ws = await websockets.connect(
                url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                ssl=ssl_context,
            )

            # Wait for welcome message
            welcome_raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
            welcome = json.loads(welcome_raw)

            if welcome.get("type") == "welcome":
                self._connection_id = welcome.get("payload", {}).get("connection_id")
                self._state = ConnectionState.CONNECTED
                logger.info(f"Connected: {self._connection_id}")

                # If user_id was provided, we should be authenticated
                if self.config.user_id:
                    self._state = ConnectionState.AUTHENTICATED

                # Start background tasks
                self._receive_task = asyncio.create_task(self._receive_loop())
                self._reconnect_attempts = 0

                return True
            else:
                logger.error(f"Unexpected welcome message: {welcome}")
                await self.disconnect()
                return False

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._state = ConnectionState.DISCONNECTED
            return False

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        self._running = False

        # Cancel background tasks
        for task in [self._receive_task, self._ping_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close WebSocket
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            self._ws = None

        self._state = ConnectionState.DISCONNECTED
        self._connection_id = None
        logger.info("Disconnected")

    async def _reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff."""
        if not self.config.reconnect_enabled:
            return False

        self._state = ConnectionState.RECONNECTING

        while self._running:
            self._reconnect_attempts += 1

            if (
                self.config.reconnect_max_attempts > 0
                and self._reconnect_attempts > self.config.reconnect_max_attempts
            ):
                logger.error(
                    f"Max reconnect attempts ({self.config.reconnect_max_attempts}) reached"
                )
                self._state = ConnectionState.DISCONNECTED
                return False

            # Calculate delay with exponential backoff
            delay = min(
                self.config.reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                self.config.reconnect_max_delay,
            )
            logger.info(
                f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts})"
            )
            await asyncio.sleep(delay)

            if await self.connect():
                # Resubscribe to rooms
                for room in list(self._subscriptions):
                    await self.subscribe(room)
                return True

        return False

    # ============== AUTHENTICATION ==============

    async def authenticate(
        self,
        user_id: str,
        user_type: str = "agent",
        token: Optional[str] = None,
    ) -> bool:
        """
        Authenticate with the server (if not authenticated via URL params).

        Args:
            user_id: User identifier
            user_type: Type of user
            token: Optional auth token

        Returns:
            True if authentication successful
        """
        if not self.is_connected:
            logger.error("Not connected")
            return False

        response = await self._send_and_wait(
            "auth",
            {
                "user_id": user_id,
                "user_type": user_type,
                "token": token,
            },
            timeout=10.0,
        )

        if response and response.type == "auth_success":
            self._state = ConnectionState.AUTHENTICATED
            self.config.user_id = user_id
            self.config.user_type = user_type
            logger.info(f"Authenticated as {user_id} ({user_type})")
            return True

        logger.error(f"Authentication failed: {response}")
        return False

    # ============== SUBSCRIPTIONS ==============

    async def subscribe(self, room: str) -> bool:
        """
        Subscribe to a room.

        Args:
            room: Room name (e.g., "task:123", "category:physical")

        Returns:
            True if subscription successful
        """
        if not self.is_connected:
            logger.error("Not connected")
            return False

        response = await self._send_and_wait(
            "subscribe",
            {"room": room},
            timeout=5.0,
        )

        if response and response.type == "subscribed":
            self._subscriptions.add(room)
            logger.info(f"Subscribed to {room}")
            return True

        logger.error(f"Subscription failed: {response}")
        return False

    async def unsubscribe(self, room: str) -> bool:
        """
        Unsubscribe from a room.

        Args:
            room: Room name

        Returns:
            True if unsubscription successful
        """
        if not self.is_connected:
            logger.error("Not connected")
            return False

        response = await self._send_and_wait(
            "unsubscribe",
            {"room": room},
            timeout=5.0,
        )

        if response and response.type == "unsubscribed":
            self._subscriptions.discard(room)
            logger.info(f"Unsubscribed from {room}")
            return True

        return False

    # ============== MESSAGING ==============

    async def _send(self, msg_type: str, payload: Dict[str, Any]) -> str:
        """
        Send a message to the server.

        Args:
            msg_type: Message type
            payload: Message payload

        Returns:
            Message ID
        """
        if not self._ws:
            raise RuntimeError("Not connected")

        msg_id = secrets.token_hex(8)
        message = {
            "type": msg_type,
            "payload": payload,
            "id": msg_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await self._ws.send(json.dumps(message))
        return msg_id

    async def _send_and_wait(
        self,
        msg_type: str,
        payload: Dict[str, Any],
        timeout: float = 10.0,
    ) -> Optional[ReceivedMessage]:
        """
        Send a message and wait for response.

        Args:
            msg_type: Message type
            payload: Message payload
            timeout: Response timeout in seconds

        Returns:
            Response message or None if timeout
        """
        msg_id = await self._send(msg_type, payload)

        # Create future for response
        future = asyncio.Future()
        self._pending_responses[msg_id] = future

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Response timeout for message {msg_id}")
            return None
        finally:
            self._pending_responses.pop(msg_id, None)

    async def ping(self) -> float:
        """
        Send a ping and measure latency.

        Returns:
            Round-trip time in milliseconds
        """
        start = datetime.now(timezone.utc)
        response = await self._send_and_wait("ping", {}, timeout=5.0)
        if response and response.type == "pong":
            end = datetime.now(timezone.utc)
            latency_ms = (end - start).total_seconds() * 1000
            return latency_ms
        return -1

    # ============== EVENT HANDLING ==============

    def on(
        self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: Event type to handle (e.g., "TaskCreated", "SubmissionReceived")
            handler: Async function to call when event is received
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Optional[Callable] = None) -> None:
        """
        Remove handler(s) for an event type.

        Args:
            event_type: Event type
            handler: Specific handler to remove, or None to remove all
        """
        if handler is None:
            self._event_handlers.pop(event_type, None)
        elif event_type in self._event_handlers:
            self._event_handlers[event_type] = [
                h for h in self._event_handlers[event_type] if h != handler
            ]

    async def events(self) -> AsyncIterator[ReceivedMessage]:
        """
        Async iterator for receiving events.

        Yields:
            Received messages/events

        Usage:
            async for event in client.events():
                print(f"Event: {event.type}")
        """
        while self._running:
            try:
                message = await self._event_queue.get()
                yield message
            except asyncio.CancelledError:
                break

    async def _receive_loop(self) -> None:
        """Background task for receiving messages."""
        while self._running and self._ws:
            try:
                raw_message = await self._ws.recv()
                data = json.loads(raw_message)
                message = ReceivedMessage.from_dict(data)

                # Handle correlation (response to request)
                if (
                    message.correlation_id
                    and message.correlation_id in self._pending_responses
                ):
                    future = self._pending_responses[message.correlation_id]
                    if not future.done():
                        future.set_result(message)
                    continue

                # Handle events
                if message.type == "event":
                    event_data = message.payload
                    event_type = event_data.get("event", "unknown")

                    # Call registered handlers
                    handlers = self._event_handlers.get(event_type, [])
                    for handler in handlers:
                        try:
                            await handler(event_data)
                        except Exception as e:
                            logger.error(f"Handler error for {event_type}: {e}")

                    # Put in queue for async iteration
                    await self._event_queue.put(message)

                # Handle pong
                elif message.type == "pong":
                    pass  # Handled by correlation

                # Handle errors
                elif message.type == "error":
                    logger.error(f"Server error: {message.payload}")

            except websockets.ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}")
                if self._running and self.config.reconnect_enabled:
                    await self._reconnect()
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")

    # ============== CONTEXT MANAGER ==============

    async def __aenter__(self) -> "EMWebSocketClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


# ============== CONVENIENCE FUNCTIONS ==============


async def connect_and_subscribe(
    url: str,
    user_id: str,
    rooms: List[str],
    user_type: str = "agent",
    api_key: Optional[str] = None,
) -> EMWebSocketClient:
    """
    Convenience function to connect and subscribe to rooms.

    Args:
        url: WebSocket URL
        user_id: User identifier
        rooms: List of rooms to subscribe
        user_type: Type of user
        api_key: Optional API key

    Returns:
        Connected and subscribed client
    """
    client = EMWebSocketClient(
        url=url,
        user_id=user_id,
        user_type=user_type,
        api_key=api_key,
    )

    if not await client.connect():
        raise ConnectionError("Failed to connect")

    for room in rooms:
        await client.subscribe(room)

    return client


# ============== CLI FOR TESTING ==============


async def _main():
    """Simple CLI for testing the WebSocket client."""
    import argparse

    parser = argparse.ArgumentParser(description="Execution Market WebSocket Client")
    parser.add_argument("--url", default="ws://localhost:8000/ws", help="WebSocket URL")
    parser.add_argument("--user-id", required=True, help="User ID")
    parser.add_argument("--user-type", default="agent", choices=["agent", "worker"])
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--subscribe", nargs="+", help="Rooms to subscribe")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    async def print_event(event: Dict[str, Any]):
        print(f"\n[EVENT] {event.get('event', 'unknown')}")
        print(json.dumps(event.get("payload", {}), indent=2))

    client = EMWebSocketClient(
        url=args.url,
        user_id=args.user_id,
        user_type=args.user_type,
        api_key=args.api_key,
    )

    # Register handler for all events
    for event_type in [
        "TaskCreated",
        "TaskUpdated",
        "TaskCancelled",
        "ApplicationReceived",
        "WorkerAssigned",
        "SubmissionReceived",
        "SubmissionApproved",
        "SubmissionRejected",
        "PaymentReleased",
        "PaymentFailed",
        "NotificationNew",
    ]:
        client.on(event_type, print_event)

    print(f"Connecting to {args.url}...")
    if not await client.connect():
        print("Failed to connect")
        return

    print(f"Connected as {args.user_id} ({args.user_type})")

    # Subscribe to rooms
    if args.subscribe:
        for room in args.subscribe:
            await client.subscribe(room)

    # Ping
    latency = await client.ping()
    print(f"Latency: {latency:.1f}ms")

    print("\nListening for events (Ctrl+C to quit)...")

    try:
        async for event in client.events():
            pass  # Events are printed by handler
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(_main())


# ============== EXPORTS ==============


__all__ = [
    "EMWebSocketClient",
    "ClientConfig",
    "ConnectionState",
    "ReceivedMessage",
    "connect_and_subscribe",
]
