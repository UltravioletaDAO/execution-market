"""
Execution Market Gamified Progression System (NOW-135)

Implements a gamified worker progression system:
- Levels: Novice -> Apprentice -> Journeyman -> Expert -> Master
- XP system based on task completion
- Level-specific perks and unlocks
- Achievement system for engagement

Progression Gates:
- Novice: Anyone can start
- Apprentice: 10 tasks + 25 XP
- Journeyman: 50 tasks + 150 XP + 40 rep
- Expert: 200 tasks + 500 XP + 60 rep
- Master: 500 tasks + 1500 XP + 80 rep + manual review
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Set


class WorkerLevel(str, Enum):
    """
    Worker progression levels.

    Each level unlocks new capabilities and earns better rates.
    """
    NOVICE = "novice"           # Starting level
    APPRENTICE = "apprentice"   # Proven basics
    JOURNEYMAN = "journeyman"   # Reliable worker
    EXPERT = "expert"           # High performer
    MASTER = "master"           # Elite status


@dataclass
class LevelRequirements:
    """
    Requirements to achieve a level.

    Attributes:
        level: The level these requirements are for
        min_tasks_completed: Minimum completed tasks
        min_xp: Minimum experience points
        min_reputation: Minimum reputation score
        requires_review: Whether manual review is needed
        min_account_age_days: Minimum account age
    """
    level: WorkerLevel
    min_tasks_completed: int
    min_xp: int
    min_reputation: int
    requires_review: bool = False
    min_account_age_days: int = 0

    def check_eligibility(
        self,
        tasks_completed: int,
        xp: int,
        reputation: int,
        account_age_days: int,
    ) -> tuple[bool, List[str]]:
        """
        Check if a worker meets requirements for this level.

        Returns:
            Tuple of (meets_requirements, list of unmet requirements)
        """
        unmet = []

        if tasks_completed < self.min_tasks_completed:
            unmet.append(
                f"Need {self.min_tasks_completed - tasks_completed} more tasks "
                f"({tasks_completed}/{self.min_tasks_completed})"
            )

        if xp < self.min_xp:
            unmet.append(
                f"Need {self.min_xp - xp} more XP ({xp}/{self.min_xp})"
            )

        if reputation < self.min_reputation:
            unmet.append(
                f"Need {self.min_reputation - reputation} more reputation "
                f"({reputation}/{self.min_reputation})"
            )

        if account_age_days < self.min_account_age_days:
            unmet.append(
                f"Account must be {self.min_account_age_days} days old "
                f"({account_age_days} days)"
            )

        if self.requires_review:
            unmet.append("Manual review required - apply for promotion")

        return len(unmet) == 0, unmet

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "level": self.level.value,
            "min_tasks_completed": self.min_tasks_completed,
            "min_xp": self.min_xp,
            "min_reputation": self.min_reputation,
            "requires_review": self.requires_review,
            "min_account_age_days": self.min_account_age_days,
        }


@dataclass
class LevelPerks:
    """
    Perks unlocked at each level.

    Attributes:
        level: The level
        bounty_multiplier: Bonus multiplier on bounties (1.0 = no bonus)
        max_concurrent_tasks: How many tasks can be active
        early_access_hours: Hours of early access to new tasks
        can_mentor: Can mentor other workers
        priority_support: Gets priority support
        reduced_fees: Platform fee reduction percentage
        badge_emoji: Visual badge (for display)
    """
    level: WorkerLevel
    bounty_multiplier: Decimal
    max_concurrent_tasks: int
    early_access_hours: int = 0
    can_mentor: bool = False
    priority_support: bool = False
    reduced_fees: Decimal = Decimal("0")
    badge_emoji: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "level": self.level.value,
            "bounty_multiplier": str(self.bounty_multiplier),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "early_access_hours": self.early_access_hours,
            "can_mentor": self.can_mentor,
            "priority_support": self.priority_support,
            "reduced_fees": str(self.reduced_fees),
            "badge": self.badge_emoji,
        }


# Level requirements configuration
LEVEL_REQUIREMENTS: Dict[WorkerLevel, LevelRequirements] = {
    WorkerLevel.NOVICE: LevelRequirements(
        level=WorkerLevel.NOVICE,
        min_tasks_completed=0,
        min_xp=0,
        min_reputation=0,
        min_account_age_days=0,
    ),
    WorkerLevel.APPRENTICE: LevelRequirements(
        level=WorkerLevel.APPRENTICE,
        min_tasks_completed=10,
        min_xp=25,
        min_reputation=20,
        min_account_age_days=3,
    ),
    WorkerLevel.JOURNEYMAN: LevelRequirements(
        level=WorkerLevel.JOURNEYMAN,
        min_tasks_completed=50,
        min_xp=150,
        min_reputation=40,
        min_account_age_days=14,
    ),
    WorkerLevel.EXPERT: LevelRequirements(
        level=WorkerLevel.EXPERT,
        min_tasks_completed=200,
        min_xp=500,
        min_reputation=60,
        min_account_age_days=30,
    ),
    WorkerLevel.MASTER: LevelRequirements(
        level=WorkerLevel.MASTER,
        min_tasks_completed=500,
        min_xp=1500,
        min_reputation=80,
        min_account_age_days=90,
        requires_review=True,
    ),
}


# Level perks configuration
LEVEL_PERKS: Dict[WorkerLevel, LevelPerks] = {
    WorkerLevel.NOVICE: LevelPerks(
        level=WorkerLevel.NOVICE,
        bounty_multiplier=Decimal("1.00"),
        max_concurrent_tasks=3,
        badge_emoji="[N]",
    ),
    WorkerLevel.APPRENTICE: LevelPerks(
        level=WorkerLevel.APPRENTICE,
        bounty_multiplier=Decimal("1.05"),  # 5% bonus
        max_concurrent_tasks=5,
        badge_emoji="[A]",
    ),
    WorkerLevel.JOURNEYMAN: LevelPerks(
        level=WorkerLevel.JOURNEYMAN,
        bounty_multiplier=Decimal("1.10"),  # 10% bonus
        max_concurrent_tasks=7,
        early_access_hours=2,
        reduced_fees=Decimal("0.01"),  # 1% fee reduction
        badge_emoji="[J]",
    ),
    WorkerLevel.EXPERT: LevelPerks(
        level=WorkerLevel.EXPERT,
        bounty_multiplier=Decimal("1.15"),  # 15% bonus
        max_concurrent_tasks=10,
        early_access_hours=6,
        can_mentor=True,
        reduced_fees=Decimal("0.02"),  # 2% fee reduction
        badge_emoji="[E]",
    ),
    WorkerLevel.MASTER: LevelPerks(
        level=WorkerLevel.MASTER,
        bounty_multiplier=Decimal("1.25"),  # 25% bonus
        max_concurrent_tasks=15,
        early_access_hours=12,
        can_mentor=True,
        priority_support=True,
        reduced_fees=Decimal("0.05"),  # 5% fee reduction
        badge_emoji="[M]",
    ),
}


class AchievementType(str, Enum):
    """Types of achievements workers can earn."""
    FIRST_TASK = "first_task"
    STREAK_7 = "streak_7_days"
    STREAK_30 = "streak_30_days"
    PERFECT_10 = "perfect_10"  # 10 consecutive 100% ratings
    SPEED_DEMON = "speed_demon"  # Complete 5 tasks in 1 hour
    NIGHT_OWL = "night_owl"  # 10 tasks between 10pm-6am
    EARLY_BIRD = "early_bird"  # 10 tasks between 5am-9am
    SPECIALIST = "specialist"  # 50 tasks of same type
    EXPLORER = "explorer"  # Tasks in 10 different zones
    MENTOR = "mentor"  # Help 5 workers
    THOUSAND_CLUB = "thousand_club"  # 1000 tasks completed
    HIGH_ROLLER = "high_roller"  # Complete a $500 task
    BUNDLE_MASTER = "bundle_master"  # Complete 10 bundles


@dataclass
class Achievement:
    """
    An achievement that workers can earn.

    Attributes:
        achievement_type: Type of achievement
        name: Display name
        description: How to earn it
        xp_reward: XP awarded for earning
        badge_emoji: Visual badge
        secret: Whether achievement is hidden until earned
    """
    achievement_type: AchievementType
    name: str
    description: str
    xp_reward: int
    badge_emoji: str
    secret: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": self.achievement_type.value,
            "name": self.name,
            "description": self.description if not self.secret else "???",
            "xp_reward": self.xp_reward,
            "badge": self.badge_emoji,
            "secret": self.secret,
        }


# Achievement definitions
ACHIEVEMENTS: Dict[AchievementType, Achievement] = {
    AchievementType.FIRST_TASK: Achievement(
        achievement_type=AchievementType.FIRST_TASK,
        name="First Steps",
        description="Complete your first task",
        xp_reward=5,
        badge_emoji="[1]",
    ),
    AchievementType.STREAK_7: Achievement(
        achievement_type=AchievementType.STREAK_7,
        name="Week Warrior",
        description="Complete at least one task every day for 7 days",
        xp_reward=25,
        badge_emoji="[7]",
    ),
    AchievementType.STREAK_30: Achievement(
        achievement_type=AchievementType.STREAK_30,
        name="Month Marathoner",
        description="Complete at least one task every day for 30 days",
        xp_reward=100,
        badge_emoji="[30]",
    ),
    AchievementType.PERFECT_10: Achievement(
        achievement_type=AchievementType.PERFECT_10,
        name="Perfectionist",
        description="Get 10 consecutive perfect ratings",
        xp_reward=50,
        badge_emoji="[10/10]",
    ),
    AchievementType.SPEED_DEMON: Achievement(
        achievement_type=AchievementType.SPEED_DEMON,
        name="Speed Demon",
        description="Complete 5 tasks in a single hour",
        xp_reward=30,
        badge_emoji="[FAST]",
    ),
    AchievementType.NIGHT_OWL: Achievement(
        achievement_type=AchievementType.NIGHT_OWL,
        name="Night Owl",
        description="Complete 10 tasks between 10pm and 6am",
        xp_reward=20,
        badge_emoji="[OWL]",
    ),
    AchievementType.EARLY_BIRD: Achievement(
        achievement_type=AchievementType.EARLY_BIRD,
        name="Early Bird",
        description="Complete 10 tasks between 5am and 9am",
        xp_reward=20,
        badge_emoji="[BIRD]",
    ),
    AchievementType.SPECIALIST: Achievement(
        achievement_type=AchievementType.SPECIALIST,
        name="Specialist",
        description="Complete 50 tasks of the same type",
        xp_reward=40,
        badge_emoji="[PRO]",
    ),
    AchievementType.EXPLORER: Achievement(
        achievement_type=AchievementType.EXPLORER,
        name="Explorer",
        description="Complete tasks in 10 different zones",
        xp_reward=35,
        badge_emoji="[MAP]",
    ),
    AchievementType.MENTOR: Achievement(
        achievement_type=AchievementType.MENTOR,
        name="Mentor",
        description="Help 5 novice workers complete their first task",
        xp_reward=50,
        badge_emoji="[TEACH]",
    ),
    AchievementType.THOUSAND_CLUB: Achievement(
        achievement_type=AchievementType.THOUSAND_CLUB,
        name="Thousand Club",
        description="Complete 1000 tasks",
        xp_reward=200,
        badge_emoji="[1K]",
        secret=True,
    ),
    AchievementType.HIGH_ROLLER: Achievement(
        achievement_type=AchievementType.HIGH_ROLLER,
        name="High Roller",
        description="Complete a task worth $500 or more",
        xp_reward=75,
        badge_emoji="[$$$]",
    ),
    AchievementType.BUNDLE_MASTER: Achievement(
        achievement_type=AchievementType.BUNDLE_MASTER,
        name="Bundle Master",
        description="Complete 10 task bundles",
        xp_reward=60,
        badge_emoji="[BUNDLE]",
    ),
}


@dataclass
class XPEvent:
    """
    An event that grants XP.

    Attributes:
        event_type: Type of event
        xp_amount: Base XP amount
        timestamp: When event occurred
        task_id: Related task ID (if applicable)
        description: Human-readable description
        multiplier: Applied multiplier (for bonuses)
    """
    event_type: str
    xp_amount: int
    timestamp: datetime
    task_id: Optional[str] = None
    description: str = ""
    multiplier: Decimal = Decimal("1.0")

    @property
    def total_xp(self) -> int:
        """Calculate total XP with multiplier."""
        return int(self.xp_amount * self.multiplier)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_type": self.event_type,
            "xp_amount": self.xp_amount,
            "multiplier": str(self.multiplier),
            "total_xp": self.total_xp,
            "timestamp": self.timestamp.isoformat(),
            "task_id": self.task_id,
            "description": self.description,
        }


# XP awards for different actions
XP_AWARDS = {
    "task_completed": 3,  # Base XP for completing any task
    "tier_1_bonus": 0,    # No extra for Tier 1
    "tier_2_bonus": 2,    # +2 for Tier 2 tasks
    "tier_3_bonus": 5,    # +5 for Tier 3 tasks
    "perfect_rating": 2,   # Bonus for 100% rating
    "on_time": 1,         # Bonus for completing before deadline
    "early_completion": 2, # Bonus for completing >50% early
    "bundle_bonus": 5,     # Bonus for completing a bundle
    "first_of_day": 1,     # First task of the day bonus
    "streak_daily": 2,     # Daily streak bonus
    "achievement": 0,      # Achievements give their own XP
}


class ProgressionManager:
    """
    Manages worker progression, XP, and achievements.

    Tracks:
    - Worker levels and requirements
    - XP accumulation and history
    - Achievement progress and unlocks
    """

    def __init__(
        self,
        requirements: Optional[Dict[WorkerLevel, LevelRequirements]] = None,
        perks: Optional[Dict[WorkerLevel, LevelPerks]] = None,
        achievements: Optional[Dict[AchievementType, Achievement]] = None,
    ):
        self.requirements = requirements or LEVEL_REQUIREMENTS
        self.perks = perks or LEVEL_PERKS
        self.achievements = achievements or ACHIEVEMENTS

    def get_current_level(
        self,
        tasks_completed: int,
        xp: int,
        reputation: int,
        account_age_days: int,
        is_master_approved: bool = False,
    ) -> WorkerLevel:
        """
        Determine worker's current level based on stats.

        Args:
            tasks_completed: Number of completed tasks
            xp: Total XP earned
            reputation: Current reputation score
            account_age_days: Days since account creation
            is_master_approved: Whether worker has been approved for Master

        Returns:
            Current WorkerLevel
        """
        level = WorkerLevel.NOVICE

        # Check each level in order
        level_order = [
            WorkerLevel.NOVICE,
            WorkerLevel.APPRENTICE,
            WorkerLevel.JOURNEYMAN,
            WorkerLevel.EXPERT,
            WorkerLevel.MASTER,
        ]

        for check_level in level_order:
            reqs = self.requirements[check_level]

            # Master requires approval
            if check_level == WorkerLevel.MASTER and not is_master_approved:
                continue

            eligible, _ = reqs.check_eligibility(
                tasks_completed, xp, reputation, account_age_days
            )

            if eligible:
                level = check_level

        return level

    def get_progress_to_next_level(
        self,
        current_level: WorkerLevel,
        tasks_completed: int,
        xp: int,
        reputation: int,
        account_age_days: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get progress toward next level.

        Args:
            current_level: Current level
            tasks_completed: Number of completed tasks
            xp: Total XP earned
            reputation: Current reputation score
            account_age_days: Days since account creation

        Returns:
            Dict with progress info, or None if at max level
        """
        level_order = [
            WorkerLevel.NOVICE,
            WorkerLevel.APPRENTICE,
            WorkerLevel.JOURNEYMAN,
            WorkerLevel.EXPERT,
            WorkerLevel.MASTER,
        ]

        current_idx = level_order.index(current_level)
        if current_idx >= len(level_order) - 1:
            return None  # Already at Master

        next_level = level_order[current_idx + 1]
        next_reqs = self.requirements[next_level]

        # Calculate progress percentages
        task_progress = min(100, (tasks_completed / next_reqs.min_tasks_completed) * 100)
        xp_progress = min(100, (xp / next_reqs.min_xp) * 100)
        rep_progress = min(100, (reputation / next_reqs.min_reputation) * 100) if next_reqs.min_reputation > 0 else 100

        overall_progress = (task_progress + xp_progress + rep_progress) / 3

        return {
            "current_level": current_level.value,
            "next_level": next_level.value,
            "overall_progress": round(overall_progress, 1),
            "requirements": {
                "tasks": {
                    "current": tasks_completed,
                    "required": next_reqs.min_tasks_completed,
                    "progress": round(task_progress, 1),
                },
                "xp": {
                    "current": xp,
                    "required": next_reqs.min_xp,
                    "progress": round(xp_progress, 1),
                },
                "reputation": {
                    "current": reputation,
                    "required": next_reqs.min_reputation,
                    "progress": round(rep_progress, 1),
                },
            },
            "requires_review": next_reqs.requires_review,
            "perks_at_next_level": self.perks[next_level].to_dict(),
        }

    def calculate_task_xp(
        self,
        tier: str,
        rating: int,
        deadline_hours: int,
        completion_hours: float,
        is_bundle: bool = False,
        is_first_of_day: bool = False,
        streak_days: int = 0,
    ) -> XPEvent:
        """
        Calculate XP earned for completing a task.

        Args:
            tier: Task tier (tier_1, tier_2, tier_3)
            rating: Rating received (0-100)
            deadline_hours: Hours given to complete
            completion_hours: Actual hours to complete
            is_bundle: Whether task was part of a bundle
            is_first_of_day: Whether this is first task of the day
            streak_days: Current streak length

        Returns:
            XPEvent with calculated XP
        """
        xp = XP_AWARDS["task_completed"]
        description_parts = ["Task completed (+3 XP)"]

        # Tier bonus
        tier_bonus = {
            "tier_1": XP_AWARDS["tier_1_bonus"],
            "tier_2": XP_AWARDS["tier_2_bonus"],
            "tier_3": XP_AWARDS["tier_3_bonus"],
        }.get(tier, 0)

        if tier_bonus > 0:
            xp += tier_bonus
            description_parts.append(f"Tier bonus (+{tier_bonus} XP)")

        # Perfect rating bonus
        if rating >= 95:
            xp += XP_AWARDS["perfect_rating"]
            description_parts.append(f"Excellent rating (+{XP_AWARDS['perfect_rating']} XP)")

        # On-time bonus
        if completion_hours <= deadline_hours:
            xp += XP_AWARDS["on_time"]
            description_parts.append(f"On time (+{XP_AWARDS['on_time']} XP)")

            # Early completion bonus (more than 50% of time remaining)
            if completion_hours <= deadline_hours * 0.5:
                xp += XP_AWARDS["early_completion"]
                description_parts.append(f"Early completion (+{XP_AWARDS['early_completion']} XP)")

        # Bundle bonus
        if is_bundle:
            xp += XP_AWARDS["bundle_bonus"]
            description_parts.append(f"Bundle bonus (+{XP_AWARDS['bundle_bonus']} XP)")

        # First of day bonus
        if is_first_of_day:
            xp += XP_AWARDS["first_of_day"]
            description_parts.append(f"First today (+{XP_AWARDS['first_of_day']} XP)")

        # Streak multiplier
        multiplier = Decimal("1.0")
        if streak_days >= 7:
            multiplier = Decimal("1.1")  # 10% bonus for 7+ day streak
            description_parts.append("7+ day streak (1.1x)")
        if streak_days >= 30:
            multiplier = Decimal("1.25")  # 25% bonus for 30+ day streak
            description_parts.append("30+ day streak (1.25x)")

        return XPEvent(
            event_type="task_completed",
            xp_amount=xp,
            timestamp=datetime.now(UTC),
            description=" | ".join(description_parts),
            multiplier=multiplier,
        )

    def check_achievements(
        self,
        worker_stats: Dict[str, Any],
        earned_achievements: Set[AchievementType],
    ) -> List[Achievement]:
        """
        Check which new achievements a worker has earned.

        Args:
            worker_stats: Dict with worker statistics
            earned_achievements: Set of already earned achievement types

        Returns:
            List of newly earned achievements
        """
        newly_earned = []

        # First task
        if (AchievementType.FIRST_TASK not in earned_achievements
                and worker_stats.get("tasks_completed", 0) >= 1):
            newly_earned.append(self.achievements[AchievementType.FIRST_TASK])

        # Streaks
        streak = worker_stats.get("current_streak_days", 0)
        if (AchievementType.STREAK_7 not in earned_achievements and streak >= 7):
            newly_earned.append(self.achievements[AchievementType.STREAK_7])
        if (AchievementType.STREAK_30 not in earned_achievements and streak >= 30):
            newly_earned.append(self.achievements[AchievementType.STREAK_30])

        # Perfect ratings
        if (AchievementType.PERFECT_10 not in earned_achievements
                and worker_stats.get("consecutive_perfect_ratings", 0) >= 10):
            newly_earned.append(self.achievements[AchievementType.PERFECT_10])

        # Task count milestones
        total_tasks = worker_stats.get("tasks_completed", 0)
        if (AchievementType.THOUSAND_CLUB not in earned_achievements
                and total_tasks >= 1000):
            newly_earned.append(self.achievements[AchievementType.THOUSAND_CLUB])

        # Specialist
        if AchievementType.SPECIALIST not in earned_achievements:
            task_types = worker_stats.get("tasks_by_type", {})
            for count in task_types.values():
                if count >= 50:
                    newly_earned.append(self.achievements[AchievementType.SPECIALIST])
                    break

        # Explorer
        if (AchievementType.EXPLORER not in earned_achievements
                and worker_stats.get("unique_zones", 0) >= 10):
            newly_earned.append(self.achievements[AchievementType.EXPLORER])

        # Bundle Master
        if (AchievementType.BUNDLE_MASTER not in earned_achievements
                and worker_stats.get("bundles_completed", 0) >= 10):
            newly_earned.append(self.achievements[AchievementType.BUNDLE_MASTER])

        # High Roller
        if (AchievementType.HIGH_ROLLER not in earned_achievements
                and worker_stats.get("max_task_value", 0) >= 500):
            newly_earned.append(self.achievements[AchievementType.HIGH_ROLLER])

        return newly_earned

    def get_level_perks(self, level: WorkerLevel) -> LevelPerks:
        """Get perks for a specific level."""
        return self.perks[level]

    def calculate_effective_bounty(
        self,
        base_bounty: Decimal,
        worker_level: WorkerLevel,
    ) -> Decimal:
        """
        Calculate effective bounty with level multiplier.

        Args:
            base_bounty: Original bounty amount
            worker_level: Worker's level

        Returns:
            Bounty with level bonus applied
        """
        perks = self.perks[worker_level]
        return base_bounty * perks.bounty_multiplier

    def get_all_achievements(self) -> List[Dict[str, Any]]:
        """Get all achievements (hides secret achievement details)."""
        return [a.to_dict() for a in self.achievements.values()]

    def get_level_roadmap(self) -> List[Dict[str, Any]]:
        """Get complete level progression roadmap."""
        roadmap = []
        for level in WorkerLevel:
            reqs = self.requirements[level]
            perks = self.perks[level]
            roadmap.append({
                "level": level.value,
                "requirements": reqs.to_dict(),
                "perks": perks.to_dict(),
            })
        return roadmap


# Convenience functions
def get_worker_level(
    tasks_completed: int,
    xp: int,
    reputation: int,
    account_age_days: int = 0,
) -> WorkerLevel:
    """Quick function to determine worker level."""
    manager = ProgressionManager()
    return manager.get_current_level(
        tasks_completed, xp, reputation, account_age_days
    )


def calculate_bounty_with_level(
    bounty_usd: float,
    level: WorkerLevel,
) -> float:
    """Quick function to apply level bonus to bounty."""
    manager = ProgressionManager()
    result = manager.calculate_effective_bounty(
        Decimal(str(bounty_usd)), level
    )
    return float(result)
