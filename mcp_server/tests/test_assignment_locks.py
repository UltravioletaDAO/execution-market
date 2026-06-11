"""em_accept_agent_task vs the escrow marker (sign-on-assignment refusal).

Escrow-mode tasks carry a publish-time ``escrows`` marker row
(``status='pending_assignment'``, ``escrow_timing='sign_on_assignment'``).
The escrow EIP-3009 nonce = ``AuthCaptureEscrow.getHash(paymentInfo)``
INCLUDES the receiver, so a valid lock can only be signed by the publisher
FOR a chosen worker at assignment time. Self-accept therefore must REFUSE
escrow-mode tasks without mutating any state, and keep today's status-only
behavior for legacy tasks (no marker).

See MASTER_PLAN_UNIVERSAL_ESCROW_CONSISTENCY.md (Task 2.2, D2) and
ESCROW_CONSISTENCY_AUDIT_2026-06-11 (EC-06, EC-15).
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Module-level imports (collection time) so the sys.modules isolation fixture
# preserves them between tests — lazy in-test imports of mcp/pydantic get
# stripped after the first test and break generic model re-creation.
from mcp.server.fastmcp import FastMCP
import integrations.x402.escrow_lock as escrow_lock
from models import AcceptAgentTaskInput
from tools.agent_executor_tools import register_agent_executor_tools

pytestmark = pytest.mark.agent_executor

TASK_ID = "a1b2c3d4-0000-0000-0000-000000000001"
EXECUTOR_ID = "e5f6a7b8-0000-0000-0000-000000000002"

MARKER_ROW = {
    "id": "esc-0001",
    "status": "pending_assignment",
    "metadata": {"escrow_timing": "sign_on_assignment", "network": "base"},
}


# ---------------------------------------------------------------------------
# Helpers (mirroring test_agent_executor_tools.py conventions)
# ---------------------------------------------------------------------------


def _make_mcp():
    return FastMCP("test")


def _get_tool_func(mcp, tool_name):
    for tool in mcp._tool_manager._tools.values():
        if tool.name == tool_name:
            return tool.fn
    raise KeyError(f"Tool {tool_name} not found")


def _published_task():
    return {
        "id": TASK_ID,
        "status": "published",
        "target_executor_type": "agent",
        "required_capabilities": ["data_processing"],
        "title": "Escrow Gate Task",
        "bounty_usd": 5.0,
        "instructions": "Do the thing",
        "payment_network": "base",
    }


def _agent_executor():
    return {
        "id": EXECUTOR_ID,
        "capabilities": ["data_processing", "web_research"],
        "reputation_score": 80,
        "executor_type": "agent",
        "wallet_address": "0x" + "22" * 20,
    }


def _accept_fn(db_mod):
    """Register the agent executor tools and return em_accept_agent_task."""
    mcp = _make_mcp()
    register_agent_executor_tools(mcp, db_mod)
    return _get_tool_func(mcp, "em_accept_agent_task")


def _db_module():
    db_mod = MagicMock()
    db_mod.get_task = AsyncMock(return_value=_published_task())
    db_mod.update_task = AsyncMock(return_value=None)

    exec_result = MagicMock()
    exec_result.data = _agent_executor()
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = exec_result
    db_mod.get_client.return_value = mock_client
    return db_mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_refused_when_escrow_marker_exists(monkeypatch):
    """Marker present -> refuse with a clear error; NO state mutated."""
    marker_mock = AsyncMock(return_value=dict(MARKER_ROW))
    monkeypatch.setattr(escrow_lock, "get_escrow_marker", marker_mock)

    db_mod = _db_module()
    fn = _accept_fn(db_mod)

    result = await fn(AcceptAgentTaskInput(task_id=TASK_ID, executor_id=EXECUTOR_ID))

    assert result.startswith("Error")
    assert "escrow" in result.lower()
    # Points the executor at the correct path: apply, then publisher assigns.
    assert "em_apply_to_task" in result
    assert "assign" in result.lower()
    # The marker was checked for THIS task...
    marker_mock.assert_awaited_once_with(TASK_ID)
    # ...and nothing was mutated: no accept, no rollback, nothing.
    db_mod.update_task.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_passes_through_without_marker(monkeypatch):
    """No marker -> legacy status-only acceptance, unchanged behavior."""
    marker_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(escrow_lock, "get_escrow_marker", marker_mock)

    db_mod = _db_module()
    fn = _accept_fn(db_mod)

    result = await fn(AcceptAgentTaskInput(task_id=TASK_ID, executor_id=EXECUTOR_ID))

    assert "Task Accepted" in result
    marker_mock.assert_awaited_once_with(TASK_ID)
    db_mod.update_task.assert_awaited_once()
    call_args = db_mod.update_task.await_args
    assert call_args.args[0] == TASK_ID
    updates = call_args.args[1]
    assert updates["status"] == "accepted"
    assert updates["executor_id"] == EXECUTOR_ID


@pytest.mark.asyncio
async def test_gates_run_before_marker_check(monkeypatch):
    """A non-published task is rejected before the marker is even consulted
    (the refusal gate only guards the final published->accepted mutation)."""
    marker_mock = AsyncMock(return_value=dict(MARKER_ROW))
    monkeypatch.setattr(escrow_lock, "get_escrow_marker", marker_mock)

    db_mod = _db_module()
    taken = _published_task()
    taken["status"] = "accepted"
    db_mod.get_task = AsyncMock(return_value=taken)
    fn = _accept_fn(db_mod)

    result = await fn(AcceptAgentTaskInput(task_id=TASK_ID, executor_id=EXECUTOR_ID))

    assert "Error" in result
    assert "not available" in result.lower()
    marker_mock.assert_not_awaited()
    db_mod.update_task.assert_not_awaited()
