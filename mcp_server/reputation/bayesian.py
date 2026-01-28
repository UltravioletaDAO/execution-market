"""
Bayesian Reputation Calculator for Chamba

Implements a Beta-Binomial reputation system that:
1. Uses Beta(2, 2) prior for new users (neutral starting point)
2. Updates based on task completions/failures weighted by value
3. Provides confidence intervals for uncertainty quantification
4. Normalizes to 0-100 scale for display

The Beta distribution is perfect for reputation because:
- It's the conjugate prior for binomial data (success/failure)
- It naturally handles uncertainty (wide with few data, narrow with many)
- Easy to update: just add to alpha (successes) and beta (failures)
- Provides interpretable confidence intervals

Formula:
    Mean score = alpha / (alpha + beta)
    Normalized = mean * 100 (for 0-100 scale)

Weighting by task value:
    - $1 task = 0.1 weight
    - $10 task = 1.0 weight
    - $100 task = 2.0 weight (log scale)
"""

import math
from datetime import datetime, UTC
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .models import ReputationScore, ConfidenceInterval, ReputationHistory


@dataclass
class Rating:
    """Individual rating record."""
    score: int  # 1-100 or 1-5 stars (will be normalized)
    task_value_usdc: float
    created_at: datetime
    task_type: Optional[str] = None
    rater_id: Optional[str] = None
    task_id: Optional[str] = None


@dataclass
class BayesianConfig:
    """Configuration for Bayesian calculation."""
    # Beta prior parameters (Beta(2,2) = neutral, mildly informative)
    prior_alpha: float = 2.0  # Prior successes
    prior_beta: float = 2.0   # Prior failures

    # Score normalization
    min_score: float = 0.0
    max_score: float = 100.0

    # Value weighting
    base_weight: float = 1.0      # Weight for a $10 task
    min_weight: float = 0.1       # Minimum weight for very small tasks
    max_weight: float = 5.0       # Maximum weight cap

    # Confidence interval
    confidence_level: float = 0.90  # 90% CI by default


class BayesianCalculator:
    """
    Bayesian reputation calculator using Beta-Binomial model.

    The Beta distribution tracks our belief about a worker's "true" success rate.
    Each task outcome updates this belief:
    - Success: alpha += weight
    - Failure: beta += weight

    Example:
        >>> calc = BayesianCalculator()
        >>> score = calc.calculate_score(completed=10, failed=2, disputes=1)
        >>> print(f"Reputation: {score:.1f}")
        Reputation: 73.5
    """

    def __init__(self, config: Optional[BayesianConfig] = None):
        self.config = config or BayesianConfig()

    def calculate_score(
        self,
        completed: int,
        failed: int,
        disputes: int,
        total_value_completed: float = 0.0,
        total_value_failed: float = 0.0,
    ) -> float:
        """
        Calculate reputation score from task counts.

        Simple version that uses counts rather than individual ratings.
        Disputes count as 0.5 failure (partial penalty).

        Args:
            completed: Number of successfully completed tasks
            failed: Number of failed/abandoned tasks
            disputes: Number of disputes (lost by worker)
            total_value_completed: Sum of bounty values for completed tasks
            total_value_failed: Sum of bounty values for failed tasks

        Returns:
            Score between 0 and 100
        """
        # Calculate alpha (successes)
        if total_value_completed > 0 and completed > 0:
            # Use value-weighted if we have value data
            avg_value = total_value_completed / completed
            alpha_weight = self._calculate_weight(avg_value)
            alpha = self.config.prior_alpha + (completed * alpha_weight)
        else:
            alpha = self.config.prior_alpha + completed

        # Calculate beta (failures)
        failure_count = failed + (disputes * 0.5)  # Disputes = half failure
        if total_value_failed > 0 and (failed + disputes) > 0:
            avg_value = total_value_failed / (failed + disputes)
            beta_weight = self._calculate_weight(avg_value)
            beta = self.config.prior_beta + (failure_count * beta_weight)
        else:
            beta = self.config.prior_beta + failure_count

        # Calculate mean of Beta distribution
        mean = alpha / (alpha + beta)

        # Normalize to 0-100 scale
        score = mean * self.config.max_score

        return max(self.config.min_score, min(self.config.max_score, score))

    def calculate_from_reputation_score(self, rep: ReputationScore) -> float:
        """
        Calculate score directly from a ReputationScore object.

        Uses the stored alpha/beta parameters.

        Args:
            rep: ReputationScore object

        Returns:
            Score between 0 and 100
        """
        mean = rep.alpha / (rep.alpha + rep.beta)
        return mean * self.config.max_score

    def update_on_completion(
        self,
        rep: ReputationScore,
        rating: int,
        task_value: float,
        task_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Tuple[ReputationScore, ReputationHistory]:
        """
        Update reputation after a successful task completion.

        Args:
            rep: Current reputation score
            rating: Rating given (1-5 stars or 1-100)
            task_value: Task bounty value in USD
            task_id: Optional task ID for history
            task_type: Optional task category

        Returns:
            Tuple of (updated ReputationScore, ReputationHistory record)
        """
        old_score = self.calculate_from_reputation_score(rep)

        # Normalize rating to 0-1 scale
        if rating <= 5:
            # Star rating (1-5)
            normalized_rating = (rating - 1) / 4  # 1->0, 5->1
        else:
            # Score rating (1-100)
            normalized_rating = rating / 100

        # Calculate weight based on task value
        weight = self._calculate_weight(task_value)

        # Update alpha/beta based on rating
        # Good rating adds more to alpha, poor rating adds more to beta
        rep.alpha += weight * normalized_rating
        rep.beta += weight * (1 - normalized_rating)

        # Update stats
        rep.tasks_completed += 1
        rep.total_value_completed += task_value
        rep.total_ratings += 1
        rep.sum_ratings += rating
        rep.avg_rating = rep.sum_ratings / rep.total_ratings

        # Update timestamps
        rep.updated_at = datetime.now(UTC)
        rep.last_activity_at = datetime.now(UTC)

        # Calculate new score
        new_score = self.calculate_from_reputation_score(rep)
        rep.score = new_score
        rep.confidence = self._calculate_confidence(rep)

        # Update category score if applicable
        if task_type:
            self._update_category_score(rep, task_type, normalized_rating, weight)

        # Create history record
        history = ReputationHistory(
            id=f"hist_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            executor_id=rep.executor_id,
            event_type="completion",
            old_score=old_score,
            new_score=new_score,
            delta=new_score - old_score,
            task_id=task_id,
            task_value=task_value,
            rating=rating,
            reason=f"Task completed with {rating} rating",
        )

        return rep, history

    def update_on_failure(
        self,
        rep: ReputationScore,
        reason: str,
        task_value: float = 0.0,
        task_id: Optional[str] = None,
        is_abandonment: bool = False,
        is_dispute_loss: bool = False,
    ) -> Tuple[ReputationScore, ReputationHistory]:
        """
        Update reputation after a task failure.

        Args:
            rep: Current reputation score
            reason: Reason for failure
            task_value: Task bounty value in USD
            task_id: Optional task ID
            is_abandonment: True if worker abandoned (harsher penalty)
            is_dispute_loss: True if worker lost a dispute

        Returns:
            Tuple of (updated ReputationScore, ReputationHistory record)
        """
        old_score = self.calculate_from_reputation_score(rep)

        # Calculate weight based on task value
        weight = self._calculate_weight(task_value)

        # Apply penalty multiplier based on type
        if is_abandonment:
            # Abandonment is serious - 1.5x penalty
            weight *= 1.5
            rep.tasks_abandoned += 1
            event_type = "abandonment"
        elif is_dispute_loss:
            # Dispute loss - standard penalty
            rep.tasks_disputed += 1
            event_type = "dispute_loss"
        else:
            # Regular failure
            rep.tasks_failed += 1
            event_type = "failure"

        # Update beta (failures)
        rep.beta += weight
        rep.total_value_failed += task_value

        # Update timestamps
        rep.updated_at = datetime.now(UTC)
        rep.last_activity_at = datetime.now(UTC)

        # Calculate new score
        new_score = self.calculate_from_reputation_score(rep)
        rep.score = new_score
        rep.confidence = self._calculate_confidence(rep)

        # Create history record
        history = ReputationHistory(
            id=f"hist_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            executor_id=rep.executor_id,
            event_type=event_type,
            old_score=old_score,
            new_score=new_score,
            delta=new_score - old_score,
            task_id=task_id,
            task_value=task_value,
            reason=reason,
        )

        return rep, history

    def get_confidence_interval(
        self,
        rep: ReputationScore,
        confidence_level: Optional[float] = None,
    ) -> ConfidenceInterval:
        """
        Calculate confidence interval for the reputation score.

        Uses the Beta distribution quantile function to find the
        interval that contains the true score with given probability.

        Args:
            rep: Reputation score object
            confidence_level: Confidence level (default 0.90 for 90% CI)

        Returns:
            ConfidenceInterval with lower, upper, mean, mode
        """
        try:
            from scipy import stats
        except ImportError:
            # Fallback without scipy - use normal approximation
            return self._confidence_interval_approximation(rep, confidence_level)

        level = confidence_level or self.config.confidence_level
        tail = (1 - level) / 2

        # Create Beta distribution with current parameters
        beta_dist = stats.beta(rep.alpha, rep.beta)

        # Calculate quantiles
        lower = beta_dist.ppf(tail) * 100
        upper = beta_dist.ppf(1 - tail) * 100
        mean = beta_dist.mean() * 100

        # Mode (most likely value)
        if rep.alpha > 1 and rep.beta > 1:
            mode = ((rep.alpha - 1) / (rep.alpha + rep.beta - 2)) * 100
        else:
            mode = mean  # Use mean if mode is at boundary

        return ConfidenceInterval(
            lower=max(0, lower),
            upper=min(100, upper),
            mean=mean,
            mode=mode,
            confidence_level=level,
        )

    def _confidence_interval_approximation(
        self,
        rep: ReputationScore,
        confidence_level: Optional[float] = None,
    ) -> ConfidenceInterval:
        """
        Approximate confidence interval without scipy.

        Uses normal approximation to Beta distribution.
        """
        level = confidence_level or self.config.confidence_level
        z = 1.645 if level == 0.90 else 1.96  # 90% or 95%

        mean = rep.alpha / (rep.alpha + rep.beta)
        variance = (rep.alpha * rep.beta) / (
            (rep.alpha + rep.beta) ** 2 * (rep.alpha + rep.beta + 1)
        )
        std = math.sqrt(variance)

        lower = (mean - z * std) * 100
        upper = (mean + z * std) * 100

        # Mode
        if rep.alpha > 1 and rep.beta > 1:
            mode = ((rep.alpha - 1) / (rep.alpha + rep.beta - 2)) * 100
        else:
            mode = mean * 100

        return ConfidenceInterval(
            lower=max(0, lower),
            upper=min(100, upper),
            mean=mean * 100,
            mode=mode,
            confidence_level=level,
        )

    def _calculate_weight(self, task_value: float) -> float:
        """
        Calculate weight for a task based on its value.

        Uses log scale to prevent very high-value tasks from dominating.

        $1 task = 0.1 weight
        $10 task = 1.0 weight
        $100 task = 2.0 weight
        $1000 task = 3.0 weight

        Args:
            task_value: Task bounty in USD

        Returns:
            Weight value between min_weight and max_weight
        """
        if task_value <= 0:
            return self.config.min_weight

        # Log scale: log10(value) / log10(10) = log10(value)
        # $10 = 1.0, $100 = 2.0, etc.
        weight = math.log10(max(1, task_value))

        # Clamp to configured range
        return max(self.config.min_weight, min(self.config.max_weight, weight))

    def _calculate_confidence(self, rep: ReputationScore) -> float:
        """
        Calculate how confident we are in the score.

        Based on total observations (alpha + beta - prior).
        More observations = higher confidence.

        Returns:
            Confidence percentage (0-100)
        """
        total_observations = rep.alpha + rep.beta - (
            self.config.prior_alpha + self.config.prior_beta
        )

        # Confidence grows logarithmically
        # 10 tasks = ~50% confident
        # 100 tasks = ~80% confident
        # 1000 tasks = ~95% confident
        if total_observations <= 0:
            return 0.0

        confidence = (math.log10(total_observations + 1) / math.log10(1000)) * 100
        return min(100.0, confidence)

    def _update_category_score(
        self,
        rep: ReputationScore,
        category: str,
        normalized_rating: float,
        weight: float,
    ) -> None:
        """Update category-specific score."""
        # Simple weighted average for categories
        if category not in rep.category_scores:
            rep.category_scores[category] = {
                "score": 50.0,
                "weight_sum": 0.0,
                "count": 0,
            }

        cat = rep.category_scores[category]
        old_weight = cat["weight_sum"]
        new_weight = old_weight + weight

        # Weighted average update
        cat["score"] = (
            (cat["score"] * old_weight + normalized_rating * 100 * weight) / new_weight
        )
        cat["weight_sum"] = new_weight
        cat["count"] = cat.get("count", 0) + 1

    def simulate_impact(
        self,
        rep: ReputationScore,
        task_value: float,
        rating: int,
    ) -> Dict[str, Any]:
        """
        Simulate what a new rating would do to the score.

        Useful for workers to understand their trajectory.

        Args:
            rep: Current reputation
            task_value: Hypothetical task value
            rating: Hypothetical rating (1-5 or 1-100)

        Returns:
            Dict with current, projected scores and delta
        """
        # Create a copy to simulate
        sim_rep = ReputationScore(
            executor_id=rep.executor_id,
            alpha=rep.alpha,
            beta=rep.beta,
            tasks_completed=rep.tasks_completed,
            tasks_failed=rep.tasks_failed,
        )

        current_score = self.calculate_from_reputation_score(rep)

        # Simulate completion
        sim_rep, _ = self.update_on_completion(
            sim_rep, rating, task_value, None, None
        )

        projected_score = sim_rep.score
        new_ci = self.get_confidence_interval(sim_rep)

        return {
            "current_score": round(current_score, 2),
            "projected_score": round(projected_score, 2),
            "delta": round(projected_score - current_score, 2),
            "projected_confidence_interval": new_ci.to_dict(),
            "weight_applied": round(self._calculate_weight(task_value), 3),
        }


# Convenience functions for simple use cases

def calculate_bayesian_score(
    ratings: List[Dict[str, Any]],
    prior_alpha: float = 2.0,
    prior_beta: float = 2.0,
) -> float:
    """
    Convenience function to calculate Bayesian score from rating dicts.

    Args:
        ratings: List of dicts with 'score', 'task_value_usdc', 'created_at'
        prior_alpha: Prior successes (default 2)
        prior_beta: Prior failures (default 2)

    Returns:
        Score (0-100)

    Example:
        >>> ratings = [
        ...     {"score": 90, "task_value_usdc": 50.0, "outcome": "success"},
        ...     {"score": 80, "task_value_usdc": 10.0, "outcome": "success"},
        ... ]
        >>> score = calculate_bayesian_score(ratings)
    """
    config = BayesianConfig(prior_alpha=prior_alpha, prior_beta=prior_beta)
    calc = BayesianCalculator(config)

    # Count outcomes
    completed = sum(1 for r in ratings if r.get("outcome") == "success")
    failed = sum(1 for r in ratings if r.get("outcome") == "failure")
    disputes = sum(1 for r in ratings if r.get("outcome") == "dispute_loss")

    total_value_completed = sum(
        r.get("task_value_usdc", 0) for r in ratings if r.get("outcome") == "success"
    )
    total_value_failed = sum(
        r.get("task_value_usdc", 0) for r in ratings if r.get("outcome") in ("failure", "dispute_loss")
    )

    return calc.calculate_score(
        completed=completed,
        failed=failed,
        disputes=disputes,
        total_value_completed=total_value_completed,
        total_value_failed=total_value_failed,
    )


def create_new_reputation(executor_id: str) -> ReputationScore:
    """
    Create a new reputation score for a worker.

    Starts with Beta(2, 2) prior which gives:
    - Initial score: 50 (neutral)
    - High uncertainty (wide confidence interval)

    Args:
        executor_id: The worker's ID

    Returns:
        New ReputationScore
    """
    return ReputationScore(
        executor_id=executor_id,
        alpha=2.0,
        beta=2.0,
        score=50.0,
        confidence=0.0,
    )
