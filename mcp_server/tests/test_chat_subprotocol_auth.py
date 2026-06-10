"""
Tests for WebSocket subprotocol bearer auth on the chat relay.

Security audit 2026-06-09, finding L-72 (WS-FRONT): the chat token used to
travel as ``?token=<JWT>`` in the URL, leaking into ALB access logs. Mobile
clients now send it via the ``Sec-WebSocket-Protocol`` header (see
``em-mobile/lib/wsAuth.ts``): two subprotocols are offered — the sentinel
``em-bearer`` and ``bearer.<JWT>``. The server must extract the token, echo
the sentinel in the handshake (RFC 6455), and keep the ``?token=`` query
fallback working for web dashboard clients.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.websockets import WebSocketDisconnect

pytestmark = pytest.mark.infrastructure

# Same shape as the fixture used in em-mobile/__tests__/wsAuth.test.ts
VALID_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ3b3JrZXIifQ.s3cr3t-signature_value"
TASK_ID = "abcd1234-5678-9012-3456-789012345678"


# =========================================================================
# Unit tests — _negotiate_subprotocol_auth parsing
# =========================================================================


class _ScopeOnlyWS:
    """Minimal stand-in exposing the ASGI scope like starlette.WebSocket."""

    def __init__(self, subprotocols):
        self.scope = {"subprotocols": subprotocols}


class TestNegotiateSubprotocolAuth:
    def test_sentinel_plus_bearer_yields_token_and_echoes_sentinel(self):
        from chat.relay import (
            WS_AUTH_SENTINEL,
            WS_BEARER_PREFIX,
            _negotiate_subprotocol_auth,
        )

        ws = _ScopeOnlyWS([WS_AUTH_SENTINEL, f"{WS_BEARER_PREFIX}{VALID_TOKEN}"])
        token, echo = _negotiate_subprotocol_auth(ws)
        assert token == VALID_TOKEN
        assert echo == WS_AUTH_SENTINEL

    def test_no_subprotocols_returns_nothing(self):
        from chat.relay import _negotiate_subprotocol_auth

        assert _negotiate_subprotocol_auth(_ScopeOnlyWS([])) == (None, None)
        # Scope may omit the key entirely (plain query-string clients)
        ws = _ScopeOnlyWS([])
        ws.scope = {}
        assert _negotiate_subprotocol_auth(ws) == (None, None)

    def test_sentinel_without_bearer_entry_returns_nothing(self):
        from chat.relay import WS_AUTH_SENTINEL, _negotiate_subprotocol_auth

        assert _negotiate_subprotocol_auth(_ScopeOnlyWS([WS_AUTH_SENTINEL])) == (
            None,
            None,
        )

    def test_bearer_without_sentinel_is_not_recognized(self):
        from chat.relay import WS_BEARER_PREFIX, _negotiate_subprotocol_auth

        ws = _ScopeOnlyWS([f"{WS_BEARER_PREFIX}{VALID_TOKEN}"])
        assert _negotiate_subprotocol_auth(ws) == (None, None)

    def test_empty_bearer_value_returns_nothing(self):
        from chat.relay import (
            WS_AUTH_SENTINEL,
            WS_BEARER_PREFIX,
            _negotiate_subprotocol_auth,
        )

        ws = _ScopeOnlyWS([WS_AUTH_SENTINEL, WS_BEARER_PREFIX])
        assert _negotiate_subprotocol_auth(ws) == (None, None)

    def test_constants_match_mobile_wire_format(self):
        """Must mirror em-mobile/lib/wsAuth.ts exactly."""
        from chat.relay import WS_AUTH_SENTINEL, WS_BEARER_PREFIX

        assert WS_AUTH_SENTINEL == "em-bearer"
        assert WS_BEARER_PREFIX == "bearer."


# =========================================================================
# Endpoint tests — direct invocation with a FakeWebSocket
# (pattern from tests/test_websocket_auth_hardening.py)
# =========================================================================


class FakeWebSocket:
    """Fake starlette WebSocket capturing accept/close/send calls."""

    def __init__(self, subprotocols=None):
        self.scope = {"subprotocols": subprotocols or []}
        self.accepted = False
        self.accepted_subprotocol = None
        self.closed = False
        self.close_code = None
        self.close_reason = None
        self.sent = []

    async def accept(self, subprotocol=None, headers=None):
        self.accepted = True
        self.accepted_subprotocol = subprotocol

    async def send_json(self, data):
        self.sent.append(data)

    async def receive_json(self):
        # Disconnect right after the history payload — enough to exercise
        # the full handshake without a real message loop.
        raise WebSocketDisconnect(code=1000)

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True
        self.close_code = code
        self.close_reason = reason


@pytest.fixture
def relay_env(monkeypatch):
    """Mock auth/IRC/log/config around chat.relay.chat_websocket.

    Yields ``seen_tokens`` — every token the endpoint handed to
    ``_verify_token``.
    """
    from chat import relay
    from chat.irc_pool import IRCPool

    seen_tokens: list = []

    async def fake_verify(token):
        seen_tokens.append(token)
        if token == VALID_TOKEN:
            return {
                "executor_id": "exec-1",
                "wallet": "0x" + "ab" * 20,
                "nick": "tester",
                "user_id": "user-1",
            }
        return None

    async def fake_participant(task_id, user_info):
        return True

    monkeypatch.setattr(relay, "_verify_token", fake_verify)
    monkeypatch.setattr(relay, "_is_task_participant", fake_participant)

    log_svc = MagicMock()
    log_svc.get_history = AsyncMock(return_value=[])
    log_svc.log_message = AsyncMock()
    monkeypatch.setattr(relay, "get_log_service", lambda: log_svc)

    pool = MagicMock()
    pool.subscribe = AsyncMock()
    pool.unsubscribe = AsyncMock()
    pool.send_message = AsyncMock()
    monkeypatch.setattr(IRCPool, "get_instance", classmethod(lambda cls: pool))

    # Feature flag: enabled
    try:
        from config.platform_config import PlatformConfig

        monkeypatch.setattr(PlatformConfig, "get", AsyncMock(return_value=True))
    except Exception:
        pass  # endpoint fails open if config is unavailable

    return seen_tokens


class TestChatWebSocketAuth:
    @pytest.mark.asyncio
    async def test_subprotocol_auth_accepted_and_sentinel_echoed(self, relay_env):
        from chat.relay import chat_websocket

        ws = FakeWebSocket(subprotocols=["em-bearer", f"bearer.{VALID_TOKEN}"])
        await chat_websocket(ws, TASK_ID, token="")

        assert ws.accepted is True
        # RFC 6455: server must select an offered subprotocol — the sentinel,
        # never the bearer entry (token stays out of response headers).
        assert ws.accepted_subprotocol == "em-bearer"
        assert relay_env == [VALID_TOKEN]
        # History payload delivered after accept
        assert ws.sent and ws.sent[0]["task_id"] == TASK_ID

    @pytest.mark.asyncio
    async def test_query_token_fallback_still_works(self, relay_env):
        """Web dashboard clients still authenticate via ?token= (no subprotocol)."""
        from chat.relay import chat_websocket

        ws = FakeWebSocket(subprotocols=[])
        await chat_websocket(ws, TASK_ID, token=VALID_TOKEN)

        assert ws.accepted is True
        # No subprotocols offered → none selected (legacy behavior intact)
        assert ws.accepted_subprotocol is None
        assert relay_env == [VALID_TOKEN]
        assert ws.sent and ws.sent[0]["task_id"] == TASK_ID

    @pytest.mark.asyncio
    async def test_bad_subprotocol_token_rejected(self, relay_env):
        from chat.relay import chat_websocket

        ws = FakeWebSocket(subprotocols=["em-bearer", "bearer.not-a-valid-token"])
        await chat_websocket(ws, TASK_ID, token="")

        assert ws.accepted is False
        assert ws.closed is True
        assert ws.close_code == 4001

    @pytest.mark.asyncio
    async def test_bad_query_token_rejected(self, relay_env):
        from chat.relay import chat_websocket

        ws = FakeWebSocket(subprotocols=[])
        await chat_websocket(ws, TASK_ID, token="invalid")

        assert ws.accepted is False
        assert ws.closed is True
        assert ws.close_code == 4001

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self, relay_env):
        from chat.relay import chat_websocket

        ws = FakeWebSocket(subprotocols=[])
        await chat_websocket(ws, TASK_ID, token="")

        assert ws.accepted is False
        assert ws.closed is True
        assert ws.close_code == 4001
        assert relay_env == [""]

    @pytest.mark.asyncio
    async def test_subprotocol_token_takes_precedence_over_query(self, relay_env):
        from chat.relay import chat_websocket

        ws = FakeWebSocket(subprotocols=["em-bearer", f"bearer.{VALID_TOKEN}"])
        await chat_websocket(ws, TASK_ID, token="stale-query-token")

        assert ws.accepted is True
        assert ws.accepted_subprotocol == "em-bearer"
        assert relay_env == [VALID_TOKEN]


# =========================================================================
# Handshake integration — real ASGI header parsing via TestClient
# (skipped in envs with the httpx/starlette TestClient incompatibility,
# same guard as tests/test_a2a_protocol.py)
# =========================================================================


class TestChatWebSocketHandshake:
    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from chat.relay import router

        app = FastAPI()
        app.include_router(router)
        try:
            return TestClient(app)
        except TypeError:
            pytest.skip("httpx/starlette TestClient incompatibility")

    def test_sec_websocket_protocol_header_round_trip(self, relay_env, client):
        """Token sent in the Sec-WebSocket-Protocol header; sentinel echoed."""
        with client.websocket_connect(
            f"/ws/chat/{TASK_ID}",
            subprotocols=["em-bearer", f"bearer.{VALID_TOKEN}"],
        ) as ws:
            assert ws.accepted_subprotocol == "em-bearer"
            history = ws.receive_json()
            assert history["task_id"] == TASK_ID
        assert relay_env == [VALID_TOKEN]

    def test_query_fallback_round_trip(self, relay_env, client):
        with client.websocket_connect(f"/ws/chat/{TASK_ID}?token={VALID_TOKEN}") as ws:
            assert ws.accepted_subprotocol is None
            history = ws.receive_json()
            assert history["task_id"] == TASK_ID
        assert relay_env == [VALID_TOKEN]
