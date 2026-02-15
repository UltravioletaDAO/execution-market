"""Tests for GET /tasks/{task_id}/transactions endpoint."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from api import routes

pytestmark = [pytest.mark.core, pytest.mark.payments]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class _MockQuery:
    """Chainable mock for Supabase PostgREST queries."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self._limit = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, *_a, **_kw):
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def not_(self, *_a, **_kw):
        return self

    def execute(self):
        rows = self._rows[: self._limit] if isinstance(self._limit, int) else self._rows
        return SimpleNamespace(data=rows)


class _MockClient:
    """Supabase client mock supporting payment_events and escrows tables."""

    def __init__(self, payment_events=None, escrows=None):
        self._payment_events = payment_events or []
        self._escrows = escrows or []

    def table(self, name: str):
        if name == "payment_events":
            return _MockQuery(rows=self._payment_events)
        if name == "escrows":
            return _MockQuery(rows=self._escrows)
        return _MockQuery(rows=[])


TASK_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

SAMPLE_TASK = {
    "id": TASK_ID,
    "agent_id": "agent_test",
    "status": "completed",
    "bounty_usd": 0.10,
    "payment_network": "base",
    "created_at": "2026-02-14T17:50:00+00:00",
    "updated_at": "2026-02-14T17:55:00+00:00",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transactions_returns_empty_for_new_task(monkeypatch):
    """New task with no payment events returns empty list."""
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(return_value={**SAMPLE_TASK, "status": "published"}),
    )
    monkeypatch.setattr(routes.db, "get_client", lambda: _MockClient())

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    assert result.task_id == TASK_ID
    assert result.total_count == 0
    assert result.transactions == []
    assert result.summary["total_locked"] == 0.0


@pytest.mark.asyncio
async def test_transactions_returns_404_for_missing_task(monkeypatch):
    """Missing task returns 404."""
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            side_effect=Exception(
                "PGRST116: JSON object requested, multiple (or no) rows returned"
            )
        ),
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await routes.get_task_transactions(task_id=TASK_ID, api_key=None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_transactions_happy_path_full_lifecycle(monkeypatch):
    """Full lifecycle: escrow_authorize + escrow_release + fee_collect."""
    events = [
        {
            "id": "evt-1",
            "event_type": "escrow_authorize",
            "tx_hash": "0x" + "a" * 64,
            "amount_usdc": 0.10,
            "from_address": "0xAgent",
            "to_address": "0xEscrow",
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:50:00+00:00",
            "metadata": None,
        },
        {
            "id": "evt-2",
            "event_type": "escrow_release",
            "tx_hash": "0x" + "b" * 64,
            "amount_usdc": 0.087,
            "from_address": "0xEscrow",
            "to_address": "0xWorker",
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:51:00+00:00",
            "metadata": None,
        },
        {
            "id": "evt-3",
            "event_type": "fee_collect",
            "tx_hash": "0x" + "c" * 64,
            "amount_usdc": 0.013,
            "from_address": "0xAgent",
            "to_address": "0xPlatform",
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:50:30+00:00",
            "metadata": None,
        },
    ]
    monkeypatch.setattr(routes.db, "get_task", AsyncMock(return_value=SAMPLE_TASK))
    monkeypatch.setattr(
        routes.db, "get_client", lambda: _MockClient(payment_events=events)
    )

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    assert result.total_count == 3
    assert result.summary["total_locked"] == 0.10
    assert result.summary["total_released"] == 0.087
    assert result.summary["fee_collected"] == 0.013
    assert result.summary["total_refunded"] == 0.0

    # Verify chronological order
    timestamps = [t.timestamp for t in result.transactions]
    assert timestamps == sorted(timestamps)

    # Verify explorer URLs
    for tx in result.transactions:
        if tx.tx_hash:
            assert tx.explorer_url is not None
            assert "basescan.org/tx/" in tx.explorer_url

    # Verify labels
    assert result.transactions[0].label == "Deposito Escrow"
    assert result.transactions[1].label == "Cobro de Fee"  # sorted by time
    assert result.transactions[2].label == "Liberacion Escrow"


@pytest.mark.asyncio
async def test_transactions_refund_flow(monkeypatch):
    """Refund flow: escrow_authorize + escrow_refund."""
    events = [
        {
            "id": "evt-1",
            "event_type": "escrow_authorize",
            "tx_hash": "0x" + "a" * 64,
            "amount_usdc": 0.10,
            "from_address": "0xAgent",
            "to_address": "0xEscrow",
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:50:00+00:00",
            "metadata": None,
        },
        {
            "id": "evt-2",
            "event_type": "escrow_refund",
            "tx_hash": "0x" + "d" * 64,
            "amount_usdc": 0.10,
            "from_address": "0xEscrow",
            "to_address": "0xAgent",
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:55:00+00:00",
            "metadata": None,
        },
    ]
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(return_value={**SAMPLE_TASK, "status": "cancelled"}),
    )
    monkeypatch.setattr(
        routes.db, "get_client", lambda: _MockClient(payment_events=events)
    )

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    assert result.total_count == 2
    assert result.summary["total_locked"] == 0.10
    assert result.summary["total_refunded"] == 0.10
    assert result.summary["total_released"] == 0.0


@pytest.mark.asyncio
async def test_transactions_injects_reputation_from_escrow_metadata(monkeypatch):
    """Reputation TXs from escrow metadata are injected if not in payment_events."""
    events = [
        {
            "id": "evt-1",
            "event_type": "escrow_authorize",
            "tx_hash": "0x" + "a" * 64,
            "amount_usdc": 0.10,
            "from_address": "0xAgent",
            "to_address": "0xEscrow",
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:50:00+00:00",
            "metadata": None,
        },
    ]
    escrows = [
        {
            "task_id": TASK_ID,
            "metadata": {
                "reputation_agent_tx": "0x" + "e" * 64,
                "reputation_worker_tx": "0x" + "f" * 64,
            },
            "created_at": "2026-02-14T17:50:00+00:00",
        }
    ]
    monkeypatch.setattr(routes.db, "get_task", AsyncMock(return_value=SAMPLE_TASK))
    monkeypatch.setattr(
        routes.db,
        "get_client",
        lambda: _MockClient(payment_events=events, escrows=escrows),
    )

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    assert result.total_count == 3  # 1 payment + 2 reputation
    event_types = [t.event_type for t in result.transactions]
    assert "reputation_agent_rates_worker" in event_types
    assert "reputation_worker_rates_agent" in event_types

    # Check reputation events have explorer URLs
    rep_events = [t for t in result.transactions if "reputation" in t.event_type]
    for re in rep_events:
        assert re.explorer_url is not None
        assert re.label in ("Agente Califica Worker", "Worker Califica Agente")


@pytest.mark.asyncio
async def test_transactions_no_duplicates_from_escrow_metadata(monkeypatch):
    """If reputation TX is already in payment_events, don't duplicate from escrow metadata."""
    rep_tx_hash = "0x" + "e" * 64
    events = [
        {
            "id": "evt-1",
            "event_type": "reputation_agent_rates_worker",
            "tx_hash": rep_tx_hash,
            "amount_usdc": None,
            "from_address": None,
            "to_address": None,
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:52:00+00:00",
            "metadata": None,
        },
    ]
    escrows = [
        {
            "task_id": TASK_ID,
            "metadata": {"reputation_agent_tx": rep_tx_hash},
            "created_at": "2026-02-14T17:50:00+00:00",
        }
    ]
    monkeypatch.setattr(routes.db, "get_task", AsyncMock(return_value=SAMPLE_TASK))
    monkeypatch.setattr(
        routes.db,
        "get_client",
        lambda: _MockClient(payment_events=events, escrows=escrows),
    )

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    # Should NOT duplicate — only 1 reputation event
    rep_count = sum(1 for t in result.transactions if "reputation" in t.event_type)
    assert rep_count == 1


@pytest.mark.asyncio
async def test_transactions_failed_events_not_counted_in_summary(monkeypatch):
    """Failed events appear in list but don't count toward summary totals."""
    events = [
        {
            "id": "evt-1",
            "event_type": "escrow_authorize",
            "tx_hash": "0x" + "a" * 64,
            "amount_usdc": 0.10,
            "from_address": "0xAgent",
            "to_address": "0xEscrow",
            "network": "base",
            "token": "USDC",
            "status": "failed",
            "created_at": "2026-02-14T17:50:00+00:00",
            "metadata": {"error": "insufficient balance"},
        },
    ]
    monkeypatch.setattr(routes.db, "get_task", AsyncMock(return_value=SAMPLE_TASK))
    monkeypatch.setattr(
        routes.db, "get_client", lambda: _MockClient(payment_events=events)
    )

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    assert result.total_count == 1
    assert result.transactions[0].status == "failed"
    assert result.summary["total_locked"] == 0.0  # Failed, not counted


@pytest.mark.asyncio
async def test_transactions_explorer_url_per_network(monkeypatch):
    """Explorer URLs use the correct domain per network."""
    events = [
        {
            "id": "evt-1",
            "event_type": "settle",
            "tx_hash": "0x" + "a" * 64,
            "amount_usdc": 1.0,
            "network": "polygon",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:50:00+00:00",
        },
        {
            "id": "evt-2",
            "event_type": "settle",
            "tx_hash": "0x" + "b" * 64,
            "amount_usdc": 1.0,
            "network": "arbitrum",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:51:00+00:00",
        },
    ]
    monkeypatch.setattr(routes.db, "get_task", AsyncMock(return_value=SAMPLE_TASK))
    monkeypatch.setattr(
        routes.db, "get_client", lambda: _MockClient(payment_events=events)
    )

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    assert "polygonscan.com/tx/" in result.transactions[0].explorer_url
    assert "arbiscan.io/tx/" in result.transactions[1].explorer_url


@pytest.mark.asyncio
async def test_transactions_handles_payment_events_query_failure(monkeypatch):
    """Gracefully handles payment_events query failure."""

    class _FailingClient:
        def table(self, name):
            if name == "payment_events":
                return _FailingQuery()
            return _MockQuery()

    class _FailingQuery:
        def select(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def order(self, *a, **kw):
            return self

        def limit(self, n):
            return self

        def execute(self):
            raise Exception("connection error")

    monkeypatch.setattr(routes.db, "get_task", AsyncMock(return_value=SAMPLE_TASK))
    monkeypatch.setattr(routes.db, "get_client", lambda: _FailingClient())

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    # Should return empty, not crash
    assert result.total_count == 0
    assert result.transactions == []


@pytest.mark.asyncio
async def test_transactions_tx_without_0x_prefix_gets_normalized(monkeypatch):
    """TX hashes without 0x prefix get normalized in explorer URL."""
    events = [
        {
            "id": "evt-1",
            "event_type": "escrow_authorize",
            "tx_hash": "a" * 64,  # No 0x prefix
            "amount_usdc": 0.10,
            "network": "base",
            "token": "USDC",
            "status": "success",
            "created_at": "2026-02-14T17:50:00+00:00",
        },
    ]
    monkeypatch.setattr(routes.db, "get_task", AsyncMock(return_value=SAMPLE_TASK))
    monkeypatch.setattr(
        routes.db, "get_client", lambda: _MockClient(payment_events=events)
    )

    result = await routes.get_task_transactions(task_id=TASK_ID, api_key=None)

    assert result.transactions[0].explorer_url.startswith("https://basescan.org/tx/0x")


@pytest.mark.asyncio
async def test_build_explorer_url_no_hash():
    """_build_explorer_url returns None when no tx_hash."""
    assert routes._build_explorer_url(None, "base") is None
    assert routes._build_explorer_url("", "base") is None


@pytest.mark.asyncio
async def test_build_explorer_url_unknown_network():
    """Unknown network falls back to basescan."""
    url = routes._build_explorer_url("0x" + "a" * 64, "unknown_chain")
    assert "basescan.org/tx/" in url
