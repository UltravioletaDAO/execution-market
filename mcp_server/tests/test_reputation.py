"""
Tests for Bayesian reputation module.
"""

from datetime import datetime, timedelta, UTC
from reputation.bayesian import (
    BayesianCalculator,
    BayesianConfig,
    Rating,
    calculate_bayesian_score,
)


class TestBayesianConfig:
    """Tests for BayesianConfig defaults."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        config = BayesianConfig()
        assert config.C == 15.0
        assert config.m == 50.0
        assert config.decay_rate == 0.9

    def test_custom_values(self):
        """Config should accept custom values."""
        config = BayesianConfig(C=20, m=60, decay_rate=0.85)
        assert config.C == 20
        assert config.m == 60
        assert config.decay_rate == 0.85


class TestBayesianCalculator:
    """Tests for BayesianCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = BayesianCalculator()
        self.now = datetime.now(UTC)

    def test_no_ratings_returns_prior(self):
        """No ratings should return the prior mean."""
        score = self.calculator.calculate_score([])
        assert score == self.calculator.config.m

    def test_single_high_rating(self):
        """Single high rating should pull score above prior."""
        ratings = [
            Rating(
                score=100, task_value_usdc=50.0, created_at=self.now, task_id="task-1"
            )
        ]
        score = self.calculator.calculate_score(ratings)
        # Should be above prior (50) but not 100 due to confidence
        assert 50 < score < 100

    def test_single_low_rating(self):
        """Single low rating should pull score below prior."""
        ratings = [
            Rating(score=0, task_value_usdc=50.0, created_at=self.now, task_id="task-1")
        ]
        score = self.calculator.calculate_score(ratings)
        # Should be below prior (50) but not 0 due to confidence
        assert 0 < score < 50

    def test_many_ratings_approaches_average(self):
        """Many ratings should approach the average rating."""
        # 20 ratings of 80
        ratings = [
            Rating(
                score=80, task_value_usdc=50.0, created_at=self.now, task_id=f"task-{i}"
            )
            for i in range(20)
        ]
        score = self.calculator.calculate_score(ratings)
        # With many ratings, should be close to 80
        assert 75 < score < 85

    def test_weight_by_task_value(self):
        """Higher value tasks should have more weight."""
        # One low-value low rating
        low_value_ratings = [
            Rating(score=20, task_value_usdc=5.0, created_at=self.now, task_id="t1")
        ]
        # One high-value high rating
        high_value_ratings = [
            Rating(score=80, task_value_usdc=500.0, created_at=self.now, task_id="t2")
        ]

        low_only = self.calculator.calculate_score(low_value_ratings)
        high_only = self.calculator.calculate_score(high_value_ratings)
        both = self.calculator.calculate_score(low_value_ratings + high_value_ratings)

        # Combined score should be closer to the high-value rating
        assert abs(both - high_only) < abs(both - low_only)

    def test_decay_over_time(self):
        """Older ratings should have less weight."""
        old_time = self.now - timedelta(days=180)  # 6 months ago

        recent_rating = Rating(
            score=80, task_value_usdc=50.0, created_at=self.now, task_id="recent"
        )
        old_rating = Rating(
            score=20, task_value_usdc=50.0, created_at=old_time, task_id="old"
        )

        score = self.calculator.calculate_score([recent_rating, old_rating])
        # Recent high rating should dominate over old low rating
        assert score > 50  # Should be closer to 80 than 20

    def test_calculate_weight(self):
        """Weight calculation should use log."""
        weight = self.calculator.calculate_weight(100)
        # log(101) ≈ 4.62
        assert 4.5 < weight < 4.7

    def test_calculate_weight_small_task(self):
        """Small task should have less weight."""
        small_weight = self.calculator.calculate_weight(1)
        large_weight = self.calculator.calculate_weight(100)
        assert small_weight < large_weight

    def test_calculate_decay(self):
        """Decay calculation should work correctly."""
        # Recent: decay should be ~1
        recent_decay = self.calculator.calculate_decay(self.now)
        assert 0.99 < recent_decay <= 1.0

        # 1 month old: decay should be ~0.9
        one_month = self.now - timedelta(days=30)
        one_month_decay = self.calculator.calculate_decay(one_month)
        assert 0.85 < one_month_decay < 0.95

        # 6 months old: decay should be ~0.53
        six_months = self.now - timedelta(days=180)
        six_month_decay = self.calculator.calculate_decay(six_months)
        assert 0.4 < six_month_decay < 0.6


class TestCalculateBayesianScore:
    """Tests for convenience function."""

    def test_convenience_function(self):
        """Convenience function should work like calculator."""
        now = datetime.now(UTC)
        ratings = [Rating(score=80, task_value_usdc=50.0, created_at=now, task_id="t1")]

        score = calculate_bayesian_score(ratings)
        assert isinstance(score, float)
        assert 50 < score < 80

    def test_with_custom_config(self):
        """Should accept custom config parameters."""
        now = datetime.now(UTC)
        ratings = [Rating(score=80, task_value_usdc=50.0, created_at=now, task_id="t1")]

        # Lower confidence (C=5), higher prior (m=70)
        score = calculate_bayesian_score(ratings, C=5, m=70)

        # With higher prior and lower confidence, score should be different
        assert score > 70  # Should be between 70 and 80


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_task_value(self):
        """Zero task value should return minimum weight."""
        calculator = BayesianCalculator()
        weight = calculator.calculate_weight(0)
        # Returns min_weight (default 0.1) for zero/negative values
        # to prevent tasks from having zero influence
        assert weight == calculator.config.min_weight

    def test_negative_score_clamped(self):
        """Negative scores should be handled."""
        calculator = BayesianCalculator()
        now = datetime.now(UTC)

        # This shouldn't happen in practice but test robustness
        ratings = [
            Rating(score=-10, task_value_usdc=50.0, created_at=now, task_id="t1")
        ]
        score = calculator.calculate_score(ratings)
        # Should still calculate something reasonable
        assert isinstance(score, float)

    def test_very_high_score(self):
        """Scores above 100 should be handled."""
        calculator = BayesianCalculator()
        now = datetime.now(UTC)

        ratings = [
            Rating(score=150, task_value_usdc=50.0, created_at=now, task_id="t1")
        ]
        score = calculator.calculate_score(ratings)
        # Should still calculate (even if score is above 100)
        assert isinstance(score, float)
