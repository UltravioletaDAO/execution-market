"""
Karma Kadabra V2 — Turnstile Client

Client for MeshRelay's Turnstile bot API. Handles channel listing,
health checks, and x402 payment-gated channel access.

Turnstile is the payment gate for premium IRC channels on MeshRelay.
It uses x402 (EIP-3009 gasless) via the Ultravioleta Facilitator.

Usage:
    from lib.turnstile_client import TurnstileClient

    client = TurnstileClient()
    channels = await client.list_channels()
    result = await client.request_access(
        channel="kk-alpha",
        nick="kk-coordinator",
        wallet_key="0x...",
    )
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger("kk.turnstile")

TURNSTILE_BASE_URL = "http://54.156.88.5:8090"
FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
DEFAULT_NETWORK = "eip155:8453"  # Base mainnet

# USDC on Base
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # seconds


@dataclass
class ChannelInfo:
    """Premium channel metadata from Turnstile."""

    name: str
    price: str
    currency: str
    network: str
    duration_seconds: int
    max_slots: int
    active_slots: int
    description: str

    @property
    def price_float(self) -> float:
        return float(self.price)

    @property
    def available_slots(self) -> int:
        return self.max_slots - self.active_slots

    @property
    def is_available(self) -> bool:
        return self.active_slots < self.max_slots

    @property
    def channel_slug(self) -> str:
        """Channel name without # prefix, for URL params."""
        return self.name.lstrip("#")


@dataclass
class AccessResult:
    """Result of a channel access request."""

    success: bool
    channel: str = ""
    nick: str = ""
    expires_at: str = ""
    duration_seconds: int = 0
    tx_hash: str = ""
    error: str = ""

    # Payment requirement info (when 402)
    price: str = ""
    currency: str = ""
    network: str = ""
    pay_to: str = ""


@dataclass
class HealthStatus:
    """Turnstile health status."""

    ok: bool
    irc_connected: bool = False
    irc_oper: bool = False
    facilitator_reachable: bool = False
    channels_count: int = 0
    uptime: float = 0.0
    error: str = ""


class TurnstileClient:
    """Client for MeshRelay Turnstile bot API.

    Handles listing channels, checking health, and requesting
    x402 payment-gated access to premium IRC channels.
    """

    def __init__(
        self,
        base_url: str = TURNSTILE_BASE_URL,
        facilitator_url: str = FACILITATOR_URL,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.facilitator_url = facilitator_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def check_health(self) -> HealthStatus:
        """Check Turnstile service health."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    if resp.status != 200:
                        return HealthStatus(
                            ok=False, error=f"HTTP {resp.status}"
                        )
                    data = await resp.json()
                    return HealthStatus(
                        ok=data.get("status") == "ok",
                        irc_connected=data.get("irc", {}).get("connected", False),
                        irc_oper=data.get("irc", {}).get("oper", False),
                        facilitator_reachable=data.get("facilitator", {}).get(
                            "reachable", False
                        ),
                        channels_count=data.get("channels", 0),
                        uptime=data.get("uptime", 0.0),
                    )
        except Exception as e:
            return HealthStatus(ok=False, error=str(e))

    async def list_channels(self) -> list[ChannelInfo]:
        """List all premium channels with pricing."""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(f"{self.base_url}/api/channels") as resp:
                resp.raise_for_status()
                data = await resp.json()
                return [
                    ChannelInfo(
                        name=ch["name"],
                        price=ch["price"],
                        currency=ch["currency"],
                        network=ch["network"],
                        duration_seconds=ch["durationSeconds"],
                        max_slots=ch["maxSlots"],
                        active_slots=ch["activeSlots"],
                        description=ch["description"],
                    )
                    for ch in data.get("channels", [])
                ]

    async def get_channel(self, channel_name: str) -> ChannelInfo | None:
        """Get info for a specific channel. Returns None if not found."""
        channels = await self.list_channels()
        # Normalize: allow with or without #
        target = channel_name if channel_name.startswith("#") else f"#{channel_name}"
        for ch in channels:
            if ch.name == target:
                return ch
        return None

    async def request_access(
        self,
        channel: str,
        nick: str,
        payment_signature: str,
    ) -> AccessResult:
        """Request access to a premium channel with x402 payment.

        Args:
            channel: Channel name (with or without #).
            nick: IRC nick that should receive access.
                  Must be connected to irc.meshrelay.xyz BEFORE calling.
            payment_signature: x402 PAYMENT-SIGNATURE header value
                (base64-encoded EIP-3009 authorization).

        Returns:
            AccessResult with success status, expiry, and tx hash.
        """
        slug = channel.lstrip("#")

        for attempt in range(MAX_RETRIES):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(
                        f"{self.base_url}/api/access/{slug}",
                        json={"nick": nick},
                        headers={
                            "Content-Type": "application/json",
                            "PAYMENT-SIGNATURE": payment_signature,
                        },
                    ) as resp:
                        data = await resp.json()

                        if resp.status == 200:
                            return AccessResult(
                                success=True,
                                channel=data.get("channel", f"#{slug}"),
                                nick=data.get("nick", nick),
                                expires_at=data.get("expiresAt", ""),
                                duration_seconds=data.get("durationSeconds", 0),
                                tx_hash=data.get("txHash", ""),
                            )
                        elif resp.status == 402:
                            return AccessResult(
                                success=False,
                                channel=f"#{slug}",
                                error="Payment required",
                                price=data.get("price", ""),
                                currency=data.get("currency", ""),
                                network=data.get("network", ""),
                                pay_to=data.get("payTo", ""),
                            )
                        else:
                            error_msg = data.get("message", f"HTTP {resp.status}")
                            if attempt < MAX_RETRIES - 1 and resp.status >= 500:
                                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                                logger.warning(
                                    f"Turnstile error (attempt {attempt + 1}): "
                                    f"{error_msg}. Retrying in {wait:.0f}s..."
                                )
                                await asyncio.sleep(wait)
                                continue
                            return AccessResult(
                                success=False,
                                channel=f"#{slug}",
                                error=error_msg,
                            )

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning(
                        f"Turnstile request failed (attempt {attempt + 1}): "
                        f"{e}. Retrying in {wait:.0f}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    return AccessResult(
                        success=False,
                        channel=f"#{slug}",
                        error=str(e),
                    )

        return AccessResult(success=False, error="Max retries exceeded")

    async def get_payment_requirements(
        self, channel: str
    ) -> dict[str, Any] | None:
        """Get payment requirements for a channel without paying.

        Sends a request without payment signature to get the 402 response
        with price, network, and pay-to address.
        """
        slug = channel.lstrip("#")
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/access/{slug}",
                    json={"nick": "price-check"},
                ) as resp:
                    if resp.status == 402:
                        return await resp.json()
                    return None
        except Exception:
            return None


async def _demo():
    """Quick demo — list channels and check health."""
    client = TurnstileClient()

    print("=== Turnstile Health ===")
    health = await client.check_health()
    print(f"  Status: {'OK' if health.ok else 'ERROR'}")
    print(f"  IRC: connected={health.irc_connected}, oper={health.irc_oper}")
    print(f"  Facilitator: reachable={health.facilitator_reachable}")
    print(f"  Channels: {health.channels_count}")
    print(f"  Uptime: {health.uptime:.0f}s")

    print("\n=== Premium Channels ===")
    channels = await client.list_channels()
    for ch in channels:
        slots = f"{ch.active_slots}/{ch.max_slots}"
        duration = f"{ch.duration_seconds // 60}min"
        print(f"  {ch.name}: ${ch.price} {ch.currency} / {duration} [{slots} slots] — {ch.description}")


if __name__ == "__main__":
    asyncio.run(_demo())
