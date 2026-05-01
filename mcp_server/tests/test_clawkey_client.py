"""Unit tests for integrations.clawkey.client.

Mocks all HTTP. Asserts URL format, response parsing, caching, error paths.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest

from integrations.clawkey import client as ck_client

pytestmark = pytest.mark.clawkey


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_cfg() -> dict:
    return {
        "base": "https://api.clawkey.ai",
        "pubkey_path": "/v1/agent/verify/public-key/{pubkey}",
        "device_path": "/v1/agent/verify/device/{device_id}",
        "cache_ttl": 300.0,
        "http_timeout": 10.0,
    }


@pytest.fixture(autouse=True)
def _isolate_module_cache() -> None:
    """Ensure cache state never leaks between tests."""
    ck_client.clear_cache()


def _patch_config(monkeypatch: pytest.MonkeyPatch, cfg: dict) -> None:
    async def fake_resolved() -> dict:
        return cfg

    monkeypatch.setattr(ck_client, "_resolved_config", fake_resolved)


class _FakeAsyncClient:
    """Context-manager-aware httpx.AsyncClient stub."""

    def __init__(self, response: httpx.Response):
        self._response = response
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._response


def _mk_response(status_code: int, json_body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_body if json_body is not None else {},
        request=httpx.Request("GET", "https://api.clawkey.ai/test"),
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_camel_case_fields(self) -> None:
        result = ck_client._parse_response(
            {
                "registered": True,
                "verified": True,
                "humanId": "hum-abc",
                "registeredAt": "2026-04-30T00:00:00Z",
            }
        )
        assert result.registered is True
        assert result.verified is True
        assert result.human_id == "hum-abc"
        assert result.registered_at == "2026-04-30T00:00:00Z"

    def test_snake_case_fields(self) -> None:
        result = ck_client._parse_response(
            {
                "registered": True,
                "verified": False,
                "human_id": "hum-snake",
                "registered_at": "2026-04-30T00:00:00Z",
            }
        )
        assert result.human_id == "hum-snake"

    def test_missing_fields_default_safe(self) -> None:
        result = ck_client._parse_response({})
        assert result.registered is False
        assert result.verified is False
        assert result.human_id is None
        assert result.registered_at is None


# ---------------------------------------------------------------------------
# verify_by_public_key
# ---------------------------------------------------------------------------


class TestVerifyByPublicKey:
    @pytest.mark.asyncio
    async def test_registered_verified(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(
            _mk_response(
                200,
                {
                    "registered": True,
                    "verified": True,
                    "humanId": "hum-1",
                    "registeredAt": "2026-04-30T00:00:00Z",
                },
            )
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            result = await ck_client.verify_by_public_key("PubKeyB58")

        assert result.registered is True
        assert result.verified is True
        assert result.human_id == "hum-1"
        assert (
            fake.calls[0]["url"]
            == "https://api.clawkey.ai/v1/agent/verify/public-key/PubKeyB58"
        )

    @pytest.mark.asyncio
    async def test_unregistered_via_404(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(_mk_response(404, {"error": "not_found"}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            result = await ck_client.verify_by_public_key("Missing")
        assert result.registered is False
        assert result.verified is False
        assert result.human_id is None

    @pytest.mark.asyncio
    async def test_unregistered_via_200_payload(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        # Upstream may return 200 with `registered: false` instead of 404.
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(_mk_response(200, {"registered": False}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            result = await ck_client.verify_by_public_key("PubX")
        assert result.registered is False
        assert result.verified is False

    @pytest.mark.asyncio
    async def test_server_error_raises(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(_mk_response(503, {"error": "down"}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            with pytest.raises(httpx.HTTPStatusError):
                await ck_client.verify_by_public_key("PubX")

    @pytest.mark.asyncio
    async def test_empty_pubkey_raises(self) -> None:
        with pytest.raises(ValueError):
            await ck_client.verify_by_public_key("")


# ---------------------------------------------------------------------------
# verify_by_device_id
# ---------------------------------------------------------------------------


class TestVerifyByDeviceId:
    @pytest.mark.asyncio
    async def test_registered_path_format(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(
            _mk_response(
                200,
                {"registered": True, "verified": True, "humanId": "hum-dev"},
            )
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            result = await ck_client.verify_by_device_id("dev-123")

        assert result.verified is True
        assert (
            fake.calls[0]["url"]
            == "https://api.clawkey.ai/v1/agent/verify/device/dev-123"
        )

    @pytest.mark.asyncio
    async def test_unregistered_via_404(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(_mk_response(404, {}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            result = await ck_client.verify_by_device_id("dev-missing")
        assert result.registered is False

    @pytest.mark.asyncio
    async def test_server_error_raises(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(_mk_response(500, {"error": "boom"}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            with pytest.raises(httpx.HTTPStatusError):
                await ck_client.verify_by_device_id("dev-x")

    @pytest.mark.asyncio
    async def test_empty_device_id_raises(self) -> None:
        with pytest.raises(ValueError):
            await ck_client.verify_by_device_id("")


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------


class TestCache:
    @pytest.mark.asyncio
    async def test_second_call_hits_cache(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(
            _mk_response(200, {"registered": True, "verified": True})
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            await ck_client.verify_by_public_key("PubCache")
            await ck_client.verify_by_public_key("PubCache")

        # Only the first call should have hit upstream
        assert len(fake.calls) == 1

    @pytest.mark.asyncio
    async def test_use_cache_false_forces_refresh(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(
            _mk_response(200, {"registered": True, "verified": True})
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            await ck_client.verify_by_public_key("PubFresh")
            await ck_client.verify_by_public_key("PubFresh", use_cache=False)
        assert len(fake.calls) == 2

    @pytest.mark.asyncio
    async def test_pubkey_and_device_caches_are_independent(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(
            _mk_response(200, {"registered": True, "verified": True})
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            await ck_client.verify_by_public_key("Same")
            await ck_client.verify_by_device_id("Same")

        # Same string used for both lookups; cache namespacing must keep
        # them separate so the second call still reaches upstream.
        assert len(fake.calls) == 2

    @pytest.mark.asyncio
    async def test_404_response_is_cached(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        _patch_config(monkeypatch, fake_cfg)
        fake = _FakeAsyncClient(_mk_response(404, {}))
        with patch.object(httpx, "AsyncClient", return_value=fake):
            await ck_client.verify_by_public_key("Ghost")
            await ck_client.verify_by_public_key("Ghost")
        assert len(fake.calls) == 1

    @pytest.mark.asyncio
    async def test_expired_entry_triggers_refetch(
        self, monkeypatch: pytest.MonkeyPatch, fake_cfg: dict
    ) -> None:
        # Tiny TTL — first call seeds, sleep advances clock past expiry.
        cfg = {**fake_cfg, "cache_ttl": 0.01}
        _patch_config(monkeypatch, cfg)
        fake = _FakeAsyncClient(
            _mk_response(200, {"registered": True, "verified": True})
        )
        with patch.object(httpx, "AsyncClient", return_value=fake):
            await ck_client.verify_by_public_key("ExpKey")
            import asyncio

            await asyncio.sleep(0.05)
            await ck_client.verify_by_public_key("ExpKey")
        assert len(fake.calls) == 2
