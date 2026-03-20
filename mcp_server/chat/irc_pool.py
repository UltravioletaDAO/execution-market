"""
IRCPool — Singleton IRC connection multiplexed across task chat channels.

Maintains a single TCP/TLS connection to MeshRelay IRC. Tracks which
WebSocket clients are subscribed to which ``#task-{id}`` channels.
JOIN when first client connects, PART when last disconnects.

Uses raw asyncio sockets (IRC protocol is simple enough to not need a library).
"""

import asyncio
import logging
import os
import random
import ssl
import string
import time
from collections import defaultdict
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

# Type for the callback that dispatches IRC messages to WebSocket clients
MessageCallback = Callable[[str, str, str], Awaitable[None]]
# callback(channel, nick, text) -> None


def _generate_nick(prefix: str) -> str:
    """Generate a unique IRC nick: {prefix}-{random4}."""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{prefix}-{suffix}"


class IRCPool:
    """
    Singleton IRC connection pool for the chat relay.

    One IRC connection, many channels. Routes incoming PRIVMSG to
    registered WebSocket callbacks per channel.
    """

    _instance: Optional["IRCPool"] = None

    def __init__(
        self,
        host: str = "irc.meshrelay.xyz",
        port: int = 6697,
        use_tls: bool = True,
        nick_prefix: str = "em-relay",
        sasl_user: str = "",
        sasl_pass: str = "",
    ):
        self._host = host
        self._port = port
        self._use_tls = use_tls
        self._nick = _generate_nick(nick_prefix)
        self._sasl_user = sasl_user or os.getenv("CHAT_IRC_SASL_USER", "")
        self._sasl_pass = sasl_pass or os.getenv("CHAT_IRC_SASL_PASS", "")

        # channel -> set of subscriber IDs
        self._subscriptions: dict[str, set[str]] = defaultdict(set)
        # subscriber_id -> callback
        self._callbacks: dict[str, MessageCallback] = {}

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._registered = False
        self._read_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._shutdown = False

        # Stats
        self._stats = {
            "messages_relayed": 0,
            "joins": 0,
            "parts": 0,
            "reconnects": 0,
            "errors": 0,
        }

    @classmethod
    def get_instance(
        cls,
        host: str = "irc.meshrelay.xyz",
        port: int = 6697,
        use_tls: bool = True,
        nick_prefix: str = "em-relay",
    ) -> "IRCPool":
        """Get or create the singleton IRCPool."""
        if cls._instance is None:
            cls._instance = cls(
                host=host,
                port=port,
                use_tls=use_tls,
                nick_prefix=nick_prefix,
            )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish IRC connection and register."""
        if self._connected:
            return True

        try:
            ssl_ctx = None
            if self._use_tls:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port, ssl=ssl_ctx),
                timeout=15.0,
            )

            # IRC registration
            await self._send(f"NICK {self._nick}")
            await self._send(f"USER {self._nick} 0 * :EM Chat Relay")

            # Wait for RPL_WELCOME (001) or ERR_NICKNAMEINUSE (433)
            registered = await self._wait_for_registration()
            if not registered:
                logger.error("IRC registration failed for nick %s", self._nick)
                await self._close_connection()
                return False

            self._connected = True
            self._registered = True

            # Start read loop
            self._read_task = asyncio.create_task(self._read_loop())
            logger.info(
                "IRCPool connected: %s@%s:%d (TLS=%s)",
                self._nick,
                self._host,
                self._port,
                self._use_tls,
            )
            return True

        except Exception:
            self._stats["errors"] += 1
            logger.exception("IRCPool connect failed: %s:%d", self._host, self._port)
            await self._close_connection()
            return False

    async def disconnect(self) -> None:
        """Gracefully disconnect from IRC."""
        self._shutdown = True
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._connected:
            try:
                await self._send("QUIT :Chat relay shutting down")
            except Exception:
                pass

        await self._close_connection()
        self._subscriptions.clear()
        self._callbacks.clear()
        logger.info("IRCPool disconnected")

    async def _close_connection(self) -> None:
        self._connected = False
        self._registered = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
        self._reader = None

    # ------------------------------------------------------------------
    # IRC protocol helpers
    # ------------------------------------------------------------------

    async def _send(self, line: str) -> None:
        """Send a raw IRC line."""
        if self._writer is None:
            return
        data = (line + "\r\n").encode("utf-8")
        self._writer.write(data)
        await self._writer.drain()

    async def _wait_for_registration(self) -> bool:
        """Read lines until we get 001 (welcome) or 433 (nick in use)."""
        if not self._reader:
            return False
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            try:
                line = await asyncio.wait_for(self._reader.readline(), timeout=5.0)
                if not line:
                    return False
                text = line.decode("utf-8", errors="replace").strip()
                if " 001 " in text:
                    return True
                if " 433 " in text:
                    # Nick in use — try alternate
                    self._nick = _generate_nick(self._nick.rsplit("-", 1)[0])
                    await self._send(f"NICK {self._nick}")
                if text.startswith("PING"):
                    token = text.split(" ", 1)[1] if " " in text else ""
                    await self._send(f"PONG {token}")
            except asyncio.TimeoutError:
                continue
        return False

    async def _read_loop(self) -> None:
        """Continuously read IRC messages and dispatch to subscribers."""
        while self._connected and self._reader and not self._shutdown:
            try:
                line = await asyncio.wait_for(self._reader.readline(), timeout=300.0)
                if not line:
                    logger.warning("IRCPool: connection closed by server")
                    break

                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue

                # Handle PING
                if text.startswith("PING"):
                    token = text.split(" ", 1)[1] if " " in text else ""
                    await self._send(f"PONG {token}")
                    continue

                # Parse PRIVMSG: :nick!user@host PRIVMSG #channel :message
                await self._handle_line(text)

            except asyncio.TimeoutError:
                # Send a PING to keep alive
                await self._send("PING :keepalive")
            except asyncio.CancelledError:
                return
            except Exception:
                self._stats["errors"] += 1
                logger.exception("IRCPool read_loop error")
                break

        # Connection lost — attempt reconnect
        if not self._shutdown:
            self._connected = False
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _handle_line(self, line: str) -> None:
        """Parse and dispatch a single IRC line."""
        # :nick!user@host PRIVMSG #channel :message text
        if " PRIVMSG " not in line:
            return

        try:
            prefix, rest = (
                line[1:].split(" ", 1) if line.startswith(":") else ("", line)
            )
            nick = prefix.split("!")[0] if "!" in prefix else prefix

            # Skip our own messages
            if nick == self._nick:
                return

            parts = rest.split(" ", 2)  # PRIVMSG #channel :text
            if len(parts) < 3:
                return

            channel = parts[1].lower()
            msg_text = parts[2][1:] if parts[2].startswith(":") else parts[2]

            # Dispatch to subscribers
            if channel in self._subscriptions:
                self._stats["messages_relayed"] += 1
                for sub_id in list(self._subscriptions[channel]):
                    cb = self._callbacks.get(sub_id)
                    if cb:
                        try:
                            await cb(channel, nick, msg_text)
                        except Exception:
                            logger.exception(
                                "IRCPool: callback error for %s in %s",
                                sub_id[:8],
                                channel,
                            )
        except Exception:
            logger.debug("IRCPool: failed to parse line: %s", line[:100])

    # ------------------------------------------------------------------
    # Reconnection
    # ------------------------------------------------------------------

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff."""
        backoff = 2.0
        max_backoff = 120.0
        attempt = 0

        while not self._shutdown:
            attempt += 1
            self._stats["reconnects"] += 1
            logger.info(
                "IRCPool: reconnecting (attempt %d, backoff %.0fs)",
                attempt,
                backoff,
            )

            await self._close_connection()
            await asyncio.sleep(backoff)

            if await self.connect():
                # Rejoin all active channels
                for channel in list(self._subscriptions.keys()):
                    if self._subscriptions[channel]:
                        await self._send(f"JOIN {channel}")
                        logger.info("IRCPool: rejoined %s", channel)
                return

            backoff = min(backoff * 2, max_backoff)

    # ------------------------------------------------------------------
    # Channel subscription API
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        channel: str,
        subscriber_id: str,
        callback: MessageCallback,
    ) -> None:
        """Subscribe a WebSocket client to an IRC channel.

        JOINs the channel if this is the first subscriber.
        """
        channel = channel.lower()
        self._callbacks[subscriber_id] = callback

        was_empty = len(self._subscriptions[channel]) == 0
        self._subscriptions[channel].add(subscriber_id)

        if was_empty and self._connected:
            await self._send(f"JOIN {channel}")
            self._stats["joins"] += 1
            logger.info(
                "IRCPool: JOIN %s (first subscriber: %s)",
                channel,
                subscriber_id[:8],
            )

    async def unsubscribe(self, channel: str, subscriber_id: str) -> None:
        """Unsubscribe a WebSocket client from an IRC channel.

        PARTs the channel if this was the last subscriber.
        """
        channel = channel.lower()
        self._subscriptions[channel].discard(subscriber_id)
        self._callbacks.pop(subscriber_id, None)

        if not self._subscriptions[channel]:
            del self._subscriptions[channel]
            if self._connected:
                await self._send(f"PART {channel} :No more listeners")
                self._stats["parts"] += 1
                logger.info("IRCPool: PART %s (no subscribers)", channel)

    async def send_message(self, channel: str, text: str) -> None:
        """Send a PRIVMSG to an IRC channel."""
        if not self._connected:
            logger.warning("IRCPool: cannot send, not connected")
            return
        # IRC messages have a max length of ~512 bytes. Truncate if needed.
        if len(text) > 450:
            text = text[:447] + "..."
        await self._send(f"PRIVMSG {channel} :{text}")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def nick(self) -> str:
        return self._nick

    @property
    def active_channels(self) -> list[str]:
        return [ch for ch, subs in self._subscriptions.items() if subs]

    @property
    def connected_clients(self) -> int:
        return len(self._callbacks)

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "connected": self._connected,
            "nick": self._nick,
            "active_channels": len(self.active_channels),
            "connected_clients": self.connected_clients,
        }
