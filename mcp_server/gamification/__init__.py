"""
Gamification module for Execution Market.

Provides progression system, achievements, and streak tracking.
"""

from .progression import (
    WorkerLevel,
    AchievementCategory,
    LevelConfig,
    Achievement,
    WorkerProgress,
    ProgressionSystem,
    get_progression_system,
)
from .streaks import (
    StreakBonus,
    StreakTracker,
    get_streak_tracker,
)

__all__ = [
    # Progression
    "WorkerLevel",
    "AchievementCategory",
    "LevelConfig",
    "Achievement",
    "WorkerProgress",
    "ProgressionSystem",
    "get_progression_system",
    # Streaks
    "StreakBonus",
    "StreakTracker",
    "get_streak_tracker",
]
