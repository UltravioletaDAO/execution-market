"""
Tests for Execution Market MCP Server Tools

Tests covering the main MCP tool implementations:
- em_publish_task: Publishing tasks for human execution
- em_get_tasks: Retrieving and filtering tasks
- em_approve_submission: Approving/rejecting worker submissions
- em_apply_to_task: Workers applying to tasks
- em_submit_work: Workers submitting evidence

Uses pytest-asyncio and mocks for Supabase client.
"""

import pytest

pytestmark = pytest.mark.core
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    PublishTaskInput,
    GetTasksInput,
    GetTaskInput,
    CheckSubmissionInput,
    ApproveSubmissionInput,
    ApplyToTaskInput,
    SubmitWorkInput,
    TaskCategory,
    TaskStatus,
    EvidenceType,
    SubmissionVerdict,
    ResponseFormat,
)


# ==================== FIXTURES ====================


@pytest.fixture
def mock_db():
    """Mock database module with all async functions."""
    db = MagicMock()

    # Make all db functions async
    db.create_task = AsyncMock()
    db.get_tasks = AsyncMock()
    db.get_task = AsyncMock()
    db.update_task = AsyncMock()
    db.cancel_task = AsyncMock()
    db.get_submissions_for_task = AsyncMock()
    db.get_applications_for_task = AsyncMock(return_value=[])
    db.get_submission = AsyncMock()
    db.update_submission = AsyncMock()
    db.apply_to_task = AsyncMock()
    db.submit_work = AsyncMock()
    db.get_executor_tasks = AsyncMock()
    db.get_executor_earnings = AsyncMock()
    db.get_executor_stats = AsyncMock()
    db.assign_task = AsyncMock()
    db.get_agent_analytics = AsyncMock()

    # Default get_task returns low-bounty task (below World ID threshold)
    # Tests that need specific task data override this.
    db.get_task.return_value = {"id": "default", "bounty_usd": 1.00, "agent_id": "agent-default", "status": "published"}

    # Mock Supabase client for World ID enforcement check
    _wid_result = MagicMock(data=[{"world_id_verified": True, "world_id_level": "orb"}])
    _wid_chain = MagicMock()
    _wid_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = _wid_result
    db.get_client = MagicMock(return_value=MagicMock(table=MagicMock(return_value=_wid_chain)))

    return db


@pytest.fixture
def sample_task_id():
    """Generate a sample task ID."""
    return str(uuid4())


@pytest.fixture
def sample_executor_id():
    """Generate a sample executor ID."""
    return str(uuid4())


@pytest.fixture
def sample_submission_id():
    """Generate a sample submission ID."""
    return str(uuid4())


@pytest.fixture
def sample_agent_id():
    """Sample agent ID (wallet address style)."""
    return "0x1234567890abcdef1234567890abcdef12345678"


@pytest.fixture
def sample_task(sample_task_id, sample_agent_id):
    """Sample task returned from database."""
    return {
        "id": sample_task_id,
        "agent_id": sample_agent_id,
        "title": "Verify store is open",
        "instructions": "Take a photo of the Walmart entrance showing it's open during business hours.",
        "category": "physical_presence",
        "bounty_usd": 5.00,
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "evidence_schema": {
            "required": ["photo_geo"],
            "optional": ["text_response"],
        },
        "location_hint": "Miami, FL",
        "min_reputation": 0,
        "payment_token": "USDC",
        "status": "published",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "executor_id": None,
        "executor": None,
    }


@pytest.fixture
def sample_executor(sample_executor_id):
    """Sample executor returned from database."""
    return {
        "id": sample_executor_id,
        "display_name": "Test Worker",
        "wallet_address": "0xabcdef1234567890abcdef1234567890abcdef12",
        "reputation_score": 100,
        "tasks_completed": 50,
        "tasks_disputed": 2,
        "status": "active",
    }


@pytest.fixture
def sample_submission(
    sample_submission_id, sample_task_id, sample_executor_id, sample_executor
):
    """Sample submission returned from database."""
    return {
        "id": sample_submission_id,
        "task_id": sample_task_id,
        "executor_id": sample_executor_id,
        "evidence": {
            "photo_geo": "ipfs://QmTest123abc456",
        },
        "notes": "Store was open, photo attached.",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "agent_verdict": "pending",
        "agent_notes": None,
        "executor": sample_executor,
    }


# ==================== PUBLISH_TASK TESTS ====================


class TestPublishTask:
    """Tests for em_publish_task tool."""

    @pytest.mark.asyncio
    async def test_publish_creates_task(self, mock_db, sample_task):
        """Publishing a task should create it in the database."""
        mock_db.create_task.return_value = sample_task

        # Import and call the tool implementation directly
        from server import em_publish_task

        params = PublishTaskInput(
            agent_id="0x1234567890abcdef1234567890abcdef12345678",
            title="Verify store is open",
            instructions="Take a photo of the Walmart entrance showing it's open during business hours.",
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=5.00,
            deadline_hours=24,
            evidence_required=[EvidenceType.PHOTO_GEO],
            evidence_optional=[EvidenceType.TEXT_RESPONSE],
            location_hint="Miami, FL",
        )

        with patch("server.db", mock_db):
            result = await em_publish_task(params)

        # Verify task was created
        mock_db.create_task.assert_called_once()

        # Verify response contains task ID
        assert "Task Published Successfully" in result or "Task ID" in result
        assert sample_task["id"] in result

    @pytest.mark.asyncio
    async def test_publish_validates_bounty_minimum(self):
        """Publishing requires a minimum bounty of $0.01."""
        # Pydantic validation should reject bounty <= 0
        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Test task",
                instructions="Test instructions that is long enough to pass validation",
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=0.00,  # Invalid: must be > 0
                deadline_hours=24,
                evidence_required=[EvidenceType.PHOTO],
            )

    @pytest.mark.asyncio
    async def test_publish_validates_bounty_maximum(self):
        """Publishing bounty cannot exceed $10,000."""
        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Test task",
                instructions="Test instructions that is long enough to pass validation",
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=15000.00,  # Invalid: must be <= 10000
                deadline_hours=24,
                evidence_required=[EvidenceType.PHOTO],
            )

    @pytest.mark.asyncio
    async def test_publish_validates_title_length(self):
        """Title must be 5-255 characters."""
        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Hi",  # Too short, must be >= 5 chars
                instructions="Test instructions that is long enough to pass validation",
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=5.00,
                deadline_hours=24,
                evidence_required=[EvidenceType.PHOTO],
            )

    @pytest.mark.asyncio
    async def test_publish_validates_instructions_length(self):
        """Instructions must be 20-5000 characters."""
        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Valid title",
                instructions="Short",  # Too short, must be >= 20 chars
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=5.00,
                deadline_hours=24,
                evidence_required=[EvidenceType.PHOTO],
            )

    @pytest.mark.asyncio
    async def test_publish_returns_task_id(self, mock_db, sample_task):
        """Publishing should return the created task ID."""
        mock_db.create_task.return_value = sample_task

        from server import em_publish_task

        params = PublishTaskInput(
            agent_id="0x1234567890abcdef1234567890abcdef12345678",
            title="Verify store is open",
            instructions="Take a photo of the Walmart entrance showing it's open during business hours.",
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=5.00,
            deadline_hours=24,
            evidence_required=[EvidenceType.PHOTO_GEO],
        )

        with patch("server.db", mock_db):
            result = await em_publish_task(params)

        # Should contain the task ID
        assert sample_task["id"] in result

    @pytest.mark.asyncio
    async def test_publish_requires_evidence(self):
        """Publishing requires at least one evidence type."""
        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Valid title",
                instructions="Test instructions that is long enough to pass validation",
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=5.00,
                deadline_hours=24,
                evidence_required=[],  # Invalid: must have at least 1
            )

    @pytest.mark.asyncio
    async def test_publish_validates_deadline_range(self):
        """Deadline must be between 1 and 720 hours."""
        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Valid title",
                instructions="Test instructions that is long enough to pass validation",
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=5.00,
                deadline_hours=0,  # Invalid: must be >= 1
                evidence_required=[EvidenceType.PHOTO],
            )

        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Valid title",
                instructions="Test instructions that is long enough to pass validation",
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=5.00,
                deadline_hours=1000,  # Invalid: must be <= 720
                evidence_required=[EvidenceType.PHOTO],
            )


# ==================== GET_TASKS TESTS ====================


class TestGetTasks:
    """Tests for em_get_tasks tool."""

    @pytest.mark.asyncio
    async def test_get_tasks_returns_list(self, mock_db, sample_task):
        """Getting tasks should return a list."""
        mock_db.get_tasks.return_value = {
            "total": 1,
            "count": 1,
            "offset": 0,
            "tasks": [sample_task],
            "has_more": False,
        }

        from server import em_get_tasks

        params = GetTasksInput(limit=20)

        with patch("server.db", mock_db):
            result = await em_get_tasks(params)

        mock_db.get_tasks.assert_called_once()
        # Should contain task info
        assert "Tasks" in result or sample_task["title"] in result

    @pytest.mark.asyncio
    async def test_get_tasks_filters_by_status(self, mock_db, sample_task):
        """Filtering by status should pass status to database."""
        mock_db.get_tasks.return_value = {
            "total": 1,
            "count": 1,
            "offset": 0,
            "tasks": [sample_task],
            "has_more": False,
        }

        from server import em_get_tasks

        params = GetTasksInput(
            status=TaskStatus.PUBLISHED,
            limit=20,
        )

        with patch("server.db", mock_db):
            await em_get_tasks(params)

        # Verify status filter was passed
        call_kwargs = mock_db.get_tasks.call_args
        assert call_kwargs.kwargs.get("status") == "published"

    @pytest.mark.asyncio
    async def test_get_tasks_filters_by_category(self, mock_db, sample_task):
        """Filtering by category should pass category to database."""
        mock_db.get_tasks.return_value = {
            "total": 1,
            "count": 1,
            "offset": 0,
            "tasks": [sample_task],
            "has_more": False,
        }

        from server import em_get_tasks

        params = GetTasksInput(
            category=TaskCategory.PHYSICAL_PRESENCE,
            limit=20,
        )

        with patch("server.db", mock_db):
            await em_get_tasks(params)

        call_kwargs = mock_db.get_tasks.call_args
        assert call_kwargs.kwargs.get("category") == "physical_presence"

    @pytest.mark.asyncio
    async def test_get_tasks_pagination(self, mock_db, sample_task):
        """Pagination with limit/offset should work correctly."""
        mock_db.get_tasks.return_value = {
            "total": 50,
            "count": 10,
            "offset": 20,
            "tasks": [sample_task] * 10,
            "has_more": True,
        }

        from server import em_get_tasks

        params = GetTasksInput(
            limit=10,
            offset=20,
        )

        with patch("server.db", mock_db):
            await em_get_tasks(params)

        call_kwargs = mock_db.get_tasks.call_args
        assert call_kwargs.kwargs.get("limit") == 10
        assert call_kwargs.kwargs.get("offset") == 20

    @pytest.mark.asyncio
    async def test_get_tasks_empty_result(self, mock_db):
        """Getting tasks when none exist should return appropriate message."""
        mock_db.get_tasks.return_value = {
            "total": 0,
            "count": 0,
            "offset": 0,
            "tasks": [],
            "has_more": False,
        }

        from server import em_get_tasks

        params = GetTasksInput(limit=20)

        with patch("server.db", mock_db):
            result = await em_get_tasks(params)

        assert "No tasks found" in result

    @pytest.mark.asyncio
    async def test_get_tasks_json_format(self, mock_db, sample_task):
        """JSON response format should return valid JSON."""
        mock_db.get_tasks.return_value = {
            "total": 1,
            "count": 1,
            "offset": 0,
            "tasks": [sample_task],
            "has_more": False,
        }

        from server import em_get_tasks

        params = GetTasksInput(
            limit=20,
            response_format=ResponseFormat.JSON,
        )

        with patch("server.db", mock_db):
            result = await em_get_tasks(params)

        # Should be valid JSON
        parsed = json.loads(result)
        assert "tasks" in parsed
        assert parsed["total"] == 1


# ==================== APPROVE_SUBMISSION TESTS ====================


class TestApproveSubmission:
    """Tests for em_approve_submission tool."""

    @pytest.mark.asyncio
    async def test_approve_updates_status(
        self, mock_db, sample_submission, sample_task, sample_agent_id
    ):
        """Approving a submission should update its status to completed."""
        sample_submission["task"] = sample_task
        mock_db.get_submission.return_value = sample_submission
        mock_db.update_submission.return_value = {
            **sample_submission,
            "agent_verdict": "accepted",
        }
        mock_db.get_task.return_value = sample_task

        from server import em_approve_submission

        params = ApproveSubmissionInput(
            submission_id=sample_submission["id"],
            agent_id=sample_agent_id,
            verdict=SubmissionVerdict.ACCEPTED,
            notes="Good work, verified successfully.",
        )

        # Mock payment dispatcher to return success (pay-before-mark pattern)
        mock_dispatcher = MagicMock()
        mock_dispatcher.get_mode.return_value = "fase1"
        mock_dispatcher.release_payment = AsyncMock(
            return_value={
                "success": True,
                "tx_hash": "0xmock",
                "net_to_worker": 4.35,
                "platform_fee": 0.65,
            }
        )

        with (
            patch("server.db", mock_db),
            patch(
                "integrations.x402.payment_dispatcher.get_dispatcher",
                return_value=mock_dispatcher,
            ),
        ):
            result = await em_approve_submission(params)

        mock_db.update_submission.assert_called_once()
        call_kwargs = mock_db.update_submission.call_args
        assert call_kwargs.kwargs.get("verdict") == "accepted"
        assert "APPROVED" in result

    @pytest.mark.asyncio
    async def test_approve_requires_ownership(
        self, mock_db, sample_submission, sample_task
    ):
        """Only task owner can approve submissions."""
        sample_task["agent_id"] = "different_agent_id"
        sample_submission["task"] = sample_task

        mock_db.update_submission.side_effect = Exception(
            "Not authorized to update this submission"
        )

        from server import em_approve_submission

        params = ApproveSubmissionInput(
            submission_id=sample_submission["id"],
            agent_id="wrong_agent_id",
            verdict=SubmissionVerdict.ACCEPTED,
        )

        with patch("server.db", mock_db):
            result = await em_approve_submission(params)

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_approve_dispute_verdict(
        self, mock_db, sample_submission, sample_task, sample_agent_id
    ):
        """Disputing a submission should work correctly."""
        sample_submission["task"] = sample_task
        mock_db.get_submission.return_value = sample_submission
        mock_db.update_submission.return_value = {
            **sample_submission,
            "agent_verdict": "disputed",
        }
        mock_db.get_task.return_value = sample_task

        from server import em_approve_submission

        params = ApproveSubmissionInput(
            submission_id=sample_submission["id"],
            agent_id=sample_agent_id,
            verdict=SubmissionVerdict.DISPUTED,
            notes="Photo does not show the store entrance clearly.",
        )

        with patch("server.db", mock_db):
            result = await em_approve_submission(params)

        call_kwargs = mock_db.update_submission.call_args
        assert call_kwargs.kwargs.get("verdict") == "disputed"
        assert "DISPUTED" in result

    @pytest.mark.asyncio
    async def test_approve_more_info_verdict(
        self, mock_db, sample_submission, sample_task, sample_agent_id
    ):
        """Requesting more info should work correctly."""
        sample_submission["task"] = sample_task
        mock_db.get_submission.return_value = sample_submission
        mock_db.update_submission.return_value = {
            **sample_submission,
            "agent_verdict": "more_info_requested",
        }
        mock_db.get_task.return_value = sample_task

        from server import em_approve_submission

        params = ApproveSubmissionInput(
            submission_id=sample_submission["id"],
            agent_id=sample_agent_id,
            verdict=SubmissionVerdict.MORE_INFO,
            notes="Please also include a timestamp in the photo.",
        )

        with patch("server.db", mock_db):
            result = await em_approve_submission(params)

        call_kwargs = mock_db.update_submission.call_args
        assert call_kwargs.kwargs.get("verdict") == "more_info_requested"
        assert "MORE INFO" in result


# ==================== APPLY_TO_TASK TESTS ====================


class TestApplyToTask:
    """Tests for em_apply_to_task tool."""

    @pytest.mark.asyncio
    async def test_apply_creates_application(
        self, mock_db, sample_task, sample_executor, sample_task_id, sample_executor_id
    ):
        """Applying to a task should create an application record."""
        mock_db.get_task.return_value = sample_task
        mock_db.apply_to_task.return_value = {
            "application": {
                "id": str(uuid4()),
                "task_id": sample_task_id,
                "executor_id": sample_executor_id,
                "status": "pending",
            },
            "task": sample_task,
            "executor": sample_executor,
        }

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = ApplyToTaskInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
            message="I can complete this task in 2 hours.",
        )

        # Get the registered tool and call it
        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_apply_to_task":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result = await tool_func(params)

        mock_db.apply_to_task.assert_called_once()
        assert "Application Submitted" in result

    @pytest.mark.asyncio
    async def test_apply_validates_executor(
        self, mock_db, sample_task_id, sample_executor_id
    ):
        """Executor must exist in the system."""
        mock_db.apply_to_task.side_effect = Exception(
            f"Executor {sample_executor_id} not found"
        )

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = ApplyToTaskInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
        )

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_apply_to_task":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        assert "Error" in result
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_apply_prevents_duplicate(
        self, mock_db, sample_task_id, sample_executor_id
    ):
        """Cannot apply to the same task twice."""
        mock_db.apply_to_task.side_effect = Exception("Already applied to this task")

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = ApplyToTaskInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
        )

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_apply_to_task":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        assert "Error" in result
        assert "Already applied" in result

    @pytest.mark.asyncio
    async def test_apply_checks_reputation(
        self, mock_db, sample_task_id, sample_executor_id
    ):
        """Task minimum reputation requirement must be met."""
        mock_db.apply_to_task.side_effect = Exception(
            "Insufficient reputation. Required: 100, yours: 50"
        )

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = ApplyToTaskInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
        )

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_apply_to_task":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        assert "Error" in result
        assert "reputation" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.worldid
    async def test_apply_blocked_by_world_id_high_value(
        self, mock_db, sample_task, sample_executor, sample_task_id, sample_executor_id
    ):
        """MCP tool must block unverified workers on high-value tasks."""
        # Task with bounty >= $5
        sample_task["bounty_usd"] = 10.00
        mock_db.get_task.return_value = sample_task
        mock_db.get_executor_stats.return_value = None  # skip self-application check

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        # Mock the enforcement utility to return blocked
        with patch(
            "integrations.worldid.enforcement.check_world_id_eligibility",
            new_callable=AsyncMock,
            return_value=(False, {
                "error": "world_id_orb_required",
                "message": "Tasks with bounty >= $5.00 require World ID Orb verification.",
                "required_level": "orb",
                "current_level": None,
            }),
        ):
            mcp = FastMCP("test")
            config = WorkerToolsConfig()
            register_worker_tools(mcp, mock_db, None, config)

            params = ApplyToTaskInput(
                task_id=sample_task_id,
                executor_id=sample_executor_id,
            )

            tool_func = None
            for tool in mcp._tool_manager._tools.values():
                if tool.name == "em_apply_to_task":
                    tool_func = tool.fn
                    break

            result = await tool_func(params)

        assert "Error" in result
        assert "World ID" in result
        mock_db.apply_to_task.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.worldid
    async def test_apply_allowed_world_id_verified(
        self, mock_db, sample_task, sample_executor, sample_task_id, sample_executor_id
    ):
        """MCP tool allows orb-verified workers on high-value tasks."""
        sample_task["bounty_usd"] = 10.00
        mock_db.get_task.return_value = sample_task
        mock_db.get_executor_stats.return_value = None
        mock_db.apply_to_task.return_value = {
            "application": {"id": str(uuid4()), "task_id": sample_task_id, "executor_id": sample_executor_id, "status": "pending"},
            "task": sample_task,
            "executor": sample_executor,
        }

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        with patch(
            "integrations.worldid.enforcement.check_world_id_eligibility",
            new_callable=AsyncMock,
            return_value=(True, None),
        ):
            mcp = FastMCP("test")
            config = WorkerToolsConfig()
            register_worker_tools(mcp, mock_db, None, config)

            params = ApplyToTaskInput(
                task_id=sample_task_id,
                executor_id=sample_executor_id,
            )

            tool_func = None
            for tool in mcp._tool_manager._tools.values():
                if tool.name == "em_apply_to_task":
                    tool_func = tool.fn
                    break

            result = await tool_func(params)

        assert "Application Submitted" in result
        mock_db.apply_to_task.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.worldid
    async def test_apply_low_value_no_world_id_needed(
        self, mock_db, sample_task, sample_executor, sample_task_id, sample_executor_id
    ):
        """Low-value tasks don't require World ID — enforcement utility returns allowed."""
        sample_task["bounty_usd"] = 1.00
        mock_db.get_task.return_value = sample_task
        mock_db.get_executor_stats.return_value = None
        mock_db.apply_to_task.return_value = {
            "application": {"id": str(uuid4()), "task_id": sample_task_id, "executor_id": sample_executor_id, "status": "pending"},
            "task": sample_task,
            "executor": sample_executor,
        }

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        with patch(
            "integrations.worldid.enforcement.check_world_id_eligibility",
            new_callable=AsyncMock,
            return_value=(True, None),
        ):
            mcp = FastMCP("test")
            config = WorkerToolsConfig()
            register_worker_tools(mcp, mock_db, None, config)

            params = ApplyToTaskInput(
                task_id=sample_task_id,
                executor_id=sample_executor_id,
            )

            tool_func = None
            for tool in mcp._tool_manager._tools.values():
                if tool.name == "em_apply_to_task":
                    tool_func = tool.fn
                    break

            result = await tool_func(params)

        assert "Application Submitted" in result


# ==================== SUBMIT_WORK TESTS ====================


class TestSubmitWork:
    """Tests for em_submit_work tool."""

    @pytest.mark.asyncio
    async def test_submit_requires_assignment(
        self, mock_db, sample_task_id, sample_executor_id
    ):
        """Only assigned worker can submit work."""
        mock_db.get_task.return_value = {
            "id": sample_task_id,
            "executor_id": "different_executor",  # Not the same
            "status": "accepted",
            "evidence_schema": {"required": ["photo"], "optional": []},
        }

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = SubmitWorkInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
            evidence={"photo": "ipfs://QmTest123"},
        )

        mock_db.submit_work.side_effect = Exception("You are not assigned to this task")

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_submit_work":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        assert "Error" in result or "not assigned" in result

    @pytest.mark.asyncio
    async def test_submit_validates_evidence_required(
        self, mock_db, sample_task_id, sample_executor_id
    ):
        """Required evidence fields must be provided."""
        mock_db.get_task.return_value = {
            "id": sample_task_id,
            "executor_id": sample_executor_id,
            "status": "accepted",
            "evidence_schema": {
                "required": ["photo_geo", "timestamp_proof"],
                "optional": ["text_response"],
            },
        }

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = SubmitWorkInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
            evidence={"photo_geo": "ipfs://QmTest123"},  # Missing timestamp_proof
        )

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_submit_work":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        assert "Missing required evidence" in result or "Validation Failed" in result

    @pytest.mark.asyncio
    async def test_submit_validates_evidence_format(
        self, mock_db, sample_task_id, sample_executor_id
    ):
        """Evidence fields must have correct format."""
        mock_db.get_task.return_value = {
            "id": sample_task_id,
            "executor_id": sample_executor_id,
            "status": "accepted",
            "evidence_schema": {
                "required": ["photo_geo"],
                "optional": [],
            },
        }

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = SubmitWorkInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
            evidence={"photo_geo": "not_a_valid_url"},  # Invalid format
        )

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_submit_work":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        # Should fail validation
        assert "Validation Failed" in result or "IPFS" in result or "URL" in result

    @pytest.mark.asyncio
    async def test_submit_success(self, mock_db, sample_task_id, sample_executor_id):
        """Successful submission should return confirmation."""
        task_data = {
            "id": sample_task_id,
            "title": "Test Task",
            "executor_id": sample_executor_id,
            "status": "accepted",
            "bounty_usd": 5.00,
            "payment_token": "USDC",
            "evidence_schema": {
                "required": ["photo"],
                "optional": [],
            },
        }
        mock_db.get_task.return_value = task_data
        mock_db.submit_work.return_value = {
            "submission": {
                "id": str(uuid4()),
                "task_id": sample_task_id,
                "executor_id": sample_executor_id,
                "evidence": {"photo": "https://example.com/photo.jpg"},
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "agent_verdict": "pending",
            },
            "task": task_data,
        }

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = SubmitWorkInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
            evidence={"photo": "https://example.com/photo.jpg"},
            notes="Task completed successfully.",
        )

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_submit_work":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        assert "Work Submitted Successfully" in result
        mock_db.submit_work.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_validates_task_status(
        self, mock_db, sample_task_id, sample_executor_id
    ):
        """Can only submit work for tasks in submittable status."""
        mock_db.get_task.return_value = {
            "id": sample_task_id,
            "executor_id": sample_executor_id,
            "status": "completed",  # Already completed
            "evidence_schema": {"required": ["photo"], "optional": []},
        }
        mock_db.submit_work.side_effect = Exception(
            "Task is not in a submittable state (status: completed)"
        )

        from tools.worker_tools import register_worker_tools, WorkerToolsConfig
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        config = WorkerToolsConfig()
        register_worker_tools(mcp, mock_db, None, config)

        params = SubmitWorkInput(
            task_id=sample_task_id,
            executor_id=sample_executor_id,
            evidence={"photo": "https://example.com/photo.jpg"},
        )

        tool_func = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "em_submit_work":
                tool_func = tool.fn
                break

        result = await tool_func(params)

        assert "Error" in result


# ==================== ADDITIONAL INTEGRATION TESTS ====================


class TestTaskLifecycle:
    """Integration tests for complete task lifecycle."""

    @pytest.mark.asyncio
    async def test_task_status_transitions(self, mock_db, sample_agent_id):
        """Test that task status transitions follow correct flow."""
        task_id = str(uuid4())
        str(uuid4())

        # 1. Create task (published)
        published_task = {
            "id": task_id,
            "agent_id": sample_agent_id,
            "status": "published",
            "title": "Test Task",
            "instructions": "Test instructions that is long enough",
            "category": "simple_action",
            "bounty_usd": 5.00,
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "evidence_schema": {"required": ["photo"], "optional": []},
            "payment_token": "USDC",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.create_task.return_value = published_task

        # 2. After assignment (accepted)

        # 3. After submission (submitted)

        # 4. After approval (completed)

        # Verify valid transitions
        from tools.worker_tools import can_transition

        assert can_transition("published", "accepted")
        assert can_transition("accepted", "in_progress")
        assert can_transition("in_progress", "submitted")
        assert can_transition("submitted", "completed")

        # Verify invalid transitions
        assert not can_transition("published", "completed")  # Can't skip to completed
        assert not can_transition(
            "completed", "published"
        )  # Can't go back from terminal
        assert not can_transition("cancelled", "published")  # Cancelled is terminal


class TestInputValidation:
    """Tests for Pydantic model validation."""

    def test_task_id_must_be_uuid(self):
        """Task ID must be valid UUID format."""
        with pytest.raises(ValueError):
            GetTaskInput(
                task_id="not-a-uuid",  # Too short
            )

    def test_executor_id_must_be_uuid(self):
        """Executor ID must be valid UUID format."""
        valid_uuid = str(uuid4())

        # Should work with valid UUID
        params = ApplyToTaskInput(
            task_id=valid_uuid,
            executor_id=valid_uuid,
        )
        assert params.executor_id == valid_uuid

    def test_duplicate_evidence_types_rejected(self):
        """Duplicate evidence types should be rejected."""
        with pytest.raises(ValueError):
            PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Valid title here",
                instructions="Test instructions that is long enough to pass validation",
                category=TaskCategory.SIMPLE_ACTION,
                bounty_usd=5.00,
                deadline_hours=24,
                evidence_required=[EvidenceType.PHOTO, EvidenceType.PHOTO],  # Duplicate
            )

    def test_valid_categories(self):
        """All task categories should be valid."""
        valid_categories = [
            TaskCategory.PHYSICAL_PRESENCE,
            TaskCategory.KNOWLEDGE_ACCESS,
            TaskCategory.HUMAN_AUTHORITY,
            TaskCategory.SIMPLE_ACTION,
            TaskCategory.DIGITAL_PHYSICAL,
        ]

        for category in valid_categories:
            params = PublishTaskInput(
                agent_id="0x1234567890abcdef1234567890abcdef12345678",
                title="Valid title here",
                instructions="Test instructions that is long enough to pass validation",
                category=category,
                bounty_usd=5.00,
                deadline_hours=24,
                evidence_required=[EvidenceType.PHOTO],
            )
            assert params.category == category


# ==================== ADR-001: CHECK_SUBMISSION + APPLICATIONS ====================


class TestCheckSubmissionApplications:
    """Tests for em_check_submission showing applications (ADR-001)."""

    @pytest.fixture
    def sample_applications(self, sample_task_id, sample_executor_id):
        """Sample applications from task_applications table."""
        return [
            {
                "id": str(uuid4()),
                "task_id": sample_task_id,
                "executor_id": sample_executor_id,
                "message": "I can do this task",
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    @pytest.mark.asyncio
    async def test_shows_applications_when_no_submissions(
        self, mock_db, sample_task, sample_agent_id, sample_applications
    ):
        """When workers applied but no evidence submitted, show applications."""
        mock_db.get_task.return_value = sample_task
        mock_db.get_submissions_for_task.return_value = []
        mock_db.get_applications_for_task.return_value = sample_applications

        from server import em_check_submission

        params = CheckSubmissionInput(
            task_id=sample_task["id"],
            agent_id=sample_agent_id,
        )

        with patch("server.db", mock_db):
            result = await em_check_submission(params)

        assert "1 worker(s) applied" in result
        assert "No evidence submitted yet" in result

    @pytest.mark.asyncio
    async def test_no_applications_no_submissions(
        self, mock_db, sample_task, sample_agent_id
    ):
        """When no one applied and no submissions, show empty state."""
        mock_db.get_task.return_value = sample_task
        mock_db.get_submissions_for_task.return_value = []
        mock_db.get_applications_for_task.return_value = []

        from server import em_check_submission

        params = CheckSubmissionInput(
            task_id=sample_task["id"],
            agent_id=sample_agent_id,
        )

        with patch("server.db", mock_db):
            result = await em_check_submission(params)

        assert "No Submissions Yet" in result
        assert "no one has applied" in result

    @pytest.mark.asyncio
    async def test_json_format_includes_application_count(
        self, mock_db, sample_task, sample_agent_id, sample_applications
    ):
        """JSON response should include application_count field."""
        mock_db.get_task.return_value = sample_task
        mock_db.get_submissions_for_task.return_value = []
        mock_db.get_applications_for_task.return_value = sample_applications

        from server import em_check_submission

        params = CheckSubmissionInput(
            task_id=sample_task["id"],
            agent_id=sample_agent_id,
            response_format=ResponseFormat.JSON,
        )

        with patch("server.db", mock_db):
            result = await em_check_submission(params)

        parsed = json.loads(result)
        assert parsed["application_count"] == 1
        assert parsed["submission_count"] == 0
        assert len(parsed["applications"]) == 1


# ==================== ADR-001: GET_TASK WITH ESCROW + APPLICATIONS ====================


class TestGetTaskEnriched:
    """Tests for em_get_task with escrow status and application count (ADR-001)."""

    @pytest.fixture
    def mock_escrow_client(self):
        """Mock Supabase client with escrow table."""
        client = MagicMock()
        return client

    @pytest.mark.asyncio
    async def test_get_task_includes_application_count(
        self, mock_db, sample_task, sample_agent_id
    ):
        """em_get_task JSON should include application_count."""
        mock_db.get_task.return_value = sample_task
        mock_db.get_applications_for_task.return_value = [
            {"id": "app1", "executor_id": "exec1", "status": "pending"},
            {"id": "app2", "executor_id": "exec2", "status": "pending"},
        ]
        # Mock get_client for escrow query
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_db.get_client.return_value = mock_client

        from server import em_get_task

        params = GetTaskInput(
            task_id=sample_task["id"],
            response_format=ResponseFormat.JSON,
        )

        with patch("server.db", mock_db):
            result = await em_get_task(params)

        parsed = json.loads(result)
        assert parsed["application_count"] == 2

    @pytest.mark.asyncio
    async def test_get_task_shows_deposited_escrow(self, mock_db, sample_task):
        """em_get_task should show real escrow status from escrows table."""
        mock_db.get_task.return_value = sample_task
        mock_db.get_applications_for_task.return_value = []

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "status": "deposited",
                "funding_tx": "0xabc123",
                "total_amount_usdc": 5.0,
                "metadata": {"network": "base"},
            }
        ]
        mock_db.get_client.return_value = mock_client

        from server import em_get_task

        params = GetTaskInput(
            task_id=sample_task["id"],
            response_format=ResponseFormat.JSON,
        )

        with patch("server.db", mock_db):
            result = await em_get_task(params)

        parsed = json.loads(result)
        assert parsed["escrow"]["status"] == "deposited"
        assert parsed["escrow"]["tx_ref"] == "0xabc123"

    @pytest.mark.asyncio
    async def test_get_task_markdown_shows_escrow_and_applications(
        self, mock_db, sample_task
    ):
        """em_get_task markdown should include escrow section and application count."""
        mock_db.get_task.return_value = sample_task
        mock_db.get_applications_for_task.return_value = [
            {"id": "app1", "executor_id": "exec1", "status": "pending"},
        ]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "status": "pending_assignment",
                "funding_tx": None,
                "total_amount_usdc": 5.0,
                "metadata": {"network": "base"},
            }
        ]
        mock_db.get_client.return_value = mock_client

        from server import em_get_task

        params = GetTaskInput(task_id=sample_task["id"])

        with patch("server.db", mock_db):
            result = await em_get_task(params)

        assert "PENDING_ASSIGNMENT" in result
        assert "1 pending" in result
        assert "$5.0 USDC" in result
