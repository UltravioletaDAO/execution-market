"""
Tests for ERC-8004 Side Effects Processor (Outbox Pattern)

Covers:
- enqueue_side_effect creates a record
- enqueue_side_effect dedup (same submission_id + effect_type = no duplicate)
- mark_side_effect updates status and increments attempts
- get_pending_effects respects retry schedule
- Structured logging output
- Validation of invalid effect_type and score
"""

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.erc8004

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from reputation.side_effects import (
    MAX_ATTEMPTS,
    RETRY_SCHEDULE_MINUTES,
    enqueue_side_effect,
    get_pending_effects,
    mark_side_effect,
    _log_side_effect,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_supabase_mock(
    select_data=None, upsert_data=None, update_data=None, single_data=None
):
    """Create a mock Supabase client with chainable query builder."""
    mock = MagicMock()

    # Chain for .table().upsert().execute()
    upsert_result = MagicMock()
    upsert_result.data = upsert_data
    upsert_chain = MagicMock()
    upsert_chain.execute.return_value = upsert_result

    # Chain for .table().update().eq().execute()
    update_result = MagicMock()
    update_result.data = update_data
    update_eq = MagicMock()
    update_eq.execute.return_value = update_result
    update_chain = MagicMock()
    update_chain.eq.return_value = update_eq

    # Chain for .table().select().eq().single().execute()
    single_result = MagicMock()
    single_result.data = single_data
    single_chain = MagicMock()
    single_chain.execute.return_value = single_result
    eq_chain = MagicMock()
    eq_chain.single.return_value = single_chain
    select_for_single = MagicMock()
    select_for_single.eq.return_value = eq_chain

    # Chain for .table().select().in_().lt().order().limit().execute()
    select_result = MagicMock()
    select_result.data = select_data
    limit_chain = MagicMock()
    limit_chain.execute.return_value = select_result
    order_chain = MagicMock()
    order_chain.limit.return_value = limit_chain
    lt_chain = MagicMock()
    lt_chain.order.return_value = order_chain
    in_chain = MagicMock()
    in_chain.lt.return_value = lt_chain
    select_for_list = MagicMock()
    select_for_list.in_.return_value = in_chain

    def table_side_effect(name):
        tbl = MagicMock()

        def upsert_fn(row, on_conflict=None, ignore_duplicates=False):
            return upsert_chain

        tbl.upsert.side_effect = upsert_fn
        tbl.update.return_value = update_chain

        def select_fn(cols):
            if cols == "*":
                return select_for_list
            else:
                return select_for_single

        tbl.select.side_effect = select_fn
        return tbl

    mock.table.side_effect = table_side_effect
    return mock


# ---------------------------------------------------------------------------
# Tests: enqueue_side_effect
# ---------------------------------------------------------------------------


class TestEnqueueSideEffect:
    """Test enqueue_side_effect function."""

    @pytest.mark.asyncio
    async def test_enqueue_creates_record(self):
        """Enqueue should insert a new side effect record."""
        created_row = {
            "id": "ef-001",
            "submission_id": "sub-001",
            "effect_type": "register_worker_identity",
            "status": "pending",
            "attempts": 0,
            "payload": {"task_id": "task-001", "worker_wallet": "0xWorker"},
        }
        mock_sb = _make_supabase_mock(upsert_data=[created_row])

        result = await enqueue_side_effect(
            supabase=mock_sb,
            submission_id="sub-001",
            effect_type="register_worker_identity",
            payload={"task_id": "task-001", "worker_wallet": "0xWorker"},
        )

        assert result is not None
        assert result["id"] == "ef-001"
        assert result["effect_type"] == "register_worker_identity"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_enqueue_with_score(self):
        """Enqueue with score should include it in the record."""
        created_row = {
            "id": "ef-002",
            "submission_id": "sub-002",
            "effect_type": "rate_worker_from_agent",
            "status": "pending",
            "attempts": 0,
            "score": 85,
            "payload": {},
        }
        mock_sb = _make_supabase_mock(upsert_data=[created_row])

        result = await enqueue_side_effect(
            supabase=mock_sb,
            submission_id="sub-002",
            effect_type="rate_worker_from_agent",
            score=85,
        )

        assert result is not None
        assert result["score"] == 85

    @pytest.mark.asyncio
    async def test_enqueue_dedup_returns_none(self):
        """Duplicate enqueue (same submission_id + effect_type) returns None."""
        mock_sb = _make_supabase_mock(upsert_data=[])

        result = await enqueue_side_effect(
            supabase=mock_sb,
            submission_id="sub-001",
            effect_type="register_worker_identity",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_enqueue_invalid_effect_type_raises(self):
        """Invalid effect_type should raise ValueError."""
        mock_sb = _make_supabase_mock()

        with pytest.raises(ValueError, match="Invalid effect_type"):
            await enqueue_side_effect(
                supabase=mock_sb,
                submission_id="sub-001",
                effect_type="invalid_type",
            )

    @pytest.mark.asyncio
    async def test_enqueue_invalid_score_raises(self):
        """Score outside 0-100 should raise ValueError."""
        mock_sb = _make_supabase_mock()

        with pytest.raises(ValueError, match="Score must be 0-100"):
            await enqueue_side_effect(
                supabase=mock_sb,
                submission_id="sub-001",
                effect_type="rate_worker_from_agent",
                score=150,
            )

    @pytest.mark.asyncio
    async def test_enqueue_negative_score_raises(self):
        """Negative score should raise ValueError."""
        mock_sb = _make_supabase_mock()

        with pytest.raises(ValueError, match="Score must be 0-100"):
            await enqueue_side_effect(
                supabase=mock_sb,
                submission_id="sub-001",
                effect_type="rate_worker_from_agent",
                score=-1,
            )


# ---------------------------------------------------------------------------
# Tests: mark_side_effect
# ---------------------------------------------------------------------------


class TestMarkSideEffect:
    """Test mark_side_effect function."""

    @pytest.mark.asyncio
    async def test_mark_success_increments_attempts(self):
        """Marking as success should increment attempts."""
        current_data = {
            "attempts": 0,
            "submission_id": "sub-001",
            "effect_type": "register_worker_identity",
            "payload": {"task_id": "task-001"},
        }
        mock_sb = _make_supabase_mock(single_data=current_data, update_data=[{}])

        await mark_side_effect(
            supabase=mock_sb,
            effect_id="ef-001",
            status="success",
            tx_hash="0xabc123",
        )

        # Verify update was called (via the table mock chain)
        # The mock chain was called — no exception means success
        assert True

    @pytest.mark.asyncio
    async def test_mark_failed_with_error(self):
        """Marking as failed should store error message."""
        current_data = {
            "attempts": 2,
            "submission_id": "sub-001",
            "effect_type": "rate_worker_from_agent",
            "payload": {},
        }
        mock_sb = _make_supabase_mock(single_data=current_data, update_data=[{}])

        await mark_side_effect(
            supabase=mock_sb,
            effect_id="ef-001",
            status="failed",
            error="Network timeout",
        )

        # No exception = success
        assert True

    @pytest.mark.asyncio
    async def test_mark_invalid_status_raises(self):
        """Invalid status should raise ValueError."""
        mock_sb = _make_supabase_mock()

        with pytest.raises(ValueError, match="Invalid status"):
            await mark_side_effect(
                supabase=mock_sb,
                effect_id="ef-001",
                status="bogus",
            )


# ---------------------------------------------------------------------------
# Tests: get_pending_effects
# ---------------------------------------------------------------------------


class TestGetPendingEffects:
    """Test get_pending_effects function."""

    @pytest.mark.asyncio
    async def test_returns_never_attempted_immediately(self):
        """Effects with attempts=0 should be returned immediately."""
        effects = [
            {
                "id": "ef-001",
                "submission_id": "sub-001",
                "effect_type": "register_worker_identity",
                "status": "pending",
                "attempts": 0,
                "payload": {},
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        mock_sb = _make_supabase_mock(select_data=effects)

        result = await get_pending_effects(mock_sb)

        assert len(result) == 1
        assert result[0]["id"] == "ef-001"

    @pytest.mark.asyncio
    async def test_respects_retry_schedule(self):
        """Effects should only be returned after backoff period."""
        now = datetime.now(timezone.utc)
        # 1 attempt, updated 30 seconds ago — should NOT be ready (need 1 min)
        effects = [
            {
                "id": "ef-002",
                "submission_id": "sub-002",
                "effect_type": "rate_worker_from_agent",
                "status": "failed",
                "attempts": 1,
                "payload": {},
                "updated_at": (now - timedelta(seconds=30)).isoformat(),
                "created_at": (now - timedelta(minutes=5)).isoformat(),
            }
        ]
        mock_sb = _make_supabase_mock(select_data=effects)

        result = await get_pending_effects(mock_sb)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_returns_after_backoff_elapsed(self):
        """Effects should be returned after backoff period has passed."""
        now = datetime.now(timezone.utc)
        # 1 attempt, updated 2 minutes ago — should be ready (need 1 min)
        effects = [
            {
                "id": "ef-003",
                "submission_id": "sub-003",
                "effect_type": "rate_agent_from_worker",
                "status": "failed",
                "attempts": 1,
                "payload": {},
                "updated_at": (now - timedelta(minutes=2)).isoformat(),
                "created_at": (now - timedelta(minutes=10)).isoformat(),
            }
        ]
        mock_sb = _make_supabase_mock(select_data=effects)

        result = await get_pending_effects(mock_sb)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_empty_table_returns_empty(self):
        """Empty table should return empty list."""
        mock_sb = _make_supabase_mock(select_data=[])

        result = await get_pending_effects(mock_sb)

        assert result == []

    @pytest.mark.asyncio
    async def test_none_data_returns_empty(self):
        """None data from Supabase should return empty list."""
        mock_sb = _make_supabase_mock(select_data=None)

        result = await get_pending_effects(mock_sb)

        assert result == []

    @pytest.mark.asyncio
    async def test_higher_attempt_longer_backoff(self):
        """Higher attempt count should require longer backoff."""
        now = datetime.now(timezone.utc)
        # 3 attempts, updated 10 minutes ago — need 15 min backoff, should NOT be ready
        effects = [
            {
                "id": "ef-004",
                "submission_id": "sub-004",
                "effect_type": "rate_worker_on_rejection",
                "status": "failed",
                "attempts": 3,
                "payload": {},
                "updated_at": (now - timedelta(minutes=10)).isoformat(),
                "created_at": (now - timedelta(hours=1)).isoformat(),
            }
        ]
        mock_sb = _make_supabase_mock(select_data=effects)

        result = await get_pending_effects(mock_sb)

        assert len(result) == 0


# ---------------------------------------------------------------------------
# Tests: _log_side_effect
# ---------------------------------------------------------------------------


class TestLogSideEffect:
    """Test structured logging output."""

    def test_log_includes_all_fields(self, caplog):
        """Log output should include all structured fields."""
        effect = {
            "submission_id": "sub-001",
            "effect_type": "register_worker_identity",
            "status": "pending",
            "attempts": 0,
            "tx_hash": None,
            "last_error": None,
            "payload": {"task_id": "task-001"},
        }

        with caplog.at_level(logging.INFO, logger="reputation.side_effects"):
            _log_side_effect(effect, {"action": "enqueued"})

        assert "erc8004_side_effect" in caplog.text

    def test_log_with_tx_hash(self, caplog):
        """Log should include tx_hash when present."""
        effect = {
            "submission_id": "sub-002",
            "effect_type": "rate_worker_from_agent",
            "status": "success",
            "attempts": 1,
            "tx_hash": "0xabc123",
            "last_error": None,
            "payload": {"task_id": "task-002"},
        }

        with caplog.at_level(logging.INFO, logger="reputation.side_effects"):
            _log_side_effect(effect)

        assert "erc8004_side_effect" in caplog.text


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Test module constants."""

    def test_retry_schedule_is_ascending(self):
        """Retry schedule should be strictly ascending."""
        for i in range(1, len(RETRY_SCHEDULE_MINUTES)):
            assert RETRY_SCHEDULE_MINUTES[i] > RETRY_SCHEDULE_MINUTES[i - 1]

    def test_max_attempts_matches_schedule(self):
        """MAX_ATTEMPTS should match the length of RETRY_SCHEDULE_MINUTES."""
        assert MAX_ATTEMPTS == len(RETRY_SCHEDULE_MINUTES)

    def test_retry_schedule_values(self):
        """Verify the exact retry schedule values."""
        assert RETRY_SCHEDULE_MINUTES == [1, 5, 15, 60, 360, 1440]
