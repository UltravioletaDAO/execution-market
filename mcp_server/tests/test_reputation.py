"""
Tests for Bayesian reputation module.

Tests the Beta-Binomial reputation system:
- BayesianConfig defaults and custom values
- BayesianCalculator.calculate_score (counts-based API)
- _calculate_weight (log-scale task value weighting)
- calculate_bayesian_score convenience function (dict-based API)
- Edge cases (zero values, negatives, extremes)
"""

import math
from datetime import datetime, UTC

from reputation.bayesian import (
    BayesianCalculator,
    BayesianConfig,
    Rating,
    calculate_bayesian_score,
    create_new_reputation,
)
from reputation.models import ReputationScore


class TestBayesianConfig:
    """Tests for BayesianConfig defaults."""

    def test_default_values(self):
        """Config should have sensible Beta(2,2) prior defaults."""
        config = BayesianConfig()
        assert config.prior_alpha == 2.0
        assert config.prior_beta == 2.0
        assert config.min_score == 0.0
        assert config.max_score == 100.0
        assert config.base_weight == 1.0
        assert config.min_weight == 0.1
        assert config.max_weight == 5.0
        assert config.confidence_level == 0.90

    def test_custom_values(self):
        """Config should accept custom values."""
        config = BayesianConfig(
            prior_alpha=3.0, prior_beta=1.0, min_weight=0.5, max_weight=10.0
        )
        assert config.prior_alpha == 3.0
        assert config.prior_beta == 1.0
        assert config.min_weight == 0.5
        assert config.max_weight == 10.0


class TestBayesianCalculator:
    """Tests for BayesianCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = BayesianCalculator()

    def test_no_tasks_returns_prior(self):
        """No tasks should return the prior mean (50.0 for Beta(2,2))."""
        score = self.calculator.calculate_score(completed=0, failed=0, disputes=0)
        assert score == 50.0  # Beta(2,2) mean = 2/(2+2) = 0.5 * 100

    def test_completions_raise_score(self):
        """Completions should raise score above the prior."""
        score = self.calculator.calculate_score(completed=10, failed=0, disputes=0)
        assert score > 50.0
        assert score <= 100.0

    def test_failures_lower_score(self):
        """Failures should lower score below the prior."""
        score = self.calculator.calculate_score(completed=0, failed=10, disputes=0)
        assert score < 50.0
        assert score >= 0.0

    def test_many_completions_approaches_100(self):
        """Many completions with no failures should approach 100."""
        score = self.calculator.calculate_score(completed=100, failed=0, disputes=0)
        # With Beta(2+100, 2+0), mean = 102/104 * 100 ~ 98.08
        assert score > 95.0

    def test_disputes_count_as_half_failure(self):
        """Disputes should count as 0.5 failure each."""
        # 2 disputes = 1 effective failure
        score_disputes = self.calculator.calculate_score(
            completed=10, failed=0, disputes=2
        )
        score_one_fail = self.calculator.calculate_score(
            completed=10, failed=1, disputes=0
        )
        # 2 disputes = 1.0 failure weight, same as 1 failed
        assert abs(score_disputes - score_one_fail) < 0.01

    def test_value_weighted_completions(self):
        """Higher value tasks should influence score more."""
        # High-value completions (avg $100/task => weight ~2.0)
        score_high = self.calculator.calculate_score(
            completed=5,
            failed=0,
            disputes=0,
            total_value_completed=500.0,  # avg $100
        )
        # Low-value completions (no value data => weight 1.0)
        score_low = self.calculator.calculate_score(
            completed=5,
            failed=0,
            disputes=0,
            total_value_completed=0.0,
        )
        # Higher-value tasks should give a higher score (more alpha weight)
        assert score_high > score_low

    def test_value_weighted_failures(self):
        """Higher value failures should penalize more."""
        # High-value failures
        score_high = self.calculator.calculate_score(
            completed=5,
            failed=3,
            disputes=0,
            total_value_completed=50.0,
            total_value_failed=300.0,  # avg $100 per failure
        )
        # Low-value failures (no value data)
        score_low = self.calculator.calculate_score(
            completed=5,
            failed=3,
            disputes=0,
            total_value_completed=50.0,
            total_value_failed=0.0,
        )
        # Higher-value failures should produce lower score
        assert score_high < score_low

    def test_calculate_weight_log_scale(self):
        """_calculate_weight uses log10 scale: $10=1.0, $100=2.0."""
        weight_10 = self.calculator._calculate_weight(10)
        weight_100 = self.calculator._calculate_weight(100)
        weight_1000 = self.calculator._calculate_weight(1000)

        assert abs(weight_10 - 1.0) < 0.01  # log10(10) = 1.0
        assert abs(weight_100 - 2.0) < 0.01  # log10(100) = 2.0
        assert abs(weight_1000 - 3.0) < 0.01  # log10(1000) = 3.0

    def test_calculate_weight_small_vs_large(self):
        """Small task should have less weight than large task."""
        small_weight = self.calculator._calculate_weight(1)
        large_weight = self.calculator._calculate_weight(100)
        assert small_weight < large_weight

    def test_calculate_weight_clamped(self):
        """Weight should be clamped between min_weight and max_weight."""
        # Very small value
        tiny_weight = self.calculator._calculate_weight(0.01)
        assert tiny_weight >= self.calculator.config.min_weight

        # Very large value
        huge_weight = self.calculator._calculate_weight(1_000_000)
        assert huge_weight <= self.calculator.config.max_weight

    def test_score_clamped_to_range(self):
        """Score should always be between min_score and max_score."""
        # Extreme success
        score_high = self.calculator.calculate_score(
            completed=1000, failed=0, disputes=0
        )
        assert 0 <= score_high <= 100

        # Extreme failure
        score_low = self.calculator.calculate_score(
            completed=0, failed=1000, disputes=0
        )
        assert 0 <= score_low <= 100


class TestCalculateBayesianScore:
    """Tests for convenience function."""

    def test_convenience_function_success(self):
        """Convenience function should score successful tasks above prior."""
        ratings = [
            {"score": 80, "task_value_usdc": 50.0, "outcome": "success"},
        ]
        score = calculate_bayesian_score(ratings)
        assert isinstance(score, float)
        # 1 success + Beta(2,2) prior => mean = 3/5 * 100 = 60
        assert score > 50.0

    def test_convenience_function_mixed(self):
        """Mixed outcomes should balance between success and failure."""
        ratings = [
            {"score": 90, "task_value_usdc": 50.0, "outcome": "success"},
            {"score": 90, "task_value_usdc": 50.0, "outcome": "success"},
            {"score": 10, "task_value_usdc": 50.0, "outcome": "failure"},
        ]
        score = calculate_bayesian_score(ratings)
        assert isinstance(score, float)
        # 2 successes, 1 failure + prior => (2+2)/(2+2+2+1) * 100 ~ 57.1
        assert 50 < score < 70

    def test_with_custom_prior(self):
        """Should accept custom prior_alpha and prior_beta."""
        ratings = [
            {"score": 80, "task_value_usdc": 50.0, "outcome": "success"},
        ]

        # Optimistic prior: Beta(5, 1) => initial mean = 5/6 ~ 83.3
        score_optimistic = calculate_bayesian_score(
            ratings, prior_alpha=5.0, prior_beta=1.0
        )

        # Pessimistic prior: Beta(1, 5) => initial mean = 1/6 ~ 16.7
        score_pessimistic = calculate_bayesian_score(
            ratings, prior_alpha=1.0, prior_beta=5.0
        )

        # Optimistic prior should produce higher score
        assert score_optimistic > score_pessimistic

    def test_empty_ratings(self):
        """Empty ratings should return prior mean."""
        score = calculate_bayesian_score([])
        # Beta(2,2) mean = 0.5 * 100 = 50
        assert score == 50.0

    def test_dispute_loss_outcome(self):
        """Dispute loss should penalize score."""
        ratings_clean = [
            {"score": 80, "task_value_usdc": 50.0, "outcome": "success"},
            {"score": 80, "task_value_usdc": 50.0, "outcome": "success"},
        ]
        ratings_disputed = [
            {"score": 80, "task_value_usdc": 50.0, "outcome": "success"},
            {"score": 80, "task_value_usdc": 50.0, "outcome": "success"},
            {"score": 0, "task_value_usdc": 50.0, "outcome": "dispute_loss"},
        ]
        score_clean = calculate_bayesian_score(ratings_clean)
        score_disputed = calculate_bayesian_score(ratings_disputed)
        assert score_disputed < score_clean


class TestCreateNewReputation:
    """Tests for create_new_reputation helper."""

    def test_creates_neutral_reputation(self):
        """New reputation should start at 50 with Beta(2,2)."""
        rep = create_new_reputation("worker-123")
        assert rep.executor_id == "worker-123"
        assert rep.alpha == 2.0
        assert rep.beta == 2.0
        assert rep.score == 50.0
        assert rep.confidence == 0.0

    def test_is_reputation_score_instance(self):
        """Should return a ReputationScore dataclass."""
        rep = create_new_reputation("worker-456")
        assert isinstance(rep, ReputationScore)


class TestUpdateOnCompletion:
    """Tests for update_on_completion method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = BayesianCalculator()
        self.rep = create_new_reputation("worker-test")

    def test_completion_raises_score(self):
        """A good completion should raise the score."""
        old_score = self.rep.score
        updated_rep, history = self.calculator.update_on_completion(
            self.rep, rating=5, task_value=50.0, task_id="task-1"
        )
        assert updated_rep.score > old_score
        assert history.event_type == "completion"
        assert history.delta > 0

    def test_poor_rating_lowers_score(self):
        """A poor rating (1 star) should lower the score."""
        old_score = self.rep.score
        updated_rep, history = self.calculator.update_on_completion(
            self.rep, rating=1, task_value=50.0, task_id="task-1"
        )
        assert updated_rep.score < old_score
        assert history.delta < 0

    def test_stats_updated(self):
        """Completion should update task stats."""
        self.calculator.update_on_completion(
            self.rep, rating=4, task_value=25.0, task_id="task-1"
        )
        assert self.rep.tasks_completed == 1
        assert self.rep.total_value_completed == 25.0
        assert self.rep.total_ratings == 1

    def test_star_rating_normalization(self):
        """Star ratings (1-5) should be normalized to 0-1."""
        # 5 stars = normalized 1.0 => all weight goes to alpha
        rep5 = create_new_reputation("w5")
        self.calculator.update_on_completion(rep5, rating=5, task_value=10.0)

        # 1 star = normalized 0.0 => all weight goes to beta
        rep1 = create_new_reputation("w1")
        self.calculator.update_on_completion(rep1, rating=1, task_value=10.0)

        assert rep5.score > rep1.score


class TestUpdateOnFailure:
    """Tests for update_on_failure method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = BayesianCalculator()
        self.rep = create_new_reputation("worker-test")

    def test_failure_lowers_score(self):
        """A failure should lower the score."""
        old_score = self.rep.score
        updated_rep, history = self.calculator.update_on_failure(
            self.rep, reason="Abandoned task", task_value=50.0, task_id="task-1"
        )
        assert updated_rep.score < old_score
        assert history.delta < 0

    def test_abandonment_harsher(self):
        """Abandonment should penalize more than regular failure."""
        rep_abandon = create_new_reputation("w-abandon")
        rep_fail = create_new_reputation("w-fail")

        self.calculator.update_on_failure(
            rep_abandon,
            reason="Abandoned",
            task_value=50.0,
            is_abandonment=True,
        )
        self.calculator.update_on_failure(
            rep_fail, reason="Failed", task_value=50.0, is_abandonment=False
        )

        # Abandonment has 1.5x penalty
        assert rep_abandon.score < rep_fail.score

    def test_failure_stats_updated(self):
        """Failure should update the right stats."""
        self.calculator.update_on_failure(
            self.rep, reason="test", task_value=10.0, is_abandonment=True
        )
        assert self.rep.tasks_abandoned == 1
        assert self.rep.total_value_failed == 10.0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_task_value_weight(self):
        """Zero task value should return minimum weight."""
        calculator = BayesianCalculator()
        weight = calculator._calculate_weight(0)
        assert weight == calculator.config.min_weight

    def test_negative_task_value_weight(self):
        """Negative task value should return minimum weight."""
        calculator = BayesianCalculator()
        weight = calculator._calculate_weight(-10)
        assert weight == calculator.config.min_weight

    def test_extreme_completions(self):
        """Extreme number of completions should still produce valid score."""
        calculator = BayesianCalculator()
        score = calculator.calculate_score(completed=10000, failed=0, disputes=0)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_extreme_failures(self):
        """Extreme number of failures should still produce valid score."""
        calculator = BayesianCalculator()
        score = calculator.calculate_score(completed=0, failed=10000, disputes=0)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_rating_dataclass(self):
        """Rating dataclass should accept all fields."""
        now = datetime.now(UTC)
        rating = Rating(
            score=80,
            task_value_usdc=50.0,
            created_at=now,
            task_id="t1",
            task_type="physical_presence",
            rater_id="agent-1",
        )
        assert rating.score == 80
        assert rating.task_value_usdc == 50.0
        assert rating.task_id == "t1"
        assert rating.task_type == "physical_presence"
