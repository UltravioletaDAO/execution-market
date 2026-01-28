"""
Behavioral Analysis Module for Fraud Detection

Detects fraudulent behavioral patterns:
1. Velocity abuse - Completing too many tasks too quickly
2. Collusion - Suspicious agent-worker pairing patterns
3. Multi-account detection - Same device/IP across multiple accounts
4. Gaming patterns - Unusual task selection, cherry-picking

Complements the existing fraud_detection.py module with
additional behavioral signals.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Velocity thresholds
MAX_TASKS_PER_HOUR = 5
MAX_TASKS_PER_DAY = 30
SUSPICIOUS_COMPLETION_RATE = 0.95  # 95% success rate is suspicious

# Collusion thresholds
SUSPICIOUS_PAIRING_COUNT = 5  # Same agent-worker pair 5+ times
PAIRING_WINDOW_DAYS = 30

# Multi-account thresholds
MAX_ACCOUNTS_PER_DEVICE = 1
MAX_ACCOUNTS_PER_IP = 3

# Value thresholds
HIGH_VALUE_BOUNTY_PERCENTILE = 0.9  # Top 10% of bounties


# =============================================================================
# DATA CLASSES
# =============================================================================

class BehavioralFlag(str, Enum):
    """Behavioral warning flags."""
    VELOCITY_ABUSE = "velocity_abuse"
    CHERRY_PICKING = "cherry_picking"
    COLLUSION = "collusion"
    MULTI_ACCOUNT = "multi_account"
    IMPOSSIBLE_COMPLETION = "impossible_completion"
    VALUE_MANIPULATION = "value_manipulation"
    COORDINATED_ACTIVITY = "coordinated_activity"
    ABNORMAL_HOURS = "abnormal_hours"
    GEOGRAPHIC_IMPOSSIBILITY = "geographic_impossibility"


@dataclass
class BehavioralResult:
    """Result of behavioral analysis."""
    risk_score: float  # 0.0 to 1.0
    flags: List[BehavioralFlag] = field(default_factory=list)

    # Specific findings
    velocity_abuse: bool = False
    collusion_suspected: bool = False
    multi_account_suspected: bool = False

    # Details
    reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_score": round(self.risk_score, 4),
            "flags": [f.value for f in self.flags],
            "velocity_abuse": self.velocity_abuse,
            "collusion_suspected": self.collusion_suspected,
            "multi_account_suspected": self.multi_account_suspected,
            "reasons": self.reasons,
        }


@dataclass
class ExecutorProfile:
    """Behavioral profile for an executor/worker."""
    executor_id: str
    first_seen: datetime
    last_seen: datetime

    # Activity metrics
    total_tasks: int = 0
    completed_tasks: int = 0
    disputed_tasks: int = 0
    average_completion_time_sec: float = 0.0

    # Temporal patterns
    hourly_activity: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    daily_activity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Connection patterns
    agents_worked_with: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    categories_worked: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Device/IP tracking
    devices: Set[str] = field(default_factory=set)
    ip_addresses: Set[str] = field(default_factory=set)

    # Value metrics
    total_earnings: float = 0.0
    average_bounty: float = 0.0

    # Flags
    flags: Set[BehavioralFlag] = field(default_factory=set)
    risk_score: float = 0.0


@dataclass
class TaskRecord:
    """Record of a task for behavioral analysis."""
    task_id: str
    agent_id: str
    executor_id: Optional[str]
    bounty_usd: float
    category: str
    created_at: datetime
    accepted_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None


# =============================================================================
# BEHAVIORAL ANALYZER CLASS
# =============================================================================

class BehavioralAnalyzer:
    """
    Analyzes behavioral patterns for fraud detection.

    Tracks executor activity over time to detect:
    - Velocity abuse (too many tasks too fast)
    - Collusion (suspicious agent-worker patterns)
    - Multi-account abuse
    - Gaming/manipulation patterns
    """

    def __init__(
        self,
        max_tasks_per_hour: int = MAX_TASKS_PER_HOUR,
        max_tasks_per_day: int = MAX_TASKS_PER_DAY,
        suspicious_pairing_count: int = SUSPICIOUS_PAIRING_COUNT,
    ):
        """
        Initialize behavioral analyzer.

        Args:
            max_tasks_per_hour: Maximum tasks allowed per hour
            max_tasks_per_day: Maximum tasks allowed per day
            suspicious_pairing_count: Threshold for suspicious agent-worker pairing
        """
        self.max_tasks_per_hour = max_tasks_per_hour
        self.max_tasks_per_day = max_tasks_per_day
        self.suspicious_pairing_count = suspicious_pairing_count

        # In-memory storage (use Redis/DB in production)
        self._executor_profiles: Dict[str, ExecutorProfile] = {}
        self._task_records: Dict[str, TaskRecord] = {}
        self._device_to_executors: Dict[str, Set[str]] = defaultdict(set)
        self._ip_to_executors: Dict[str, Set[str]] = defaultdict(set)
        self._agent_worker_pairs: Dict[Tuple[str, str], int] = defaultdict(int)

        # Recent activity tracking
        self._hourly_activity: Dict[str, List[datetime]] = defaultdict(list)
        self._daily_activity: Dict[str, List[datetime]] = defaultdict(list)

        logger.info("BehavioralAnalyzer initialized")

    async def analyze_submission(
        self,
        executor_id: str,
        agent_id: str,
        task_id: str,
        bounty_usd: Optional[float] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> BehavioralResult:
        """
        Analyze a submission for behavioral fraud signals.

        Args:
            executor_id: Worker's ID
            agent_id: Agent's ID
            task_id: Task ID
            bounty_usd: Task bounty value
            device_id: Device identifier
            ip_address: Client IP address

        Returns:
            BehavioralResult with analysis findings
        """
        flags: List[BehavioralFlag] = []
        reasons: List[str] = []
        risk_scores: List[float] = []
        details: Dict[str, Any] = {}

        velocity_abuse = False
        collusion_suspected = False
        multi_account_suspected = False

        now = datetime.now(timezone.utc)

        # Ensure profile exists
        profile = self._get_or_create_profile(executor_id)

        # 1. Check velocity abuse
        velocity_result = await self.detect_velocity_abuse(executor_id)
        if velocity_result["suspicious"]:
            velocity_abuse = True
            flags.append(BehavioralFlag.VELOCITY_ABUSE)
            reasons.append(velocity_result["reason"])
            risk_scores.append(velocity_result["risk_score"])
            details["velocity"] = velocity_result

        # 2. Check collusion patterns
        collusion_result = await self.detect_collusion(executor_id, agent_id)
        if collusion_result["suspicious"]:
            collusion_suspected = True
            flags.append(BehavioralFlag.COLLUSION)
            reasons.append(collusion_result["reason"])
            risk_scores.append(collusion_result["risk_score"])
            details["collusion"] = collusion_result

        # 3. Check multi-account (device fingerprint)
        if device_id:
            device_result = await self.check_device_fingerprint(executor_id, device_id)
            if device_result["suspicious"]:
                multi_account_suspected = True
                flags.append(BehavioralFlag.MULTI_ACCOUNT)
                reasons.append(device_result["reason"])
                risk_scores.append(device_result["risk_score"])
                details["device"] = device_result

        # 4. Check multi-account (IP address)
        if ip_address:
            ip_result = await self._check_ip_patterns(executor_id, ip_address)
            if ip_result["suspicious"]:
                if not multi_account_suspected:
                    multi_account_suspected = True
                    flags.append(BehavioralFlag.MULTI_ACCOUNT)
                reasons.append(ip_result["reason"])
                risk_scores.append(ip_result["risk_score"])
                details["ip"] = ip_result

        # Update tracking
        self._record_activity(executor_id, agent_id, device_id, ip_address, now)

        # Calculate overall risk
        overall_risk = max(risk_scores) if risk_scores else 0.0

        return BehavioralResult(
            risk_score=overall_risk,
            flags=flags,
            velocity_abuse=velocity_abuse,
            collusion_suspected=collusion_suspected,
            multi_account_suspected=multi_account_suspected,
            reasons=reasons,
            details=details,
        )

    async def detect_velocity_abuse(self, executor_id: str) -> Dict[str, Any]:
        """
        Detect if executor is completing tasks too quickly.

        Velocity abuse indicators:
        1. Too many tasks per hour
        2. Too many tasks per day
        3. Suspiciously high completion rate

        Args:
            executor_id: Worker's ID

        Returns:
            Dictionary with detection results
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        # Get recent activity
        hourly_tasks = self._hourly_activity.get(executor_id, [])
        daily_tasks = self._daily_activity.get(executor_id, [])

        # Clean old entries
        hourly_tasks = [t for t in hourly_tasks if t > one_hour_ago]
        daily_tasks = [t for t in daily_tasks if t > one_day_ago]

        self._hourly_activity[executor_id] = hourly_tasks
        self._daily_activity[executor_id] = daily_tasks

        # Check hourly limit
        if len(hourly_tasks) >= self.max_tasks_per_hour:
            return {
                "suspicious": True,
                "reason": f"Hourly velocity exceeded: {len(hourly_tasks)} tasks in 1 hour (max: {self.max_tasks_per_hour})",
                "risk_score": 0.8,
                "hourly_count": len(hourly_tasks),
                "daily_count": len(daily_tasks),
            }

        # Check daily limit
        if len(daily_tasks) >= self.max_tasks_per_day:
            return {
                "suspicious": True,
                "reason": f"Daily velocity exceeded: {len(daily_tasks)} tasks in 24 hours (max: {self.max_tasks_per_day})",
                "risk_score": 0.7,
                "hourly_count": len(hourly_tasks),
                "daily_count": len(daily_tasks),
            }

        # Check for approaching limits (warning level)
        if len(hourly_tasks) >= self.max_tasks_per_hour * 0.8:
            return {
                "suspicious": False,
                "reason": f"Approaching hourly limit: {len(hourly_tasks)}/{self.max_tasks_per_hour}",
                "risk_score": 0.3,
                "hourly_count": len(hourly_tasks),
                "daily_count": len(daily_tasks),
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "hourly_count": len(hourly_tasks),
            "daily_count": len(daily_tasks),
        }

    async def detect_collusion(
        self,
        executor_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Detect collusion patterns between executor and agent.

        Collusion indicators:
        1. Same agent-worker pair repeatedly
        2. Unusually high approval rate between pair
        3. Coordinated timing patterns

        Args:
            executor_id: Worker's ID
            agent_id: Agent's ID

        Returns:
            Dictionary with detection results
        """
        pair_key = (agent_id, executor_id)
        pair_count = self._agent_worker_pairs.get(pair_key, 0)

        # Update count
        self._agent_worker_pairs[pair_key] = pair_count + 1
        new_count = pair_count + 1

        if new_count >= self.suspicious_pairing_count:
            return {
                "suspicious": True,
                "reason": f"Repeated pairing: agent {agent_id[:8]}... and worker {executor_id[:8]}... paired {new_count} times",
                "risk_score": min(0.9, 0.5 + (new_count - self.suspicious_pairing_count) * 0.1),
                "pair_count": new_count,
                "threshold": self.suspicious_pairing_count,
            }

        # Warning level
        if new_count >= self.suspicious_pairing_count * 0.6:
            return {
                "suspicious": False,
                "reason": f"Multiple pairings: {new_count} (threshold: {self.suspicious_pairing_count})",
                "risk_score": 0.3,
                "pair_count": new_count,
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "pair_count": new_count,
        }

    async def check_device_fingerprint(
        self,
        executor_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """
        Check for multiple accounts using same device.

        Args:
            executor_id: Worker's ID
            device_id: Device fingerprint

        Returns:
            Dictionary with detection results
        """
        # Track device to executor mapping
        existing_executors = self._device_to_executors.get(device_id, set())

        if executor_id not in existing_executors:
            self._device_to_executors[device_id].add(executor_id)
            existing_executors = self._device_to_executors[device_id]

        # Check for multi-account
        if len(existing_executors) > MAX_ACCOUNTS_PER_DEVICE:
            other_accounts = existing_executors - {executor_id}
            return {
                "suspicious": True,
                "reason": f"Device {device_id[:16]}... used by {len(existing_executors)} accounts",
                "risk_score": 0.9,
                "accounts_on_device": len(existing_executors),
                "other_accounts": list(other_accounts)[:5],  # Limit for privacy
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "accounts_on_device": len(existing_executors),
        }

    async def _check_ip_patterns(
        self,
        executor_id: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """Check for multiple accounts from same IP."""
        # Track IP to executor mapping
        existing_executors = self._ip_to_executors.get(ip_address, set())

        if executor_id not in existing_executors:
            self._ip_to_executors[ip_address].add(executor_id)
            existing_executors = self._ip_to_executors[ip_address]

        # Check for multi-account (with higher threshold for IPs)
        if len(existing_executors) > MAX_ACCOUNTS_PER_IP:
            other_accounts = existing_executors - {executor_id}
            return {
                "suspicious": True,
                "reason": f"IP {ip_address} used by {len(existing_executors)} accounts",
                "risk_score": 0.7,
                "accounts_on_ip": len(existing_executors),
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "accounts_on_ip": len(existing_executors),
        }

    def _get_or_create_profile(self, executor_id: str) -> ExecutorProfile:
        """Get or create executor profile."""
        if executor_id not in self._executor_profiles:
            now = datetime.now(timezone.utc)
            self._executor_profiles[executor_id] = ExecutorProfile(
                executor_id=executor_id,
                first_seen=now,
                last_seen=now,
            )
        return self._executor_profiles[executor_id]

    def _record_activity(
        self,
        executor_id: str,
        agent_id: str,
        device_id: Optional[str],
        ip_address: Optional[str],
        timestamp: datetime
    ) -> None:
        """Record activity for tracking."""
        # Update hourly/daily activity
        self._hourly_activity[executor_id].append(timestamp)
        self._daily_activity[executor_id].append(timestamp)

        # Update profile
        profile = self._get_or_create_profile(executor_id)
        profile.last_seen = timestamp
        profile.total_tasks += 1
        profile.agents_worked_with[agent_id] += 1

        if device_id:
            profile.devices.add(device_id)
        if ip_address:
            profile.ip_addresses.add(ip_address)

        # Update hour of day activity
        hour = timestamp.hour
        profile.hourly_activity[hour] += 1

    def get_executor_profile(self, executor_id: str) -> Optional[ExecutorProfile]:
        """Get profile for an executor."""
        return self._executor_profiles.get(executor_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get behavioral analyzer statistics."""
        return {
            "total_profiles": len(self._executor_profiles),
            "device_mappings": len(self._device_to_executors),
            "ip_mappings": len(self._ip_to_executors),
            "agent_worker_pairs": len(self._agent_worker_pairs),
        }

    def clear_executor_data(self, executor_id: str) -> None:
        """Clear all data for an executor (GDPR)."""
        self._executor_profiles.pop(executor_id, None)
        self._hourly_activity.pop(executor_id, None)
        self._daily_activity.pop(executor_id, None)

        # Remove from device/IP mappings
        for device_executors in self._device_to_executors.values():
            device_executors.discard(executor_id)
        for ip_executors in self._ip_to_executors.values():
            ip_executors.discard(executor_id)

        # Remove pair records
        keys_to_remove = [k for k in self._agent_worker_pairs if k[1] == executor_id]
        for key in keys_to_remove:
            del self._agent_worker_pairs[key]
