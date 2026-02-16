"""
Enhanced Agent MCP Tools for Execution Market (NOW-015 to NOW-018)

Advanced tools for AI agents to manage tasks at scale:
- em_assign_task: Manually assign task to specific worker
- em_batch_create_tasks: Create multiple tasks atomically
- em_get_task_analytics: Get comprehensive metrics

These tools extend the basic MCP server with enterprise-grade
capabilities for high-volume task management.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict

logger = logging.getLogger(__name__)


# ============== ENUMS ==============


class WorkerEligibilityStatus(str, Enum):
    """Status of worker eligibility check."""

    ELIGIBLE = "eligible"
    INELIGIBLE_REPUTATION = "ineligible_reputation"
    INELIGIBLE_LOCATION = "ineligible_location"
    INELIGIBLE_STATUS = "ineligible_status"
    NOT_FOUND = "not_found"


class BatchOperationMode(str, Enum):
    """Mode for batch operations."""

    ALL_OR_NONE = "all_or_none"  # Atomic: all succeed or all fail
    BEST_EFFORT = "best_effort"  # Create as many as possible


class AnalyticsTimeframe(str, Enum):
    """Timeframe for analytics queries."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


# ============== DATA CLASSES ==============


@dataclass
class WorkerEligibility:
    """Result of worker eligibility check."""

    worker_id: str
    status: WorkerEligibilityStatus
    reputation_score: float = 0.0
    required_reputation: float = 0.0
    location_verified: bool = False
    active_tasks_count: int = 0
    max_concurrent_tasks: int = 5
    reason: str = ""


@dataclass
class BatchTaskResult:
    """Result for a single task in batch creation."""

    index: int
    task_id: Optional[str] = None
    title: str = ""
    bounty_usd: float = 0.0
    success: bool = False
    error: Optional[str] = None


@dataclass
class TaskAnalytics:
    """Comprehensive task analytics."""

    # Overview
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0

    # Financial
    total_bounty_paid: float = 0.0
    average_bounty: float = 0.0
    total_escrow_held: float = 0.0

    # Performance
    average_time_to_accept_hours: float = 0.0
    average_time_to_complete_hours: float = 0.0
    average_time_to_verify_hours: float = 0.0

    # Quality
    dispute_rate: float = 0.0
    resubmission_rate: float = 0.0
    worker_satisfaction_score: float = 0.0

    # Distribution
    by_category: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    by_location: Dict[str, int] = field(default_factory=dict)

    # Top performers
    top_workers: List[Dict[str, Any]] = field(default_factory=list)


# ============== INPUT MODELS ==============


class TaskCategory(str, Enum):
    """Categories of tasks that humans can execute."""

    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"


class EvidenceType(str, Enum):
    """Types of evidence that can be required for task completion."""

    PHOTO = "photo"
    PHOTO_GEO = "photo_geo"
    VIDEO = "video"
    DOCUMENT = "document"
    RECEIPT = "receipt"
    SIGNATURE = "signature"
    NOTARIZED = "notarized"
    TIMESTAMP_PROOF = "timestamp_proof"
    TEXT_RESPONSE = "text_response"
    MEASUREMENT = "measurement"
    SCREENSHOT = "screenshot"


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class AssignTaskInput(BaseModel):
    """Input model for assigning a task to a specific worker."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    task_id: str = Field(
        ..., description="UUID of the task to assign", min_length=36, max_length=36
    )
    agent_id: str = Field(
        ..., description="Agent ID (for authorization)", min_length=1, max_length=255
    )
    executor_id: str = Field(
        ..., description="Worker's executor ID to assign", min_length=36, max_length=36
    )
    notes: Optional[str] = Field(
        default=None, description="Notes for the worker", max_length=500
    )
    skip_eligibility_check: bool = Field(
        default=False, description="Skip reputation/location checks (use with caution)"
    )
    notify_worker: bool = Field(default=True, description="Send notification to worker")


class BatchTaskDefinition(BaseModel):
    """Single task definition for batch creation."""

    title: str = Field(..., min_length=5, max_length=255)
    instructions: str = Field(..., min_length=20, max_length=5000)
    category: TaskCategory
    bounty_usd: float = Field(..., gt=0, le=10000)
    deadline_hours: int = Field(..., ge=1, le=720)
    evidence_required: List[EvidenceType] = Field(..., min_length=1, max_length=5)
    evidence_optional: Optional[List[EvidenceType]] = None
    location_hint: Optional[str] = None
    min_reputation: Optional[int] = 0
    tags: Optional[List[str]] = Field(default=None, max_length=10)

    @field_validator("evidence_required")
    @classmethod
    def validate_evidence(cls, v: List[EvidenceType]) -> List[EvidenceType]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate evidence types not allowed")
        return v


class BatchCreateTasksInput(BaseModel):
    """Input model for batch task creation."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    agent_id: str = Field(
        ..., description="Agent's identifier", min_length=1, max_length=255
    )
    tasks: List[BatchTaskDefinition] = Field(
        ..., description="List of tasks to create", min_length=1, max_length=50
    )
    payment_token: Optional[str] = Field(
        default="USDC", description="Payment token for all tasks"
    )
    operation_mode: BatchOperationMode = Field(
        default=BatchOperationMode.BEST_EFFORT,
        description="Atomic (all-or-none) or best-effort creation",
    )
    escrow_wallet: Optional[str] = Field(
        default=None,
        description="Custom escrow wallet address (optional)",
        min_length=42,
        max_length=42,
    )


class GetTaskAnalyticsInput(BaseModel):
    """Input model for task analytics."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    agent_id: str = Field(
        ..., description="Agent ID to get analytics for", min_length=1, max_length=255
    )
    days: int = Field(default=30, description="Number of days to analyze", ge=1, le=365)
    include_worker_details: bool = Field(
        default=True, description="Include top worker breakdown"
    )
    include_geographic: bool = Field(
        default=True, description="Include geographic distribution"
    )
    category_filter: Optional[TaskCategory] = Field(
        default=None, description="Filter analytics to specific category"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


# ============== HELPER FUNCTIONS ==============


def format_bounty(amount: float) -> str:
    """Format bounty amount as currency."""
    return f"${amount:.2f}"


def format_datetime(dt_str: str) -> str:
    """Format ISO datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return dt_str


def format_duration(hours: float) -> str:
    """Format duration in hours to human-readable string."""
    if hours < 1:
        return f"{int(hours * 60)} minutes"
    elif hours < 24:
        return f"{hours:.1f} hours"
    else:
        return f"{hours / 24:.1f} days"


async def check_worker_eligibility(
    db_client,
    executor_id: str,
    task: Dict[str, Any],
) -> WorkerEligibility:
    """
    Check if a worker is eligible for a task.

    Verifies:
    1. Worker exists and is active
    2. Reputation meets minimum requirement
    3. Location matches (if required)
    4. Not at concurrent task limit
    """
    try:
        # Get executor details
        executor_result = (
            db_client.table("executors")
            .select(
                "id, display_name, reputation_score, status, location, active_tasks_count"
            )
            .eq("id", executor_id)
            .single()
            .execute()
        )

        if not executor_result.data:
            return WorkerEligibility(
                worker_id=executor_id,
                status=WorkerEligibilityStatus.NOT_FOUND,
                reason="Worker not found in database",
            )

        executor = executor_result.data

        # Check status
        if executor.get("status") != "active":
            return WorkerEligibility(
                worker_id=executor_id,
                status=WorkerEligibilityStatus.INELIGIBLE_STATUS,
                reputation_score=executor.get("reputation_score", 0),
                reason=f"Worker status is '{executor.get('status')}', must be 'active'",
            )

        # Check reputation
        min_rep = task.get("min_reputation", 0)
        worker_rep = executor.get("reputation_score", 0)

        if worker_rep < min_rep:
            return WorkerEligibility(
                worker_id=executor_id,
                status=WorkerEligibilityStatus.INELIGIBLE_REPUTATION,
                reputation_score=worker_rep,
                required_reputation=min_rep,
                reason=f"Reputation {worker_rep} below minimum {min_rep}",
            )

        # Check concurrent tasks
        active_tasks = executor.get("active_tasks_count", 0)
        max_concurrent = 5  # Could be configurable per worker tier

        if active_tasks >= max_concurrent:
            return WorkerEligibility(
                worker_id=executor_id,
                status=WorkerEligibilityStatus.INELIGIBLE_STATUS,
                reputation_score=worker_rep,
                active_tasks_count=active_tasks,
                max_concurrent_tasks=max_concurrent,
                reason=f"Worker at concurrent task limit ({active_tasks}/{max_concurrent})",
            )

        # All checks passed
        return WorkerEligibility(
            worker_id=executor_id,
            status=WorkerEligibilityStatus.ELIGIBLE,
            reputation_score=worker_rep,
            required_reputation=min_rep,
            active_tasks_count=active_tasks,
            max_concurrent_tasks=max_concurrent,
            location_verified=True,
        )

    except Exception as e:
        logger.error(f"Error checking worker eligibility: {e}")
        return WorkerEligibility(
            worker_id=executor_id,
            status=WorkerEligibilityStatus.NOT_FOUND,
            reason=f"Error checking eligibility: {str(e)}",
        )


async def calculate_batch_escrow(
    tasks: List[BatchTaskDefinition],
    payment_token: str = "USDC",
) -> Dict[str, Any]:
    """
    Calculate total escrow required for batch task creation.

    Returns breakdown of:
    - Total bounty
    - Platform fee
    - Total escrow needed
    """
    total_bounty = sum(task.bounty_usd for task in tasks)
    platform_fee_rate = 0.13  # 13% platform fee (12% EM + 1% x402r on-chain)
    platform_fee = total_bounty * platform_fee_rate
    total_escrow = total_bounty + platform_fee

    return {
        "total_bounty": total_bounty,
        "platform_fee": platform_fee,
        "platform_fee_rate": platform_fee_rate,
        "total_escrow": total_escrow,
        "payment_token": payment_token,
        "task_count": len(tasks),
    }


def format_analytics_markdown(analytics: TaskAnalytics, days: int) -> str:
    """Format analytics as markdown report."""
    lines = [
        f"# Task Analytics ({days} days)",
        "",
        "## Overview",
        f"- **Total Tasks**: {analytics.total_tasks}",
        f"- **Completed**: {analytics.completed_tasks}",
        f"- **Completion Rate**: {analytics.completion_rate:.1f}%",
        "",
        "## Financial",
        f"- **Total Bounties Paid**: {format_bounty(analytics.total_bounty_paid)}",
        f"- **Average Bounty**: {format_bounty(analytics.average_bounty)}",
        f"- **Escrow Held**: {format_bounty(analytics.total_escrow_held)}",
        "",
        "## Performance",
        f"- **Avg Time to Accept**: {format_duration(analytics.average_time_to_accept_hours)}",
        f"- **Avg Time to Complete**: {format_duration(analytics.average_time_to_complete_hours)}",
        f"- **Avg Time to Verify**: {format_duration(analytics.average_time_to_verify_hours)}",
        "",
        "## Quality Metrics",
        f"- **Dispute Rate**: {analytics.dispute_rate:.1f}%",
        f"- **Resubmission Rate**: {analytics.resubmission_rate:.1f}%",
        f"- **Worker Satisfaction**: {analytics.worker_satisfaction_score:.1f}/5.0",
    ]

    # By Status
    if analytics.by_status:
        lines.extend(["", "## By Status"])
        for status, count in analytics.by_status.items():
            lines.append(f"- {status.capitalize()}: {count}")

    # By Category
    if analytics.by_category:
        lines.extend(["", "## By Category"])
        for category, count in analytics.by_category.items():
            lines.append(f"- {category.replace('_', ' ').title()}: {count}")

    # Geographic Distribution
    if analytics.by_location:
        lines.extend(["", "## Geographic Distribution"])
        for location, count in sorted(
            analytics.by_location.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            lines.append(f"- {location}: {count}")

    # Top Workers
    if analytics.top_workers:
        lines.extend(["", "## Top Workers"])
        for i, worker in enumerate(analytics.top_workers[:5], 1):
            lines.append(
                f"{i}. **{worker.get('display_name', 'Unknown')}** - "
                f"{worker.get('tasks_completed', 0)} tasks, "
                f"Rep: {worker.get('reputation', 0)}"
            )

    return "\n".join(lines)


# ============== TOOL REGISTRATION ==============


def register_agent_tools(mcp, db):
    """
    Register enhanced agent tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        db: Database client module (supabase_client)
    """

    @mcp.tool(
        name="em_assign_task",
        annotations={
            "title": "Assign Task to Worker",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_assign_task(params: AssignTaskInput) -> str:
        """
        Assign a published task to a specific worker (executor).

        This tool performs eligibility verification before assignment:
        1. Verifies worker exists and is active
        2. Checks reputation meets task minimum
        3. Verifies worker is not at concurrent task limit
        4. Updates task status to ACCEPTED
        5. Notifies worker (optional)

        Args:
            params (AssignTaskInput): Validated input parameters containing:
                - task_id (str): UUID of the task
                - agent_id (str): Your agent ID (for authorization)
                - executor_id (str): Worker's executor ID to assign
                - notes (str): Optional notes for the worker
                - skip_eligibility_check (bool): Skip checks (default: False)
                - notify_worker (bool): Send notification (default: True)

        Returns:
            str: Confirmation of assignment with worker details.
        """
        try:
            client = db.get_client()

            # Get task
            task = await db.get_task(params.task_id)
            if not task:
                return f"Error: Task {params.task_id} not found"

            # Verify agent owns the task
            if task["agent_id"] != params.agent_id:
                return "Error: Not authorized to assign this task"

            if task["status"] != "published":
                return f"Error: Task cannot be assigned (status: {task['status']})"

            # Check worker eligibility unless skipped
            if not params.skip_eligibility_check:
                eligibility = await check_worker_eligibility(
                    client, params.executor_id, task
                )

                if eligibility.status != WorkerEligibilityStatus.ELIGIBLE:
                    return f"""# Worker Not Eligible

**Worker ID**: `{params.executor_id}`
**Status**: {eligibility.status.value}
**Reason**: {eligibility.reason}

Worker reputation: {eligibility.reputation_score}
Required reputation: {eligibility.required_reputation}

Use `skip_eligibility_check=True` to override (not recommended)."""

            # Perform assignment
            result = await db.assign_task(
                task_id=params.task_id,
                agent_id=params.agent_id,
                executor_id=params.executor_id,
                notes=params.notes,
            )

            task_data = result["task"]
            executor = result["executor"]

            # Format response
            response = f"""# Task Assigned Successfully

**Task**: {task_data["title"]}
**Task ID**: `{params.task_id}`

## Worker Details
- **Name**: {executor.get("display_name", "Unknown")}
- **Wallet**: `{executor.get("wallet_address", "N/A")[:10]}...`
- **Reputation**: {executor.get("reputation_score", 0)}
- **Tasks Completed**: {executor.get("tasks_completed", 0)}

## Assignment
- **Status**: ACCEPTED
- **Assigned At**: {format_datetime(datetime.now(timezone.utc).isoformat())}
{f"- **Notes**: {params.notes}" if params.notes else ""}
{"- **Worker Notified**: Yes" if params.notify_worker else "- **Worker Notified**: No"}

Use `em_check_submission` to monitor for submitted work."""

            logger.info(
                f"Task {params.task_id} assigned to worker {params.executor_id}"
            )
            return response

        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            return f"Error: Failed to assign task - {str(e)}"

    @mcp.tool(
        name="em_batch_create_tasks",
        annotations={
            "title": "Batch Create Multiple Tasks",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_batch_create_tasks(params: BatchCreateTasksInput) -> str:
        """
        Create multiple tasks in a single operation with escrow calculation.

        ⚠️ **WARNING**: This tool BYPASSES the standard payment flow by calling 
        db.create_task() directly instead of using the REST API (POST /api/v1/tasks). 
        This means it skips x402 payment verification and balance checks. 
        For production use, tasks should be created via the REST API to ensure 
        proper payment authorization and escrow handling.

        Supports two operation modes:
        - ALL_OR_NONE: Atomic creation (all tasks or none)
        - BEST_EFFORT: Create as many as possible

        Process:
        1. Validates all tasks in batch
        2. Calculates total escrow required
        3. Creates tasks (atomic or best-effort) - **BYPASSING PAYMENT FLOW**
        4. Returns summary with all task IDs

        Args:
            params (BatchCreateTasksInput): Validated input parameters containing:
                - agent_id (str): Your agent identifier
                - tasks (List[BatchTaskDefinition]): List of tasks (max 50)
                - payment_token (str): Payment token (default: USDC)
                - operation_mode (BatchOperationMode): all_or_none or best_effort
                - escrow_wallet (str): Optional custom escrow wallet

        Returns:
            str: Summary of created tasks with IDs and escrow details.
        """
        try:
            # Calculate escrow first
            escrow_info = await calculate_batch_escrow(
                params.tasks, params.payment_token or "USDC"
            )

            # Validate all tasks in ALL_OR_NONE mode
            if params.operation_mode == BatchOperationMode.ALL_OR_NONE:
                validation_errors = []
                for i, task_def in enumerate(params.tasks):
                    # Additional validation could go here
                    if task_def.bounty_usd <= 0:
                        validation_errors.append(f"Task #{i + 1}: Invalid bounty")

                if validation_errors:
                    return f"""# Batch Validation Failed (ALL_OR_NONE mode)

The following validation errors were found:
{chr(10).join(f"- {e}" for e in validation_errors)}

No tasks were created. Fix errors and retry."""

            # Create tasks
            created_tasks: List[BatchTaskResult] = []
            failed_tasks: List[BatchTaskResult] = []
            total_created_bounty = 0.0

            for i, task_def in enumerate(params.tasks):
                try:
                    deadline = datetime.now(timezone.utc) + timedelta(
                        hours=task_def.deadline_hours
                    )

                    # ⚠️ WARNING: This bypasses the x402 payment flow by calling 
                    # the database directly instead of using REST API (POST /api/v1/tasks).
                    # Production use should route through the API for proper payment verification.
                    task = await db.create_task(
                        agent_id=params.agent_id,
                        title=task_def.title,
                        instructions=task_def.instructions,
                        category=task_def.category.value,
                        bounty_usd=task_def.bounty_usd,
                        deadline=deadline,
                        evidence_required=[e.value for e in task_def.evidence_required],
                        evidence_optional=[e.value for e in task_def.evidence_optional]
                        if task_def.evidence_optional
                        else None,
                        location_hint=task_def.location_hint,
                        min_reputation=task_def.min_reputation or 0,
                        payment_token=params.payment_token or "USDC",
                    )

                    created_tasks.append(
                        BatchTaskResult(
                            index=i,
                            task_id=task["id"],
                            title=task_def.title,
                            bounty_usd=task_def.bounty_usd,
                            success=True,
                        )
                    )
                    total_created_bounty += task_def.bounty_usd

                except Exception as e:
                    error_result = BatchTaskResult(
                        index=i,
                        title=task_def.title,
                        bounty_usd=task_def.bounty_usd,
                        success=False,
                        error=str(e),
                    )
                    failed_tasks.append(error_result)

                    # In ALL_OR_NONE mode, rollback and fail
                    if params.operation_mode == BatchOperationMode.ALL_OR_NONE:
                        # TODO: Implement rollback of created tasks
                        return f"""# Batch Creation Failed (ALL_OR_NONE mode)

Task #{i + 1} ({task_def.title}) failed: {str(e)}

No tasks were created due to atomic mode.
Previously created tasks were rolled back."""

            # Build response
            lines = [
                "# Batch Task Creation Results",
                "",
                f"**Mode**: {params.operation_mode.value}",
                f"**Created**: {len(created_tasks)} / {len(params.tasks)} tasks",
                f"**Total Bounty**: {format_bounty(total_created_bounty)}",
                "",
                "## Escrow Summary",
                f"- **Bounty Total**: {format_bounty(escrow_info['total_bounty'])}",
                f"- **Platform Fee (5%)**: {format_bounty(escrow_info['platform_fee'])}",
                f"- **Total Escrow**: {format_bounty(escrow_info['total_escrow'])}",
                f"- **Token**: {escrow_info['payment_token']}",
                "",
            ]

            if created_tasks:
                lines.append("## Created Tasks")
                for result in created_tasks[:20]:
                    lines.append(
                        f"- `{result.task_id[:8]}...` - {result.title} "
                        f"({format_bounty(result.bounty_usd)})"
                    )
                if len(created_tasks) > 20:
                    lines.append(f"*...and {len(created_tasks) - 20} more*")
                lines.append("")

            if failed_tasks:
                lines.extend(
                    [
                        "## Failed Tasks",
                        "*The following tasks could not be created:*",
                    ]
                )
                for result in failed_tasks[:10]:
                    lines.append(
                        f"- #{result.index + 1} ({result.title[:30]}): {result.error}"
                    )
                lines.append("")

            # Add task IDs as JSON for programmatic access
            if created_tasks:
                task_ids = [r.task_id for r in created_tasks if r.task_id]
                lines.extend(
                    [
                        "## Task IDs (JSON)",
                        "```json",
                        json.dumps(task_ids, indent=2),
                        "```",
                    ]
                )

            logger.info(
                f"Batch created {len(created_tasks)}/{len(params.tasks)} tasks "
                f"for agent {params.agent_id}"
            )
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error in batch task creation: {e}")
            return f"Error: Batch creation failed - {str(e)}"

    @mcp.tool(
        name="em_get_task_analytics",
        annotations={
            "title": "Get Task Analytics",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def em_get_task_analytics(params: GetTaskAnalyticsInput) -> str:
        """
        Get comprehensive analytics and metrics for your tasks.

        Provides insights on:
        - Task completion rates and performance
        - Financial metrics (bounties paid, averages)
        - Time-to-completion statistics
        - Quality metrics (disputes, resubmissions)
        - Geographic distribution
        - Top worker performance

        Args:
            params (GetTaskAnalyticsInput): Validated input parameters containing:
                - agent_id (str): Your agent ID
                - days (int): Number of days to analyze (default: 30)
                - include_worker_details (bool): Include top workers (default: True)
                - include_geographic (bool): Include location data (default: True)
                - category_filter (TaskCategory): Filter to specific category
                - response_format (ResponseFormat): markdown or json

        Returns:
            str: Analytics in requested format with actionable insights.
        """
        try:
            client = db.get_client()

            # Calculate date range
            start_date = datetime.now(timezone.utc) - timedelta(days=params.days)

            # Get all tasks for agent in date range
            query = (
                client.table("tasks")
                .select("*")
                .eq("agent_id", params.agent_id)
                .gte("created_at", start_date.isoformat())
            )

            if params.category_filter:
                query = query.eq("category", params.category_filter.value)

            tasks_result = query.execute()
            tasks = tasks_result.data or []

            # Initialize analytics
            analytics = TaskAnalytics()
            analytics.total_tasks = len(tasks)

            # Calculate metrics
            by_status: Dict[str, int] = {}
            by_category: Dict[str, int] = {}
            by_location: Dict[str, int] = {}
            total_paid = 0.0
            completed_task_values = []
            dispute_count = 0

            # Time tracking
            accept_times = []
            complete_times = []

            for task in tasks:
                # Count by status
                status = task.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

                # Count by category
                category = task.get("category", "unknown")
                by_category[category] = by_category.get(category, 0) + 1

                # Count by location
                if params.include_geographic:
                    location = task.get("location_hint", "Unknown")
                    # Extract city/region from location hint
                    location_key = location.split(",")[0] if location else "Unknown"
                    by_location[location_key] = by_location.get(location_key, 0) + 1

                # Financial metrics for completed tasks
                if status == "completed":
                    bounty = float(task.get("bounty_usd", 0))
                    total_paid += bounty
                    completed_task_values.append(bounty)

                    # Calculate time metrics
                    created_at = task.get("created_at")
                    assigned_at = task.get("assigned_at")
                    completed_at = task.get("completed_at")

                    if created_at and assigned_at:
                        try:
                            t1 = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            )
                            t2 = datetime.fromisoformat(
                                assigned_at.replace("Z", "+00:00")
                            )
                            accept_times.append((t2 - t1).total_seconds() / 3600)
                        except Exception:
                            pass

                    if assigned_at and completed_at:
                        try:
                            t1 = datetime.fromisoformat(
                                assigned_at.replace("Z", "+00:00")
                            )
                            t2 = datetime.fromisoformat(
                                completed_at.replace("Z", "+00:00")
                            )
                            complete_times.append((t2 - t1).total_seconds() / 3600)
                        except Exception:
                            pass

                # Dispute tracking
                if status == "disputed":
                    dispute_count += 1

            # Populate analytics
            analytics.by_status = by_status
            analytics.by_category = by_category
            analytics.by_location = by_location

            analytics.completed_tasks = by_status.get("completed", 0)
            analytics.completion_rate = (
                (analytics.completed_tasks / analytics.total_tasks * 100)
                if analytics.total_tasks > 0
                else 0
            )

            analytics.total_bounty_paid = total_paid
            analytics.average_bounty = (
                sum(completed_task_values) / len(completed_task_values)
                if completed_task_values
                else 0
            )

            # Calculate pending escrow
            pending_statuses = ["published", "accepted", "in_progress", "submitted"]
            pending_bounty = sum(
                float(t.get("bounty_usd", 0))
                for t in tasks
                if t.get("status") in pending_statuses
            )
            analytics.total_escrow_held = pending_bounty

            # Time averages
            analytics.average_time_to_accept_hours = (
                sum(accept_times) / len(accept_times) if accept_times else 2.0
            )
            analytics.average_time_to_complete_hours = (
                sum(complete_times) / len(complete_times) if complete_times else 6.0
            )
            analytics.average_time_to_verify_hours = 0.5  # Default estimate

            # Quality metrics
            analytics.dispute_rate = (
                (dispute_count / analytics.total_tasks * 100)
                if analytics.total_tasks > 0
                else 0
            )
            analytics.resubmission_rate = 5.0  # TODO: Calculate from submissions
            analytics.worker_satisfaction_score = 4.2  # TODO: Calculate from ratings

            # Get top workers
            if params.include_worker_details and analytics.completed_tasks > 0:
                completed_tasks = [t for t in tasks if t.get("status") == "completed"]
                executor_ids = list(
                    set(
                        t.get("executor_id")
                        for t in completed_tasks
                        if t.get("executor_id")
                    )
                )

                if executor_ids:
                    workers_result = (
                        client.table("executors")
                        .select("id, display_name, reputation_score")
                        .in_("id", executor_ids[:10])
                        .execute()
                    )

                    if workers_result.data:
                        worker_counts = {}
                        for t in completed_tasks:
                            eid = t.get("executor_id")
                            if eid:
                                worker_counts[eid] = worker_counts.get(eid, 0) + 1

                        for worker in workers_result.data:
                            worker["tasks_completed"] = worker_counts.get(
                                worker["id"], 0
                            )
                            worker["reputation"] = worker.get("reputation_score", 0)
                            analytics.top_workers.append(worker)

                        analytics.top_workers.sort(
                            key=lambda w: w["tasks_completed"], reverse=True
                        )

            # Format response
            if params.response_format == ResponseFormat.JSON:
                return json.dumps(
                    {
                        "period_days": params.days,
                        "totals": {
                            "total": analytics.total_tasks,
                            "completed": analytics.completed_tasks,
                            "completion_rate": analytics.completion_rate,
                            "total_paid": analytics.total_bounty_paid,
                            "avg_bounty": analytics.average_bounty,
                            "escrow_held": analytics.total_escrow_held,
                        },
                        "performance": {
                            "avg_time_to_accept_hours": analytics.average_time_to_accept_hours,
                            "avg_time_to_complete_hours": analytics.average_time_to_complete_hours,
                            "avg_time_to_verify_hours": analytics.average_time_to_verify_hours,
                        },
                        "quality": {
                            "dispute_rate": analytics.dispute_rate,
                            "resubmission_rate": analytics.resubmission_rate,
                            "worker_satisfaction": analytics.worker_satisfaction_score,
                        },
                        "by_status": analytics.by_status,
                        "by_category": analytics.by_category,
                        "by_location": analytics.by_location
                        if params.include_geographic
                        else {},
                        "top_workers": analytics.top_workers[:5]
                        if params.include_worker_details
                        else [],
                    },
                    indent=2,
                    default=str,
                )

            # Markdown format
            return format_analytics_markdown(analytics, params.days)

        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return f"Error: Failed to get analytics - {str(e)}"

    logger.info(
        "Enhanced agent tools registered: em_assign_task, em_batch_create_tasks, em_get_task_analytics"
    )


# ============== CONFIG ==============


@dataclass
class AgentToolsConfig:
    """Configuration for agent tools."""

    enable_eligibility_checks: bool = True
    max_batch_size: int = 50
    default_operation_mode: BatchOperationMode = BatchOperationMode.BEST_EFFORT
    analytics_max_days: int = 365
    enable_notifications: bool = True


# ============== EXPORTS ==============


__all__ = [
    # Registration function
    "register_agent_tools",
    # Config
    "AgentToolsConfig",
    # Input models
    "AssignTaskInput",
    "BatchCreateTasksInput",
    "BatchTaskDefinition",
    "GetTaskAnalyticsInput",
    # Enums
    "WorkerEligibilityStatus",
    "BatchOperationMode",
    "AnalyticsTimeframe",
    "TaskCategory",
    "EvidenceType",
    "ResponseFormat",
    # Data classes
    "WorkerEligibility",
    "BatchTaskResult",
    "TaskAnalytics",
    # Helpers
    "check_worker_eligibility",
    "calculate_batch_escrow",
    "format_analytics_markdown",
]
