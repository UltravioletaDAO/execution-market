"""
describe.net Seals Integration - Types and Definitions (NOW-166 to NOW-170)

Defines all seal types, badges, and their criteria for the Execution Market integration.

Seal Philosophy:
- Seals are earned through consistent behavior, not single events
- Each seal has clear, measurable criteria
- Seals can be revoked if behavior changes
- Bidirectional: both workers AND requesters earn seals
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class WorkerSealType(str, Enum):
    """
    Seals that workers can earn based on task performance.

    These seals are visible to agents when selecting workers,
    and influence matching priority.
    """

    SKILLFUL = "skillful"  # High quality work consistently
    RELIABLE = "reliable"  # Shows up, completes tasks
    THOROUGH = "thorough"  # Goes above minimum requirements
    ON_TIME = "on_time"  # Consistently meets deadlines


class RequesterSealType(str, Enum):
    """
    Seals that requesters (agents) can earn based on their behavior.

    Workers can filter tasks by requester seals to avoid bad actors.
    This creates bidirectional accountability.
    """

    FAIR_EVALUATOR = "fair_evaluator"  # Accepts reasonable work
    CLEAR_INSTRUCTIONS = "clear_instructions"  # Writes good task specs
    FAST_PAYMENT = "fast_payment"  # Releases payment quickly


class BadgeType(str, Enum):
    """
    Fusion badges earned through long-term excellence.

    These are harder to earn and represent sustained performance.
    """

    MASTER_WORKER = "master_worker"  # 50+ tasks, 6+ months, high rep
    TRUSTED_REQUESTER = "trusted_requester"  # 100+ tasks posted, good ratings
    EARLY_ADOPTER = "early_adopter"  # First 1000 users
    SPECIALIST = "specialist"  # 20+ tasks in single category


class SealStatus(str, Enum):
    """Status of a seal."""

    ACTIVE = "active"  # Seal is valid and displayed
    PENDING = "pending"  # Criteria met, awaiting confirmation
    REVOKED = "revoked"  # Seal was removed due to behavior change
    EXPIRED = "expired"  # Seal expired (if time-limited)


@dataclass
class SealCriteria:
    """
    Criteria required to earn a specific seal.

    All conditions must be met to earn the seal.
    If conditions are no longer met, seal may be revoked.
    """

    min_tasks: int = 0  # Minimum completed tasks
    min_success_rate: float = 0.0  # 0-1 success rate
    min_rating: float = 0.0  # 0-100 minimum rating
    min_on_time_rate: float = 0.0  # 0-1 on-time completion rate
    min_days_active: int = 0  # Minimum days since first task
    lookback_days: int = 90  # Window for calculating metrics
    require_recent_activity: bool = True  # Must have task in last 30 days
    custom_criteria: Optional[Dict[str, Any]] = None  # For special cases

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage."""
        return {
            "min_tasks": self.min_tasks,
            "min_success_rate": self.min_success_rate,
            "min_rating": self.min_rating,
            "min_on_time_rate": self.min_on_time_rate,
            "min_days_active": self.min_days_active,
            "lookback_days": self.lookback_days,
            "require_recent_activity": self.require_recent_activity,
            "custom_criteria": self.custom_criteria,
        }


@dataclass
class Seal:
    """
    A seal earned by a user (worker or requester).

    Seals are stored on describe.net and synced to Execution Market.
    """

    seal_type: str  # WorkerSealType or RequesterSealType value
    user_id: str  # Execution Market user ID (worker or agent)
    user_type: str  # "worker" or "requester"
    status: SealStatus = SealStatus.ACTIVE
    earned_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    criteria_snapshot: Optional[Dict[str, Any]] = None  # Metrics when earned
    describe_net_id: Optional[str] = None  # ID on describe.net
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None

    def __post_init__(self):
        if self.earned_at is None:
            self.earned_at = datetime.now(timezone.utc)

    @property
    def is_active(self) -> bool:
        """Check if seal is currently active."""
        if self.status != SealStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage."""
        return {
            "seal_type": self.seal_type,
            "user_id": self.user_id,
            "user_type": self.user_type,
            "status": self.status.value,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "criteria_snapshot": self.criteria_snapshot,
            "describe_net_id": self.describe_net_id,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revocation_reason": self.revocation_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Seal":
        """Create from dictionary."""
        return cls(
            seal_type=data["seal_type"],
            user_id=data["user_id"],
            user_type=data["user_type"],
            status=SealStatus(data.get("status", "active")),
            earned_at=datetime.fromisoformat(data["earned_at"])
            if data.get("earned_at")
            else None,
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            criteria_snapshot=data.get("criteria_snapshot"),
            describe_net_id=data.get("describe_net_id"),
            revoked_at=datetime.fromisoformat(data["revoked_at"])
            if data.get("revoked_at")
            else None,
            revocation_reason=data.get("revocation_reason"),
        )


@dataclass
class Badge:
    """
    A fusion badge representing sustained excellence.

    Badges are harder to earn than seals and represent long-term commitment.
    """

    badge_type: BadgeType
    user_id: str
    user_type: str  # "worker" or "requester"
    status: SealStatus = SealStatus.ACTIVE
    earned_at: Optional[datetime] = None
    criteria_snapshot: Optional[Dict[str, Any]] = None
    describe_net_id: Optional[str] = None
    level: int = 1  # For tiered badges (bronze/silver/gold)

    def __post_init__(self):
        if self.earned_at is None:
            self.earned_at = datetime.now(timezone.utc)

    @property
    def is_active(self) -> bool:
        """Check if badge is currently active."""
        return self.status == SealStatus.ACTIVE

    @property
    def display_name(self) -> str:
        """Get human-readable badge name with level."""
        level_names = {1: "Bronze", 2: "Silver", 3: "Gold", 4: "Platinum"}
        level_str = level_names.get(self.level, f"Level {self.level}")
        badge_names = {
            BadgeType.MASTER_WORKER: "Master Worker",
            BadgeType.TRUSTED_REQUESTER: "Trusted Requester",
            BadgeType.EARLY_ADOPTER: "Early Adopter",
            BadgeType.SPECIALIST: "Specialist",
        }
        return (
            f"{badge_names.get(self.badge_type, self.badge_type.value)} ({level_str})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage."""
        return {
            "badge_type": self.badge_type.value,
            "user_id": self.user_id,
            "user_type": self.user_type,
            "status": self.status.value,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
            "criteria_snapshot": self.criteria_snapshot,
            "describe_net_id": self.describe_net_id,
            "level": self.level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Badge":
        """Create from dictionary."""
        return cls(
            badge_type=BadgeType(data["badge_type"]),
            user_id=data["user_id"],
            user_type=data["user_type"],
            status=SealStatus(data.get("status", "active")),
            earned_at=datetime.fromisoformat(data["earned_at"])
            if data.get("earned_at")
            else None,
            criteria_snapshot=data.get("criteria_snapshot"),
            describe_net_id=data.get("describe_net_id"),
            level=data.get("level", 1),
        )


# ============== SEAL CRITERIA DEFINITIONS ==============

# Worker Seal Criteria (NOW-166)
WORKER_SEAL_CRITERIA: Dict[WorkerSealType, SealCriteria] = {
    WorkerSealType.SKILLFUL: SealCriteria(
        min_tasks=10,
        min_rating=80.0,
        min_success_rate=0.90,
        lookback_days=90,
    ),
    WorkerSealType.RELIABLE: SealCriteria(
        min_tasks=15,
        min_success_rate=0.95,
        min_days_active=30,
        lookback_days=90,
    ),
    WorkerSealType.THOROUGH: SealCriteria(
        min_tasks=10,
        min_rating=85.0,
        lookback_days=90,
        custom_criteria={
            "min_extra_evidence_rate": 0.5,  # 50% of tasks with optional evidence
        },
    ),
    WorkerSealType.ON_TIME: SealCriteria(
        min_tasks=15,
        min_on_time_rate=0.95,
        lookback_days=90,
    ),
}

# Requester Seal Criteria (NOW-167)
REQUESTER_SEAL_CRITERIA: Dict[RequesterSealType, SealCriteria] = {
    RequesterSealType.FAIR_EVALUATOR: SealCriteria(
        min_tasks=20,
        min_success_rate=0.85,  # 85% acceptance rate
        lookback_days=90,
        custom_criteria={
            "max_dispute_rate": 0.10,  # Max 10% disputed
        },
    ),
    RequesterSealType.CLEAR_INSTRUCTIONS: SealCriteria(
        min_tasks=15,
        lookback_days=90,
        custom_criteria={
            "max_clarification_rate": 0.15,  # Max 15% need clarification
            "min_first_submission_accept": 0.70,  # 70% accepted on first try
        },
    ),
    RequesterSealType.FAST_PAYMENT: SealCriteria(
        min_tasks=20,
        lookback_days=90,
        custom_criteria={
            "median_payment_hours": 24,  # Median < 24h
            "max_payment_hours_p95": 72,  # 95th percentile < 72h
        },
    ),
}


def get_seal_criteria(
    seal_type: WorkerSealType | RequesterSealType,
) -> Optional[SealCriteria]:
    """Get criteria for a seal type."""
    if isinstance(seal_type, WorkerSealType):
        return WORKER_SEAL_CRITERIA.get(seal_type)
    elif isinstance(seal_type, RequesterSealType):
        return REQUESTER_SEAL_CRITERIA.get(seal_type)
    return None


def seal_type_description(seal_type: WorkerSealType | RequesterSealType) -> str:
    """Get human-readable description of a seal."""
    descriptions = {
        # Worker seals
        WorkerSealType.SKILLFUL: "Consistently delivers high-quality work above expectations",
        WorkerSealType.RELIABLE: "Dependable worker who completes what they commit to",
        WorkerSealType.THOROUGH: "Goes beyond requirements with extra evidence and detail",
        WorkerSealType.ON_TIME: "Completes tasks well before deadlines",
        # Requester seals
        RequesterSealType.FAIR_EVALUATOR: "Accepts reasonable work without unfair rejections",
        RequesterSealType.CLEAR_INSTRUCTIONS: "Writes clear, actionable task specifications",
        RequesterSealType.FAST_PAYMENT: "Releases payment promptly after task approval",
    }
    return descriptions.get(seal_type, "No description available")
