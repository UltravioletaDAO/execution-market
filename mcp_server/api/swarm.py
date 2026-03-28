"""
Swarm API Routes — KK V2 Swarm Coordination REST Endpoints

Provides HTTP endpoints for swarm management, monitoring, and operations.
These endpoints expose the swarm coordinator's capabilities through the
standard EM REST API.

Routes:
    GET  /api/v1/swarm/status    — Fleet overview and metrics
    GET  /api/v1/swarm/health    — Subsystem health checks
    GET  /api/v1/swarm/agents    — List registered agents with state
    GET  /api/v1/swarm/agents/{agent_id} — Single agent details
    POST /api/v1/swarm/poll      — Trigger one poll cycle (ingest + route)
    GET  /api/v1/swarm/dashboard — Full operational dashboard
    GET  /api/v1/swarm/metrics   — Numeric metrics for monitoring
    POST /api/v1/swarm/config    — Update swarm configuration
    GET  /api/v1/swarm/events    — Recent coordinator events
    GET  /api/v1/swarm/tasks     — Swarm task queue status
    POST /api/v1/swarm/agents/{agent_id}/activate   — Activate an agent
    POST /api/v1/swarm/agents/{agent_id}/suspend     — Suspend an agent
    POST /api/v1/swarm/agents/{agent_id}/budget      — Update agent budget

Authentication:
    All endpoints require admin API key (X-API-Key header).
    Read endpoints: any valid API key.
    Write endpoints (poll, config, activate, suspend): admin tier only.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Path
from pydantic import BaseModel, Field

from .auth import verify_api_key, APIKeyData
from .admin import verify_admin_key

logger = logging.getLogger("em.api.swarm")

router = APIRouter(prefix="/api/v1/swarm", tags=["swarm"])


# ─── Configuration ────────────────────────────────────────────────────────────

EM_API_URL = os.environ.get("EM_API_URL", "https://api.execution.market")
AUTOJOB_URL = os.environ.get("AUTOJOB_URL", "http://localhost:8765")
SWARM_ENABLED = os.environ.get("SWARM_ENABLED", "false").lower() == "true"
SWARM_MODE = os.environ.get("SWARM_MODE", "passive")  # passive | semi-auto | full-auto
SWARM_DAILY_BUDGET = float(os.environ.get("SWARM_DAILY_BUDGET", "10.0"))
SWARM_MAX_TASK_BOUNTY = float(os.environ.get("SWARM_MAX_TASK_BOUNTY", "1.0"))


# ─── Singleton Coordinator ────────────────────────────────────────────────────

_coordinator = None
_coordinator_initialized = False


def get_coordinator():
    """
    Lazy-initialize the swarm coordinator singleton.
    Returns None if swarm is disabled or import fails.
    """
    global _coordinator, _coordinator_initialized

    if _coordinator_initialized:
        return _coordinator

    _coordinator_initialized = True

    if not SWARM_ENABLED:
        logger.info("Swarm disabled (SWARM_ENABLED != true)")
        return None

    try:
        from swarm import SwarmCoordinator

        _coordinator = SwarmCoordinator.create(
            em_api_url=EM_API_URL,
            autojob_url=AUTOJOB_URL,
        )
        logger.info(f"Swarm coordinator initialized (mode={SWARM_MODE})")
        return _coordinator
    except Exception as e:
        logger.error(f"Failed to initialize swarm coordinator: {e}")
        _coordinator = None
        return None


def require_coordinator():
    """Get coordinator or raise 503."""
    coord = get_coordinator()
    if coord is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "swarm_disabled",
                "message": "Swarm coordination is not enabled. Set SWARM_ENABLED=true.",
                "swarm_enabled": SWARM_ENABLED,
            },
        )
    return coord


async def require_admin(
    authorization: Optional[str] = Header(None, description="Bearer admin key"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    x_admin_actor: Optional[str] = Header(None, alias="X-Admin-Actor"),
    admin_key: Optional[str] = Query(None, alias="admin_key"),
):
    """Require admin key for write operations (delegates to admin.verify_admin_key)."""
    return await verify_admin_key(
        authorization=authorization,
        x_admin_key=x_admin_key,
        x_admin_actor=x_admin_actor,
        admin_key=admin_key,
    )


# ─── Request/Response Models ──────────────────────────────────────────────────


class SwarmConfigUpdate(BaseModel):
    """Swarm configuration update request."""

    mode: Optional[str] = Field(
        None, description="Swarm mode: passive | semi-auto | full-auto"
    )
    daily_budget: Optional[float] = Field(
        None, ge=0, description="Daily budget cap (USD)"
    )
    max_task_bounty: Optional[float] = Field(
        None, ge=0, description="Max bounty per task (USD)"
    )
    autojob_url: Optional[str] = Field(
        None, description="AutoJob enrichment service URL"
    )


class BudgetUpdate(BaseModel):
    """Agent budget update request."""

    daily_limit: Optional[float] = Field(
        None, ge=0, description="Daily spending limit (USD)"
    )
    monthly_limit: Optional[float] = Field(
        None, ge=0, description="Monthly spending limit (USD)"
    )


class AgentActivation(BaseModel):
    """Agent activation parameters."""

    skills: Optional[List[str]] = Field(
        None, description="Skill categories this agent can handle"
    )
    daily_budget: Optional[float] = Field(None, ge=0, description="Daily budget (USD)")


class PollResult(BaseModel):
    """Result of a poll cycle."""

    new_tasks_ingested: int = 0
    tasks_assigned: int = 0
    health_issues: List[str] = Field(default_factory=list)
    duration_ms: float = 0
    mode: str = "passive"
    timestamp: str = ""


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/status")
async def swarm_status(api_key: APIKeyData = Depends(verify_api_key)):
    """
    Get swarm fleet overview.

    Returns high-level status even when swarm is disabled,
    so operators can see configuration state.
    """
    coord = get_coordinator()

    base_status = {
        "swarm_enabled": SWARM_ENABLED,
        "mode": SWARM_MODE,
        "daily_budget": SWARM_DAILY_BUDGET,
        "max_task_bounty": SWARM_MAX_TASK_BOUNTY,
        "autojob_url": AUTOJOB_URL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if coord is None:
        base_status["coordinator"] = "not_initialized"
        base_status["agents"] = {"registered": 0, "active": 0}
        return base_status

    try:
        dashboard = coord.get_dashboard()
        base_status["coordinator"] = "active"
        base_status["agents"] = dashboard.get("agents", {})
        base_status["tasks"] = dashboard.get("tasks", {})
        base_status["performance"] = dashboard.get("performance", {})
        return base_status
    except Exception as e:
        logger.exception(f"Error getting swarm status: {e}")
        base_status["coordinator"] = "error"
        base_status["error"] = "Failed to retrieve coordinator status"
        return base_status


@router.get("/health")
async def swarm_health(api_key: APIKeyData = Depends(verify_api_key)):
    """
    Run health checks on all swarm subsystems.

    Returns per-component health status with actionable details.
    """
    coord = get_coordinator()

    if coord is None:
        return {
            "status": "disabled",
            "message": "Swarm is not enabled",
            "checks": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        health = coord.run_health_checks()
        # Determine overall status from the health report dict
        agents = health.get("agents", {})
        systems = health.get("systems", {})
        degraded_count = agents.get("degraded", 0)
        unreachable = sum(
            1 for v in systems.values() if v in ("unreachable", "unavailable")
        )
        total_issues = degraded_count + unreachable

        status = (
            "healthy"
            if total_issues == 0
            else "degraded"
            if total_issues < 3
            else "unhealthy"
        )

        return {
            "status": status,
            "report": health,
            "issues_count": total_issues,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception(f"Health check error: {e}")
        return {
            "status": "error",
            "error": "Health check failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/agents")
async def list_agents(
    state: Optional[str] = Query(
        None, description="Filter by state: IDLE, ACTIVE, WORKING, etc."
    ),
    include_scores: bool = Query(False, description="Include composite scores"),
    api_key: APIKeyData = Depends(verify_api_key),
):
    """
    List all registered swarm agents with current state and budget.
    """
    coord = require_coordinator()

    try:
        dashboard = coord.get_dashboard()
        fleet = dashboard.get("fleet", [])

        # Filter by state if requested
        if state:
            state_upper = state.upper()
            fleet = [a for a in fleet if a.get("state", "").upper() == state_upper]

        # Optionally include composite scores
        if include_scores:
            for agent in fleet:
                agent_id = agent.get("agent_id", "")
                try:
                    score = coord.reputation.compute(agent_id)
                    agent["composite_score"] = {
                        "total": score.total if hasattr(score, "total") else 0,
                        "skill": score.skill if hasattr(score, "skill") else 0,
                        "reputation": score.reputation
                        if hasattr(score, "reputation")
                        else 0,
                        "reliability": score.reliability
                        if hasattr(score, "reliability")
                        else 0,
                    }
                except Exception:
                    agent["composite_score"] = None

        return {
            "agents": fleet,
            "total": len(fleet),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str = Path(..., description="Agent ID (ERC-8004 or wallet address)"),
    api_key: APIKeyData = Depends(verify_api_key),
):
    """
    Get detailed information about a specific swarm agent.
    """
    coord = require_coordinator()

    try:
        # Get from lifecycle manager
        record = coord.lifecycle.get_agent(agent_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        result = {
            "agent_id": agent_id,
            "state": record.state.name
            if hasattr(record.state, "name")
            else str(record.state),
            "skills": record.skills if hasattr(record, "skills") else [],
            "budget": {
                "daily_spent": record.daily_spent
                if hasattr(record, "daily_spent")
                else 0,
                "monthly_spent": record.monthly_spent
                if hasattr(record, "monthly_spent")
                else 0,
                "daily_limit": record.budget.daily_limit
                if hasattr(record, "budget") and record.budget
                else None,
                "monthly_limit": record.budget.monthly_limit
                if hasattr(record, "budget") and record.budget
                else None,
            },
            "last_heartbeat": record.last_heartbeat
            if hasattr(record, "last_heartbeat")
            else None,
            "tasks_completed": record.tasks_completed
            if hasattr(record, "tasks_completed")
            else 0,
            "tasks_failed": record.tasks_failed
            if hasattr(record, "tasks_failed")
            else 0,
        }

        # Try to get composite score
        try:
            score = coord.reputation.compute(agent_id)
            result["composite_score"] = {
                "total": score.total if hasattr(score, "total") else 0,
                "skill": score.skill if hasattr(score, "skill") else 0,
                "reputation": score.reputation if hasattr(score, "reputation") else 0,
                "reliability": score.reliability
                if hasattr(score, "reliability")
                else 0,
                "tier": score.tier.name if hasattr(score, "tier") else "unknown",
            }
        except Exception:
            result["composite_score"] = None

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/poll")
async def trigger_poll(
    api_key: APIKeyData = Depends(require_admin),
):
    """
    Trigger one poll cycle: ingest new tasks from EM API and route them.

    In passive mode, ingests but doesn't auto-assign.
    In semi-auto mode, auto-assigns tasks under max_task_bounty.
    In full-auto mode, uses all routing strategies.
    """
    coord = require_coordinator()
    start = time.monotonic()

    try:
        result = PollResult(
            mode=SWARM_MODE,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Step 1: Ingest new tasks from API
        try:
            new_tasks = coord.ingest_from_api()
            result.new_tasks_ingested = new_tasks
        except Exception as e:
            logger.warning(f"Task ingestion failed: {e}")
            result.health_issues.append(f"ingestion_error: {e}")

        # Step 2: Route tasks based on mode
        if SWARM_MODE == "passive":
            # Passive mode: ingest only, no auto-assignment
            result.tasks_assigned = 0
        else:
            # Semi-auto or full-auto: process queued tasks
            try:
                assignments = coord.process_task_queue(max_tasks=10)
                # Count successful assignments (not RoutingFailure)
                result.tasks_assigned = sum(
                    1
                    for a in assignments
                    if hasattr(
                        a, "agent_id"
                    )  # Assignment has agent_id, RoutingFailure doesn't
                )
            except Exception as e:
                logger.warning(f"Task routing failed: {e}")
                result.health_issues.append(f"routing_error: {e}")

        # Step 3: Run health checks
        try:
            health = coord.run_health_checks()
            agents = health.get("agents", {})
            if agents.get("degraded", 0) > 0:
                result.health_issues.append(f"degraded_agents: {agents['degraded']}")
            systems = health.get("systems", {})
            for sys_name, sys_status in systems.items():
                if sys_status in ("unreachable", "unavailable"):
                    result.health_issues.append(f"{sys_name}: {sys_status}")
        except Exception as e:
            result.health_issues.append(f"health_check_error: {e}")

        result.duration_ms = round((time.monotonic() - start) * 1000, 2)
        return result.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Poll cycle failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dashboard")
async def swarm_dashboard(api_key: APIKeyData = Depends(verify_api_key)):
    """
    Full operational dashboard with fleet details, task metrics, and performance.

    This is the comprehensive view for operators — combines status, agents,
    tasks, and metrics in a single response.
    """
    coord = require_coordinator()

    try:
        dashboard = coord.get_dashboard()

        # Enrich with API-level config
        dashboard["config"] = {
            "mode": SWARM_MODE,
            "daily_budget": SWARM_DAILY_BUDGET,
            "max_task_bounty": SWARM_MAX_TASK_BOUNTY,
            "autojob_url": AUTOJOB_URL,
            "swarm_enabled": SWARM_ENABLED,
        }
        dashboard["timestamp"] = datetime.now(timezone.utc).isoformat()

        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics")
async def swarm_metrics(api_key: APIKeyData = Depends(verify_api_key)):
    """
    Numeric metrics suitable for Prometheus/Grafana scraping.

    Returns flat key-value pairs for easy integration with monitoring.
    """
    coord = get_coordinator()

    if coord is None:
        return {
            "swarm_enabled": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        metrics = coord.get_metrics()
        flat = {
            "swarm_enabled": 1,
            "agents_registered": metrics.agents_registered
            if hasattr(metrics, "agents_registered")
            else 0,
            "agents_active": metrics.agents_active
            if hasattr(metrics, "agents_active")
            else 0,
            "agents_degraded": metrics.agents_degraded
            if hasattr(metrics, "agents_degraded")
            else 0,
            "agents_suspended": metrics.agents_suspended
            if hasattr(metrics, "agents_suspended")
            else 0,
            "tasks_ingested": metrics.tasks_ingested
            if hasattr(metrics, "tasks_ingested")
            else 0,
            "tasks_assigned": metrics.tasks_assigned
            if hasattr(metrics, "tasks_assigned")
            else 0,
            "tasks_completed": metrics.tasks_completed
            if hasattr(metrics, "tasks_completed")
            else 0,
            "tasks_failed": metrics.tasks_failed
            if hasattr(metrics, "tasks_failed")
            else 0,
            "bounty_earned_usd": metrics.bounty_earned
            if hasattr(metrics, "bounty_earned")
            else 0,
            "avg_routing_ms": metrics.avg_routing_ms
            if hasattr(metrics, "avg_routing_ms")
            else 0,
            "success_rate": metrics.success_rate
            if hasattr(metrics, "success_rate")
            else 0,
            "enrichment_rate": metrics.enrichment_rate
            if hasattr(metrics, "enrichment_rate")
            else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return flat
    except Exception as e:
        logger.exception(f"Metrics error: {e}")
        return {
            "swarm_enabled": 1,
            "error": "Failed to retrieve metrics",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/config")
async def update_config(
    config: SwarmConfigUpdate,
    api_key: APIKeyData = Depends(require_admin),
):
    """
    Update swarm configuration at runtime.

    Changes take effect immediately. Does not persist across restarts
    (use environment variables for persistent config).
    """
    global SWARM_MODE, SWARM_DAILY_BUDGET, SWARM_MAX_TASK_BOUNTY, AUTOJOB_URL

    changes = {}

    if config.mode is not None:
        if config.mode not in ("passive", "semi-auto", "full-auto"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {config.mode}. Must be: passive, semi-auto, full-auto",
            )
        SWARM_MODE = config.mode
        changes["mode"] = config.mode

    if config.daily_budget is not None:
        SWARM_DAILY_BUDGET = config.daily_budget
        changes["daily_budget"] = config.daily_budget

    if config.max_task_bounty is not None:
        SWARM_MAX_TASK_BOUNTY = config.max_task_bounty
        changes["max_task_bounty"] = config.max_task_bounty

    if config.autojob_url is not None:
        AUTOJOB_URL = config.autojob_url
        changes["autojob_url"] = config.autojob_url

    logger.info(f"Swarm config updated: {changes}")

    return {
        "updated": changes,
        "current_config": {
            "mode": SWARM_MODE,
            "daily_budget": SWARM_DAILY_BUDGET,
            "max_task_bounty": SWARM_MAX_TASK_BOUNTY,
            "autojob_url": AUTOJOB_URL,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/events")
async def list_events(
    limit: int = Query(50, ge=1, le=500, description="Max events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    api_key: APIKeyData = Depends(verify_api_key),
):
    """
    Get recent coordinator events for audit trail.
    """
    coord = require_coordinator()

    try:
        events = coord.get_events(limit=limit)

        if event_type:
            events = [
                e for e in events if e.get("type", "").upper() == event_type.upper()
            ]

        return {
            "events": events,
            "total": len(events),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Events error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tasks")
async def swarm_tasks(
    status: Optional[str] = Query(None, description="Filter by task status in queue"),
    limit: int = Query(50, ge=1, le=200),
    api_key: APIKeyData = Depends(verify_api_key),
):
    """
    Get tasks in the swarm coordination queue.

    These are tasks the swarm is tracking — not the same as the main EM task list.
    """
    coord = require_coordinator()

    try:
        queue_summary = coord.get_queue_summary()
        tasks = (
            queue_summary.get("tasks", []) if isinstance(queue_summary, dict) else []
        )

        if status:
            tasks = [t for t in tasks if t.get("status", "").upper() == status.upper()]

        tasks = tasks[:limit]

        return {
            "tasks": tasks,
            "total": len(tasks),
            "queue_depth": queue_summary.get("total", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Task queue error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/agents/{agent_id}/activate")
async def activate_agent(
    agent_id: str = Path(..., description="Agent ID to activate"),
    params: Optional[AgentActivation] = None,
    api_key: APIKeyData = Depends(require_admin),
):
    """
    Activate an agent in the swarm — transitions to IDLE state and makes
    it available for task routing.
    """
    coord = require_coordinator()

    try:
        # Register or reactivate agent
        coord.register_agent(
            agent_id=agent_id,
            skills=params.skills if params else None,
            daily_budget=params.daily_budget if params else SWARM_DAILY_BUDGET,
        )

        return {
            "agent_id": agent_id,
            "state": "IDLE",
            "message": f"Agent {agent_id} activated and available for task routing",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Agent activation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/agents/{agent_id}/suspend")
async def suspend_agent(
    agent_id: str = Path(..., description="Agent ID to suspend"),
    api_key: APIKeyData = Depends(require_admin),
):
    """
    Suspend an agent — removes from task routing until reactivated.
    """
    coord = require_coordinator()

    try:
        coord.lifecycle.suspend_agent(agent_id)

        return {
            "agent_id": agent_id,
            "state": "SUSPENDED",
            "message": f"Agent {agent_id} suspended — will not receive new task assignments",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Agent suspension error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/agents/{agent_id}/budget")
async def update_agent_budget(
    agent_id: str = Path(..., description="Agent ID"),
    budget: BudgetUpdate = ...,
    api_key: APIKeyData = Depends(require_admin),
):
    """
    Update an agent's spending budget limits.
    """
    coord = require_coordinator()

    try:
        record = coord.lifecycle.get_agent(agent_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        updates = {}
        if budget.daily_limit is not None:
            coord.lifecycle.update_budget(agent_id, daily_limit=budget.daily_limit)
            updates["daily_limit"] = budget.daily_limit
        if budget.monthly_limit is not None:
            coord.lifecycle.update_budget(agent_id, monthly_limit=budget.monthly_limit)
            updates["monthly_limit"] = budget.monthly_limit

        return {
            "agent_id": agent_id,
            "budget_updated": updates,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Budget update error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
