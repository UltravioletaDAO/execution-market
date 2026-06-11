"""
Universal Hiring Matrix — party matching gate + escrow lifecycle.

Validates the single source of truth (`api.party`) that every apply/accept path
shares, so the 3x3 matrix {human,agent,robot} x {human,agent,robot} (+ 'any')
behaves identically across REST and MCP. See
MASTER_PLAN_UNIVERSAL_HIRING_MATRIX.md (Phase 2 + 3).

``TestUniversalEscrowMatrix`` extends this with the escrow lifecycle for the
9 publisher x executor cells (MASTER_PLAN_UNIVERSAL_ESCROW_CONSISTENCY Task
5.2): the cells ride 2 publisher rails (human JWT via api/h2a.py; agent and
robot ERC-8128 via api/routers/tasks.py — robot publishers authenticate
exactly like agents) and the executor side only contributes the receiver
wallet (party gates are covered by the classes above).
"""

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Module-level imports (collection time) so the sys.modules isolation fixture
# preserves them between tests — lazy in-test imports of mcp/pydantic get
# stripped after the first test and break generic model re-creation.
from mcp.server.fastmcp import FastMCP
import integrations.x402.escrow_lock as escrow_lock
from api.party import can_execute, party_required_label
from models import (
    AcceptAgentTaskInput,
    ApproveH2ASubmissionRequest,
    PartyType,
    PublishH2ATaskRequest,
    RegisterAgentExecutorInput,
    party_type_from_agent_type,
)
from tools.agent_executor_tools import register_agent_executor_tools

PARTIES = [p.value for p in PartyType]  # human, agent, robot


@pytest.mark.core
class TestCanExecute:
    @pytest.mark.parametrize("party", PARTIES)
    def test_any_target_open_to_all(self, party):
        assert can_execute(party, "any") is True

    @pytest.mark.parametrize("party", PARTIES)
    def test_unset_target_open_to_all(self, party):
        assert can_execute(party, None) is True
        assert can_execute(party, "") is True

    @pytest.mark.parametrize("party", PARTIES)
    def test_same_party_allowed(self, party):
        assert can_execute(party, party) is True

    @pytest.mark.parametrize("party", PARTIES)
    @pytest.mark.parametrize("target", PARTIES)
    def test_full_matrix(self, party, target):
        # Exactly the diagonal is allowed for specific targets.
        assert can_execute(party, target) is (party == target)

    def test_unknown_executor_party_rejected_for_specific_target(self):
        assert can_execute(None, "human") is False
        assert can_execute("alien", "agent") is False


@pytest.mark.core
class TestPartyLabel:
    def test_any(self):
        assert party_required_label("any") == "any party"
        assert party_required_label(None) == "any party"

    @pytest.mark.parametrize("target", PARTIES)
    def test_specific(self, target):
        assert party_required_label(target) == f"{target} executors"


@pytest.mark.core
class TestAgentTypeMapping:
    @pytest.mark.parametrize(
        "agent_type,expected",
        [
            ("human", "human"),
            ("ai", "agent"),
            ("agent", "agent"),
            ("organization", "agent"),
            ("robot", "robot"),
            (None, "human"),
            ("unknown", "human"),
        ],
    )
    def test_party_type_from_agent_type(self, agent_type, expected):
        assert party_type_from_agent_type(agent_type) == expected


@pytest.mark.core
class TestRobotRegistration:
    _BASE = dict(
        wallet_address="0x" + "a" * 40,
        capabilities=["data_processing"],
        display_name="Unit One",
    )

    def test_default_is_agent(self):
        req = RegisterAgentExecutorInput(**self._BASE)
        assert req.executor_type == "agent"

    def test_robot_accepted(self):
        req = RegisterAgentExecutorInput(**self._BASE, executor_type="robot")
        assert req.executor_type == "robot"

    def test_human_rejected(self):
        # Humans register via the worker/REST path, not the programmatic one.
        with pytest.raises(Exception):
            RegisterAgentExecutorInput(**self._BASE, executor_type="human")


@pytest.mark.core
class TestPublishRouteAlias:
    """The neutral /api/v1/publish route and the legacy /api/v1/h2a/tasks alias
    both resolve to the same handler (Task 7.2)."""

    def test_both_paths_registered(self):
        from api.h2a import router, create_h2a_task

        post_paths = {
            r.path
            for r in router.routes
            if "POST" in getattr(r, "methods", set())
            and getattr(r, "endpoint", None) is create_h2a_task
        }
        assert "/api/v1/publish" in post_paths
        assert "/api/v1/h2a/tasks" in post_paths


# ============================================================================
# Universal Escrow Matrix (MASTER_PLAN_UNIVERSAL_ESCROW_CONSISTENCY Task 5.2)
# ============================================================================
#
# 9 cells = {human, agent, robot} publishers x {human, agent, robot} executors.
# Publisher side has exactly 2 rails:
#   - human  -> JWT + api/h2a.py (marker at publish, fresh-auth lock at assign,
#               releasable escrow at approve, refund/free-cancel at cancel)
#   - agent  -> ERC-8128 + api/routers/tasks.py (Mode B stored pre-auth at
#     robot    publish, lock_stored_preauth at assign). Robots authenticate
#               exactly like agents; tasks.publisher_type='robot' is recorded
#               from the wallet's registered executor_type (Task 5.1).
# Executor side only contributes the receiver wallet — the party gates for who
# may apply/accept are covered by TestCanExecute above and the apply/accept
# enforcement suites. All network/DB access is mocked.

PUBLISHER_WALLET = "0x" + "11" * 20
WORKER_WALLETS = {
    "human": "0x" + "aa" * 20,
    "agent": "0x" + "bb" * 20,
    "robot": "0x" + "cc" * 20,
}
LOCK_TX = "0x" + "ab" * 32  # built by concatenation (pre-commit key scan)
H2A_TASK_ID = "00000000-0000-0000-0000-00000000beef"
REST_TASK_ID = "12345678-1234-1234-1234-1234567890ab"
EXECUTOR_UUID = "87654321-4321-4321-4321-ba0987654321"
SUB_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

_ESCROW_MARKER = {
    "id": "esc-matrix-1",
    "status": "pending_assignment",
    "metadata": {"escrow_timing": "sign_on_assignment", "network": "base"},
}


# ---------------------------------------------------------------------------
# Human rail helpers (direct handler calls — mirrors test_h2a_escrow.py)
# ---------------------------------------------------------------------------


def _jwt_auth():
    from api.h2a import JWTData

    return JWTData(user_id="user-1", wallet_address=PUBLISHER_WALLET)


def _h2a_publish_request(target):
    return PublishH2ATaskRequest(
        title="Escrow matrix task",
        instructions="Do something verifiable for the escrow matrix",
        category="data_processing",
        bounty_usd=5.0,
        deadline_hours=24,
        evidence_required=["text_report"],
        target_executor_type=target,
    )


def _h2a_publish_client(task_id=H2A_TASK_ID):
    client = MagicMock()
    ins = MagicMock()
    ins.data = [{"id": task_id, "status": "published"}]
    client.table.return_value.insert.return_value.execute.return_value = ins
    return client


def _h2a_task_row(status="published"):
    return {
        "id": H2A_TASK_ID,
        "human_user_id": "user-1",
        "human_wallet": PUBLISHER_WALLET,
        "publisher_type": "human",
        "status": status,
        "bounty_usd": 5.0,
        "payment_network": "base",
        "payment_token": "USDC",
    }


def _recorder(updates, table):
    def _update(data):
        updates.append((table, data))
        return MagicMock()

    return _update


def _h2a_assign_client(updates, worker_wallet):
    client = MagicMock()
    task_chain = MagicMock()
    task_res = MagicMock()
    task_res.data = _h2a_task_row()
    task_chain.single.return_value.execute.return_value = task_res

    app_res = MagicMock()
    app_res.data = [{"id": "app-1"}]
    exec_res = MagicMock()
    exec_res.data = [{"wallet_address": worker_wallet}]

    def table_side_effect(name):
        t = MagicMock()
        if name == "tasks":
            t.select.return_value.eq.return_value = task_chain
            t.update.side_effect = _recorder(updates, "tasks")
        elif name == "task_applications":
            t.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = app_res
            t.update.side_effect = _recorder(updates, "task_applications")
        elif name == "executors":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = exec_res
        return t

    client.table.side_effect = table_side_effect
    return client


def _h2a_approve_client(updates, esc_rows, worker_wallet):
    client = MagicMock()
    task_chain = MagicMock()
    task_res = MagicMock()
    task_res.data = _h2a_task_row(status="submitted")
    task_chain.single.return_value.execute.return_value = task_res

    sub_chain = MagicMock()
    sub_res = MagicMock()
    sub_res.data = {
        "id": SUB_UUID,
        "task_id": H2A_TASK_ID,
        "executor": {
            "id": "executor-1",
            "wallet_address": worker_wallet,
            "display_name": "Matrix Worker",
        },
    }
    sub_chain.single.return_value.execute.return_value = sub_res

    esc_res = MagicMock()
    esc_res.data = esc_rows

    def table_side_effect(name):
        t = MagicMock()
        if name == "tasks":
            t.select.return_value.eq.return_value = task_chain
            t.update.side_effect = _recorder(updates, "tasks")
        elif name == "submissions":
            t.select.return_value.eq.return_value.eq.return_value = sub_chain
            t.update.side_effect = _recorder(updates, "submissions")
        elif name == "escrows":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = esc_res
        return t

    client.table.side_effect = table_side_effect
    return client


def _h2a_cancel_client(updates, esc_rows, task_status="published"):
    client = MagicMock()
    task_chain = MagicMock()
    task_res = MagicMock()
    task_res.data = _h2a_task_row(status=task_status)
    task_chain.single.return_value.execute.return_value = task_res

    esc_res = MagicMock()
    esc_res.data = esc_rows

    def table_side_effect(name):
        t = MagicMock()
        if name == "tasks":
            t.select.return_value.eq.return_value = task_chain
            t.update.side_effect = _recorder(updates, "tasks")
        elif name == "escrows":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = esc_res
            t.update.side_effect = _recorder(updates, "escrows")
        return t

    client.table.side_effect = table_side_effect
    return client


# ---------------------------------------------------------------------------
# Wallet rail helpers (route-level — mirrors test_evm_balance_gate_routes.py)
# ---------------------------------------------------------------------------


def _wallet_auth():
    """An ERC-8128 wallet-authed publisher (agents and robots auth alike)."""
    auth = MagicMock()
    auth.agent_id = PUBLISHER_WALLET
    auth.wallet_address = PUBLISHER_WALLET
    auth.auth_method = "erc8128"
    auth.erc8004_registered = True
    return auth


class _Chain:
    """Chainable Supabase query stub: every method returns self, .data fixed."""

    def __init__(self, data=None):
        self.data = data if data is not None else []

    def execute(self):
        return self

    def __getattr__(self, _name):
        def _passthrough(*_a, **_kw):
            return self

        return _passthrough


class _ClientStub:
    def __init__(self, tables=None):
        self._tables = tables or {}

    def table(self, name):
        return _Chain(self._tables.get(name))


def _tasks_app(auth):
    from fastapi import FastAPI
    from api.auth import verify_agent_auth_write
    from api.routers.tasks import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_agent_auth_write] = lambda: auth
    return app


def _http_client(app):
    from fastapi.testclient import TestClient

    try:
        return TestClient(app, raise_server_exceptions=False)
    except TypeError:
        pytest.skip("httpx/starlette TestClient incompatibility")


def _fase2_dispatcher():
    d = MagicMock()
    d.get_mode.return_value = "fase2"
    d.escrow_mode = "direct_release"
    d.validate_agent_preauth = MagicMock(
        return_value={
            "x402Version": 2,
            "payload": {
                "authorization": {
                    "from": PUBLISHER_WALLET,
                    "nonce": "0x" + "ab" * 32,
                },
                "signature": "0x" + "cc" * 65,
                "paymentInfo": {"token": "0x" + "33" * 20, "receiver": ""},
            },
        }
    )
    d.store_preauth = MagicMock(
        return_value={"success": True, "escrow_status": "pending_assignment"}
    )
    return d


_PREAUTH_HEADER = json.dumps({"x402Version": 2, "payload": {"signed": "offline"}})


def _created_task(target):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": REST_TASK_ID,
        "title": "Matrix publish task",
        "status": "published",
        "category": "simple_action",
        "bounty_usd": 5.0,
        "deadline": now,
        "created_at": now,
        "agent_id": PUBLISHER_WALLET,
        "instructions": "Do something verifiable for the escrow matrix",
        "payment_network": "base",
        "payment_token": "USDC",
        "target_executor_type": target,
        "metadata": {},
    }


def _create_body(target):
    return {
        "title": "Matrix publish task",
        "instructions": "Do something verifiable for the escrow matrix",
        "category": "simple_action",
        "bounty_usd": 5.0,
        "deadline_hours": 6,
        "evidence_required": ["photo"],
        "payment_network": "base",
        "payment_token": "USDC",
        "target_executor": target,
    }


# ---------------------------------------------------------------------------
# MCP self-accept helpers (mirrors test_assignment_locks.py)
# ---------------------------------------------------------------------------


def _accept_fn(db_mod):
    mcp = FastMCP("test-escrow-matrix")
    register_agent_executor_tools(mcp, db_mod)
    for tool in mcp._tool_manager._tools.values():
        if tool.name == "em_accept_agent_task":
            return tool.fn
    raise KeyError("Tool em_accept_agent_task not found")


def _accept_db_module(executor_party):
    db_mod = MagicMock()
    db_mod.get_task = AsyncMock(
        return_value={
            "id": H2A_TASK_ID,
            "status": "published",
            "target_executor_type": executor_party,
            "required_capabilities": ["data_processing"],
            "title": "Escrow Matrix Gate Task",
            "bounty_usd": 5.0,
            "instructions": "Do the thing",
            "payment_network": "base",
        }
    )
    db_mod.update_task = AsyncMock(return_value=None)

    exec_result = MagicMock()
    exec_result.data = {
        "id": EXECUTOR_UUID,
        "capabilities": ["data_processing"],
        "reputation_score": 80,
        "executor_type": executor_party,
        "wallet_address": WORKER_WALLETS[executor_party],
    }
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = exec_result
    db_mod.get_client.return_value = mock_client
    return db_mod


@pytest.mark.payments
class TestUniversalEscrowMatrix:
    """Escrow lifecycle x the 9 publisher/executor cells (plan Task 5.2).

    Sections follow the lifecycle: publish marker -> lock at assign ->
    self-accept refusal -> release -> refund.
    """

    # ---- 1. PUBLISH + MARKER -------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target", PARTIES)
    async def test_publish_marker_human_rail(self, monkeypatch, target):
        """Human publisher (flag on) -> create_escrow_marker for each target
        party. Cells: human x {human, agent, robot}."""
        monkeypatch.setenv("EM_H2A_ESCROW_ENABLED", "true")
        from api.h2a import create_h2a_task

        auth = _jwt_auth()
        request = _h2a_publish_request(target)
        mock_client = _h2a_publish_client()

        with (
            patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock),
            patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.01"), Decimal("500.00")),
            ),
            patch(
                "api.h2a.get_platform_fee_percent",
                new_callable=AsyncMock,
                return_value=Decimal("0.13"),
            ),
            patch("api.h2a.db.get_client", return_value=mock_client),
            patch("api.h2a.create_escrow_marker", new_callable=AsyncMock) as marker,
        ):
            result = await create_h2a_task(request=request, auth=auth)

        assert result.task_id == H2A_TASK_ID
        marker.assert_awaited_once_with(H2A_TASK_ID, 5.0, "base", PUBLISHER_WALLET)
        inserted = mock_client.table.return_value.insert.call_args[0][0]
        assert inserted["target_executor_type"] == target
        assert inserted["publisher_type"] == "human"

    @pytest.mark.parametrize("publisher", ["agent", "robot"])
    @pytest.mark.parametrize("target", PARTIES)
    def test_publish_preauth_wallet_rail(self, publisher, target):
        """Agent/robot publisher + X-Payment-Auth -> Mode B store_preauth
        (escrows pending_assignment row), no on-chain lock at publish.
        Cells: {agent, robot} x {human, agent, robot}."""
        auth = _wallet_auth()
        dispatcher = _fase2_dispatcher()
        robot_rows = [{"id": "robot-exec-1"}] if publisher == "robot" else []

        mock_db = MagicMock()
        mock_db.get_task_by_idempotency_key = AsyncMock(return_value=None)
        mock_db.create_task = AsyncMock(return_value=_created_task(target))
        mock_db.update_task = AsyncMock(return_value={})
        mock_db.get_client.return_value = _ClientStub({"executors": robot_rows})

        app = _tasks_app(auth)
        with (
            patch("api.routers.tasks.db", mock_db),
            patch("api.routers.tasks.X402_AVAILABLE", True),
            patch("api.routers.tasks.ERC8004_IDENTITY_AVAILABLE", False),
            patch("api.routers.tasks.get_payment_dispatcher", return_value=dispatcher),
            patch(
                "integrations.x402.payment_events.log_payment_event",
                new=AsyncMock(),
            ),
        ):
            resp = _http_client(app).post(
                "/api/v1/tasks",
                json=_create_body(target),
                headers={
                    "X-Payment-Auth": _PREAUTH_HEADER,
                    "X-Escrow-Timing": "lock_on_assignment",
                },
            )

        assert resp.status_code == 201, resp.text
        assert resp.json()["target_executor_type"] == target

        # Mode B: the signed pre-auth was stored for deferred lock...
        dispatcher.store_preauth.assert_called_once()
        s_args = dispatcher.store_preauth.call_args[0]
        assert s_args[0] == REST_TASK_ID
        assert s_args[1] == _PREAUTH_HEADER
        assert s_args[3] == "base"
        # ...and nothing was locked on-chain at publish.
        dispatcher.relay_agent_auth_to_facilitator.assert_not_called()

        # Robot publishers are recorded on the task; agents keep the default.
        publisher_updates = [
            c.args[1]
            for c in mock_db.update_task.await_args_list
            if c.args[1].get("publisher_type")
        ]
        if publisher == "robot":
            assert {"publisher_type": "robot"} in publisher_updates
        else:
            assert publisher_updates == []

    # ---- 2. LOCK AT ASSIGN ---------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.parametrize("party", PARTIES)
    async def test_assign_lock_human_rail(self, party):
        """Human publisher assigns with X-Payment-Auth -> lock_with_fresh_auth
        receives the chosen worker's wallet (any executor party) and the task
        lands accepted."""
        from api.h2a import H2AAssignRequest, assign_h2a_worker

        worker_wallet = WORKER_WALLETS[party]
        updates = []
        mock_client = _h2a_assign_client(updates, worker_wallet)

        with (
            patch("api.h2a.db.get_client", return_value=mock_client),
            patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_ESCROW_MARKER),
            ),
            patch("api.h2a.get_payment_dispatcher", return_value=MagicMock()),
            patch(
                "api.h2a.lock_with_fresh_auth",
                new_callable=AsyncMock,
                return_value={
                    "status": "locked",
                    "escrow_tx": LOCK_TX,
                    "network": "base",
                },
            ) as lock_mock,
        ):
            result = await assign_h2a_worker(
                task_id=H2A_TASK_ID,
                request=H2AAssignRequest(executor_id=EXECUTOR_UUID),
                auth=_jwt_auth(),
                x_payment_auth=_PREAUTH_HEADER,
            )

        assert result["status"] == "accepted"
        assert result["escrow_tx"] == LOCK_TX
        assert (
            "tasks",
            {"executor_id": EXECUTOR_UUID, "status": "accepted"},
        ) in updates
        call = lock_mock.await_args
        assert call.args[0] == H2A_TASK_ID
        assert call.args[2] == worker_wallet  # receiver = chosen executor
        assert call.args[3] == _PREAUTH_HEADER
        assert call.kwargs["expected_payer"] == PUBLISHER_WALLET

    @pytest.mark.parametrize("party", PARTIES)
    def test_assign_lock_wallet_rail(self, party):
        """Agent/robot publisher REST assign -> lock_stored_preauth executes
        the stored pre-auth with the worker's wallet as receiver and the
        response carries the escrow lock."""
        worker_wallet = WORKER_WALLETS[party]
        auth = _wallet_auth()
        now = datetime.now(timezone.utc).isoformat()
        task_row = {
            "id": REST_TASK_ID,
            "title": "Matrix assign task",
            "status": "accepted",
            "assigned_at": now,
            "bounty_usd": 5.0,
            "payment_network": "base",
            "agent_id": PUBLISHER_WALLET,
        }

        mock_db = MagicMock()
        mock_db.get_task = AsyncMock(return_value=task_row)
        mock_db.assign_task = AsyncMock(
            return_value={
                "task": dict(task_row),
                "executor": {"wallet_address": worker_wallet},
            }
        )
        mock_db.update_task = AsyncMock(return_value={})
        mock_db.get_client.return_value = _ClientStub()

        lock_mock = AsyncMock(
            return_value={
                "status": "locked",
                "escrow_tx": LOCK_TX,
                "network": "base",
            }
        )

        app = _tasks_app(auth)
        with (
            patch("api.routers.tasks.db", mock_db),
            patch(
                "api.routers.tasks.get_payment_dispatcher",
                return_value=_fase2_dispatcher(),
            ),
            patch("integrations.x402.escrow_lock.lock_stored_preauth", new=lock_mock),
        ):
            resp = _http_client(app).post(
                f"/api/v1/tasks/{REST_TASK_ID}/assign",
                json={"executor_id": EXECUTOR_UUID},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["escrow"]["escrow_tx"] == LOCK_TX
        assert data["worker_wallet"] == worker_wallet
        lock_mock.assert_awaited_once()
        l_args = lock_mock.await_args.args
        assert l_args[0] == REST_TASK_ID
        assert l_args[2] == worker_wallet  # receiver = chosen executor

    # ---- 3. SELF-ACCEPT REFUSAL (D2 / EC-15) ----------------------------

    @pytest.mark.asyncio
    @pytest.mark.parametrize("party", ["agent", "robot"])
    async def test_self_accept_refused_for_escrow_tasks(self, monkeypatch, party):
        """em_accept_agent_task refuses escrow-mode tasks for agent AND robot
        executors (humans never self-accept via MCP): the escrow signature
        commits to the chosen worker, so only the publisher can assign."""
        marker_mock = AsyncMock(return_value=dict(_ESCROW_MARKER))
        monkeypatch.setattr(escrow_lock, "get_escrow_marker", marker_mock)

        db_mod = _accept_db_module(party)
        fn = _accept_fn(db_mod)

        result = await fn(
            AcceptAgentTaskInput(task_id=H2A_TASK_ID, executor_id=EXECUTOR_UUID)
        )

        assert result.startswith("Error")
        assert "escrow" in result.lower()
        assert "em_apply_to_task" in result
        marker_mock.assert_awaited_once_with(H2A_TASK_ID)
        db_mod.update_task.assert_not_awaited()  # no state mutated

    # ---- 4. RELEASE (approve, no signatures) -----------------------------

    @pytest.mark.asyncio
    async def test_release_human_rail_without_signatures(self):
        """Human rail approve with a releasable escrow -> single gasless
        release_direct_to_worker call, no settlement_auth_* signatures.

        Wallet rail (agent/robot publishers) releases through the same
        PaymentDispatcher.release_direct_to_worker — covered in the payments
        suite (test_payment_dispatcher.py, test_escrow_settlement_safety.py).
        """
        from api.h2a import approve_h2a_submission

        updates = []
        mock_client = _h2a_approve_client(
            updates,
            esc_rows=[{"id": "esc-1", "status": "deposited", "funding_tx": LOCK_TX}],
            worker_wallet=WORKER_WALLETS["agent"],
        )
        dispatcher = MagicMock()
        dispatcher.release_direct_to_worker = AsyncMock(
            return_value={
                "success": True,
                "tx_hash": LOCK_TX,
                "fee_distribute_tx": None,
            }
        )

        with (
            patch("api.h2a.db.get_client", return_value=mock_client),
            patch("api.h2a.get_payment_dispatcher", return_value=dispatcher),
        ):
            result = await approve_h2a_submission(
                task_id=H2A_TASK_ID,
                request=ApproveH2ASubmissionRequest(
                    submission_id=SUB_UUID, verdict="accepted"
                ),
                auth=_jwt_auth(),
            )

        assert result.status == "accepted"
        assert result.worker_tx == LOCK_TX
        dispatcher.release_direct_to_worker.assert_awaited_once_with(
            task_id=H2A_TASK_ID, network="base", token="USDC"
        )
        tasks_updates = [d for t, d in updates if t == "tasks"]
        assert any(u.get("status") == "completed" for u in tasks_updates)

    # ---- 5. REFUND (cancel) ----------------------------------------------

    @pytest.mark.asyncio
    async def test_cancel_marker_only_is_free(self):
        """Unlocked marker (no deposit yet) -> free cancel, no refund tx."""
        from api.h2a import cancel_h2a_task

        updates = []
        mock_client = _h2a_cancel_client(updates, esc_rows=[])

        with (
            patch("api.h2a.db.get_client", return_value=mock_client),
            patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_ESCROW_MARKER),
            ),
        ):
            result = await cancel_h2a_task(task_id=H2A_TASK_ID, auth=_jwt_auth())

        assert result["status"] == "cancelled"
        assert "refund_tx" not in result
        assert ("tasks", {"status": "cancelled"}) in updates
        assert ("escrows", {"status": "cancelled"}) in updates

    @pytest.mark.asyncio
    async def test_cancel_deposited_escrow_refunds(self):
        """Deposited escrow -> refund_trustless_escrow back to the publisher,
        then cancel."""
        from api.h2a import cancel_h2a_task

        updates = []
        mock_client = _h2a_cancel_client(
            updates,
            esc_rows=[{"id": "esc-1", "status": "deposited"}],
            task_status="accepted",
        )
        dispatcher = MagicMock()
        dispatcher.refund_trustless_escrow = AsyncMock(
            return_value={"success": True, "tx_hash": LOCK_TX}
        )

        with (
            patch("api.h2a.db.get_client", return_value=mock_client),
            patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("api.h2a.get_payment_dispatcher", return_value=dispatcher),
        ):
            result = await cancel_h2a_task(task_id=H2A_TASK_ID, auth=_jwt_auth())

        assert result["status"] == "cancelled"
        assert result["refund_tx"] == LOCK_TX
        dispatcher.refund_trustless_escrow.assert_awaited_once_with(
            task_id=H2A_TASK_ID, reason="h2a_cancel"
        )
        escrow_updates = [d for t, d in updates if t == "escrows"]
        assert any(u.get("status") == "refunded" for u in escrow_updates)
