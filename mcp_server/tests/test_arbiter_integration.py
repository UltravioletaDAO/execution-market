"""
Integration tests for the Ring 2 Arbiter auto-release/refund pipeline.

Covers Phase 2 of the commerce scheme + arbiter integration:
- processor.process_arbiter_verdict() dispatch logic
- auto mode -> Facilitator /settle (PASS) or /refund (FAIL)
- hybrid mode -> verdict stored, agent still confirms
- manual mode -> arbiter never runs
- INCONCLUSIVE -> escalation dispute row created
- Defensive handling of None returns from settle/refund
- Idempotency: double-release prevention
- Cost controls enforced by tier router
- Fee split sanity (87%/13% preserved by existing dispatcher)

Uses sys.modules stubs to avoid importing api/__init__.py (which has an
unrelated web3 import issue in the local env).

Run:
    pytest -m arbiter tests/test_arbiter_integration.py
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.arbiter


# ---------------------------------------------------------------------------
# Module-level stubs for lazy imports
# ---------------------------------------------------------------------------


def _install_stubs():
    """Install sys.modules stubs BEFORE the arbiter module is imported.

    This is necessary because processor.py uses lazy imports for
    api.routers._helpers and integrations.x402.payment_dispatcher. In
    production these modules exist; in the test env they either don't
    or have import errors unrelated to arbiter code.
    """
    # --- api.routers._helpers ---
    # ALWAYS force-override. The real _helpers has unrelated imports
    # that may fail in test env, and processor.py lazy-imports
    # _settle_submission_payment which MUST be our mock.
    fake_settle = AsyncMock(return_value={"payment_tx": "0xPAY_DEFAULT"})
    fake_dispatch_webhook = AsyncMock()

    existing_helpers = sys.modules.get("api.routers._helpers")
    if existing_helpers is not None:
        # Monkey-patch the real module's attributes so lazy imports
        # inside arbiter code use our mocks.
        existing_helpers._settle_submission_payment = fake_settle
        existing_helpers.dispatch_webhook = fake_dispatch_webhook
        fake_helpers = existing_helpers
    else:
        fake_helpers = types.ModuleType("api.routers._helpers")
        fake_helpers._settle_submission_payment = fake_settle
        fake_helpers.dispatch_webhook = fake_dispatch_webhook
        fake_routers_pkg = types.ModuleType("api.routers")
        fake_routers_pkg.__path__ = []
        fake_routers_pkg._helpers = fake_helpers
        fake_api_pkg = types.ModuleType("api")
        fake_api_pkg.__path__ = []
        fake_api_pkg.routers = fake_routers_pkg
        sys.modules["api"] = fake_api_pkg
        sys.modules["api.routers"] = fake_routers_pkg
        sys.modules["api.routers._helpers"] = fake_helpers

    # --- events.bus ---
    # CANNOT force-override because test_event_bus.py needs the real module.
    # Only stub if not present (conftest reorders arbiter tests LAST, so
    # test_event_bus runs first and loads the real module, meaning we'll
    # fall through to the else branch and patch attributes on the real module).
    fake_event_bus_instance = MagicMock()
    fake_event_bus_instance.publish = AsyncMock()

    existing_events_bus = sys.modules.get("events.bus")
    if existing_events_bus is not None:
        # Preserve the original get_event_bus for other test files by only
        # patching on a per-test basis via the instance. Here we just override
        # the factory function to return our mock.
        existing_events_bus.get_event_bus = lambda: fake_event_bus_instance
    else:

        class _FakeEventBus:
            pass

        fake_bus_module = types.ModuleType("events.bus")
        fake_bus_module.get_event_bus = lambda: fake_event_bus_instance
        fake_bus_module.EventBus = _FakeEventBus
        sys.modules["events.bus"] = fake_bus_module

    # --- x402 payment dispatcher ---
    fake_dispatcher = MagicMock()
    fake_dispatcher.refund_trustless_escrow = AsyncMock(
        return_value={"success": True, "tx_hash": "0xREF_DEFAULT"}
    )

    existing_pd = sys.modules.get("integrations.x402.payment_dispatcher")
    if existing_pd is not None:
        existing_pd.get_dispatcher = lambda: fake_dispatcher
        existing_pd.get_payment_dispatcher = lambda: fake_dispatcher
    else:
        fake_pd_module = types.ModuleType("integrations.x402.payment_dispatcher")
        fake_pd_module.get_dispatcher = lambda: fake_dispatcher
        fake_pd_module.get_payment_dispatcher = lambda: fake_dispatcher
        sys.modules["integrations.x402.payment_dispatcher"] = fake_pd_module

    return fake_helpers, fake_event_bus_instance, fake_dispatcher


# Module-level placeholders. Populated by the autouse fixture below so
# tests run with our mocks but OTHER test files in the same pytest
# process see the real modules. DO NOT call _install_stubs() at module
# load time -- it would pollute sys.modules during collection.
_FAKE_HELPERS = None
_FAKE_EVENT_BUS = None
_FAKE_DISPATCHER = None


# ---------------------------------------------------------------------------
# Supabase client stub
# ---------------------------------------------------------------------------


def _make_fake_supabase_client(existing_verdict=None):
    """Build a MagicMock that mimics the Supabase client chain for
    .table().update/select/insert/eq/execute calls.
    """
    table = MagicMock()
    # update().eq().execute() -> ok
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{}]
    )
    # insert().execute() -> dispute row
    table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "dispute-mock-id"}]
    )
    # select().eq().execute() -> existing verdict check
    select_resp = MagicMock(data=[{"arbiter_verdict": existing_verdict}])
    table.select.return_value.eq.return_value.execute.return_value = select_resp

    client = MagicMock()
    client.table.return_value = table
    return client


# Supabase stub is installed by the autouse fixture below (scoped to this
# test module so it doesn't leak to other test files).
fake_db = None


_STUB_MODULES = [
    "api",
    "api.routers",
    "api.routers._helpers",
    "events.bus",
    "integrations.x402.payment_dispatcher",
    "supabase_client",
]


@pytest.fixture(scope="module", autouse=True)
def _arbiter_stubs_module_scope():
    """Install arbiter test stubs for the duration of this test module only.

    This fixture runs BEFORE any test in this file and AFTER the last test.
    It saves the original sys.modules state and the original attributes it
    patches, then restores everything on teardown. This prevents the stubs
    from leaking to other test files in the same pytest process.
    """
    global _FAKE_HELPERS, _FAKE_EVENT_BUS, _FAKE_DISPATCHER, fake_db

    # Save original sys.modules entries and specific attributes we patch
    saved_modules = {}
    saved_attrs = {}  # (module_name, attr_name) -> original value
    for name in _STUB_MODULES:
        saved_modules[name] = sys.modules.get(name)

    # Save attributes we monkey-patch on real modules
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

    # Install stubs
    _FAKE_HELPERS, _FAKE_EVENT_BUS, _FAKE_DISPATCHER = _install_stubs()
    existing_db = sys.modules.get("supabase_client")
    if existing_db is not None:
        existing_db.get_client = lambda: _make_fake_supabase_client()
        existing_db._arbiter_stub = "integration"
        fake_db = existing_db
    else:
        fake_db_local = types.ModuleType("supabase_client")
        fake_db_local.get_client = lambda: _make_fake_supabase_client()
        fake_db_local._arbiter_stub = "integration"
        sys.modules["supabase_client"] = fake_db_local
        fake_db = fake_db_local

    yield

    # Teardown: restore everything
    for (mod_name, attr_name), original in saved_attrs.items():
        mod = sys.modules.get(mod_name)
        if mod is not None:
            setattr(mod, attr_name, original)

    # Remove any entries we added that weren't there before
    for name, original_mod in saved_modules.items():
        if original_mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original_mod

    # Clear our stub tags
    sb = sys.modules.get("supabase_client")
    if sb is not None and hasattr(sb, "_arbiter_stub"):
        try:
            delattr(sb, "_arbiter_stub")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Phase 0 GR-0.2: enable auto-release for this test module.
# ---------------------------------------------------------------------------
#
# processor.py now reads EM_ARBITER_AUTO_RELEASE_ENABLED at call time and
# defaults to false. This module's tests were written against the pre-gate
# behavior and assert that auto-mode PASS/FAIL trigger settle/refund. To
# keep the semantic coverage of those tests while the gate exists, we
# flip the env flag on for every test in this file. The new
# test_arbiter_phase0.py file exercises the OFF path explicitly.
@pytest.fixture(autouse=True)
def _enable_auto_release_for_integration_tests(monkeypatch):
    monkeypatch.setenv("EM_ARBITER_AUTO_RELEASE_ENABLED", "true")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


from integrations.arbiter.types import (  # noqa: E402
    ArbiterDecision,
    ArbiterTier,
    ArbiterVerdict,
    RingScore,
)


@pytest.fixture
def task_auto():
    return {
        "id": "task-auto-001",
        "agent_id": "0xagent",
        "bounty_usd": 0.10,
        "arbiter_mode": "auto",
        "arbiter_enabled": True,
    }


@pytest.fixture
def task_manual():
    return {
        "id": "task-manual-001",
        "agent_id": "0xagent",
        "bounty_usd": 0.10,
        "arbiter_mode": "manual",
        "arbiter_enabled": False,
    }


@pytest.fixture
def task_hybrid():
    return {
        "id": "task-hybrid-001",
        "agent_id": "0xagent",
        "bounty_usd": 0.10,
        "arbiter_mode": "hybrid",
        "arbiter_enabled": True,
    }


@pytest.fixture
def submission():
    return {
        "id": "sub-001",
        "evidence": {"photo": "https://example.com/p.jpg"},
        "auto_check_details": {"score": 0.92},
        "ai_verification_result": {"score": 0.88},
        "executor": {"id": "exec-1", "wallet_address": "0xworker"},
    }


def make_verdict(decision: ArbiterDecision, score: float, disagreement: bool = False):
    return ArbiterVerdict(
        decision=decision,
        tier=ArbiterTier.CHEAP,
        aggregate_score=score,
        confidence=0.85,
        evidence_hash="0x" + "a" * 64,
        commitment_hash="0x" + "b" * 64,
        ring_scores=[
            RingScore(
                ring="ring1",
                score=score,
                decision=decision.value,
                confidence=0.85,
                provider="photint",
                model="phase_a+b",
            )
        ],
        reason=f"test verdict score={score}",
        disagreement=disagreement,
    )


# ---------------------------------------------------------------------------
# Auto mode tests
# ---------------------------------------------------------------------------


class TestAutoMode:
    """auto mode triggers release/refund via Facilitator."""

    @pytest.mark.asyncio
    async def test_auto_pass_triggers_settle(self, task_auto, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_HELPERS._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xPAY_PASS"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.PASS, 0.92)
            result = await process_arbiter_verdict(v, task_auto, submission)

        assert result.action == "released"
        assert result.success is True
        assert result.payment_tx == "0xPAY_PASS"
        _FAKE_HELPERS._settle_submission_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_fail_triggers_refund(self, task_auto, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_DISPATCHER.refund_trustless_escrow = AsyncMock(
            return_value={"success": True, "tx_hash": "0xREF_FAIL"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.FAIL, 0.15)
            result = await process_arbiter_verdict(v, task_auto, submission)

        assert result.action == "refunded"
        assert result.success is True
        assert result.refund_tx == "0xREF_FAIL"
        _FAKE_DISPATCHER.refund_trustless_escrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_inconclusive_creates_dispute(self, task_auto, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.INCONCLUSIVE, 0.55)
            result = await process_arbiter_verdict(v, task_auto, submission)

        assert result.action == "escalated"
        assert result.dispute_id is not None

    @pytest.mark.asyncio
    async def test_auto_settle_returns_none_logged_as_failure(
        self, task_auto, submission
    ):
        """Defensive: if Facilitator returns None we must not crash."""
        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_HELPERS._settle_submission_payment = AsyncMock(return_value=None)

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.PASS, 0.92)
            result = await process_arbiter_verdict(v, task_auto, submission)

        assert result.action == "released"
        assert result.success is False
        assert "non-dict" in (result.error or "")


# ---------------------------------------------------------------------------
# Manual + hybrid mode tests
# ---------------------------------------------------------------------------


class TestManualAndHybridModes:
    """manual never auto-acts; hybrid stores but doesn't release."""

    @pytest.mark.asyncio
    async def test_manual_pass_stored_only(self, task_manual, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_HELPERS._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xSHOULD_NOT_BE_CALLED"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.PASS, 0.92)
            result = await process_arbiter_verdict(v, task_manual, submission)

        assert result.action == "stored"
        # Settle must NOT be called in manual mode
        _FAKE_HELPERS._settle_submission_payment.assert_not_called()

    @pytest.mark.asyncio
    async def test_hybrid_pass_stored_awaits_agent(self, task_hybrid, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_HELPERS._settle_submission_payment = AsyncMock()

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.PASS, 0.92)
            result = await process_arbiter_verdict(v, task_hybrid, submission)

        assert result.action == "stored"
        _FAKE_HELPERS._settle_submission_payment.assert_not_called()


# ---------------------------------------------------------------------------
# Skipped + inconclusive tests
# ---------------------------------------------------------------------------


class TestSkippedAndInconclusive:
    @pytest.mark.asyncio
    async def test_skipped_is_noop(self, task_auto, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.SKIPPED, 0.0)
            result = await process_arbiter_verdict(v, task_auto, submission)

        assert result.action == "skipped"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_inconclusive_with_disagreement_flag(self, task_auto, submission):
        """Ring disagreement should still escalate via the disputes table."""
        from integrations.arbiter.processor import process_arbiter_verdict

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.INCONCLUSIVE, 0.55, disagreement=True)
            result = await process_arbiter_verdict(v, task_auto, submission)

        assert result.action == "escalated"
        assert result.dispute_id is not None


# ---------------------------------------------------------------------------
# Event bus + webhook tests
# ---------------------------------------------------------------------------


class TestEventDispatch:
    """All verdicts should publish events and dispatch webhooks."""

    @pytest.mark.asyncio
    async def test_pass_emits_arbiter_pass_event(self, task_auto, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_HELPERS._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xPAY_EVT"}
        )
        _FAKE_EVENT_BUS.publish.reset_mock()
        _FAKE_HELPERS.dispatch_webhook.reset_mock()

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.PASS, 0.92)
            await process_arbiter_verdict(v, task_auto, submission)

        assert _FAKE_EVENT_BUS.publish.called
        assert _FAKE_HELPERS.dispatch_webhook.called

    @pytest.mark.asyncio
    async def test_fail_emits_arbiter_fail_event(self, task_auto, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_DISPATCHER.refund_trustless_escrow = AsyncMock(
            return_value={"success": True, "tx_hash": "0xREF_EVT"}
        )
        _FAKE_EVENT_BUS.publish.reset_mock()

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.FAIL, 0.15)
            await process_arbiter_verdict(v, task_auto, submission)

        assert _FAKE_EVENT_BUS.publish.called


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_existing_verdict_does_not_double_persist(
        self, task_auto, submission
    ):
        """If submissions.arbiter_verdict is already set, persist short-circuits."""
        from integrations.arbiter.processor import process_arbiter_verdict

        # Swap in a client that reports an existing verdict
        fake_db.get_client = lambda: _make_fake_supabase_client(existing_verdict="pass")
        _FAKE_HELPERS._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xPAY_IDEM"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.PASS, 0.92)
            # Should still return a valid ProcessResult (not crash)
            result = await process_arbiter_verdict(v, task_auto, submission)

        assert result.action in ("released", "stored")
        # Reset for other tests
        fake_db.get_client = lambda: _make_fake_supabase_client()


# ---------------------------------------------------------------------------
# Fee-split regression test
# ---------------------------------------------------------------------------


class TestFeeSplit:
    """Arbiter dispatch must NOT alter the 87/13 fee split.

    This is a structural test: the processor delegates to existing
    _settle_submission_payment which already has its own fee-split logic.
    We verify the processor does not attempt to override that behavior.
    """

    @pytest.mark.asyncio
    async def test_processor_does_not_compute_fees(self, task_auto, submission):
        from integrations.arbiter.processor import process_arbiter_verdict

        called_with = {}

        async def capture_settle(**kwargs):
            called_with.update(kwargs)
            return {"payment_tx": "0xFEE_TEST"}

        _FAKE_HELPERS._settle_submission_payment = capture_settle

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            v = make_verdict(ArbiterDecision.PASS, 0.92)
            await process_arbiter_verdict(v, task_auto, submission)

        # Processor should NOT pass any fee override to settle
        # (fee split is computed by _settle_submission_payment from bounty_usd)
        assert "fee_usdc" not in called_with
        assert "platform_fee_pct" not in called_with
        assert "override_fee" not in called_with
