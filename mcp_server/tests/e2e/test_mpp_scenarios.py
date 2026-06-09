"""E2E: parametrized MPP scenario tests (Phase 2.5.4).

Validates the four cells of the worker-type matrix against the same
backend:

    A. robot              — real hardware (skipped unless EM_ROBOT_HARDWARE_AVAILABLE=1)
    B. agent_to_human     — agent publishes, human worker signs via browser console
    C. human_to_human     — human publishes, human signs
    D. robot_sim          — robot-simulator CLI signs (no hardware)

The point: prove the lifecycle binding (`task ↔ MPP channel`) is the
same in all four cells. Only the **signer identity** changes; the wire
protocol, the dispatcher path, and the settlement semantics are
identical.

Tests are unit-style with PayShellClient mocked — CI doesn't have a
Solana RPC. The harness validates that the dispatcher + state machine
produce the same audit trail regardless of `mode` label.

Mocking conventions (must match the green dispatcher suites — see
tests/test_payment_dispatcher.py and tests/test_phase4_payment_fund_loss.py):
  - ALL dispatcher Supabase access resolves through the top-level
    ``supabase_client`` module's ``get_client()`` at call time, so one
    ``patch.object(supabase_client, "get_client", ...)`` covers both
    log_payment_event writes and _lookup_channel_id reads.
  - The binding service keeps its own ``_get_db`` seam — patch that.
  - Heavy modules are imported at module (collection) time: the autouse
    ``_isolate_sys_modules`` fixture in tests/conftest.py strips modules
    imported *inside* a test after it finishes, and re-importing
    PyO3-backed native deps in a later test aborts with "PyO3 modules
    may only be initialized once per interpreter".
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module-level imports — see "Mocking conventions" above for why these
# MUST happen at collection time rather than inside test bodies.
import supabase_client
import integrations.x402.payment_dispatcher as pd
from services import task_channel_binding as binding

pytestmark = pytest.mark.payments


SCENARIO_IDS = ["B_agent_to_human", "C_human_to_human", "D_robot_sim"]
if os.environ.get("EM_ROBOT_HARDWARE_AVAILABLE", "").lower() in ("1", "true"):
    SCENARIO_IDS.insert(0, "A_robot")


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
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def supabase_mock():
    mock = MagicMock()
    mock._rows: Dict[str, List[Dict[str, Any]]] = {}
    mock._inserts: Dict[str, List[Dict[str, Any]]] = {}
    mock._updates: Dict[str, List[Dict[str, Any]]] = {}
    mock._rpc_calls: List[Dict[str, Any]] = []

    def _table(name: str) -> MagicMock:
        t = MagicMock()

        def _execute_select():
            r = MagicMock()
            r.data = mock._rows.get(name, [])
            return r

        chain = MagicMock()
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.execute.side_effect = _execute_select
        t.select.return_value = chain

        def _insert(row):
            mock._inserts.setdefault(name, []).append(row)
            r = MagicMock()
            # Real PostgREST echoes the row back including the generated id
            # (log_payment_event reads rows[0]["id"]).
            r.execute.return_value = MagicMock(
                data=[{**row, "id": f"evt-{len(mock._inserts[name])}"}]
            )
            return r

        t.insert.side_effect = _insert

        def _update(payload):
            up = MagicMock()
            up.eq = MagicMock(return_value=up)
            up.execute = MagicMock(
                side_effect=lambda: mock._updates.setdefault(name, []).append(payload)
            )
            return up

        t.update.side_effect = _update
        return t

    mock.table.side_effect = _table

    def _rpc(fn_name, params):
        mock._rpc_calls.append({"fn": fn_name, "params": params})
        r = MagicMock()
        r.execute = MagicMock(return_value=MagicMock(data="bind-uuid-test"))
        return r

    mock.rpc.side_effect = _rpc
    return mock


@pytest.fixture
def payshell_mock():
    client = MagicMock()
    close_result = MagicMock()
    close_result.settlement_tx_hash = "TX_SOL_BASE58_SCENARIO"
    close_result.refund_usdc = Decimal("0.012")
    close_result.final_cumulative_usdc = Decimal("0.088")
    client.close_session = AsyncMock(return_value=close_result)
    # get_session feeds the L-25 payee-vs-worker check; tests override the
    # payee to match their per-scenario worker address.
    client.get_session = AsyncMock(return_value=_FakeSession(payee=""))
    client.health = AsyncMock(return_value={"status": "ok"})
    return client


# ---------------------------------------------------------------------------
# Parametrized lifecycle test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIO_IDS)
async def test_session_lifecycle_same_for_all_worker_types(
    scenario, supabase_mock, payshell_mock
):
    """Same audit trail regardless of who signs.

    Steps:
      1. dispatcher.authorize_payment(network="solana") → logs
         solana_session_authorize
      2. binding service is invoked at assignment time
      3. dispatcher.release_payment(network="solana") looks up channel,
         calls pay.sh close, logs solana_session_release
      4. on_settlement_complete transitions the task

    The scenario id is only used to tag the test output — the wire
    protocol must be identical.
    """
    task_id = f"task-{scenario}"
    channel_id = f"CHAN_{scenario.upper()}_BASE58"
    agent_addr = "AGT" + "x" * 41  # ~44 chars base58
    worker_addr = "WRK" + "x" * 41

    # 1) Authorize on the Solana path.
    dispatcher = _make_dispatcher("fase2")
    with patch.object(supabase_client, "get_client", return_value=supabase_mock):
        auth = await dispatcher.authorize_payment(
            task_id=task_id,
            receiver=agent_addr,
            amount_usdc=Decimal("0.10"),
            agent_address=agent_addr,
            network="solana",
            token="USDC",
        )
    assert auth["success"] is True
    # Routed to the Solana session backend despite mode=fase2
    assert auth.get("mode") == "solana_session"
    auth_events = supabase_mock._inserts.get("payment_events", [])
    assert any(
        e.get("event_type") == "solana_session_authorize"
        and e.get("network") == "solana"
        for e in auth_events
    ), f"scenario {scenario}: missing solana_session_authorize audit row"

    # 2) Binding service stamps the channel — same call shape for every scenario.
    with patch("services.task_channel_binding._get_db", return_value=supabase_mock):
        binding.on_task_assigned(
            task_id=task_id,
            channel_id=channel_id,
            payer=agent_addr,
            payee=worker_addr,
            cap_usdc=Decimal("0.10"),
            metadata={"scenario": scenario},
        )
    rpc_calls = [
        c for c in supabase_mock._rpc_calls if c["fn"] == "upsert_task_channel_binding"
    ]
    assert len(rpc_calls) == 1, f"binding RPC must fire exactly once, got {rpc_calls}"
    assert rpc_calls[0]["params"]["p_channel_id"] == channel_id

    # 3) Release — dispatcher looks up the channel from payment_events,
    #    verifies the channel payee matches the assigned worker (L-25),
    #    then closes via pay.sh.
    supabase_mock._rows["payment_events"] = [
        {"event_type": "payshell_session_open", "metadata": {"channel_id": channel_id}}
    ]
    payshell_mock.get_session.return_value = _FakeSession(payee=worker_addr)
    with (
        patch.object(supabase_client, "get_client", return_value=supabase_mock),
        patch.object(pd, "get_pay_shell_client", return_value=payshell_mock),
    ):
        rel = await dispatcher.release_payment(
            task_id=task_id,
            worker_address=worker_addr,
            bounty_amount=Decimal("0.10"),
            network="solana",
        )
    assert rel["success"] is True
    assert rel["tx_hash"] == "TX_SOL_BASE58_SCENARIO"
    payshell_mock.close_session.assert_awaited_once_with(channel_id)

    # 4) State machine transition fires off settlement_complete.
    supabase_mock._rows["task_channel_bindings"] = [
        {
            "id": "bind-uuid-test",
            "task_id": task_id,
            "channel_id": channel_id,
            "settlement_tx_hash": None,
        }
    ]
    with patch("services.task_channel_binding._get_db", return_value=supabase_mock):
        transitioned = binding.on_settlement_complete(
            channel_id=channel_id,
            settlement_tx_hash="TX_SOL_BASE58_SCENARIO",
            refund_uusdc=12_000,
            final_cumulative_uusdc=88_000,
        )
    assert transitioned is True, (
        f"scenario {scenario}: settlement must transition state once"
    )

    # The tasks UPDATE call must include status=completed.
    task_updates = supabase_mock._updates.get("tasks", [])
    assert any(u.get("status") == "completed" for u in task_updates), (
        f"scenario {scenario}: task should transition to completed; updates={task_updates}"
    )


# ---------------------------------------------------------------------------
# Double-settle defense — explicit case from the master plan
# ---------------------------------------------------------------------------


def test_double_settle_does_not_overwrite_existing_tx(supabase_mock):
    """If two settlement_complete events arrive with DIFFERENT tx hashes,
    the second one MUST be refused — pay.sh's settleAndFinalize is atomic
    so a divergent hash means SSE relay confusion, not on-chain reality.
    """
    supabase_mock._rows["task_channel_bindings"] = [
        {
            "id": "bind-1",
            "task_id": "task-double",
            "channel_id": "CHAN_DOUBLE",
            "settlement_tx_hash": "TX_FIRST_SOL",
        }
    ]
    with patch("services.task_channel_binding._get_db", return_value=supabase_mock):
        result = binding.on_settlement_complete(
            channel_id="CHAN_DOUBLE",
            settlement_tx_hash="TX_SECOND_SOL_DIFFERENT",
        )
    assert result is False
    # No update to settlement_tx_hash should have been written.
    tcb_updates = supabase_mock._updates.get("task_channel_bindings", [])
    for u in tcb_updates:
        assert u.get("settlement_tx_hash") != "TX_SECOND_SOL_DIFFERENT", (
            f"second tx must NOT overwrite first; got update {u}"
        )


def test_same_tx_seen_twice_is_idempotent_noop(supabase_mock):
    """Same tx_hash twice → no state regression, no error, returns False
    (no transition happened on this call) but doesn't blow up."""
    supabase_mock._rows["task_channel_bindings"] = [
        {
            "id": "bind-1",
            "task_id": "task-same",
            "channel_id": "CHAN_SAME",
            "settlement_tx_hash": "TX_ONLY_SOL",
        }
    ]
    with patch("services.task_channel_binding._get_db", return_value=supabase_mock):
        result = binding.on_settlement_complete(
            channel_id="CHAN_SAME",
            settlement_tx_hash="TX_ONLY_SOL",
        )
    assert result is False  # nothing changed
    # task_channel_bindings update should NOT have been issued (no new info)
    # — only acceptable update is empty or status unchanged
    for u in supabase_mock._updates.get("task_channel_bindings", []):
        if "settlement_tx_hash" in u:
            assert u["settlement_tx_hash"] == "TX_ONLY_SOL"


def test_settlement_for_unbound_channel_is_logged_not_raised(supabase_mock):
    """If pay.sh emits settlement_complete for a channel we never bound,
    log it and move on. Don't raise — the SSE relay can't survive
    exceptions from a tee handler."""
    supabase_mock._rows["task_channel_bindings"] = []
    with patch("services.task_channel_binding._get_db", return_value=supabase_mock):
        result = binding.on_settlement_complete(
            channel_id="CHAN_ORPHAN",
            settlement_tx_hash="TX_ORPHAN_SOL",
        )
    assert result is False


# ---------------------------------------------------------------------------
# Missing-settle case — task stays VERIFYING, audit row visible
# ---------------------------------------------------------------------------


def test_session_close_without_settlement_leaves_task_in_draining(supabase_mock):
    """When pay.sh emits session_close but settlement never arrives, the
    binding goes to 'draining' but the task is NOT transitioned. Operator
    intervention (runbook) is what fixes it."""
    supabase_mock._rows["task_channel_bindings"] = [
        {
            "id": "bind-1",
            "task_id": "task-stuck",
            "channel_id": "CHAN_STUCK",
            "status": "open",
            "settlement_tx_hash": None,
        }
    ]
    with patch("services.task_channel_binding._get_db", return_value=supabase_mock):
        binding.on_session_close(channel_id="CHAN_STUCK")

    tcb_updates = supabase_mock._updates.get("task_channel_bindings", [])
    assert any(u.get("status") == "draining" for u in tcb_updates), (
        f"close must set binding.status=draining, got {tcb_updates}"
    )
    # tasks table NOT updated — only on_settlement_complete does that.
    task_updates = supabase_mock._updates.get("tasks", [])
    assert not any(u.get("status") == "completed" for u in task_updates)
