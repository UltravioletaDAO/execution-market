"""
Badge System for Execution Market

Achievement badges that workers can earn through various milestones.

Badges serve multiple purposes:
1. Gamification - makes work more engaging
2. Signal quality - agents can filter by badges
3. Specialization - identify workers with specific skills
4. Trust building - progressive trust levels

Badge categories:
- Milestone: Task completion counts
- Quality: Approval rates and ratings
- Speed: Fast completion
- Trust: Verification and dispute-free work
- Specialty: Category-specific achievements
- Community: Streaks, referrals, rankings
- Special: Unique achievements
"""

from datetime import datetime, timedelta, UTC
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

from .models import Badge, BadgeDefinition, EarnedBadge, ReputationScore


@dataclass
class BadgeContext:
    """Context data for badge eligibility checks."""
    # Task counts
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_disputed: int = 0
    tasks_abandoned: int = 0

    # Quality metrics
    approval_rate: float = 0.0  # 0-100%
    avg_rating: float = 0.0     # 1-5 stars

    # Speed metrics
    avg_completion_percentage: float = 100.0  # % of deadline used
    fast_completions: int = 0  # Tasks done in <25% of deadline

    # Trust metrics
    is_verified: bool = False
    dispute_free_tasks: int = 0  # Consecutive tasks without dispute
    days_above_85: int = 0       # Days with score > 85

    # Category tasks
    category_counts: Dict[str, int] = None  # {"photo": 25, "delivery": 10, ...}

    # Community
    joined_at: Optional[datetime] = None
    current_streak_days: int = 0
    referrals_active: int = 0

    # Rankings
    local_rank: Optional[int] = None
    global_rank: Optional[int] = None

    # Special conditions
    lowest_score: float = 50.0
    current_score: float = 50.0
    disputes_won: int = 0

    def __post_init__(self):
        if self.category_counts is None:
            self.category_counts = {}


class BadgeManager:
    """
    Manages badge eligibility and awarding.

    Example:
        >>> manager = BadgeManager()
        >>> context = BadgeContext(tasks_completed=10, approval_rate=95.0)
        >>> eligible = manager.check_eligibility(context, current_badges=[])
        >>> print([b.value for b in eligible])
        ['reliable', 'quality_star']
    """

    def __init__(self):
        self.definitions = BadgeDefinition.get_all()
        # Map of badge -> eligibility checker function
        self._eligibility_checks = self._build_eligibility_checks()

    def _build_eligibility_checks(self) -> Dict[Badge, callable]:
        """Build the eligibility check functions for each badge."""
        return {
            # Milestone badges
            Badge.NEWCOMER: lambda ctx: ctx.tasks_completed >= 1,
            Badge.RELIABLE: lambda ctx: ctx.tasks_completed >= 10,
            Badge.VETERAN: lambda ctx: ctx.tasks_completed >= 50,
            Badge.MASTER: lambda ctx: ctx.tasks_completed >= 100,
            Badge.LEGEND: lambda ctx: ctx.tasks_completed >= 500,

            # Quality badges
            Badge.QUALITY_STAR: lambda ctx: (
                ctx.tasks_completed >= 10 and ctx.approval_rate >= 95.0
            ),
            Badge.PERFECTIONIST: lambda ctx: (
                ctx.tasks_completed >= 25 and ctx.approval_rate >= 100.0
            ),

            # Speed badges
            Badge.FAST_WORKER: lambda ctx: (
                ctx.tasks_completed >= 5 and ctx.avg_completion_percentage < 50.0
            ),
            Badge.LIGHTNING: lambda ctx: ctx.fast_completions >= 10,

            # Trust badges
            Badge.VERIFIED: lambda ctx: ctx.is_verified,
            Badge.TRUSTED: lambda ctx: (
                ctx.dispute_free_tasks >= 25 and ctx.tasks_disputed == 0
            ),
            Badge.EXPERT: lambda ctx: ctx.days_above_85 >= 30,

            # Specialty badges
            Badge.PHOTOGRAPHER: lambda ctx: (
                ctx.category_counts.get("photo", 0) +
                ctx.category_counts.get("photo_geo", 0) >= 20
            ),
            Badge.DELIVERY_PRO: lambda ctx: (
                ctx.category_counts.get("delivery", 0) +
                ctx.category_counts.get("physical_presence", 0) >= 20
            ),
            Badge.SURVEYOR: lambda ctx: (
                ctx.category_counts.get("data_collection", 0) +
                ctx.category_counts.get("knowledge_access", 0) >= 20
            ),
            Badge.INSPECTOR: lambda ctx: (
                ctx.category_counts.get("verification", 0) +
                ctx.category_counts.get("inspection", 0) >= 20
            ),

            # Community badges
            Badge.EARLY_ADOPTER: lambda ctx: (
                ctx.joined_at is not None and
                ctx.joined_at <= datetime(2026, 3, 1, tzinfo=UTC)  # First month
            ),
            Badge.STREAK_7: lambda ctx: ctx.current_streak_days >= 7,
            Badge.STREAK_30: lambda ctx: ctx.current_streak_days >= 30,
            Badge.TOP_10: lambda ctx: (
                ctx.local_rank is not None and ctx.local_rank <= 10
            ),
            Badge.TOP_100: lambda ctx: (
                ctx.global_rank is not None and ctx.global_rank <= 100
            ),

            # Special badges
            Badge.DISPUTE_WINNER: lambda ctx: ctx.disputes_won >= 1,
            Badge.COMEBACK: lambda ctx: (
                ctx.lowest_score < 30.0 and ctx.current_score > 70.0
            ),
            Badge.MENTOR: lambda ctx: ctx.referrals_active >= 5,
        }

    def check_eligibility(
        self,
        context: BadgeContext,
        current_badges: List[Badge],
    ) -> List[Badge]:
        """
        Check which new badges the worker is eligible for.

        Args:
            context: Current worker context/stats
            current_badges: Badges already earned

        Returns:
            List of newly eligible badges
        """
        current_set = set(current_badges)
        eligible = []

        for badge, check_fn in self._eligibility_checks.items():
            # Skip if already earned
            if badge in current_set:
                continue

            # Check eligibility
            try:
                if check_fn(context):
                    eligible.append(badge)
            except Exception:
                # Skip badges that fail checks (missing data, etc.)
                continue

        return eligible

    def award_badge(
        self,
        executor_id: str,
        badge: Badge,
        context: Optional[Dict[str, Any]] = None,
    ) -> EarnedBadge:
        """
        Create a badge award record.

        Args:
            executor_id: Worker's ID
            badge: Badge to award
            context: Optional context (task ID, milestone details)

        Returns:
            EarnedBadge record
        """
        return EarnedBadge(
            executor_id=executor_id,
            badge=badge,
            earned_at=datetime.now(UTC),
            context=context,
        )

    def get_badge_info(self, badge: Badge) -> Dict[str, Any]:
        """
        Get full information about a badge.

        Args:
            badge: Badge to look up

        Returns:
            Dict with badge details
        """
        defn = self.definitions.get(badge)
        if not defn:
            return {"error": "Badge not found"}

        return {
            "badge": badge.value,
            "name": defn.name,
            "description": defn.description,
            "icon": defn.icon,
            "category": defn.category,
            "points": defn.points,
            "rarity": defn.rarity,
        }

    def get_all_badges(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all badge definitions, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of badge info dicts
        """
        badges = []
        for badge, defn in self.definitions.items():
            if category and defn.category != category:
                continue

            badges.append({
                "badge": badge.value,
                "name": defn.name,
                "description": defn.description,
                "icon": defn.icon,
                "category": defn.category,
                "points": defn.points,
                "rarity": defn.rarity,
            })

        # Sort by category, then rarity (legendary first)
        rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "uncommon": 3, "common": 4}
        badges.sort(key=lambda b: (b["category"], rarity_order.get(b["rarity"], 5)))

        return badges

    def get_progress(
        self,
        context: BadgeContext,
        current_badges: List[Badge],
    ) -> List[Dict[str, Any]]:
        """
        Get progress toward unearned badges.

        Shows how close the worker is to each badge.

        Args:
            context: Current stats
            current_badges: Already earned badges

        Returns:
            List of {badge, progress, remaining} dicts
        """
        current_set = set(current_badges)
        progress_list = []

        # Define progress calculations
        progress_calcs = {
            Badge.NEWCOMER: lambda: (min(1, context.tasks_completed), 1),
            Badge.RELIABLE: lambda: (context.tasks_completed, 10),
            Badge.VETERAN: lambda: (context.tasks_completed, 50),
            Badge.MASTER: lambda: (context.tasks_completed, 100),
            Badge.LEGEND: lambda: (context.tasks_completed, 500),

            Badge.QUALITY_STAR: lambda: (
                (context.tasks_completed, 10) if context.tasks_completed < 10
                else (context.approval_rate, 95)
            ),
            Badge.PERFECTIONIST: lambda: (
                (context.tasks_completed, 25) if context.tasks_completed < 25
                else (context.approval_rate, 100)
            ),

            Badge.FAST_WORKER: lambda: (
                (context.tasks_completed, 5) if context.tasks_completed < 5
                else (100 - context.avg_completion_percentage, 50)
            ),
            Badge.LIGHTNING: lambda: (context.fast_completions, 10),

            Badge.TRUSTED: lambda: (context.dispute_free_tasks, 25),
            Badge.EXPERT: lambda: (context.days_above_85, 30),

            Badge.PHOTOGRAPHER: lambda: (
                context.category_counts.get("photo", 0) +
                context.category_counts.get("photo_geo", 0),
                20
            ),
            Badge.DELIVERY_PRO: lambda: (
                context.category_counts.get("delivery", 0) +
                context.category_counts.get("physical_presence", 0),
                20
            ),

            Badge.STREAK_7: lambda: (context.current_streak_days, 7),
            Badge.STREAK_30: lambda: (context.current_streak_days, 30),

            Badge.MENTOR: lambda: (context.referrals_active, 5),
        }

        for badge, calc_fn in progress_calcs.items():
            if badge in current_set:
                continue

            try:
                current_val, target = calc_fn()
                if isinstance(current_val, tuple):
                    current_val, target = current_val

                percentage = min(100, (current_val / target) * 100) if target > 0 else 0
                remaining = max(0, target - current_val)

                defn = self.definitions.get(badge)
                progress_list.append({
                    "badge": badge.value,
                    "name": defn.name if defn else badge.value,
                    "current": current_val,
                    "target": target,
                    "percentage": round(percentage, 1),
                    "remaining": remaining,
                    "category": defn.category if defn else "unknown",
                    "rarity": defn.rarity if defn else "common",
                })
            except Exception:
                continue

        # Sort by completion percentage (closest to earning first)
        progress_list.sort(key=lambda p: -p["percentage"])

        return progress_list

    def calculate_badge_points(self, badges: List[Badge]) -> int:
        """
        Calculate total bonus points from badges.

        Args:
            badges: List of earned badges

        Returns:
            Total points
        """
        total = 0
        for badge in badges:
            defn = self.definitions.get(badge)
            if defn:
                total += defn.points

        return total

    def get_badge_summary(
        self,
        badges: List[Badge],
    ) -> Dict[str, Any]:
        """
        Get a summary of earned badges.

        Args:
            badges: List of earned badges

        Returns:
            Summary with counts by category and rarity
        """
        by_category: Dict[str, int] = {}
        by_rarity: Dict[str, int] = {}

        for badge in badges:
            defn = self.definitions.get(badge)
            if defn:
                by_category[defn.category] = by_category.get(defn.category, 0) + 1
                by_rarity[defn.rarity] = by_rarity.get(defn.rarity, 0) + 1

        return {
            "total": len(badges),
            "total_points": self.calculate_badge_points(badges),
            "by_category": by_category,
            "by_rarity": by_rarity,
            "badges": [b.value for b in badges],
        }


def check_and_award_badges(
    rep: ReputationScore,
    context: BadgeContext,
) -> Tuple[ReputationScore, List[EarnedBadge]]:
    """
    Check for and award any newly eligible badges.

    Convenience function that checks eligibility and returns
    updated reputation with newly awarded badges.

    Args:
        rep: Current reputation
        context: Worker's current stats context

    Returns:
        Tuple of (updated reputation, list of new badges)
    """
    manager = BadgeManager()

    # Check for new badges
    new_badges = manager.check_eligibility(context, rep.badges)

    # Award each new badge
    earned = []
    for badge in new_badges:
        earned_badge = manager.award_badge(
            executor_id=rep.executor_id,
            badge=badge,
            context={
                "tasks_completed": context.tasks_completed,
                "approval_rate": context.approval_rate,
            },
        )
        earned.append(earned_badge)
        rep.badges.append(badge)

    # Update score with badge points if any new badges
    if earned:
        bonus_points = sum(
            manager.definitions[b.badge].points for b in earned
        )
        # Add to alpha (good thing)
        rep.alpha += bonus_points * 0.1

    return rep, earned
