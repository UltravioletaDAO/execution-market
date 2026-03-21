"""WebSocket event client for Execution Market real-time updates.

Requires the ``websockets`` package (optional dependency)::

    pip install em-plugin-sdk[realtime]

Usage::

    from em_plugin_sdk.realtime import EMEventClient, EventType

    async with EMEventClient(api_key="em_...") as ws:
        await ws.watch_task("task-uuid")

        ws.on(EventType.SUBMISSION_RECEIVED, lambda e: print("New submission!", e))

        async for event in ws.events():
            print(event["type"], event["payload"])
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable

logger = logging.getLogger(__name__)

DEFAULT_WS_URL = "wss://api.execution.market/ws"


@dataclass
class _Config:
    url: str = DEFAULT_WS_URL
    api_key: str | None = None
    user_id: str | None = None
    user_type: str = "agent"
    reconnect: bool = True
    reconnect_delay: float = 1.0
    reconnect_max_delay: float = 60.0
    reconnect_max_attempts: int = 10
    ping_interval: float = 30.0


class EMEventClient:
    """Async WebSocket client for EM real-time events.

    Supports:
    - Room-based subscriptions (task, user, category, global)
    - Typed event handlers via ``on()``
    - Async iteration via ``events()``
    - Automatic reconnection with exponential backoff
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        url: str = DEFAULT_WS_URL,
        user_id: str | None = None,
        user_type: str = "agent",
        reconnect: bool = True,
    ):
        try:
            import websockets  # noqa: F401
        except ImportError:
            raise ImportError(
                "websockets is required for real-time features. "
                "Install with: pip install em-plugin-sdk[realtime]"
            )

        self._cfg = _Config(
            url=url,
            api_key=api_key,
            user_id=user_id,
            user_type=user_type,
            reconnect=reconnect,
        )
        self._ws: Any = None
        self._connected = False
        self._running = False
        self._connection_id: str | None = None
        self._subscriptions: set[str] = set()
        self._handlers: dict[str, list[Callable]] = {}
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._recv_task: asyncio.Task | None = None
        self._reconnect_attempts = 0

    # -- lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to the WebSocket server and wait for the welcome message."""
        import websockets

        self._running = True
        url = self._cfg.url
        params = []
        if self._cfg.api_key:
            params.append(f"api_key={self._cfg.api_key}")
        if self._cfg.user_id:
            params.append(f"user_id={self._cfg.user_id}")
        params.append(f"user_type={self._cfg.user_type}")
        if params:
            url = f"{url}?{'&'.join(params)}"

        ssl_ctx = None
        if url.startswith("wss://"):
            ssl_ctx = ssl.create_default_context()

        try:
            self._ws = await websockets.connect(
                url,
                ping_interval=self._cfg.ping_interval,
                ssl=ssl_ctx,
            )
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
            welcome = json.loads(raw)
            if welcome.get("type") == "welcome":
                self._connection_id = welcome.get("payload", {}).get("connection_id")
                self._connected = True
                self._reconnect_attempts = 0
                self._recv_task = asyncio.create_task(self._receive_loop())
                return True
        except Exception as exc:
            logger.error("WebSocket connect failed: %s", exc)
        self._connected = False
        return False

    async def disconnect(self) -> None:
        """Gracefully disconnect."""
        self._running = False
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False

    async def __aenter__(self) -> EMEventClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._connected

    # -- subscriptions ------------------------------------------------------

    async def subscribe(self, room: str) -> bool:
        """Subscribe to a room (e.g. ``task:uuid``, ``category:physical_presence``)."""
        ok = await self._send_and_expect("subscribe", {"room": room}, "subscribed")
        if ok:
            self._subscriptions.add(room)
        return ok

    async def unsubscribe(self, room: str) -> bool:
        """Unsubscribe from a room."""
        ok = await self._send_and_expect("unsubscribe", {"room": room}, "unsubscribed")
        if ok:
            self._subscriptions.discard(room)
        return ok

    async def watch_task(self, task_id: str) -> bool:
        """Subscribe to updates for a specific task."""
        return await self.subscribe(f"task:{task_id}")

    async def watch_category(self, category: str) -> bool:
        """Subscribe to new tasks in a category."""
        return await self.subscribe(f"category:{category}")

    async def watch_global(self) -> bool:
        """Subscribe to system-wide announcements."""
        return await self.subscribe("global")

    # -- event handling -----------------------------------------------------

    def on(self, event_type: str, handler: Callable[..., Any]) -> None:
        """Register a handler for an event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    def off(self, event_type: str, handler: Callable | None = None) -> None:
        """Remove handler(s) for an event type."""
        if handler is None:
            self._handlers.pop(event_type, None)
        elif event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Async iterator yielding events as dicts with ``type`` and ``payload``."""
        while self._running:
            try:
                event = await self._queue.get()
                yield event
            except asyncio.CancelledError:
                break

    # -- ping ---------------------------------------------------------------

    async def ping(self) -> float:
        """Send a ping and return round-trip latency in ms. Returns -1 on failure."""
        start = datetime.now(timezone.utc)
        ok = await self._send_and_expect("ping", {}, "pong")
        if not ok:
            return -1
        end = datetime.now(timezone.utc)
        return (end - start).total_seconds() * 1000

    # -- internals ----------------------------------------------------------

    async def _send(self, msg_type: str, payload: dict[str, Any]) -> str:
        if not self._ws:
            raise RuntimeError("Not connected")
        msg_id = secrets.token_hex(8)
        await self._ws.send(json.dumps({
            "type": msg_type,
            "payload": payload,
            "id": msg_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        return msg_id

    async def _send_and_expect(self, msg_type: str, payload: dict[str, Any], expected: str) -> bool:
        if not self._ws:
            return False
        try:
            await self._send(msg_type, payload)
            raw = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            data = json.loads(raw)
            return data.get("type") == expected
        except Exception:
            return False

    async def _receive_loop(self) -> None:
        import websockets

        while self._running and self._ws:
            try:
                raw = await self._ws.recv()
                data = json.loads(raw)

                if data.get("type") == "event":
                    event_payload = data.get("payload", {})
                    event_type = event_payload.get("event", "unknown")

                    # Dispatch to handlers
                    for handler in self._handlers.get(event_type, []):
                        try:
                            result = handler(event_payload)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as exc:
                            logger.error("Handler error for %s: %s", event_type, exc)

                    # Put in queue for async iteration
                    await self._queue.put({"type": event_type, "payload": event_payload})

            except websockets.ConnectionClosed:
                self._connected = False
                if self._running and self._cfg.reconnect:
                    await self._reconnect()
                break
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Receive error: %s", exc)

    async def _reconnect(self) -> None:
        while self._running and self._reconnect_attempts < self._cfg.reconnect_max_attempts:
            self._reconnect_attempts += 1
            delay = min(
                self._cfg.reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                self._cfg.reconnect_max_delay,
            )
            logger.info("Reconnecting in %.1fs (attempt %d)", delay, self._reconnect_attempts)
            await asyncio.sleep(delay)
            if await self.connect():
                for room in list(self._subscriptions):
                    await self.subscribe(room)
                return
