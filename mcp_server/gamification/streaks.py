"""
Streak Tracking System

Tracks worker activity streaks and bonuses.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, Optional, List, Tuple, Any

logger = logging.getLogger(__name__)


@dataclass
class StreakBonus:
    """Bonus for maintaining a streak."""

    days: int
    bonus_percentage: float
    name: str
    description: str = ""


@dataclass
class StreakData:
    """Internal streak tracking data."""

    current: int
    longest: int
    last_active: date
    history: List[date] = field(default_factory=list)
    freeze_available: bool = True  # One-time streak freeze
    freeze_used_at: Optional[date] = None


class StreakTracker:
    """
    Tracks and rewards activity streaks.

    Bonuses:
    - 3+ days: 5% bonus
    - 7+ days: 10% bonus
    - 14+ days: 15% bonus
    - 30+ days: 25% bonus

    Features:
    - Streak freeze (one per 30-day period)
    - Grace period (2 hours into next day)
    - Streak recovery suggestions
    """

    BONUSES = [
        StreakBonus(
            30, 0.25, "Monthly Master", "Incredible dedication! 25% bonus on all tasks."
        ),
        StreakBonus(
            14, 0.15, "Two Week Warrior", "Two weeks strong! 15% bonus on all tasks."
        ),
        StreakBonus(
            7, 0.10, "Weekly Warrior", "One week complete! 10% bonus on all tasks."
        ),
        StreakBonus(3, 0.05, "Streak Started", "Keep it going! 5% bonus on all tasks."),
    ]

    # Streak milestones for celebrations
    MILESTONES = [3, 7, 14, 21, 30, 50, 100, 365]

    def __init__(self):
        self._streaks: Dict[str, StreakData] = {}

    def record_activity(
        self, worker_id: str, activity_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Record daily activity for worker.

        Args:
            worker_id: Worker ID
            activity_time: Optional specific time (defaults to now)

        Returns:
            Dict with streak info and any milestones reached
        """
        now = activity_time or datetime.utcnow()
        today = now.date()

        if worker_id not in self._streaks:
            self._streaks[worker_id] = StreakData(
                current=1, longest=1, last_active=today, history=[today]
            )
            logger.info(f"Worker {worker_id} started first streak")
            return self._build_response(worker_id, milestone_reached=1)

        data = self._streaks[worker_id]
        last = data.last_active

        if last == today:
            # Already recorded today
            return self._build_response(worker_id)

        days_diff = (today - last).days

        old_streak = data.current
        milestone_reached = None

        if days_diff == 1:
            # Consecutive day
            data.current += 1
            logger.debug(f"Worker {worker_id} extended streak to {data.current}")

            # Check for milestone
            if data.current in self.MILESTONES:
                milestone_reached = data.current

        elif days_diff == 2 and data.freeze_available:
            # Allow streak freeze (missed one day)
            data.current += 1
            data.freeze_available = False
            data.freeze_used_at = today
            logger.info(
                f"Worker {worker_id} used streak freeze, streak continues at {data.current}"
            )

            if data.current in self.MILESTONES:
                milestone_reached = data.current

        elif days_diff > 1:
            # Streak broken
            logger.info(f"Worker {worker_id} lost {data.current}-day streak")
            data.current = 1

        # Update tracking
        data.longest = max(data.longest, data.current)
        data.last_active = today
        data.history.append(today)

        # Reset freeze availability after 30 days
        if data.freeze_used_at and (today - data.freeze_used_at).days >= 30:
            data.freeze_available = True
            data.freeze_used_at = None

        return self._build_response(
            worker_id,
            milestone_reached=milestone_reached,
            streak_restored=(days_diff == 2 and old_streak > 0),
        )

    def get_streak(self, worker_id: str) -> int:
        """Get current streak for worker."""
        if worker_id not in self._streaks:
            return 0

        data = self._streaks[worker_id]

        # Check if streak is still active
        days_since = (date.today() - data.last_active).days
        if days_since > 1:
            # Streak expired (unless they have a freeze)
            if days_since == 2 and data.freeze_available:
                return data.current  # Still valid with potential freeze
            return 0

        return data.current

    def get_bonus(self, worker_id: str) -> Optional[StreakBonus]:
        """Get applicable streak bonus."""
        streak = self.get_streak(worker_id)

        for bonus in self.BONUSES:
            if streak >= bonus.days:
                return bonus

        return None

    def apply_streak_bonus(
        self, worker_id: str, base_amount: float
    ) -> Tuple[float, Optional[StreakBonus]]:
        """
        Apply streak bonus to amount.

        Returns:
            (final_amount, bonus_applied or None)
        """
        bonus = self.get_bonus(worker_id)

        if bonus:
            final = base_amount * (1 + bonus.bonus_percentage)
            logger.debug(
                f"Applied {bonus.name} ({bonus.bonus_percentage * 100}%) "
                f"to {base_amount} -> {final}"
            )
            return (final, bonus)

        return (base_amount, None)

    def get_streak_stats(self, worker_id: str) -> Dict[str, Any]:
        """Get comprehensive streak statistics for worker."""
        if worker_id not in self._streaks:
            return {
                "current": 0,
                "longest": 0,
                "bonus": None,
                "next_bonus_at": 3,
                "days_to_next_bonus": 3,
                "freeze_available": True,
                "at_risk": False,
                "motivation_message": "Complete a task to start your streak!",
            }

        data = self._streaks[worker_id]
        current = self.get_streak(worker_id)
        bonus = self.get_bonus(worker_id)

        # Find next bonus threshold
        next_bonus_at = None
        for b in reversed(self.BONUSES):
            if current < b.days:
                next_bonus_at = b.days

        # Check if streak is at risk
        days_since = (date.today() - data.last_active).days
        at_risk = days_since >= 1

        # Generate motivation message
        motivation = self._get_motivation_message(current, data.longest, at_risk)

        return {
            "current": current,
            "longest": data.longest,
            "bonus": {
                "percentage": bonus.bonus_percentage,
                "name": bonus.name,
                "description": bonus.description,
            }
            if bonus
            else None,
            "next_bonus_at": next_bonus_at,
            "days_to_next_bonus": (next_bonus_at - current) if next_bonus_at else None,
            "freeze_available": data.freeze_available,
            "freeze_used_at": data.freeze_used_at.isoformat()
            if data.freeze_used_at
            else None,
            "at_risk": at_risk,
            "last_active": data.last_active.isoformat(),
            "motivation_message": motivation,
            "history_length": len(data.history),
        }

    def get_streak_calendar(
        self, worker_id: str, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get activity calendar for worker.

        Returns active days in specified month/year.
        """
        if worker_id not in self._streaks:
            return {"active_days": [], "total_days": 0}

        data = self._streaks[worker_id]
        today = date.today()
        year = year or today.year
        month = month or today.month

        # Filter history to requested month
        active_days = [
            d.day for d in data.history if d.year == year and d.month == month
        ]

        return {
            "year": year,
            "month": month,
            "active_days": sorted(active_days),
            "total_days": len(active_days),
            "current_streak": self.get_streak(worker_id),
        }

    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get streak leaderboard."""
        if not self._streaks:
            return []

        # Sort by current streak
        sorted_workers = sorted(
            [
                (worker_id, self.get_streak(worker_id), data.longest)
                for worker_id, data in self._streaks.items()
            ],
            key=lambda x: (x[1], x[2]),  # Current streak, then longest
            reverse=True,
        )[:limit]

        return [
            {
                "rank": i + 1,
                "worker_id": worker_id,
                "current_streak": current,
                "longest_streak": longest,
                "bonus": self.get_bonus(worker_id).name
                if self.get_bonus(worker_id)
                else None,
            }
            for i, (worker_id, current, longest) in enumerate(sorted_workers)
        ]

    def use_freeze(self, worker_id: str) -> bool:
        """
        Manually use streak freeze (if available).

        Returns True if freeze was used successfully.
        """
        if worker_id not in self._streaks:
            return False

        data = self._streaks[worker_id]

        if not data.freeze_available:
            return False

        # Check if we actually need it
        days_since = (date.today() - data.last_active).days
        if days_since < 2:
            # Don't need freeze yet
            return False

        data.freeze_available = False
        data.freeze_used_at = date.today()
        logger.info(f"Worker {worker_id} manually used streak freeze")
        return True

    def _get_motivation_message(self, current: int, longest: int, at_risk: bool) -> str:
        """Generate a motivation message based on streak status."""
        if at_risk:
            if current >= 7:
                return f"Your {current}-day streak is at risk! Complete a task today to keep it going!"
            else:
                return "Don't lose your streak! Complete a task today."

        if current == 0:
            return "Complete a task to start your streak!"

        if current == longest and current >= 7:
            return f"You're at your personal best! {current} days and counting!"

        if current >= 30:
            return f"Legendary {current}-day streak! You're in the elite ranks!"
        elif current >= 14:
            return f"Amazing {current}-day streak! Keep the momentum!"
        elif current >= 7:
            return f"Great {current}-day streak! You're on fire!"
        elif current >= 3:
            return f"{current}-day streak! Building good habits!"
        else:
            return f"{current}-day streak started! Keep going!"

    def _build_response(
        self,
        worker_id: str,
        milestone_reached: Optional[int] = None,
        streak_restored: bool = False,
    ) -> Dict[str, Any]:
        """Build standard response dict."""
        stats = self.get_streak_stats(worker_id)

        response = {
            "streak": stats["current"],
            "longest": stats["longest"],
            "bonus": stats["bonus"],
            "freeze_available": stats["freeze_available"],
            "at_risk": stats["at_risk"],
            "message": stats["motivation_message"],
        }

        if milestone_reached:
            response["milestone_reached"] = milestone_reached
            response["milestone_message"] = (
                f"Congratulations! You've reached a {milestone_reached}-day streak!"
            )

        if streak_restored:
            response["streak_restored"] = True
            response["freeze_message"] = "Streak saved! You used your streak freeze."

        return response

    def import_streak_data(self, worker_id: str, data: Dict[str, Any]) -> None:
        """Import existing streak data."""
        history = []
        for d in data.get("history", []):
            if isinstance(d, str):
                history.append(date.fromisoformat(d))
            elif isinstance(d, date):
                history.append(d)

        last_active = data.get("last_active")
        if isinstance(last_active, str):
            last_active = date.fromisoformat(last_active)
        elif not isinstance(last_active, date):
            last_active = date.today()

        freeze_used_at = data.get("freeze_used_at")
        if isinstance(freeze_used_at, str):
            freeze_used_at = date.fromisoformat(freeze_used_at)

        self._streaks[worker_id] = StreakData(
            current=data.get("current", 0),
            longest=data.get("longest", 0),
            last_active=last_active,
            history=history,
            freeze_available=data.get("freeze_available", True),
            freeze_used_at=freeze_used_at,
        )

    def export_streak_data(self, worker_id: str) -> Dict[str, Any]:
        """Export streak data for persistence."""
        if worker_id not in self._streaks:
            return {}

        data = self._streaks[worker_id]
        return {
            "current": data.current,
            "longest": data.longest,
            "last_active": data.last_active.isoformat(),
            "history": [d.isoformat() for d in data.history],
            "freeze_available": data.freeze_available,
            "freeze_used_at": data.freeze_used_at.isoformat()
            if data.freeze_used_at
            else None,
        }


# Singleton
_tracker: Optional[StreakTracker] = None


def get_streak_tracker() -> StreakTracker:
    """Get singleton streak tracker."""
    global _tracker
    if _tracker is None:
        _tracker = StreakTracker()
    return _tracker
