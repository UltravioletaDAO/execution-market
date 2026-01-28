"""
Reputation Decay System for Chamba

Applies time-based decay to reputation scores for inactive users.

Why decay?
1. Recency matters - a worker active 2 years ago may have different skills now
2. Prevents "reputation hoarding" - must stay active to maintain score
3. Creates economic incentive for regular participation
4. Reflects real-world skill degradation (use it or lose it)

How it works:
- Half-life model: score decays toward neutral (50) over time
- Only affects inactive users (no activity in N days)
- Minimum score floor prevents reputation death
- Decay is reversible with new activity

Formula:
    decayed_score = neutral + (current - neutral) * decay_factor
    decay_factor = 0.5 ^ (days_inactive / half_life)

Example with 30-day half-life:
    - 30 days inactive: 80 -> 65 (halfway to 50)
    - 60 days inactive: 80 -> 57.5
    - 90 days inactive: 80 -> 53.75
"""

import math
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

from .models import ReputationScore, ReputationHistory


@dataclass
class DecayConfig:
    """Configuration for reputation decay."""
    # Half-life in days (time for score to decay halfway to neutral)
    half_life_days: float = 30.0

    # Neutral point (scores decay toward this)
    neutral_score: float = 50.0

    # Minimum days before decay starts
    grace_period_days: int = 14

    # Minimum score floor (never decay below this)
    min_score_floor: float = 10.0

    # Maximum decay per application (prevent sudden drops)
    max_decay_per_application: float = 10.0


class DecayManager:
    """
    Manages reputation decay for inactive workers.

    The decay system uses a half-life model where scores
    exponentially approach the neutral point over time.

    Example:
        >>> manager = DecayManager()
        >>> rep = ReputationScore(executor_id="worker1", score=80)
        >>> rep.last_activity_at = datetime.now(UTC) - timedelta(days=45)
        >>> new_rep, history = manager.apply_decay(rep)
        >>> print(f"Score: {rep.score:.1f} -> {new_rep.score:.1f}")
        Score: 80.0 -> 58.8
    """

    def __init__(self, config: Optional[DecayConfig] = None):
        self.config = config or DecayConfig()

    def calculate_decay_factor(self, days_inactive: float) -> float:
        """
        Calculate the decay factor based on inactivity period.

        Uses exponential decay with half-life formula:
            factor = 0.5 ^ (days / half_life)

        Args:
            days_inactive: Number of days since last activity

        Returns:
            Decay factor between 0 and 1
        """
        if days_inactive <= self.config.grace_period_days:
            return 1.0  # No decay during grace period

        # Days past grace period
        effective_days = days_inactive - self.config.grace_period_days

        # Half-life formula
        decay_factor = math.pow(0.5, effective_days / self.config.half_life_days)

        return decay_factor

    def calculate_decayed_score(
        self,
        current_score: float,
        days_inactive: float,
    ) -> float:
        """
        Calculate what score would be after decay.

        Score decays toward neutral point, never below floor.

        Args:
            current_score: Current reputation score
            days_inactive: Days since last activity

        Returns:
            Decayed score
        """
        decay_factor = self.calculate_decay_factor(days_inactive)

        # Decay toward neutral
        neutral = self.config.neutral_score
        distance_from_neutral = current_score - neutral
        decayed_distance = distance_from_neutral * decay_factor

        decayed_score = neutral + decayed_distance

        # Apply floor
        return max(self.config.min_score_floor, decayed_score)

    def should_apply_decay(self, rep: ReputationScore) -> bool:
        """
        Check if decay should be applied to this reputation.

        Decay applies if:
        1. There's been activity (last_activity_at is set)
        2. More than grace_period_days since last activity
        3. Score is above neutral (no point decaying low scores further)

        Args:
            rep: Reputation score to check

        Returns:
            True if decay should be applied
        """
        if not rep.last_activity_at:
            return False

        days_inactive = (datetime.now(UTC) - rep.last_activity_at).days

        # Check grace period
        if days_inactive <= self.config.grace_period_days:
            return False

        # Only decay scores above neutral
        if rep.score <= self.config.neutral_score:
            return False

        # Check if already decayed recently
        if rep.last_decay_at:
            days_since_decay = (datetime.now(UTC) - rep.last_decay_at).days
            if days_since_decay < 1:  # Don't decay more than once per day
                return False

        return True

    def apply_decay(
        self,
        rep: ReputationScore,
        force: bool = False,
    ) -> Tuple[ReputationScore, Optional[ReputationHistory]]:
        """
        Apply decay to a reputation score.

        Args:
            rep: Reputation score to decay
            force: Force decay even if not normally applicable

        Returns:
            Tuple of (updated ReputationScore, optional history record)
        """
        if not force and not self.should_apply_decay(rep):
            return rep, None

        old_score = rep.score

        # Calculate days inactive
        if rep.last_activity_at:
            days_inactive = (datetime.now(UTC) - rep.last_activity_at).days
        else:
            days_inactive = 0

        # Calculate new score
        new_score = self.calculate_decayed_score(old_score, days_inactive)

        # Apply max decay limit
        max_decay = self.config.max_decay_per_application
        if (old_score - new_score) > max_decay:
            new_score = old_score - max_decay

        # Apply floor
        new_score = max(self.config.min_score_floor, new_score)

        # Update reputation
        rep.score = new_score
        rep.last_decay_at = datetime.now(UTC)
        rep.updated_at = datetime.now(UTC)

        # Also decay alpha/beta to match (adjust Beta distribution)
        # We maintain the same alpha/beta ratio but scale down the magnitude
        if old_score > 0:
            scale_factor = new_score / old_score
            # Don't scale below the prior
            min_alpha = 2.0
            min_beta = 2.0
            rep.alpha = max(min_alpha, rep.alpha * scale_factor)
            rep.beta = max(min_beta, rep.beta * scale_factor)

        # Create history record
        delta = new_score - old_score
        history = ReputationHistory(
            id=f"decay_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            executor_id=rep.executor_id,
            event_type="decay",
            old_score=old_score,
            new_score=new_score,
            delta=delta,
            reason=f"Inactivity decay ({days_inactive} days inactive)",
        )

        return rep, history

    def preview_decay(
        self,
        rep: ReputationScore,
        future_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Preview what decay will look like over time.

        Useful for showing workers their projected score trajectory.

        Args:
            rep: Current reputation
            future_days: How many days to project

        Returns:
            List of {day, score, decay_factor} dicts
        """
        current_inactive_days = 0
        if rep.last_activity_at:
            current_inactive_days = (datetime.now(UTC) - rep.last_activity_at).days

        projections = []
        for day in range(0, future_days + 1, 7):  # Weekly snapshots
            total_inactive = current_inactive_days + day
            projected_score = self.calculate_decayed_score(rep.score, total_inactive)
            decay_factor = self.calculate_decay_factor(total_inactive)

            projections.append({
                "day": day,
                "total_inactive_days": total_inactive,
                "projected_score": round(projected_score, 2),
                "decay_factor": round(decay_factor, 4),
            })

        return projections

    def estimate_recovery_time(
        self,
        current_score: float,
        target_score: float,
        avg_task_value: float = 10.0,
        avg_rating: int = 4,
    ) -> Dict[str, Any]:
        """
        Estimate how many tasks needed to recover from decay.

        Helps workers understand the effort to rebuild reputation.

        Args:
            current_score: Current decayed score
            target_score: Target score to reach
            avg_task_value: Average task value expected
            avg_rating: Expected average rating (1-5)

        Returns:
            Dict with estimated tasks and time
        """
        from .bayesian import BayesianCalculator, create_new_reputation

        if current_score >= target_score:
            return {
                "tasks_needed": 0,
                "estimated_days": 0,
                "current_score": current_score,
                "target_score": target_score,
                "message": "Already at or above target score",
            }

        calc = BayesianCalculator()

        # Simulate building up
        sim_rep = create_new_reputation("simulation")
        # Adjust starting point to match current score
        # Rough approximation: set alpha/beta to give current score
        if current_score > 50:
            ratio = current_score / 100
            sim_rep.alpha = ratio * 4 + 2
            sim_rep.beta = (1 - ratio) * 4 + 2
        else:
            ratio = current_score / 100
            sim_rep.alpha = ratio * 4 + 2
            sim_rep.beta = (1 - ratio) * 4 + 2

        tasks_count = 0
        while sim_rep.score < target_score and tasks_count < 1000:
            sim_rep, _ = calc.update_on_completion(
                sim_rep, avg_rating, avg_task_value
            )
            tasks_count += 1

        # Estimate time (assume 1 task per day average)
        estimated_days = tasks_count

        return {
            "tasks_needed": tasks_count,
            "estimated_days": estimated_days,
            "current_score": round(current_score, 2),
            "target_score": target_score,
            "assumptions": {
                "avg_task_value": avg_task_value,
                "avg_rating": avg_rating,
                "tasks_per_day": 1,
            },
        }


def apply_batch_decay(
    reputations: List[ReputationScore],
    config: Optional[DecayConfig] = None,
) -> Tuple[List[ReputationScore], List[ReputationHistory]]:
    """
    Apply decay to multiple reputations at once.

    Useful for batch processing inactive users.

    Args:
        reputations: List of reputation scores
        config: Optional decay configuration

    Returns:
        Tuple of (updated reputations, history records)
    """
    manager = DecayManager(config)

    updated_reps = []
    histories = []

    for rep in reputations:
        if manager.should_apply_decay(rep):
            updated_rep, history = manager.apply_decay(rep)
            updated_reps.append(updated_rep)
            if history:
                histories.append(history)
        else:
            updated_reps.append(rep)

    return updated_reps, histories


def get_decay_schedule(
    half_life_days: float = 30.0,
    max_days: int = 180,
) -> List[Dict[str, Any]]:
    """
    Get a decay schedule showing factor at each interval.

    Useful for documentation and UI display.

    Args:
        half_life_days: Half-life configuration
        max_days: Maximum days to show

    Returns:
        List of {day, factor, percentage_retained} dicts
    """
    config = DecayConfig(half_life_days=half_life_days)
    manager = DecayManager(config)

    schedule = []
    for day in range(0, max_days + 1, 7):
        factor = manager.calculate_decay_factor(day)
        schedule.append({
            "day": day,
            "factor": round(factor, 4),
            "percentage_retained": round(factor * 100, 1),
            "example_80_score": round(50 + 30 * factor, 1),  # 80 -> neutral
            "example_90_score": round(50 + 40 * factor, 1),  # 90 -> neutral
        })

    return schedule
