"""
Gamified Progression System (NOW-136)

Levels: Novice -> Apprentice -> Journeyman -> Expert -> Master
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerLevel(str, Enum):
    """Worker progression levels."""
    NOVICE = "novice"           # 0-24 tasks
    APPRENTICE = "apprentice"   # 25-99 tasks
    JOURNEYMAN = "journeyman"   # 100-299 tasks
    EXPERT = "expert"           # 300-999 tasks
    MASTER = "master"           # 1000+ tasks


class AchievementCategory(str, Enum):
    """Achievement categories."""
    MILESTONES = "milestones"
    SPEED = "speed"
    QUALITY = "quality"
    CONSISTENCY = "consistency"
    SOCIAL = "social"
    SPECIAL = "special"


@dataclass
class LevelConfig:
    """Configuration for a level."""
    level: WorkerLevel
    min_tasks: int
    max_tasks: int  # -1 for unlimited
    bounty_bonus: float  # Percentage bonus
    priority_boost: float
    max_concurrent_tasks: int
    verification_tier: str  # "auto", "ai", "standard"
    features: List[str]
    badge_color: str


@dataclass
class Achievement:
    """An achievement/badge."""
    id: str
    name: str
    description: str
    category: AchievementCategory
    icon: str
    points: int
    requirements: Dict[str, Any]
    secret: bool = False  # Hidden until unlocked
    rarity: str = "common"  # common, uncommon, rare, epic, legendary


@dataclass
class WorkerProgress:
    """Worker's current progress."""
    worker_id: str
    level: WorkerLevel
    total_tasks: int
    xp: int
    xp_to_next_level: int
    achievements: List[str]
    current_streak: int
    longest_streak: int
    total_earnings: float
    joined_at: datetime
    last_active: datetime

    # Additional tracking fields
    five_star_tasks: int = 0
    consecutive_approved: int = 0
    excellent_photos: int = 0
    referrals: int = 0
    helped_workers: int = 0
    countries: List[str] = field(default_factory=list)
    highest_task_value: float = 0.0
    tasks_per_hour_record: int = 0


class ProgressionSystem:
    """
    Gamified progression system for workers.

    Features:
    - Level progression (Novice -> Master)
    - XP and achievements
    - Streak bonuses
    - Level-based perks
    """

    LEVELS = {
        WorkerLevel.NOVICE: LevelConfig(
            level=WorkerLevel.NOVICE,
            min_tasks=0,
            max_tasks=24,
            bounty_bonus=0,
            priority_boost=1.0,
            max_concurrent_tasks=2,
            verification_tier="standard",
            features=["basic_tasks", "community_support"],
            badge_color="#9CA3AF"  # Gray
        ),
        WorkerLevel.APPRENTICE: LevelConfig(
            level=WorkerLevel.APPRENTICE,
            min_tasks=25,
            max_tasks=99,
            bounty_bonus=5,
            priority_boost=1.1,
            max_concurrent_tasks=3,
            verification_tier="ai",
            features=["basic_tasks", "community_support", "priority_tasks"],
            badge_color="#3B82F6"  # Blue
        ),
        WorkerLevel.JOURNEYMAN: LevelConfig(
            level=WorkerLevel.JOURNEYMAN,
            min_tasks=100,
            max_tasks=299,
            bounty_bonus=10,
            priority_boost=1.25,
            max_concurrent_tasks=5,
            verification_tier="ai",
            features=["all_tasks", "priority_support", "early_access"],
            badge_color="#8B5CF6"  # Purple
        ),
        WorkerLevel.EXPERT: LevelConfig(
            level=WorkerLevel.EXPERT,
            min_tasks=300,
            max_tasks=999,
            bounty_bonus=15,
            priority_boost=1.5,
            max_concurrent_tasks=7,
            verification_tier="auto",
            features=["all_tasks", "priority_support", "early_access", "beta_features"],
            badge_color="#F59E0B"  # Amber
        ),
        WorkerLevel.MASTER: LevelConfig(
            level=WorkerLevel.MASTER,
            min_tasks=1000,
            max_tasks=-1,
            bounty_bonus=20,
            priority_boost=2.0,
            max_concurrent_tasks=10,
            verification_tier="auto",
            features=["all_tasks", "vip_support", "early_access", "beta_features", "validator_eligible"],
            badge_color="#EF4444"  # Red
        ),
    }

    ACHIEVEMENTS = [
        # Milestones
        Achievement("first_task", "First Steps", "Complete your first task",
                   AchievementCategory.MILESTONES, "target", 10, {"tasks": 1}),
        Achievement("ten_tasks", "Getting Started", "Complete 10 tasks",
                   AchievementCategory.MILESTONES, "star", 25, {"tasks": 10}),
        Achievement("fifty_tasks", "Dedicated Worker", "Complete 50 tasks",
                   AchievementCategory.MILESTONES, "muscle", 50, {"tasks": 50}),
        Achievement("hundred_tasks", "Century", "Complete 100 tasks",
                   AchievementCategory.MILESTONES, "trophy", 100, {"tasks": 100}),
        Achievement("five_hundred", "Power Worker", "Complete 500 tasks",
                   AchievementCategory.MILESTONES, "lightning", 250, {"tasks": 500}),
        Achievement("thousand", "Legend", "Complete 1000 tasks",
                   AchievementCategory.MILESTONES, "crown", 500, {"tasks": 1000}, rarity="legendary"),

        # Speed
        Achievement("speed_demon", "Speed Demon", "Complete 5 tasks in 1 hour",
                   AchievementCategory.SPEED, "rocket", 50, {"tasks_per_hour": 5}),
        Achievement("early_bird", "Early Bird", "Complete a task before 7 AM",
                   AchievementCategory.SPEED, "sunrise", 25, {"early_morning": True}),
        Achievement("night_owl", "Night Owl", "Complete a task after midnight",
                   AchievementCategory.SPEED, "owl", 25, {"late_night": True}),

        # Quality
        Achievement("perfectionist", "Perfectionist", "10 tasks with 5-star ratings",
                   AchievementCategory.QUALITY, "sparkles", 75, {"five_star_tasks": 10}),
        Achievement("no_rejections", "Flawless", "50 tasks without rejection",
                   AchievementCategory.QUALITY, "diamond", 100, {"consecutive_approved": 50}, rarity="rare"),
        Achievement("photo_pro", "Photo Pro", "All photos rated excellent for 20 tasks",
                   AchievementCategory.QUALITY, "camera", 50, {"excellent_photos": 20}),

        # Consistency
        Achievement("week_streak", "Weekly Warrior", "7-day active streak",
                   AchievementCategory.CONSISTENCY, "fire", 40, {"streak_days": 7}),
        Achievement("month_streak", "Monthly Master", "30-day active streak",
                   AchievementCategory.CONSISTENCY, "moon", 100, {"streak_days": 30}, rarity="rare"),
        Achievement("reliable", "Old Reliable", "90% completion rate over 100 tasks",
                   AchievementCategory.CONSISTENCY, "lock", 75, {"completion_rate": 0.9, "min_tasks": 100}),

        # Social
        Achievement("referral_1", "Connector", "Refer 1 worker",
                   AchievementCategory.SOCIAL, "handshake", 25, {"referrals": 1}),
        Achievement("referral_5", "Networker", "Refer 5 workers",
                   AchievementCategory.SOCIAL, "globe", 75, {"referrals": 5}),
        Achievement("community_helper", "Helper", "Help 10 workers via support",
                   AchievementCategory.SOCIAL, "chat", 50, {"helped_workers": 10}),

        # Special
        Achievement("first_high_value", "High Roller", "Complete a task worth $50+",
                   AchievementCategory.SPECIAL, "money", 100, {"task_value": 50}),
        Achievement("globe_trotter", "Globe Trotter", "Complete tasks in 3 countries",
                   AchievementCategory.SPECIAL, "world", 150, {"countries": 3}, rarity="epic"),
        Achievement("launch_worker", "OG Worker", "Joined during launch month",
                   AchievementCategory.SPECIAL, "cake", 200, {"launch_month": True}, rarity="legendary", secret=True),
    ]

    # XP rewards
    XP_REWARDS = {
        "task_complete": 10,
        "five_star_rating": 5,
        "fast_completion": 3,
        "streak_day": 2,
        "achievement_unlock": 20,
        "referral": 50,
        "high_value_task": 15,  # Per $10 above $5
    }

    def __init__(self):
        self._progress: Dict[str, WorkerProgress] = {}

    def get_level_for_tasks(self, task_count: int) -> WorkerLevel:
        """Get level based on task count."""
        for level_config in sorted(self.LEVELS.values(), key=lambda x: x.min_tasks, reverse=True):
            if task_count >= level_config.min_tasks:
                return level_config.level
        return WorkerLevel.NOVICE

    def get_level_config(self, level: WorkerLevel) -> LevelConfig:
        """Get configuration for a level."""
        return self.LEVELS[level]

    def calculate_xp_for_level(self, level: WorkerLevel) -> int:
        """Calculate XP needed to reach next level."""
        config = self.LEVELS[level]
        if config.max_tasks == -1:
            return 999999  # Max level

        # XP = tasks * base_xp + bonuses
        next_level_tasks = config.max_tasks + 1
        return next_level_tasks * self.XP_REWARDS["task_complete"]

    def award_xp(
        self,
        worker_id: str,
        amount: int,
        reason: str
    ) -> Tuple[int, Optional[WorkerLevel]]:
        """
        Award XP to worker.

        Returns:
            (new_xp, new_level if leveled up else None)
        """
        progress = self._get_or_create_progress(worker_id)
        old_level = progress.level
        progress.xp += amount

        logger.debug(f"Worker {worker_id} earned {amount} XP for {reason}")

        # Check for level up
        new_level = self.get_level_for_tasks(progress.total_tasks)
        if new_level != old_level:
            progress.level = new_level
            progress.xp_to_next_level = self.calculate_xp_for_level(new_level)
            logger.info(f"Worker {worker_id} leveled up to {new_level.value}!")
            return (progress.xp, new_level)

        return (progress.xp, None)

    def complete_task(
        self,
        worker_id: str,
        task_value: float,
        rating: Optional[float] = None,
        completion_time_minutes: Optional[int] = None,
        photo_quality: Optional[str] = None,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record task completion and award XP/achievements.

        Args:
            worker_id: The worker's ID
            task_value: Payment value in USD
            rating: Optional star rating (1-5)
            completion_time_minutes: Time to complete
            photo_quality: Optional photo quality rating
            country: Country where task was completed

        Returns:
            Dict with XP earned, achievements, etc.
        """
        progress = self._get_or_create_progress(worker_id)
        progress.total_tasks += 1
        progress.total_earnings += task_value
        progress.last_active = datetime.utcnow()

        # Track highest task value
        if task_value > progress.highest_task_value:
            progress.highest_task_value = task_value

        # Track country diversity
        if country and country not in progress.countries:
            progress.countries.append(country)

        # Base XP
        xp_earned = self.XP_REWARDS["task_complete"]
        rewards = ["task_complete"]

        # Quality bonus
        if rating and rating >= 5:
            xp_earned += self.XP_REWARDS["five_star_rating"]
            rewards.append("five_star_rating")
            progress.five_star_tasks += 1

        # Track consecutive approved
        if rating and rating >= 3:
            progress.consecutive_approved += 1
        else:
            progress.consecutive_approved = 0

        # Photo quality tracking
        if photo_quality == "excellent":
            progress.excellent_photos += 1

        # Speed bonus
        if completion_time_minutes and completion_time_minutes < 15:
            xp_earned += self.XP_REWARDS["fast_completion"]
            rewards.append("fast_completion")

        # High value bonus
        if task_value > 5:
            bonus = int((task_value - 5) / 10) * self.XP_REWARDS["high_value_task"]
            xp_earned += bonus
            if bonus > 0:
                rewards.append("high_value_task")

        # Update streak
        self._update_streak(progress)

        # Award XP
        new_xp, new_level = self.award_xp(worker_id, xp_earned, "task_complete")

        # Check achievements
        new_achievements = self._check_achievements(progress)

        return {
            "xp_earned": xp_earned,
            "total_xp": new_xp,
            "rewards": rewards,
            "level": progress.level.value,
            "level_config": {
                "bounty_bonus": self.LEVELS[progress.level].bounty_bonus,
                "badge_color": self.LEVELS[progress.level].badge_color,
            },
            "leveled_up": new_level.value if new_level else None,
            "new_achievements": [
                {
                    "id": a.id,
                    "name": a.name,
                    "description": a.description,
                    "icon": a.icon,
                    "points": a.points,
                    "rarity": a.rarity
                }
                for a in new_achievements
            ],
            "streak": progress.current_streak,
            "total_tasks": progress.total_tasks,
            "total_earnings": progress.total_earnings
        }

    def _update_streak(self, progress: WorkerProgress):
        """Update worker's streak."""
        now = datetime.utcnow()
        last_active_date = progress.last_active.date() if progress.last_active else None
        today = now.date()

        if last_active_date:
            days_diff = (today - last_active_date).days
            if days_diff == 1:
                progress.current_streak += 1
            elif days_diff > 1:
                progress.current_streak = 1
            # Same day: no change
        else:
            progress.current_streak = 1

        progress.longest_streak = max(progress.longest_streak, progress.current_streak)

    def _check_achievements(self, progress: WorkerProgress) -> List[Achievement]:
        """Check and award new achievements."""
        new_achievements = []
        now = datetime.utcnow()

        for achievement in self.ACHIEVEMENTS:
            if achievement.id in progress.achievements:
                continue

            # Check requirements
            met = True
            for req_key, req_value in achievement.requirements.items():
                if req_key == "tasks":
                    if progress.total_tasks < req_value:
                        met = False
                elif req_key == "streak_days":
                    if progress.current_streak < req_value:
                        met = False
                elif req_key == "five_star_tasks":
                    if progress.five_star_tasks < req_value:
                        met = False
                elif req_key == "consecutive_approved":
                    if progress.consecutive_approved < req_value:
                        met = False
                elif req_key == "excellent_photos":
                    if progress.excellent_photos < req_value:
                        met = False
                elif req_key == "referrals":
                    if progress.referrals < req_value:
                        met = False
                elif req_key == "helped_workers":
                    if progress.helped_workers < req_value:
                        met = False
                elif req_key == "task_value":
                    if progress.highest_task_value < req_value:
                        met = False
                elif req_key == "countries":
                    if len(progress.countries) < req_value:
                        met = False
                elif req_key == "tasks_per_hour":
                    if progress.tasks_per_hour_record < req_value:
                        met = False
                elif req_key == "early_morning":
                    # Check if current completion is early morning
                    if now.hour >= 7:
                        met = False
                elif req_key == "late_night":
                    # Check if current completion is late night
                    if now.hour < 0 or now.hour >= 5:
                        met = False
                elif req_key == "launch_month":
                    # Launch month is January 2026
                    if progress.joined_at.year != 2026 or progress.joined_at.month != 1:
                        met = False
                elif req_key == "completion_rate":
                    # Would need separate tracking
                    met = False
                elif req_key == "min_tasks":
                    if progress.total_tasks < req_value:
                        met = False

            if met:
                progress.achievements.append(achievement.id)
                new_achievements.append(achievement)
                logger.info(f"Worker {progress.worker_id} unlocked achievement: {achievement.name}")
                # Award achievement XP
                self.award_xp(
                    progress.worker_id,
                    self.XP_REWARDS["achievement_unlock"],
                    f"achievement_{achievement.id}"
                )

        return new_achievements

    def record_referral(self, worker_id: str) -> Dict[str, Any]:
        """Record a successful referral."""
        progress = self._get_or_create_progress(worker_id)
        progress.referrals += 1

        # Award referral XP
        new_xp, _ = self.award_xp(worker_id, self.XP_REWARDS["referral"], "referral")

        # Check for referral achievements
        new_achievements = self._check_achievements(progress)

        return {
            "referrals": progress.referrals,
            "xp_earned": self.XP_REWARDS["referral"],
            "total_xp": new_xp,
            "new_achievements": [a.id for a in new_achievements]
        }

    def record_help_given(self, worker_id: str) -> None:
        """Record that worker helped another worker."""
        progress = self._get_or_create_progress(worker_id)
        progress.helped_workers += 1
        self._check_achievements(progress)

    def record_tasks_per_hour(self, worker_id: str, count: int) -> None:
        """Record tasks completed in an hour (for speed achievements)."""
        progress = self._get_or_create_progress(worker_id)
        if count > progress.tasks_per_hour_record:
            progress.tasks_per_hour_record = count
            self._check_achievements(progress)

    def get_progress(self, worker_id: str) -> Dict[str, Any]:
        """Get worker's current progress as dict."""
        progress = self._get_or_create_progress(worker_id)
        level_config = self.LEVELS[progress.level]

        # Calculate progress to next level
        if level_config.max_tasks == -1:
            tasks_to_next = 0
            progress_percent = 100
        else:
            tasks_to_next = (level_config.max_tasks + 1) - progress.total_tasks
            tasks_in_level = level_config.max_tasks - level_config.min_tasks + 1
            tasks_done_in_level = progress.total_tasks - level_config.min_tasks
            progress_percent = min(100, int((tasks_done_in_level / tasks_in_level) * 100))

        return {
            "worker_id": progress.worker_id,
            "level": progress.level.value,
            "level_config": {
                "bounty_bonus": level_config.bounty_bonus,
                "priority_boost": level_config.priority_boost,
                "max_concurrent_tasks": level_config.max_concurrent_tasks,
                "verification_tier": level_config.verification_tier,
                "features": level_config.features,
                "badge_color": level_config.badge_color,
            },
            "total_tasks": progress.total_tasks,
            "tasks_to_next_level": tasks_to_next,
            "progress_percent": progress_percent,
            "xp": progress.xp,
            "xp_to_next_level": progress.xp_to_next_level,
            "achievements": progress.achievements,
            "achievement_count": len(progress.achievements),
            "total_achievements": len(self.ACHIEVEMENTS),
            "current_streak": progress.current_streak,
            "longest_streak": progress.longest_streak,
            "total_earnings": progress.total_earnings,
            "joined_at": progress.joined_at.isoformat(),
            "last_active": progress.last_active.isoformat(),
            "stats": {
                "five_star_tasks": progress.five_star_tasks,
                "excellent_photos": progress.excellent_photos,
                "referrals": progress.referrals,
                "countries_worked": len(progress.countries),
                "highest_task_value": progress.highest_task_value
            }
        }

    def get_achievements_list(
        self,
        worker_id: Optional[str] = None,
        category: Optional[AchievementCategory] = None,
        include_secret: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get list of achievements.

        Args:
            worker_id: If provided, include unlocked status
            category: Filter by category
            include_secret: Include secret achievements
        """
        progress = self._get_or_create_progress(worker_id) if worker_id else None
        unlocked_ids = set(progress.achievements) if progress else set()

        result = []
        for achievement in self.ACHIEVEMENTS:
            # Filter by category
            if category and achievement.category != category:
                continue

            # Handle secret achievements
            if achievement.secret and not include_secret:
                if achievement.id not in unlocked_ids:
                    continue

            result.append({
                "id": achievement.id,
                "name": achievement.name,
                "description": achievement.description,
                "category": achievement.category.value,
                "icon": achievement.icon,
                "points": achievement.points,
                "rarity": achievement.rarity,
                "secret": achievement.secret,
                "unlocked": achievement.id in unlocked_ids if worker_id else None
            })

        return result

    def get_leaderboard(
        self,
        limit: int = 10,
        metric: str = "xp"
    ) -> List[Dict[str, Any]]:
        """
        Get top workers by metric.

        Args:
            limit: Number of workers to return
            metric: "xp", "tasks", "earnings", "achievements", "streak"
        """
        if not self._progress:
            return []

        # Sort by metric
        if metric == "xp":
            sorted_workers = sorted(
                self._progress.values(),
                key=lambda p: p.xp,
                reverse=True
            )
        elif metric == "tasks":
            sorted_workers = sorted(
                self._progress.values(),
                key=lambda p: p.total_tasks,
                reverse=True
            )
        elif metric == "earnings":
            sorted_workers = sorted(
                self._progress.values(),
                key=lambda p: p.total_earnings,
                reverse=True
            )
        elif metric == "achievements":
            sorted_workers = sorted(
                self._progress.values(),
                key=lambda p: len(p.achievements),
                reverse=True
            )
        elif metric == "streak":
            sorted_workers = sorted(
                self._progress.values(),
                key=lambda p: p.current_streak,
                reverse=True
            )
        else:
            sorted_workers = sorted(
                self._progress.values(),
                key=lambda p: p.xp,
                reverse=True
            )

        return [
            {
                "rank": i + 1,
                "worker_id": p.worker_id,
                "level": p.level.value,
                "badge_color": self.LEVELS[p.level].badge_color,
                "xp": p.xp,
                "tasks": p.total_tasks,
                "earnings": p.total_earnings,
                "achievements": len(p.achievements),
                "streak": p.current_streak
            }
            for i, p in enumerate(sorted_workers[:limit])
        ]

    def get_level_requirements(self) -> List[Dict[str, Any]]:
        """Get all level requirements and perks."""
        return [
            {
                "level": config.level.value,
                "min_tasks": config.min_tasks,
                "max_tasks": config.max_tasks if config.max_tasks != -1 else None,
                "bounty_bonus": config.bounty_bonus,
                "priority_boost": config.priority_boost,
                "max_concurrent_tasks": config.max_concurrent_tasks,
                "verification_tier": config.verification_tier,
                "features": config.features,
                "badge_color": config.badge_color
            }
            for config in sorted(self.LEVELS.values(), key=lambda x: x.min_tasks)
        ]

    def _get_or_create_progress(self, worker_id: str) -> WorkerProgress:
        """Get or create progress for worker."""
        if worker_id not in self._progress:
            self._progress[worker_id] = WorkerProgress(
                worker_id=worker_id,
                level=WorkerLevel.NOVICE,
                total_tasks=0,
                xp=0,
                xp_to_next_level=self.calculate_xp_for_level(WorkerLevel.NOVICE),
                achievements=[],
                current_streak=0,
                longest_streak=0,
                total_earnings=0.0,
                joined_at=datetime.utcnow(),
                last_active=datetime.utcnow()
            )
        return self._progress[worker_id]

    def import_worker_data(
        self,
        worker_id: str,
        data: Dict[str, Any]
    ) -> WorkerProgress:
        """
        Import existing worker data (e.g., from database).

        Args:
            worker_id: Worker ID
            data: Dict with worker progress data
        """
        total_tasks = data.get("total_tasks", 0)
        level = self.get_level_for_tasks(total_tasks)

        progress = WorkerProgress(
            worker_id=worker_id,
            level=level,
            total_tasks=total_tasks,
            xp=data.get("xp", total_tasks * self.XP_REWARDS["task_complete"]),
            xp_to_next_level=self.calculate_xp_for_level(level),
            achievements=data.get("achievements", []),
            current_streak=data.get("current_streak", 0),
            longest_streak=data.get("longest_streak", 0),
            total_earnings=data.get("total_earnings", 0.0),
            joined_at=datetime.fromisoformat(data["joined_at"]) if "joined_at" in data else datetime.utcnow(),
            last_active=datetime.fromisoformat(data["last_active"]) if "last_active" in data else datetime.utcnow(),
            five_star_tasks=data.get("five_star_tasks", 0),
            consecutive_approved=data.get("consecutive_approved", 0),
            excellent_photos=data.get("excellent_photos", 0),
            referrals=data.get("referrals", 0),
            helped_workers=data.get("helped_workers", 0),
            countries=data.get("countries", []),
            highest_task_value=data.get("highest_task_value", 0.0),
            tasks_per_hour_record=data.get("tasks_per_hour_record", 0)
        )

        self._progress[worker_id] = progress
        return progress

    def export_worker_data(self, worker_id: str) -> Dict[str, Any]:
        """Export worker data for persistence."""
        progress = self._get_or_create_progress(worker_id)
        return {
            "worker_id": progress.worker_id,
            "level": progress.level.value,
            "total_tasks": progress.total_tasks,
            "xp": progress.xp,
            "achievements": progress.achievements,
            "current_streak": progress.current_streak,
            "longest_streak": progress.longest_streak,
            "total_earnings": progress.total_earnings,
            "joined_at": progress.joined_at.isoformat(),
            "last_active": progress.last_active.isoformat(),
            "five_star_tasks": progress.five_star_tasks,
            "consecutive_approved": progress.consecutive_approved,
            "excellent_photos": progress.excellent_photos,
            "referrals": progress.referrals,
            "helped_workers": progress.helped_workers,
            "countries": progress.countries,
            "highest_task_value": progress.highest_task_value,
            "tasks_per_hour_record": progress.tasks_per_hour_record
        }


# Singleton instance
_system: Optional[ProgressionSystem] = None

def get_progression_system() -> ProgressionSystem:
    """Get singleton progression system."""
    global _system
    if _system is None:
        _system = ProgressionSystem()
    return _system
