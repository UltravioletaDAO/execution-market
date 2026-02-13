"""
Agent Executor MCP Tools for Execution Market (A2A)

Tools for AI agents acting as task EXECUTORS:
- em_register_as_executor: Register agent as executor
- em_browse_agent_tasks: Browse available agent tasks
- em_accept_agent_task: Accept a task
- em_submit_agent_work: Submit structured deliverables
- em_get_my_executions: Track accepted tasks
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any, List, Dict

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutorToolsConfig:
    max_capabilities: int = 20
    require_capability_match: bool = True
    auto_verification_enabled: bool = True


KNOWN_CAPABILITIES = {
    "data_processing", "web_research", "code_execution",
    "content_generation", "api_integration", "text_analysis",
    "translation", "summarization", "image_analysis",
    "document_processing", "math_computation", "data_extraction",
    "report_generation", "code_review", "testing",
    "scheduling", "email_drafting", "social_media",
    "market_research", "competitive_analysis",
}


def capabilities_match(
    executor_capabilities: List[str],
    required_capabilities: Optional[List[str]],
) -> bool:
    if not required_capabilities:
        return True
    return set(required_capabilities).issubset(set(executor_capabilities))


def _passes_auto_verification(
    result_data: Dict[str, Any],
    criteria: Dict[str, Any],
) -> tuple:
    if not criteria:
        return True, "No criteria specified"

    required_fields = criteria.get("required_fields", [])
    for field in required_fields:
        if field not in result_data:
            return False, f"Missing required field: {field}"

    min_length = criteria.get("min_length")
    if min_length:
        serialized = json.dumps(result_data)
        if len(serialized) < min_length:
            return False, f"Result too short: {len(serialized)} < {min_length}"

    required_type = criteria.get("required_type")
    if required_type:
        if required_type == "object" and not isinstance(result_data, dict):
            return False, "Expected object type"
        elif required_type == "array" and not isinstance(result_data, list):
            return False, "Expected array type"

    keywords = criteria.get("contains_keywords", [])
    if keywords:
        serialized = json.dumps(result_data).lower()
        for kw in keywords:
            if kw.lower() not in serialized:
                return False, f"Missing required keyword: {kw}"

    return True, "All criteria passed"


def format_bounty(amount: float) -> str:
    return f"${amount:.2f}"


def format_datetime(dt_str: str) -> str:
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return dt_str


def register_agent_executor_tools(
    mcp: FastMCP,
    db_module: Any,
    config: Optional[AgentExecutorToolsConfig] = None,
) -> None:
    config = config or AgentExecutorToolsConfig()

    from models import (
        RegisterAgentExecutorInput,
        BrowseAgentTasksInput,
        AcceptAgentTaskInput,
        SubmitAgentWorkInput,
        GetAgentExecutionsInput,
        ResponseFormat,
    )

    @mcp.tool(name="em_register_as_executor")
    async def em_register_as_executor(params: RegisterAgentExecutorInput) -> str:
        """Register as an agent executor on Execution Market."""
        try:
            client = db_module.get_client()
            existing = (
                client.table("executors")
                .select("id, display_name, capabilities")
                .eq("wallet_address", params.wallet_address)
                .eq("executor_type", "agent")
                .execute()
            )

            if existing.data and len(existing.data) > 0:
                executor = existing.data[0]
                updates = {"capabilities": params.capabilities, "display_name": params.display_name}
                if params.agent_card_url:
                    updates["agent_card_url"] = params.agent_card_url
                if params.mcp_endpoint_url:
                    updates["mcp_endpoint_url"] = params.mcp_endpoint_url
                client.table("executors").update(updates).eq("id", executor["id"]).execute()
                return f"# Agent Executor Updated\n\n**Executor ID**: `{executor['id']}`\n**Capabilities**: {', '.join(params.capabilities)}"

            executor_data = {
                "wallet_address": params.wallet_address,
                "display_name": params.display_name,
                "executor_type": "agent",
                "capabilities": params.capabilities,
                "status": "active",
                "reputation_score": 50,
                "tasks_completed": 0,
            }
            if params.agent_card_url:
                executor_data["agent_card_url"] = params.agent_card_url
            if params.mcp_endpoint_url:
                executor_data["mcp_endpoint_url"] = params.mcp_endpoint_url

            result = client.table("executors").insert(executor_data).execute()
            if not result.data:
                return "Error: Failed to create executor"
            executor = result.data[0]
            return f"# Agent Executor Registered\n\n**Executor ID**: `{executor['id']}`\n**Capabilities**: {', '.join(params.capabilities)}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool(name="em_browse_agent_tasks")
    async def em_browse_agent_tasks(params: BrowseAgentTasksInput) -> str:
        """Browse tasks available for agent execution."""
        try:
            client = db_module.get_client()
            query = client.table("tasks").select("*").eq("status", "published").in_("target_executor_type", ["agent", "any"])
            if params.category:
                query = query.eq("category", params.category.value)
            if params.min_bounty is not None:
                query = query.gte("bounty_usd", params.min_bounty)
            if params.max_bounty is not None:
                query = query.lte("bounty_usd", params.max_bounty)

            result = query.order("created_at", desc=True).range(params.offset, params.offset + params.limit - 1).execute()
            tasks = result.data or []

            filter_caps = params.capabilities
            if filter_caps:
                tasks = [t for t in tasks if capabilities_match(filter_caps, t.get("required_capabilities"))]

            if params.response_format == ResponseFormat.JSON:
                return json.dumps({"count": len(tasks), "tasks": tasks}, indent=2, default=str)

            if not tasks:
                return "# No Agent Tasks Available\n\nNo tasks match your criteria."

            lines = [f"# Available Agent Tasks ({len(tasks)} found)\n"]
            for task in tasks:
                lines.extend([
                    f"### {task['title']}",
                    f"- **ID**: `{task['id']}`",
                    f"- **Bounty**: {format_bounty(task.get('bounty_usd', 0))}",
                    f"- **Category**: {task.get('category', 'N/A')}",
                    f"- **Verification**: {task.get('verification_mode', 'manual')}",
                    "",
                ])
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool(name="em_accept_agent_task")
    async def em_accept_agent_task(params: AcceptAgentTaskInput) -> str:
        """Accept a task as an agent executor."""
        try:
            client = db_module.get_client()
            task = await db_module.get_task(params.task_id)
            if not task:
                return f"Error: Task {params.task_id} not found"
            if task["status"] != "published":
                return f"Error: Task not available (status: {task['status']})"

            target_type = task.get("target_executor_type", "any")
            if target_type == "human":
                return "Error: This task is only for human executors"

            try:
                exec_result = client.table("executors").select("*").eq("id", params.executor_id).single().execute()
                executor = exec_result.data
            except Exception:
                return f"Error: Executor {params.executor_id} not found"

            if executor.get("executor_type") != "agent":
                return "Error: Not registered as agent executor"

            required_caps = task.get("required_capabilities") or []
            executor_caps = executor.get("capabilities") or []
            if config.require_capability_match and required_caps:
                if not capabilities_match(executor_caps, required_caps):
                    missing = set(required_caps) - set(executor_caps)
                    return f"Error: Missing capabilities: {', '.join(missing)}"

            await db_module.update_task(params.task_id, {
                "status": "accepted",
                "executor_id": params.executor_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            })

            return f"# Task Accepted\n\n**Task**: {task['title']}\n**Bounty**: {format_bounty(task.get('bounty_usd', 0))}\n\n## Instructions\n{task.get('instructions', 'N/A')}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool(name="em_submit_agent_work")
    async def em_submit_agent_work(params: SubmitAgentWorkInput) -> str:
        """Submit completed work as an agent executor."""
        try:
            client = db_module.get_client()
            task = await db_module.get_task(params.task_id)
            if not task:
                return f"Error: Task {params.task_id} not found"
            if task.get("executor_id") != params.executor_id:
                return "Error: Not assigned to this task"
            if task["status"] not in ("accepted", "in_progress"):
                return f"Error: Cannot submit for status: {task['status']}"

            evidence = {
                params.result_type: params.result_data,
                "submission_metadata": {
                    "executor_type": "agent",
                    "result_type": params.result_type,
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                },
            }

            sub_data = {
                "task_id": params.task_id,
                "executor_id": params.executor_id,
                "evidence": evidence,
                "notes": params.notes,
                "status": "pending",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
            sub_result = client.table("submissions").insert(sub_data).execute()
            if not sub_result.data:
                return "Error: Failed to create submission"
            submission_id = sub_result.data[0]["id"]
            await db_module.update_task(params.task_id, {"status": "submitted"})

            # Auto-verification
            if task.get("verification_mode") == "auto" and config.auto_verification_enabled:
                criteria = task.get("verification_criteria", {})
                passed, reason = _passes_auto_verification(params.result_data, criteria)
                if passed:
                    client.table("submissions").update({
                        "status": "approved", "agent_verdict": "accepted",
                    }).eq("id", submission_id).execute()
                    await db_module.update_task(params.task_id, {"status": "completed"})
                    return f"# Work Submitted & Auto-Approved\n\n**Submission ID**: `{submission_id}`"
                else:
                    client.table("submissions").update({
                        "status": "rejected", "agent_verdict": "rejected",
                        "notes": f"Auto-verification failed: {reason}",
                    }).eq("id", submission_id).execute()
                    return f"# Auto-Verification Failed\n\nReason: {reason}"

            return f"# Work Submitted\n\n**Submission ID**: `{submission_id}`\nAwaiting publisher review."
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool(name="em_get_my_executions")
    async def em_get_my_executions(params: GetAgentExecutionsInput) -> str:
        """Get tasks the agent has accepted/completed."""
        try:
            client = db_module.get_client()
            query = client.table("tasks").select("*").eq("executor_id", params.executor_id)
            if params.status:
                query = query.eq("status", params.status.value)
            result = query.order("created_at", desc=True).limit(params.limit).execute()
            tasks = result.data or []

            if params.response_format == ResponseFormat.JSON:
                return json.dumps({"count": len(tasks), "tasks": tasks}, indent=2, default=str)

            if not tasks:
                return "# My Executions\n\n*No tasks found.*"

            lines = [f"# My Executions ({len(tasks)} tasks)\n"]
            for t in tasks:
                lines.append(f"- [{t['status'].upper()}] **{t['title']}** - {format_bounty(t.get('bounty_usd', 0))}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {str(e)}"

    logger.info("Agent executor tools registered (5 tools)")


__all__ = [
    "register_agent_executor_tools",
    "AgentExecutorToolsConfig",
    "KNOWN_CAPABILITIES",
    "capabilities_match",
    "_passes_auto_verification",
]
