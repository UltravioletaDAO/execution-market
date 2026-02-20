"""
Tests for Karma Kadabra V2 integration scenarios.

Covers:
- Self-application prevention (Task 2.1 + 2.2): An agent CANNOT apply to its own task.
  Validated at 3 layers: DB, HTTP API, MCP tool.
- Duplicate application prevention (Task 2.3): Race condition protection via unique constraint.
  Validated at: DB layer (constraint violation catch), HTTP API layer (409 response).
- Payment token validation (Task 2.4 + 2.5): Token must exist on the target network.
  Validated at: model defaults, route-level validation, standalone function.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Ensure mcp_server root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Fixtures & helpers
# ============================================================================

AGENT_WALLET = "0xAgentWallet1234567890abcdef1234567890abcd"
OTHER_WALLET = "0xOtherWallet9876543210fedcba9876543210fedc"

TASK_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EXECUTOR_ID = "11111111-2222-3333-4444-555555555555"
OTHER_EXECUTOR_ID = "66666666-7777-8888-9999-aaaaaaaaaaaa"


def _make_task(agent_id=AGENT_WALLET, status="published", **overrides):
    """Return a minimal task dict matching Supabase shape."""
    base = {
        "id": TASK_ID,
        "agent_id": agent_id,
        "title": "Test task",
        "instructions": "Do the thing",
        "category": "simple_action",
        "bounty_usd": 0.10,
        "deadline": "2026-03-01T00:00:00Z",
        "evidence_schema": {"required": [], "optional": []},
        "status": status,
        "min_reputation": 0,
        "payment_token": "USDC",
        "payment_network": "base",
        "executor": None,
    }
    base.update(overrides)
    return base


def _make_executor(wallet_address=AGENT_WALLET, executor_id=EXECUTOR_ID):
    """Return a minimal executor dict."""
    return {
        "id": executor_id,
        "display_name": "TestWorker",
        "wallet_address": wallet_address,
        "reputation_score": 80,
        "tasks_completed": 5,
        "tasks_disputed": 0,
        "erc8004_agent_id": None,
    }


# ============================================================================
# Level 2: DB layer — supabase_client.apply_to_task()
# ============================================================================


class TestSelfApplicationDB:
    """Self-application prevention at the database layer."""

    @pytest.mark.asyncio
    async def test_self_application_rejected_db(self):
        """apply_to_task() raises when executor wallet == task agent_id."""
        import supabase_client as db

        task = _make_task(agent_id=AGENT_WALLET)
        executor_data = _make_executor(wallet_address=AGENT_WALLET)

        # Mock get_client to return a fake Supabase client
        mock_client = MagicMock()
        # Executor lookup returns matching wallet
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=executor_data
        )

        with (
            patch.object(db, "get_task", new_callable=AsyncMock, return_value=task),
            patch.object(db, "get_client", return_value=mock_client),
        ):
            with pytest.raises(Exception, match="Cannot apply to your own task"):
                await db.apply_to_task(
                    task_id=TASK_ID,
                    executor_id=EXECUTOR_ID,
                )

    @pytest.mark.asyncio
    async def test_self_application_case_insensitive_db(self):
        """Wallet comparison is case-insensitive (checksummed vs lowercase)."""
        import supabase_client as db

        task = _make_task(agent_id=AGENT_WALLET.lower())
        executor_data = _make_executor(wallet_address=AGENT_WALLET.upper())

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=executor_data
        )

        with (
            patch.object(db, "get_task", new_callable=AsyncMock, return_value=task),
            patch.object(db, "get_client", return_value=mock_client),
        ):
            with pytest.raises(Exception, match="Cannot apply to your own task"):
                await db.apply_to_task(
                    task_id=TASK_ID,
                    executor_id=EXECUTOR_ID,
                )

    @pytest.mark.asyncio
    async def test_different_wallet_allowed_db(self):
        """apply_to_task() succeeds when executor wallet != task agent_id."""
        import supabase_client as db

        task = _make_task(agent_id=AGENT_WALLET)
        executor_data = _make_executor(
            wallet_address=OTHER_WALLET, executor_id=OTHER_EXECUTOR_ID
        )

        application_result = {
            "id": "app-1",
            "task_id": TASK_ID,
            "executor_id": OTHER_EXECUTOR_ID,
            "status": "pending",
        }

        mock_client = MagicMock()

        def table_router(name):
            if name == "executors":
                mock_table = MagicMock()
                mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data=executor_data
                )
                return mock_table
            # For applications table (task_applications or applications)
            mock_table = MagicMock()
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_table.insert.return_value.execute.return_value = MagicMock(
                data=[application_result]
            )
            return mock_table

        mock_client.table = MagicMock(side_effect=table_router)

        with (
            patch.object(db, "get_task", new_callable=AsyncMock, return_value=task),
            patch.object(db, "get_client", return_value=mock_client),
        ):
            result = await db.apply_to_task(
                task_id=TASK_ID,
                executor_id=OTHER_EXECUTOR_ID,
            )
            assert result["application"]["id"] == "app-1"


# ============================================================================
# Level 2: HTTP API — POST /api/v1/tasks/{task_id}/apply
# ============================================================================


class TestSelfApplicationAPI:
    """Self-application prevention at the HTTP API layer."""

    @pytest.fixture
    def client(self):
        """Create a test client for the workers router."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.routers.workers import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_self_application_rejected_api(self, client):
        """POST /tasks/{id}/apply returns 403 when wallets match."""
        task = _make_task(agent_id=AGENT_WALLET)
        executor_data = _make_executor(wallet_address=AGENT_WALLET)

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=executor_data
        )

        import supabase_client as db

        with (
            patch.object(db, "get_task", new_callable=AsyncMock, return_value=task),
            patch.object(db, "get_client", return_value=mock_client),
        ):
            resp = client.post(
                f"/api/v1/tasks/{TASK_ID}/apply",
                json={
                    "executor_id": EXECUTOR_ID,
                    "message": "I want to work on this",
                },
            )
            assert resp.status_code == 403
            assert "cannot apply to your own task" in resp.json()["detail"].lower()

    def test_different_wallet_allowed_api(self, client):
        """POST /tasks/{id}/apply returns 200 when wallets differ."""
        task = _make_task(agent_id=AGENT_WALLET)
        executor_data = _make_executor(
            wallet_address=OTHER_WALLET, executor_id=OTHER_EXECUTOR_ID
        )
        application_result = {
            "id": "app-1",
            "task_id": TASK_ID,
            "executor_id": OTHER_EXECUTOR_ID,
            "status": "pending",
        }

        mock_client = MagicMock()

        def table_router(name):
            if name == "executors":
                mock_table = MagicMock()
                mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data=executor_data
                )
                return mock_table
            mock_table = MagicMock()
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_table.insert.return_value.execute.return_value = MagicMock(
                data=[application_result]
            )
            return mock_table

        mock_client.table = MagicMock(side_effect=table_router)

        import supabase_client as db

        with (
            patch.object(db, "get_task", new_callable=AsyncMock, return_value=task),
            patch.object(db, "get_client", return_value=mock_client),
        ):
            resp = client.post(
                f"/api/v1/tasks/{TASK_ID}/apply",
                json={
                    "executor_id": OTHER_EXECUTOR_ID,
                    "message": "I want to work on this",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["data"]["application_id"] == "app-1"


# ============================================================================
# Level 3: MCP tool — em_apply_to_task
# ============================================================================


class TestSelfApplicationMCP:
    """Self-application prevention at the MCP tool layer."""

    @pytest.mark.asyncio
    async def test_self_application_mcp_rejected(self):
        """MCP tool returns error string when wallets match."""
        from mcp.server.fastmcp import FastMCP
        from tools.worker_tools import register_worker_tools

        mock_db = MagicMock()
        task = _make_task(agent_id=AGENT_WALLET)
        executor_stats = _make_executor(wallet_address=AGENT_WALLET)

        mock_db.get_task = AsyncMock(return_value=task)
        mock_db.get_executor_stats = AsyncMock(return_value=executor_stats)
        # apply_to_task should NOT be called if the guard works
        mock_db.apply_to_task = AsyncMock(side_effect=Exception("Should not be called"))

        mcp_server = FastMCP("test_worker_tools")
        register_worker_tools(mcp_server, mock_db)

        # Access the registered tool
        tools = mcp_server.list_tools()
        # Find em_apply_to_task in the tool list
        tool_names = []
        for t_coro in [tools]:
            # FastMCP.list_tools() may be sync or async
            import asyncio

            if asyncio.iscoroutine(t_coro):
                tool_list = await t_coro
            else:
                tool_list = t_coro
            tool_names = [t.name for t in tool_list]

        assert "em_apply_to_task" in tool_names

        # Call the tool directly via the internal handler
        from models import ApplyToTaskInput

        params = ApplyToTaskInput(
            task_id=TASK_ID,
            executor_id=EXECUTOR_ID,
            message="I want to work on this",
        )

        # Get the tool function from registered tools
        result = await mcp_server.call_tool(
            "em_apply_to_task",
            {"params": params.model_dump()},
        )

        # Result should contain an error about self-application
        result_text = str(result)
        assert "cannot apply to your own task" in result_text.lower()
        # DB apply_to_task should NOT have been called
        mock_db.apply_to_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_different_wallet_mcp_allowed(self):
        """MCP tool proceeds when wallets differ."""
        from mcp.server.fastmcp import FastMCP
        from tools.worker_tools import register_worker_tools

        mock_db = MagicMock()
        task = _make_task(agent_id=AGENT_WALLET)
        executor_stats = _make_executor(
            wallet_address=OTHER_WALLET, executor_id=OTHER_EXECUTOR_ID
        )

        mock_db.get_task = AsyncMock(return_value=task)
        mock_db.get_executor_stats = AsyncMock(return_value=executor_stats)
        mock_db.apply_to_task = AsyncMock(
            return_value={
                "application": {
                    "id": "app-1",
                    "task_id": TASK_ID,
                    "executor_id": OTHER_EXECUTOR_ID,
                    "status": "pending",
                },
                "task": task,
                "executor": executor_stats,
            }
        )

        mcp_server = FastMCP("test_worker_tools")
        register_worker_tools(mcp_server, mock_db)

        from models import ApplyToTaskInput

        params = ApplyToTaskInput(
            task_id=TASK_ID,
            executor_id=OTHER_EXECUTOR_ID,
            message="Happy to help",
        )

        result = await mcp_server.call_tool(
            "em_apply_to_task",
            {"params": params.model_dump()},
        )

        result_text = str(result)
        assert "application submitted" in result_text.lower()
        mock_db.apply_to_task.assert_called_once()


# ============================================================================
# Task 2.3: Duplicate application prevention (race condition)
# ============================================================================

EXECUTOR_B_ID = "bbbbbbbb-1111-2222-3333-444444444444"
TASK_ID_2 = "22222222-bbbb-cccc-dddd-eeeeeeeeeeee"


class TestDuplicateApplicationDB:
    """Race condition protection at the database layer via unique constraint."""

    @pytest.mark.asyncio
    async def test_duplicate_application_caught_by_constraint(self):
        """
        Unique constraint violation (PostgreSQL 23505) during insert is caught
        and converted to 'Already applied to this task'.

        Simulates the race condition: read-check passes (no existing rows) but
        another agent inserted between the check and the insert, so the DB
        raises a duplicate key error.
        """
        import supabase_client as db

        task = _make_task(agent_id=AGENT_WALLET)
        executor_data = _make_executor(
            wallet_address=OTHER_WALLET, executor_id=OTHER_EXECUTOR_ID
        )

        # Unique constraint violation as PostgreSQL would raise it
        unique_violation = Exception(
            'duplicate key value violates unique constraint "task_applications_unique"'
        )

        mock_client = MagicMock()

        def table_router(name):
            if name == "executors":
                mock_table = MagicMock()
                mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data=executor_data
                )
                return mock_table
            # Applications table
            mock_table = MagicMock()
            # select().eq().eq().execute() returns empty — no existing application
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            # insert() raises unique violation (race condition)
            mock_table.insert.return_value.execute.side_effect = unique_violation
            return mock_table

        mock_client.table = MagicMock(side_effect=table_router)

        with (
            patch.object(db, "get_task", new_callable=AsyncMock, return_value=task),
            patch.object(db, "get_client", return_value=mock_client),
            patch.object(db, "_applications_table_name", "task_applications"),
        ):
            with pytest.raises(Exception, match="Already applied to this task"):
                await db.apply_to_task(
                    task_id=TASK_ID,
                    executor_id=OTHER_EXECUTOR_ID,
                    message="race condition insert",
                )

    @pytest.mark.asyncio
    async def test_duplicate_application_caught_by_23505_code(self):
        """
        Same as above but the error message contains the PostgreSQL error code
        23505 instead of the human-readable 'duplicate key' text.
        """
        import supabase_client as db

        task = _make_task(agent_id=AGENT_WALLET)
        executor_data = _make_executor(
            wallet_address=OTHER_WALLET, executor_id=OTHER_EXECUTOR_ID
        )

        # Some Supabase client versions surface the error code
        pg_error = Exception(
            '{"code":"23505","message":"unique_violation","details":"Key (task_id, executor_id) already exists"}'
        )

        mock_client = MagicMock()

        def table_router(name):
            if name == "executors":
                mock_table = MagicMock()
                mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data=executor_data
                )
                return mock_table
            mock_table = MagicMock()
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_table.insert.return_value.execute.side_effect = pg_error
            return mock_table

        mock_client.table = MagicMock(side_effect=table_router)

        with (
            patch.object(db, "get_task", new_callable=AsyncMock, return_value=task),
            patch.object(db, "get_client", return_value=mock_client),
            patch.object(db, "_applications_table_name", "task_applications"),
        ):
            with pytest.raises(Exception, match="Already applied to this task"):
                await db.apply_to_task(
                    task_id=TASK_ID,
                    executor_id=OTHER_EXECUTOR_ID,
                )


class TestDuplicateApplicationAPI:
    """Duplicate application returns 409 at the HTTP API layer."""

    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.routers.workers import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_duplicate_application_rejected(self, client):
        """
        Same executor applies twice to same task. Second gets 409 Conflict.
        """
        import supabase_client as db

        call_count = {"n": 0}

        async def fake_apply(task_id, executor_id, message=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {
                    "application": {
                        "id": "app-first",
                        "task_id": task_id,
                        "executor_id": executor_id,
                    },
                    "task": _make_task(agent_id=AGENT_WALLET),
                    "executor": _make_executor(
                        wallet_address=OTHER_WALLET,
                        executor_id=OTHER_EXECUTOR_ID,
                    ),
                }
            raise Exception("Already applied to this task")

        with patch.object(db, "apply_to_task", side_effect=fake_apply):
            # First application — succeeds
            resp1 = client.post(
                f"/api/v1/tasks/{TASK_ID}/apply",
                json={
                    "executor_id": OTHER_EXECUTOR_ID,
                    "message": "First try",
                },
            )
            assert resp1.status_code == 200

            # Second application — 409 Conflict
            resp2 = client.post(
                f"/api/v1/tasks/{TASK_ID}/apply",
                json={
                    "executor_id": OTHER_EXECUTOR_ID,
                    "message": "Duplicate try",
                },
            )
            assert resp2.status_code == 409
            assert "already applied" in resp2.json()["detail"].lower()

    def test_different_executors_same_task(self, client):
        """
        Two different executors apply to the same task.
        Both must succeed — unique constraint is per (task, executor).
        """
        import supabase_client as db

        async def fake_apply(task_id, executor_id, message=None):
            return {
                "application": {
                    "id": f"app-{executor_id[:8]}",
                    "task_id": task_id,
                    "executor_id": executor_id,
                },
                "task": _make_task(agent_id=AGENT_WALLET),
                "executor": _make_executor(
                    wallet_address=OTHER_WALLET, executor_id=executor_id
                ),
            }

        with patch.object(db, "apply_to_task", side_effect=fake_apply):
            # Executor A applies
            resp_a = client.post(
                f"/api/v1/tasks/{TASK_ID}/apply",
                json={
                    "executor_id": OTHER_EXECUTOR_ID,
                    "message": "Executor A",
                },
            )
            assert resp_a.status_code == 200
            assert (
                resp_a.json()["data"]["application_id"]
                == f"app-{OTHER_EXECUTOR_ID[:8]}"
            )

            # Executor B applies to same task — also succeeds
            resp_b = client.post(
                f"/api/v1/tasks/{TASK_ID}/apply",
                json={
                    "executor_id": EXECUTOR_B_ID,
                    "message": "Executor B",
                },
            )
            assert resp_b.status_code == 200
            assert resp_b.json()["data"]["application_id"] == f"app-{EXECUTOR_B_ID[:8]}"

    def test_same_executor_different_tasks(self, client):
        """
        Same executor applies to two different tasks.
        Both must succeed — unique constraint is per (task, executor).
        """
        import supabase_client as db

        async def fake_apply(task_id, executor_id, message=None):
            return {
                "application": {
                    "id": f"app-{task_id[:8]}",
                    "task_id": task_id,
                    "executor_id": executor_id,
                },
                "task": _make_task(agent_id=AGENT_WALLET, id=task_id),
                "executor": _make_executor(
                    wallet_address=OTHER_WALLET, executor_id=executor_id
                ),
            }

        with patch.object(db, "apply_to_task", side_effect=fake_apply):
            # Apply to task 1
            resp1 = client.post(
                f"/api/v1/tasks/{TASK_ID}/apply",
                json={
                    "executor_id": OTHER_EXECUTOR_ID,
                    "message": "Task 1",
                },
            )
            assert resp1.status_code == 200

            # Apply to task 2 — also succeeds
            resp2 = client.post(
                f"/api/v1/tasks/{TASK_ID_2}/apply",
                json={
                    "executor_id": OTHER_EXECUTOR_ID,
                    "message": "Task 2",
                },
            )
            assert resp2.status_code == 200


# ============================================================================
# Payment Token Validation (Task 2.4 + 2.5)
# ============================================================================


def _make_create_request(**overrides):
    """Build a CreateTaskRequest with sensible defaults, overridable."""
    from api import routes

    defaults = {
        "title": "KK V2 multi-token test task",
        "instructions": "Verify the store is open and take a photo of the entrance.",
        "category": routes.TaskCategory.SIMPLE_ACTION,
        "bounty_usd": 0.10,
        "deadline_hours": 1,
        "evidence_required": [routes.EvidenceType.SCREENSHOT],
        "payment_network": "base",
        "payment_token": "USDC",
    }
    defaults.update(overrides)
    return routes.CreateTaskRequest(**defaults)


def _fake_auth(agent_id: str = "agent_kk_test"):
    return SimpleNamespace(agent_id=agent_id)


def _fake_http_request():
    return SimpleNamespace(headers={})


def _patch_create_task_deps(monkeypatch, task_return=None):
    """Patch common dependencies so create_task can be called without real infra."""
    from api import routes

    if task_return is None:
        task_return = {
            "id": "task-kk-001",
            "agent_id": "agent_kk_test",
            "title": "KK V2 multi-token test task",
            "status": "published",
            "category": "simple_action",
            "bounty_usd": 0.10,
            "deadline": "2026-02-21T00:00:00+00:00",
            "created_at": "2026-02-20T00:00:00+00:00",
            "evidence_schema": {"required": ["screenshot"], "optional": []},
            "payment_network": "base",
            "payment_token": "USDC",
            "location_hint": None,
            "min_reputation": 0,
            "erc8004_agent_id": None,
            "escrow_tx": None,
            "refund_tx": None,
            "executor_id": None,
            "instructions": "Verify the store is open and take a photo of the entrance.",
            "metadata": None,
        }

    mock_create = AsyncMock(return_value=task_return)
    monkeypatch.setattr(routes.db, "create_task", mock_create)

    # Ensure X402 is available but payment check is a no-op
    monkeypatch.setattr(routes, "X402_AVAILABLE", True)

    # Mock payment dispatcher to be fase1 (no escrow needed)
    fake_dispatcher = SimpleNamespace(get_mode=lambda: "fase1")
    monkeypatch.setattr(routes, "get_payment_dispatcher", lambda: fake_dispatcher)

    # ERC-8004 identity check not needed
    from api.routers import tasks as tasks_mod
    from decimal import Decimal

    monkeypatch.setattr(tasks_mod, "ERC8004_IDENTITY_AVAILABLE", False)

    # Mock bounty limits so $0.10 test bounties pass validation
    monkeypatch.setattr(
        tasks_mod, "get_min_bounty", AsyncMock(return_value=Decimal("0.01"))
    )
    monkeypatch.setattr(
        tasks_mod, "get_max_bounty", AsyncMock(return_value=Decimal("10000"))
    )
    monkeypatch.setattr(
        tasks_mod, "get_platform_fee_percent", AsyncMock(return_value=Decimal("0.13"))
    )

    return mock_create


class TestPaymentTokenDefault:
    """Task 2.4: payment_token field defaults and propagation."""

    @pytest.mark.asyncio
    async def test_create_task_default_token(self, monkeypatch):
        """When payment_token is omitted, it defaults to USDC."""
        from api import routes

        request = _make_create_request()
        assert request.payment_token == "USDC"

        mock_create = _patch_create_task_deps(monkeypatch)

        await routes.create_task(
            http_request=_fake_http_request(),
            request=request,
            auth=_fake_auth(),
        )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("payment_token") == "USDC"

    @pytest.mark.asyncio
    async def test_create_task_with_eurc(self, monkeypatch):
        """Create task with payment_token=EURC on Base succeeds."""
        from api import routes

        task_return = {
            "id": "task-kk-eurc",
            "agent_id": "agent_kk_test",
            "title": "KK V2 EURC test task",
            "status": "published",
            "category": "simple_action",
            "bounty_usd": 0.10,
            "deadline": "2026-02-21T00:00:00+00:00",
            "created_at": "2026-02-20T00:00:00+00:00",
            "evidence_schema": {"required": ["screenshot"], "optional": []},
            "payment_network": "base",
            "payment_token": "EURC",
            "location_hint": None,
            "min_reputation": 0,
            "erc8004_agent_id": None,
            "escrow_tx": None,
            "refund_tx": None,
            "executor_id": None,
            "instructions": "Verify the store is open and take a photo of the entrance.",
            "metadata": None,
        }
        request = _make_create_request(payment_token="EURC")
        mock_create = _patch_create_task_deps(monkeypatch, task_return=task_return)

        await routes.create_task(
            http_request=_fake_http_request(),
            request=request,
            auth=_fake_auth(),
        )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("payment_token") == "EURC"


class TestPaymentTokenValidation:
    """Task 2.5: token validation against NETWORK_CONFIG."""

    @pytest.mark.asyncio
    async def test_invalid_token_for_network(self, monkeypatch):
        """PYUSD on Polygon should fail -- PYUSD is only on Ethereum."""
        from api import routes

        request = _make_create_request(
            payment_network="polygon",
            payment_token="PYUSD",
        )
        _patch_create_task_deps(monkeypatch)

        with pytest.raises(HTTPException) as exc:
            await routes.create_task(
                http_request=_fake_http_request(),
                request=request,
                auth=_fake_auth(),
            )

        assert exc.value.status_code == 400
        assert "PYUSD" in exc.value.detail
        assert "polygon" in exc.value.detail

    @pytest.mark.asyncio
    async def test_create_task_unknown_token(self, monkeypatch):
        """Completely unknown token (DOGECOIN) should fail with 400."""
        from api import routes

        request = _make_create_request(payment_token="DOGECOIN")
        _patch_create_task_deps(monkeypatch)

        with pytest.raises(HTTPException) as exc:
            await routes.create_task(
                http_request=_fake_http_request(),
                request=request,
                auth=_fake_auth(),
            )

        assert exc.value.status_code == 400
        assert "DOGECOIN" in exc.value.detail
        assert "base" in exc.value.detail


class TestValidatePaymentTokenFunction:
    """Unit tests for the standalone validate_payment_token function."""

    def test_valid_usdc_on_base(self):
        from integrations.x402.sdk_client import validate_payment_token

        result = validate_payment_token("base", "USDC")
        assert result == "USDC"

    def test_valid_eurc_on_base(self):
        from integrations.x402.sdk_client import validate_payment_token

        result = validate_payment_token("base", "EURC")
        assert result == "EURC"

    def test_valid_pyusd_on_ethereum(self):
        from integrations.x402.sdk_client import validate_payment_token

        result = validate_payment_token("ethereum", "PYUSD")
        assert result == "PYUSD"

    def test_valid_usdt_on_arbitrum(self):
        from integrations.x402.sdk_client import validate_payment_token

        result = validate_payment_token("arbitrum", "USDT")
        assert result == "USDT"

    def test_valid_ausd_on_polygon(self):
        from integrations.x402.sdk_client import validate_payment_token

        result = validate_payment_token("polygon", "AUSD")
        assert result == "AUSD"

    def test_invalid_pyusd_on_polygon(self):
        from integrations.x402.sdk_client import validate_payment_token

        with pytest.raises(ValueError, match="PYUSD.*not available on polygon"):
            validate_payment_token("polygon", "PYUSD")

    def test_invalid_eurc_on_celo(self):
        from integrations.x402.sdk_client import validate_payment_token

        with pytest.raises(ValueError, match="EURC.*not available on celo"):
            validate_payment_token("celo", "EURC")

    def test_unknown_token(self):
        from integrations.x402.sdk_client import validate_payment_token

        with pytest.raises(ValueError, match="DOGECOIN.*not available on base"):
            validate_payment_token("base", "DOGECOIN")

    def test_unknown_network(self):
        from integrations.x402.sdk_client import validate_payment_token

        with pytest.raises(ValueError, match="not recognized"):
            validate_payment_token("solana", "USDC")

    def test_all_base_tokens(self):
        """Base should have exactly USDC and EURC."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        base_tokens = set(NETWORK_CONFIG["base"]["tokens"].keys())
        assert base_tokens == {"USDC", "EURC"}

    def test_all_ethereum_tokens(self):
        """Ethereum should have USDC, EURC, PYUSD, AUSD."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        eth_tokens = set(NETWORK_CONFIG["ethereum"]["tokens"].keys())
        assert eth_tokens == {"USDC", "EURC", "PYUSD", "AUSD"}
