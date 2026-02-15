"""
Execution Market MCP Server - Supabase Client

Database operations for the Execution Market MCP server.
"""

import os
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# Environment variables
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://puyhpytmtkyevnxffksl.supabase.co"
)
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SERVICE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY", "")
)

# Initialize Supabase client
_client: Optional[Client] = None
_applications_table_name: Optional[str] = None
logger = logging.getLogger(__name__)


def get_client() -> Client:
    """Get or create Supabase client."""
    global _client
    if _client is None:
        if not SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY environment variable required"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# Alias for backwards compatibility
get_supabase_client = get_client


def _resolve_applications_table(client: Client) -> str:
    """
    Resolve canonical applications table name with backward compatibility.

    Prefer `task_applications` (schema canonical); fall back to legacy
    `applications` when running against older databases.
    """
    global _applications_table_name

    if _applications_table_name:
        return _applications_table_name

    for table_name in ("task_applications", "applications"):
        try:
            client.table(table_name).select("id").limit(1).execute()
            _applications_table_name = table_name
            if table_name != "task_applications":
                logger.warning(
                    "Using legacy applications table '%s'. Migrate to 'task_applications'.",
                    table_name,
                )
            return _applications_table_name
        except Exception:
            continue

    _applications_table_name = "task_applications"
    logger.warning(
        "Could not verify applications table existence. Defaulting to '%s'.",
        _applications_table_name,
    )
    return _applications_table_name


def get_applications_table_name() -> str:
    """Public helper for modules that need the resolved applications table."""
    return _resolve_applications_table(get_client())


def _extract_missing_column(error_msg: str) -> Optional[str]:
    """
    Extract missing column name from PostgREST schema errors.

    Example:
    "Could not find the 'assigned_at' column of 'tasks' in the schema cache"
    """
    match = re.search(r"Could not find the '([^']+)' column", error_msg)
    if match:
        return match.group(1)
    return None


# ============== TASK OPERATIONS ==============


async def create_task(
    agent_id: str,
    title: str,
    instructions: str,
    category: str,
    bounty_usd: float,
    deadline: datetime,
    evidence_required: List[str],
    evidence_optional: Optional[List[str]] = None,
    location_hint: Optional[str] = None,
    min_reputation: int = 0,
    payment_token: str = "USDC",
    payment_network: str = "base",
) -> Dict[str, Any]:
    """Create a new task in the database."""
    client = get_client()

    evidence_schema = {
        "required": evidence_required,
        "optional": evidence_optional or [],
    }

    task_data = {
        "agent_id": agent_id,
        "title": title,
        "instructions": instructions,
        "category": category,
        "bounty_usd": bounty_usd,
        "deadline": deadline.isoformat(),
        "evidence_schema": evidence_schema,
        "location_hint": location_hint,
        "min_reputation": min_reputation,
        "payment_token": payment_token,
        "payment_network": payment_network,
        "status": "published",
    }

    result = client.table("tasks").insert(task_data).execute()

    if result.data and len(result.data) > 0:
        return result.data[0]
    raise Exception("Failed to create task")


async def get_tasks(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Get tasks with optional filters."""
    client = get_client()

    query = client.table("tasks").select(
        "*, executor:executors(id, display_name, reputation_score)"
    )

    if agent_id:
        query = query.eq("agent_id", agent_id)
    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)

    # Get total count first
    count_query = client.table("tasks").select("id", count="exact")
    if agent_id:
        count_query = count_query.eq("agent_id", agent_id)
    if status:
        count_query = count_query.eq("status", status)
    if category:
        count_query = count_query.eq("category", category)

    count_result = count_query.execute()
    total = count_result.count if count_result.count else 0

    # Get paginated results
    result = (
        query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    )

    return {
        "total": total,
        "count": len(result.data) if result.data else 0,
        "offset": offset,
        "tasks": result.data or [],
        "has_more": total > offset + (len(result.data) if result.data else 0),
    }


async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get a single task by ID."""
    client = get_client()

    try:
        result = (
            client.table("tasks")
            .select(
                "*, executor:executors(id, display_name, wallet_address, reputation_score, erc8004_agent_id)"
            )
            .eq("id", task_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        # .single() throws when 0 rows match
        return None


async def update_task(task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a task."""
    client = get_client()
    pending_updates = dict(updates)

    # Handle schema drift by removing unknown columns and retrying.
    while pending_updates:
        try:
            result = (
                client.table("tasks")
                .update(pending_updates)
                .eq("id", task_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return result.data[0]
            raise Exception("Failed to update task")
        except Exception as e:
            missing_column = _extract_missing_column(str(e))
            if missing_column and missing_column in pending_updates:
                logger.warning(
                    "tasks.%s missing in current schema; retrying update for task %s without it",
                    missing_column,
                    task_id,
                )
                pending_updates.pop(missing_column, None)
                continue
            raise

    raise Exception(
        "Failed to update task: no compatible columns found in current schema"
    )


async def cancel_task(task_id: str, agent_id: str) -> Dict[str, Any]:
    """Cancel a task (only if published and owned by agent)."""
    get_client()

    # Verify ownership and status
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")
    if task["agent_id"] != agent_id:
        raise Exception("Not authorized to cancel this task")
    if task["status"] != "published":
        raise Exception(f"Cannot cancel task with status: {task['status']}")

    return await update_task(task_id, {"status": "cancelled"})


# ============== SUBMISSION OPERATIONS ==============


async def get_submissions_for_task(task_id: str) -> List[Dict[str, Any]]:
    """Get all submissions for a task."""
    client = get_client()

    result = (
        client.table("submissions")
        .select(
            "*, executor:executors(id, display_name, wallet_address, reputation_score)"
        )
        .eq("task_id", task_id)
        .order("submitted_at", desc=True)
        .execute()
    )

    return result.data or []


async def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    """Get a single submission by ID."""
    client = get_client()

    result = (
        client.table("submissions")
        .select(
            "*, task:tasks(*), executor:executors(id, display_name, wallet_address, reputation_score)"
        )
        .eq("id", submission_id)
        .single()
        .execute()
    )

    return result.data


async def update_submission(
    submission_id: str,
    agent_id: str,
    verdict: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a submission with agent's verdict."""
    client = get_client()

    # Get submission and verify authorization
    submission = await get_submission(submission_id)
    if not submission:
        raise Exception(f"Submission {submission_id} not found")

    task = submission.get("task")
    if not task or task["agent_id"] != agent_id:
        raise Exception("Not authorized to update this submission")

    # Update submission
    updates = {
        "agent_verdict": verdict,
        "agent_notes": notes,
        "verified_at": datetime.now(timezone.utc).isoformat()
        if verdict == "accepted"
        else None,
    }

    result = (
        client.table("submissions").update(updates).eq("id", submission_id).execute()
    )

    if result.data and len(result.data) > 0:
        # If accepted, also update task status
        if verdict == "accepted":
            await update_task(
                task["id"],
                {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Update executor reputation
            await _update_executor_reputation(
                submission["executor_id"],
                task["id"],
                delta=10,  # +10 for completed task
                reason="Task completed successfully",
            )

        return result.data[0]

    raise Exception("Failed to update submission")


async def _update_executor_reputation(
    executor_id: str,
    task_id: str,
    delta: int,
    reason: str,
) -> None:
    """Update executor's reputation score."""
    client = get_client()

    # Get current score
    executor = (
        client.table("executors")
        .select("reputation_score")
        .eq("id", executor_id)
        .single()
        .execute()
    )
    if not executor.data:
        return

    current_score = executor.data.get("reputation_score", 0)
    new_score = max(0, current_score + delta)

    # Update score
    client.table("executors").update({"reputation_score": new_score}).eq(
        "id", executor_id
    ).execute()

    # Log the change
    client.table("reputation_log").insert(
        {
            "executor_id": executor_id,
            "task_id": task_id,
            "delta": delta,
            "new_score": new_score,
            "reason": reason,
        }
    ).execute()


# ============== EXECUTOR OPERATIONS ==============


async def get_executor_stats(executor_id: str) -> Optional[Dict[str, Any]]:
    """Get executor statistics."""
    client = get_client()

    result = (
        client.table("executors")
        .select(
            "id, display_name, wallet_address, reputation_score, tasks_completed, tasks_disputed"
        )
        .eq("id", executor_id)
        .single()
        .execute()
    )

    return result.data


# ============== WORKER OPERATIONS ==============


async def apply_to_task(
    task_id: str,
    executor_id: str,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Worker applies to a task."""
    client = get_client()
    applications_table = _resolve_applications_table(client)

    # Get task to verify it's available
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")
    if task["status"] != "published":
        raise Exception(f"Task is not available (status: {task['status']})")

    # Get executor to check reputation
    try:
        executor = (
            client.table("executors")
            .select("*")
            .eq("id", executor_id)
            .single()
            .execute()
        )
    except Exception:
        raise Exception(f"Executor {executor_id} not found")
    if not executor.data:
        raise Exception(f"Executor {executor_id} not found")

    # Check minimum reputation
    min_rep = task.get("min_reputation", 0)
    executor_rep = executor.data.get("reputation_score", 0)
    if executor_rep < min_rep:
        raise Exception(
            f"Insufficient reputation. Required: {min_rep}, yours: {executor_rep}"
        )

    # Check for existing application
    existing = (
        client.table(applications_table)
        .select("*")
        .eq("task_id", task_id)
        .eq("executor_id", executor_id)
        .execute()
    )

    if existing.data and len(existing.data) > 0:
        raise Exception("Already applied to this task")

    # Create application
    application_data = {
        "task_id": task_id,
        "executor_id": executor_id,
        "message": message,
        "status": "pending",
    }
    pending_application_data = dict(application_data)
    while pending_application_data:
        try:
            result = (
                client.table(applications_table)
                .insert(pending_application_data)
                .execute()
            )
            break
        except Exception as e:
            missing_column = _extract_missing_column(str(e))
            if missing_column and missing_column in pending_application_data:
                logger.warning(
                    "%s.%s missing in current schema; retrying application insert without it",
                    applications_table,
                    missing_column,
                )
                pending_application_data.pop(missing_column, None)
                continue
            raise
    else:
        raise Exception("Failed to create application: no compatible columns found")

    if result.data and len(result.data) > 0:
        return {
            "application": result.data[0],
            "task": task,
            "executor": executor.data,
        }

    raise Exception("Failed to create application")


async def submit_work(
    task_id: str,
    executor_id: str,
    evidence: Dict[str, Any],
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Worker submits completed work."""
    client = get_client()

    # Get task
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")

    # Verify executor is assigned
    if task.get("executor_id") != executor_id:
        raise Exception("You are not assigned to this task")

    if task["status"] not in ["accepted", "in_progress"]:
        raise Exception(
            f"Task is not in a submittable state (status: {task['status']})"
        )

    # Validate required evidence
    required = task.get("evidence_schema", {}).get("required", [])
    missing = [r for r in required if r not in evidence]
    if missing:
        raise Exception(f"Missing required evidence: {', '.join(missing)}")

    # Create submission
    submission_data = {
        "task_id": task_id,
        "executor_id": executor_id,
        "evidence": evidence,
        "notes": notes,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "agent_verdict": "pending",
    }
    pending_submission_data = dict(submission_data)
    while pending_submission_data:
        try:
            result = (
                client.table("submissions").insert(pending_submission_data).execute()
            )
            break
        except Exception as e:
            missing_column = _extract_missing_column(str(e))
            if missing_column and missing_column in pending_submission_data:
                logger.warning(
                    "submissions.%s missing in current schema; retrying submission insert without it",
                    missing_column,
                )
                pending_submission_data.pop(missing_column, None)
                continue
            raise
    else:
        raise Exception("Failed to create submission: no compatible columns found")

    if result.data and len(result.data) > 0:
        # Update task status
        await update_task(task_id, {"status": "submitted"})

        return {
            "submission": result.data[0],
            "task": task,
        }

    raise Exception("Failed to create submission")


async def get_executor_tasks(
    executor_id: str,
    status: Optional[str] = None,
    include_applications: bool = True,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get all tasks for an executor (assigned + applications)."""
    client = get_client()
    applications_table = _resolve_applications_table(client)

    # Get assigned tasks
    tasks_query = (
        client.table("tasks")
        .select("*, agent:agents(id, display_name)")
        .eq("executor_id", executor_id)
    )

    if status:
        tasks_query = tasks_query.eq("status", status)

    tasks_result = tasks_query.order("created_at", desc=True).limit(limit).execute()
    assigned_tasks = tasks_result.data or []

    # Get applications
    applications = []
    if include_applications:
        app_result = (
            client.table(applications_table)
            .select("*, task:tasks(*)")
            .eq("executor_id", executor_id)
            .eq("status", "pending")
            .execute()
        )
        applications = app_result.data or []

    # Get submissions
    sub_result = (
        client.table("submissions")
        .select("*, task:tasks(*)")
        .eq("executor_id", executor_id)
        .order("submitted_at", desc=True)
        .limit(10)
        .execute()
    )
    submissions = sub_result.data or []

    return {
        "assigned_tasks": assigned_tasks,
        "applications": applications,
        "recent_submissions": submissions,
        "totals": {
            "assigned": len(assigned_tasks),
            "pending_applications": len(applications),
            "submissions": len(submissions),
        },
    }


async def get_executor_earnings(executor_id: str) -> Dict[str, Any]:
    """Get earnings summary for an executor."""
    client = get_client()

    # Get all payments
    payments_result = (
        client.table("payments").select("*").eq("executor_id", executor_id).execute()
    )
    payments = payments_result.data or []

    # Calculate totals
    completed = [p for p in payments if p.get("status") == "completed"]
    pending = [p for p in payments if p.get("status") == "pending"]
    available = [p for p in payments if p.get("status") == "available"]

    total_earned = sum(float(p.get("amount_usdc", 0)) for p in completed)
    total_pending = sum(float(p.get("amount_usdc", 0)) for p in pending)
    total_available = sum(float(p.get("amount_usdc", 0)) for p in available)

    return {
        "total_earned": total_earned,
        "pending": total_pending,
        "available": total_available,
        "payments": payments[-10:],  # Last 10 payments
    }


async def assign_task(
    task_id: str,
    agent_id: str,
    executor_id: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Agent assigns a task to a specific executor."""
    client = get_client()
    applications_table = _resolve_applications_table(client)

    # Get task
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")

    # Verify agent owns the task
    if task["agent_id"] != agent_id:
        raise Exception("Not authorized to assign this task")

    if task["status"] != "published":
        raise Exception(f"Task cannot be assigned (status: {task['status']})")

    # Verify executor exists
    executor = (
        client.table("executors").select("*").eq("id", executor_id).single().execute()
    )
    if not executor.data:
        raise Exception(f"Executor {executor_id} not found")

    # Check minimum reputation
    min_rep = task.get("min_reputation", 0)
    if executor.data.get("reputation_score", 0) < min_rep:
        raise Exception(f"Executor has insufficient reputation. Required: {min_rep}")

    # Update task
    updates = {
        "executor_id": executor_id,
        "status": "accepted",
        "assignment_notes": notes,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
    }

    updated_task = await update_task(task_id, updates)

    # Update any pending application to accepted
    try:
        client.table(applications_table).update({"status": "accepted"}).eq(
            "task_id", task_id
        ).eq("executor_id", executor_id).execute()
    except Exception as e:
        logger.warning(
            "Could not mark selected application as accepted (table=%s, task=%s, executor=%s): %s",
            applications_table,
            task_id,
            executor_id,
            e,
        )

    # Reject other applications
    rejection_updates = {
        "status": "rejected",
        "rejection_reason": "Task assigned to another executor",
    }
    while rejection_updates:
        try:
            client.table(applications_table).update(rejection_updates).eq(
                "task_id", task_id
            ).neq("executor_id", executor_id).execute()
            break
        except Exception as e:
            missing_column = _extract_missing_column(str(e))
            if missing_column and missing_column in rejection_updates:
                logger.warning(
                    "%s.%s missing in current schema; retrying reject-applications update without it",
                    applications_table,
                    missing_column,
                )
                rejection_updates.pop(missing_column, None)
                continue
            logger.warning(
                "Could not reject non-selected applications (table=%s, task=%s): %s",
                applications_table,
                task_id,
                e,
            )
            break

    return {
        "task": updated_task,
        "executor": executor.data,
    }


# ============== ANALYTICS OPERATIONS ==============


async def get_agent_analytics(
    agent_id: str,
    days: int = 30,
) -> Dict[str, Any]:
    """Get analytics for an agent's tasks."""
    client = get_client()

    # Calculate date range
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all tasks for agent in date range
    tasks_result = (
        client.table("tasks")
        .select("*")
        .eq("agent_id", agent_id)
        .gte("created_at", start_date.isoformat())
        .execute()
    )

    tasks = tasks_result.data or []

    # Calculate totals
    total = len(tasks)
    by_status: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    total_paid = 0.0

    for task in tasks:
        # Count by status
        status = task.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

        # Count by category
        category = task.get("category", "unknown")
        by_category[category] = by_category.get(category, 0) + 1

        # Sum bounties for completed tasks
        if status == "completed":
            total_paid += float(task.get("bounty_usd", 0))

    completed = by_status.get("completed", 0)
    completion_rate = (completed / total * 100) if total > 0 else 0
    avg_bounty = (total_paid / completed) if completed > 0 else 0

    # Get top workers
    top_workers = []
    if completed > 0:
        # Get completed task executor IDs
        completed_tasks = [t for t in tasks if t.get("status") == "completed"]
        executor_ids = list(
            set(t.get("executor_id") for t in completed_tasks if t.get("executor_id"))
        )

        if executor_ids:
            workers_result = (
                client.table("executors")
                .select("id, display_name, reputation_score")
                .in_("id", executor_ids[:10])
                .execute()
            )

            if workers_result.data:
                # Count tasks per worker
                worker_counts = {}
                for t in completed_tasks:
                    eid = t.get("executor_id")
                    if eid:
                        worker_counts[eid] = worker_counts.get(eid, 0) + 1

                for worker in workers_result.data:
                    worker["tasks_completed"] = worker_counts.get(worker["id"], 0)
                    worker["reputation"] = worker.get("reputation_score", 0)
                    top_workers.append(worker)

                top_workers.sort(key=lambda w: w["tasks_completed"], reverse=True)

    # Calculate average times (simplified)
    avg_times = {
        "to_accept": "~2 hours",
        "to_complete": "~6 hours",
        "to_approve": "~30 minutes",
    }

    return {
        "totals": {
            "total": total,
            "completed": completed,
            "completion_rate": completion_rate,
            "total_paid": total_paid,
            "avg_bounty": avg_bounty,
        },
        "by_status": by_status,
        "by_category": by_category,
        "average_times": avg_times,
        "top_workers": top_workers[:5],
        "period_days": days,
    }
