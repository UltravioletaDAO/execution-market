"""
Phase 5 tests — Dispute resolution endpoints + Arbiter-as-a-Service.

Covers:
- disputes.py: list/detail/resolve endpoints with auth scoping
- arbiter_public.py: AaaS /verify + /status endpoints
- ResolveDisputeInput model validation
- Rate limiter sliding window logic

Uses sys.modules stubs for api.routers._helpers / events.bus /
payment_dispatcher / supabase_client to isolate arbiter tests from
unrelated web3 imports.

Run:
    pytest tests/test_arbiter_phase5.py
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.arbiter


# ---------------------------------------------------------------------------
# sys.modules stubs (reused from test_arbiter_integration.py pattern)
# ---------------------------------------------------------------------------


def _install_stubs():
    # Use setdefault so we play nicely with test_arbiter_integration.py
    # which also installs stubs for api.routers._helpers. If integration
    # already set these up, we reuse them (their mocks are sufficient).
    # We only ADD disputes and arbiter_public to sys.modules by loading
    # them via importlib.util (additive).
    import importlib.util
    from pathlib import Path

    # _helpers: reuse if present, else create
    if "api.routers._helpers" in sys.modules:
        fake_helpers = sys.modules["api.routers._helpers"]
    else:
        fake_helpers = types.ModuleType("api.routers._helpers")
        fake_helpers._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xRES"}
        )
        fake_helpers.dispatch_webhook = AsyncMock()
        sys.modules["api.routers._helpers"] = fake_helpers

    # _pagination: reuse if present, else create a no-op stub. disputes.py
    # imports set_pagination_headers from here (Task 6.4); tests don't care
    # about the Link/X-Total-Count headers so a do-nothing callable is fine.
    if "api.routers._pagination" not in sys.modules:
        fake_pagination = types.ModuleType("api.routers._pagination")
        fake_pagination.set_pagination_headers = lambda *args, **kwargs: None
        fake_pagination.MAX_PAGE_SIZE = 100
        sys.modules["api.routers._pagination"] = fake_pagination

    # api package: reuse if present, else create
    if "api" in sys.modules:
        fake_api = sys.modules["api"]
        if not hasattr(fake_api, "__path__"):
            fake_api.__path__ = []
    else:
        fake_api = types.ModuleType("api")
        fake_api.__path__ = []
        sys.modules["api"] = fake_api

    # api.routers package: reuse if present, else create
    if "api.routers" in sys.modules:
        fake_routers = sys.modules["api.routers"]
        if not hasattr(fake_routers, "__path__"):
            fake_routers.__path__ = []
    else:
        fake_routers = types.ModuleType("api.routers")
        fake_routers.__path__ = []
        sys.modules["api.routers"] = fake_routers
    fake_routers._helpers = fake_helpers
    fake_api.routers = fake_routers

    # Stub api.auth with just AgentAuth (used by disputes.py + arbiter_public.py)
    fake_auth = types.ModuleType("api.auth")

    class _AgentAuth:
        def __init__(
            self,
            agent_id: str = "test",
            wallet_address: str = None,
            auth_method: str = "mcp_tool",
            tier: str = "free",
            chain_id: int = None,
            organization_id: str = None,
            erc8004_registered: bool = False,
            erc8004_agent_id: int = None,
        ):
            self.agent_id = agent_id
            self.wallet_address = wallet_address
            self.auth_method = auth_method
            self.tier = tier
            self.chain_id = chain_id
            self.organization_id = organization_id
            self.erc8004_registered = erc8004_registered
            self.erc8004_agent_id = erc8004_agent_id

    async def _verify_agent_auth():
        return _AgentAuth()

    fake_auth.AgentAuth = _AgentAuth
    # Provide all three entry points so routers using the post-GR-0.1
    # verify_agent_auth_read / verify_agent_auth_write split still import
    # cleanly against this stub module. The legacy alias is kept for any
    # remaining call sites.
    fake_auth.verify_agent_auth = _verify_agent_auth
    fake_auth.verify_agent_auth_read = _verify_agent_auth
    fake_auth.verify_agent_auth_write = _verify_agent_auth
    # Only install if not already present (don't clobber integration.py's stub)
    sys.modules.setdefault("api.auth", fake_auth)

    # Load disputes.py and arbiter_public.py by file path -- bypasses
    # the real api package init entirely. Always load these since
    # integration.py doesn't set them up.
    repo_root = Path(__file__).resolve().parent.parent  # mcp_server/
    routers_dir = repo_root / "api" / "routers"

    def _load_router(module_name: str, file_path: Path):
        if module_name in sys.modules:
            return sys.modules[module_name]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    _load_router("api.routers.disputes", routers_dir / "disputes.py")
    _load_router("api.routers.arbiter_public", routers_dir / "arbiter_public.py")

    # Install events.bus stub (setdefault so we don't clobber integration)
    if "events.bus" not in sys.modules:
        fake_event_bus_instance_local = MagicMock()
        fake_event_bus_instance_local.publish = AsyncMock()

        class _FakeEventBus:
            pass

        fake_bus_module = types.ModuleType("events.bus")
        fake_bus_module.get_event_bus = lambda: fake_event_bus_instance_local
        fake_bus_module.EventBus = _FakeEventBus
        sys.modules["events.bus"] = fake_bus_module
        fake_event_bus = fake_event_bus_instance_local
    else:
        fake_event_bus = sys.modules["events.bus"].get_event_bus()

    # Install payment dispatcher stub. If another test file (integration.py)
    # already installed a stub with get_dispatcher, DO NOT overwrite it --
    # reuse their stub so their _FAKE_DISPATCHER references stay valid.
    existing_pd = sys.modules.get("integrations.x402.payment_dispatcher")
    if existing_pd is not None and hasattr(existing_pd, "get_dispatcher"):
        # Another test file already stubbed this -- reuse their dispatcher
        fake_dispatcher = existing_pd.get_dispatcher()
    else:
        # First stub install (we run alone or before integration.py)
        fake_dispatcher_local = MagicMock()
        fake_dispatcher_local.refund_trustless_escrow = AsyncMock(
            return_value={"success": True, "tx_hash": "0xREF"}
        )
        fake_pd_module = types.ModuleType("integrations.x402.payment_dispatcher")
        fake_pd_module.get_dispatcher = lambda: fake_dispatcher_local
        fake_pd_module.get_payment_dispatcher = lambda: fake_dispatcher_local
        sys.modules["integrations.x402.payment_dispatcher"] = fake_pd_module
        fake_dispatcher = fake_dispatcher_local

    return fake_helpers, fake_event_bus, fake_dispatcher


# Module-level placeholders. Populated by autouse fixture below.
_FAKE_HELPERS = None
_FAKE_EVENT_BUS = None
_FAKE_DISPATCHER = None


# Supabase client stub
def _make_fake_supabase_client(disputes=None, executors=None, tasks=None):
    disputes = disputes or []
    executors = executors or []
    tasks = tasks or []

    def mk_table(name):
        table = MagicMock()
        rows_by_table = {
            "disputes": disputes,
            "executors": executors,
            "tasks": tasks,
            "submissions": [],
            "payments": [],
        }
        rows = rows_by_table.get(name, [])

        # For select().execute() default
        resp = MagicMock(data=list(rows), count=len(rows))

        # Build a chain that returns resp regardless of chaining
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.not_.is_.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = resp

        table.select.return_value = chain
        table.update.return_value = chain
        table.insert.return_value = chain
        table.upsert.return_value = chain
        return table

    client = MagicMock()
    client.table.side_effect = mk_table
    return client


# Supabase stub is installed by the autouse module-scope fixture below.
fake_db = None


_STUB_MODULES_P5 = [
    "api",
    "api.routers",
    "api.routers._helpers",
    "api.routers._pagination",
    "api.routers.disputes",
    "api.routers.arbiter_public",
    "api.auth",
    "events.bus",
    "integrations.x402.payment_dispatcher",
    "supabase_client",
]


@pytest.fixture(scope="module", autouse=True)
def _arbiter_phase5_stubs_module_scope():
    """Install phase5 stubs scoped to this module. Save + restore sys.modules
    to prevent leakage to other test files.
    """
    global _FAKE_HELPERS, _FAKE_EVENT_BUS, _FAKE_DISPATCHER, fake_db

    saved_modules = {}
    saved_attrs = {}

    for name in _STUB_MODULES_P5:
        saved_modules[name] = sys.modules.get(name)

    def _save_attr(mod_name, attr_name):
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, attr_name):
            saved_attrs[(mod_name, attr_name)] = getattr(mod, attr_name)

    _save_attr("api.routers._helpers", "_settle_submission_payment")
    _save_attr("api.routers._helpers", "dispatch_webhook")
    _save_attr("events.bus", "get_event_bus")
    _save_attr("events.bus", "EventBus")
    _save_attr("integrations.x402.payment_dispatcher", "get_dispatcher")
    _save_attr("integrations.x402.payment_dispatcher", "get_payment_dispatcher")
    _save_attr("supabase_client", "get_client")

    # Install stubs (runs _install_stubs which loads disputes.py + arbiter_public.py)
    _FAKE_HELPERS, _FAKE_EVENT_BUS, _FAKE_DISPATCHER = _install_stubs()

    # Install supabase stub for phase5 tests
    existing_db_p5 = sys.modules.get("supabase_client")
    _is_integration_stub = (
        existing_db_p5 is not None
        and getattr(existing_db_p5, "_arbiter_stub", None) == "integration"
    )

    if _is_integration_stub:
        fake_db = existing_db_p5
    elif existing_db_p5 is not None:
        existing_db_p5.get_client = lambda: _make_fake_supabase_client()
        existing_db_p5._arbiter_stub = "phase5"
        fake_db = existing_db_p5
    else:
        fake_db_local = types.ModuleType("supabase_client")
        fake_db_local.get_client = lambda: _make_fake_supabase_client()
        fake_db_local._arbiter_stub = "phase5"
        sys.modules["supabase_client"] = fake_db_local
        fake_db = fake_db_local

    yield

    # Teardown
    for (mod_name, attr_name), original in saved_attrs.items():
        mod = sys.modules.get(mod_name)
        if mod is not None:
            setattr(mod, attr_name, original)

    for name, original_mod in saved_modules.items():
        if original_mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original_mod

    sb = sys.modules.get("supabase_client")
    if sb is not None and hasattr(sb, "_arbiter_stub"):
        try:
            delattr(sb, "_arbiter_stub")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tests: ResolveDisputeInput (MCP model)
# ---------------------------------------------------------------------------


class TestResolveDisputeInput:
    def test_valid_release(self):
        from models import ResolveDisputeInput

        inp = ResolveDisputeInput(
            dispute_id="12345678-1234-1234-1234-123456789012",
            verdict="release",
            reason="Evidence is clearly valid",
        )
        assert inp.verdict == "release"
        assert inp.split_pct is None

    def test_valid_refund(self):
        from models import ResolveDisputeInput

        inp = ResolveDisputeInput(
            dispute_id="12345678-1234-1234-1234-123456789012",
            verdict="refund",
            reason="Worker submitted stock photo",
        )
        assert inp.verdict == "refund"

    def test_valid_split(self):
        from models import ResolveDisputeInput

        inp = ResolveDisputeInput(
            dispute_id="12345678-1234-1234-1234-123456789012",
            verdict="split",
            reason="Partial completion, 60% done",
            split_pct=40.0,
        )
        assert inp.verdict == "split"
        assert inp.split_pct == 40.0

    def test_invalid_verdict_rejected(self):
        from models import ResolveDisputeInput

        with pytest.raises(Exception):
            ResolveDisputeInput(
                dispute_id="12345678-1234-1234-1234-123456789012",
                verdict="bogus",
                reason="test",
            )

    def test_short_reason_rejected(self):
        from models import ResolveDisputeInput

        with pytest.raises(Exception):
            ResolveDisputeInput(
                dispute_id="12345678-1234-1234-1234-123456789012",
                verdict="release",
                reason="no",  # < 5 chars
            )

    def test_short_uuid_rejected(self):
        from models import ResolveDisputeInput

        with pytest.raises(Exception):
            ResolveDisputeInput(
                dispute_id="too-short",
                verdict="release",
                reason="valid reason",
            )

    def test_split_pct_bounds(self):
        from models import ResolveDisputeInput

        # 0 and 100 are valid
        ResolveDisputeInput(
            dispute_id="12345678-1234-1234-1234-123456789012",
            verdict="split",
            reason="valid",
            split_pct=0,
        )
        ResolveDisputeInput(
            dispute_id="12345678-1234-1234-1234-123456789012",
            verdict="split",
            reason="valid",
            split_pct=100,
        )
        # > 100 rejected
        with pytest.raises(Exception):
            ResolveDisputeInput(
                dispute_id="12345678-1234-1234-1234-123456789012",
                verdict="split",
                reason="valid",
                split_pct=150,
            )


# ---------------------------------------------------------------------------
# Tests: Disputes router helpers (pure logic, no async/DB)
# ---------------------------------------------------------------------------


class TestDisputesRouterHelpers:
    """Tests the pure helper functions inside api.routers.disputes."""

    def test_row_to_summary_minimal(self):
        from api.routers.disputes import _row_to_summary

        row = {
            "id": "d-1",
            "task_id": "t-1",
            "agent_id": "0xAGENT",
            "reason": "poor_quality",
            "description": "Low-quality photo",
            "status": "open",
            "priority": 7,
            "created_at": "2026-04-08T12:00:00Z",
        }
        s = _row_to_summary(row)
        assert s.id == "d-1"
        assert s.priority == 7
        assert s.escalation_tier == 2  # default
        assert s.disputed_amount_usdc is None
        assert s.winner is None

    def test_row_to_summary_with_arbiter_fields(self):
        from api.routers.disputes import _row_to_summary

        row = {
            "id": "d-2",
            "task_id": "t-2",
            "submission_id": "s-2",
            "agent_id": "0xAGENT",
            "executor_id": "e-2",
            "reason": "fake_evidence",
            "description": "Ring disagreement",
            "status": "in_arbitration",
            "priority": 9,
            "escalation_tier": 2,
            "disputed_amount_usdc": 5.00,
            "created_at": "2026-04-08T12:00:00Z",
            "winner": None,
        }
        s = _row_to_summary(row)
        assert s.escalation_tier == 2
        assert s.disputed_amount_usdc == 5.00
        assert s.submission_id == "s-2"

    def test_row_to_detail_includes_arbiter_snapshot(self):
        from api.routers.disputes import _row_to_detail

        row = {
            "id": "d-3",
            "task_id": "t-3",
            "agent_id": "0xagent",
            "reason": "poor_quality",
            "description": "test",
            "status": "open",
            "priority": 5,
            "created_at": "2026-04-08T12:00:00Z",
            "arbiter_verdict_data": {
                "decision": "inconclusive",
                "aggregate_score": 0.55,
                "ring_scores": [],
            },
        }
        d = _row_to_detail(row)
        assert d.arbiter_verdict_data is not None
        assert d.arbiter_verdict_data["decision"] == "inconclusive"


# ---------------------------------------------------------------------------
# Tests: Arbiter-as-a-Service rate limiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def setup_method(self):
        # Clear buckets between tests
        from api.routers.arbiter_public import _rate_limit_buckets

        _rate_limit_buckets.clear()

    def test_under_limit_allows_request(self):
        from api.routers.arbiter_public import _check_rate_limit

        # 99 requests are fine
        for _ in range(99):
            _check_rate_limit("caller-a")

    def test_over_limit_raises_429(self):
        from api.routers.arbiter_public import _check_rate_limit

        for _ in range(100):
            _check_rate_limit("caller-b")

        with pytest.raises(Exception) as exc_info:
            _check_rate_limit("caller-b")
        # HTTPException or whatever — just ensure it blocks
        assert "Rate limit" in str(exc_info.value) or "429" in str(exc_info.value)

    def test_different_callers_have_separate_buckets(self):
        from api.routers.arbiter_public import _check_rate_limit

        for _ in range(100):
            _check_rate_limit("caller-c")
        # A different caller should NOT be blocked
        _check_rate_limit("caller-d")

    def test_old_entries_are_dropped(self):
        from api.routers.arbiter_public import _check_rate_limit, _rate_limit_buckets

        # Seed bucket with very old timestamps
        _rate_limit_buckets["caller-e"] = [0.0] * 100  # 100 ancient entries

        # Should succeed because old entries drop past the 60s window
        _check_rate_limit("caller-e")
        assert len(_rate_limit_buckets["caller-e"]) == 1


# ---------------------------------------------------------------------------
# Tests: Arbiter-as-a-Service request/response models
# ---------------------------------------------------------------------------


class TestAaasRequestModels:
    def test_verify_request_minimal(self):
        from api.routers.arbiter_public import ArbiterVerifyRequest, TaskSchema

        req = ArbiterVerifyRequest(
            evidence={"photo": "url"},
            task_schema=TaskSchema(category="physical_presence"),
            bounty_usd=0.50,
        )
        assert req.bounty_usd == 0.50
        assert req.photint_score is None

    def test_verify_request_with_photint_score(self):
        from api.routers.arbiter_public import ArbiterVerifyRequest, TaskSchema

        req = ArbiterVerifyRequest(
            evidence={"photo": "url"},
            task_schema=TaskSchema(category="physical_presence"),
            bounty_usd=2.0,
            photint_score=0.88,
            photint_confidence=0.82,
        )
        assert req.photint_score == 0.88

    def test_verify_request_rejects_out_of_range_score(self):
        from api.routers.arbiter_public import ArbiterVerifyRequest, TaskSchema

        with pytest.raises(Exception):
            ArbiterVerifyRequest(
                evidence={},
                task_schema=TaskSchema(category="general"),
                bounty_usd=1.0,
                photint_score=1.5,  # > 1.0
            )

    def test_verify_request_rejects_negative_bounty(self):
        from api.routers.arbiter_public import ArbiterVerifyRequest, TaskSchema

        with pytest.raises(Exception):
            ArbiterVerifyRequest(
                evidence={},
                task_schema=TaskSchema(category="general"),
                bounty_usd=-5.0,
            )


# ---------------------------------------------------------------------------
# Tests: AaaS endpoint end-to-end (with mocked arbiter)
# ---------------------------------------------------------------------------


class TestAaasEndpoint:
    @pytest.fixture(autouse=True)
    def _enable_aaas(self, monkeypatch):
        # Phase 0 GR-0.2: AaaS defaults disabled. Flip the env flag on
        # for this class so we exercise the underlying endpoint logic.
        monkeypatch.setenv("EM_AAAS_ENABLED", "true")

    @pytest.mark.asyncio
    async def test_verify_pass_path(self):
        """End-to-end: arbiter returns PASS -> endpoint maps to response."""
        from api.routers.arbiter_public import (
            ArbiterVerifyRequest,
            TaskSchema,
            verify_evidence,
        )
        from api.auth import AgentAuth

        auth = AgentAuth(agent_id="test-caller", wallet_address="0xtest")
        req = ArbiterVerifyRequest(
            evidence={"photo": "url", "gps": {"lat": 1, "lng": 2}},
            task_schema=TaskSchema(category="physical_presence"),
            bounty_usd=0.50,
            photint_score=0.92,
            photint_confidence=0.85,
        )

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=True),
        ):
            response = await verify_evidence(req, auth)

        assert response.verdict == "pass"
        # physical_presence is in CATEGORIES_MIN_STANDARD: promoted to STANDARD
        # even on sub-$1 bounty (Ring 2 providers fail gracefully -> cheap fallback)
        assert response.tier in ("cheap", "standard")
        assert response.evidence_hash.startswith("0x")
        assert len(response.evidence_hash) == 66

    @pytest.mark.asyncio
    async def test_verify_fail_path(self):
        from api.routers.arbiter_public import (
            ArbiterVerifyRequest,
            TaskSchema,
            verify_evidence,
        )
        from api.auth import AgentAuth

        auth = AgentAuth(agent_id="test-caller2", wallet_address="0xtest2")
        req = ArbiterVerifyRequest(
            evidence={"photo": "url"},
            task_schema=TaskSchema(category="physical_presence"),
            bounty_usd=0.50,
            photint_score=0.15,  # Below fail threshold
        )

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=True),
        ):
            response = await verify_evidence(req, auth)

        assert response.verdict == "fail"

    @pytest.mark.asyncio
    async def test_verify_master_switch_off_returns_503(self):
        from api.routers.arbiter_public import (
            ArbiterVerifyRequest,
            TaskSchema,
            verify_evidence,
        )
        from api.auth import AgentAuth

        auth = AgentAuth(agent_id="t3", wallet_address="0x3")
        req = ArbiterVerifyRequest(
            evidence={},
            task_schema=TaskSchema(category="general"),
            bounty_usd=0.10,
            photint_score=0.9,
        )

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=False),
        ):
            with pytest.raises(Exception) as exc_info:
                await verify_evidence(req, auth)

        assert "not enabled" in str(exc_info.value).lower() or "503" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_verify_without_photint_returns_400(self):
        """Arbiter with no photint_score in CHEAP tier -> SKIPPED -> 400."""
        from api.routers.arbiter_public import (
            ArbiterVerifyRequest,
            TaskSchema,
            verify_evidence,
        )
        from api.auth import AgentAuth

        auth = AgentAuth(agent_id="t4", wallet_address="0x4")
        req = ArbiterVerifyRequest(
            evidence={"raw": "data"},
            task_schema=TaskSchema(category="general"),
            bounty_usd=0.10,
            # No photint_score
        )

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=True),
        ):
            with pytest.raises(Exception) as exc_info:
                await verify_evidence(req, auth)

        assert "photint_score" in str(exc_info.value).lower() or "400" in str(
            exc_info.value
        )


# ---------------------------------------------------------------------------
# Tests: AaaS /status endpoint
# ---------------------------------------------------------------------------


class TestAaasStatus:
    @pytest.fixture(autouse=True)
    def _enable_aaas(self, monkeypatch):
        # Phase 0 GR-0.2: AaaS defaults disabled. Enable for this class
        # so the /status endpoint doesn't 503 on the env flag check
        # before we can exercise the PlatformConfig master switch.
        monkeypatch.setenv("EM_AAAS_ENABLED", "true")

    @pytest.mark.asyncio
    async def test_status_returns_tiers_and_categories(self):
        from api.routers.arbiter_public import arbiter_status

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=True),
        ):
            status = await arbiter_status()

        assert isinstance(status.supported_categories, list)
        assert len(status.supported_categories) >= 20
        assert "physical_presence" in status.supported_categories
        assert status.tier_thresholds["cheap_max_usd"] == 1.0
        assert status.tier_thresholds["standard_max_usd"] == 10.0
        assert status.cost_model["rate_limit_per_minute"] == 100

    @pytest.mark.asyncio
    async def test_status_reflects_master_switch(self):
        from api.routers.arbiter_public import arbiter_status

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=False),
        ):
            status = await arbiter_status()

        assert status.enabled is False
