"""FIX-P1-03 — GET /payments/events: ownership + injection-proof + no metadata.

Calls the handler function directly (the WSL test env has a broken Starlette
TestClient), with mocked worker_auth / verify_api_key / supabase client.
"""

import pytest

pytestmark = [pytest.mark.security, pytest.mark.payments]

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from api.auth import WorkerAuth

OWNER_WALLET = "0x" + "ab" * 20  # 42-char EVM
OTHER_WALLET = "0x" + "cd" * 20


def _request(path="/api/v1/payments/events"):
    req = MagicMock()
    req.url.path = path
    return req


def _fake_client_with_rows(rows):
    """Return a fake supabase client whose query chain yields *rows*."""
    table = MagicMock()
    table.select.return_value = table
    table.or_.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.eq.return_value = table
    table.gte.return_value = table
    table.execute.return_value = MagicMock(data=rows)
    client = MagicMock()
    client.table.return_value = table
    return client


async def _call(
    monkeypatch,
    *,
    worker_auth=None,
    authorization=None,
    x_api_key=None,
    address=OWNER_WALLET,
    rows=None,
    enforce=True,
):
    """Call the handler with the enforcement flag patched in-place (NO module
    reload — that corrupts module identity for the rest of the suite)."""
    import api.routers.workers as w

    fake_client = _fake_client_with_rows(rows or [])
    with (
        patch.object(w, "_ENFORCE_PAYMENT_EVENTS_AUTH", enforce),
        patch.object(w.db, "get_client", return_value=fake_client),
    ):
        return await w.get_payment_events(
            raw_request=_request(),
            address=address,
            since=None,
            limit=20,
            event_type=None,
            worker_auth=worker_auth,
            authorization=authorization,
            x_api_key=x_api_key,
        )


@pytest.mark.asyncio
async def test_anonymous_request_rejected(monkeypatch):
    """Reproduces the bug: anonymous request now 401 (was 200 + data)."""
    with pytest.raises(HTTPException) as exc:
        await _call(monkeypatch, address=OTHER_WALLET)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_worker_cannot_query_other_wallet(monkeypatch):
    wa = WorkerAuth(executor_id="e1", wallet_address=OWNER_WALLET, auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _call(monkeypatch, worker_auth=wa, address=OTHER_WALLET)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_worker_can_query_own_wallet_and_metadata_hidden(monkeypatch):
    wa = WorkerAuth(executor_id="e1", wallet_address=OWNER_WALLET, auth_method="jwt")
    rows = [
        {
            "id": "evt-1",
            "task_id": "t-1",
            "event_type": "disburse_worker",
            "to_address": OWNER_WALLET,
            "amount_usdc": "1.5",
            "network": "base",
            "metadata": {"secret": "internal"},
        }
    ]
    result = await _call(monkeypatch, worker_auth=wa, address=OWNER_WALLET, rows=rows)
    assert "events" in result and len(result["events"]) == 1
    # FIX-P1-03: raw metadata must NOT be leaked.
    assert "metadata" not in result["events"][0]
    assert "total_earned_usdc" in result


@pytest.mark.asyncio
async def test_internal_api_key_allowed_cross_wallet(monkeypatch):
    import api.routers.workers as w

    fake_client = _fake_client_with_rows([])
    with (
        patch.object(w, "_ENFORCE_PAYMENT_EVENTS_AUTH", True),
        patch.object(w.db, "get_client", return_value=fake_client),
        patch.object(w, "verify_api_key", new=AsyncMock(return_value=MagicMock())),
    ):
        result = await w.get_payment_events(
            raw_request=_request(),
            address=OTHER_WALLET,
            since=None,
            limit=20,
            event_type=None,
            worker_auth=None,
            authorization=None,
            x_api_key="valid-key",
        )
    assert "events" in result


@pytest.mark.asyncio
async def test_invalid_api_key_falls_through_to_401(monkeypatch):
    import api.routers.workers as w

    with (
        patch.object(w, "_ENFORCE_PAYMENT_EVENTS_AUTH", True),
        patch.object(
            w,
            "verify_api_key",
            new=AsyncMock(side_effect=HTTPException(status_code=401)),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await w.get_payment_events(
                raw_request=_request(),
                address=OTHER_WALLET,
                since=None,
                limit=20,
                event_type=None,
                worker_auth=None,
                authorization=None,
                x_api_key="bad-key",
            )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_malformed_address_rejected(monkeypatch):
    """PostgREST injection payload → 400, before any DB access."""
    wa = WorkerAuth(executor_id="e1", wallet_address=OWNER_WALLET, auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _call(
            monkeypatch,
            worker_auth=wa,
            address="0x*,from_address.ilike.*aaaaaaaaaaaaaaa",
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_solana_address_accepted_format(monkeypatch):
    """A valid base58 Solana address passes format validation (not 400)."""
    wa = WorkerAuth(
        executor_id="e1",
        wallet_address="9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
        auth_method="jwt",
    )
    # Owns the requested wallet → not 400, not 403.
    result = await _call(
        monkeypatch,
        worker_auth=wa,
        address="9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
    )
    assert "events" in result


@pytest.mark.asyncio
async def test_enforcement_flag_off_is_legacy(monkeypatch):
    """Kill-switch off → byte-identical to pre-WS-AUTH main: anonymous allowed,
    NO format-validation 400, and raw metadata included in the response.

    (When EM_REQUIRE_WORKER_AUTH / EM_ENFORCE_PAYMENT_EVENTS_AUTH are off the
    endpoint must be a TOTAL no-op; the injection-hardening and metadata-hiding
    only activate when enforcement is enabled — see test_malformed_address_rejected
    and test_worker_can_query_own_wallet_and_metadata_hidden above.)"""
    rows = [
        {
            "id": "evt-legacy",
            "task_id": "t-1",
            "event_type": "disburse_worker",
            "to_address": OWNER_WALLET,
            "amount_usdc": "1.5",
            "network": "base",
            "metadata": {"secret": "internal"},
        }
    ]
    # Anonymous allowed when enforcement off.
    result = await _call(monkeypatch, address=OWNER_WALLET, enforce=False, rows=rows)
    assert "events" in result
    # Legacy includes raw metadata (hidden only when enforcement is on).
    assert result["events"][0].get("metadata") == {"secret": "internal"}
    # Malformed address does NOT 400 when enforcement is off (no format gate).
    legacy = await _call(
        monkeypatch, address="not-a-valid-wallet-addr-xx", enforce=False
    )
    assert "events" in legacy
