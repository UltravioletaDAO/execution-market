"""
Tests for the shared facilitator HTTP retry/timeout primitives.

Phase 2 SAAS_PRODUCTION_HARDENING — covers:

  * ``facilitator_timeout`` is capped at ``FACILITATOR_TIMEOUT_SECONDS`` (30s default).
  * ``facilitator_retry`` retries on transient transport errors (network / timeout /
    remote-protocol) and on 5xx without a tx hash.
  * ``facilitator_retry`` does **not** retry on 4xx (bad request / auth / idempotency).
  * ``facilitator_retry`` does **not** retry on a 5xx response that already carries
    a transaction hash (double-settle guard).
  * ``raise_for_status_if_no_tx`` leaves a 5xx-with-tx-hash un-raised, but raises on
    a 5xx without a tx hash and on any 4xx.

These tests mock ``httpx`` transport via ``httpx.MockTransport`` so no real network
calls are made and tenacity's backoff doesn't slow the suite (we patch ``time.sleep``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations._http_retry import (  # noqa: E402
    FACILITATOR_TIMEOUT_SECONDS,
    _is_retryable,
    _response_has_tx_hash,
    facilitator_retry,
    facilitator_timeout,
    raise_for_status_if_no_tx,
)

pytestmark = [pytest.mark.core, pytest.mark.payments]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status: int, body: dict | str | None = None) -> httpx.Response:
    """Build an ``httpx.Response`` wired up to a throwaway request for raise_for_status."""
    request = httpx.Request("POST", "https://facilitator.example/settle")
    if isinstance(body, dict):
        return httpx.Response(status, json=body, request=request)
    if isinstance(body, str):
        return httpx.Response(status, text=body, request=request)
    return httpx.Response(status, request=request)


def _http_status_error(
    status: int, body: dict | str | None = None
) -> httpx.HTTPStatusError:
    """Build an ``HTTPStatusError`` with a concrete response attached."""
    response = _make_response(status, body)
    return httpx.HTTPStatusError(
        message=f"HTTP {status}",
        request=response.request,
        response=response,
    )


# ---------------------------------------------------------------------------
# Timeout cap — Phase 2.2
# ---------------------------------------------------------------------------


class TestFacilitatorTimeout:
    """The timeout helper must never exceed the configured cap."""

    def test_default_timeout_matches_cap(self):
        """Default (no argument) should produce a timeout equal to the cap."""
        t = facilitator_timeout()
        # 30s default. connect bounded at 5s.
        assert t.read == float(FACILITATOR_TIMEOUT_SECONDS)
        assert t.write == float(FACILITATOR_TIMEOUT_SECONDS)
        assert t.connect == min(5.0, float(FACILITATOR_TIMEOUT_SECONDS))

    def test_timeout_capped_at_30s(self):
        """A caller asking for 300s must be clamped to 30s (or the env cap)."""
        t = facilitator_timeout(300)
        assert t.read == float(FACILITATOR_TIMEOUT_SECONDS)
        assert t.write == float(FACILITATOR_TIMEOUT_SECONDS)
        # Read/write/pool cannot exceed the cap.
        assert t.read <= 30.0
        assert t.write <= 30.0

    def test_timeout_below_cap_preserved(self):
        """A short timeout (e.g. 5s) must be preserved, not expanded to the cap."""
        t = facilitator_timeout(5)
        assert t.read == 5.0
        assert t.write == 5.0
        # Connect budget is min(5, total) — here both are 5.
        assert t.connect == 5.0

    def test_timeout_900s_capped_to_cap(self):
        """Ethereum L1 callers used to request 900s — must be clamped too."""
        t = facilitator_timeout(900)
        assert t.read == float(FACILITATOR_TIMEOUT_SECONDS)
        assert t.read <= 30.0


# ---------------------------------------------------------------------------
# Retry predicate — direct unit tests
# ---------------------------------------------------------------------------


class TestIsRetryable:
    """``_is_retryable`` decides which exceptions tenacity should retry."""

    def test_timeout_is_retryable(self):
        assert _is_retryable(httpx.ReadTimeout("read timeout")) is True
        assert _is_retryable(httpx.ConnectTimeout("connect timeout")) is True

    def test_network_error_is_retryable(self):
        assert _is_retryable(httpx.ConnectError("conn refused")) is True

    def test_remote_protocol_error_is_retryable(self):
        assert (
            _is_retryable(httpx.RemoteProtocolError("conn closed mid-stream")) is True
        )

    def test_5xx_without_tx_hash_is_retryable(self):
        exc = _http_status_error(503, {"success": False, "error": "db unavailable"})
        assert _is_retryable(exc) is True

    def test_5xx_with_tx_hash_is_not_retryable(self):
        """Double-settle guard — if the tx was broadcast, don't retry."""
        body = {
            "success": False,
            "error": "post-settle hook failed",
            "transaction": {"hash": "0xabc123"},
        }
        exc = _http_status_error(503, body)
        assert _is_retryable(exc) is False

    def test_5xx_with_top_level_tx_hash_is_not_retryable(self):
        """``txHash`` / ``tx_hash`` at top level also triggers the guard."""
        assert _is_retryable(_http_status_error(503, {"txHash": "0xabc"})) is False
        assert _is_retryable(_http_status_error(503, {"tx_hash": "0xabc"})) is False
        assert (
            _is_retryable(_http_status_error(503, {"transaction_hash": "0xabc"}))
            is False
        )

    def test_400_is_not_retryable(self):
        exc = _http_status_error(400, {"error": "bad request"})
        assert _is_retryable(exc) is False

    def test_401_is_not_retryable(self):
        exc = _http_status_error(401, {"error": "unauthorized"})
        assert _is_retryable(exc) is False

    def test_403_is_not_retryable(self):
        exc = _http_status_error(403, {"error": "forbidden"})
        assert _is_retryable(exc) is False

    def test_404_is_not_retryable(self):
        exc = _http_status_error(404, {"error": "not found"})
        assert _is_retryable(exc) is False

    def test_409_idempotency_conflict_is_not_retryable(self):
        exc = _http_status_error(409, {"error": "duplicate nonce"})
        assert _is_retryable(exc) is False

    def test_generic_exception_is_not_retryable(self):
        assert _is_retryable(ValueError("something else")) is False


# ---------------------------------------------------------------------------
# tx_hash detection
# ---------------------------------------------------------------------------


class TestResponseHasTxHash:
    """Mirror the facilitator's various tx-hash shapes."""

    def test_transaction_dict_with_hash(self):
        assert _response_has_tx_hash({"transaction": {"hash": "0xabc"}}) is True

    def test_transaction_string(self):
        assert _response_has_tx_hash({"transaction": "0xabc"}) is True

    def test_top_level_txhash(self):
        assert _response_has_tx_hash({"txHash": "0xabc"}) is True

    def test_top_level_tx_hash(self):
        assert _response_has_tx_hash({"tx_hash": "0xabc"}) is True

    def test_top_level_transaction_hash(self):
        assert _response_has_tx_hash({"transaction_hash": "0xabc"}) is True

    def test_empty_body(self):
        assert _response_has_tx_hash({}) is False

    def test_empty_transaction_dict(self):
        assert _response_has_tx_hash({"transaction": {}}) is False

    def test_non_dict_body(self):
        assert _response_has_tx_hash("not a dict") is False
        assert _response_has_tx_hash(None) is False
        assert _response_has_tx_hash([1, 2, 3]) is False


# ---------------------------------------------------------------------------
# raise_for_status_if_no_tx
# ---------------------------------------------------------------------------


class TestRaiseForStatusIfNoTx:
    """2xx never raises; 4xx always raises; 5xx raises only without tx_hash."""

    def test_2xx_does_not_raise(self):
        raise_for_status_if_no_tx(_make_response(200, {"success": True}))
        raise_for_status_if_no_tx(_make_response(204))

    def test_4xx_raises(self):
        with pytest.raises(httpx.HTTPStatusError):
            raise_for_status_if_no_tx(_make_response(400, {"error": "bad"}))
        with pytest.raises(httpx.HTTPStatusError):
            raise_for_status_if_no_tx(_make_response(403, {"error": "forbidden"}))

    def test_5xx_without_tx_hash_raises(self):
        with pytest.raises(httpx.HTTPStatusError):
            raise_for_status_if_no_tx(_make_response(500, {"error": "oops"}))

    def test_5xx_with_tx_hash_does_not_raise(self):
        """Double-settle guard — tx was broadcast, let caller handle the body."""
        response = _make_response(
            503, {"success": False, "transaction": {"hash": "0xabc"}}
        )
        # Should NOT raise.
        raise_for_status_if_no_tx(response)

    def test_5xx_with_invalid_json_raises(self):
        """If we cannot even parse JSON, err on the safe side and raise."""
        response = _make_response(500, "not-json")
        with pytest.raises(httpx.HTTPStatusError):
            raise_for_status_if_no_tx(response)


# ---------------------------------------------------------------------------
# @facilitator_retry integration — sync + async
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_backoff_sleep():
    """Neutralise tenacity's wait so the test suite runs instantly."""
    with patch("tenacity.nap.time.sleep", return_value=None):
        yield


class TestFacilitatorRetrySync:
    """Decorator semantics on synchronous callables."""

    def test_retries_on_network_error_then_succeeds(self):
        attempts = {"count": 0}

        @facilitator_retry
        def call():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise httpx.ConnectError("conn refused")
            return "ok"

        assert call() == "ok"
        assert attempts["count"] == 3

    def test_retries_on_timeout_then_succeeds(self):
        attempts = {"count": 0}

        @facilitator_retry
        def call():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise httpx.ReadTimeout("read timeout")
            return "ok"

        assert call() == "ok"
        assert attempts["count"] == 2

    def test_retries_on_5xx_then_succeeds(self):
        attempts = {"count": 0}

        @facilitator_retry
        def call():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise _http_status_error(503, {"error": "unavailable"})
            return "ok"

        assert call() == "ok"
        assert attempts["count"] == 2

    def test_does_not_retry_on_4xx(self):
        attempts = {"count": 0}

        @facilitator_retry
        def call():
            attempts["count"] += 1
            raise _http_status_error(400, {"error": "bad request"})

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            call()
        assert exc_info.value.response.status_code == 400
        # Must not have retried.
        assert attempts["count"] == 1

    def test_does_not_retry_on_401(self):
        attempts = {"count": 0}

        @facilitator_retry
        def call():
            attempts["count"] += 1
            raise _http_status_error(401, {"error": "unauthorized"})

        with pytest.raises(httpx.HTTPStatusError):
            call()
        assert attempts["count"] == 1

    def test_does_not_retry_on_5xx_with_tx_hash(self):
        """Double-settle guard — if the tx was broadcast, a single attempt is enough."""
        attempts = {"count": 0}

        @facilitator_retry
        def call():
            attempts["count"] += 1
            raise _http_status_error(
                503, {"success": False, "transaction": {"hash": "0xabc"}}
            )

        with pytest.raises(httpx.HTTPStatusError):
            call()
        # Exactly one attempt — the tx was already broadcast.
        assert attempts["count"] == 1

    def test_gives_up_after_3_attempts(self):
        attempts = {"count": 0}

        @facilitator_retry
        def call():
            attempts["count"] += 1
            raise httpx.ConnectError("persistent failure")

        with pytest.raises(httpx.ConnectError):
            call()
        assert attempts["count"] == 3  # stop_after_attempt(3)


class TestFacilitatorRetryAsync:
    """Decorator must also wrap async callables (payment_dispatcher uses async)."""

    async def test_async_retries_on_network_error_then_succeeds(self):
        attempts = {"count": 0}

        @facilitator_retry
        async def call():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise httpx.ConnectError("conn refused")
            return "async-ok"

        assert await call() == "async-ok"
        assert attempts["count"] == 2

    async def test_async_does_not_retry_on_4xx(self):
        attempts = {"count": 0}

        @facilitator_retry
        async def call():
            attempts["count"] += 1
            raise _http_status_error(400, {"error": "bad"})

        with pytest.raises(httpx.HTTPStatusError):
            await call()
        assert attempts["count"] == 1

    async def test_async_does_not_retry_on_5xx_with_tx_hash(self):
        attempts = {"count": 0}

        @facilitator_retry
        async def call():
            attempts["count"] += 1
            raise _http_status_error(502, {"tx_hash": "0xabc"})

        with pytest.raises(httpx.HTTPStatusError):
            await call()
        assert attempts["count"] == 1


# ---------------------------------------------------------------------------
# Integration: real httpx client against a MockTransport
# ---------------------------------------------------------------------------


class TestFacilitatorRetryWithMockTransport:
    """End-to-end through an actual ``httpx.AsyncClient`` + ``MockTransport``.

    This exercises the exact code path ``PaymentDispatcher._post_facilitator_json``
    takes: real httpx client, real exceptions, just faked transport.
    """

    async def test_retries_then_succeeds_on_5xx(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] < 2:
                return httpx.Response(503, json={"error": "unavailable"})
            return httpx.Response(200, json={"success": True, "txHash": "0xabc"})

        transport = httpx.MockTransport(handler)

        @facilitator_retry
        async def do_post():
            async with httpx.AsyncClient(
                transport=transport, timeout=facilitator_timeout()
            ) as client:
                resp = await client.post("https://facilitator.example/settle", json={})
            raise_for_status_if_no_tx(resp)
            return resp.json()

        result = await do_post()
        assert result["success"] is True
        assert result["txHash"] == "0xabc"
        assert calls["count"] == 2

    async def test_does_not_retry_on_4xx_through_mock(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(400, json={"error": "bad request"})

        transport = httpx.MockTransport(handler)

        @facilitator_retry
        async def do_post():
            async with httpx.AsyncClient(
                transport=transport, timeout=facilitator_timeout()
            ) as client:
                resp = await client.post("https://facilitator.example/settle", json={})
            raise_for_status_if_no_tx(resp)

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await do_post()
        assert exc_info.value.response.status_code == 400
        # No retries on 4xx.
        assert calls["count"] == 1

    async def test_5xx_with_tx_hash_skips_retry_through_mock(self):
        """The response is 5xx but carries a tx_hash — ``raise_for_status_if_no_tx``
        does not raise, so the call succeeds on first attempt with no retry."""
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(
                502,
                json={"success": False, "transaction": {"hash": "0xabc"}},
            )

        transport = httpx.MockTransport(handler)

        @facilitator_retry
        async def do_post():
            async with httpx.AsyncClient(
                transport=transport, timeout=facilitator_timeout()
            ) as client:
                resp = await client.post("https://facilitator.example/settle", json={})
            raise_for_status_if_no_tx(resp)
            return resp

        resp = await do_post()
        # Only one attempt — the tx was already broadcast.
        assert calls["count"] == 1
        assert resp.status_code == 502
        assert resp.json()["transaction"]["hash"] == "0xabc"
