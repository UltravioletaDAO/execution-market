"""
Phase 1 Audit — Payment Safety Tests

4 tests covering critical payment safety invariants:
1. Payment failure must NOT change submission verdict to accepted
2. Idempotency: payment_events success hit must skip re-settlement
3. em_cancel_task must reject in_progress / submitted / completed tasks
4. em_check_submission must be case-insensitive on agent_id comparison
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.core

from models import (
    ApproveSubmissionInput,
    CancelTaskInput,
    CheckSubmissionInput,
    SubmissionVerdict,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def task_id():
    return str(uuid4())


@pytest.fixture
def submission_id():
    return str(uuid4())


@pytest.fixture
def agent_id():
    return "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"


@pytest.fixture
def worker_wallet():
    return "0xDeAdBeEf1234567890DeAdBeEf1234567890DeAd"


@pytest.fixture
def sample_task(task_id, agent_id):
    return {
        "id": task_id,
        "agent_id": agent_id,
        "title": "Audit test task",
        "instructions": "Take a photo of the store entrance showing it is open.",
        "category": "physical_presence",
        "bounty_usd": 0.10,
        "payment_token": "USDC",
        "payment_network": "base",
        "status": "submitted",
    }


@pytest.fixture
def sample_executor(worker_wallet):
    return {
        "id": str(uuid4()),
        "display_name": "Test Worker",
        "wallet_address": worker_wallet,
        "reputation_score": 80,
    }


@pytest.fixture
def sample_submission(submission_id, task_id, sample_task, sample_executor):
    return {
        "id": submission_id,
        "task_id": task_id,
        "executor_id": sample_executor["id"],
        "agent_verdict": "pending",
        "notes": "Done.",
        "task": sample_task,
        "executor": sample_executor,
    }


# ---------------------------------------------------------------------------
# Test 1: Payment failure must NOT change verdict to "accepted"
# ---------------------------------------------------------------------------


class TestApprovePaymentFailureNoVerdictChange:
    @pytest.mark.asyncio
    async def test_mcp_approve_payment_failure_no_verdict_change(
        self,
        sample_submission,
        sample_task,
        submission_id,
        task_id,
        agent_id,
    ):
        """
        When the payment dispatcher raises an exception during approval,
        the submission verdict must NOT be updated to 'accepted'.
        The tool must return an error string.
        """
        mock_db = MagicMock()
        mock_db.get_submission = AsyncMock(return_value=sample_submission)
        mock_db.get_task = AsyncMock(return_value=sample_task)
        mock_db.update_submission = AsyncMock()

        mock_dispatcher = MagicMock()
        mock_dispatcher.get_mode.return_value = "fase1"
        mock_dispatcher.release_payment = AsyncMock(
            side_effect=Exception("Network timeout during settlement")
        )

        params = ApproveSubmissionInput(
            submission_id=submission_id,
            agent_id=agent_id,
            verdict=SubmissionVerdict.ACCEPTED,
            notes="Looks good",
        )

        # Import via server module — it re-exports em_approve_submission
        from server import em_approve_submission

        with (
            patch("server.db", mock_db),
            patch(
                "integrations.x402.payment_dispatcher.get_dispatcher",
                return_value=mock_dispatcher,
            ),
        ):
            result = await em_approve_submission(params)

        # Payment failed → verdict must NOT have been written
        mock_db.update_submission.assert_not_called()

        # Result must signal an error
        assert "Error" in result or "error" in result.lower() or "Payment" in result


# ---------------------------------------------------------------------------
# Test 2: Idempotency — payment_events success hit must skip re-settlement
# ---------------------------------------------------------------------------


class TestIdempotencyPaymentEventsTable:
    @pytest.mark.asyncio
    async def test_idempotency_checks_payment_events_table(
        self,
        submission_id,
        task_id,
    ):
        """
        _get_existing_submission_payment should detect a settled event in
        payment_events (when payments table is empty) and return a synthesised
        payment row so callers skip re-settlement.
        """
        from api.routers._helpers import _get_existing_submission_payment

        mock_client = MagicMock()

        # payments table returns empty
        payments_result = MagicMock()
        payments_result.data = []

        # submissions lookup returns task_id
        submissions_result = MagicMock()
        submissions_result.data = [{"task_id": task_id}]

        # payment_events returns a success event
        events_result = MagicMock()
        events_result.data = [
            {
                "id": str(uuid4()),
                "task_id": task_id,
                "event_type": "settle",
                "status": "success",
                "tx_hash": "0x" + "a" * 64,
                "created_at": "2026-03-20T00:00:00Z",
                "metadata": {"amount": 0.10},
            }
        ]

        # Chain the mock builder pattern used by supabase-py
        def _table_side_effect(table_name):
            tbl = MagicMock()
            if table_name == "payments":
                tbl.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = payments_result
            elif table_name == "submissions":
                tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = submissions_result
            elif table_name == "payment_events":
                (
                    tbl.select.return_value.eq.return_value.in_.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value
                ) = events_result
            return tbl

        mock_client.table.side_effect = _table_side_effect

        with patch("api.routers._helpers.db.get_client", return_value=mock_client):
            result = _get_existing_submission_payment(submission_id)

        # Must find the event and synthesise a payment row
        assert result is not None, "Expected a payment row from payment_events fallback"
        assert result.get("_source") == "payment_events"
        assert result.get("task_id") == task_id
        assert result.get("type") == "release"
        assert result.get("status") == "confirmed"
        # tx_hash must be the one from the event
        assert result.get("tx_hash") == "0x" + "a" * 64


# ---------------------------------------------------------------------------
# Test 3: em_cancel_task must reject non-cancellable statuses
# ---------------------------------------------------------------------------


class TestCancelRejectsInProgressTask:
    @pytest.mark.asyncio
    async def test_mcp_cancel_rejects_in_progress_task(self, task_id, agent_id):
        """
        Cancelling a task in 'in_progress' status must be rejected.
        The tool must return an error mentioning the disallowed status.
        """
        await self._assert_cancel_rejected(task_id, agent_id, "in_progress")

    @pytest.mark.asyncio
    async def test_mcp_cancel_rejects_submitted_task(self, task_id, agent_id):
        """Cancelling a task in 'submitted' status must be rejected."""
        await self._assert_cancel_rejected(task_id, agent_id, "submitted")

    @pytest.mark.asyncio
    async def test_mcp_cancel_rejects_completed_task(self, task_id, agent_id):
        """Cancelling a task in 'completed' status must be rejected."""
        await self._assert_cancel_rejected(task_id, agent_id, "completed")

    async def _assert_cancel_rejected(self, task_id, agent_id, status):
        mock_db = MagicMock()
        mock_db.get_task = AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": agent_id,
                "title": "Test task",
                "status": status,
            }
        )
        mock_db.cancel_task = AsyncMock()

        params = CancelTaskInput(
            task_id=task_id,
            agent_id=agent_id,
            reason="No longer needed",
        )

        from server import em_cancel_task

        with patch("server.db", mock_db):
            result = await em_cancel_task(params)

        # Must return an error
        assert "Error" in result, (
            f"Expected Error for status='{status}', got: {result!r}"
        )
        # DB cancel must NOT have been called
        mock_db.cancel_task.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: em_check_submission must be case-insensitive on agent_id
# ---------------------------------------------------------------------------


class TestCheckSubmissionCaseInsensitiveAgentId:
    @pytest.mark.asyncio
    async def test_check_submission_case_insensitive_agent_id(self, task_id, agent_id):
        """
        em_check_submission with a lowercase variant of the agent_id stored
        in mixed-case must still grant access (no 'Not authorized' error).
        """
        mock_db = MagicMock()

        # Task stored with mixed-case agent_id
        mock_db.get_task = AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": agent_id,  # mixed case: 0xAbCdEf...
                "title": "Photo task",
                "status": "submitted",
            }
        )
        mock_db.get_submissions_for_task = AsyncMock(return_value=[])

        # Call with lowercase version of the same address
        lowercase_agent_id = agent_id.lower()
        assert lowercase_agent_id != agent_id, (
            "Test precondition: addresses differ in case"
        )

        params = CheckSubmissionInput(
            task_id=task_id,
            agent_id=lowercase_agent_id,
        )

        from server import em_check_submission

        with patch("server.db", mock_db):
            result = await em_check_submission(params)

        # Must NOT be an authorization error
        assert "Not authorized" not in result, (
            f"Case-insensitive check failed — got auth error: {result!r}"
        )
        # Should be a normal "no submissions" or similar response
        assert "Error" not in result or "not found" not in result.lower()
