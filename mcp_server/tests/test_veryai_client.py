"""Unit tests for integrations.veryai.client.

Mocks all HTTP. Asserts URL format, JWT round-trip, error paths.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import httpx
import pytest

# These env vars must be set BEFORE importing the client module — the module
# captures them at import time. The conftest set them in another order, so we
# enforce here for safety.
os.environ.setdefault("VERYAI_CLIENT_ID", "em-test-client")
os.environ.setdefault("VERYAI_CLIENT_SECRET", "em-test-secret")
os.environ.setdefault("VERYAI_REDIRECT_URI", "https://em.test/api/v1/very-id/callback")
os.environ.setdefault("VERYAI_STATE_SECRET", "em-test-state-secret")

from integrations.veryai import client as veryai_client  # noqa: E402

pytestmark = pytest.mark.core


def _patch_module_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the module-level captured env vars to known test values."""
    monkeypatch.setattr(veryai_client, "VERYAI_CLIENT_ID", "em-test-client")
    monkeypatch.setattr(veryai_client, "VERYAI_CLIENT_SECRET", "em-test-secret")
    monkeypatch.setattr(
        veryai_client,
        "VERYAI_REDIRECT_URI",
        "https://em.test/api/v1/very-id/callback",
    )
    monkeypatch.setattr(veryai_client, "VERYAI_STATE_SECRET", "em-test-state-secret")


@pytest.fixture
def fake_paths() -> dict:
    return {
        "base": "https://api.very.org",
        "authorize": "/oauth2/authorize",
        "token": "/oauth2/token",
        "userinfo": "/oauth2/userinfo",
        "scope": "openid",
    }


# ---------------------------------------------------------------------------
# PKCE
# ---------------------------------------------------------------------------


class TestPKCE:
    def test_verifier_length_in_rfc7636_range(self):
        v, c = veryai_client.generate_pkce()
        assert 43 <= len(v) <= 128
        assert len(c) == 43  # SHA-256 base64url-no-pad

    def test_challenge_is_sha256_of_verifier(self):
        import base64
        import hashlib

        v, c = veryai_client.generate_pkce()
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(v.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        assert c == expected

    def test_verifiers_are_unique_per_call(self):
        verifiers = {veryai_client.generate_pkce()[0] for _ in range(20)}
        assert len(verifiers) == 20  # all unique


# ---------------------------------------------------------------------------
# State token
# ---------------------------------------------------------------------------


class TestStateToken:
    def test_round_trip_preserves_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_module_env(monkeypatch)
        token = veryai_client.create_state_token("executor-uuid", "verifier-xyz")
        decoded = veryai_client.verify_state_token(token)
        assert decoded["executor_id"] == "executor-uuid"
        assert decoded["code_verifier"] == "verifier-xyz"
        assert decoded["action"] == veryai_client.DEFAULT_ACTION
        assert "exp" in decoded and "iat" in decoded

    def test_invalid_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_module_env(monkeypatch)
        with pytest.raises(veryai_client.StateTokenError):
            veryai_client.verify_state_token("not-a-real-token")

    def test_expired_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_module_env(monkeypatch)
        # Negative TTL -> already expired
        token = veryai_client.create_state_token(
            "executor-uuid", "verifier", ttl_seconds=-1
        )
        with pytest.raises(veryai_client.StateTokenError):
            veryai_client.verify_state_token(token)

    def test_tampered_signature_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_module_env(monkeypatch)
        token = veryai_client.create_state_token("executor-uuid", "verifier")
        # Flip last char of signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(veryai_client.StateTokenError):
            veryai_client.verify_state_token(tampered)

    def test_missing_secret_raises_value_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(veryai_client, "VERYAI_STATE_SECRET", "")
        with pytest.raises(ValueError):
            veryai_client.create_state_token("executor-uuid", "verifier")


# ---------------------------------------------------------------------------
# Authorization URL
# ---------------------------------------------------------------------------


class TestAuthorizationUrl:
    @pytest.mark.asyncio
    async def test_url_has_required_params(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        result = await veryai_client.get_authorization_url("executor-1")
        assert result.url.startswith("https://api.very.org/oauth2/authorize?")
        assert "response_type=code" in result.url
        assert "client_id=em-test-client" in result.url
        assert "code_challenge_method=S256" in result.url
        assert "code_challenge=" in result.url
        assert f"state={result.state}" in result.url or "state=" in result.url
        assert result.code_verifier  # surfaced for tests

    @pytest.mark.asyncio
    async def test_state_round_trips_with_returned_verifier(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        result = await veryai_client.get_authorization_url("executor-2")
        decoded = veryai_client.verify_state_token(result.state)
        assert decoded["executor_id"] == "executor-2"
        assert decoded["code_verifier"] == result.code_verifier

    @pytest.mark.asyncio
    async def test_missing_client_id_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_module_env(monkeypatch)
        monkeypatch.setattr(veryai_client, "VERYAI_CLIENT_ID", "")
        with pytest.raises(ValueError):
            await veryai_client.get_authorization_url("executor-1")


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------


class _FakeAsyncClient:
    """Context-manager-aware httpx.AsyncClient stub."""

    def __init__(self, response: httpx.Response):
        self._response = response
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self._response

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._response


def _mk_response(status_code: int, json_body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_body or {},
        request=httpx.Request("POST", "https://api.very.org/test"),
    )


class TestTokenExchange:
    @pytest.mark.asyncio
    async def test_success_returns_token_result(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        fake = _FakeAsyncClient(
            _mk_response(
                200,
                {
                    "access_token": "AT-1",
                    "id_token": "ID-1",
                    "refresh_token": "RT-1",
                    "expires_in": 7200,
                    "token_type": "Bearer",
                },
            )
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            result = await veryai_client.exchange_code_for_token(
                code="abc", code_verifier="ver"
            )

        assert result.access_token == "AT-1"
        assert result.id_token == "ID-1"
        assert result.expires_in == 7200
        # Verify the request body included PKCE verifier + grant type
        call = fake.calls[0]
        assert call["url"].endswith("/oauth2/token")
        body = call["data"]
        assert body["grant_type"] == "authorization_code"
        assert body["code_verifier"] == "ver"
        assert body["client_id"] == "em-test-client"
        assert body["client_secret"] == "em-test-secret"

    @pytest.mark.asyncio
    async def test_non_200_raises_http_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        fake = _FakeAsyncClient(_mk_response(401, {"error": "invalid_client"}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            with pytest.raises(httpx.HTTPStatusError):
                await veryai_client.exchange_code_for_token(code="x", code_verifier="y")


# ---------------------------------------------------------------------------
# Userinfo
# ---------------------------------------------------------------------------


class TestUserInfo:
    @pytest.mark.asyncio
    async def test_extracts_sub_and_level(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        fake = _FakeAsyncClient(
            _mk_response(
                200,
                {
                    "sub": "veryai|abc-123",
                    "verification_level": "palm_dual",
                    "email": "x@y.z",
                },
            )
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            info = await veryai_client.get_userinfo("AT-1")

        assert info.sub == "veryai|abc-123"
        assert info.verification_level == "palm_dual"
        assert info.raw["email"] == "x@y.z"
        # Bearer header was set
        assert fake.calls[0]["headers"]["Authorization"] == "Bearer AT-1"

    @pytest.mark.asyncio
    async def test_missing_sub_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        fake = _FakeAsyncClient(
            _mk_response(200, {"verification_level": "palm_single"})
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            with pytest.raises(ValueError):
                await veryai_client.get_userinfo("AT-1")

    @pytest.mark.asyncio
    async def test_default_level_when_absent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        fake = _FakeAsyncClient(_mk_response(200, {"sub": "veryai|x"}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            info = await veryai_client.get_userinfo("AT-1")
        assert info.verification_level == "unverified"

    @pytest.mark.asyncio
    async def test_non_200_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_paths: dict,
    ) -> None:
        _patch_module_env(monkeypatch)

        async def fake_paths_fn() -> dict:
            return fake_paths

        monkeypatch.setattr(veryai_client, "_resolved_paths", fake_paths_fn)

        fake = _FakeAsyncClient(_mk_response(401, {"error": "invalid_token"}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            with pytest.raises(httpx.HTTPStatusError):
                await veryai_client.get_userinfo("AT-bad")
