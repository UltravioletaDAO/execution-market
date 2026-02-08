"""
Health Check Endpoints for Execution Market.

Provides liveness, readiness, and detailed health probes for:
- Kubernetes/ECS container orchestration
- Load balancer health checks
- Monitoring and alerting systems
- Status page integration
"""

from fastapi import APIRouter, Response, status
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import httpx
import os
import logging
import time
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(str, Enum):
    """Health status values following standard patterns."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2)
            if self.latency_ms is not None
            else None,
            "message": self.message,
            "last_check": self.last_check.isoformat(),
            "details": self.details if self.details else None,
        }


@dataclass
class SystemHealth:
    """Overall system health."""

    status: HealthStatus
    version: str
    uptime_seconds: float
    components: Dict[str, ComponentHealth]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": self.timestamp.isoformat(),
            "components": {
                name: comp.to_dict() for name, comp in self.components.items()
            },
        }


class HealthChecker:
    """
    Comprehensive health checker for all Execution Market components.

    Features:
    - Caching to prevent excessive health check load
    - Concurrent health checks for fast response
    - Configurable timeouts per component
    - Critical vs non-critical component distinction
    - Custom health check registration
    """

    # Critical components that cause UNHEALTHY status if down
    CRITICAL_COMPONENTS = {"database", "blockchain"}

    # Default timeouts in seconds
    DEFAULT_TIMEOUT = 5.0
    COMPONENT_TIMEOUTS = {
        "database": 5.0,
        "redis": 2.0,
        "blockchain": 10.0,
        "storage": 5.0,
        "anthropic": 3.0,
        "x402": 5.0,
    }

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.version = os.getenv("APP_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")

        # Cache configuration
        self._cache: Dict[str, ComponentHealth] = {}
        self._cache_ttl = timedelta(seconds=30)
        self._last_full_check: Optional[datetime] = None

        # Custom health checks
        self._custom_checks: Dict[str, Callable[[], Awaitable[ComponentHealth]]] = {}

        # Health check history for trend analysis
        self._history: List[SystemHealth] = []
        self._history_max_size = 100

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[ComponentHealth]],
        critical: bool = False,
    ) -> None:
        """
        Register a custom health check.

        Args:
            name: Component name
            check_fn: Async function that returns ComponentHealth
            critical: If True, failure marks system as UNHEALTHY
        """
        self._custom_checks[name] = check_fn
        if critical:
            self.CRITICAL_COMPONENTS.add(name)

    async def check_database(self) -> ComponentHealth:
        """Check Supabase PostgreSQL connection."""
        start = time.time()
        try:
            import supabase_client

            client = supabase_client.get_client()

            # Simple query to verify connection
            await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: client.table("tasks").select("id").limit(1).execute()
                ),
                timeout=self.COMPONENT_TIMEOUTS.get("database", self.DEFAULT_TIMEOUT),
            )

            latency = (time.time() - start) * 1000

            # Check latency thresholds
            if latency > 2000:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message=f"High latency: {latency:.1f}ms",
                )

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message=f"Connected, latency: {latency:.1f}ms",
            )
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message="Connection timeout (>5s)",
            )
        except Exception as e:
            logger.error("Database health check failed: %s", str(e))
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message=f"Connection failed: {str(e)[:100]}",
            )

    async def check_redis(self) -> ComponentHealth:
        """Check Redis connection (if configured)."""
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Not configured (optional component)",
            )

        start = time.time()
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(redis_url, decode_responses=True)

            await asyncio.wait_for(
                client.ping(),
                timeout=self.COMPONENT_TIMEOUTS.get("redis", self.DEFAULT_TIMEOUT),
            )

            # Get additional info
            info = await client.info("memory")
            await client.aclose()

            latency = (time.time() - start) * 1000

            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message=f"Connected, latency: {latency:.1f}ms",
                details={
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", "unknown"),
                },
            )
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.time() - start) * 1000,
                message="Connection timeout",
            )
        except ImportError:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis client not installed (optional)",
            )
        except Exception as e:
            logger.warning("Redis health check failed: %s", str(e))
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.time() - start) * 1000,
                message=f"Connection issue: {str(e)[:100]}",
            )

    async def check_blockchain(self) -> ComponentHealth:
        """Check Base RPC connection."""
        rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        start = time.time()

        try:
            async with httpx.AsyncClient(
                timeout=self.COMPONENT_TIMEOUTS.get("blockchain", self.DEFAULT_TIMEOUT)
            ) as client:
                response = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_blockNumber",
                        "params": [],
                        "id": 1,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "result" in data:
                    block_number = int(data["result"], 16)
                    latency = (time.time() - start) * 1000

                    return ComponentHealth(
                        name="blockchain",
                        status=HealthStatus.HEALTHY
                        if latency < 2000
                        else HealthStatus.DEGRADED,
                        latency_ms=latency,
                        message=f"Connected, block: {block_number:,}",
                        details={
                            "block_number": block_number,
                            "network": "base"
                            if "base.org" in rpc_url
                            else "custom",
                        },
                    )
                elif "error" in data:
                    return ComponentHealth(
                        name="blockchain",
                        status=HealthStatus.DEGRADED,
                        latency_ms=(time.time() - start) * 1000,
                        message=f"RPC error: {data['error'].get('message', 'Unknown')}",
                    )
                else:
                    return ComponentHealth(
                        name="blockchain",
                        status=HealthStatus.DEGRADED,
                        latency_ms=(time.time() - start) * 1000,
                        message="Invalid RPC response",
                    )
        except httpx.TimeoutException:
            return ComponentHealth(
                name="blockchain",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.time() - start) * 1000,
                message="RPC timeout",
            )
        except Exception as e:
            logger.error("Blockchain health check failed: %s", str(e))
            return ComponentHealth(
                name="blockchain",
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message=f"RPC error: {str(e)[:100]}",
            )

    async def check_storage(self) -> ComponentHealth:
        """Check Supabase Storage connection."""
        start = time.time()
        try:
            import supabase_client

            client = supabase_client.get_client()

            # Try to access evidence bucket directly (list_buckets can fail with some auth)
            evidence_bucket_exists = False
            bucket_name = "evidence"
            error_msg = None

            try:
                # Try to list files in the evidence bucket (limit 1 to minimize overhead)
                await asyncio.wait_for(
                    asyncio.to_thread(lambda: client.storage.from_(bucket_name).list()),
                    timeout=self.COMPONENT_TIMEOUTS.get(
                        "storage", self.DEFAULT_TIMEOUT
                    ),
                )
                evidence_bucket_exists = True  # If no exception, bucket exists
            except Exception as e:
                error_msg = str(e)

            latency = (time.time() - start) * 1000

            if evidence_bucket_exists:
                status = HealthStatus.HEALTHY
                message = f"Connected, bucket '{bucket_name}' accessible"
            else:
                status = HealthStatus.DEGRADED
                message = f"Evidence bucket not accessible: {error_msg or 'not found'}"

            return ComponentHealth(
                name="storage",
                status=status,
                latency_ms=latency,
                message=message,
                details={"bucket": bucket_name, "accessible": evidence_bucket_exists},
            )
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="storage",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.time() - start) * 1000,
                message="Storage timeout",
            )
        except Exception as e:
            logger.warning("Storage health check failed: %s", str(e))
            return ComponentHealth(
                name="storage",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.time() - start) * 1000,
                message=f"Storage check failed: {str(e)[:100]}",
            )

    async def check_anthropic(self) -> ComponentHealth:
        """Check AI verification providers."""
        try:
            from verification.providers import list_available_providers

            providers = list_available_providers()
            available = [p for p in providers if p["available"]]

            if not available:
                return ComponentHealth(
                    name="ai_verification",
                    status=HealthStatus.DEGRADED,
                    message="No AI provider configured (set ANTHROPIC_API_KEY, OPENAI_API_KEY, or AWS Bedrock)",
                )

            names = ", ".join(f"{p['name']}({p['model']})" for p in available)
            return ComponentHealth(
                name="ai_verification",
                status=HealthStatus.HEALTHY,
                message=f"Providers: {names}",
            )
        except Exception as e:
            # Fallback to legacy check
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key and api_key.startswith("sk-ant-"):
                return ComponentHealth(
                    name="ai_verification",
                    status=HealthStatus.HEALTHY,
                    message="Anthropic API key configured",
                )
            return ComponentHealth(
                name="ai_verification",
                status=HealthStatus.DEGRADED,
                message=f"Check failed: {e}",
            )

    async def check_x402(self) -> ComponentHealth:
        """Check x402 payment service."""
        x402_url = os.getenv("X402_URL", "https://x402.org")
        start = time.time()

        try:
            async with httpx.AsyncClient(
                timeout=self.COMPONENT_TIMEOUTS.get("x402", self.DEFAULT_TIMEOUT)
            ) as client:
                response = await client.get(f"{x402_url}/health")
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return ComponentHealth(
                        name="x402",
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message="Payment service operational",
                    )
                else:
                    return ComponentHealth(
                        name="x402",
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        message=f"Service returned {response.status_code}",
                    )
        except Exception as e:
            return ComponentHealth(
                name="x402",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.time() - start) * 1000,
                message=f"x402 unavailable: {str(e)[:50]}",
            )

    async def check_erc8004(self) -> ComponentHealth:
        """Check ERC-8004 facilitator (identity + reputation) availability."""
        facilitator_url = os.getenv(
            "X402_FACILITATOR_URL", "https://facilitator.ultravioletadao.xyz"
        )
        agent_id = os.getenv("EM_AGENT_ID", "469")
        network = os.getenv("ERC8004_NETWORK", "base")
        start = time.time()

        try:
            async with httpx.AsyncClient(
                timeout=self.COMPONENT_TIMEOUTS.get("erc8004", self.DEFAULT_TIMEOUT)
            ) as client:
                response = await client.get(
                    f"{facilitator_url}/identity/{network}/{agent_id}"
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    name = data.get("name", "unknown")
                    return ComponentHealth(
                        name="erc8004",
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message=f"Identity + reputation operational (agent {agent_id}: {name})",
                    )
                elif response.status_code == 404:
                    return ComponentHealth(
                        name="erc8004",
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        message=f"Facilitator reachable but agent {agent_id} not found on {network}",
                    )
                else:
                    return ComponentHealth(
                        name="erc8004",
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        message=f"Facilitator returned {response.status_code}",
                    )
        except Exception as e:
            return ComponentHealth(
                name="erc8004",
                status=HealthStatus.DEGRADED,
                latency_ms=(time.time() - start) * 1000,
                message=f"ERC-8004 facilitator unavailable: {str(e)[:50]}",
            )

    async def check_all(self, force_refresh: bool = False) -> SystemHealth:
        """
        Run all health checks concurrently.

        Args:
            force_refresh: Skip cache and run fresh checks

        Returns:
            SystemHealth with all component statuses
        """
        now = datetime.now(timezone.utc)

        # Check cache
        if (
            not force_refresh
            and self._last_full_check
            and now - self._last_full_check < self._cache_ttl
            and self._cache
        ):
            overall = self._determine_overall_status(self._cache)
            return SystemHealth(
                status=overall,
                version=self.version,
                uptime_seconds=(now - self.start_time).total_seconds(),
                components=self._cache.copy(),
            )

        # Build list of checks
        checks = [
            ("database", self.check_database()),
            ("redis", self.check_redis()),
            ("blockchain", self.check_blockchain()),
            ("storage", self.check_storage()),
            ("anthropic", self.check_anthropic()),
            ("x402", self.check_x402()),
            ("erc8004", self.check_erc8004()),
        ]

        # Add custom checks
        for name, check_fn in self._custom_checks.items():
            checks.append((name, check_fn()))

        # Run all checks concurrently
        results = await asyncio.gather(
            *[check for _, check in checks], return_exceptions=True
        )

        # Process results
        components: Dict[str, ComponentHealth] = {}
        for (name, _), result in zip(checks, results):
            if isinstance(result, ComponentHealth):
                components[name] = result
            elif isinstance(result, Exception):
                logger.error(
                    "Health check %s failed with exception: %s", name, str(result)
                )
                components[name] = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)[:100]}",
                )

        # Update cache
        self._cache = components.copy()
        self._last_full_check = now

        overall = self._determine_overall_status(components)

        health = SystemHealth(
            status=overall,
            version=self.version,
            uptime_seconds=(now - self.start_time).total_seconds(),
            components=components,
        )

        # Store in history
        self._history.append(health)
        if len(self._history) > self._history_max_size:
            self._history.pop(0)

        return health

    def _determine_overall_status(
        self, components: Dict[str, ComponentHealth]
    ) -> HealthStatus:
        """
        Determine overall system health from components.

        Logic:
        - UNHEALTHY if any critical component is unhealthy
        - DEGRADED if any component is unhealthy or degraded
        - HEALTHY otherwise
        """
        # Check critical components first
        for name in self.CRITICAL_COMPONENTS:
            if name in components and components[name].status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY

        # Check for any degraded/unhealthy
        statuses = [c.status for c in components.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.DEGRADED
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def liveness(self) -> Dict[str, Any]:
        """
        Kubernetes liveness probe.

        Returns 200 if the process is alive.
        Used to determine if the pod should be restarted.
        """
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(
                (datetime.now(timezone.utc) - self.start_time).total_seconds(), 2
            ),
        }

    async def readiness(self) -> Dict[str, Any]:
        """
        Kubernetes readiness probe.

        Returns 200 if the service can accept traffic.
        Used by load balancers to route traffic.
        """
        health = await self.check_all()

        # Consider DEGRADED as ready (can still serve, just not optimally)
        ready = health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

        return {
            "status": "ready" if ready else "not_ready",
            "overall": health.status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "critical_components": {
                name: components[name].status.value
                for name, components in [
                    (n, health.components) for n in self.CRITICAL_COMPONENTS
                ]
                if name in components
            },
        }

    async def startup(self) -> Dict[str, Any]:
        """
        Kubernetes startup probe.

        Used during initial startup to allow slow-starting containers.
        More lenient than liveness probe.
        """
        # During startup, just check if core services are reachable
        try:
            db_health = await asyncio.wait_for(
                self.check_database(),
                timeout=30.0,  # Longer timeout for startup
            )
            return {
                "status": "started"
                if db_health.status != HealthStatus.UNHEALTHY
                else "starting",
                "database": db_health.status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "starting",
                "message": str(e)[:100],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history."""
        return [h.to_dict() for h in self._history[-limit:]]

    def invalidate_cache(self) -> None:
        """Clear the health check cache."""
        self._cache.clear()
        self._last_full_check = None


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/")
async def health_check(force: bool = False) -> Response:
    """
    Comprehensive health check.

    Returns detailed status of all system components.

    Args:
        force: Force fresh health check, bypass cache

    Returns:
        200: System is healthy
        200: System is degraded (with warning)
        503: System is unhealthy
    """
    checker = get_health_checker()
    health = await checker.check_all(force_refresh=force)

    response_code = 200
    if health.status == HealthStatus.UNHEALTHY:
        response_code = 503

    return Response(
        content=json.dumps(health.to_dict(), default=str),
        media_type="application/json",
        status_code=response_code,
    )


@router.get("/live")
async def liveness_probe() -> Dict[str, Any]:
    """
    Kubernetes liveness probe.

    Returns 200 if the process is alive.
    Used by Kubernetes to determine if the pod should be restarted.

    This endpoint is intentionally lightweight and does not check dependencies.
    """
    checker = get_health_checker()
    return await checker.liveness()


@router.get("/ready")
async def readiness_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes readiness probe.

    Returns 200 if the service can accept traffic.
    Used by load balancers to determine if traffic should be routed to this instance.
    """
    checker = get_health_checker()
    result = await checker.readiness()

    if result["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result


@router.get("/startup")
async def startup_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes startup probe.

    Used during initial container startup.
    Allows longer initialization time before liveness kicks in.
    """
    checker = get_health_checker()
    result = await checker.startup()

    if result["status"] == "starting":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text exposition format.
    """
    checker = get_health_checker()
    health = await checker.check_all()

    # Build Prometheus metrics
    lines = []

    # System up status
    lines.extend(
        [
            "# HELP em_up Service health status (1=healthy, 0.5=degraded, 0=unhealthy)",
            "# TYPE em_up gauge",
            f'em_up{{status="{health.status.value}",version="{health.version}"}} {1 if health.status == HealthStatus.HEALTHY else (0.5 if health.status == HealthStatus.DEGRADED else 0)}',
            "",
        ]
    )

    # Uptime
    lines.extend(
        [
            "# HELP em_uptime_seconds Service uptime in seconds",
            "# TYPE em_uptime_seconds counter",
            f"em_uptime_seconds {health.uptime_seconds:.2f}",
            "",
        ]
    )

    # Component health
    lines.extend(
        [
            "# HELP em_component_health Component health status (1=healthy, 0.5=degraded, 0=unhealthy)",
            "# TYPE em_component_health gauge",
        ]
    )

    for name, comp in health.components.items():
        health_value = {
            HealthStatus.HEALTHY: 1,
            HealthStatus.DEGRADED: 0.5,
            HealthStatus.UNHEALTHY: 0,
        }[comp.status]
        lines.append(f'em_component_health{{component="{name}"}} {health_value}')

    lines.append("")

    # Component latency
    lines.extend(
        [
            "# HELP em_component_latency_ms Component check latency in milliseconds",
            "# TYPE em_component_latency_ms gauge",
        ]
    )

    for name, comp in health.components.items():
        if comp.latency_ms is not None:
            lines.append(
                f'em_component_latency_ms{{component="{name}"}} {comp.latency_ms:.2f}'
            )

    lines.append("")

    # Last check timestamp
    lines.extend(
        [
            "# HELP em_health_check_timestamp_seconds Unix timestamp of last health check",
            "# TYPE em_health_check_timestamp_seconds gauge",
            f"em_health_check_timestamp_seconds {health.timestamp.timestamp():.0f}",
        ]
    )

    return Response(
        content="\n".join(lines) + "\n", media_type="text/plain; charset=utf-8"
    )


@router.get("/history")
async def health_history(limit: int = 10) -> Dict[str, Any]:
    """
    Get recent health check history.

    Useful for trend analysis and debugging intermittent issues.

    Args:
        limit: Maximum number of history entries to return (default: 10)
    """
    checker = get_health_checker()
    return {
        "history": checker.get_history(limit),
        "count": len(checker._history),
        "max_size": checker._history_max_size,
    }


@router.post("/invalidate-cache")
async def invalidate_cache() -> Dict[str, Any]:
    """
    Invalidate health check cache.

    Forces next health check to run fresh checks for all components.
    """
    checker = get_health_checker()
    checker.invalidate_cache()
    return {
        "status": "cache_invalidated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/version")
async def version_info() -> Dict[str, Any]:
    """
    Get API version and build information.
    """
    checker = get_health_checker()
    return {
        "name": "Execution Market API",
        "version": checker.version,
        "environment": checker.environment,
        "build_date": os.getenv("BUILD_DATE", "unknown"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown")[:8]
        if os.getenv("GIT_COMMIT")
        else "unknown",
        "uptime_seconds": round(
            (datetime.now(timezone.utc) - checker.start_time).total_seconds(), 2
        ),
    }
