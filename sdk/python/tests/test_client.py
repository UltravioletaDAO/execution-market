"""Tests for execution_market.client.ExecutionMarketClient (post-OWS migration).

These tests exercise the wire-format behaviour that matters most for
agents-in-production: deterministic idempotency, retry-on-429, and the
constructor invariants. No real OWS subprocess and no real HTTP — every
external call is stubbed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from execution_market._signer import task_fingerprint
from execution_market.client import ExecutionMarketClient
from execution_market.exceptions import AuthenticationError

# ----------------------------------------------------------------------
# Fixtures / helpers
# ----------------------------------------------------------------------


def _make_client() -> ExecutionMarketClient:
    """Construct a client and stub the OWS signer so no subprocess runs."""
    c = ExecutionMarketClient(
        wallet_name="test-agent",
        wallet_address="0x" + "a" * 40,
        chain_id=8453,
        base_url="https://api.execution.market",
    )

    # Replace _sign_headers with an async stub that returns predictable headers.
    async def fake_sign_headers(method: str, url: str, body=None) -> dict[str, str]:
        return {
            "Signature": "eth=:FAKE:",
            "Signature-Input": "eth=()",
        }

    c._ows._sign_headers = fake_sign_headers  # type: ignore[assignment]
    return c


def _fake_task_payload(task_id: str = "task-1", status: str = "published") -> dict[str, Any]:
    """Server response shape for a single task."""
    return {
        "id": task_id,
        "title": "Verify storefront",
        "instructions": "Photo of front entrance",
        "category": "physical_presence",
        "bounty_usd": 0.10,
        "status": status,
        "deadline": (datetime.now(timezone.utc)).isoformat(),
        "evidence_required": ["photo_geo"],
        "location_hint": None,
        "executor_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {},
    }


def _ok_response(payload: dict[str, Any], status_code: int = 200) -> MagicMock:
    """Build a fake httpx.Response that satisfies _handle_response()."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {}
    resp.json = MagicMock(return_value=payload)
    resp.raise_for_status = MagicMock()
    resp.url = "https://api.execution.market/test"
    return resp


def _http_error_response(status_code: int) -> MagicMock:
    """Build a fake httpx.Response whose .raise_for_status raises HTTPStatusError."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {}
    resp.url = "https://api.execution.market/test"

    request = MagicMock(spec=httpx.Request)

    def _raise() -> None:
        raise httpx.HTTPStatusError(
            f"server returned {status_code}",
            request=request,
            response=resp,
        )

    resp.raise_for_status = _raise
    return resp


# ----------------------------------------------------------------------
# Constructor
# ----------------------------------------------------------------------


def test_constructor_requires_wallet_name():
    with pytest.raises(ValueError, match="wallet_name and wallet_address"):
        ExecutionMarketClient(wallet_name="", wallet_address="0x" + "a" * 40)


def test_constructor_requires_wallet_address():
    with pytest.raises(ValueError, match="wallet_name and wallet_address"):
        ExecutionMarketClient(wallet_name="agent", wallet_address="")


def test_constructor_no_api_key_kwarg():
    """`api_key=` must NOT be a recognized keyword (clean break, not dual-auth)."""
    with pytest.raises(TypeError):
        # The signature should reject api_key; not silently swallow it.
        ExecutionMarketClient(
            api_key="should-fail",  # type: ignore[call-arg]
            wallet_name="agent",
            wallet_address="0x" + "a" * 40,
        )


# ----------------------------------------------------------------------
# create_task — deterministic X-Idempotency-Key
# ----------------------------------------------------------------------


def test_create_task_sets_deterministic_idempotency_key():
    """Calling create_task twice with the same args produces the same
    X-Idempotency-Key — the dedupe contract documented in the skill.

    A retry with the same body must hit the server's idempotency cache
    and return the original task instead of creating a duplicate. A
    uuid4 here would defeat that.
    """
    c = _make_client()
    captured_headers: list[dict[str, str]] = []

    def fake_post(path, content=None, headers=None):
        captured_headers.append(dict(headers or {}))
        return _ok_response(_fake_task_payload())

    c._client.post = fake_post  # type: ignore[method-assign]

    kwargs = dict(
        title="Verify storefront open",
        instructions="Photo with GPS",
        category="physical_presence",
        bounty_usd=0.10,
        deadline_hours=4,
        evidence_required=["photo_geo"],
    )
    c.create_task(**kwargs)
    c.create_task(**kwargs)

    assert len(captured_headers) == 2
    k1 = captured_headers[0]["X-Idempotency-Key"]
    k2 = captured_headers[1]["X-Idempotency-Key"]
    assert k1 == k2, "Idempotency key must be deterministic for identical bodies"

    # And it must equal task_fingerprint of the actual body we expect to send.
    expected = task_fingerprint({
        "title": "Verify storefront open",
        "instructions": "Photo with GPS",
        "category": "physical_presence",
        "bounty_usd": 0.10,
        "deadline_hours": 4,
        "evidence_required": ["photo_geo"],
        "evidence_optional": None,
        "location_hint": None,
        "min_reputation": 0,
        "payment_token": "USDC",
        "metadata": {},
    })
    assert k1 == expected


def test_create_task_idempotency_key_differs_when_bounty_differs():
    """Different bounty → different fingerprint → different idempotency key."""
    c = _make_client()
    captured_headers: list[dict[str, str]] = []

    def fake_post(path, content=None, headers=None):
        captured_headers.append(dict(headers or {}))
        return _ok_response(_fake_task_payload())

    c._client.post = fake_post  # type: ignore[method-assign]

    common = dict(
        title="T",
        instructions="I" * 30,
        category="physical_presence",
        deadline_hours=4,
        evidence_required=["photo"],
    )
    c.create_task(bounty_usd=0.10, **common)
    c.create_task(bounty_usd=0.20, **common)

    assert captured_headers[0]["X-Idempotency-Key"] != captured_headers[1]["X-Idempotency-Key"]


# ----------------------------------------------------------------------
# wait_for_completion — 429 retry hardening
# ----------------------------------------------------------------------


def test_wait_for_completion_retries_on_429():
    """get_task may raise httpx.HTTPStatusError 429 transiently; the
    `with_backoff` wrapper around it should retry until success.
    """
    c = _make_client()

    # Fail twice with 429, then return a completed task.
    call_count = {"n": 0}

    def fake_get_task(task_id: str):
        call_count["n"] += 1
        if call_count["n"] < 3:
            resp = _http_error_response(429)
            raise httpx.HTTPStatusError("rate limited", request=MagicMock(), response=resp)
        # Third call: return a completed Task object.
        from execution_market.types import Task, TaskCategory, TaskStatus
        return Task(
            id=task_id,
            title="t",
            instructions="i",
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=0.10,
            status=TaskStatus.COMPLETED,
            deadline=datetime.now(timezone.utc),
            evidence_required=["photo"],
        )

    c.get_task = fake_get_task  # type: ignore[method-assign]
    c.get_submissions = MagicMock(return_value=[])  # type: ignore[method-assign]

    # Patch asyncio.sleep inside _signer.with_backoff so the retry loop doesn't actually sleep.
    async def fast_sleep(_):
        return None

    with patch("execution_market._signer.asyncio.sleep", side_effect=fast_sleep):
        result = c.wait_for_completion("task-x", timeout_hours=0.01, poll_interval=0.01)

    assert call_count["n"] == 3, "Expected 2 retries before success"
    assert result.task_id == "task-x"


# ----------------------------------------------------------------------
# _handle_response — 401 message is wallet-oriented
# ----------------------------------------------------------------------


def test_401_raises_wallet_oriented_authentication_error():
    """The 401 branch must mention wallet auth, not 'API key'."""
    c = _make_client()
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 401
    resp.headers = {}
    resp.url = "https://api.execution.market/tasks/x"
    resp.raise_for_status = MagicMock()

    with pytest.raises(AuthenticationError) as exc_info:
        c._handle_response(resp)

    msg = str(exc_info.value).lower()
    assert "wallet" in msg, f"401 message should reference wallet auth, got: {exc_info.value}"
    assert "api key" not in msg, f"401 message must not mention 'API key', got: {exc_info.value}"


# ----------------------------------------------------------------------
# batch_create — per-task idempotency keys
# ----------------------------------------------------------------------


def test_batch_create_sends_per_task_idempotency_keys():
    """Each task in the batch gets its own fingerprint, so the server can
    dedupe individual items in a retried batch.
    """
    c = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(path, content=None, headers=None):
        captured["body"] = json.loads(content) if content else None
        return _ok_response({"tasks": [_fake_task_payload("t1"), _fake_task_payload("t2")]})

    c._client.post = fake_post  # type: ignore[method-assign]

    tasks_in = [
        {"title": "A", "bounty_usd": 0.10},
        {"title": "B", "bounty_usd": 0.20},
    ]
    c.batch_create(tasks_in)

    body = captured["body"]
    assert "idempotency_keys" in body, "Batch must include per-task idempotency keys"
    keys = body["idempotency_keys"]
    assert len(keys) == 2
    assert keys[0] == task_fingerprint(tasks_in[0])
    assert keys[1] == task_fingerprint(tasks_in[1])
    assert keys[0] != keys[1], "Different task bodies → different keys"
