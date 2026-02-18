"""
P0 Tests for A2A Payment Bridge

Tests that A2A approve/cancel operations properly delegate to
PaymentDispatcher instead of just updating DB status.

Covers bugs: P0-3, P0-4 from AUDIT_AGENT_EXECUTOR_2026-02-18.md
"""

import sys
import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Fixtures
# ============================================================================


def _make_task(
    task_id="task-a2a-001",
    status="submitted",
    agent_id="agent-1",
    bounty_usd=1.0,
    escrow_status=None,
):
    """Create a mock EM task dict."""
    task = {
        "id": task_id,
        "agent_id": agent_id,
        "title": "Test A2A task",
        "description": "Do something",
        "bounty_usd": bounty_usd,
        "status": status,
        "category": "simple_action",
        "created_at": "2026-02-18T00:00:00Z",
        "updated_at": "2026-02-18T00:00:00Z",
        "deadline": "2026-02-19T00:00:00Z",
        "metadata": {},
    }
    if escrow_status:
        task["escrow_status"] = escrow_status
        task["metadata"]["escrow_status"] = escrow_status
    return task


def _make_text_message(text):
    """Create an A2A Message with a TextPart."""
    from a2a.models import Message, TextPart

    return Message(role="user", parts=[TextPart(text=text)])


def _make_data_message(action):
    """Create an A2A Message with a DataPart action."""
    from a2a.models import Message, DataPart

    return Message(role="user", parts=[DataPart(data={"action": action})])


# ============================================================================
# P0 Tests — A2A Approve Payment Bridge
# ============================================================================


@pytest.mark.a2a_bridge
class TestA2AApprovePaymentBridge:
    """Test that A2A approve correctly delegates to PaymentDispatcher."""

    @pytest.mark.asyncio
    async def test_a2a_approve_calls_payment_dispatcher(self):
        """
        P0-3: send_message('approve') must call PaymentDispatcher
        before updating task status to completed.
        """
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="submitted")
        message = _make_text_message("approve this submission")

        mock_payment = AsyncMock(return_value=True)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_approval_payment", mock_payment):
                manager = A2ATaskManager(agent_id="agent-1")
                await manager.send_message(task_id="task-a2a-001", message=message)

        # Payment must have been called
        mock_payment.assert_called_once_with(task)
        # Task must be completed after payment
        mock_db.update_task.assert_called()
        update_data = mock_db.update_task.call_args[0][1]
        assert update_data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_a2a_approve_payment_failure_stays_working(self):
        """
        P0-3: If payment fails, task status must NOT change to completed.
        """
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="submitted")
        message = _make_text_message("approve")

        mock_payment = AsyncMock(return_value=False)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_approval_payment", mock_payment):
                manager = A2ATaskManager(agent_id="agent-1")
                await manager.send_message(task_id="task-a2a-001", message=message)

        # Payment was called but failed
        mock_payment.assert_called_once()
        # update_task should NOT have been called with completed
        for call_args in mock_db.update_task.call_args_list:
            data = call_args[0][1]
            assert data.get("status") != "completed"

    @pytest.mark.asyncio
    async def test_a2a_approve_triggers_via_data_part(self):
        """
        P0-3: DataPart with action='approve' must also call PaymentDispatcher.
        """
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="submitted")
        message = _make_data_message("approve")

        mock_payment = AsyncMock(return_value=True)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_approval_payment", mock_payment):
                manager = A2ATaskManager(agent_id="agent-1")
                await manager.send_message(task_id="task-a2a-001", message=message)

        mock_payment.assert_called_once_with(task)
        mock_db.update_task.assert_called()
        update_data = mock_db.update_task.call_args[0][1]
        assert update_data["status"] == "completed"


# ============================================================================
# P0 Tests — A2A Cancel Refund Bridge
# ============================================================================


@pytest.mark.a2a_bridge
class TestA2ACancelRefundBridge:
    """Test that A2A cancel correctly triggers escrow refund."""

    @pytest.mark.asyncio
    async def test_a2a_cancel_calls_refund(self):
        """
        P0-4: cancel_task() must attempt escrow refund before updating status.
        """
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="published", escrow_status="locked")

        mock_refund = AsyncMock(return_value=True)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_cancel_refund", mock_refund):
                manager = A2ATaskManager(agent_id="agent-1")
                await manager.cancel_task(task_id="task-a2a-001")

        mock_refund.assert_called_once_with(task)
        mock_db.update_task.assert_called()
        update_data = mock_db.update_task.call_args[0][1]
        assert update_data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_a2a_cancel_no_escrow_succeeds(self):
        """
        P0-4: Tasks without escrow (fase1) should cancel successfully.
        """
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="published")  # no escrow_status

        mock_refund = AsyncMock(return_value=True)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_cancel_refund", mock_refund):
                manager = A2ATaskManager(agent_id="agent-1")
                result = await manager.cancel_task(task_id="task-a2a-001")

        # Should still call refund helper (which returns True for no-escrow)
        mock_refund.assert_called_once()
        # Task should be cancelled
        assert result is not None
        assert result.status.state.value == "canceled"

    @pytest.mark.asyncio
    async def test_a2a_cancel_refund_failure_stays_active(self):
        """
        P0-4: If escrow refund fails, task must NOT be cancelled.
        """
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="accepted", escrow_status="locked")

        mock_refund = AsyncMock(return_value=False)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_cancel_refund", mock_refund):
                manager = A2ATaskManager(agent_id="agent-1")
                result = await manager.cancel_task(task_id="task-a2a-001")

        mock_refund.assert_called_once()
        # update_task should NOT have been called with cancelled
        for call_args in mock_db.update_task.call_args_list:
            data = call_args[0][1]
            assert data.get("status") != "cancelled"
        # Result should be None (cancel failed)
        assert result is None
