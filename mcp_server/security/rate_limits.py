"""
Rate Limiting Module (NOW-111, NOW-165)

IP, device, and API tier rate limiting with sliding window implementation.

Features:
- Per-IP rate limiting (50 tasks/day)
- Per-device rate limiting (20 tasks/day)
- API tier-based rate limiting (FREE to ENTERPRISE)
- Sliding window algorithm for accurate rate limiting
- Automatic cleanup of stale entries
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitTier(str, Enum):
    """API rate limit tiers for different subscription levels."""

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

# Burst allowance multiplier (allows short bursts above limit)
TIER_BURST_MULTIPLIER: Dict[RateLimitTier, float] = {
    RateLimitTier.FREE: 1.0,  # No burst for free tier
    RateLimitTier.STARTER: 1.5,  # 50% burst allowance
    RateLimitTier.GROWTH: 2.0,  # 100% burst allowance
    RateLimitTier.ENTERPRISE: 3.0,  # 200% burst allowance
}

# Task creation limits
TASK_LIMITS = {
    "per_ip_daily": 50,
    "per_device_daily": 20,
    "per_agent_hourly": 100,
}

# Window sizes
WINDOW_SIZES = {
    "minute": 60,  # 1 minute in seconds
    "hour": 3600,  # 1 hour in seconds
    "day": 86400,  # 24 hours in seconds
}

# Cleanup interval (seconds)
CLEANUP_INTERVAL = 300  # 5 minutes


@dataclass
class SlidingWindowState:
    """State for sliding window rate limiting."""

    identifier: str
    window_size: int  # seconds
    max_requests: int
    timestamps: List[float] = field(default_factory=list)
    blocked_until: Optional[float] = None

    def cleanup_old_timestamps(self, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window_size
        self.timestamps = [ts for ts in self.timestamps if ts > cutoff]

    def get_request_count(self, now: float) -> int:
        """Get number of requests in current window."""
        self.cleanup_old_timestamps(now)
        return len(self.timestamps)

    def record_request(self, now: float) -> None:
        """Record a new request timestamp."""
        self.timestamps.append(now)

    def is_blocked(self, now: float) -> bool:
        """Check if currently blocked due to previous violations."""
        if self.blocked_until is None:
            return False
        if now >= self.blocked_until:
            self.blocked_until = None
            return False
        return True

    def block_for(self, seconds: float, now: float) -> None:
        """Block this identifier for a duration."""
        self.blocked_until = now + seconds


@dataclass
class TaskLimitState:
    """State for task creation limits."""

    identifier: str
    daily_count: int = 0
    hourly_count: int = 0
    daily_reset: float = 0.0
    hourly_reset: float = 0.0

    def reset_if_needed(self, now: float) -> None:
        """Reset counters if window has passed."""
        if now >= self.daily_reset:
            self.daily_count = 0
            self.daily_reset = now + WINDOW_SIZES["day"]
        if now >= self.hourly_reset:
            self.hourly_count = 0
            self.hourly_reset = now + WINDOW_SIZES["hour"]

    def increment(self, now: float) -> None:
        """Increment task counters."""
        self.reset_if_needed(now)
        self.daily_count += 1
        self.hourly_count += 1


class RateLimiter:
    """
    Manages rate limiting across multiple dimensions.

    Implements sliding window rate limiting for accurate request counting
    without the boundary issues of fixed windows.

    Thread-safe for concurrent access.
    """

    def __init__(self, cleanup_interval: int = CLEANUP_INTERVAL):
        """
        Initialize the rate limiter.

        Args:
            cleanup_interval: Seconds between automatic cleanup runs
        """
        self._lock = threading.RLock()
        self._ip_limits: Dict[str, SlidingWindowState] = {}
        self._device_limits: Dict[str, TaskLimitState] = {}
        self._api_limits: Dict[str, SlidingWindowState] = {}
        self._agent_limits: Dict[str, TaskLimitState] = {}
        self._ip_task_limits: Dict[str, TaskLimitState] = {}

        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

        logger.info(
            "RateLimiter initialized with cleanup_interval=%d", cleanup_interval
        )

    def _maybe_cleanup(self) -> None:
        """Run periodic cleanup if enough time has passed."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        cleaned = 0

        # Cleanup stale IP limits
        stale_ips = [
            ip
            for ip, state in self._ip_limits.items()
            if state.get_request_count(now) == 0 and not state.is_blocked(now)
        ]
        for ip in stale_ips:
            del self._ip_limits[ip]
            cleaned += 1

        # Cleanup stale API limits
        stale_apis = [
            key
            for key, state in self._api_limits.items()
            if state.get_request_count(now) == 0 and not state.is_blocked(now)
        ]
        for key in stale_apis:
            del self._api_limits[key]
            cleaned += 1

        if cleaned > 0:
            logger.debug("Cleaned up %d stale rate limit entries", cleaned)

    def check_ip_limit(self, ip: str) -> Tuple[bool, Optional[int]]:
        """
        Check and update IP rate limit.

        Args:
            ip: The IP address to check

        Returns:
            Tuple of (allowed, retry_after_seconds)
            - allowed: True if request should be permitted
            - retry_after_seconds: Seconds until next allowed request (if blocked)
        """
        with self._lock:
            self._maybe_cleanup()
            now = time.time()

            # Get or create state
            if ip not in self._ip_limits:
                self._ip_limits[ip] = SlidingWindowState(
                    identifier=ip,
                    window_size=WINDOW_SIZES["minute"],
                    max_requests=TIER_LIMITS[
                        RateLimitTier.FREE
                    ],  # Default to free tier
                )

            state = self._ip_limits[ip]

            # Check if blocked
            if state.is_blocked(now):
                retry_after = int(state.blocked_until - now) + 1
                logger.warning(
                    "IP %s is blocked, retry after %d seconds", ip, retry_after
                )
                return False, retry_after

            # Check current request count
            current_count = state.get_request_count(now)

            if current_count >= state.max_requests:
                # Calculate retry time based on oldest request in window
                if state.timestamps:
                    oldest = min(state.timestamps)
                    retry_after = int((oldest + state.window_size) - now) + 1
                else:
                    retry_after = state.window_size

                logger.info(
                    "IP %s rate limited: %d/%d requests in window",
                    ip,
                    current_count,
                    state.max_requests,
                )
                return False, max(1, retry_after)

            # Allow request
            state.record_request(now)
            return True, None

    def check_device_limit(self, device_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check device task creation limit.

        Args:
            device_id: The device identifier to check

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        with self._lock:
            now = time.time()

            if device_id not in self._device_limits:
                self._device_limits[device_id] = TaskLimitState(
                    identifier=device_id,
                    daily_reset=now + WINDOW_SIZES["day"],
                    hourly_reset=now + WINDOW_SIZES["hour"],
                )

            state = self._device_limits[device_id]
            state.reset_if_needed(now)

            limit = TASK_LIMITS["per_device_daily"]

            if state.daily_count >= limit:
                retry_after = int(state.daily_reset - now) + 1
                logger.info(
                    "Device %s rate limited: %d/%d tasks today",
                    device_id[:16],
                    state.daily_count,
                    limit,
                )
                return False, retry_after

            return True, None

    def check_api_limit(
        self, api_key: str, tier: RateLimitTier = RateLimitTier.FREE
    ) -> Tuple[bool, Optional[int]]:
        """
        Check API tier rate limit.

        Args:
            api_key: The API key to check
            tier: The subscription tier for this API key

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        with self._lock:
            self._maybe_cleanup()
            now = time.time()

            # Get tier limits
            base_limit = TIER_LIMITS.get(tier, TIER_LIMITS[RateLimitTier.FREE])
            burst_multiplier = TIER_BURST_MULTIPLIER.get(tier, 1.0)
            burst_limit = int(base_limit * burst_multiplier)

            if api_key not in self._api_limits:
                self._api_limits[api_key] = SlidingWindowState(
                    identifier=api_key,
                    window_size=WINDOW_SIZES["minute"],
                    max_requests=burst_limit,
                )

            state = self._api_limits[api_key]
            # Update max_requests in case tier changed
            state.max_requests = burst_limit

            # Check if blocked
            if state.is_blocked(now):
                retry_after = int(state.blocked_until - now) + 1
                return False, retry_after

            current_count = state.get_request_count(now)

            if current_count >= state.max_requests:
                if state.timestamps:
                    oldest = min(state.timestamps)
                    retry_after = int((oldest + state.window_size) - now) + 1
                else:
                    retry_after = state.window_size

                logger.info(
                    "API key %s... rate limited (tier=%s): %d/%d requests",
                    api_key[:8],
                    tier.value,
                    current_count,
                    state.max_requests,
                )
                return False, max(1, retry_after)

            state.record_request(now)
            return True, None

    def check_agent_limit(self, agent_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check agent hourly task creation limit.

        Args:
            agent_id: The agent identifier to check

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        with self._lock:
            now = time.time()

            if agent_id not in self._agent_limits:
                self._agent_limits[agent_id] = TaskLimitState(
                    identifier=agent_id,
                    daily_reset=now + WINDOW_SIZES["day"],
                    hourly_reset=now + WINDOW_SIZES["hour"],
                )

            state = self._agent_limits[agent_id]
            state.reset_if_needed(now)

            limit = TASK_LIMITS["per_agent_hourly"]

            if state.hourly_count >= limit:
                retry_after = int(state.hourly_reset - now) + 1
                logger.info(
                    "Agent %s rate limited: %d/%d tasks this hour",
                    agent_id[:16],
                    state.hourly_count,
                    limit,
                )
                return False, retry_after

            return True, None

    def record_task_creation(
        self, ip: str, device_id: Optional[str], agent_id: str
    ) -> None:
        """
        Record task creation for all relevant limits.

        Call this after successfully creating a task.

        Args:
            ip: Source IP address
            device_id: Device identifier (optional)
            agent_id: Agent/requester identifier
        """
        with self._lock:
            now = time.time()

            # Record IP task
            if ip not in self._ip_task_limits:
                self._ip_task_limits[ip] = TaskLimitState(
                    identifier=ip,
                    daily_reset=now + WINDOW_SIZES["day"],
                    hourly_reset=now + WINDOW_SIZES["hour"],
                )
            self._ip_task_limits[ip].increment(now)

            # Record device task
            if device_id:
                if device_id not in self._device_limits:
                    self._device_limits[device_id] = TaskLimitState(
                        identifier=device_id,
                        daily_reset=now + WINDOW_SIZES["day"],
                        hourly_reset=now + WINDOW_SIZES["hour"],
                    )
                self._device_limits[device_id].increment(now)

            # Record agent task
            if agent_id not in self._agent_limits:
                self._agent_limits[agent_id] = TaskLimitState(
                    identifier=agent_id,
                    daily_reset=now + WINDOW_SIZES["day"],
                    hourly_reset=now + WINDOW_SIZES["hour"],
                )
            self._agent_limits[agent_id].increment(now)

            logger.debug(
                "Recorded task creation: ip=%s, device=%s, agent=%s",
                ip,
                device_id[:16] if device_id else None,
                agent_id[:16],
            )

    def check_ip_task_limit(self, ip: str) -> Tuple[bool, Optional[int]]:
        """
        Check IP daily task creation limit.

        Args:
            ip: The IP address to check

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        with self._lock:
            now = time.time()

            if ip not in self._ip_task_limits:
                return True, None

            state = self._ip_task_limits[ip]
            state.reset_if_needed(now)

            limit = TASK_LIMITS["per_ip_daily"]

            if state.daily_count >= limit:
                retry_after = int(state.daily_reset - now) + 1
                logger.info(
                    "IP %s task limited: %d/%d tasks today",
                    ip,
                    state.daily_count,
                    limit,
                )
                return False, retry_after

            return True, None

    def get_remaining(self, identifier: str, limit_type: str) -> int:
        """
        Get remaining requests/tasks for an identifier.

        Args:
            identifier: The identifier to check (IP, device ID, API key)
            limit_type: Type of limit ("ip", "device", "api", "agent", "ip_task")

        Returns:
            Number of remaining requests/tasks in current window
        """
        with self._lock:
            now = time.time()

            if limit_type == "ip":
                if identifier not in self._ip_limits:
                    return TIER_LIMITS[RateLimitTier.FREE]
                state = self._ip_limits[identifier]
                return max(0, state.max_requests - state.get_request_count(now))

            elif limit_type == "device":
                if identifier not in self._device_limits:
                    return TASK_LIMITS["per_device_daily"]
                state = self._device_limits[identifier]
                state.reset_if_needed(now)
                return max(0, TASK_LIMITS["per_device_daily"] - state.daily_count)

            elif limit_type == "api":
                if identifier not in self._api_limits:
                    return TIER_LIMITS[RateLimitTier.FREE]
                state = self._api_limits[identifier]
                return max(0, state.max_requests - state.get_request_count(now))

            elif limit_type == "agent":
                if identifier not in self._agent_limits:
                    return TASK_LIMITS["per_agent_hourly"]
                state = self._agent_limits[identifier]
                state.reset_if_needed(now)
                return max(0, TASK_LIMITS["per_agent_hourly"] - state.hourly_count)

            elif limit_type == "ip_task":
                if identifier not in self._ip_task_limits:
                    return TASK_LIMITS["per_ip_daily"]
                state = self._ip_task_limits[identifier]
                state.reset_if_needed(now)
                return max(0, TASK_LIMITS["per_ip_daily"] - state.daily_count)

            else:
                logger.warning("Unknown limit type: %s", limit_type)
                return 0

    def get_limit_status(self, identifier: str, limit_type: str) -> Dict:
        """
        Get detailed status for a rate limit.

        Args:
            identifier: The identifier to check
            limit_type: Type of limit

        Returns:
            Dict with limit details
        """
        with self._lock:
            now = time.time()
            remaining = self.get_remaining(identifier, limit_type)

            result = {
                "identifier": identifier,
                "limit_type": limit_type,
                "remaining": remaining,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if limit_type in ("ip", "api"):
                states = self._ip_limits if limit_type == "ip" else self._api_limits
                if identifier in states:
                    state = states[identifier]
                    result["window_size"] = state.window_size
                    result["max_requests"] = state.max_requests
                    result["current_count"] = state.get_request_count(now)
                    result["blocked"] = state.is_blocked(now)
                    if state.blocked_until and state.blocked_until > now:
                        result["blocked_until"] = datetime.fromtimestamp(
                            state.blocked_until
                        ).isoformat()

            elif limit_type in ("device", "agent", "ip_task"):
                if limit_type == "device":
                    states = self._device_limits
                    limit_key = "per_device_daily"
                elif limit_type == "agent":
                    states = self._agent_limits
                    limit_key = "per_agent_hourly"
                else:
                    states = self._ip_task_limits
                    limit_key = "per_ip_daily"

                if identifier in states:
                    state = states[identifier]
                    result["daily_count"] = state.daily_count
                    result["hourly_count"] = state.hourly_count
                    result["daily_limit"] = TASK_LIMITS.get(limit_key, 0)
                    result["daily_reset"] = datetime.fromtimestamp(
                        state.daily_reset
                    ).isoformat()

            return result

    def block_identifier(
        self, identifier: str, limit_type: str, duration_seconds: int, reason: str = ""
    ) -> None:
        """
        Manually block an identifier for a duration.

        Useful for abuse prevention or manual intervention.

        Args:
            identifier: The identifier to block
            limit_type: Type of limit ("ip" or "api")
            duration_seconds: How long to block
            reason: Optional reason for logging
        """
        with self._lock:
            now = time.time()

            if limit_type == "ip":
                if identifier not in self._ip_limits:
                    self._ip_limits[identifier] = SlidingWindowState(
                        identifier=identifier,
                        window_size=WINDOW_SIZES["minute"],
                        max_requests=TIER_LIMITS[RateLimitTier.FREE],
                    )
                self._ip_limits[identifier].block_for(duration_seconds, now)

            elif limit_type == "api":
                if identifier not in self._api_limits:
                    self._api_limits[identifier] = SlidingWindowState(
                        identifier=identifier,
                        window_size=WINDOW_SIZES["minute"],
                        max_requests=TIER_LIMITS[RateLimitTier.FREE],
                    )
                self._api_limits[identifier].block_for(duration_seconds, now)

            logger.warning(
                "Blocked %s %s for %d seconds. Reason: %s",
                limit_type,
                identifier,
                duration_seconds,
                reason or "manual block",
            )

    def reset_identifier(self, identifier: str, limit_type: str) -> None:
        """
        Reset rate limits for an identifier.

        Args:
            identifier: The identifier to reset
            limit_type: Type of limit to reset
        """
        with self._lock:
            if limit_type == "ip":
                if identifier in self._ip_limits:
                    del self._ip_limits[identifier]
            elif limit_type == "device":
                if identifier in self._device_limits:
                    del self._device_limits[identifier]
            elif limit_type == "api":
                if identifier in self._api_limits:
                    del self._api_limits[identifier]
            elif limit_type == "agent":
                if identifier in self._agent_limits:
                    del self._agent_limits[identifier]
            elif limit_type == "ip_task":
                if identifier in self._ip_task_limits:
                    del self._ip_task_limits[identifier]

            logger.info("Reset %s rate limit for %s", limit_type, identifier)

    def get_stats(self) -> Dict:
        """
        Get overall rate limiter statistics.

        Returns:
            Dict with statistics about tracked identifiers
        """
        with self._lock:
            return {
                "ip_limits_tracked": len(self._ip_limits),
                "device_limits_tracked": len(self._device_limits),
                "api_limits_tracked": len(self._api_limits),
                "agent_limits_tracked": len(self._agent_limits),
                "ip_task_limits_tracked": len(self._ip_task_limits),
                "last_cleanup": datetime.fromtimestamp(self._last_cleanup).isoformat(),
            }


# Convenience function for checking all limits at once
def check_all_limits(
    limiter: RateLimiter,
    ip: str,
    device_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    api_key: Optional[str] = None,
    api_tier: RateLimitTier = RateLimitTier.FREE,
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Check all applicable rate limits at once.

    Args:
        limiter: The RateLimiter instance
        ip: Source IP address
        device_id: Optional device identifier
        agent_id: Optional agent identifier
        api_key: Optional API key
        api_tier: API subscription tier

    Returns:
        Tuple of (allowed, limit_type_that_blocked, retry_after_seconds)
    """
    # Check IP rate limit
    allowed, retry = limiter.check_ip_limit(ip)
    if not allowed:
        return False, "ip", retry

    # Check IP task limit
    allowed, retry = limiter.check_ip_task_limit(ip)
    if not allowed:
        return False, "ip_task", retry

    # Check device limit if provided
    if device_id:
        allowed, retry = limiter.check_device_limit(device_id)
        if not allowed:
            return False, "device", retry

    # Check agent limit if provided
    if agent_id:
        allowed, retry = limiter.check_agent_limit(agent_id)
        if not allowed:
            return False, "agent", retry

    # Check API limit if key provided
    if api_key:
        allowed, retry = limiter.check_api_limit(api_key, api_tier)
        if not allowed:
            return False, "api", retry

    return True, None, None
