"""
Tests for the routes.py refactoring — verifies modular architecture integrity.

These tests ensure:
1. All route paths survived the split (no dropped endpoints)
2. The _RoutesModuleProxy propagates monkeypatches to sub-modules
3. All backward-compatible re-exports are accessible from routes
4. Sub-routers are independently importable
5. Cross-module helper access works correctly
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.core

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# 1. Route inventory — every endpoint path must survive the split
# ---------------------------------------------------------------------------

EXPECTED_ROUTES = {
    "/api/v1/tasks",
    "/api/v1/tasks/available",
    "/api/v1/tasks/batch",
    "/api/v1/tasks/{task_id}",
    "/api/v1/tasks/{task_id}/applications",
    "/api/v1/tasks/{task_id}/apply",
    "/api/v1/tasks/{task_id}/assign",
    "/api/v1/tasks/{task_id}/cancel",
    "/api/v1/tasks/{task_id}/payment",
    "/api/v1/tasks/{task_id}/submissions",
    "/api/v1/tasks/{task_id}/submit",
    "/api/v1/tasks/{task_id}/transactions",
    "/api/v1/submissions/{submission_id}/approve",
    "/api/v1/submissions/{submission_id}/reject",
    "/api/v1/submissions/{submission_id}/request-more-info",
    "/api/v1/config",
    "/api/v1/analytics",
    "/api/v1/public/metrics",
    "/api/v1/evidence/verify",
    "/api/v1/evidence/presign-upload",
    "/api/v1/evidence/presign-download",
    "/api/v1/health",
    "/api/v1/auth/nonce",
    "/api/v1/auth/erc8128/nonce",
    "/api/v1/auth/erc8128/info",
    "/api/v1/executors/{executor_id}/identity",
    "/api/v1/executors/{executor_id}/confirm-identity",
    "/api/v1/executors/{executor_id}/register-identity",
}


class TestRouteInventory:
    """Verify all endpoint paths are registered after the split."""

    def test_all_expected_routes_present(self):
        from api.routes import router

        actual = {r.path for r in router.routes if hasattr(r, "path")}
        missing = EXPECTED_ROUTES - actual
        assert not missing, f"Routes dropped during split: {missing}"

    def test_no_unexpected_routes_added(self):
        from api.routes import router

        actual = {r.path for r in router.routes if hasattr(r, "path")}
        extra = actual - EXPECTED_ROUTES
        assert not extra, f"Unexpected routes appeared: {extra}"

    def test_route_count_stable(self):
        from api.routes import router

        actual = {r.path for r in router.routes if hasattr(r, "path")}
        assert len(actual) == len(EXPECTED_ROUTES)


# ---------------------------------------------------------------------------
# 2. Module proxy — monkeypatch propagation to sub-modules
# ---------------------------------------------------------------------------


class TestModuleProxy:
    """Verify _RoutesModuleProxy propagates setattr to sub-modules."""

    def test_routes_module_is_proxy(self):
        import api.routes as routes

        assert type(routes).__name__ == "_RoutesModuleProxy"

    def test_db_patch_propagates_to_helpers(self):
        """When tests do `monkeypatch.setattr(routes, 'db', mock)`,
        the mock must also appear in _helpers.db where the actual
        code runs."""
        import api.routes as routes
        from api.routers import _helpers

        original_db = _helpers.db
        mock_db = MagicMock(name="mock_db")

        try:
            routes.db = mock_db
            assert _helpers.db is mock_db, (
                "db patch on routes did not propagate to _helpers"
            )
        finally:
            routes.db = original_db

    def test_db_patch_propagates_to_tasks(self):
        import api.routes as routes
        from api.routers import tasks

        original_db = tasks.db
        mock_db = MagicMock(name="mock_db")

        try:
            routes.db = mock_db
            assert tasks.db is mock_db, "db patch on routes did not propagate to tasks"
        finally:
            routes.db = original_db

    def test_db_patch_propagates_to_submissions(self):
        import api.routes as routes
        from api.routers import submissions

        original_db = submissions.db
        mock_db = MagicMock(name="mock_db")

        try:
            routes.db = mock_db
            assert submissions.db is mock_db
        finally:
            routes.db = original_db

    def test_db_patch_propagates_to_workers(self):
        import api.routes as routes
        from api.routers import workers

        original_db = workers.db
        mock_db = MagicMock(name="mock_db")

        try:
            routes.db = mock_db
            assert workers.db is mock_db
        finally:
            routes.db = original_db

    def test_nonexistent_attr_does_not_crash(self):
        """Setting an attribute that doesn't exist in sub-modules
        should not raise."""
        import api.routes as routes

        routes._test_sentinel_xyz = 42
        assert routes._test_sentinel_xyz == 42
        del routes._test_sentinel_xyz


# ---------------------------------------------------------------------------
# 3. Backward-compatible re-exports
# ---------------------------------------------------------------------------

# These are the symbols that test files import from api.routes
REQUIRED_REEXPORTS = [
    # Database
    "db",
    # Router
    "router",
    # Models (from models.py)
    "TaskCategory",
    "EvidenceType",
    # Auth
    "verify_agent_owns_submission",
    # Pydantic models
    "ApprovalRequest",
    "CreateTaskRequest",
    "RejectionRequest",
    "WorkerApplicationRequest",
    "WorkerSubmissionRequest",
    # Endpoint functions
    "cancel_task",
    "create_task",
    "get_public_platform_metrics",
    "get_task_payment",
    "get_task_transactions",
    "approve_submission",
    "reject_submission",
    "apply_to_task",
    "submit_work",
    # Helpers and constants
    "X402_AVAILABLE",
    "get_payment_dispatcher",
    "get_sdk",
    "_build_explorer_url",
    "_is_payment_finalized",
    "_resolve_task_payment_header",
    "_ws1_auto_register_worker",
    "_ws2_auto_rate_agent",
    "_execute_post_approval_side_effects",
    "_is_submission_ready_for_instant_payout",
    "_settle_submission_payment",
    "_auto_approve_submission",
]


class TestReExports:
    """Every symbol that tests import from api.routes must exist."""

    @pytest.mark.parametrize("symbol", REQUIRED_REEXPORTS)
    def test_symbol_accessible(self, symbol):
        import api.routes as routes

        assert hasattr(routes, symbol), (
            f"routes.{symbol} is missing — tests that import it will break"
        )

    def test_all_reexports_are_not_none(self):
        import api.routes as routes

        for symbol in REQUIRED_REEXPORTS:
            val = getattr(routes, symbol, None)
            assert val is not None, f"routes.{symbol} is None"


# ---------------------------------------------------------------------------
# 4. Sub-router independence — each module imports cleanly
# ---------------------------------------------------------------------------


class TestSubRouterImports:
    """Each sub-router module must be independently importable."""

    def test_import_helpers(self):
        from api.routers import _helpers

        assert hasattr(_helpers, "get_payment_dispatcher")

    def test_import_models(self):
        from api.routers import _models

        assert hasattr(_models, "CreateTaskRequest")

    def test_import_tasks(self):
        from api.routers import tasks

        assert hasattr(tasks, "router")
        assert hasattr(tasks, "create_task")

    def test_import_submissions(self):
        from api.routers import submissions

        assert hasattr(submissions, "router")
        assert hasattr(submissions, "approve_submission")

    def test_import_workers(self):
        from api.routers import workers

        assert hasattr(workers, "router")
        assert hasattr(workers, "apply_to_task")

    def test_import_misc(self):
        from api.routers import misc

        assert hasattr(misc, "router")


# ---------------------------------------------------------------------------
# 5. Sub-routers have correct prefixes and tags
# ---------------------------------------------------------------------------


class TestSubRouterConfig:
    """Verify each sub-router is configured correctly."""

    def test_tasks_router_has_routes(self):
        from api.routers.tasks import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/tasks" in paths
        assert "/api/v1/tasks/{task_id}" in paths

    def test_submissions_router_has_routes(self):
        from api.routers.submissions import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/submissions/{submission_id}/approve" in paths

    def test_workers_router_has_routes(self):
        from api.routers.workers import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/tasks/{task_id}/apply" in paths
        assert "/api/v1/tasks/{task_id}/submit" in paths

    def test_misc_router_has_routes(self):
        from api.routers.misc import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/health" in paths
        assert "/api/v1/auth/nonce" in paths

    def test_tasks_router_has_config_and_analytics(self):
        """Config, analytics, and metrics live in the tasks router."""
        from api.routers.tasks import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/config" in paths
        assert "/api/v1/analytics" in paths
        assert "/api/v1/public/metrics" in paths
