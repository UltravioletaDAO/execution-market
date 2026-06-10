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
    "/api/v1/workers/tasks/{task_id}/my-submission",
    "/api/v1/workers/register",
    "/api/v1/payments/events",
    "/api/v1/payments/balance/{address}",
    "/api/v1/webhooks/",
    "/api/v1/webhooks/{webhook_id}",
    "/api/v1/webhooks/{webhook_id}/rotate-secret",
    "/api/v1/webhooks/{webhook_id}/test",
    "/api/v1/identity/lookup",
    "/api/v1/identity/sync",
    "/api/v1/identity/verify-challenge",
    "/api/v1/tasks/{task_id}/chat-history",
    # Relay chain endpoints (Phase 6)
    "/api/v1/relay-chains",
    "/api/v1/relay-chains/{chain_id}",
    "/api/v1/relay-chains/{chain_id}/legs/{leg_number}/assign",
    "/api/v1/relay-chains/{chain_id}/legs/{leg_number}/handoff",
    # Agent visibility endpoints
    "/api/v1/agent-info",
    "/api/v1/skills",
    # Mobile config
    "/api/v1/config/mobile",
    # Audit grid
    "/api/v1/tasks/audit-grid",
    # User blocking
    "/api/v1/users/block",
    "/api/v1/users/block/{blocked_user_id}",
    "/api/v1/users/blocked",
    # Reports / moderation
    "/api/v1/reports",
    "/api/v1/reports/{report_id}",
    # Account management
    "/api/v1/account",
    "/api/v1/account/export",
    "/api/v1/account/wallet",
    "/api/v1/account/link-wallet",
    # Legal
    "/api/v1/legal/privacy",
    "/api/v1/legal/terms",
    # Worker submission detail (Phase B verification polling)
    "/api/v1/submissions/{submission_id}",
    # Worker social links
    "/api/v1/workers/social-links",
    # World ID 4.0 verification
    "/api/v1/world-id/rp-signature",
    "/api/v1/world-id/verify",
    "/api/v1/workers/world-status",
    # ENS integration
    "/api/v1/ens/resolve/{name_or_address}",
    "/api/v1/ens/link",
    "/api/v1/ens/records/{name}",
    "/api/v1/ens/subname/{subname}",
    "/api/v1/ens/claim-subname",
    # Ring 2 Arbiter — dispute resolution (Phase 5)
    "/api/v1/disputes",
    "/api/v1/disputes/{dispute_id}",
    "/api/v1/disputes/available",
    "/api/v1/disputes/{dispute_id}/resolve",
    # Ring 2 Arbiter — public Arbiter-as-a-Service (Phase 5)
    "/api/v1/arbiter/verify",
    "/api/v1/arbiter/status",
    # Escrow state endpoint
    "/api/v1/tasks/{task_id}/escrow",
    # Version endpoints
    "/api/v1/version",
    "/api/v1/version/all",
    # Proof Wall showcase
    "/api/v1/showcase/evidence",
}


# Feature-gated routers register only when their env flag is on
# (EM_MOONPAY_ENABLED, EM_PAYSHELL_ENABLED, EM_CLAWKEY_ENABLED, EM_VERYAI_ENABLED).
# Whether they appear in `api.routes.router` depends on which flags were set
# when that module was first imported — global module state, so it's
# order-dependent under the full suite. The inventory tests exclude them by
# prefix so they stay deterministic regardless of flag state.
GATED_PREFIXES = (
    "/api/v1/moonpay/",
    "/api/v1/taximetro/",
    "/api/v1/clawkey/",
    "/api/v1/veryai/",
)


def _ungated(paths: set) -> set:
    return {p for p in paths if not any(p.startswith(g) for g in GATED_PREFIXES)}


class TestRouteInventory:
    """Verify all endpoint paths are registered after the split."""

    def test_all_expected_routes_present(self):
        from api.routes import router

        actual = {r.path for r in router.routes if hasattr(r, "path")}
        missing = EXPECTED_ROUTES - actual
        assert not missing, f"Routes dropped during split: {missing}"

    def test_no_unexpected_routes_added(self):
        from api.routes import router

        actual = _ungated({r.path for r in router.routes if hasattr(r, "path")})
        extra = actual - EXPECTED_ROUTES
        assert not extra, f"Unexpected routes appeared: {extra}"

    def test_route_count_stable(self):
        from api.routes import router

        actual = _ungated({r.path for r in router.routes if hasattr(r, "path")})
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


# ---------------------------------------------------------------------------
# 6. Gated router inventory (Task 5.5 / F-16)
# ---------------------------------------------------------------------------
#
# The ungated inventory above excludes feature-gated prefixes (MoonPay,
# Taximetro, ClawKey, VeryAI) because whether they appear in `api.routes.router`
# depends on env-flag state at the module's FIRST import — global, order-
# dependent state under the full suite. Excluding them keeps the ungated tests
# deterministic, but it also means a deleted/renamed gated route slips through
# CI. These tests close that gap WITHOUT an `importlib.reload` (a reload is a
# global, non-reverted mutation that has leaked across the suite and broken CI).
#
# Strategy: import `api.routes`, take the SAME gated sub-router OBJECTS it wires
# in (`moonpay_router`, `clawkey_router`), and rebuild a throwaway aggregate with
# the flags ON to assert the gated paths surface. This tests the real router
# objects (so a path rename/deletion fails) and the include contract, while
# touching only a local APIRouter — nothing global. Env flags are still toggled
# with monkeypatch (auto-reverted) to pin intent.

# Gated paths that MUST appear when each flag is ON. Renaming/removing any of
# these in the sub-router fails this test (the drift the audit's F-16 flagged).
EXPECTED_MOONPAY_ROUTES = {
    "/api/v1/moonpay/sign-url",
    "/api/v1/moonpay/session",
    "/api/v1/moonpay/webhook",
    "/api/v1/moonpay/health",
}
EXPECTED_CLAWKEY_ROUTES = {
    "/api/v1/clawkey/status/{executor_id}",
    "/api/v1/clawkey/refresh/{executor_id}",
}


class TestGatedRouterInventory:
    """When the feature flags are ON, the gated MoonPay/ClawKey routes must be
    reachable through the api.routes wiring (router-drift guard)."""

    def test_moonpay_and_clawkey_routes_present_when_enabled(self, monkeypatch):
        from fastapi import APIRouter
        import api.routes as routes

        monkeypatch.setenv("EM_MOONPAY_ENABLED", "true")
        monkeypatch.setenv("EM_CLAWKEY_ENABLED", "true")

        # Rebuild the aggregate from the REAL gated sub-router objects that
        # api.routes imported. Mirrors the include logic in api/routes.py but
        # against a local router so no global module state is mutated.
        aggregate = APIRouter()
        aggregate.include_router(routes.moonpay_router)
        aggregate.include_router(routes.clawkey_router)

        paths = {r.path for r in aggregate.routes if hasattr(r, "path")}

        missing_moonpay = EXPECTED_MOONPAY_ROUTES - paths
        assert not missing_moonpay, (
            f"MoonPay gated routes missing (router drift): {missing_moonpay}"
        )
        missing_clawkey = EXPECTED_CLAWKEY_ROUTES - paths
        assert not missing_clawkey, (
            f"ClawKey gated routes missing (router drift): {missing_clawkey}"
        )

    def test_gated_routes_excluded_from_ungated_inventory(self):
        """Sanity: the gated prefixes are NOT counted in the ungated inventory,
        so the deterministic inventory tests above stay flag-independent."""
        for path in EXPECTED_MOONPAY_ROUTES | EXPECTED_CLAWKEY_ROUTES:
            assert any(path.startswith(g) for g in GATED_PREFIXES), (
                f"{path} should match a GATED_PREFIXES entry"
            )
            assert path not in EXPECTED_ROUTES, (
                f"{path} is gated and must not be in the ungated EXPECTED_ROUTES"
            )
