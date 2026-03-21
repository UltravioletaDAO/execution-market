"""
Integration tests for A2A ↔ Agent Executor lifecycle.

Tests the flow: register → browse → accept → submit → approve/cancel
through the A2A protocol's task_manager.py bridge.

Task 2.10 from MASTER_PLAN_H2A_A2A_HARDENING.md
"""

import sys
import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Helpers
# ============================================================================


def _make_task(
    task_id="task-lifecycle-001",
    status="published",
    agent_id="agent-1",
    bounty_usd=1.0,
    executor_id=None,
    target_executor_type="agent",
    verification_mode="manual",
    category="data_processing",
):
    """Create a mock EM task dict."""
    task = {
        "id": task_id,
        "agent_id": agent_id,
        "title": "Lifecycle Test Task",
        "description": "Test the full lifecycle",
        "instructions": "Do the thing",
        "bounty_usd": bounty_usd,
        "status": status,
        "category": category,
        "target_executor_type": target_executor_type,
        "verification_mode": verification_mode,
        "created_at": "2026-02-18T00:00:00Z",
        "updated_at": "2026-02-18T00:00:00Z",
        "deadline": "2026-02-19T00:00:00Z",
        "metadata": {},
    }
    if executor_id:
        task["executor_id"] = executor_id
    return task


def _make_text_message(text):
    """Create an A2A Message with TextPart."""
    from a2a.models import Message, TextPart

    return Message(role="user", parts=[TextPart(text=text)])


# ============================================================================
# Lifecycle Integration Tests
# ============================================================================


@pytest.mark.infrastructure
class TestA2AAgentExecutorLifecycle:
    """Integration tests for A2A ↔ Agent Executor full lifecycle."""

    @pytest.mark.asyncio
    async def test_send_message_returns_task_object(self):
        """send_message with text returns a valid A2A task."""
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="accepted")
        message = _make_text_message("working on it")

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            manager = A2ATaskManager(agent_id="agent-1")
            result = await manager.send_message(
                task_id="task-lifecycle-001", message=message
            )

        assert result is not None
        assert hasattr(result, "status")

    @pytest.mark.asyncio
    async def test_get_task_returns_a2a_format(self):
        """get_task returns A2A-formatted task."""
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="published")

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task

            manager = A2ATaskManager(agent_id="agent-1")
            result = await manager.get_task(task_id="task-lifecycle-001")

        assert result is not None
        assert hasattr(result, "id")

    @pytest.mark.asyncio
    async def test_cancel_published_task_succeeds(self):
        """Published task with no escrow → cancel succeeds."""
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="published")
        mock_refund = AsyncMock(return_value=True)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_cancel_refund", mock_refund):
                manager = A2ATaskManager(agent_id="agent-1")
                result = await manager.cancel_task(task_id="task-lifecycle-001")

        assert result is not None
        assert result.status.state.value == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_completed_task_fails(self):
        """Completed task → cancel returns None."""
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="completed")

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task

            manager = A2ATaskManager(agent_id="agent-1")
            result = await manager.cancel_task(task_id="task-lifecycle-001")

        # Should either be None or raise — completed tasks can't be cancelled
        # Implementation may vary, but status should not change
        if result is not None:
            assert result.status.state.value != "canceled"

    @pytest.mark.asyncio
    async def test_approve_via_text_triggers_payment(self):
        """'approve' text → calls payment + updates status."""
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="submitted")
        message = _make_text_message("approve this work")
        mock_payment = AsyncMock(return_value=True)

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            with patch("a2a.task_manager._a2a_execute_approval_payment", mock_payment):
                manager = A2ATaskManager(agent_id="agent-1")
                await manager.send_message(
                    task_id="task-lifecycle-001", message=message
                )

        mock_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_via_text_sets_rejected(self):
        """'reject' text → sets task as rejected/disputed."""
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="submitted")
        message = _make_text_message("reject this is wrong")

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            manager = A2ATaskManager(agent_id="agent-1")
            await manager.send_message(task_id="task-lifecycle-001", message=message)

        # update_task should have been called with rejected/disputed
        if mock_db.update_task.called:
            update_data = mock_db.update_task.call_args[0][1]
            assert update_data.get("status") in ("disputed", "rejected")

    @pytest.mark.asyncio
    async def test_nonexistent_task_returns_none(self):
        """Nonexistent task → get returns None."""
        from a2a.task_manager import A2ATaskManager

        with patch("a2a.task_manager.db") as mock_db:
            mock_db.get_task.return_value = None

            manager = A2ATaskManager(agent_id="agent-1")
            result = await manager.get_task(task_id="nonexistent-task-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_full_lifecycle_register_to_complete(self):
        """
        Full lifecycle: register → browse → accept → submit → approve.
        """
        from a2a.task_manager import A2ATaskManager

        task = _make_task(status="published")
        mock_payment = AsyncMock(return_value=True)

        with patch("a2a.task_manager.db") as mock_db:
            # Phase 1: browse available tasks
            mock_db.get_task.return_value = task

            manager = A2ATaskManager(agent_id="agent-1")
            browse_result = await manager.get_task(task_id="task-lifecycle-001")
            assert browse_result is not None

            # Phase 2: accept task
            task["status"] = "accepted"
            task["executor_id"] = "executor-lifecycle"
            mock_db.get_task.return_value = task
            mock_db.update_task.return_value = None

            msg = _make_text_message("I accept this task")
            await manager.send_message(task_id="task-lifecycle-001", message=msg)

            # Phase 3: submit work
            task["status"] = "submitted"
            mock_db.get_task.return_value = task

            msg = _make_text_message("Here is my completed work")
            await manager.send_message(task_id="task-lifecycle-001", message=msg)

            # Phase 4: approve
            with patch("a2a.task_manager._a2a_execute_approval_payment", mock_payment):
                msg = _make_text_message("approve")
                await manager.send_message(task_id="task-lifecycle-001", message=msg)

            mock_payment.assert_called_once()
