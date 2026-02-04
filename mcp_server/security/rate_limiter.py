"""
Rate Limiter Module with Redis Backend

Implements sliding window rate limiting for fraud prevention:
- Per-endpoint limits by tier (FREE, STARTER, GROWTH, ENTERPRISE)
- Per-IP, per-device, and per-agent limits
- Sliding window algorithm for accurate rate limiting
- Redis backend for distributed deployments

This module provides a Redis-backed alternative to the
in-memory rate_limits.py for production use.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Try to import Redis (optional)
try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.info("Redis not available - using in-memory rate limiting")


# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

class RateLimitTier(str, Enum):
    """API rate limit tiers."""
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


# Rate limits by tier (requests per minute)
TIER_LIMITS: Dict[RateLimitTier, int] = {
    RateLimitTier.FREE: 10,
    RateLimitTier.STARTER: 60,
    RateLimitTier.GROWTH: 300,
    RateLimitTier.ENTERPRISE: 1000,
}

# Burst allowance multiplier
TIER_BURST_MULTIPLIER: Dict[RateLimitTier, float] = {
    RateLimitTier.FREE: 1.0,
    RateLimitTier.STARTER: 1.5,
    RateLimitTier.GROWTH: 2.0,
    RateLimitTier.ENTERPRISE: 3.0,
}

# Endpoint-specific limits (requests per minute)
ENDPOINT_LIMITS: Dict[str, Dict[RateLimitTier, int]] = {
    "submit_work": {
        RateLimitTier.FREE: 5,
        RateLimitTier.STARTER: 20,
        RateLimitTier.GROWTH: 100,
        RateLimitTier.ENTERPRISE: 500,
    },
    "publish_task": {
        RateLimitTier.FREE: 3,
        RateLimitTier.STARTER: 15,
        RateLimitTier.GROWTH: 75,
        RateLimitTier.ENTERPRISE: 300,
    },
    "check_submission": {
        RateLimitTier.FREE: 10,
        RateLimitTier.STARTER: 60,
        RateLimitTier.GROWTH: 300,
        RateLimitTier.ENTERPRISE: 1000,
    },
}

# Window sizes in seconds
WINDOW_MINUTE = 60
WINDOW_HOUR = 3600
WINDOW_DAY = 86400

# Default limits
DEFAULT_IP_LIMIT_PER_MINUTE = 30
DEFAULT_DEVICE_LIMIT_PER_DAY = 50
DEFAULT_AGENT_LIMIT_PER_HOUR = 100


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    limit: int
    reset_at: datetime
    retry_after_seconds: Optional[int] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response headers."""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
            "reset_at": self.reset_at.isoformat(),
            "retry_after": self.retry_after_seconds,
        }


@dataclass
class SlidingWindowConfig:
    """Configuration for a sliding window rate limit."""
    key_prefix: str
    window_seconds: int
    max_requests: int
    block_duration_seconds: int = 0  # How long to block after limit exceeded


# =============================================================================
# RATE LIMITER CLASS
# =============================================================================

class RateLimiter:
    """
    Rate limiter with Redis backend.

    Implements sliding window algorithm for accurate rate limiting
    without the boundary issues of fixed windows.

    Can fall back to in-memory storage if Redis is not available.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = "em:ratelimit:",
    ):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379")
            key_prefix: Prefix for all Redis keys
        """
        self.key_prefix = key_prefix
        self._redis: Optional[redis.Redis] = None
        self._redis_url = redis_url

        # In-memory fallback
        self._memory_store: Dict[str, List[float]] = {}
        self._memory_blocks: Dict[str, float] = {}

        logger.info(f"RateLimiter initialized (Redis: {redis_url is not None})")

    async def connect(self) -> bool:
        """Connect to Redis if URL provided."""
        if not HAS_REDIS or not self._redis_url:
            return False

        try:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("Connected to Redis for rate limiting")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._redis = None
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "default",
        tier: RateLimitTier = RateLimitTier.FREE,
        endpoint: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.

        Args:
            identifier: Unique identifier (IP, device_id, agent_id)
            limit_type: Type of limit ("ip", "device", "agent", "api")
            tier: API tier for the identifier
            endpoint: Optional endpoint for endpoint-specific limits

        Returns:
            RateLimitResult with check outcome
        """
        # Determine limit and window
        limit, window = self._get_limit_config(limit_type, tier, endpoint)
        key = f"{self.key_prefix}{limit_type}:{identifier}"

        now = time.time()

        # Use Redis if available
        if self._redis:
            return await self._check_redis(key, limit, window, now)

        # Fall back to in-memory
        return self._check_memory(key, limit, window, now)

    async def record_request(
        self,
        identifier: str,
        limit_type: str = "default",
    ) -> None:
        """
        Record a successful request.

        Call this after check_rate_limit returns allowed=True.

        Args:
            identifier: Unique identifier
            limit_type: Type of limit
        """
        key = f"{self.key_prefix}{limit_type}:{identifier}"
        now = time.time()

        if self._redis:
            await self._record_redis(key, now)
        else:
            self._record_memory(key, now)

    async def check_and_record(
        self,
        identifier: str,
        limit_type: str = "default",
        tier: RateLimitTier = RateLimitTier.FREE,
        endpoint: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check rate limit and record request atomically.

        Args:
            identifier: Unique identifier
            limit_type: Type of limit
            tier: API tier
            endpoint: Optional endpoint

        Returns:
            RateLimitResult with check outcome
        """
        result = await self.check_rate_limit(identifier, limit_type, tier, endpoint)

        if result.allowed:
            await self.record_request(identifier, limit_type)
            result.remaining -= 1

        return result

    async def _check_redis(
        self,
        key: str,
        limit: int,
        window: int,
        now: float
    ) -> RateLimitResult:
        """Check rate limit using Redis."""
        window_start = now - window

        # Use pipeline for atomic operation
        async with self._redis.pipeline() as pipe:
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count entries in window
            pipe.zcard(key)
            # Get oldest entry for reset time
            pipe.zrange(key, 0, 0, withscores=True)

            results = await pipe.execute()
            count = results[1]
            oldest = results[2]

        # Calculate reset time
        if oldest:
            oldest_time = oldest[0][1]
            reset_at = datetime.fromtimestamp(oldest_time + window)
        else:
            reset_at = datetime.fromtimestamp(now + window)

        # Check if blocked
        block_key = f"{key}:blocked"
        blocked_until = await self._redis.get(block_key)
        if blocked_until:
            blocked_until_ts = float(blocked_until)
            if now < blocked_until_ts:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=limit,
                    reset_at=datetime.fromtimestamp(blocked_until_ts),
                    retry_after_seconds=int(blocked_until_ts - now) + 1,
                    reason="Rate limit exceeded - temporarily blocked",
                )

        # Check limit
        if count >= limit:
            retry_after = int(oldest[0][1] + window - now) + 1 if oldest else window
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limit,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
                reason=f"Rate limit exceeded: {count}/{limit} requests",
            )

        return RateLimitResult(
            allowed=True,
            remaining=limit - count,
            limit=limit,
            reset_at=reset_at,
        )

    async def _record_redis(self, key: str, now: float) -> None:
        """Record request in Redis."""
        async with self._redis.pipeline() as pipe:
            # Add timestamp to sorted set
            pipe.zadd(key, {str(now): now})
            # Set expiry on key
            pipe.expire(key, WINDOW_DAY)  # Expire after 24h of inactivity
            await pipe.execute()

    def _check_memory(
        self,
        key: str,
        limit: int,
        window: int,
        now: float
    ) -> RateLimitResult:
        """Check rate limit using in-memory storage."""
        window_start = now - window

        # Get and clean timestamps
        timestamps = self._memory_store.get(key, [])
        timestamps = [ts for ts in timestamps if ts > window_start]
        self._memory_store[key] = timestamps

        count = len(timestamps)

        # Calculate reset time
        if timestamps:
            oldest_time = min(timestamps)
            reset_at = datetime.fromtimestamp(oldest_time + window)
        else:
            reset_at = datetime.fromtimestamp(now + window)

        # Check if blocked
        blocked_until = self._memory_blocks.get(key)
        if blocked_until and now < blocked_until:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limit,
                reset_at=datetime.fromtimestamp(blocked_until),
                retry_after_seconds=int(blocked_until - now) + 1,
                reason="Rate limit exceeded - temporarily blocked",
            )

        # Check limit
        if count >= limit:
            retry_after = int(oldest_time + window - now) + 1 if timestamps else window
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limit,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
                reason=f"Rate limit exceeded: {count}/{limit} requests",
            )

        return RateLimitResult(
            allowed=True,
            remaining=limit - count,
            limit=limit,
            reset_at=reset_at,
        )

    def _record_memory(self, key: str, now: float) -> None:
        """Record request in memory."""
        if key not in self._memory_store:
            self._memory_store[key] = []
        self._memory_store[key].append(now)

    def _get_limit_config(
        self,
        limit_type: str,
        tier: RateLimitTier,
        endpoint: Optional[str]
    ) -> Tuple[int, int]:
        """Get limit and window for given parameters."""
        # Endpoint-specific limits
        if endpoint and endpoint in ENDPOINT_LIMITS:
            limit = ENDPOINT_LIMITS[endpoint].get(
                tier,
                ENDPOINT_LIMITS[endpoint][RateLimitTier.FREE]
            )
            return limit, WINDOW_MINUTE

        # Type-specific limits
        if limit_type == "ip":
            return DEFAULT_IP_LIMIT_PER_MINUTE, WINDOW_MINUTE
        elif limit_type == "device":
            return DEFAULT_DEVICE_LIMIT_PER_DAY, WINDOW_DAY
        elif limit_type == "agent":
            return DEFAULT_AGENT_LIMIT_PER_HOUR, WINDOW_HOUR
        elif limit_type == "api":
            base_limit = TIER_LIMITS.get(tier, TIER_LIMITS[RateLimitTier.FREE])
            burst = TIER_BURST_MULTIPLIER.get(tier, 1.0)
            return int(base_limit * burst), WINDOW_MINUTE

        # Default
        return TIER_LIMITS[RateLimitTier.FREE], WINDOW_MINUTE

    async def block_identifier(
        self,
        identifier: str,
        limit_type: str,
        duration_seconds: int,
        reason: str = ""
    ) -> None:
        """
        Manually block an identifier.

        Args:
            identifier: Identifier to block
            limit_type: Type of limit
            duration_seconds: Block duration
            reason: Optional reason for logging
        """
        key = f"{self.key_prefix}{limit_type}:{identifier}"
        block_key = f"{key}:blocked"
        blocked_until = time.time() + duration_seconds

        if self._redis:
            await self._redis.set(block_key, str(blocked_until), ex=duration_seconds)
        else:
            self._memory_blocks[key] = blocked_until

        logger.warning(
            f"Blocked {limit_type} {identifier} for {duration_seconds}s. Reason: {reason}"
        )

    async def unblock_identifier(
        self,
        identifier: str,
        limit_type: str
    ) -> None:
        """Unblock an identifier."""
        key = f"{self.key_prefix}{limit_type}:{identifier}"
        block_key = f"{key}:blocked"

        if self._redis:
            await self._redis.delete(block_key)
        else:
            self._memory_blocks.pop(key, None)

        logger.info(f"Unblocked {limit_type} {identifier}")

    async def get_status(
        self,
        identifier: str,
        limit_type: str,
        tier: RateLimitTier = RateLimitTier.FREE,
    ) -> Dict[str, Any]:
        """
        Get current rate limit status for an identifier.

        Args:
            identifier: Identifier to check
            limit_type: Type of limit
            tier: API tier

        Returns:
            Dictionary with status information
        """
        key = f"{self.key_prefix}{limit_type}:{identifier}"
        limit, window = self._get_limit_config(limit_type, tier, None)
        now = time.time()
        window_start = now - window

        if self._redis:
            count = await self._redis.zcount(key, window_start, now)
            blocked_until = await self._redis.get(f"{key}:blocked")
        else:
            timestamps = self._memory_store.get(key, [])
            count = len([ts for ts in timestamps if ts > window_start])
            blocked_until = self._memory_blocks.get(key)

        return {
            "identifier": identifier,
            "limit_type": limit_type,
            "tier": tier.value,
            "current_count": count,
            "limit": limit,
            "remaining": max(0, limit - count),
            "window_seconds": window,
            "blocked": blocked_until is not None and float(blocked_until or 0) > now,
            "blocked_until": datetime.fromtimestamp(float(blocked_until)).isoformat() if blocked_until else None,
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        if self._redis:
            keys = await self._redis.keys(f"{self.key_prefix}*")
            return {
                "backend": "redis",
                "total_keys": len(keys),
                "key_prefix": self.key_prefix,
            }
        else:
            return {
                "backend": "memory",
                "total_keys": len(self._memory_store),
                "blocked_identifiers": len(self._memory_blocks),
            }

    def reset_memory_store(self) -> None:
        """Reset in-memory store (for testing)."""
        self._memory_store.clear()
        self._memory_blocks.clear()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def check_all_limits(
    limiter: RateLimiter,
    ip: str,
    device_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    tier: RateLimitTier = RateLimitTier.FREE,
    endpoint: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Check all applicable rate limits at once.

    Args:
        limiter: RateLimiter instance
        ip: Source IP address
        device_id: Optional device identifier
        agent_id: Optional agent identifier
        tier: API tier
        endpoint: Optional endpoint name

    Returns:
        Tuple of (allowed, limit_type_that_blocked, retry_after_seconds)
    """
    # Check IP limit
    result = await limiter.check_rate_limit(ip, "ip", tier, endpoint)
    if not result.allowed:
        return False, "ip", result.retry_after_seconds

    # Check device limit if provided
    if device_id:
        result = await limiter.check_rate_limit(device_id, "device", tier, endpoint)
        if not result.allowed:
            return False, "device", result.retry_after_seconds

    # Check agent limit if provided
    if agent_id:
        result = await limiter.check_rate_limit(agent_id, "agent", tier, endpoint)
        if not result.allowed:
            return False, "agent", result.retry_after_seconds

    return True, None, None
