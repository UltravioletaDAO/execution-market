"""
Execution Market Reputation System - Data Models

Core data structures for the reputation system.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, List, Dict, Any


class Badge(str, Enum):
    """Achievement badges that workers can earn."""

    # Milestone badges
    NEWCOMER = "newcomer"  # Completed first task
    RELIABLE = "reliable"  # 10 tasks completed
    VETERAN = "veteran"  # 50 tasks completed
    MASTER = "master"  # 100 tasks completed
    LEGEND = "legend"  # 500 tasks completed

    # Quality badges
    QUALITY_STAR = "quality_star"  # 95%+ approval rate (min 10 tasks)
    PERFECTIONIST = "perfectionist"  # 100% approval rate (min 25 tasks)

    # Speed badges
    FAST_WORKER = "fast_worker"  # Avg completion < 50% of deadline
    LIGHTNING = "lightning"  # 10 tasks completed in < 25% of deadline

    # Trust badges
    VERIFIED = "verified"  # ID verification completed
    TRUSTED = "trusted"  # 25+ tasks with 0 disputes
    EXPERT = "expert"  # Score > 85 for 30+ days

    # Specialty badges
    PHOTOGRAPHER = "photographer"  # 20+ photo tasks completed
    DELIVERY_PRO = "delivery_pro"  # 20+ delivery tasks completed
    SURVEYOR = "surveyor"  # 20+ data collection tasks
    INSPECTOR = "inspector"  # 20+ verification tasks

    # Community badges
    EARLY_ADOPTER = "early_adopter"  # Joined in first month
    STREAK_7 = "streak_7"  # 7 day activity streak
    STREAK_30 = "streak_30"  # 30 day activity streak
    TOP_10 = "top_10"  # Reached top 10 in location
    TOP_100 = "top_100"  # Reached top 100 globally

    # Special badges
    DISPUTE_WINNER = "dispute_winner"  # Won a dispute
    COMEBACK = "comeback"  # Recovered from <30 to >70 score
    MENTOR = "mentor"  # Referred 5+ active workers


@dataclass
class BadgeDefinition:
    """Complete definition of a badge with display info."""

    badge: Badge
    name: str
    description: str
    icon: str  # Emoji or icon identifier
    category: str  # milestone, quality, speed, trust, specialty, community, special
    points: int  # Bonus reputation points for earning
    rarity: str  # common, uncommon, rare, epic, legendary

    @classmethod
    def get_all(cls) -> Dict[Badge, "BadgeDefinition"]:
        """Get all badge definitions."""
        return {
            Badge.NEWCOMER: cls(
                badge=Badge.NEWCOMER,
                name="Newcomer",
                description="Completed your first task",
                icon="seedling",
                category="milestone",
                points=5,
                rarity="common",
            ),
            Badge.RELIABLE: cls(
                badge=Badge.RELIABLE,
                name="Reliable",
                description="Completed 10 tasks",
                icon="check-circle",
                category="milestone",
                points=10,
                rarity="common",
            ),
            Badge.VETERAN: cls(
                badge=Badge.VETERAN,
                name="Veteran",
                description="Completed 50 tasks",
                icon="star",
                category="milestone",
                points=25,
                rarity="uncommon",
            ),
            Badge.MASTER: cls(
                badge=Badge.MASTER,
                name="Master",
                description="Completed 100 tasks",
                icon="crown",
                category="milestone",
                points=50,
                rarity="rare",
            ),
            Badge.LEGEND: cls(
                badge=Badge.LEGEND,
                name="Legend",
                description="Completed 500 tasks",
                icon="trophy",
                category="milestone",
                points=100,
                rarity="legendary",
            ),
            Badge.QUALITY_STAR: cls(
                badge=Badge.QUALITY_STAR,
                name="Quality Star",
                description="Maintained 95%+ approval rate",
                icon="star-quality",
                category="quality",
                points=15,
                rarity="uncommon",
            ),
            Badge.PERFECTIONIST: cls(
                badge=Badge.PERFECTIONIST,
                name="Perfectionist",
                description="100% approval on 25+ tasks",
                icon="diamond",
                category="quality",
                points=30,
                rarity="rare",
            ),
            Badge.FAST_WORKER: cls(
                badge=Badge.FAST_WORKER,
                name="Fast Worker",
                description="Avg completion under 50% of deadline",
                icon="clock-fast",
                category="speed",
                points=10,
                rarity="common",
            ),
            Badge.LIGHTNING: cls(
                badge=Badge.LIGHTNING,
                name="Lightning",
                description="10 tasks in under 25% of deadline",
                icon="lightning",
                category="speed",
                points=20,
                rarity="rare",
            ),
            Badge.VERIFIED: cls(
                badge=Badge.VERIFIED,
                name="Verified",
                description="Completed ID verification",
                icon="shield-check",
                category="trust",
                points=20,
                rarity="common",
            ),
            Badge.TRUSTED: cls(
                badge=Badge.TRUSTED,
                name="Trusted",
                description="25+ tasks with zero disputes",
                icon="handshake",
                category="trust",
                points=25,
                rarity="uncommon",
            ),
            Badge.EXPERT: cls(
                badge=Badge.EXPERT,
                name="Expert",
                description="Score above 85 for 30+ days",
                icon="graduation-cap",
                category="trust",
                points=35,
                rarity="rare",
            ),
            Badge.PHOTOGRAPHER: cls(
                badge=Badge.PHOTOGRAPHER,
                name="Photographer",
                description="Completed 20+ photo tasks",
                icon="camera",
                category="specialty",
                points=15,
                rarity="uncommon",
            ),
            Badge.DELIVERY_PRO: cls(
                badge=Badge.DELIVERY_PRO,
                name="Delivery Pro",
                description="Completed 20+ delivery tasks",
                icon="package",
                category="specialty",
                points=15,
                rarity="uncommon",
            ),
            Badge.SURVEYOR: cls(
                badge=Badge.SURVEYOR,
                name="Surveyor",
                description="Completed 20+ data collection tasks",
                icon="clipboard",
                category="specialty",
                points=15,
                rarity="uncommon",
            ),
            Badge.INSPECTOR: cls(
                badge=Badge.INSPECTOR,
                name="Inspector",
                description="Completed 20+ verification tasks",
                icon="magnifying-glass",
                category="specialty",
                points=15,
                rarity="uncommon",
            ),
            Badge.EARLY_ADOPTER: cls(
                badge=Badge.EARLY_ADOPTER,
                name="Early Adopter",
                description="Joined in the first month",
                icon="rocket",
                category="community",
                points=25,
                rarity="epic",
            ),
            Badge.STREAK_7: cls(
                badge=Badge.STREAK_7,
                name="Weekly Streak",
                description="7 day activity streak",
                icon="fire",
                category="community",
                points=5,
                rarity="common",
            ),
            Badge.STREAK_30: cls(
                badge=Badge.STREAK_30,
                name="Monthly Streak",
                description="30 day activity streak",
                icon="fire-alt",
                category="community",
                points=20,
                rarity="uncommon",
            ),
            Badge.TOP_10: cls(
                badge=Badge.TOP_10,
                name="Local Champion",
                description="Reached top 10 in your location",
                icon="medal",
                category="community",
                points=30,
                rarity="rare",
            ),
            Badge.TOP_100: cls(
                badge=Badge.TOP_100,
                name="Global Elite",
                description="Reached top 100 globally",
                icon="globe",
                category="community",
                points=40,
                rarity="epic",
            ),
            Badge.DISPUTE_WINNER: cls(
                badge=Badge.DISPUTE_WINNER,
                name="Dispute Winner",
                description="Won a dispute with evidence",
                icon="gavel",
                category="special",
                points=10,
                rarity="uncommon",
            ),
            Badge.COMEBACK: cls(
                badge=Badge.COMEBACK,
                name="Comeback",
                description="Recovered from low to high score",
                icon="phoenix",
                category="special",
                points=25,
                rarity="rare",
            ),
            Badge.MENTOR: cls(
                badge=Badge.MENTOR,
                name="Mentor",
                description="Referred 5+ active workers",
                icon="users",
                category="special",
                points=20,
                rarity="uncommon",
            ),
        }


@dataclass
class EarnedBadge:
    """A badge earned by a specific executor."""

    executor_id: str
    badge: Badge
    earned_at: datetime
    context: Optional[Dict[str, Any]] = None  # Task ID, milestone details, etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "executor_id": self.executor_id,
            "badge": self.badge.value,
            "earned_at": self.earned_at.isoformat(),
            "context": self.context,
        }


@dataclass
class ReputationScore:
    """Complete reputation profile for an executor."""

    executor_id: str

    # Beta distribution parameters (Bayesian prior)
    alpha: float = 2.0  # Successes + prior
    beta: float = 2.0  # Failures + prior

    # Computed scores
    score: float = 50.0  # 0-100 normalized score
    confidence: float = 0.0  # 0-100, how confident we are

    # Stats
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_disputed: int = 0
    tasks_abandoned: int = 0

    # Value-weighted stats
    total_value_completed: float = 0.0  # Sum of bounty values for completed tasks
    total_value_failed: float = 0.0  # Sum of bounty values for failed tasks

    # Ratings received
    total_ratings: int = 0
    sum_ratings: float = 0.0
    avg_rating: Optional[float] = None  # 1-5 star average

    # Time tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity_at: Optional[datetime] = None
    last_decay_at: Optional[datetime] = None

    # Badges
    badges: List[Badge] = field(default_factory=list)

    # Category-specific scores (optional enhancement)
    category_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API."""
        return {
            "executor_id": self.executor_id,
            "alpha": self.alpha,
            "beta": self.beta,
            "score": round(self.score, 2),
            "confidence": round(self.confidence, 2),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_disputed": self.tasks_disputed,
            "tasks_abandoned": self.tasks_abandoned,
            "total_value_completed": round(self.total_value_completed, 2),
            "total_value_failed": round(self.total_value_failed, 2),
            "total_ratings": self.total_ratings,
            "avg_rating": round(self.avg_rating, 2) if self.avg_rating else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat()
            if self.last_activity_at
            else None,
            "badges": [b.value for b in self.badges],
            "category_scores": self.category_scores,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReputationScore":
        """Create from dictionary."""
        return cls(
            executor_id=data["executor_id"],
            alpha=data.get("alpha", 2.0),
            beta=data.get("beta", 2.0),
            score=data.get("score", 50.0),
            confidence=data.get("confidence", 0.0),
            tasks_completed=data.get("tasks_completed", 0),
            tasks_failed=data.get("tasks_failed", 0),
            tasks_disputed=data.get("tasks_disputed", 0),
            tasks_abandoned=data.get("tasks_abandoned", 0),
            total_value_completed=data.get("total_value_completed", 0.0),
            total_value_failed=data.get("total_value_failed", 0.0),
            total_ratings=data.get("total_ratings", 0),
            sum_ratings=data.get("sum_ratings", 0.0),
            avg_rating=data.get("avg_rating"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.now(UTC),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else datetime.now(UTC),
            last_activity_at=datetime.fromisoformat(data["last_activity_at"])
            if data.get("last_activity_at")
            else None,
            badges=[Badge(b) for b in data.get("badges", [])],
            category_scores=data.get("category_scores", {}),
        )


@dataclass
class ReputationHistory:
    """Historical record of reputation changes."""

    id: str
    executor_id: str

    # Change details
    event_type: str  # completion, failure, dispute, decay, badge, manual
    old_score: float
    new_score: float
    delta: float

    # Context
    task_id: Optional[str] = None
    task_value: Optional[float] = None
    rating: Optional[int] = None
    reason: str = ""

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Badge earned (if applicable)
    badge_earned: Optional[Badge] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "executor_id": self.executor_id,
            "event_type": self.event_type,
            "old_score": round(self.old_score, 2),
            "new_score": round(self.new_score, 2),
            "delta": round(self.delta, 2),
            "task_id": self.task_id,
            "task_value": self.task_value,
            "rating": self.rating,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "badge_earned": self.badge_earned.value if self.badge_earned else None,
        }


@dataclass
class ConfidenceInterval:
    """Statistical confidence interval for a reputation score."""

    lower: float  # Lower bound (e.g., 5th percentile)
    upper: float  # Upper bound (e.g., 95th percentile)
    mean: float  # Expected value
    mode: float  # Most likely value
    confidence_level: float = 0.90  # Default 90% CI

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "lower": round(self.lower, 2),
            "upper": round(self.upper, 2),
            "mean": round(self.mean, 2),
            "mode": round(self.mode, 2),
            "confidence_level": self.confidence_level,
            "range": round(self.upper - self.lower, 2),
        }
