"""
Leaderboard Functions for Execution Market

Provides rankings and leaderboard functionality:
1. Top workers by score (global and by location)
2. Rising stars (fastest improving)
3. Category specialists
4. Recent activity leaders

Why leaderboards?
- Motivation through gamification
- Helps agents find quality workers
- Creates healthy competition
- Recognizes top performers
"""

from datetime import datetime, timedelta, UTC
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import ReputationScore, Badge


class LeaderboardPeriod(str, Enum):
    """Time periods for leaderboards."""
    ALL_TIME = "all_time"
    THIS_MONTH = "this_month"
    THIS_WEEK = "this_week"
    TODAY = "today"


@dataclass
class LeaderboardEntry:
    """A single entry in a leaderboard."""
    rank: int
    executor_id: str
    display_name: Optional[str]
    score: float
    confidence: float
    tasks_completed: int
    badges: List[str]
    location: Optional[str] = None

    # Period-specific stats
    period_tasks: int = 0
    period_earnings: float = 0.0
    score_change: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rank": self.rank,
            "executor_id": self.executor_id,
            "display_name": self.display_name,
            "score": round(self.score, 2),
            "confidence": round(self.confidence, 1),
            "tasks_completed": self.tasks_completed,
            "badges": self.badges,
            "location": self.location,
            "period_tasks": self.period_tasks,
            "period_earnings": round(self.period_earnings, 2),
            "score_change": round(self.score_change, 2),
        }


@dataclass
class LeaderboardResult:
    """Complete leaderboard result."""
    title: str
    period: LeaderboardPeriod
    entries: List[LeaderboardEntry]
    total_participants: int
    location: Optional[str] = None
    category: Optional[str] = None
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(UTC)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "period": self.period.value,
            "entries": [e.to_dict() for e in self.entries],
            "total_participants": self.total_participants,
            "location": self.location,
            "category": self.category,
            "last_updated": self.last_updated.isoformat(),
        }


class LeaderboardManager:
    """
    Manages leaderboard queries and rankings.

    In production, this would query the database directly.
    Here we provide the interface and logic for building leaderboards.

    Example:
        >>> manager = LeaderboardManager()
        >>> result = manager.get_top_workers(limit=10)
        >>> for entry in result.entries:
        ...     print(f"{entry.rank}. {entry.display_name}: {entry.score}")
    """

    def __init__(self, db_client=None):
        """
        Initialize leaderboard manager.

        Args:
            db_client: Optional database client for queries
        """
        self.db_client = db_client

    async def get_top_workers(
        self,
        limit: int = 10,
        location: Optional[str] = None,
        period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME,
        min_tasks: int = 5,
        min_confidence: float = 20.0,
    ) -> LeaderboardResult:
        """
        Get top workers by reputation score.

        Args:
            limit: Maximum entries to return
            location: Optional location filter (city or country)
            period: Time period filter
            min_tasks: Minimum tasks to be eligible
            min_confidence: Minimum confidence score

        Returns:
            LeaderboardResult with top workers
        """
        if not self.db_client:
            return self._mock_top_workers(limit, location, period)

        # Build query
        query = self.db_client.table("executors").select(
            "id, display_name, reputation_score, tasks_completed, location_city, location_country"
        ).gte("tasks_completed", min_tasks)

        # Apply location filter
        if location:
            query = query.or_(
                f"location_city.ilike.%{location}%,location_country.ilike.%{location}%"
            )

        # Order and limit
        query = query.order("reputation_score", desc=True).limit(limit)

        result = await query.execute()
        executors = result.data or []

        # Build entries
        entries = []
        for idx, executor in enumerate(executors, 1):
            entries.append(LeaderboardEntry(
                rank=idx,
                executor_id=executor["id"],
                display_name=executor.get("display_name", "Anonymous"),
                score=executor.get("reputation_score", 50),
                confidence=50.0,  # Would need to query reputation table
                tasks_completed=executor.get("tasks_completed", 0),
                badges=[],  # Would need to query badges
                location=executor.get("location_city"),
            ))

        title = "Top Workers"
        if location:
            title = f"Top Workers in {location}"

        return LeaderboardResult(
            title=title,
            period=period,
            entries=entries,
            total_participants=len(executors),
            location=location,
        )

    async def get_rising_stars(
        self,
        limit: int = 10,
        days: int = 30,
    ) -> LeaderboardResult:
        """
        Get fastest improving workers.

        Rising stars are workers who have significantly improved
        their score in the given time period.

        Args:
            limit: Maximum entries
            days: Period to measure improvement

        Returns:
            LeaderboardResult with rising stars
        """
        if not self.db_client:
            return self._mock_rising_stars(limit, days)

        # This would query reputation_log to calculate score changes
        # For now, we query executors and would need to join with history

        cutoff = datetime.now(UTC) - timedelta(days=days)

        # In production: query reputation_log for score changes
        # SELECT executor_id,
        #        MAX(new_score) - MIN(old_score) as improvement
        # FROM reputation_log
        # WHERE created_at > cutoff
        # GROUP BY executor_id
        # ORDER BY improvement DESC

        return self._mock_rising_stars(limit, days)

    async def get_specialists(
        self,
        category: str,
        limit: int = 10,
        min_category_tasks: int = 10,
    ) -> LeaderboardResult:
        """
        Get top workers in a specific category.

        Args:
            category: Task category (photo, delivery, data_collection, etc.)
            limit: Maximum entries
            min_category_tasks: Minimum tasks in category to qualify

        Returns:
            LeaderboardResult with category specialists
        """
        if not self.db_client:
            return self._mock_specialists(category, limit)

        # In production: query task completions by category
        # SELECT executor_id, COUNT(*) as category_tasks,
        #        AVG(rating) as avg_rating
        # FROM submissions s
        # JOIN tasks t ON s.task_id = t.id
        # WHERE t.category = :category
        #   AND s.agent_verdict = 'accepted'
        # GROUP BY executor_id
        # HAVING COUNT(*) >= min_category_tasks
        # ORDER BY avg_rating DESC, category_tasks DESC

        return self._mock_specialists(category, limit)

    async def get_weekly_leaders(
        self,
        limit: int = 10,
        location: Optional[str] = None,
    ) -> LeaderboardResult:
        """
        Get leaders for the current week.

        Based on tasks completed and ratings received this week.

        Args:
            limit: Maximum entries
            location: Optional location filter

        Returns:
            LeaderboardResult
        """
        if not self.db_client:
            return self._mock_weekly_leaders(limit, location)

        week_start = datetime.now(UTC) - timedelta(days=7)

        # Query completions this week
        # ...

        return self._mock_weekly_leaders(limit, location)

    async def get_worker_rank(
        self,
        executor_id: str,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific worker's ranking.

        Args:
            executor_id: Worker's ID
            location: Optional location for local rank

        Returns:
            Dict with global rank, local rank, percentile
        """
        if not self.db_client:
            return {
                "executor_id": executor_id,
                "global_rank": 42,
                "local_rank": 5 if location else None,
                "percentile": 85.0,
                "total_workers": 1000,
                "location": location,
            }

        # Count workers with higher score
        # ...

        return {
            "executor_id": executor_id,
            "global_rank": None,
            "local_rank": None,
            "percentile": None,
        }

    # Mock data for testing without database

    def _mock_top_workers(
        self,
        limit: int,
        location: Optional[str],
        period: LeaderboardPeriod,
    ) -> LeaderboardResult:
        """Generate mock top workers data."""
        entries = []
        for i in range(1, min(limit + 1, 11)):
            entries.append(LeaderboardEntry(
                rank=i,
                executor_id=f"worker_{i:03d}",
                display_name=f"Worker {i}",
                score=95 - (i * 3),
                confidence=80 + (10 - i),
                tasks_completed=100 - (i * 5),
                badges=["reliable", "quality_star"] if i <= 3 else ["reliable"],
                location=location or "Mexico City",
            ))

        return LeaderboardResult(
            title=f"Top Workers" + (f" in {location}" if location else ""),
            period=period,
            entries=entries,
            total_participants=100,
            location=location,
        )

    def _mock_rising_stars(
        self,
        limit: int,
        days: int,
    ) -> LeaderboardResult:
        """Generate mock rising stars data."""
        entries = []
        for i in range(1, min(limit + 1, 11)):
            entries.append(LeaderboardEntry(
                rank=i,
                executor_id=f"star_{i:03d}",
                display_name=f"Rising Star {i}",
                score=65 + (10 - i),
                confidence=40 + (i * 5),
                tasks_completed=15 - i,
                badges=["newcomer"],
                score_change=20 - (i * 2),  # How much they improved
                period_tasks=10 - i,
            ))

        return LeaderboardResult(
            title=f"Rising Stars (Last {days} Days)",
            period=LeaderboardPeriod.THIS_MONTH,
            entries=entries,
            total_participants=50,
        )

    def _mock_specialists(
        self,
        category: str,
        limit: int,
    ) -> LeaderboardResult:
        """Generate mock category specialists data."""
        entries = []
        badge_map = {
            "photo": "photographer",
            "delivery": "delivery_pro",
            "data_collection": "surveyor",
            "verification": "inspector",
        }
        specialty_badge = badge_map.get(category, "reliable")

        for i in range(1, min(limit + 1, 11)):
            entries.append(LeaderboardEntry(
                rank=i,
                executor_id=f"specialist_{category}_{i:03d}",
                display_name=f"{category.title()} Expert {i}",
                score=90 - (i * 2),
                confidence=75 + (10 - i),
                tasks_completed=50 - (i * 3),
                badges=[specialty_badge, "reliable"],
            ))

        return LeaderboardResult(
            title=f"Top {category.replace('_', ' ').title()} Specialists",
            period=LeaderboardPeriod.ALL_TIME,
            entries=entries,
            total_participants=30,
            category=category,
        )

    def _mock_weekly_leaders(
        self,
        limit: int,
        location: Optional[str],
    ) -> LeaderboardResult:
        """Generate mock weekly leaders data."""
        entries = []
        for i in range(1, min(limit + 1, 11)):
            entries.append(LeaderboardEntry(
                rank=i,
                executor_id=f"weekly_{i:03d}",
                display_name=f"Active Worker {i}",
                score=80 - (i * 2),
                confidence=70,
                tasks_completed=30 - (i * 2),
                badges=["streak_7"],
                period_tasks=8 - i,
                period_earnings=(8 - i) * 15.0,
            ))

        return LeaderboardResult(
            title="This Week's Leaders" + (f" in {location}" if location else ""),
            period=LeaderboardPeriod.THIS_WEEK,
            entries=entries,
            total_participants=80,
            location=location,
        )


# Convenience functions

async def get_top_workers(
    limit: int = 10,
    location: Optional[str] = None,
    db_client=None,
) -> LeaderboardResult:
    """
    Get top workers by reputation score.

    Convenience function that creates manager and runs query.

    Args:
        limit: Number of entries to return
        location: Optional location filter
        db_client: Optional database client

    Returns:
        LeaderboardResult
    """
    manager = LeaderboardManager(db_client)
    return await manager.get_top_workers(limit=limit, location=location)


async def get_rising_stars(
    limit: int = 10,
    db_client=None,
) -> LeaderboardResult:
    """
    Get fastest improving workers.

    Args:
        limit: Number of entries
        db_client: Optional database client

    Returns:
        LeaderboardResult
    """
    manager = LeaderboardManager(db_client)
    return await manager.get_rising_stars(limit=limit)


async def get_specialists(
    category: str,
    limit: int = 10,
    db_client=None,
) -> LeaderboardResult:
    """
    Get top workers in a specific category.

    Args:
        category: Task category
        limit: Number of entries
        db_client: Optional database client

    Returns:
        LeaderboardResult
    """
    manager = LeaderboardManager(db_client)
    return await manager.get_specialists(category=category, limit=limit)


def calculate_percentile(rank: int, total: int) -> float:
    """
    Calculate percentile from rank and total participants.

    Args:
        rank: Worker's rank (1 = highest)
        total: Total number of participants

    Returns:
        Percentile (0-100, higher is better)
    """
    if total <= 0:
        return 0.0
    if rank <= 0:
        return 100.0

    # Percentile = (total - rank + 1) / total * 100
    return ((total - rank + 1) / total) * 100
