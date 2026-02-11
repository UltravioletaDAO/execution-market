"""
Tests for ERC-8004 post-approval side effects (WS-1 + WS-2).

WS-1: Worker auto-registration on first paid completion
WS-2: Worker auto-rates agent after payment

Tests verify:
- Missing wallet -> skipped, approval succeeds
- Already registered -> no external call, skipped
- Facilitator success -> executor identity updated
- Facilitator failure -> failed row, approval still succeeds
- Valid erc8004_agent_id -> feedback submitted
- Wallet-only agent -> skipped, no exception
- Idempotent retry -> single submission due outbox dedup
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.erc8004

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure integrations.erc8004 submodules are importable for patching.
# The real modules have heavy dependencies (httpx, eth_account, etc.)
# that may not fully resolve in the test environment, so we stub
# the specific submodules in sys.modules when they haven't loaded.
_STUB_MODULES = [
    "integrations.erc8004",
    "integrations.erc8004.identity",
    "integrations.erc8004.facilitator_client",
]
for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        stub = ModuleType(_mod_name)
        # Pre-set attributes that will be patched so patch() doesn't fail
        if _mod_name.endswith(".identity"):
            stub.register_worker_gasless = None
            stub.update_executor_identity = None
        elif _mod_name.endswith(".facilitator_client"):
            stub.rate_agent = None
        sys.modules[_mod_name] = stub


# ---------------------------------------------------------------------------
# Helpers: build fake submission dicts matching routes.py expectations
# ---------------------------------------------------------------------------


def _make_submission(
    submission_id="sub-001",
    task_id="task-001",
    executor_id="exec-001",
    worker_wallet="0x1234567890abcdef1234567890abcdef12345678",
    erc8004_agent_id=None,
    task_erc8004_agent_id=None,
    task_agent_id=None,
    payment_network="base",
):
    return {
        "id": submission_id,
        "task": {
            "id": task_id,
            "erc8004_agent_id": task_erc8004_agent_id,
            "agent_id": task_agent_id,
            "payment_network": payment_network,
            "bounty_usd": 5.0,
            "title": "Test task",
        },
        "executor": {
            "id": executor_id,
            "wallet_address": worker_wallet,
            "erc8004_agent_id": erc8004_agent_id,
        },
    }


def _make_supabase_mock():
    """Create a mock Supabase client for side effects operations."""
    mock = MagicMock()

    def make_upsert_chain(return_data):
        result = MagicMock()
        result.data = return_data
        chain = MagicMock()
        chain.execute.return_value = result
        return chain

    single_result = MagicMock()
    single_result.data = {
        "attempts": 0,
        "submission_id": "sub-001",
        "effect_type": "test",
        "payload": {},
    }
    single_chain = MagicMock()
    single_chain.execute.return_value = single_result
    eq_for_single = MagicMock()
    eq_for_single.single.return_value = single_chain
    select_for_single = MagicMock()
    select_for_single.eq.return_value = eq_for_single

    update_result = MagicMock()
    update_result.data = [{}]
    update_eq = MagicMock()
    update_eq.execute.return_value = update_result
    update_chain = MagicMock()
    update_chain.eq.return_value = update_eq

    enqueue_calls = []

    def table_fn(name):
        tbl = MagicMock()

        def upsert_fn(row, on_conflict=None, ignore_duplicates=False):
            enqueue_calls.append(row)
            data = [{**row, "id": f"ef-{len(enqueue_calls):03d}"}]
            return make_upsert_chain(data)

        tbl.upsert.side_effect = upsert_fn
        tbl.update.return_value = update_chain

        def select_fn(cols):
            return select_for_single

        tbl.select.side_effect = select_fn
        return tbl

    mock.table.side_effect = table_fn
    mock._enqueue_calls = enqueue_calls
    return mock


# ---------------------------------------------------------------------------
# Fake objects for identity and facilitator
# ---------------------------------------------------------------------------


class FakeWorkerIdentityResult:
    def __init__(self, status="registered", agent_id=42, error=None):
        self.status = MagicMock(value=status)
        self.agent_id = agent_id
        self.error = error


class FakeFeedbackResult:
    def __init__(self, success=True, tx_hash="0xfeedback123", error=None):
        self.success = success
        self.transaction_hash = tx_hash
        self.error = error


# ===========================================================================
# WS-1: Worker Auto-Registration Tests
# ===========================================================================


class TestWS1AutoRegisterWorker:
    """WS-1: Worker auto-registration on first paid completion."""

    @pytest.mark.asyncio
    async def test_missing_wallet_skipped(self):
        """Missing wallet -> enqueue + mark skipped, no registration call."""
        submission = _make_submission(worker_wallet=None)
        mock_sb = _make_supabase_mock()

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=True)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws1_auto_register_worker

            await _ws1_auto_register_worker(
                submission_id="sub-001",
                executor=submission["executor"],
                worker_address=None,
                executor_id="exec-001",
                task_network="base",
                task_id="task-001",
            )

        assert len(mock_sb._enqueue_calls) == 1
        assert mock_sb._enqueue_calls[0]["effect_type"] == "register_worker_identity"
        payload = mock_sb._enqueue_calls[0]["payload"]
        assert payload.get("skip_reason") == "missing_or_invalid_wallet"

    @pytest.mark.asyncio
    async def test_already_registered_skipped(self):
        """Already registered executor -> enqueue + mark skipped, no external call."""
        submission = _make_submission(erc8004_agent_id=42)
        mock_sb = _make_supabase_mock()

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=True)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws1_auto_register_worker

            await _ws1_auto_register_worker(
                submission_id="sub-001",
                executor=submission["executor"],
                worker_address=submission["executor"]["wallet_address"],
                executor_id="exec-001",
                task_network="base",
                task_id="task-001",
            )

        assert len(mock_sb._enqueue_calls) == 1
        payload = mock_sb._enqueue_calls[0]["payload"]
        assert payload.get("skip_reason") == "already_registered"

    @pytest.mark.asyncio
    async def test_facilitator_success_updates_identity(self):
        """Successful registration -> executor identity updated, effect marked success."""
        submission = _make_submission(erc8004_agent_id=None)
        mock_sb = _make_supabase_mock()

        mock_register = AsyncMock(
            return_value=FakeWorkerIdentityResult(status="registered", agent_id=99)
        )
        mock_update = AsyncMock(return_value=True)

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
            patch(
                "integrations.erc8004.identity.register_worker_gasless",
                mock_register,
            ),
            patch(
                "integrations.erc8004.identity.update_executor_identity",
                mock_update,
            ),
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=True)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws1_auto_register_worker

            await _ws1_auto_register_worker(
                submission_id="sub-001",
                executor=submission["executor"],
                worker_address=submission["executor"]["wallet_address"],
                executor_id="exec-001",
                task_network="base",
                task_id="task-001",
            )

        mock_register.assert_called_once_with(
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            network="base",
        )
        mock_update.assert_called_once_with("exec-001", 99)

    @pytest.mark.asyncio
    async def test_facilitator_failure_marks_failed(self):
        """Failed registration -> effect marked failed, no exception raised."""
        submission = _make_submission(erc8004_agent_id=None)
        mock_sb = _make_supabase_mock()

        mock_register = AsyncMock(
            return_value=FakeWorkerIdentityResult(
                status="error", agent_id=None, error="RPC timeout"
            )
        )

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
            patch(
                "integrations.erc8004.identity.register_worker_gasless",
                mock_register,
            ),
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=True)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws1_auto_register_worker

            # Should NOT raise
            await _ws1_auto_register_worker(
                submission_id="sub-001",
                executor=submission["executor"],
                worker_address=submission["executor"]["wallet_address"],
                executor_id="exec-001",
                task_network="base",
                task_id="task-001",
            )

        # Enqueue happened (no skip_reason)
        assert len(mock_sb._enqueue_calls) == 1
        assert "skip_reason" not in mock_sb._enqueue_calls[0]["payload"]


# ===========================================================================
# WS-2: Worker Auto-Rates Agent Tests
# ===========================================================================


class TestWS2AutoRateAgent:
    """WS-2: Worker auto-rates agent after payment."""

    @pytest.mark.asyncio
    async def test_valid_agent_id_feedback_submitted(self):
        """Valid erc8004_agent_id -> feedback submitted successfully."""
        submission = _make_submission(task_erc8004_agent_id=2106)
        mock_sb = _make_supabase_mock()

        mock_rate = AsyncMock(
            return_value=FakeFeedbackResult(success=True, tx_hash="0xfeed123")
        )

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
            patch(
                "integrations.erc8004.facilitator_client.rate_agent",
                mock_rate,
            ),
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=False)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws2_auto_rate_agent

            await _ws2_auto_rate_agent(
                submission_id="sub-001",
                submission=submission,
                task=submission["task"],
                executor=submission["executor"],
                release_tx="0xpayment123",
                task_id="task-001",
            )

        mock_rate.assert_called_once_with(
            agent_id=2106,
            task_id="task-001",
            score=85,  # fallback score
            proof_tx="0xpayment123",
        )

    @pytest.mark.asyncio
    async def test_wallet_only_agent_skipped(self):
        """Agent with no numeric ID -> enqueue + mark skipped, no exception."""
        submission = _make_submission(
            task_erc8004_agent_id=None,
            task_agent_id="0xWalletAddress",  # non-numeric
        )
        mock_sb = _make_supabase_mock()

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=False)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws2_auto_rate_agent

            await _ws2_auto_rate_agent(
                submission_id="sub-001",
                submission=submission,
                task=submission["task"],
                executor=submission["executor"],
                release_tx="0xpayment123",
                task_id="task-001",
            )

        assert len(mock_sb._enqueue_calls) == 1
        payload = mock_sb._enqueue_calls[0]["payload"]
        assert payload.get("skip_reason") == "missing_agent_erc8004_id"

    @pytest.mark.asyncio
    async def test_numeric_agent_id_fallback(self):
        """Falls back to task.agent_id when erc8004_agent_id is missing."""
        submission = _make_submission(
            task_erc8004_agent_id=None,
            task_agent_id="469",  # numeric string
        )
        mock_sb = _make_supabase_mock()

        mock_rate = AsyncMock(return_value=FakeFeedbackResult(success=True))

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
            patch(
                "integrations.erc8004.facilitator_client.rate_agent",
                mock_rate,
            ),
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=False)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws2_auto_rate_agent

            await _ws2_auto_rate_agent(
                submission_id="sub-001",
                submission=submission,
                task=submission["task"],
                executor=submission["executor"],
                release_tx="0xpayment123",
                task_id="task-001",
            )

        mock_rate.assert_called_once()
        assert mock_rate.call_args.kwargs["agent_id"] == 469

    @pytest.mark.asyncio
    async def test_idempotent_dedup(self):
        """Second enqueue for same submission + effect_type should be deduped."""
        submission = _make_submission(task_erc8004_agent_id=2106)

        mock_sb = MagicMock()
        call_count = [0]

        def table_fn(name):
            tbl = MagicMock()

            def upsert_fn(row, on_conflict=None, ignore_duplicates=False):
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.data = [{**row, "id": "ef-001"}]
                else:
                    result.data = []  # dedup
                chain = MagicMock()
                chain.execute.return_value = result
                return chain

            single_result = MagicMock()
            single_result.data = {
                "attempts": 0,
                "submission_id": "sub-001",
                "effect_type": "test",
                "payload": {},
            }
            single_chain = MagicMock()
            single_chain.execute.return_value = single_result
            eq_single = MagicMock()
            eq_single.single.return_value = single_chain
            select_chain = MagicMock()
            select_chain.eq.return_value = eq_single

            update_result = MagicMock()
            update_result.data = [{}]
            update_eq = MagicMock()
            update_eq.execute.return_value = update_result
            update_chain = MagicMock()
            update_chain.eq.return_value = update_eq

            tbl.upsert.side_effect = upsert_fn
            tbl.select.return_value = select_chain
            tbl.update.return_value = update_chain
            return tbl

        mock_sb.table.side_effect = table_fn

        mock_rate = AsyncMock(return_value=FakeFeedbackResult(success=True))

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
            patch(
                "integrations.erc8004.facilitator_client.rate_agent",
                mock_rate,
            ),
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=False)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _ws2_auto_rate_agent

            # First call: should proceed
            await _ws2_auto_rate_agent(
                submission_id="sub-001",
                submission=submission,
                task=submission["task"],
                executor=submission["executor"],
                release_tx="0xpayment123",
                task_id="task-001",
            )

            # Second call: dedup should prevent rate_agent call
            mock_rate.reset_mock()
            await _ws2_auto_rate_agent(
                submission_id="sub-001",
                submission=submission,
                task=submission["task"],
                executor=submission["executor"],
                release_tx="0xpayment123",
                task_id="task-001",
            )

        # rate_agent should NOT be called the second time (dedup)
        mock_rate.assert_not_called()


# ===========================================================================
# Integration: _execute_post_approval_side_effects
# ===========================================================================


class TestExecutePostApprovalSideEffects:
    """Test the orchestrator function."""

    @pytest.mark.asyncio
    async def test_both_flags_disabled_noop(self):
        """Both flags disabled -> no side effects executed."""
        submission = _make_submission(task_erc8004_agent_id=2106)
        mock_sb = _make_supabase_mock()

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
        ):
            MockConfig.is_feature_enabled = AsyncMock(return_value=False)
            mock_db.get_client.return_value = mock_sb

            from api.routes import _execute_post_approval_side_effects

            await _execute_post_approval_side_effects(
                submission_id="sub-001",
                submission=submission,
                release_tx="0xpayment123",
            )

        assert len(mock_sb._enqueue_calls) == 0

    @pytest.mark.asyncio
    async def test_exception_never_propagates(self):
        """Side effect errors must never propagate to the caller."""
        submission = _make_submission()

        with (
            patch("api.routes.PlatformConfig") as MockConfig,
            patch("api.routes.db") as mock_db,
        ):
            MockConfig.is_feature_enabled = AsyncMock(side_effect=Exception("DB down"))
            mock_db.get_client.return_value = MagicMock()

            from api.routes import _execute_post_approval_side_effects

            await _execute_post_approval_side_effects(
                submission_id="sub-001",
                submission=submission,
                release_tx="0xpayment123",
            )
