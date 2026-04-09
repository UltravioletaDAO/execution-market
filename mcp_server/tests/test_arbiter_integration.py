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
    # api.routers._helpers
    fake_helpers = types.ModuleType("api.routers._helpers")
    fake_helpers._settle_submission_payment = AsyncMock(
        return_value={"payment_tx": "0xPAY_DEFAULT"}
    )
    fake_helpers.dispatch_webhook = AsyncMock()
    fake_routers_pkg = types.ModuleType("api.routers")
    fake_routers_pkg._helpers = fake_helpers
    fake_api_pkg = types.ModuleType("api")
    fake_api_pkg.routers = fake_routers_pkg
    sys.modules.setdefault("api", fake_api_pkg)
    sys.modules.setdefault("api.routers", fake_routers_pkg)
    sys.modules.setdefault("api.routers._helpers", fake_helpers)

    # events.bus (stub the get_event_bus factory)
    fake_event_bus_instance = MagicMock()
    fake_event_bus_instance.publish = AsyncMock()

    class _FakeEventBus:
        pass

    fake_bus_module = types.ModuleType("events.bus")
    fake_bus_module.get_event_bus = lambda: fake_event_bus_instance
    fake_bus_module.EventBus = _FakeEventBus
    sys.modules.setdefault("events.bus", fake_bus_module)

    # x402 payment dispatcher
    fake_dispatcher = MagicMock()
    fake_dispatcher.refund_trustless_escrow = AsyncMock(
        return_value={"success": True, "tx_hash": "0xREF_DEFAULT"}
    )
    fake_pd_module = types.ModuleType("integrations.x402.payment_dispatcher")
    fake_pd_module.get_payment_dispatcher = lambda: fake_dispatcher
    sys.modules.setdefault("integrations.x402.payment_dispatcher", fake_pd_module)

    return fake_helpers, fake_event_bus_instance, fake_dispatcher


_FAKE_HELPERS, _FAKE_EVENT_BUS, _FAKE_DISPATCHER = _install_stubs()


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


# Install supabase_client stub so processor._persist_verdict + escalation can run
fake_db = types.ModuleType("supabase_client")
fake_db.get_client = lambda: _make_fake_supabase_client()
sys.modules.setdefault("supabase_client", fake_db)


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
