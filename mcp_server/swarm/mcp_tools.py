"""
Swarm MCP Tools — Expose swarm coordination as MCP tools.

These tools allow AI agents to interact with the KK V2 swarm
through the native MCP protocol (the same interface used for
task management, escrow, etc.).

Tools:
    em_swarm_status     — Get swarm fleet status and operational metrics
    em_swarm_dashboard  — Full operational dashboard with fleet details
    em_swarm_poll       — Trigger coordination cycle (ingest + route)
    em_swarm_agent_info — Get details about a specific swarm agent
    em_swarm_health     — Run and return subsystem health checks

Registration:
    from swarm.mcp_tools import register_swarm_tools
    register_swarm_tools(mcp_server, coordinator)
"""

import logging
import time
import os
from datetime import datetime, timezone

logger = logging.getLogger("em.swarm.mcp_tools")


def register_swarm_tools(mcp, coordinator=None):
    """
    Register swarm coordination tools on the MCP server.

    If coordinator is None, tools return disabled status.
    This allows graceful degradation when swarm is not enabled.
    """

    swarm_enabled = os.environ.get("SWARM_ENABLED", "false").lower() == "true"
    swarm_mode = os.environ.get("SWARM_MODE", "passive")

    @mcp.tool()
    async def em_swarm_status() -> dict:
        """
        Get swarm fleet status and operational metrics.

        Returns:
            - enabled: whether swarm coordination is active
            - mode: current operation mode (passive/semi-auto/full-auto)
            - agents: count of registered, active, degraded agents
            - tasks: count of ingested, assigned, completed, failed tasks
            - performance: success rate, avg routing time
            - bounty_earned: total USDC earned by the swarm

        Use this to check if the swarm is running and how it's performing.
        """
        if coordinator is None:
            return {
                "enabled": False,
                "message": "Swarm coordination is not enabled. Set SWARM_ENABLED=true.",
            }

        try:
            dashboard = coordinator.get_dashboard()
            metrics = coordinator.get_metrics()

            return {
                "enabled": True,
                "mode": swarm_mode,
                "agents": dashboard.get("agents", {}),
                "tasks": dashboard.get("tasks", {}),
                "performance": dashboard.get("performance", {}),
                "bounty_earned_usd": metrics.bounty_earned
                if hasattr(metrics, "bounty_earned")
                else 0,
                "success_rate": metrics.success_rate
                if hasattr(metrics, "success_rate")
                else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Swarm status error: {e}")
            return {"enabled": True, "error": str(e)}

    @mcp.tool()
    async def em_swarm_dashboard() -> dict:
        """
        Full operational dashboard with fleet details, task metrics, and config.

        Returns comprehensive view including:
            - Per-agent status (state, budget, skills, composite scores)
            - Task queue depth and processing metrics
            - Routing strategy performance
            - Budget utilization
            - System health indicators

        This is the detailed view — use em_swarm_status for a quick summary.
        """
        if coordinator is None:
            return {
                "enabled": False,
                "message": "Swarm coordination is not enabled.",
            }

        try:
            dashboard = coordinator.get_dashboard()
            dashboard["config"] = {
                "mode": swarm_mode,
                "enabled": swarm_enabled,
            }
            dashboard["timestamp"] = datetime.now(timezone.utc).isoformat()
            return dashboard
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def em_swarm_poll() -> dict:
        """
        Trigger one swarm coordination cycle.

        This runs the full pipeline:
        1. Checks EM API for new published tasks
        2. Ingests new tasks into the coordination queue
        3. Routes queued tasks to the best available agents
        4. Runs health checks on all agents
        5. Returns a summary of what happened

        In passive mode, ingests but doesn't auto-assign.
        In semi-auto mode, only assigns tasks under the bounty threshold.
        In full-auto mode, uses all routing strategies.

        Call this periodically (every 5-30 min) to keep the swarm active.
        """
        if coordinator is None:
            return {
                "enabled": False,
                "message": "Swarm coordination is not enabled.",
            }

        if swarm_mode == "passive":
            return {
                "enabled": True,
                "mode": "passive",
                "message": "Swarm is in passive mode, poll skipped. Change SWARM_MODE to semi-auto or full-auto to enable polling.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        start = time.monotonic()
        result = {
            "mode": swarm_mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "new_tasks": 0,
            "tasks_assigned": 0,
            "health_issues": [],
        }

        # Step 1: Ingest
        try:
            result["new_tasks"] = coordinator.ingest_from_api()
        except Exception as e:
            result["health_issues"].append(f"ingest: {e}")

        # Step 2: Route
        try:
            assignments = coordinator.process_task_queue(max_tasks=10)
            result["tasks_assigned"] = sum(
                1 for a in assignments if hasattr(a, "agent_id")
            )
        except Exception as e:
            result["health_issues"].append(f"routing: {e}")

        # Step 3: Health
        try:
            health = coordinator.run_health_checks()
            agents = health.get("agents", {})
            if agents.get("degraded", 0) > 0:
                result["health_issues"].append(f"degraded_agents: {agents['degraded']}")
        except Exception as e:
            result["health_issues"].append(f"health: {e}")

        result["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
        return result

    @mcp.tool()
    async def em_swarm_agent_info(agent_id: str) -> dict:
        """
        Get detailed information about a specific swarm agent.

        Args:
            agent_id: The agent's ERC-8004 ID or wallet address

        Returns:
            - state: current lifecycle state (IDLE, ACTIVE, WORKING, etc.)
            - skills: registered skill categories
            - budget: daily/monthly spend and limits
            - composite_score: reputation + skill + reliability scores
            - task history: completed, failed, current assignment
        """
        if coordinator is None:
            return {"error": "Swarm not enabled"}

        try:
            record = coordinator.lifecycle.get_agent(agent_id)
            if record is None:
                return {"error": f"Agent {agent_id} not found"}

            result = {
                "agent_id": agent_id,
                "state": record.state.name
                if hasattr(record.state, "name")
                else str(record.state),
                "skills": record.skills if hasattr(record, "skills") else [],
                "health": {
                    "is_healthy": record.health.is_healthy
                    if hasattr(record, "health")
                    else True,
                },
            }

            # Budget info
            if hasattr(record, "budget") and record.budget:
                result["budget"] = {
                    "daily_spent": record.daily_spent
                    if hasattr(record, "daily_spent")
                    else 0,
                    "monthly_spent": record.monthly_spent
                    if hasattr(record, "monthly_spent")
                    else 0,
                    "daily_limit": record.budget.daily_limit,
                    "monthly_limit": record.budget.monthly_limit,
                }

            # Composite score
            try:
                score = coordinator.reputation.compute(agent_id)
                result["composite_score"] = {
                    "total": score.total if hasattr(score, "total") else 0,
                    "tier": score.tier.name if hasattr(score, "tier") else "unknown",
                }
            except Exception:
                result["composite_score"] = None

            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def em_swarm_health() -> dict:
        """
        Run comprehensive health checks on all swarm subsystems.

        Checks:
            - Agent heartbeats and degradation detection
            - Cooldown expiry and recovery
            - Budget warnings and limits
            - Task queue stale entries
            - EM API connectivity
            - AutoJob enrichment service availability

        Returns per-subsystem health with actionable details.
        """
        if coordinator is None:
            return {
                "status": "disabled",
                "message": "Swarm not enabled",
            }

        try:
            health = coordinator.run_health_checks()
            agents = health.get("agents", {})
            systems = health.get("systems", {})

            degraded = agents.get("degraded", 0)
            unreachable = sum(
                1 for v in systems.values() if v in ("unreachable", "unavailable")
            )

            status = "healthy" if (degraded + unreachable) == 0 else "degraded"

            return {
                "status": status,
                "agents": agents,
                "tasks": health.get("tasks", {}),
                "systems": systems,
                "timestamp": health.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    logger.info("Registered 5 swarm MCP tools")
