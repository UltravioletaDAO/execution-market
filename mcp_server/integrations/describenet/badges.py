"""
Badge Management for Execution Market (NOW-168)

Manages fusion badges that represent sustained excellence:
- MASTER_WORKER: 50+ tasks, 6+ months active, high reputation
- TRUSTED_REQUESTER: 100+ tasks posted, good worker ratings
- EARLY_ADOPTER: First 1000 users
- SPECIALIST: 20+ tasks in single category

Badges are harder to earn than seals and represent long-term commitment.
They have tiered levels (Bronze, Silver, Gold, Platinum).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

from .seals import Badge, BadgeType, SealStatus
from .client import DescribeNetClient, DescribeNetError
from .worker_seals import WorkerMetrics, WorkerSealType
from .requester_seals import RequesterMetrics

logger = logging.getLogger(__name__)


@dataclass
class MasterWorkerCriteria:
    """
    Criteria for MASTER_WORKER badge levels (NOW-168).

    Levels:
    - Bronze: 50+ tasks, 6+ months, 75+ rating
    - Silver: 100+ tasks, 12+ months, 80+ rating, 3+ seals
    - Gold: 200+ tasks, 18+ months, 85+ rating, 4 seals
    - Platinum: 500+ tasks, 24+ months, 90+ rating, 4 seals, no disputes in 6mo
    """
    # Bronze (Level 1)
    bronze_min_tasks: int = 50
    bronze_min_months: int = 6
    bronze_min_rating: float = 75.0

    # Silver (Level 2)
    silver_min_tasks: int = 100
    silver_min_months: int = 12
    silver_min_rating: float = 80.0
    silver_min_seals: int = 3

    # Gold (Level 3)
    gold_min_tasks: int = 200
    gold_min_months: int = 18
    gold_min_rating: float = 85.0
    gold_min_seals: int = 4

    # Platinum (Level 4)
    platinum_min_tasks: int = 500
    platinum_min_months: int = 24
    platinum_min_rating: float = 90.0
    platinum_min_seals: int = 4
    platinum_no_disputes_months: int = 6


@dataclass
class TrustedRequesterCriteria:
    """Criteria for TRUSTED_REQUESTER badge levels."""
    # Bronze
    bronze_min_tasks: int = 100
    bronze_min_months: int = 6
    bronze_min_acceptance_rate: float = 0.80

    # Silver
    silver_min_tasks: int = 250
    silver_min_months: int = 12
    silver_min_acceptance_rate: float = 0.85
    silver_min_seals: int = 2

    # Gold
    gold_min_tasks: int = 500
    gold_min_months: int = 18
    gold_min_acceptance_rate: float = 0.90
    gold_min_seals: int = 3


@dataclass
class SpecialistCriteria:
    """Criteria for SPECIALIST badge (category-specific)."""
    min_tasks_in_category: int = 20
    min_rating_in_category: float = 80.0
    min_success_rate_in_category: float = 0.90


class BadgeManager:
    """
    Manages badge lifecycle: evaluation, creation, and upgrades.

    Badges represent sustained excellence over time and have multiple levels.

    Usage:
        manager = BadgeManager(client)

        # Evaluate worker for badges
        result = await manager.evaluate_worker_badges(worker_id, metrics, seals)

        # Check specific badge eligibility
        level = manager.check_master_worker_eligibility(metrics, seals)
    """

    def __init__(
        self,
        client: Optional[DescribeNetClient] = None,
        local_mode: bool = False,
    ):
        """
        Initialize badge manager.

        Args:
            client: describe.net API client
            local_mode: If True, don't sync to describe.net (for testing)
        """
        self.client = client or DescribeNetClient.from_env()
        self.local_mode = local_mode
        self._badge_cache: Dict[str, List[Badge]] = {}

        # Criteria
        self.master_worker_criteria = MasterWorkerCriteria()
        self.trusted_requester_criteria = TrustedRequesterCriteria()
        self.specialist_criteria = SpecialistCriteria()

    # ============== MASTER_WORKER BADGE (NOW-168) ==============

    def check_master_worker_eligibility(
        self,
        metrics: WorkerMetrics,
        active_seal_count: int,
        recent_disputes: int = 0,
    ) -> Tuple[Optional[int], str]:
        """
        Check if worker qualifies for MASTER_WORKER badge.

        Args:
            metrics: Worker metrics
            active_seal_count: Number of active seals
            recent_disputes: Disputes in last 6 months

        Returns:
            (level, reason) - level is None if not eligible, 1-4 if eligible
        """
        criteria = self.master_worker_criteria

        # Check Platinum first (highest)
        if (
            metrics.total_tasks >= criteria.platinum_min_tasks
            and metrics.days_active >= criteria.platinum_min_months * 30
            and metrics.average_rating >= criteria.platinum_min_rating
            and active_seal_count >= criteria.platinum_min_seals
            and recent_disputes == 0
        ):
            return 4, "Platinum Master Worker - exceptional long-term excellence"

        # Check Gold
        if (
            metrics.total_tasks >= criteria.gold_min_tasks
            and metrics.days_active >= criteria.gold_min_months * 30
            and metrics.average_rating >= criteria.gold_min_rating
            and active_seal_count >= criteria.gold_min_seals
        ):
            return 3, "Gold Master Worker - sustained excellence"

        # Check Silver
        if (
            metrics.total_tasks >= criteria.silver_min_tasks
            and metrics.days_active >= criteria.silver_min_months * 30
            and metrics.average_rating >= criteria.silver_min_rating
            and active_seal_count >= criteria.silver_min_seals
        ):
            return 2, "Silver Master Worker - proven track record"

        # Check Bronze
        if (
            metrics.total_tasks >= criteria.bronze_min_tasks
            and metrics.days_active >= criteria.bronze_min_months * 30
            and metrics.average_rating >= criteria.bronze_min_rating
        ):
            return 1, "Bronze Master Worker - established performer"

        # Not eligible
        missing = []
        if metrics.total_tasks < criteria.bronze_min_tasks:
            missing.append(f"tasks ({metrics.total_tasks}/{criteria.bronze_min_tasks})")
        if metrics.days_active < criteria.bronze_min_months * 30:
            missing.append(f"months active ({metrics.days_active // 30}/{criteria.bronze_min_months})")
        if metrics.average_rating < criteria.bronze_min_rating:
            missing.append(f"rating ({metrics.average_rating:.1f}/{criteria.bronze_min_rating})")

        return None, f"Not eligible - need: {', '.join(missing)}"

    # ============== TRUSTED_REQUESTER BADGE ==============

    def check_trusted_requester_eligibility(
        self,
        metrics: RequesterMetrics,
        active_seal_count: int,
    ) -> Tuple[Optional[int], str]:
        """
        Check if requester qualifies for TRUSTED_REQUESTER badge.

        Args:
            metrics: Requester metrics
            active_seal_count: Number of active seals

        Returns:
            (level, reason) - level is None if not eligible, 1-3 if eligible
        """
        criteria = self.trusted_requester_criteria

        days_active = 0
        if metrics.first_task_date:
            days_active = (datetime.now(timezone.utc) - metrics.first_task_date.replace(tzinfo=timezone.utc)).days

        # Check Gold
        if (
            metrics.total_tasks_posted >= criteria.gold_min_tasks
            and days_active >= criteria.gold_min_months * 30
            and metrics.acceptance_rate >= criteria.gold_min_acceptance_rate
            and active_seal_count >= criteria.gold_min_seals
        ):
            return 3, "Gold Trusted Requester - exemplary track record"

        # Check Silver
        if (
            metrics.total_tasks_posted >= criteria.silver_min_tasks
            and days_active >= criteria.silver_min_months * 30
            and metrics.acceptance_rate >= criteria.silver_min_acceptance_rate
            and active_seal_count >= criteria.silver_min_seals
        ):
            return 2, "Silver Trusted Requester - established reputation"

        # Check Bronze
        if (
            metrics.total_tasks_posted >= criteria.bronze_min_tasks
            and days_active >= criteria.bronze_min_months * 30
            and metrics.acceptance_rate >= criteria.bronze_min_acceptance_rate
        ):
            return 1, "Bronze Trusted Requester - good track record"

        return None, "Not eligible for Trusted Requester badge"

    # ============== SPECIALIST BADGE ==============

    def check_specialist_eligibility(
        self,
        category_metrics: Dict[str, Dict[str, Any]],
    ) -> List[Tuple[str, int, str]]:
        """
        Check if worker qualifies for SPECIALIST badges in any category.

        Args:
            category_metrics: Dict of category -> {tasks, rating, success_rate}

        Returns:
            List of (category, level, reason) for earned badges
        """
        specialists = []
        criteria = self.specialist_criteria

        for category, stats in category_metrics.items():
            tasks = stats.get("tasks", 0)
            rating = stats.get("rating", 0)
            success_rate = stats.get("success_rate", 0)

            if (
                tasks >= criteria.min_tasks_in_category
                and rating >= criteria.min_rating_in_category
                and success_rate >= criteria.min_success_rate_in_category
            ):
                # Determine level based on task count
                if tasks >= 100:
                    level = 3  # Gold
                elif tasks >= 50:
                    level = 2  # Silver
                else:
                    level = 1  # Bronze

                specialists.append((
                    category,
                    level,
                    f"{category.title()} Specialist - {tasks} tasks at {rating:.1f} rating"
                ))

        return specialists

    # ============== BADGE MANAGEMENT ==============

    async def evaluate_worker_badges(
        self,
        worker_id: str,
        metrics: WorkerMetrics,
        active_seals: List[Any],  # List of Seal objects
        category_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
        recent_disputes: int = 0,
    ) -> "BadgeUpdateResult":
        """
        Evaluate worker for all applicable badges.

        Args:
            worker_id: Worker ID
            metrics: Worker metrics
            active_seals: List of active seals
            category_metrics: Category-specific metrics for specialist badges
            recent_disputes: Disputes in last 6 months

        Returns:
            BadgeUpdateResult with earned/upgraded badges
        """
        current_badges = await self.get_user_badges(worker_id)
        current_badge_types = {b.badge_type: b for b in current_badges if b.is_active}

        badges_earned = []
        badges_upgraded = []
        seal_count = len(active_seals)

        # Check MASTER_WORKER
        level, reason = self.check_master_worker_eligibility(metrics, seal_count, recent_disputes)
        if level:
            existing = current_badge_types.get(BadgeType.MASTER_WORKER)
            if existing:
                if level > existing.level:
                    # Upgrade
                    badge = await self.upgrade_badge(existing, level, metrics.to_dict())
                    if badge:
                        badges_upgraded.append(badge)
            else:
                # New badge
                badge = await self.create_badge(
                    worker_id, BadgeType.MASTER_WORKER, "worker", level, metrics.to_dict()
                )
                if badge:
                    badges_earned.append(badge)

        # Check SPECIALIST badges
        if category_metrics:
            specialist_eligibility = self.check_specialist_eligibility(category_metrics)
            for category, level, reason in specialist_eligibility:
                # Use composite key for specialist badges
                badge_key = f"specialist_{category}"
                existing_specialist = next(
                    (b for b in current_badges
                     if b.badge_type == BadgeType.SPECIALIST
                     and b.criteria_snapshot
                     and b.criteria_snapshot.get("category") == category),
                    None
                )
                if existing_specialist:
                    if level > existing_specialist.level:
                        badge = await self.upgrade_badge(
                            existing_specialist, level,
                            {"category": category, **category_metrics[category]}
                        )
                        if badge:
                            badges_upgraded.append(badge)
                else:
                    badge = await self.create_badge(
                        worker_id, BadgeType.SPECIALIST, "worker", level,
                        {"category": category, **category_metrics[category]}
                    )
                    if badge:
                        badges_earned.append(badge)

        return BadgeUpdateResult(
            user_id=worker_id,
            user_type="worker",
            badges_earned=badges_earned,
            badges_upgraded=badges_upgraded,
            current_badges=await self.get_user_badges(worker_id),
        )

    async def evaluate_requester_badges(
        self,
        requester_id: str,
        metrics: RequesterMetrics,
        active_seals: List[Any],
    ) -> "BadgeUpdateResult":
        """
        Evaluate requester for all applicable badges.

        Args:
            requester_id: Requester ID
            metrics: Requester metrics
            active_seals: List of active seals

        Returns:
            BadgeUpdateResult with earned/upgraded badges
        """
        current_badges = await self.get_user_badges(requester_id)
        current_badge_types = {b.badge_type: b for b in current_badges if b.is_active}

        badges_earned = []
        badges_upgraded = []
        seal_count = len(active_seals)

        # Check TRUSTED_REQUESTER
        level, reason = self.check_trusted_requester_eligibility(metrics, seal_count)
        if level:
            existing = current_badge_types.get(BadgeType.TRUSTED_REQUESTER)
            if existing:
                if level > existing.level:
                    badge = await self.upgrade_badge(existing, level, metrics.to_dict())
                    if badge:
                        badges_upgraded.append(badge)
            else:
                badge = await self.create_badge(
                    requester_id, BadgeType.TRUSTED_REQUESTER, "requester", level, metrics.to_dict()
                )
                if badge:
                    badges_earned.append(badge)

        return BadgeUpdateResult(
            user_id=requester_id,
            user_type="requester",
            badges_earned=badges_earned,
            badges_upgraded=badges_upgraded,
            current_badges=await self.get_user_badges(requester_id),
        )

    async def create_badge(
        self,
        user_id: str,
        badge_type: BadgeType,
        user_type: str,
        level: int,
        criteria_snapshot: Dict[str, Any],
    ) -> Optional[Badge]:
        """Create a new badge."""
        if self.local_mode:
            badge = Badge(
                badge_type=badge_type,
                user_id=user_id,
                user_type=user_type,
                status=SealStatus.ACTIVE,
                earned_at=datetime.now(timezone.utc),
                criteria_snapshot=criteria_snapshot,
                level=level,
            )
            self._update_cache(user_id, badge)
            logger.info(f"Created badge {badge_type.value} (level {level}) for {user_type} {user_id}")
            return badge

        try:
            badge = await self.client.create_badge(
                badge_type=badge_type,
                user_id=user_id,
                user_type=user_type,
                level=level,
                criteria_snapshot=criteria_snapshot,
            )
            self._update_cache(user_id, badge)
            return badge
        except DescribeNetError as e:
            logger.error(f"Failed to create badge: {e}")
            return None

    async def upgrade_badge(
        self,
        badge: Badge,
        new_level: int,
        new_snapshot: Dict[str, Any],
    ) -> Optional[Badge]:
        """Upgrade an existing badge to a higher level."""
        if self.local_mode:
            badge.level = new_level
            badge.criteria_snapshot = new_snapshot
            logger.info(f"Upgraded badge {badge.badge_type.value} to level {new_level}")
            return badge

        # In real implementation, this would call describe.net API
        # For now, create new badge with higher level
        try:
            new_badge = await self.client.create_badge(
                badge_type=badge.badge_type,
                user_id=badge.user_id,
                user_type=badge.user_type,
                level=new_level,
                criteria_snapshot=new_snapshot,
            )
            self._update_cache(badge.user_id, new_badge)
            return new_badge
        except DescribeNetError as e:
            logger.error(f"Failed to upgrade badge: {e}")
            return None

    async def get_user_badges(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> List[Badge]:
        """Get all badges for a user."""
        if self.local_mode:
            badges = self._badge_cache.get(user_id, [])
            if active_only:
                return [b for b in badges if b.is_active]
            return badges

        try:
            return await self.client.get_user_badges(user_id, active_only)
        except DescribeNetError as e:
            logger.error(f"Failed to get badges for {user_id}: {e}")
            return self._badge_cache.get(user_id, [])

    def _update_cache(self, user_id: str, badge: Badge):
        """Update local badge cache."""
        if user_id not in self._badge_cache:
            self._badge_cache[user_id] = []

        # Replace existing badge of same type (or type+category for specialist)
        self._badge_cache[user_id] = [
            b for b in self._badge_cache[user_id]
            if not self._badges_match(b, badge)
        ]
        self._badge_cache[user_id].append(badge)

    def _badges_match(self, b1: Badge, b2: Badge) -> bool:
        """Check if two badges represent the same achievement."""
        if b1.badge_type != b2.badge_type:
            return False
        if b1.badge_type == BadgeType.SPECIALIST:
            # For specialist, also check category
            cat1 = b1.criteria_snapshot.get("category") if b1.criteria_snapshot else None
            cat2 = b2.criteria_snapshot.get("category") if b2.criteria_snapshot else None
            return cat1 == cat2
        return True

    async def get_badge_display(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get formatted badge display for user profile."""
        badges = await self.get_user_badges(user_id, active_only=True)

        level_names = {1: "Bronze", 2: "Silver", 3: "Gold", 4: "Platinum"}
        level_icons = {1: "[B]", 2: "[S]", 3: "[G]", 4: "[P]"}

        badge_display = []
        for badge in badges:
            level_name = level_names.get(badge.level, f"Level {badge.level}")
            level_icon = level_icons.get(badge.level, f"[{badge.level}]")

            display = {
                "type": badge.badge_type.value,
                "level": badge.level,
                "level_name": level_name,
                "icon": level_icon,
                "display_name": badge.display_name,
                "earned_at": badge.earned_at.isoformat() if badge.earned_at else None,
            }

            # Add category for specialist badges
            if badge.badge_type == BadgeType.SPECIALIST and badge.criteria_snapshot:
                display["category"] = badge.criteria_snapshot.get("category")

            badge_display.append(display)

        return {
            "user_id": user_id,
            "badges": badge_display,
            "badge_count": len(badges),
            "highest_level": max((b.level for b in badges), default=0),
            "has_master_worker": any(b.badge_type == BadgeType.MASTER_WORKER for b in badges),
        }


@dataclass
class BadgeUpdateResult:
    """Result of badge evaluation and update."""
    user_id: str
    user_type: str
    badges_earned: List[Badge]
    badges_upgraded: List[Badge]
    current_badges: List[Badge]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "user_type": self.user_type,
            "badges_earned": [b.to_dict() for b in self.badges_earned],
            "badges_upgraded": [b.to_dict() for b in self.badges_upgraded],
            "current_badges": [b.to_dict() for b in self.current_badges],
        }


# ============== EARLY ADOPTER BADGE ==============

async def grant_early_adopter_badge(
    badge_manager: BadgeManager,
    user_id: str,
    user_type: str,
    user_number: int,
) -> Optional[Badge]:
    """
    Grant EARLY_ADOPTER badge to first 1000 users.

    Args:
        badge_manager: Badge manager instance
        user_id: User ID
        user_type: "worker" or "requester"
        user_number: User's signup number (1-1000)

    Returns:
        Badge if granted, None otherwise
    """
    if user_number > 1000:
        return None

    # Determine level based on signup order
    if user_number <= 100:
        level = 3  # Gold for first 100
    elif user_number <= 500:
        level = 2  # Silver for 101-500
    else:
        level = 1  # Bronze for 501-1000

    return await badge_manager.create_badge(
        user_id=user_id,
        badge_type=BadgeType.EARLY_ADOPTER,
        user_type=user_type,
        level=level,
        criteria_snapshot={"user_number": user_number},
    )
