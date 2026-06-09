"""E2E test: Solana MPP session flow through pay.sh (Phase 2.9).

Validates the full Solana session lifecycle without requiring pay.sh
to actually be running. The PayShellClient is mocked at the integration
boundary; everything from the dispatcher inward runs real code.

Scenarios covered:
  1. Authorize routing — network="solana" goes to _authorize_solana_session
     even when dispatcher mode is fase2 (the EVM default)
  2. Channel lookup — _lookup_channel_id walks payment_events metadata
  3. Release — _release_solana_session calls pay.sh close + records the
     settlement event
  4. Refund tolerance — _refund_solana_session no-ops cleanly when no
     channel has been bound yet (cancel-before-open is free)
  5. SSE relay tee — _persist_event normalizes pay.sh event names to the
     migration 108 CHECK-allowed set and writes through to mpp_session_events

The test runs unit-style with mocked Supabase + mocked PayShellClient so
CI doesn't need surfpool or a Solana RPC. The MULTI-SCENARIO harness
(Phase 2.5, separate task) is what runs against a real surfpool fork.

Mocking conventions (must match the green dispatcher suites — see
tests/test_payment_dispatcher.py and tests/test_phase4_payment_fund_loss.py):
  - ALL Supabase access goes through the top-level ``supabase_client``
    module's ``get_client()`` — log_payment_event, _lookup_channel_id and
    taximetro._persist_event all resolve it at call time, so a single
    ``patch.object(supabase_client, "get_client", ...)`` covers reads+writes.
  - ``get_pay_shell_client`` is a module-level name inside
    integrations.x402.payment_dispatcher — patch it there.
  - Heavy modules are imported at module (collection) time: the autouse
    ``_isolate_sys_modules`` fixture in tests/conftest.py strips modules
    imported *inside* a test after it finishes, and re-importing
    PyO3-backed native deps (cryptography et al.) in a later test aborts
    with "PyO3 modules may only be initialized once per interpreter".
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module-level imports — see "Mocking conventions" above for why these
# MUST happen at collection time rather than inside test bodies.
import supabase_client
import integrations.x402.payment_dispatcher as pd
import api.routers.taximetro as taximetro
import api.routes  # noqa: F401  (preloads the router chain for the reload test)

pytestmark = pytest.mark.payments


WORKER_ADDR = "WRKBASE5832xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


class _FakeSession:
    """Minimal pay.sh session record — only `.payee` is consulted (L-25)."""

    def __init__(self, payee: str):
        self.payee = payee


def _make_dispatcher(mode: str = "fase2") -> "pd.PaymentDispatcher":
    with (
        patch.object(pd, "SDK_AVAILABLE", True),
        patch.object(pd, "FASE2_SDK_AVAILABLE", True),
    ):
        return pd.PaymentDispatcher(mode=mode)


# ---------------------------------------------------------------------------
# Fixtures — minimal mocks; the goal is to assert dispatcher branching
# and SSE-tee shape, not exercise the whole Supabase client.
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_supabase():
    """Returns a Supabase mock that records inserts + serves canned reads.

    Each table can be primed by appending dicts to ``mock._rows[table]``
    before the call under test. Inserts land in ``mock._inserts[table]``
    so assertions can verify shape without re-implementing the chained
    query builder.
    """
    mock = MagicMock()
    mock._rows: Dict[str, List[Dict[str, Any]]] = {}
    mock._inserts: Dict[str, List[Dict[str, Any]]] = {}

    def _table(name: str) -> MagicMock:
        table = MagicMock()

        # SELECT chain: .select(...).eq(...).order(...).limit(...).execute()
        def _execute():
            resp = MagicMock()
            resp.data = mock._rows.get(name, [])
            return resp

        chain = MagicMock()
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.execute.side_effect = _execute
        table.select.return_value = chain

        # INSERT: .insert(row).execute()
        def _insert(row):
            mock._inserts.setdefault(name, []).append(row)
            insert_chain = MagicMock()
            resp = MagicMock()
            # Real PostgREST echoes the row back including the generated id
            # (log_payment_event reads rows[0]["id"]).
            resp.data = [{**row, "id": f"evt-{len(mock._inserts[name])}"}]
            insert_chain.execute.return_value = resp
            return insert_chain

        table.insert.side_effect = _insert
        return table

    mock.table.side_effect = _table
    return mock


@pytest.fixture
def fake_payshell_client():
    """Mocked PayShellClient: get_session (L-25 payee check) + close_session.

    get_session defaults to a session whose payee matches WORKER_ADDR so
    the recipient-validation gate passes; override per-test to exercise
    the mismatch branch.
    """
    client = MagicMock()
    client.get_session = AsyncMock(return_value=_FakeSession(payee=WORKER_ADDR))
    client.close_session = AsyncMock()
    client.health = AsyncMock(return_value={"status": "ok"})
    return client


# ---------------------------------------------------------------------------
# 1. Authorize routing — Solana network forces _authorize_solana_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authorize_routes_solana_to_session_path(fake_supabase):
    """When network=solana, dispatcher MUST take _authorize_solana_session
    regardless of its overall mode. Otherwise it would try to find an
    EVM operator address that does not exist on Solana and 500.
    """
    agent_addr = "ABCDE12345" + "x" * 34  # ~44-char base58

    dispatcher = _make_dispatcher("fase2")
    with patch.object(supabase_client, "get_client", return_value=fake_supabase):
        result = await dispatcher.authorize_payment(
            task_id="task-solana-1",
            receiver=agent_addr,
            amount_usdc=Decimal("0.10"),
            agent_address=agent_addr,
            network="solana",
            token="USDC",
        )

    assert result["success"] is True
    # Routed to the Solana session backend despite mode=fase2
    assert result.get("mode") == "solana_session"
    # channel_pending = no on-chain lock yet; channel opens on worker request
    assert result.get("escrow_status") == "channel_pending"

    # Audit event landed in payment_events with the new event_type
    events = fake_supabase._inserts.get("payment_events", [])
    assert any(e.get("event_type") == "solana_session_authorize" for e in events), (
        f"expected solana_session_authorize event, got {[e.get('event_type') for e in events]}"
    )
    # The audit row (not the return dict) carries the network tag
    assert any(e.get("network") == "solana" for e in events)


# ---------------------------------------------------------------------------
# 2. Release — looks up channel + calls pay.sh close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_release_closes_channel_and_records_settlement(
    fake_supabase, fake_payshell_client
):
    """_release_solana_session must:
    1) find the channel_id from payment_events.metadata
    2) verify the channel payee matches the assigned worker (L-25)
    3) call client.close_session()
    4) emit solana_session_release with the settlement tx hash
    """
    # Prime: a prior authorize landed a channel binding in payment_events
    fake_supabase._rows["payment_events"] = [
        {
            "event_type": "payshell_session_open",
            "metadata": {"channel_id": "CHAN_BASE58_X1"},
        }
    ]

    # close_session returns a settled CloseResult
    close_result = MagicMock()
    close_result.settlement_tx_hash = "SOL_TX_BASE58_ABC"
    close_result.refund_usdc = Decimal("0.012")
    close_result.final_cumulative_usdc = Decimal("0.088")
    fake_payshell_client.close_session.return_value = close_result

    dispatcher = _make_dispatcher("fase2")
    with (
        patch.object(supabase_client, "get_client", return_value=fake_supabase),
        patch.object(pd, "get_pay_shell_client", return_value=fake_payshell_client),
    ):
        result = await dispatcher.release_payment(
            task_id="task-solana-1",
            worker_address=WORKER_ADDR,
            bounty_amount=Decimal("0.10"),
            network="solana",
        )

    assert result.get("success") is True
    assert result.get("tx_hash") == "SOL_TX_BASE58_ABC"
    assert result.get("channel_id") == "CHAN_BASE58_X1"
    fake_payshell_client.close_session.assert_awaited_once_with("CHAN_BASE58_X1")

    # Audit row written with the new event type
    events = fake_supabase._inserts.get("payment_events", [])
    assert any(e.get("event_type") == "solana_session_release" for e in events), (
        f"expected solana_session_release, got {[e.get('event_type') for e in events]}"
    )


# ---------------------------------------------------------------------------
# 3. Refund tolerance — cancel-before-open path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refund_with_no_channel_is_noop_success(fake_supabase):
    """If a task is cancelled BEFORE the worker triggers session_open,
    there is no channel to close. The dispatcher must return success
    (the refund is logically free because no funds ever moved).
    """
    # No payment_events rows — channel was never bound
    fake_supabase._rows["payment_events"] = []

    dispatcher = _make_dispatcher("fase2")
    with patch.object(supabase_client, "get_client", return_value=fake_supabase):
        result = await dispatcher.refund_payment(
            task_id="task-solana-empty",
            network="solana",
            reason="cancelled before assignment",
        )

    assert result.get("success") is True
    assert result.get("status") == "no_channel"
    # The dispatcher records the intent so audit isn't blank
    events = fake_supabase._inserts.get("payment_events", [])
    assert any(e.get("event_type") == "solana_session_refund" for e in events), (
        f"expected solana_session_refund noop entry, got {events}"
    )


# ---------------------------------------------------------------------------
# 4. SSE relay tee — event normalization + DB persistence shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_event_normalizes_unknown_types_to_error(fake_supabase):
    """The migration 108 CHECK constraint only allows 5 event types.
    Anything else (e.g. a future pay.sh event we don't know about yet)
    must be coerced to "error" so the INSERT doesn't fail.
    """
    with patch.object(supabase_client, "get_client", return_value=fake_supabase):
        await taximetro._persist_event(
            "CHAN_BASE58_X1",
            "future_unknown_event",
            {"foo": "bar"},
        )

    inserted = fake_supabase._inserts.get("mpp_session_events", [])
    assert len(inserted) == 1
    assert inserted[0]["event_type"] == "error", (
        f"unknown event must be normalized to 'error', got {inserted[0]['event_type']}"
    )
    # Raw payload preserved so we don't lose forward-compat info
    assert inserted[0]["payload"] == {"foo": "bar"}


@pytest.mark.asyncio
async def test_persist_event_extracts_voucher_fields(fake_supabase):
    """Persist must pull cumulative_uusdc / voucher_index / tx_hash out
    of the SSE payload regardless of camelCase vs snake_case spelling.
    """
    with patch.object(supabase_client, "get_client", return_value=fake_supabase):
        await taximetro._persist_event(
            "CHAN_BASE58_X1",
            "voucher_accepted",
            {
                "cumulativeUusdc": 88000,
                "voucherIndex": 4,
                "txHash": None,
                "taskId": "task-solana-1",
            },
        )

    inserted = fake_supabase._inserts.get("mpp_session_events", [])[0]
    assert inserted["event_type"] == "voucher_accepted"
    assert inserted["cumulative_uusdc"] == 88000
    assert inserted["voucher_index"] == 4
    assert inserted["task_id"] == "task-solana-1"


@pytest.mark.asyncio
async def test_persist_event_never_raises():
    """If the DB insert fails, _persist_event must log and swallow.
    The user-facing SSE stream cannot be torn down by an audit-mirror
    write failure — pay.sh is the source of truth, this is just a tap.
    """
    bad_supabase = MagicMock()
    bad_supabase.table.side_effect = RuntimeError("DB down")

    with patch.object(supabase_client, "get_client", return_value=bad_supabase):
        # Must NOT raise
        await taximetro._persist_event(
            "CHAN_X", "voucher_accepted", {"cumulativeUusdc": 1}
        )


# ---------------------------------------------------------------------------
# 5. SSE format — frame encoding matches the spec
# ---------------------------------------------------------------------------


def test_sse_format_emits_canonical_frame():
    """One SSE frame = `event: <type>\\ndata: <json>\\n\\n`.

    Browsers buffer until they see the trailing blank line. Without that
    blank line the dashboard taxímetro would hang forever waiting for
    the first event.
    """
    frame = taximetro._sse_format(
        "voucher_accepted", {"cumulative_uusdc": 1000, "voucher_index": 2}
    )
    text = frame.decode("utf-8")

    assert text.startswith("event: voucher_accepted\n")
    assert "data: " in text
    assert text.endswith("\n\n"), "SSE frame must end with blank line"
    # JSON compact (no spaces) — keeps stream lean
    assert '"cumulative_uusdc":1000' in text


# ---------------------------------------------------------------------------
# 6. Master switch — taximetro router is only registered when flag is on
# ---------------------------------------------------------------------------


def test_taximetro_router_gated_by_env_flag(monkeypatch):
    """When EM_PAYSHELL_ENABLED is unset/false, /api/v1/taximetro/* must
    return 404 (route not registered), not 503 (registered but disabled).

    This matches the MoonPay/VeryAI/ClawKey pattern — feature flags gate
    the include_router() call at app boot, not the request handler.

    NOTE: api/routes.py swaps a fresh _RoutesModuleProxy into sys.modules at
    the end of every execution, so a stale module reference cannot be
    reloaded twice — always reload the CURRENT sys.modules entry.
    """
    import importlib
    import sys

    def _reload_routes():
        return importlib.reload(sys.modules["api.routes"])

    # Force-off
    monkeypatch.setenv("EM_PAYSHELL_ENABLED", "false")
    routes_mod = _reload_routes()
    paths_off = {r.path for r in routes_mod.router.routes if hasattr(r, "path")}
    assert not any(p.startswith("/api/v1/taximetro") for p in paths_off), (
        "taximetro routes should not be registered when EM_PAYSHELL_ENABLED=false"
    )

    # Force-on
    monkeypatch.setenv("EM_PAYSHELL_ENABLED", "true")
    routes_mod = _reload_routes()
    paths_on = {r.path for r in routes_mod.router.routes if hasattr(r, "path")}
    assert any(p.startswith("/api/v1/taximetro") for p in paths_on), (
        f"taximetro routes should be registered when EM_PAYSHELL_ENABLED=true; got {sorted(paths_on)}"
    )

    # Reset to default for the rest of the suite
    monkeypatch.setenv("EM_PAYSHELL_ENABLED", "false")
    _reload_routes()
