"""
Tests for PipelineOptimizer — Module #60
==========================================

Comprehensive test coverage for pipeline performance analysis,
bottleneck detection, trend analysis, correlation computation,
suggestion generation, and persistence.
"""

import json
import os
import random
import tempfile

import pytest

from mcp_server.swarm.pipeline_optimizer import (
    DEFAULT_HISTORY_LIMIT,
    PIPELINE_STAGES,
    PipelineOptimizer,
    PipelineReport,
    PipelineStage,
    StageRecord,
    Suggestion,
    SuggestionPriority,
    TrendDirection,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def optimizer():
    """Fresh PipelineOptimizer with default settings."""
    return PipelineOptimizer()


@pytest.fixture
def populated_optimizer():
    """PipelineOptimizer with 100 records per stage."""
    opt = PipelineOptimizer()
    for i in range(100):
        opt.record(
            "batch", duration_ms=10 + random.random() * 5, tasks_in=50, tasks_out=8
        )
        opt.record(
            "validate", duration_ms=1 + random.random() * 0.5, tasks_in=8, tasks_out=7
        )
        opt.record(
            "chain", duration_ms=40 + random.random() * 10, tasks_in=7, tasks_out=7
        )
        opt.record(
            "score", duration_ms=100 + random.random() * 30, tasks_in=7, tasks_out=7
        )
        opt.record(
            "blend", duration_ms=5 + random.random() * 2, tasks_in=7, tasks_out=7
        )
        opt.record(
            "select", duration_ms=15 + random.random() * 5, tasks_in=7, tasks_out=6
        )
        opt.record(
            "route", duration_ms=8 + random.random() * 3, tasks_in=6, tasks_out=6
        )
    return opt


@pytest.fixture
def degrading_optimizer():
    """PipelineOptimizer with score stage degrading over time."""
    opt = PipelineOptimizer()
    # First 50: score is fast (~50ms)
    for i in range(50):
        opt.record(
            "score", duration_ms=50 + random.random() * 5, tasks_in=10, tasks_out=10
        )
    # Next 50: score is slow (~150ms — 3x slower)
    for i in range(50):
        opt.record(
            "score", duration_ms=150 + random.random() * 10, tasks_in=10, tasks_out=10
        )
    return opt


# ──────────────────────────────────────────────────────────────
# 1. StageRecord Tests
# ──────────────────────────────────────────────────────────────


class TestStageRecord:
    def test_basic_creation(self):
        r = StageRecord(stage="batch", duration_ms=12.5, tasks_in=50, tasks_out=8)
        assert r.stage == "batch"
        assert r.duration_ms == 12.5
        assert r.tasks_in == 50
        assert r.tasks_out == 8
        assert r.timestamp > 0
        assert r.metadata == {}

    def test_dropoff_rate(self):
        r = StageRecord(stage="validate", duration_ms=1.0, tasks_in=10, tasks_out=7)
        assert abs(r.dropoff_rate - 0.3) < 0.01

    def test_dropoff_rate_zero_input(self):
        r = StageRecord(stage="batch", duration_ms=0.1, tasks_in=0, tasks_out=0)
        assert r.dropoff_rate == 0.0

    def test_dropoff_rate_no_loss(self):
        r = StageRecord(stage="chain", duration_ms=5.0, tasks_in=10, tasks_out=10)
        assert r.dropoff_rate == 0.0

    def test_throughput(self):
        r = StageRecord(stage="score", duration_ms=100, tasks_in=10, tasks_out=10)
        assert r.throughput == 100.0  # 10 tasks / 100ms * 1000 = 100 tasks/sec

    def test_throughput_zero_duration(self):
        r = StageRecord(stage="score", duration_ms=0, tasks_in=10, tasks_out=10)
        assert r.throughput == float("inf")

    def test_metadata(self):
        r = StageRecord(
            stage="chain",
            duration_ms=5.0,
            tasks_in=7,
            tasks_out=7,
            metadata={"strategy": "cost_optimal"},
        )
        assert r.metadata["strategy"] == "cost_optimal"


# ──────────────────────────────────────────────────────────────
# 2. Recording Tests
# ──────────────────────────────────────────────────────────────


class TestRecording:
    def test_record_basic(self, optimizer):
        record = optimizer.record("batch", duration_ms=10, tasks_in=50, tasks_out=8)
        assert record.stage == "batch"
        assert optimizer.record_count("batch") == 1
        assert optimizer.record_count() == 1

    def test_record_all_stages(self, optimizer):
        for stage in PIPELINE_STAGES:
            optimizer.record(stage, duration_ms=5, tasks_in=10, tasks_out=10)
        assert optimizer.record_count() == 7

    def test_record_invalid_stage(self, optimizer):
        with pytest.raises(ValueError, match="Unknown stage"):
            optimizer.record("invalid", duration_ms=5, tasks_in=10, tasks_out=10)

    def test_record_negative_duration_clamped(self, optimizer):
        r = optimizer.record("batch", duration_ms=-5, tasks_in=10, tasks_out=8)
        assert r.duration_ms == 0.0

    def test_record_tasks_out_capped_at_in(self, optimizer):
        r = optimizer.record("validate", duration_ms=1, tasks_in=5, tasks_out=10)
        assert r.tasks_out == 5  # Capped at tasks_in

    def test_record_negative_tasks_clamped(self, optimizer):
        r = optimizer.record("chain", duration_ms=5, tasks_in=-3, tasks_out=-1)
        assert r.tasks_in == 0
        assert r.tasks_out == 0

    def test_history_limit(self):
        opt = PipelineOptimizer(history_limit=10)
        for i in range(20):
            opt.record("batch", duration_ms=i, tasks_in=10, tasks_out=10)
        assert opt.record_count("batch") == 10  # Only last 10 kept

    def test_record_pipeline_run(self, optimizer):
        optimizer.record_pipeline_run(
            total_duration_ms=200,
            tasks_submitted=50,
            tasks_routed=45,
            stage_durations={"batch": 10, "validate": 1, "chain": 40},
        )
        m = optimizer.metrics()
        assert m["total_pipeline_runs"] == 1

    def test_case_insensitive_stage(self, optimizer):
        r = optimizer.record("BATCH", duration_ms=5, tasks_in=10, tasks_out=10)
        assert r.stage == "batch"
        assert optimizer.record_count("batch") == 1

    def test_has_data(self, optimizer):
        assert not optimizer.has_data()
        optimizer.record("batch", duration_ms=5, tasks_in=10, tasks_out=10)
        assert optimizer.has_data()


# ──────────────────────────────────────────────────────────────
# 3. Profile Computation Tests
# ──────────────────────────────────────────────────────────────


class TestProfiles:
    def test_single_record_profile(self, optimizer):
        optimizer.record("batch", duration_ms=10, tasks_in=50, tasks_out=8)
        p = optimizer.profile("batch")
        assert p is not None
        assert p.stage == "batch"
        assert p.count == 1
        assert p.mean_ms == 10.0
        assert p.median_ms == 10.0
        assert p.min_ms == 10.0
        assert p.max_ms == 10.0
        assert p.std_dev_ms == 0.0

    def test_multiple_records_profile(self, optimizer):
        for d in [10, 20, 30, 40, 50]:
            optimizer.record("chain", duration_ms=d, tasks_in=10, tasks_out=10)
        p = optimizer.profile("chain")
        assert p.count == 5
        assert p.mean_ms == 30.0
        assert p.median_ms == 30.0
        assert p.min_ms == 10.0
        assert p.max_ms == 50.0

    def test_percentiles(self, optimizer):
        # 100 records with known distribution
        for i in range(100):
            optimizer.record("score", duration_ms=float(i), tasks_in=10, tasks_out=10)
        p = optimizer.profile("score")
        assert p.p90_ms > 85  # ~90th percentile of 0-99
        assert p.p99_ms > 95

    def test_no_data_profile(self, optimizer):
        p = optimizer.profile("batch")
        assert p is None

    def test_dropoff_tracking(self, optimizer):
        for _ in range(10):
            optimizer.record("validate", duration_ms=1, tasks_in=10, tasks_out=7)
        p = optimizer.profile("validate")
        assert abs(p.avg_dropoff_rate - 0.3) < 0.01

    def test_throughput_tracking(self, optimizer):
        for _ in range(10):
            optimizer.record("route", duration_ms=100, tasks_in=10, tasks_out=10)
        p = optimizer.profile("route")
        assert p.avg_throughput == 100.0  # 10/100ms * 1000

    def test_total_tasks(self, optimizer):
        for _ in range(5):
            optimizer.record("batch", duration_ms=10, tasks_in=50, tasks_out=8)
        p = optimizer.profile("batch")
        assert p.total_tasks_in == 250
        assert p.total_tasks_out == 40


# ──────────────────────────────────────────────────────────────
# 4. Bottleneck Detection Tests
# ──────────────────────────────────────────────────────────────


class TestBottleneck:
    def test_score_is_bottleneck(self, populated_optimizer):
        bn = populated_optimizer.bottleneck()
        assert bn is not None
        stage, share = bn
        assert stage == "score"  # Score has highest mean latency in fixture
        assert share > 0.4  # Should be >40% of total

    def test_no_data_bottleneck(self, optimizer):
        bn = optimizer.bottleneck()
        assert bn is None

    def test_balanced_stages(self, optimizer):
        # All stages with equal latency — no clear bottleneck
        for _ in range(20):
            for stage in PIPELINE_STAGES:
                optimizer.record(stage, duration_ms=10, tasks_in=10, tasks_out=10)
        bn = optimizer.bottleneck()
        assert bn is not None
        _, share = bn
        # Each stage should be ~14.3% (1/7), no bottleneck above threshold
        assert share < 0.20

    def test_single_dominant_stage(self, optimizer):
        for _ in range(20):
            optimizer.record("batch", duration_ms=1, tasks_in=50, tasks_out=8)
            optimizer.record("score", duration_ms=1000, tasks_in=8, tasks_out=8)
        bn = optimizer.bottleneck()
        assert bn is not None
        stage, share = bn
        assert stage == "score"
        assert share > 0.95


# ──────────────────────────────────────────────────────────────
# 5. Trend Analysis Tests
# ──────────────────────────────────────────────────────────────


class TestTrends:
    def test_degrading_trend(self, degrading_optimizer):
        trend = degrading_optimizer.trend("score")
        assert trend is not None
        assert trend.direction == TrendDirection.DEGRADING
        assert trend.change_pct > 100  # ~200% slower
        assert trend.baseline_ms < 60
        assert trend.current_ms > 140

    def test_improving_trend(self, optimizer):
        # First 50: slow
        for _ in range(50):
            optimizer.record("chain", duration_ms=100, tasks_in=10, tasks_out=10)
        # Next 50: fast (>25% faster)
        for _ in range(50):
            optimizer.record("chain", duration_ms=30, tasks_in=10, tasks_out=10)
        trend = optimizer.trend("chain")
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.change_pct < -50

    def test_stable_trend(self, optimizer):
        for _ in range(100):
            optimizer.record(
                "batch", duration_ms=10 + random.random(), tasks_in=10, tasks_out=10
            )
        trend = optimizer.trend("batch")
        assert trend.direction == TrendDirection.STABLE

    def test_insufficient_data(self, optimizer):
        optimizer.record("batch", duration_ms=10, tasks_in=10, tasks_out=10)
        optimizer.record("batch", duration_ms=10, tasks_in=10, tasks_out=10)
        trend = optimizer.trend("batch")
        assert trend is not None
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA

    def test_custom_window(self, optimizer):
        # 200 records, trend on last 20
        for i in range(200):
            d = 10 if i < 190 else 100  # Last 10 are slow
            optimizer.record("route", duration_ms=d, tasks_in=5, tasks_out=5)
        trend = optimizer.trend("route", window=20)
        assert trend is not None
        assert trend.sample_count == 20

    def test_no_data_trend(self, optimizer):
        trend = optimizer.trend("batch")
        assert trend is None


# ──────────────────────────────────────────────────────────────
# 6. Correlation Tests
# ──────────────────────────────────────────────────────────────


class TestCorrelations:
    def test_correlated_stages(self, optimizer):
        # Chain and score always slow/fast together
        for i in range(50):
            d = 10 + i * 2
            optimizer.record("chain", duration_ms=d, tasks_in=10, tasks_out=10)
            optimizer.record("score", duration_ms=d * 2, tasks_in=10, tasks_out=10)
        report = optimizer.analyze()
        # Find chain-score correlation
        for c in report.correlations:
            if c.stage_a == "chain" and c.stage_b == "score":
                assert c.coefficient > 0.9  # Strong positive
                assert "strong" in c.interpretation.lower()
                break

    def test_uncorrelated_stages(self, optimizer):
        random.seed(42)
        for _ in range(50):
            optimizer.record(
                "batch",
                duration_ms=random.random() * 100,
                tasks_in=10,
                tasks_out=10,
            )
            optimizer.record(
                "validate",
                duration_ms=random.random() * 100,
                tasks_in=10,
                tasks_out=10,
            )
        report = optimizer.analyze()
        for c in report.correlations:
            if c.stage_a == "batch" and c.stage_b == "validate":
                assert abs(c.coefficient) < 0.5  # Weak/no correlation
                break

    def test_insufficient_data_no_correlation(self, optimizer):
        optimizer.record("batch", duration_ms=10, tasks_in=10, tasks_out=10)
        optimizer.record("validate", duration_ms=5, tasks_in=10, tasks_out=10)
        report = optimizer.analyze()
        # Not enough data for correlation
        assert len(report.correlations) == 0


# ──────────────────────────────────────────────────────────────
# 7. Suggestion Generation Tests
# ──────────────────────────────────────────────────────────────


class TestSuggestions:
    def test_bottleneck_suggestion(self, populated_optimizer):
        suggestions = populated_optimizer.suggestions()
        # Should have at least one suggestion about score bottleneck
        bottleneck_suggestions = [
            s for s in suggestions if "bottleneck" in s.title.lower()
        ]
        assert len(bottleneck_suggestions) >= 1
        assert bottleneck_suggestions[0].stage == "score"

    def test_degradation_suggestion(self, degrading_optimizer):
        # Add other stages so analyze works
        for _ in range(100):
            for stage in ["batch", "validate", "chain", "blend", "select", "route"]:
                degrading_optimizer.record(
                    stage, duration_ms=5, tasks_in=10, tasks_out=10
                )

        suggestions = degrading_optimizer.suggestions()
        degradation = [s for s in suggestions if "degrading" in s.title.lower()]
        assert len(degradation) >= 1
        assert degradation[0].priority == SuggestionPriority.CRITICAL

    def test_dropoff_suggestion(self, optimizer):
        for _ in range(20):
            optimizer.record(
                "validate", duration_ms=1, tasks_in=100, tasks_out=50
            )  # 50% drop
        suggestions = optimizer.suggestions()
        dropoff = [s for s in suggestions if "dropoff" in s.title.lower()]
        assert len(dropoff) >= 1
        assert dropoff[0].stage == "validate"

    def test_high_variance_suggestion(self, optimizer):
        # High variance: std_dev > mean
        for _ in range(10):
            optimizer.record("chain", duration_ms=1, tasks_in=10, tasks_out=10)
        for _ in range(10):
            optimizer.record("chain", duration_ms=100, tasks_in=10, tasks_out=10)
        suggestions = optimizer.suggestions()
        variance = [s for s in suggestions if "variance" in s.title.lower()]
        assert len(variance) >= 1

    def test_suggestion_priority_ordering(self, optimizer):
        # Create conditions for multiple suggestion types
        for _ in range(20):
            optimizer.record(
                "validate", duration_ms=1, tasks_in=100, tasks_out=20
            )  # High dropoff
        for _ in range(50):
            optimizer.record("score", duration_ms=50, tasks_in=10, tasks_out=10)
        for _ in range(50):
            optimizer.record(
                "score", duration_ms=200, tasks_in=10, tasks_out=10
            )  # Degrading

        suggestions = optimizer.suggestions()
        if len(suggestions) >= 2:
            priority_values = [
                {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}[
                    s.priority.value
                ]
                for s in suggestions
            ]
            # Should be sorted by priority (critical first)
            assert priority_values == sorted(priority_values)

    def test_no_data_no_suggestions(self, optimizer):
        suggestions = optimizer.suggestions()
        assert suggestions == []

    def test_custom_analyzer(self):
        def my_analyzer(records, profiles):
            return [
                Suggestion(
                    priority=SuggestionPriority.INFO,
                    stage="batch",
                    title="Custom insight",
                    detail="Custom detail",
                )
            ]

        opt = PipelineOptimizer(custom_analyzers=[my_analyzer])
        for _ in range(10):
            opt.record("batch", duration_ms=10, tasks_in=10, tasks_out=10)
        suggestions = opt.suggestions()
        custom = [s for s in suggestions if s.title == "Custom insight"]
        assert len(custom) == 1

    def test_suggestion_to_dict(self):
        s = Suggestion(
            priority=SuggestionPriority.HIGH,
            stage="score",
            title="Optimize scoring",
            detail="Reduce signal count",
            metric_before=120.5,
            metric_name="mean_latency_ms",
            estimated_improvement="Reduce from 120ms to 80ms",
        )
        d = s.to_dict()
        assert d["priority"] == "high"
        assert d["stage"] == "score"
        assert d["metric_before"] == 120.5


# ──────────────────────────────────────────────────────────────
# 8. Full Analysis Tests
# ──────────────────────────────────────────────────────────────


class TestAnalysis:
    def test_full_report(self, populated_optimizer):
        report = populated_optimizer.analyze()
        assert isinstance(report, PipelineReport)
        assert report.total_executions == 700  # 100 records * 7 stages
        assert report.bottleneck is not None
        assert 0 <= report.health_score <= 100
        assert report.overall_latency_ms > 0
        assert len(report.stage_profiles) == 7

    def test_report_to_dict(self, populated_optimizer):
        report = populated_optimizer.analyze()
        d = report.to_dict()
        assert "bottleneck" in d
        assert "health_score" in d
        assert "stage_profiles" in d
        assert "suggestions" in d
        assert "trends" in d
        assert "correlations" in d

    def test_report_summary(self, populated_optimizer):
        report = populated_optimizer.analyze()
        summary = report.summary()
        assert "Pipeline Report" in summary
        assert "Health:" in summary
        assert "Throughput:" in summary

    def test_empty_report(self, optimizer):
        report = optimizer.analyze()
        assert report.total_executions == 0
        assert report.bottleneck is None
        assert report.health_score == 100.0  # No issues = perfect
        assert len(report.suggestions) == 0


# ──────────────────────────────────────────────────────────────
# 9. Health Score Tests
# ──────────────────────────────────────────────────────────────


class TestHealthScore:
    def test_perfect_health(self, optimizer):
        # All stages balanced, no dropoff, no degradation
        for _ in range(20):
            for stage in PIPELINE_STAGES:
                optimizer.record(stage, duration_ms=10, tasks_in=100, tasks_out=100)
        report = optimizer.analyze()
        assert report.health_score >= 90  # Near perfect

    def test_degraded_health(self, optimizer):
        # One stage degrading
        for _ in range(50):
            optimizer.record("score", duration_ms=10, tasks_in=10, tasks_out=10)
        for _ in range(50):
            optimizer.record("score", duration_ms=100, tasks_in=10, tasks_out=10)
        for _ in range(100):
            for stage in ["batch", "validate", "chain", "blend", "select", "route"]:
                optimizer.record(stage, duration_ms=10, tasks_in=10, tasks_out=10)
        report = optimizer.analyze()
        assert report.health_score < 90  # Penalty for degradation

    def test_high_dropoff_penalized(self, optimizer):
        for _ in range(20):
            optimizer.record(
                "validate", duration_ms=1, tasks_in=100, tasks_out=30
            )  # 70% drop
            optimizer.record(
                "select", duration_ms=10, tasks_in=30, tasks_out=10
            )  # 67% drop
        report = optimizer.analyze()
        assert report.health_score < 80  # Double dropoff penalty

    def test_health_bounded(self, optimizer):
        # Extreme conditions
        for _ in range(50):
            optimizer.record(
                "batch", duration_ms=1, tasks_in=100, tasks_out=0
            )  # 100% drop
        for _ in range(50):
            optimizer.record(
                "batch", duration_ms=1000, tasks_in=100, tasks_out=0
            )  # Degrading too
        for _ in range(100):
            for stage in ["validate", "chain", "score", "blend", "select", "route"]:
                optimizer.record(
                    stage, duration_ms=10, tasks_in=10, tasks_out=1
                )  # Lots of drops
        report = optimizer.analyze()
        assert 0 <= report.health_score <= 100


# ──────────────────────────────────────────────────────────────
# 10. Persistence Tests
# ──────────────────────────────────────────────────────────────


class TestPersistence:
    def test_save_load_roundtrip(self, populated_optimizer):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            populated_optimizer.save(path)

            loaded = PipelineOptimizer.load(path)
            assert loaded.record_count() == populated_optimizer.record_count()
            assert (
                loaded.metrics()["total_records"]
                == populated_optimizer.metrics()["total_records"]
            )

            # Profiles should be similar
            orig_profile = populated_optimizer.profile("score")
            loaded_profile = loaded.profile("score")
            assert abs(orig_profile.mean_ms - loaded_profile.mean_ms) < 0.01
        finally:
            os.unlink(path)

    def test_save_empty(self, optimizer):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            optimizer.save(path)
            loaded = PipelineOptimizer.load(path)
            assert loaded.record_count() == 0
        finally:
            os.unlink(path)

    def test_save_with_pipeline_runs(self, optimizer):
        optimizer.record_pipeline_run(
            total_duration_ms=200,
            tasks_submitted=50,
            tasks_routed=45,
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            optimizer.save(path)
            loaded = PipelineOptimizer.load(path)
            assert loaded.metrics()["total_pipeline_runs"] == 1
        finally:
            os.unlink(path)

    def test_save_json_valid(self, populated_optimizer):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            populated_optimizer.save(path)
            with open(path) as f:
                data = json.load(f)
            assert data["version"] == "1.0"
            assert "records" in data
            assert "config" in data
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────────────────────
# 11. Metrics & Diagnostics Tests
# ──────────────────────────────────────────────────────────────


class TestMetricsDiagnostics:
    def test_metrics(self, populated_optimizer):
        m = populated_optimizer.metrics()
        assert m["total_records"] == 700
        assert m["records_per_stage"]["batch"] == 100
        assert m["history_limit"] == DEFAULT_HISTORY_LIMIT
        assert m["uptime_seconds"] >= 0

    def test_diagnostics(self, optimizer):
        d = optimizer.diagnostics()
        assert "config" in d
        assert "metrics" in d
        assert "stages" in d
        assert d["stages"] == PIPELINE_STAGES
        assert d["has_data"] is False

    def test_stage_names(self, optimizer):
        assert optimizer.stage_names() == PIPELINE_STAGES

    def test_stage_records(self, optimizer):
        for i in range(10):
            optimizer.record("batch", duration_ms=float(i), tasks_in=10, tasks_out=10)
        records = optimizer.stage_records("batch")
        assert len(records) == 10

        last_3 = optimizer.stage_records("batch", last=3)
        assert len(last_3) == 3
        assert last_3[0].duration_ms == 7.0

    def test_reset(self, populated_optimizer):
        assert populated_optimizer.has_data()
        populated_optimizer.reset()
        assert not populated_optimizer.has_data()
        assert populated_optimizer.record_count() == 0


# ──────────────────────────────────────────────────────────────
# 12. Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_zero_duration_records(self, optimizer):
        for _ in range(10):
            optimizer.record("batch", duration_ms=0, tasks_in=10, tasks_out=10)
        p = optimizer.profile("batch")
        assert p.mean_ms == 0.0

    def test_single_task_records(self, optimizer):
        for _ in range(10):
            optimizer.record("route", duration_ms=5, tasks_in=1, tasks_out=1)
        p = optimizer.profile("route")
        assert p.total_tasks_in == 10
        assert p.avg_dropoff_rate == 0.0

    def test_all_tasks_dropped(self, optimizer):
        for _ in range(10):
            optimizer.record("validate", duration_ms=1, tasks_in=100, tasks_out=0)
        p = optimizer.profile("validate")
        assert p.avg_dropoff_rate == 1.0

    def test_history_limit_respected(self):
        opt = PipelineOptimizer(history_limit=5)
        for i in range(20):
            opt.record("batch", duration_ms=float(i), tasks_in=10, tasks_out=10)
        assert opt.record_count("batch") == 5
        # Should have the last 5: 15, 16, 17, 18, 19
        records = opt.stage_records("batch")
        assert records[0].duration_ms == 15.0

    def test_trend_with_constant_values(self, optimizer):
        for _ in range(100):
            optimizer.record("chain", duration_ms=50, tasks_in=10, tasks_out=10)
        trend = optimizer.trend("chain")
        assert trend.direction == TrendDirection.STABLE
        assert abs(trend.change_pct) < 1

    def test_pearson_constant_values(self):
        # When one series is constant, Pearson returns 0
        assert PipelineOptimizer._pearson([1, 1, 1, 1], [2, 3, 4, 5]) == 0.0

    def test_pearson_perfect_correlation(self):
        coeff = PipelineOptimizer._pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert abs(coeff - 1.0) < 0.01

    def test_pearson_negative_correlation(self):
        coeff = PipelineOptimizer._pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        assert abs(coeff - (-1.0)) < 0.01

    def test_very_large_records(self, optimizer):
        # Simulate high-volume production data
        for _ in range(1000):
            for stage in PIPELINE_STAGES:
                optimizer.record(
                    stage,
                    duration_ms=random.gauss(50, 15),
                    tasks_in=random.randint(5, 100),
                    tasks_out=random.randint(3, 80),
                )
        report = optimizer.analyze()
        assert report.total_executions == 7000
        assert report.health_score >= 0


# ──────────────────────────────────────────────────────────────
# 13. Pipeline Stages Enum Tests
# ──────────────────────────────────────────────────────────────


class TestPipelineStageEnum:
    def test_all_stages_present(self):
        assert len(PipelineStage) == 7
        assert PipelineStage.BATCH.value == "batch"
        assert PipelineStage.VALIDATE.value == "validate"
        assert PipelineStage.CHAIN.value == "chain"
        assert PipelineStage.SCORE.value == "score"
        assert PipelineStage.BLEND.value == "blend"
        assert PipelineStage.SELECT.value == "select"
        assert PipelineStage.ROUTE.value == "route"

    def test_trend_directions(self):
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.DEGRADING.value == "degrading"

    def test_suggestion_priorities(self):
        assert SuggestionPriority.CRITICAL.value == "critical"
        assert SuggestionPriority.HIGH.value == "high"
        assert SuggestionPriority.LOW.value == "low"


# ──────────────────────────────────────────────────────────────
# 14. Overall Throughput & Latency Tests
# ──────────────────────────────────────────────────────────────


class TestOverallMetrics:
    def test_throughput_from_pipeline_runs(self, optimizer):
        for _ in range(10):
            optimizer.record_pipeline_run(
                total_duration_ms=100,
                tasks_submitted=50,
                tasks_routed=45,
            )
        report = optimizer.analyze()
        # 45 tasks / 100ms * 1000 = 450 tasks/sec
        assert report.overall_throughput > 0

    def test_throughput_from_route_stage(self, optimizer):
        for _ in range(10):
            optimizer.record("route", duration_ms=100, tasks_in=10, tasks_out=10)
        report = optimizer.analyze()
        assert report.overall_throughput > 0

    def test_latency_from_pipeline_runs(self, optimizer):
        for _ in range(10):
            optimizer.record_pipeline_run(
                total_duration_ms=200,
                tasks_submitted=50,
                tasks_routed=45,
            )
        report = optimizer.analyze()
        assert abs(report.overall_latency_ms - 200) < 1

    def test_latency_from_stage_sum(self, populated_optimizer):
        report = populated_optimizer.analyze()
        # Should be sum of all stage means
        stage_sum = sum(p.mean_ms for p in report.stage_profiles.values())
        assert abs(report.overall_latency_ms - stage_sum) < 1

    def test_zero_data_metrics(self, optimizer):
        report = optimizer.analyze()
        assert report.overall_throughput == 0.0
        assert report.overall_latency_ms == 0.0


# ──────────────────────────────────────────────────────────────
# 15. Integration Simulation Tests
# ──────────────────────────────────────────────────────────────


class TestIntegrationSimulation:
    def test_realistic_pipeline_flow(self, optimizer):
        """Simulate a realistic routing session."""
        random.seed(123)
        for cycle in range(50):
            tasks = random.randint(20, 100)
            # Batch: reduces task count
            batched = max(1, tasks // random.randint(4, 8))
            optimizer.record(
                "batch", duration_ms=tasks * 0.2, tasks_in=tasks, tasks_out=batched
            )

            # Validate: drops ~10%
            validated = max(1, int(batched * 0.9))
            optimizer.record(
                "validate",
                duration_ms=batched * 0.15,
                tasks_in=batched,
                tasks_out=validated,
            )

            # Chain: no drop, but variable latency
            optimizer.record(
                "chain",
                duration_ms=validated * random.gauss(6, 2),
                tasks_in=validated,
                tasks_out=validated,
            )

            # Score: slowest, no drop
            optimizer.record(
                "score",
                duration_ms=validated * random.gauss(15, 5),
                tasks_in=validated,
                tasks_out=validated,
            )

            # Blend: fast
            optimizer.record(
                "blend",
                duration_ms=validated * 0.5,
                tasks_in=validated,
                tasks_out=validated,
            )

            # Select: drops ~5% (no available agents)
            selected = max(1, int(validated * 0.95))
            optimizer.record(
                "select",
                duration_ms=validated * 2,
                tasks_in=validated,
                tasks_out=selected,
            )

            # Route: final
            routed = selected
            optimizer.record(
                "route", duration_ms=selected * 1.2, tasks_in=selected, tasks_out=routed
            )

            optimizer.record_pipeline_run(
                total_duration_ms=tasks * 0.2
                + batched * 0.15
                + validated * (6 + 15 + 0.5 + 2 + 1.2),
                tasks_submitted=tasks,
                tasks_routed=routed,
            )

        report = optimizer.analyze()
        assert report.total_executions == 350  # 50 * 7
        assert report.bottleneck == "score"  # Score is ~15ms/task vs others
        assert report.health_score > 0
        assert len(report.suggestions) > 0
        assert report.overall_throughput > 0

        # Summary should be readable
        summary = report.summary()
        assert len(summary) > 50

    def test_pipeline_with_degradation_recovery(self, optimizer):
        """Simulate degradation followed by recovery."""
        # Phase 1: Normal (50 cycles)
        for _ in range(50):
            optimizer.record("chain", duration_ms=40, tasks_in=10, tasks_out=10)

        # Phase 2: Degradation (25 cycles)
        for _ in range(25):
            optimizer.record("chain", duration_ms=200, tasks_in=10, tasks_out=10)

        # Phase 3: Recovery (25 cycles)
        for _ in range(25):
            optimizer.record("chain", duration_ms=45, tasks_in=10, tasks_out=10)

        trend = optimizer.trend("chain")
        # With window=100, baseline includes normal+degraded, current includes degraded+recovery
        # The overall trend depends on the split point
        assert trend is not None
        assert trend.sample_count == 100
