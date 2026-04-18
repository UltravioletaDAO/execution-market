"""
Tests for admin API endpoints (config, stats, tasks, payments, users, analytics, audit).

Covers 20 endpoints in api/admin.py that were previously untested.
Each test mocks the Supabase client to avoid real database calls.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.admin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# admin.py does: `import supabase_client as db` then `db.get_supabase_client()`
# and audit_summary uses `db.get_client()`.  We patch the module-level reference.
ADMIN_DB = "api.admin.db"


def _admin():
    """Bypass admin auth for testing."""
    return {"role": "admin", "auth_source": "test", "actor_id": "test-admin"}


def _resp(data=None, count=None):
    """Create a mock Supabase response object."""
    r = MagicMock()
    r.data = data if data is not None else []
    r.count = count
    return r


class _QB:
    """Minimal Supabase query builder stub — every method returns self, execute() returns the response."""

    def __init__(self, response):
        self._r = response

    def select(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def in_(self, *a, **kw):
        return self

    def is_(self, *a, **kw):
        return self

    def or_(self, *a, **kw):
        return self

    def like(self, *a, **kw):
        return self

    def gte(self, *a, **kw):
        return self

    def order(self, *a, **kw):
        return self

    def range(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def single(self, *a, **kw):
        return self

    def update(self, *a, **kw):
        return self

    def execute(self):
        return self._r


def _client_single(response):
    """Client where every table() call returns the same response."""
    c = MagicMock()
    c.table.return_value = _QB(response)
    return c


def _client_by_table(table_map):
    """Client where table(name) returns a response from *table_map*."""
    empty = _resp()

    def _t(name):
        return _QB(table_map.get(name, empty))

    c = MagicMock()
    c.table.side_effect = _t
    return c


def _client_sequence(responses):
    """Client where successive table() calls return successive responses."""
    idx = {"n": 0}

    def _t(name):
        r = responses[min(idx["n"], len(responses) - 1)]
        idx["n"] += 1
        return _QB(r)

    c = MagicMock()
    c.table.side_effect = _t
    return c


# ==========================================================================
# CONFIG ENDPOINTS
# ==========================================================================


class TestGetAllConfig:
    """GET /api/v1/admin/config"""

    @pytest.mark.asyncio
    async def test_get_all_config(self):
        rows = [
            {"key": "fees.platform_fee_pct", "value": 0.13, "category": "fees"},
            {"key": "limits.max_bounty", "value": 100, "category": "limits"},
            {"key": "timing.expiry_hours", "value": 24, "category": "timing"},
            {"key": "features.escrow", "value": True, "category": "features"},
            {
                "key": "payments.default_network",
                "value": "base",
                "category": "payments",
            },
            {"key": "treasury.address", "value": "0xTreasury", "category": "treasury"},
        ]
        db = _client_single(_resp(data=rows))

        with (
            patch(f"{ADMIN_DB}.get_supabase_client", return_value=db),
            patch("api.admin.CONFIG_AVAILABLE", True),
        ):
            from api.admin import get_all_config

            result = await get_all_config(admin=_admin())

        assert result.fees["platform_fee_pct"] == 0.13
        assert result.limits["max_bounty"] == 100
        assert result.features["escrow"] is True


class TestGetConfigValue:
    """GET /api/v1/admin/config/{key}"""

    @pytest.mark.asyncio
    async def test_get_config_value(self):
        row = {
            "key": "fees.platform_fee_pct",
            "value": 0.13,
            "description": "Platform fee",
            "category": "fees",
            "is_public": True,
            "updated_at": None,
        }
        db = _client_single(_resp(data=[row]))

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_config_value

            result = await get_config_value(key="fees.platform_fee_pct", admin=_admin())

        assert result.key == "fees.platform_fee_pct"
        assert result.value == 0.13
        assert result.category == "fees"


class TestUpdateConfigValue:
    """PUT /api/v1/admin/config/{key}"""

    @pytest.mark.asyncio
    async def test_update_config_value(self):
        # Sequential: 1) get current, 2) update, 3) audit lookup, 4) audit update
        db = _client_sequence(
            [
                _resp(data=[{"value": 0.13}]),  # select current
                _resp(data=[{"key": "fees.platform_fee_pct", "value": 0.15}]),  # update
                _resp(data=[{"id": "audit-1"}]),  # audit select
                _resp(data=[{"id": "audit-1"}]),  # audit update
            ]
        )

        with (
            patch(f"{ADMIN_DB}.get_supabase_client", return_value=db),
            patch("api.admin.CONFIG_AVAILABLE", False),
        ):
            from api.admin import update_config_value, ConfigUpdateRequest

            req = ConfigUpdateRequest(value=0.15, reason="Testing")
            result = await update_config_value(
                key="fees.platform_fee_pct", request=req, admin=_admin()
            )

        assert result.success is True
        assert result.old_value == 0.13
        assert result.new_value == 0.15


class TestGetConfigAuditLog:
    """GET /api/v1/admin/config/audit"""

    @pytest.mark.asyncio
    async def test_get_config_audit_log(self):
        rows = [
            {
                "id": "log-1",
                "config_key": "fees.platform_fee_pct",
                "old_value": 0.10,
                "new_value": 0.13,
                "changed_by": "admin",
                "reason": "Increase fee",
                "changed_at": "2026-03-01T00:00:00+00:00",
            }
        ]
        db = _client_single(_resp(data=rows, count=1))

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_config_audit_log

            result = await get_config_audit_log(
                key=None, limit=50, offset=0, category=None, admin=_admin()
            )

        assert result.count == 1
        assert len(result.entries) == 1
        assert result.entries[0].config_key == "fees.platform_fee_pct"


# ==========================================================================
# STATS
# ==========================================================================


class TestGetPlatformStats:
    """GET /api/v1/admin/stats"""

    @pytest.mark.asyncio
    async def test_get_platform_stats(self):
        tasks_data = [
            {"status": "published", "bounty_usd": 5.0},
            {"status": "completed", "bounty_usd": 10.0},
            {"status": "completed", "bounty_usd": 8.0},
        ]
        db = _client_by_table(
            {
                "tasks": _resp(data=tasks_data),
                "executors": _resp(data=[], count=3),
                "api_keys": _resp(data=[], count=2),
                "submissions": _resp(data=[], count=1),
            }
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_platform_stats

            result = await get_platform_stats(admin=_admin())

        assert result["tasks"]["total"] == 3
        assert result["tasks"]["by_status"]["completed"] == 2
        assert result["users"]["active_workers"] == 3
        assert result["users"]["active_agents"] == 2
        assert "generated_at" in result


# ==========================================================================
# TASK ENDPOINTS
# ==========================================================================


class TestListTasks:
    """GET /api/v1/admin/tasks"""

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        tasks = [
            {
                "id": "t-1",
                "title": "Task 1",
                "status": "published",
                "created_at": "2026-03-01T00:00:00Z",
            },
            {
                "id": "t-2",
                "title": "Task 2",
                "status": "completed",
                "created_at": "2026-03-02T00:00:00Z",
            },
        ]
        # list_tasks calls table("tasks") twice: once for query, once for status counts
        db = _client_sequence(
            [
                _resp(data=tasks, count=2),
                _resp(data=[{"status": "published"}, {"status": "completed"}]),
            ]
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import list_tasks

            result = await list_tasks(
                status=None, search=None, limit=20, offset=0, admin=_admin()
            )

        assert result["count"] == 2
        assert len(result["tasks"]) == 2


class TestGetTaskDetail:
    """GET /api/v1/admin/tasks/{task_id}"""

    @pytest.mark.asyncio
    async def test_get_task_detail(self):
        task = {
            "id": "t-1",
            "title": "Task 1",
            "status": "published",
            "bounty_usd": 5.0,
            "instructions": "Do the thing",
        }
        db = _client_single(_resp(data=task))

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_task_detail

            result = await get_task_detail(task_id="t-1", admin=_admin())

        assert result["id"] == "t-1"
        assert result["title"] == "Task 1"


class TestUpdateTask:
    """PUT /api/v1/admin/tasks/{task_id}"""

    @pytest.mark.asyncio
    async def test_update_task(self):
        updated = {
            "id": "t-1",
            "title": "Updated Title",
            "bounty_usd": 15.0,
            "status": "published",
        }
        db = _client_single(_resp(data=[updated]))

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import update_task

            result = await update_task(
                task_id="t-1",
                updates={"title": "Updated Title", "bounty_usd": 15.0},
                admin=_admin(),
            )

        assert result["success"] is True
        assert result["task"]["title"] == "Updated Title"


class TestCancelTask:
    """POST /api/v1/admin/tasks/{task_id}/cancel"""

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        task = {"id": "t-1", "status": "published", "title": "Task 1"}
        # cancel_task calls table("tasks") twice: select then update
        db = _client_sequence(
            [
                _resp(data=task),  # fetch task via .single()
                _resp(data=[{**task, "status": "cancelled"}]),  # update
            ]
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import cancel_task

            result = await cancel_task(
                task_id="t-1",
                body={"reason": "Test cancel"},
                admin=_admin(),
            )

        assert result["success"] is True
        assert "t-1" in result["message"]


# ==========================================================================
# PAYMENT ENDPOINTS
# ==========================================================================


class TestListPayments:
    """GET /api/v1/admin/payments"""

    @pytest.mark.asyncio
    async def test_list_payments(self):
        tasks = [
            {
                "id": "t-1",
                "created_at": "2026-03-25T10:00:00Z",
                "status": "completed",
                "bounty_usd": 5.0,
                "agent_id": "agent-1",
                "escrow_tx": "0xabc",
            },
            {
                "id": "t-2",
                "created_at": "2026-03-25T11:00:00Z",
                "status": "cancelled",
                "bounty_usd": 3.0,
                "agent_id": "agent-2",
                "escrow_tx": None,
            },
        ]
        db = _client_single(_resp(data=tasks, count=2))

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import list_payments

            result = await list_payments(
                period="7d", limit=20, offset=0, admin=_admin()
            )

        assert result["count"] == 2
        assert len(result["transactions"]) == 2
        assert result["transactions"][0]["type"] == "release"
        assert result["transactions"][1]["type"] == "refund"


class TestGetPaymentStats:
    """GET /api/v1/admin/payments/stats"""

    @pytest.mark.asyncio
    async def test_get_payment_stats(self):
        tasks = [
            {
                "bounty_usd": 10.0,
                "status": "completed",
                "created_at": "2026-03-25T10:00:00Z",
            },
            {
                "bounty_usd": 5.0,
                "status": "published",
                "created_at": "2026-03-25T11:00:00Z",
            },
        ]
        # get_payment_stats calls table("tasks") then table("platform_config")
        db = _client_by_table(
            {
                "tasks": _resp(data=tasks),
                "platform_config": _resp(data=[{"value": 0.13}]),
            }
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_payment_stats

            result = await get_payment_stats(period="all", admin=_admin())

        assert result["total_volume_usd"] == 15.0
        assert result["total_fees_usd"] == 1.3
        assert result["active_escrow_usd"] == 5.0
        assert result["transaction_count"] == 2


# ==========================================================================
# USER ENDPOINTS
# ==========================================================================


class TestListAgents:
    """GET /api/v1/admin/users/agents"""

    @pytest.mark.asyncio
    async def test_list_agents(self):
        agents = [
            {
                "id": "key-1",
                "agent_id": "0xAgent1",
                "name": "TestAgent",
                "tier": "pro",
                "created_at": "2026-03-01T00:00:00Z",
                "is_active": True,
                "usage_count": 10,
            }
        ]
        # list_agents: table("api_keys"), then for each agent: table("tasks") x2
        db = _client_sequence(
            [
                _resp(data=agents, count=1),  # api_keys
                _resp(data=[], count=5),  # tasks count
                _resp(data=[{"bounty_usd": 2.0}, {"bounty_usd": 3.0}]),  # tasks spent
            ]
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import list_agents

            result = await list_agents(limit=20, offset=0, admin=_admin())

        assert result["count"] == 1
        assert len(result["users"]) == 1
        assert result["users"][0]["wallet_address"] == "0xAgent1"
        assert result["users"][0]["status"] == "active"


class TestListWorkers:
    """GET /api/v1/admin/users/workers"""

    @pytest.mark.asyncio
    async def test_list_workers(self):
        workers = [
            {
                "id": "w-1",
                "wallet_address": "0xWorker1",
                "display_name": "Worker One",
                "created_at": "2026-03-01T00:00:00Z",
                "total_earned_usdc": 50.0,
                "reputation_score": 85,
                "status": "active",
            }
        ]
        # list_workers: table("executors"), then for each worker: table("tasks")
        db = _client_sequence(
            [
                _resp(data=workers, count=1),
                _resp(data=[], count=3),
            ]
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import list_workers

            result = await list_workers(limit=20, offset=0, admin=_admin())

        assert result["count"] == 1
        assert len(result["users"]) == 1
        assert result["users"][0]["wallet_address"] == "0xWorker1"
        assert result["users"][0]["reputation_score"] == 85


class TestUpdateUserStatus:
    """PUT /api/v1/admin/users/{user_id}/status"""

    @pytest.mark.asyncio
    async def test_update_user_status_agent(self):
        """Suspend an agent (found in api_keys table)."""
        db = _client_single(_resp(data=[{"id": "key-1", "is_active": False}]))

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import update_user_status

            result = await update_user_status(
                user_id="key-1",
                body={"status": "suspended"},
                admin=_admin(),
            )

        assert result["success"] is True
        assert result["status"] == "suspended"
        assert result["type"] == "agent"


# ==========================================================================
# ANALYTICS
# ==========================================================================


class TestGetAnalytics:
    """GET /api/v1/admin/analytics"""

    @pytest.mark.asyncio
    async def test_get_analytics(self):
        tasks = [
            {
                "created_at": "2026-03-25T10:00:00Z",
                "status": "completed",
                "updated_at": "2026-03-25T12:00:00Z",
                "bounty_usd": 5.0,
            }
        ]
        # get_analytics: table("tasks"), table("api_keys"), table("executors")
        # (plus inner loops for task counts, but those also hit table("tasks"))
        db = _client_sequence(
            [
                _resp(data=tasks),  # tasks for time series
                _resp(data=[]),  # api_keys (agents)
                _resp(data=[]),  # executors (workers)
            ]
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_analytics

            result = await get_analytics(period="30d", admin=_admin())

        assert "time_series" in result
        assert "top_agents" in result
        assert "top_workers" in result
        assert "trends" in result


# ==========================================================================
# AUDIT SUMMARY
# ==========================================================================


class TestAuditSummary:
    """GET /api/v1/admin/audit/summary"""

    @pytest.mark.asyncio
    async def test_audit_summary(self):
        tasks = [
            {
                "id": "t-1",
                "status": "completed",
                "bounty_usd": 10.0,
                "payment_network": "base",
                "created_at": "2026-03-27T00:00:00Z",
            },
            {
                "id": "t-2",
                "status": "published",
                "bounty_usd": 5.0,
                "payment_network": "base",
                "created_at": "2026-03-27T01:00:00Z",
            },
        ]
        events = [
            {
                "event_type": "escrow_release",
                "amount": 10.0,
                "status": "success",
                "tx_hash": "0xabc",
            },
        ]
        escrows = [
            {
                "task_id": "t-3",
                "amount": 7.0,
                "status": "locked",
                "created_at": "2026-03-27T02:00:00Z",
            },
        ]

        # audit_summary uses db.get_client() (not get_supabase_client)
        db = _client_by_table(
            {
                "tasks": _resp(data=tasks),
                "payment_events": _resp(data=events),
                "escrows": _resp(data=escrows),
            }
        )

        mock_recon = AsyncMock(return_value={"status": "ok", "mismatches": 0})

        with (
            patch(f"{ADMIN_DB}.get_client", return_value=db),
            patch("audit.escrow_reconciler.reconcile_escrows", mock_recon),
        ):
            from api.admin import audit_summary

            result = await audit_summary(admin=_admin())

        assert result["period"] == "last_24h"
        assert result["tasks_created"] == 2
        assert result["payments_released"] == 1
        assert result["total_bounty_usd"] == 15.0
        assert len(result["open_escrows"]) == 1


# ==========================================================================
# PHANTOM / ORPHANED
# ==========================================================================


class TestGetPhantomTasks:
    """GET /api/v1/admin/tasks/phantom"""

    @pytest.mark.asyncio
    async def test_get_phantom_tasks(self):
        tasks = [
            {
                "id": "t-1",
                "title": "Phantom",
                "bounty_usd": 5.0,
                "status": "submitted",
                "created_at": "2026-03-25T00:00:00Z",
                "agent_id": "agent-1",
            },
            {
                "id": "t-2",
                "title": "Funded",
                "bounty_usd": 3.0,
                "status": "completed",
                "created_at": "2026-03-25T00:00:00Z",
                "agent_id": "agent-2",
            },
        ]
        escrows = [
            # t-2 has an escrow with "released" which IS in funded_states -> not phantom
            {"task_id": "t-2", "status": "released"},
        ]

        # get_phantom_tasks: table("tasks") then table("escrows")
        db = _client_sequence(
            [
                _resp(data=tasks),
                _resp(data=escrows),
            ]
        )

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_phantom_tasks

            result = await get_phantom_tasks(limit=100, admin=_admin())

        # t-1 has no escrow -> phantom; t-2 has funded escrow -> not phantom
        assert result["count"] == 1
        assert result["phantom_tasks"][0]["task_id"] == "t-1"


class TestGetOrphanedPayments:
    """GET /api/v1/admin/payments/orphaned"""

    @pytest.mark.asyncio
    async def test_get_orphaned_payments(self):
        submissions = [
            {
                "id": "sub-1",
                "task_id": "t-1",
                "executor_id": "w-1",
                "agent_verdict": "accepted",
                "payment_tx": None,
                "updated_at": "2026-03-25T10:00:00Z",
                "task": {
                    "id": "t-1",
                    "title": "Task",
                    "bounty_usd": 5.0,
                    "escrow_tx": None,
                    "status": "completed",
                },
                "executor": {
                    "id": "w-1",
                    "wallet_address": "0xW1",
                    "display_name": "Worker",
                },
            }
        ]
        db = _client_single(_resp(data=submissions))

        with patch(f"{ADMIN_DB}.get_supabase_client", return_value=db):
            from api.admin import get_orphaned_payments

            result = await get_orphaned_payments(limit=20, admin=_admin())

        assert result["count"] == 1
        assert result["orphaned_submissions"][0]["id"] == "sub-1"


# ==========================================================================
# AUTH ENFORCEMENT — all endpoints require admin key
# ==========================================================================


class TestAllEndpointsRequireAdminKey:
    """Verify that calling verify_admin_key without credentials raises 401."""

    @pytest.mark.asyncio
    async def test_all_endpoints_require_admin_key(self, monkeypatch):
        monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

        from fastapi import HTTPException
        from api.admin import verify_admin_key

        with pytest.raises(HTTPException) as exc_info:
            await verify_admin_key(
                authorization=None,
                x_admin_key=None,
                x_admin_actor=None,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_key_returns_403(self, monkeypatch):
        monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

        from fastapi import HTTPException
        from api.admin import verify_admin_key

        with pytest.raises(HTTPException) as exc_info:
            await verify_admin_key(
                authorization="Bearer wrongkey",
                x_admin_key=None,
                x_admin_actor=None,
            )
        assert exc_info.value.status_code == 403
