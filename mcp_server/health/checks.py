"""
Health Check Functions for Chamba Dependencies

Provides individual health check functions for:
- Database (Supabase PostgreSQL)
- Redis (optional caching layer)
- x402 Facilitator (payment processing)
- Storage (Supabase Storage for evidence)
- Blockchain (Base RPC for on-chain operations)
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


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
        result = {
            "status": self.status.value,
            "last_check": self.last_check.isoformat(),
        }
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        return result

    @property
    def is_healthy(self) -> bool:
        """Check if component is in a healthy state."""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_operational(self) -> bool:
        """Check if component is operational (healthy or degraded)."""
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


@dataclass
class SystemHealth:
    """Overall system health aggregation."""
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
                name: comp.to_dict()
                for name, comp in self.components.items()
            }
        }


# =============================================================================
# Individual Health Check Functions
# =============================================================================


async def check_database(timeout: float = 5.0) -> ComponentHealth:
    """
    Check Supabase PostgreSQL connection.

    Verifies database connectivity by executing a simple query.
    Reports latency and connection status.

    Args:
        timeout: Maximum time to wait for response in seconds

    Returns:
        ComponentHealth with database status
    """
    start = time.time()
    try:
        import supabase_client
        client = supabase_client.get_client()

        # Simple query to verify connection
        result = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: client.table("tasks").select("id").limit(1).execute()
            ),
            timeout=timeout
        )

        latency = (time.time() - start) * 1000

        # Check latency thresholds
        if latency > 2000:
            return ComponentHealth(
                name="database",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"High latency: {latency:.1f}ms (threshold: 2000ms)"
            )

        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="Connected",
            details={"rows_returned": len(result.data) if result.data else 0}
        )
    except asyncio.TimeoutError:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message=f"Connection timeout (>{timeout}s)"
        )
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message=f"Connection failed: {str(e)[:100]}"
        )


async def check_redis(timeout: float = 2.0) -> ComponentHealth:
    """
    Check Redis connection (if configured).

    Verifies Redis connectivity using PING command.
    Reports memory usage and connected clients.

    Args:
        timeout: Maximum time to wait for response in seconds

    Returns:
        ComponentHealth with Redis status
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Not configured (optional component)"
        )

    start = time.time()
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, decode_responses=True)

        await asyncio.wait_for(client.ping(), timeout=timeout)

        # Get additional info
        info = await client.info("memory")
        await client.aclose()

        latency = (time.time() - start) * 1000

        # Check if latency is high
        if latency > 500:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"High latency: {latency:.1f}ms",
                details={
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                }
            )

        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="Connected",
            details={
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", "unknown")
            }
        )
    except asyncio.TimeoutError:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message="Connection timeout"
        )
    except ImportError:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis client not installed (optional)"
        )
    except Exception as e:
        logger.warning("Redis health check failed: %s", str(e))
        return ComponentHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=f"Connection issue: {str(e)[:100]}"
        )


async def check_x402(timeout: float = 5.0) -> ComponentHealth:
    """
    Check x402 facilitator health.

    Verifies the x402 payment service is operational by calling its health endpoint.
    Also checks if required environment variables are configured.

    Args:
        timeout: Maximum time to wait for response in seconds

    Returns:
        ComponentHealth with x402 status
    """
    x402_url = os.getenv("X402_FACILITATOR_URL", os.getenv("X402_URL", "https://facilitator.ultravioletadao.xyz"))
    x402_key = os.getenv("X402_PRIVATE_KEY")

    start = time.time()

    # Check configuration
    config_issues = []
    if not x402_key:
        config_issues.append("X402_PRIVATE_KEY not set")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{x402_url}/health")
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                # Parse response for additional details
                try:
                    health_data = response.json()
                    facilitator_status = health_data.get("status", "unknown")
                except Exception:
                    health_data = {}
                    facilitator_status = "ok" if response.status_code == 200 else "unknown"

                status = HealthStatus.HEALTHY
                message = "Facilitator operational"

                # Downgrade if config issues
                if config_issues:
                    status = HealthStatus.DEGRADED
                    message = f"Facilitator ok but: {', '.join(config_issues)}"

                return ComponentHealth(
                    name="x402",
                    status=status,
                    latency_ms=latency,
                    message=message,
                    details={
                        "facilitator_url": x402_url,
                        "facilitator_status": facilitator_status,
                        "config_complete": len(config_issues) == 0,
                    }
                )
            else:
                return ComponentHealth(
                    name="x402",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message=f"Facilitator returned HTTP {response.status_code}",
                    details={"facilitator_url": x402_url}
                )
    except httpx.TimeoutException:
        return ComponentHealth(
            name="x402",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=f"Facilitator timeout (>{timeout}s)",
            details={"facilitator_url": x402_url}
        )
    except Exception as e:
        logger.warning("x402 health check failed: %s", str(e))

        # If config is missing, payments won't work anyway
        if config_issues:
            return ComponentHealth(
                name="x402",
                status=HealthStatus.DEGRADED,
                message=f"Not configured: {', '.join(config_issues)}",
            )

        return ComponentHealth(
            name="x402",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=f"Facilitator unreachable: {str(e)[:50]}",
            details={"facilitator_url": x402_url}
        )


async def check_storage(timeout: float = 5.0) -> ComponentHealth:
    """
    Check Supabase Storage connection.

    Verifies storage availability by listing buckets and checking
    for the required 'evidence' bucket.

    Args:
        timeout: Maximum time to wait for response in seconds

    Returns:
        ComponentHealth with storage status
    """
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
            files = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: client.storage.from_(bucket_name).list()
                ),
                timeout=timeout
            )
            evidence_bucket_exists = True
        except Exception as e:
            error_msg = str(e)
            # Try alternate bucket name
            try:
                files = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: client.storage.from_("chamba-evidence").list()
                    ),
                    timeout=timeout
                )
                evidence_bucket_exists = True
                bucket_name = "chamba-evidence"
            except Exception:
                pass

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
            details={
                "bucket": bucket_name,
                "accessible": evidence_bucket_exists,
            }
        )
    except asyncio.TimeoutError:
        return ComponentHealth(
            name="storage",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=f"Storage timeout (>{timeout}s)"
        )
    except Exception as e:
        logger.warning("Storage health check failed: %s", str(e))
        return ComponentHealth(
            name="storage",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=f"Storage check failed: {str(e)[:100]}"
        )


async def check_blockchain(timeout: float = 10.0) -> ComponentHealth:
    """
    Check Base RPC connection.

    Verifies blockchain connectivity by fetching the current block number.
    Reports the current block and network status.

    Args:
        timeout: Maximum time to wait for response in seconds

    Returns:
        ComponentHealth with blockchain status
    """
    rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
    start = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                }
            )
            response.raise_for_status()
            data = response.json()

            if "result" in data:
                block_number = int(data["result"], 16)
                latency = (time.time() - start) * 1000

                # Determine network from URL
                if "base.org" in rpc_url:
                    network = "base-mainnet"
                elif "quicknode" in rpc_url.lower():
                    network = "base-quicknode"
                else:
                    network = "custom"

                status = HealthStatus.HEALTHY
                if latency > 3000:
                    status = HealthStatus.DEGRADED

                return ComponentHealth(
                    name="blockchain",
                    status=status,
                    latency_ms=latency,
                    message=f"Connected at block {block_number:,}",
                    details={
                        "block_number": block_number,
                        "network": network,
                        "rpc_endpoint": rpc_url[:50] + "..." if len(rpc_url) > 50 else rpc_url,
                    }
                )
            elif "error" in data:
                return ComponentHealth(
                    name="blockchain",
                    status=HealthStatus.DEGRADED,
                    latency_ms=(time.time() - start) * 1000,
                    message=f"RPC error: {data['error'].get('message', 'Unknown')}"
                )
            else:
                return ComponentHealth(
                    name="blockchain",
                    status=HealthStatus.DEGRADED,
                    latency_ms=(time.time() - start) * 1000,
                    message="Invalid RPC response format"
                )
    except httpx.TimeoutException:
        return ComponentHealth(
            name="blockchain",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=f"RPC timeout (>{timeout}s)"
        )
    except Exception as e:
        logger.error("Blockchain health check failed: %s", str(e))
        return ComponentHealth(
            name="blockchain",
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message=f"RPC error: {str(e)[:100]}"
        )


# =============================================================================
# Health Checker Class
# =============================================================================


class HealthChecker:
    """
    Comprehensive health checker for all Chamba components.

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

    @property
    def uptime_seconds(self) -> float:
        """Get current uptime in seconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[ComponentHealth]],
        critical: bool = False
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
        logger.info("Registered health check: %s (critical=%s)", name, critical)

    def unregister_check(self, name: str) -> None:
        """Remove a custom health check."""
        self._custom_checks.pop(name, None)
        self.CRITICAL_COMPONENTS.discard(name)

    async def check_component(self, name: str) -> ComponentHealth:
        """
        Check a single component by name.

        Args:
            name: Component name (database, redis, x402, storage, blockchain)

        Returns:
            ComponentHealth for the specified component
        """
        check_map = {
            "database": lambda: check_database(self.COMPONENT_TIMEOUTS.get("database", self.DEFAULT_TIMEOUT)),
            "redis": lambda: check_redis(self.COMPONENT_TIMEOUTS.get("redis", self.DEFAULT_TIMEOUT)),
            "x402": lambda: check_x402(self.COMPONENT_TIMEOUTS.get("x402", self.DEFAULT_TIMEOUT)),
            "storage": lambda: check_storage(self.COMPONENT_TIMEOUTS.get("storage", self.DEFAULT_TIMEOUT)),
            "blockchain": lambda: check_blockchain(self.COMPONENT_TIMEOUTS.get("blockchain", self.DEFAULT_TIMEOUT)),
        }

        # Check custom checks first
        if name in self._custom_checks:
            return await self._custom_checks[name]()

        if name in check_map:
            return await check_map[name]()

        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=f"Unknown component: {name}"
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
            not force_refresh and
            self._last_full_check and
            now - self._last_full_check < self._cache_ttl and
            self._cache
        ):
            overall = self._determine_overall_status(self._cache)
            return SystemHealth(
                status=overall,
                version=self.version,
                uptime_seconds=self.uptime_seconds,
                components=self._cache.copy()
            )

        # Build list of checks
        check_names = ["database", "redis", "blockchain", "storage", "x402"]
        checks = [(name, self.check_component(name)) for name in check_names]

        # Add custom checks
        for name in self._custom_checks:
            if name not in check_names:
                checks.append((name, self.check_component(name)))

        # Run all checks concurrently
        results = await asyncio.gather(
            *[check for _, check in checks],
            return_exceptions=True
        )

        # Process results
        components: Dict[str, ComponentHealth] = {}
        for (name, _), result in zip(checks, results):
            if isinstance(result, ComponentHealth):
                components[name] = result
            elif isinstance(result, Exception):
                logger.error("Health check %s failed with exception: %s", name, str(result))
                components[name] = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)[:100]}"
                )

        # Update cache
        self._cache = components.copy()
        self._last_full_check = now

        overall = self._determine_overall_status(components)

        health = SystemHealth(
            status=overall,
            version=self.version,
            uptime_seconds=self.uptime_seconds,
            components=components
        )

        # Store in history
        self._history.append(health)
        if len(self._history) > self._history_max_size:
            self._history.pop(0)

        return health

    def _determine_overall_status(
        self,
        components: Dict[str, ComponentHealth]
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

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history."""
        return [h.to_dict() for h in self._history[-limit:]]

    def invalidate_cache(self) -> None:
        """Clear the health check cache."""
        self._cache.clear()
        self._last_full_check = None
        logger.debug("Health check cache invalidated")
