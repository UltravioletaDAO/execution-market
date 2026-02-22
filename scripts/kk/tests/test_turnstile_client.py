"""
Tests for TurnstileClient — MeshRelay premium channel access.

Tests both mocked (unit) and live (integration) scenarios.
Run with: pytest scripts/kk/tests/test_turnstile_client.py -v
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.turnstile_client import (
    AccessResult,
    ChannelInfo,
    HealthStatus,
    TurnstileClient,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return TurnstileClient(base_url="http://localhost:8090")


@pytest.fixture
def mock_channels_response():
    return {
        "channels": [
            {
                "name": "#alpha-test",
                "price": "0.10",
                "currency": "USDC",
                "network": "eip155:8453",
                "durationSeconds": 1800,
                "maxSlots": 20,
                "activeSlots": 0,
                "description": "Alpha test channel",
            },
            {
                "name": "#kk-alpha",
                "price": "1.00",
                "currency": "USDC",
                "network": "eip155:8453",
                "durationSeconds": 3600,
                "maxSlots": 50,
                "activeSlots": 5,
                "description": "KK Alpha trading",
            },
        ]
    }


@pytest.fixture
def mock_health_response():
    return {
        "status": "ok",
        "irc": {"connected": True, "oper": True, "nick": "Turnstile"},
        "facilitator": {
            "url": "https://facilitator.ultravioletadao.xyz",
            "reachable": True,
        },
        "channels": 4,
        "uptime": 3600.0,
    }


@pytest.fixture
def mock_access_success():
    return {
        "status": "granted",
        "channel": "#alpha-test",
        "nick": "kk-coordinator",
        "expiresAt": "2026-02-21T23:00:00Z",
        "durationSeconds": 1800,
        "txHash": "0xabc123def456",
    }


@pytest.fixture
def mock_access_402():
    return {
        "status": "payment_required",
        "channel": "#alpha-test",
        "price": "0.10",
        "currency": "USDC",
        "network": "eip155:8453",
        "payTo": "0xe4dc963c56979E0260fc146b87eE24F18220e545",
        "facilitator": "https://facilitator.ultravioletadao.xyz",
    }


# ---------------------------------------------------------------------------
# Unit Tests (Mocked)
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_ok(self, client, mock_health_response):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_health_response)

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock()))
            mock_session_cls.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock())

            health = await client.check_health()
            assert health.ok is True
            assert health.irc_connected is True
            assert health.irc_oper is True
            assert health.facilitator_reachable is True
            assert health.channels_count == 4
            assert health.uptime == 3600.0

    @pytest.mark.asyncio
    async def test_health_error(self, client):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(side_effect=ConnectionError("refused"))
            mock_session_cls.return_value.__aexit__ = AsyncMock()

            health = await client.check_health()
            assert health.ok is False
            assert "refused" in health.error.lower() or health.error != ""


class TestListChannels:
    @pytest.mark.asyncio
    async def test_list_channels(self, client, mock_channels_response):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_channels_response)
            mock_resp.raise_for_status = MagicMock()

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock()))
            mock_session_cls.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock())

            channels = await client.list_channels()
            assert len(channels) == 2
            assert channels[0].name == "#alpha-test"
            assert channels[0].price == "0.10"
            assert channels[0].price_float == 0.10
            assert channels[0].duration_seconds == 1800
            assert channels[0].is_available is True
            assert channels[0].channel_slug == "alpha-test"

            assert channels[1].name == "#kk-alpha"
            assert channels[1].active_slots == 5
            assert channels[1].available_slots == 45


class TestRequestAccess:
    @pytest.mark.asyncio
    async def test_access_success(self, client, mock_access_success):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_access_success)

            mock_session = AsyncMock()
            mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock()))
            mock_session_cls.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock())

            result = await client.request_access(
                channel="alpha-test",
                nick="kk-coordinator",
                payment_signature="base64sig==",
            )
            assert result.success is True
            assert result.channel == "#alpha-test"
            assert result.nick == "kk-coordinator"
            assert result.tx_hash == "0xabc123def456"
            assert result.duration_seconds == 1800

    @pytest.mark.asyncio
    async def test_access_payment_required(self, client, mock_access_402):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 402
            mock_resp.json = AsyncMock(return_value=mock_access_402)

            mock_session = AsyncMock()
            mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock()))
            mock_session_cls.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock())

            result = await client.request_access(
                channel="alpha-test",
                nick="kk-coordinator",
                payment_signature="invalid",
            )
            assert result.success is False
            assert result.error == "Payment required"
            assert result.price == "0.10"
            assert result.pay_to == "0xe4dc963c56979E0260fc146b87eE24F18220e545"


class TestChannelInfo:
    def test_channel_slug(self):
        ch = ChannelInfo(
            name="#kk-alpha",
            price="1.00",
            currency="USDC",
            network="eip155:8453",
            duration_seconds=3600,
            max_slots=50,
            active_slots=10,
            description="Test",
        )
        assert ch.channel_slug == "kk-alpha"
        assert ch.price_float == 1.0
        assert ch.available_slots == 40
        assert ch.is_available is True

    def test_channel_full(self):
        ch = ChannelInfo(
            name="#full",
            price="0.50",
            currency="USDC",
            network="eip155:8453",
            duration_seconds=1800,
            max_slots=5,
            active_slots=5,
            description="Full channel",
        )
        assert ch.is_available is False
        assert ch.available_slots == 0


# ---------------------------------------------------------------------------
# Live Integration Tests (require Turnstile running)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not pytest.importorskip("aiohttp", reason="aiohttp not installed"),
    reason="aiohttp required",
)
class TestLiveIntegration:
    """Run against live Turnstile. Skip if unreachable."""

    @pytest.fixture
    def live_client(self):
        return TurnstileClient()  # Uses default production URL

    @pytest.mark.asyncio
    async def test_live_health(self, live_client):
        health = await live_client.check_health()
        if not health.ok:
            pytest.skip("Turnstile not reachable")
        assert health.irc_connected is True
        assert health.facilitator_reachable is True

    @pytest.mark.asyncio
    async def test_live_list_channels(self, live_client):
        try:
            channels = await live_client.list_channels()
        except Exception:
            pytest.skip("Turnstile not reachable")
        assert len(channels) >= 1
        assert all(ch.name.startswith("#") for ch in channels)
        assert all(ch.currency == "USDC" for ch in channels)

    @pytest.mark.asyncio
    async def test_live_get_channel(self, live_client):
        try:
            ch = await live_client.get_channel("alpha-test")
        except Exception:
            pytest.skip("Turnstile not reachable")
        if ch is None:
            pytest.skip("alpha-test channel not configured")
        assert ch.name == "#alpha-test"
        assert ch.price_float == 0.10

    @pytest.mark.asyncio
    async def test_live_payment_requirements(self, live_client):
        try:
            reqs = await live_client.get_payment_requirements("alpha-test")
        except Exception:
            pytest.skip("Turnstile not reachable")
        if reqs is None:
            pytest.skip("Could not get payment requirements")
        assert "price" in reqs or "status" in reqs
