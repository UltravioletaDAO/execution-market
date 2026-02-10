"""
Health Check Endpoints for Execution Market

Provides HTTP endpoints for health probes:
- GET /health - Basic health check (comprehensive)
- GET /health/ready - Readiness probe (can accept traffic?)
- GET /health/live - Liveness probe (is process alive?)
- GET /health/detailed - Detailed status with all dependencies
- GET /health/routes - Route parity check (lists all registered routes)

Compatible with:
- Kubernetes health probes
- AWS ECS/ELB health checks
- Generic load balancer checks
- Status page integrations
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request, Response, status
from starlette.routing import Mount, Route

from .checks import HealthChecker, HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


# =============================================================================
# Global Health Checker Instance
# =============================================================================


_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def set_health_checker(checker: HealthChecker) -> None:
    """Set a custom health checker instance (for testing)."""
    global _health_checker
    _health_checker = checker


# =============================================================================
# Basic Health Endpoint
# =============================================================================


@router.get(
    "",
    summary="Health Check (Root)",
    responses={
        200: {"description": "System is healthy or degraded"},
        503: {"description": "System is unhealthy"},
    },
)
@router.get(
    "/",
    summary="Health Check",
    responses={
        200: {"description": "System is healthy or degraded"},
        503: {"description": "System is unhealthy"},
    },
)
async def health_check(
    force: bool = Query(False, description="Force fresh health check, bypass cache"),
    response: Response = None,
) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns detailed status of all system components including database,
    Redis, blockchain, storage, and x402 payment service.

    Response Codes:
    - 200: System is healthy or degraded (can still serve traffic)
    - 503: System is unhealthy (should not receive traffic)

    Args:
        force: If True, bypasses cache and runs fresh checks

    Returns:
        JSON object with overall status and component details
    """
    checker = get_health_checker()
    health = await checker.check_all(force_refresh=force)

    # Set appropriate status code
    if health.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health.to_dict()


# =============================================================================
# Kubernetes-Style Probes
# =============================================================================


@router.get(
    "/ready",
    summary="Readiness Probe",
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready"},
    },
)
async def readiness_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes readiness probe.

    Returns 200 if the service can accept traffic.
    Used by load balancers to determine if traffic should be routed to this instance.

    A service is considered "ready" if it can connect to its critical dependencies
    (database and blockchain). Non-critical components can be degraded.

    Response Codes:
    - 200: Ready to accept traffic
    - 503: Not ready (don't route traffic here)
    """
    checker = get_health_checker()
    health = await checker.check_all()

    # Consider DEGRADED as ready (can still serve, just not optimally)
    ready = health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    # Build critical component summary
    critical_status = {}
    for name in checker.CRITICAL_COMPONENTS:
        if name in health.components:
            critical_status[name] = health.components[name].status.value

    result = {
        "status": "ready" if ready else "not_ready",
        "overall": health.status.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "critical_components": critical_status,
    }

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        # Add reason for not being ready
        unhealthy = [
            name
            for name, comp in health.components.items()
            if comp.status == HealthStatus.UNHEALTHY
            and name in checker.CRITICAL_COMPONENTS
        ]
        result["reason"] = f"Critical components unhealthy: {', '.join(unhealthy)}"

    return result


@router.get(
    "/live",
    summary="Liveness Probe",
    responses={
        200: {"description": "Process is alive"},
    },
)
async def liveness_probe() -> Dict[str, Any]:
    """
    Kubernetes liveness probe.

    Returns 200 if the process is alive.
    Used by Kubernetes to determine if the pod should be restarted.

    This endpoint is intentionally lightweight and does NOT check dependencies.
    It only verifies that the Python process is running and can handle requests.

    Response Codes:
    - 200: Process is alive (always, unless crashed)
    """
    checker = get_health_checker()
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(checker.uptime_seconds, 2),
    }


@router.get(
    "/startup",
    summary="Startup Probe",
    responses={
        200: {"description": "Service has started"},
        503: {"description": "Service is still starting"},
    },
)
async def startup_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes startup probe.

    Used during initial container startup to allow slow-starting containers.
    More lenient than liveness probe - allows time for database connections
    and other initializations.

    Response Codes:
    - 200: Startup complete
    - 503: Still starting up
    """
    checker = get_health_checker()

    # During startup, just check if core services are reachable
    try:
        db_health = await checker.check_component("database")
        blockchain_health = await checker.check_component("blockchain")

        # Consider started if both critical components are at least reachable
        started = (
            db_health.status != HealthStatus.UNHEALTHY
            and blockchain_health.status != HealthStatus.UNHEALTHY
        )

        result = {
            "status": "started" if started else "starting",
            "database": db_health.status.value,
            "blockchain": blockchain_health.status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not started:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            reasons = []
            if db_health.status == HealthStatus.UNHEALTHY:
                reasons.append(f"database: {db_health.message}")
            if blockchain_health.status == HealthStatus.UNHEALTHY:
                reasons.append(f"blockchain: {blockchain_health.message}")
            result["reason"] = "; ".join(reasons)

        return result

    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "starting",
            "message": str(e)[:100],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# Detailed Health Endpoint
# =============================================================================


@router.get(
    "/detailed",
    summary="Detailed Health Check",
    responses={
        200: {
            "description": "Detailed health status with component latencies and configuration"
        },
        503: {"description": "System is unhealthy"},
    },
)
async def detailed_health(
    force: bool = Query(False, description="Force fresh health check"),
    include_history: bool = Query(False, description="Include recent health history"),
    response: Response = None,
) -> Dict[str, Any]:
    """
    Detailed health check with extended information.

    Returns comprehensive status including:
    - All component statuses with latency measurements
    - Configuration details (without secrets)
    - Recent health check history (optional)
    - Version and environment information

    Args:
        force: If True, bypasses cache
        include_history: If True, includes recent health check history

    Returns:
        Extended health information
    """
    checker = get_health_checker()
    health = await checker.check_all(force_refresh=force)

    if health.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    result = {
        "status": health.status.value,
        "version": health.version,
        "environment": checker.environment,
        "uptime_seconds": round(health.uptime_seconds, 2),
        "timestamp": health.timestamp.isoformat(),
        "components": {
            name: comp.to_dict() for name, comp in health.components.items()
        },
        "summary": {
            "total_components": len(health.components),
            "healthy": sum(
                1
                for c in health.components.values()
                if c.status == HealthStatus.HEALTHY
            ),
            "degraded": sum(
                1
                for c in health.components.values()
                if c.status == HealthStatus.DEGRADED
            ),
            "unhealthy": sum(
                1
                for c in health.components.values()
                if c.status == HealthStatus.UNHEALTHY
            ),
        },
        "critical_components": list(checker.CRITICAL_COMPONENTS),
    }

    if include_history:
        result["history"] = checker.get_history(limit=10)

    return result


# =============================================================================
# Component-Specific Endpoints
# =============================================================================


@router.get(
    "/component/{component_name}",
    summary="Check Single Component",
    responses={
        200: {"description": "Component health status"},
        404: {"description": "Component not found"},
        503: {"description": "Component is unhealthy"},
    },
)
async def check_component(
    component_name: str,
    response: Response,
) -> Dict[str, Any]:
    """
    Check a specific component's health.

    Args:
        component_name: Name of component (database, redis, x402, storage, blockchain)

    Returns:
        Component health status
    """
    checker = get_health_checker()

    valid_components = ["database", "redis", "x402", "storage", "blockchain"]
    valid_components.extend(checker._custom_checks.keys())

    if component_name not in valid_components:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "error": f"Unknown component: {component_name}",
            "valid_components": valid_components,
        }

    health = await checker.check_component(component_name)

    if health.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"component": component_name, **health.to_dict()}


# =============================================================================
# Administrative Endpoints
# =============================================================================


@router.get(
    "/history",
    summary="Health Check History",
    responses={
        200: {"description": "Recent health check history"},
    },
)
async def health_history(
    limit: int = Query(10, ge=1, le=100, description="Number of history entries"),
) -> Dict[str, Any]:
    """
    Get recent health check history.

    Useful for trend analysis and debugging intermittent issues.

    Args:
        limit: Maximum number of history entries to return
    """
    checker = get_health_checker()
    history = checker.get_history(limit=limit)

    return {
        "history": history,
        "count": len(history),
        "max_stored": checker._history_max_size,
    }


@router.post(
    "/invalidate-cache",
    summary="Invalidate Health Cache",
    responses={
        200: {"description": "Cache invalidated successfully"},
    },
)
async def invalidate_cache() -> Dict[str, Any]:
    """
    Invalidate health check cache.

    Forces next health check to run fresh checks for all components.
    Useful after configuration changes or incident recovery.
    """
    checker = get_health_checker()
    checker.invalidate_cache()
    return {
        "status": "cache_invalidated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/version",
    summary="API Version Info",
    responses={
        200: {"description": "Version and build information"},
    },
)
async def version_info() -> Dict[str, Any]:
    """
    Get API version and build information.

    Returns version, environment, and build metadata.
    """
    import os

    checker = get_health_checker()

    return {
        "name": "Execution Market MCP Server",
        "version": checker.version,
        "environment": checker.environment,
        "build_date": os.getenv("BUILD_DATE", "unknown"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown")[:8]
        if os.getenv("GIT_COMMIT")
        else "unknown",
        "uptime_seconds": round(checker.uptime_seconds, 2),
    }


# =============================================================================
# Route Parity Check Endpoint
# =============================================================================


def _collect_routes(routes, prefix: str = "") -> List[Dict[str, Any]]:
    """Recursively collect all routes from the app, including mounted sub-apps."""
    collected = []
    for route in routes:
        if isinstance(route, Route):
            path = prefix + route.path
            collected.append(
                {
                    "path": path,
                    "methods": sorted(route.methods - {"HEAD"})
                    if route.methods
                    else [],
                    "name": route.name or "",
                    "tags": getattr(route, "tags", None) or [],
                }
            )
        elif isinstance(route, Mount):
            mount_path = prefix + route.path
            # Recurse into mounted sub-applications
            sub_routes = getattr(route, "routes", None)
            if sub_routes:
                collected.extend(_collect_routes(sub_routes, mount_path))
            else:
                # Opaque mount (e.g. MCP ASGI app) — record the mount point itself
                collected.append(
                    {
                        "path": mount_path,
                        "methods": ["MOUNT"],
                        "name": route.name or "",
                        "tags": [],
                    }
                )
    return collected


def _group_prefix(path: str) -> str:
    """Derive a human-readable group name from a route path."""
    if path.startswith("/api/v1/admin"):
        return "admin"
    if path.startswith("/api/v1/escrow"):
        return "escrow"
    if path.startswith("/api/v1/reputation"):
        return "reputation"
    if path.startswith("/api/v1"):
        return "api/v1"
    if path.startswith("/health"):
        return "health"
    if path.startswith("/ws"):
        return "websocket"
    if path.startswith("/mcp"):
        return "mcp"
    if path.startswith("/.well-known") or path.startswith("/discovery"):
        return "a2a"
    return "root"


@router.get(
    "/routes",
    summary="List Registered Routes",
    responses={
        200: {"description": "All registered routes grouped by prefix"},
    },
)
async def route_parity_check(request: Request) -> Dict[str, Any]:
    """
    List all registered routes in the FastAPI application.

    Diagnostic endpoint for verifying production route parity.
    For each route returns path, methods, name, and tags.
    Routes are grouped by their URL prefix.

    No authentication required — no sensitive data is exposed.
    """
    app = request.app
    all_routes = _collect_routes(app.routes)

    # Sort routes by path for deterministic output
    all_routes.sort(key=lambda r: r["path"])

    # Group by prefix
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for route in all_routes:
        group = _group_prefix(route["path"])
        groups[group].append(route)

    return {
        "total": len(all_routes),
        "by_group": {
            group: {
                "count": len(routes),
                "routes": routes,
            }
            for group, routes in sorted(groups.items())
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Metrics Sanity Check Endpoint
# =============================================================================


@router.get(
    "/sanity",
    summary="Metrics Sanity Check",
    responses={
        200: {"description": "Sanity check results with any warnings"},
        503: {"description": "Sanity check failed"},
    },
)
async def metrics_sanity_check(response: Response) -> Dict[str, Any]:
    """
    Periodic metrics sanity check.

    Verifies data consistency across the platform:
    - Task counts by status sum correctly
    - Completed tasks have payment evidence
    - No orphaned submissions (task deleted but submission exists)
    - No stuck tasks (accepted but idle for >24h)

    Returns a list of warnings for any inconsistencies found.
    """
    import supabase_client

    client = supabase_client.get_client()
    warnings: List[Dict[str, str]] = []
    checks_passed = 0
    checks_total = 0

    try:
        # Check 1: Task status distribution
        checks_total += 1
        try:
            tasks_result = (
                client.table("tasks")
                .select(
                    "id, status, bounty_usd, executor_id, created_at, updated_at, escrow_tx"
                )
                .execute()
            )
            tasks = tasks_result.data or []
            status_counts: Dict[str, int] = {}
            for t in tasks:
                s = t.get("status", "unknown")
                status_counts[s] = status_counts.get(s, 0) + 1
            checks_passed += 1
        except Exception as e:
            warnings.append(
                {"check": "task_counts", "message": f"Failed to query tasks: {e}"}
            )
            tasks = []
            status_counts = {}

        # Build payment evidence index for completed tasks.
        # Canonical source: payments table release/final_release tx hashes.
        # Legacy source: submissions.payment_tx.
        payment_task_ids = set()
        try:
            payments_result = (
                client.table("payments")
                .select("task_id,type,tx_hash,transaction_hash,status")
                .in_("type", ["release", "final_release", "partial_release"])
                .execute()
            )
            for row in payments_result.data or []:
                tx_hash = row.get("tx_hash") or row.get("transaction_hash")
                if row.get("task_id") and tx_hash:
                    payment_task_ids.add(row["task_id"])
        except Exception:
            # Keep backward compatibility with legacy schemas where payments may not exist.
            pass

        submission_payment_task_ids = set()
        try:
            submissions_result = (
                client.table("submissions")
                .select("task_id,payment_tx")
                .not_("payment_tx", "is", "null")
                .execute()
            )
            for row in submissions_result.data or []:
                if row.get("task_id") and row.get("payment_tx"):
                    submission_payment_task_ids.add(row["task_id"])
        except Exception:
            pass

        # Check 2: Completed tasks should have payment evidence.
        checks_total += 1
        completed_no_payment = [
            t["id"]
            for t in tasks
            if t.get("status") == "completed"
            and t.get("id") not in payment_task_ids
            and t.get("id") not in submission_payment_task_ids
            and not t.get("escrow_tx")
        ]
        if completed_no_payment:
            warnings.append(
                {
                    "check": "completed_no_payment",
                    "message": f"{len(completed_no_payment)} completed task(s) have no payment evidence",
                    "task_ids": completed_no_payment[:10],
                }
            )
        else:
            checks_passed += 1

        # Check 3: Accepted/in_progress tasks should have an executor
        checks_total += 1
        active_no_executor = [
            t["id"]
            for t in tasks
            if t.get("status") in ("accepted", "in_progress", "submitted")
            and not t.get("executor_id")
        ]
        if active_no_executor:
            warnings.append(
                {
                    "check": "active_no_executor",
                    "message": f"{len(active_no_executor)} active task(s) have no executor assigned",
                    "task_ids": active_no_executor[:10],
                }
            )
        else:
            checks_passed += 1

        # Check 4: Stuck tasks (accepted >24h ago, no update)
        checks_total += 1
        from datetime import datetime as dt, timezone as tz, timedelta as td

        cutoff = (dt.now(tz.utc) - td(hours=24)).isoformat()
        stuck_tasks = [
            t["id"]
            for t in tasks
            if t.get("status") in ("accepted", "in_progress")
            and (t.get("updated_at") or t.get("created_at", "")) < cutoff
        ]
        if stuck_tasks:
            warnings.append(
                {
                    "check": "stuck_tasks",
                    "message": f"{len(stuck_tasks)} task(s) stuck in active state >24h",
                    "task_ids": stuck_tasks[:10],
                }
            )
        else:
            checks_passed += 1

        # Check 5: Orphaned submissions (submission exists for non-existent task)
        checks_total += 1
        try:
            subs_result = client.table("submissions").select("id, task_id").execute()
            subs = subs_result.data or []
            task_ids = {t["id"] for t in tasks}
            orphaned = [s["id"] for s in subs if s.get("task_id") not in task_ids]
            if orphaned:
                warnings.append(
                    {
                        "check": "orphaned_submissions",
                        "message": f"{len(orphaned)} submission(s) reference non-existent tasks",
                        "submission_ids": orphaned[:10],
                    }
                )
            else:
                checks_passed += 1
        except Exception as e:
            warnings.append(
                {"check": "orphaned_submissions", "message": f"Failed: {e}"}
            )

        # Check 6: Financial consistency — total bounties vs task count
        checks_total += 1
        total_bounty = sum(float(t.get("bounty_usd", 0) or 0) for t in tasks)
        zero_bounty_active = [
            t["id"]
            for t in tasks
            if t.get("status") in ("published", "accepted", "in_progress", "submitted")
            and float(t.get("bounty_usd", 0) or 0) == 0
        ]
        if zero_bounty_active:
            warnings.append(
                {
                    "check": "zero_bounty_active",
                    "message": f"{len(zero_bounty_active)} active task(s) have $0 bounty",
                    "task_ids": zero_bounty_active[:10],
                }
            )
        else:
            checks_passed += 1

    except Exception as e:
        warnings.append(
            {"check": "sanity_check", "message": f"Sanity check failed: {e}"}
        )

    all_ok = checks_passed == checks_total
    if not all_ok:
        response.status_code = (
            status.HTTP_200_OK
        )  # Warnings are informational, not failures

    return {
        "status": "ok" if all_ok else "warnings",
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "warnings": warnings,
        "summary": {
            "task_status_distribution": status_counts,
            "total_tasks": len(tasks),
            "total_bounty_usd": round(total_bounty, 2),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Prometheus Metrics Endpoint
# =============================================================================


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    responses={
        200: {"description": "Prometheus metrics in text/plain exposition format"},
    },
)
async def prometheus_metrics(
    refresh: bool = Query(
        False, description="Refresh expensive metrics before scraping"
    ),
) -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text exposition format.
    Compatible with Prometheus, Grafana, and other monitoring tools.

    Metrics include:
    - em_requests_total: Request count by endpoint and status
    - em_request_duration_seconds: Request latency histogram
    - em_active_tasks: Active tasks by status and category
    - em_escrow_balance_usd: Escrow balance by token
    - em_component_health: Component health status

    Args:
        refresh: If True, refreshes expensive metrics from database
    """
    from .metrics import get_metrics_collector, COMPONENT_HEALTH
    from .checks import HealthStatus

    collector = get_metrics_collector()

    # Optionally refresh expensive metrics
    if refresh:
        await collector.refresh_expensive_metrics()

    # Update component health metrics from last health check
    checker = get_health_checker()
    if checker._cache:
        for name, comp in checker._cache.items():
            health_value = {
                HealthStatus.HEALTHY: 1.0,
                HealthStatus.DEGRADED: 0.5,
                HealthStatus.UNHEALTHY: 0.0,
            }.get(comp.status, 0.0)
            COMPONENT_HEALTH.set(health_value, labels={"component": name})

    # Export in Prometheus format
    return Response(
        content=collector.export_prometheus(), media_type="text/plain; charset=utf-8"
    )
