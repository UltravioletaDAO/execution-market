"""
Chamba Reputation System

A comprehensive Bayesian reputation system for the Chamba human execution layer.

Components:
- bayesian.py: Core Bayesian calculator using Beta-Binomial model
- decay.py: Time-based decay for inactive users
- badges.py: Achievement badge system
- leaderboard.py: Rankings and leaderboards
- models.py: Data models and types

Quick Start:
    >>> from chamba.mcp_server.reputation import (
    ...     BayesianCalculator,
    ...     create_new_reputation,
    ...     DecayManager,
    ...     BadgeManager,
    ...     get_top_workers,
    ... )
    >>>
    >>> # Create reputation for new worker
    >>> rep = create_new_reputation("worker_123")
    >>> print(f"Initial score: {rep.score}")
    Initial score: 50.0
    >>>
    >>> # Update on task completion
    >>> calc = BayesianCalculator()
    >>> rep, history = calc.update_on_completion(rep, rating=5, task_value=25.0)
    >>> print(f"New score: {rep.score:.1f}")
    New score: 58.3
    >>>
    >>> # Get confidence interval
    >>> ci = calc.get_confidence_interval(rep)
    >>> print(f"90% CI: [{ci.lower:.1f}, {ci.upper:.1f}]")
    90% CI: [35.2, 78.4]
"""

# Models
from .models import (
    Badge,
    BadgeDefinition,
    EarnedBadge,
    ReputationScore,
    ReputationHistory,
    ConfidenceInterval,
)

# Bayesian calculator
from .bayesian import (
    BayesianCalculator,
    BayesianConfig,
    Rating,
    calculate_bayesian_score,
    create_new_reputation,
)

# Decay system
from .decay import (
    DecayManager,
    DecayConfig,
    apply_batch_decay,
    get_decay_schedule,
)

# Badge system
from .badges import (
    BadgeManager,
    BadgeContext,
    check_and_award_badges,
)

# Leaderboard
from .leaderboard import (
    LeaderboardManager,
    LeaderboardEntry,
    LeaderboardResult,
    LeaderboardPeriod,
    get_top_workers,
    get_rising_stars,
    get_specialists,
    calculate_percentile,
)

__all__ = [
    # Models
    "Badge",
    "BadgeDefinition",
    "EarnedBadge",
    "ReputationScore",
    "ReputationHistory",
    "ConfidenceInterval",

    # Bayesian
    "BayesianCalculator",
    "BayesianConfig",
    "Rating",
    "calculate_bayesian_score",
    "create_new_reputation",

    # Decay
    "DecayManager",
    "DecayConfig",
    "apply_batch_decay",
    "get_decay_schedule",

    # Badges
    "BadgeManager",
    "BadgeContext",
    "check_and_award_badges",

    # Leaderboard
    "LeaderboardManager",
    "LeaderboardEntry",
    "LeaderboardResult",
    "LeaderboardPeriod",
    "get_top_workers",
    "get_rising_stars",
    "get_specialists",
    "calculate_percentile",
]
