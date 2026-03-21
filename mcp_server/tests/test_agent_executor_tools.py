"""
Tests for Agent Executor MCP tool-level functions.

Tests register, browse, accept, submit, and get_my_executions tools
with mocked DB interactions.

Tasks 2.5 + 2.6 from MASTER_PLAN_H2A_A2A_HARDENING.md
"""

import sys
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Helpers
# ============================================================================


def _make_mcp():
    """Create a mock FastMCP that captures tool registrations."""
    from mcp.server.fastmcp import FastMCP

    return FastMCP("test")


def _register_tools(mcp, db_module=None):
    """Register agent executor tools on a mock MCP server."""
    from tools.agent_executor_tools import register_agent_executor_tools

    if db_module is None:
        db_module = MagicMock()
    register_agent_executor_tools(mcp, db_module)
    return db_module


def _get_tool_func(mcp, tool_name):
    """Get the registered async function for a tool name."""
    for tool in mcp._tool_manager._tools.values():
        if tool.name == tool_name:
            return tool.fn
    raise KeyError(f"Tool {tool_name} not found")


# ============================================================================
# Task 2.5 — Register + Browse tests
# ============================================================================


@pytest.mark.agent_executor
class TestRegisterExecutorTool:
    """Tests for em_register_as_executor MCP tool."""

    @pytest.mark.asyncio
    async def test_register_new_executor(self):
        """New wallet → creates executor, returns markdown."""
        from models import RegisterAgentExecutorInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        # No existing executor
        existing_result = MagicMock()
        existing_result.data = []
        # New insert
        insert_result = MagicMock()
        insert_result.data = [{"id": "exec-001", "display_name": "TestBot"}]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = existing_result
        mock_table.insert.return_value.execute.return_value = insert_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_register_as_executor")

        params = RegisterAgentExecutorInput(
            wallet_address="0x" + "ab" * 20,
            capabilities=["data_processing"],
            display_name="TestBot",
        )
        result = await fn(params)

        assert "exec-001" in result
        assert "Registered" in result

    @pytest.mark.asyncio
    async def test_register_updates_existing(self):
        """Existing wallet → updates, returns Updated."""
        from models import RegisterAgentExecutorInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        existing_result = MagicMock()
        existing_result.data = [
            {"id": "exec-existing", "display_name": "Old", "capabilities": ["x"]}
        ]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = existing_result
        mock_table.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_register_as_executor")

        params = RegisterAgentExecutorInput(
            wallet_address="0x" + "ab" * 20,
            capabilities=["web_research"],
            display_name="NewName",
        )
        result = await fn(params)

        assert "Updated" in result
        assert "exec-existing" in result

    @pytest.mark.asyncio
    async def test_register_unknown_capability_warns(self):
        """Unknown capability → warning in response."""
        from models import RegisterAgentExecutorInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        existing_result = MagicMock()
        existing_result.data = []
        insert_result = MagicMock()
        insert_result.data = [{"id": "exec-new"}]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = existing_result
        mock_table.insert.return_value.execute.return_value = insert_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_register_as_executor")

        params = RegisterAgentExecutorInput(
            wallet_address="0x" + "cd" * 20,
            capabilities=["custom_unknown_cap"],
            display_name="WarnBot",
        )
        result = await fn(params)

        assert "Warning" in result
        assert "custom_unknown_cap" in result

    @pytest.mark.asyncio
    async def test_register_db_error_returns_error(self):
        """DB failure → returns Error string."""
        from models import RegisterAgentExecutorInput

        mcp = _make_mcp()
        db_mod = MagicMock()
        db_mod.get_client.side_effect = Exception("Connection refused")

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_register_as_executor")

        params = RegisterAgentExecutorInput(
            wallet_address="0x" + "ef" * 20,
            capabilities=["data_processing"],
            display_name="FailBot",
        )
        result = await fn(params)

        assert "Error" in result


@pytest.mark.agent_executor
class TestBrowseAgentTasksTool:
    """Tests for em_browse_agent_tasks MCP tool."""

    @pytest.mark.asyncio
    async def test_browse_returns_tasks_markdown(self):
        """Tasks available → returns markdown listing."""
        from models import BrowseAgentTasksInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "task-1",
                "title": "Process Data",
                "bounty_usd": 5.0,
                "category": "data_processing",
                "deadline": "2026-02-19T00:00:00Z",
                "created_at": "2026-02-18T00:00:00Z",
                "required_capabilities": ["data_processing"],
            }
        ]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_browse_agent_tasks")

        params = BrowseAgentTasksInput()
        result = await fn(params)

        assert "Process Data" in result
        assert "$5.00" in result

    @pytest.mark.asyncio
    async def test_browse_no_tasks_returns_empty(self):
        """No tasks → returns no-tasks message."""
        from models import BrowseAgentTasksInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        mock_result = MagicMock()
        mock_result.data = []

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_browse_agent_tasks")

        params = BrowseAgentTasksInput()
        result = await fn(params)

        assert "No Agent Tasks" in result

    @pytest.mark.asyncio
    async def test_browse_json_format(self):
        """JSON format → returns valid JSON."""
        from models import BrowseAgentTasksInput, ResponseFormat

        mcp = _make_mcp()
        db_mod = MagicMock()

        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "t1",
                "title": "Task",
                "bounty_usd": 1.0,
                "deadline": "2026-02-19T00:00:00Z",
                "category": "research",
            }
        ]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_browse_agent_tasks")

        params = BrowseAgentTasksInput(response_format=ResponseFormat.JSON)
        result = await fn(params)

        parsed = json.loads(result)
        assert "tasks" in parsed
        assert parsed["count"] == 1


# ============================================================================
# Task 2.6 — Accept + Submit + Get tests
# ============================================================================


@pytest.mark.agent_executor
class TestAcceptAgentTaskTool:
    """Tests for em_accept_agent_task MCP tool."""

    @pytest.mark.asyncio
    async def test_accept_task_happy_path(self):
        """Valid accept → success message."""
        from models import AcceptAgentTaskInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        task_id = "a" * 36
        executor_id = "b" * 36

        # db_module.get_task is async
        db_mod.get_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": "published",
                "target_executor_type": "agent",
                "required_capabilities": ["data_processing"],
                "title": "Test Task",
                "bounty_usd": 5.0,
                "instructions": "Do the thing",
            }
        )
        db_mod.update_task = AsyncMock(return_value=None)

        # Executor lookup via client.table("executors")
        exec_result = MagicMock()
        exec_result.data = {
            "id": executor_id,
            "capabilities": ["data_processing", "web_research"],
            "reputation_score": 80,
            "executor_type": "agent",
        }

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = exec_result
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_accept_agent_task")

        params = AcceptAgentTaskInput(task_id=task_id, executor_id=executor_id)
        result = await fn(params)

        assert "Accepted" in result or "accepted" in result.lower()

    @pytest.mark.asyncio
    async def test_accept_already_taken_returns_error(self):
        """Task not published → error."""
        from models import AcceptAgentTaskInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        task_id = "c" * 36
        executor_id = "d" * 36

        db_mod.get_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": "accepted",
                "target_executor_type": "agent",
            }
        )

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_accept_agent_task")

        params = AcceptAgentTaskInput(task_id=task_id, executor_id=executor_id)
        result = await fn(params)

        assert (
            "Error" in result
            or "not available" in result.lower()
            or "already" in result.lower()
        )


@pytest.mark.agent_executor
class TestSubmitAgentWorkTool:
    """Tests for em_submit_agent_work MCP tool."""

    @pytest.mark.asyncio
    async def test_submit_work_happy_path(self):
        """Valid submission → success."""
        from models import SubmitAgentWorkInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        task_id = "e" * 36
        executor_id = "f" * 36

        # db_module.get_task is async
        db_mod.get_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": "accepted",
                "executor_id": executor_id,
                "verification_mode": "manual",
                "title": "Submit Test",
                "bounty_usd": 3.0,
            }
        )
        db_mod.update_task = AsyncMock(return_value=None)

        # Submission insert via client
        sub_insert = MagicMock()
        sub_insert.data = [{"id": "sub-001"}]

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            sub_insert
        )
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_submit_agent_work")

        params = SubmitAgentWorkInput(
            task_id=task_id,
            executor_id=executor_id,
            result_data={"analysis": "Market grew 15%"},
        )
        result = await fn(params)

        assert (
            "sub-001" in result
            or "Submitted" in result
            or "submitted" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_submit_wrong_executor_returns_error(self):
        """Submitter != assigned executor → error."""
        from models import SubmitAgentWorkInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        task_id = "g" * 36
        executor_id = "h" * 36

        db_mod.get_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": "accepted",
                "executor_id": "other-executor-id",
            }
        )

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_submit_agent_work")

        params = SubmitAgentWorkInput(
            task_id=task_id,
            executor_id=executor_id,
            result_data={"x": 1},
        )
        result = await fn(params)

        assert (
            "Error" in result
            or "not assigned" in result.lower()
            or "unauthorized" in result.lower()
        )


@pytest.mark.agent_executor
class TestGetMyExecutionsTool:
    """Tests for em_get_my_executions MCP tool."""

    @pytest.mark.asyncio
    async def test_get_executions_returns_tasks(self):
        """Executor has tasks → returns listing."""
        from models import GetAgentExecutionsInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        executor_id = "i" * 36

        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "task-x",
                "title": "My Execution",
                "status": "accepted",
                "bounty_usd": 2.0,
                "deadline": "2026-02-19T00:00:00Z",
                "created_at": "2026-02-18T00:00:00Z",
            }
        ]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_get_my_executions")

        params = GetAgentExecutionsInput(executor_id=executor_id)
        result = await fn(params)

        assert "My Execution" in result

    @pytest.mark.asyncio
    async def test_get_executions_empty(self):
        """No tasks → returns no-tasks message."""
        from models import GetAgentExecutionsInput

        mcp = _make_mcp()
        db_mod = MagicMock()

        executor_id = "j" * 36

        mock_result = MagicMock()
        mock_result.data = []

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_get_my_executions")

        params = GetAgentExecutionsInput(executor_id=executor_id)
        result = await fn(params)

        assert "No tasks found" in result

    @pytest.mark.asyncio
    async def test_get_executions_json_format(self):
        """JSON format → returns valid JSON."""
        from models import GetAgentExecutionsInput, ResponseFormat

        mcp = _make_mcp()
        db_mod = MagicMock()

        executor_id = "k" * 36

        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "task-y",
                "title": "Task Y",
                "status": "completed",
                "bounty_usd": 1.0,
            }
        ]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        db_mod.get_client.return_value = mock_client

        _register_tools(mcp, db_mod)
        fn = _get_tool_func(mcp, "em_get_my_executions")

        params = GetAgentExecutionsInput(
            executor_id=executor_id, response_format=ResponseFormat.JSON
        )
        result = await fn(params)

        parsed = json.loads(result)
        assert "tasks" in parsed


# ============================================================================
# MCP Annotations verification
# ============================================================================


@pytest.mark.agent_executor
class TestMCPAnnotations:
    """Verify all agent executor tools have MCP annotations."""

    def test_all_tools_have_annotations(self):
        """Every agent executor tool must have annotations object."""
        mcp = _make_mcp()
        _register_tools(mcp)

        agent_tools = [
            "em_register_as_executor",
            "em_browse_agent_tasks",
            "em_accept_agent_task",
            "em_submit_agent_work",
            "em_get_my_executions",
        ]

        for tool_name in agent_tools:
            found = False
            for tool in mcp._tool_manager._tools.values():
                if tool.name == tool_name:
                    found = True
                    assert tool.annotations is not None, (
                        f"{tool_name} missing annotations"
                    )
                    assert hasattr(tool.annotations, "readOnlyHint")
                    assert hasattr(tool.annotations, "destructiveHint")
                    break
            assert found, f"Tool {tool_name} not registered"

    def test_read_only_tools_marked_correctly(self):
        """Browse and get_my_executions should be readOnly=True."""
        mcp = _make_mcp()
        _register_tools(mcp)

        for tool in mcp._tool_manager._tools.values():
            if tool.name in ("em_browse_agent_tasks", "em_get_my_executions"):
                assert tool.annotations.readOnlyHint is True, (
                    f"{tool.name} should be readOnly"
                )

    def test_write_tools_marked_correctly(self):
        """Register, accept, submit should be readOnly=False."""
        mcp = _make_mcp()
        _register_tools(mcp)

        write_tools = [
            "em_register_as_executor",
            "em_accept_agent_task",
            "em_submit_agent_work",
        ]
        for tool in mcp._tool_manager._tools.values():
            if tool.name in write_tools:
                assert tool.annotations.readOnlyHint is False, (
                    f"{tool.name} should NOT be readOnly"
                )
