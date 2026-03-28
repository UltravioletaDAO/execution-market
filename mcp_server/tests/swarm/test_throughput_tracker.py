"""
ThroughputTracker Test Suite
===============================

Tests real-time throughput monitoring, quality stats, burn rate,
agent health tracking, alert evaluation, and snapshot history.

Categories:
    - Basic metric recording (completions, failures, routing)
    - Sliding window behavior
    - Quality statistics (mean, median, std)
    - Burn rate calculation
    - Agent health tracking
    - Alert threshold evaluation
    - Snapshot and trend analysis
    - Edge cases and boundary conditions
"""

import time
import math
import pytest

from mcp_server.swarm.throughput_tracker import (
    ThroughputTracker,
    AlertLevel,
    AlertThresholds,
    ThroughputSnapshot,
)


# ─── Basic Metric Recording ────────────────────────────────────────────

class TestBasicRecording:
    """Tests basic event recording and counting."""

    def test_empty_tracker(self):
        """New tracker has zero metrics."""
        tt = ThroughputTracker()
        assert tt.tasks_per_hour() == 0.0
        assert tt.failures_per_hour() == 0.0
        assert tt.routing_efficiency() == 1.0  # No data = assume healthy

    def test_record_completion(self):
        """Completions increase tasks per hour."""
        tt = ThroughputTracker(window_minutes=60, baseline_tasks_per_hour=10)
        for _ in range(5):
            tt.record_completion(quality_score=0.8)

        tph = tt.tasks_per_hour()
        assert tph == 5.0

    def test_record_failure(self):
        """Failures tracked separately from completions."""
        tt = ThroughputTracker(window_minutes=60)
        tt.record_failure()
        tt.record_failure()

        assert tt.failures_per_hour() == 2.0
        assert tt.tasks_per_hour() == 0.0  # Failures don't count as completions

    def test_record_routing(self):
        """Routing efficiency computed from attempts."""
        tt = ThroughputTracker()

        # 8 successes, 2 failures = 80% efficiency
        for _ in range(8):
            tt.record_routing_attempt(success=True)
        for _ in range(2):
            tt.record_routing_attempt(success=False)

        eff = tt.routing_efficiency()
        assert abs(eff - 0.8) < 0.01

    def test_all_routing_failures(self):
        """Zero efficiency when all routing fails."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_routing_attempt(success=False)
        assert tt.routing_efficiency() == 0.0

    def test_all_routing_successes(self):
        """Perfect efficiency when all routing succeeds."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_routing_attempt(success=True)
        assert tt.routing_efficiency() == 1.0


# ─── Quality Statistics ──────────────────────────────────────────────────

class TestQualityStats:
    """Tests quality score statistical computation."""

    def test_no_scores(self):
        """Empty quality stats when no scores recorded."""
        tt = ThroughputTracker()
        stats = tt.quality_stats()
        assert stats["mean"] == 0.0
        assert stats["count"] == 0

    def test_single_score(self):
        """Single score gives mean == score, std == 0."""
        tt = ThroughputTracker()
        tt.record_completion(quality_score=0.85)
        stats = tt.quality_stats()
        assert abs(stats["mean"] - 0.85) < 0.001
        assert stats["std"] == 0.0
        assert stats["count"] == 1

    def test_uniform_scores(self):
        """All same scores → std == 0."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_completion(quality_score=0.75)
        stats = tt.quality_stats()
        assert abs(stats["mean"] - 0.75) < 0.001
        assert stats["std"] == 0.0

    def test_varied_scores(self):
        """Varied scores produce positive std."""
        tt = ThroughputTracker()
        scores = [0.5, 0.6, 0.7, 0.8, 0.9]
        for s in scores:
            tt.record_completion(quality_score=s)
        stats = tt.quality_stats()
        expected_mean = sum(scores) / len(scores)
        assert abs(stats["mean"] - expected_mean) < 0.001
        assert stats["std"] > 0

    def test_median_odd_count(self):
        """Median correct for odd number of scores."""
        tt = ThroughputTracker()
        for s in [0.3, 0.5, 0.7, 0.8, 0.9]:
            tt.record_completion(quality_score=s)
        stats = tt.quality_stats()
        assert abs(stats["median"] - 0.7) < 0.001

    def test_median_even_count(self):
        """Median correct for even number of scores."""
        tt = ThroughputTracker()
        for s in [0.4, 0.6, 0.7, 0.9]:
            tt.record_completion(quality_score=s)
        stats = tt.quality_stats()
        expected_median = (0.6 + 0.7) / 2
        assert abs(stats["median"] - expected_median) < 0.001

    def test_low_quality_distribution(self):
        """Low quality mean triggers alert-worthy condition."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_completion(quality_score=0.3)
        stats = tt.quality_stats()
        assert stats["mean"] < 0.5


# ─── Burn Rate ───────────────────────────────────────────────────────────

class TestBurnRate:
    """Tests budget burn rate calculation."""

    def test_no_spend(self):
        """Zero burn rate with no spending."""
        tt = ThroughputTracker()
        assert tt.burn_rate_per_hour() == 0.0

    def test_spend_tracking(self):
        """Burn rate reflects total spend in window."""
        tt = ThroughputTracker(window_minutes=60)
        for _ in range(10):
            tt.record_completion(bounty_usd=5.0)
        # $50 in 60-minute window = $50/hour
        assert abs(tt.burn_rate_per_hour() - 50.0) < 0.1

    def test_failure_spend_tracked(self):
        """Failures with bounty also track spend (budget consumed even on failure)."""
        tt = ThroughputTracker(window_minutes=60)
        tt.record_failure(bounty_usd=10.0)
        assert abs(tt.burn_rate_per_hour() - 10.0) < 0.1

    def test_mixed_spend(self):
        """Completions and failures both contribute to burn rate."""
        tt = ThroughputTracker(window_minutes=60)
        for _ in range(5):
            tt.record_completion(bounty_usd=8.0)
        for _ in range(3):
            tt.record_failure(bounty_usd=4.0)
        # $40 + $12 = $52/hour
        assert abs(tt.burn_rate_per_hour() - 52.0) < 0.1


# ─── Agent Health ────────────────────────────────────────────────────────

class TestAgentHealth:
    """Tests agent health tracking and summary."""

    def test_empty_health(self):
        """No agents → all zeros."""
        tt = ThroughputTracker()
        health = tt.agent_health_summary()
        assert health["total"] == 0
        assert health["degraded_pct"] == 0.0

    def test_all_healthy(self):
        """All agents healthy → 0% degraded."""
        tt = ThroughputTracker()
        for i in range(10):
            tt.record_agent_health(i, is_healthy=True)
        health = tt.agent_health_summary()
        assert health["total"] == 10
        assert health["healthy"] == 10
        assert health["degraded"] == 0
        assert health["degraded_pct"] == 0.0

    def test_mixed_health(self):
        """Mixed health computed correctly."""
        tt = ThroughputTracker()
        for i in range(7):
            tt.record_agent_health(i, is_healthy=True)
        for i in range(7, 10):
            tt.record_agent_health(i, is_healthy=False)
        health = tt.agent_health_summary()
        assert health["healthy"] == 7
        assert health["degraded"] == 3
        assert abs(health["degraded_pct"] - 30.0) < 0.1

    def test_health_update(self):
        """Agent health can be updated (degraded → recovered)."""
        tt = ThroughputTracker()
        tt.record_agent_health(1, is_healthy=False)
        assert tt.agent_health_summary()["degraded"] == 1

        tt.record_agent_health(1, is_healthy=True)
        assert tt.agent_health_summary()["degraded"] == 0


# ─── Alert Evaluation ────────────────────────────────────────────────────

class TestAlertEvaluation:
    """Tests alert threshold evaluation."""

    def test_all_ok_with_zero_baseline(self):
        """Tracker with zero baseline → throughput is OK (can't divide by zero)."""
        tt = ThroughputTracker(baseline_tasks_per_hour=0.0)
        alerts = tt.evaluate_alerts()
        # With zero baseline, throughput alert is OK (no comparison possible)
        assert alerts["throughput"] == AlertLevel.OK
        assert alerts["routing"] == AlertLevel.OK
        assert alerts["quality"] == AlertLevel.OK

    def test_empty_tracker_throughput_critical(self):
        """Empty tracker with positive baseline → throughput CRITICAL (0% of baseline)."""
        tt = ThroughputTracker(baseline_tasks_per_hour=10.0)
        alerts = tt.evaluate_alerts()
        # 0 tasks / 10 baseline = 0% → CRITICAL
        assert alerts["throughput"] == AlertLevel.CRITICAL

    def test_throughput_warning(self):
        """Low throughput triggers warning."""
        tt = ThroughputTracker(baseline_tasks_per_hour=100, window_minutes=60)
        # Record only 30 completions in 60-min window (30/100 = 30% < 50% threshold)
        for _ in range(30):
            tt.record_completion()
        alerts = tt.evaluate_alerts()
        assert alerts["throughput"] == AlertLevel.WARNING

    def test_throughput_critical(self):
        """Very low throughput triggers critical."""
        tt = ThroughputTracker(baseline_tasks_per_hour=100, window_minutes=60)
        # Record only 10 completions (10/100 = 10% < 25% threshold)
        for _ in range(10):
            tt.record_completion()
        alerts = tt.evaluate_alerts()
        assert alerts["throughput"] == AlertLevel.CRITICAL

    def test_throughput_ok(self):
        """Good throughput → OK."""
        tt = ThroughputTracker(baseline_tasks_per_hour=10, window_minutes=60)
        for _ in range(10):
            tt.record_completion()
        alerts = tt.evaluate_alerts()
        assert alerts["throughput"] == AlertLevel.OK

    def test_routing_warning(self):
        """Low routing efficiency triggers warning."""
        tt = ThroughputTracker()
        # 70% efficiency < 80% warning threshold
        for _ in range(7):
            tt.record_routing_attempt(success=True)
        for _ in range(3):
            tt.record_routing_attempt(success=False)
        alerts = tt.evaluate_alerts()
        assert alerts["routing"] == AlertLevel.WARNING

    def test_routing_critical(self):
        """Very low routing efficiency triggers critical."""
        tt = ThroughputTracker()
        # 50% efficiency < 60% critical threshold
        for _ in range(5):
            tt.record_routing_attempt(success=True)
        for _ in range(5):
            tt.record_routing_attempt(success=False)
        alerts = tt.evaluate_alerts()
        assert alerts["routing"] == AlertLevel.CRITICAL

    def test_quality_warning(self):
        """Low quality mean triggers warning."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_completion(quality_score=0.55)
        alerts = tt.evaluate_alerts()
        assert alerts["quality"] == AlertLevel.WARNING

    def test_quality_critical(self):
        """Very low quality mean triggers critical."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_completion(quality_score=0.35)
        alerts = tt.evaluate_alerts()
        assert alerts["quality"] == AlertLevel.CRITICAL

    def test_budget_warning(self):
        """High burn rate triggers warning."""
        tt = ThroughputTracker(
            projected_daily_spend_usd=24.0,  # $1/hour projected
            window_minutes=60,
        )
        # Spend $1.80 in window ($1.80/hr vs $1.00/hr = 180% > 150%)
        for _ in range(18):
            tt.record_completion(bounty_usd=0.1)
        alerts = tt.evaluate_alerts()
        assert alerts["budget"] == AlertLevel.WARNING

    def test_budget_critical(self):
        """Very high burn rate triggers critical."""
        tt = ThroughputTracker(
            projected_daily_spend_usd=24.0,  # $1/hour projected
            window_minutes=60,
        )
        # Spend $2.50 in window ($2.50/hr vs $1.00/hr = 250% > 200%)
        for _ in range(25):
            tt.record_completion(bounty_usd=0.1)
        alerts = tt.evaluate_alerts()
        assert alerts["budget"] == AlertLevel.CRITICAL

    def test_health_warning(self):
        """Agent degradation triggers warning."""
        tt = ThroughputTracker()
        for i in range(8):
            tt.record_agent_health(i, is_healthy=True)
        for i in range(8, 11):
            tt.record_agent_health(i, is_healthy=False)
        # 3/11 ≈ 27% > 20% warning threshold
        alerts = tt.evaluate_alerts()
        assert alerts["health"] == AlertLevel.WARNING

    def test_health_critical(self):
        """Mass degradation triggers critical."""
        tt = ThroughputTracker()
        for i in range(5):
            tt.record_agent_health(i, is_healthy=True)
        for i in range(5, 10):
            tt.record_agent_health(i, is_healthy=False)
        # 5/10 = 50% > 30% critical threshold
        alerts = tt.evaluate_alerts()
        assert alerts["health"] == AlertLevel.CRITICAL

    def test_has_any_alert_warning(self):
        """has_any_alert detects warnings."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_completion(quality_score=0.55)  # Warning-level quality
        assert tt.has_any_alert(AlertLevel.WARNING)

    def test_has_any_alert_false(self):
        """has_any_alert returns False when all OK (zero baseline)."""
        tt = ThroughputTracker(baseline_tasks_per_hour=0.0, projected_daily_spend_usd=0.0)
        assert not tt.has_any_alert(AlertLevel.WARNING)

    def test_custom_thresholds(self):
        """Custom thresholds override defaults."""
        custom = AlertThresholds(
            routing_warning_pct=90.0,  # Stricter than default 80%
        )
        tt = ThroughputTracker(thresholds=custom)
        # 85% efficiency → OK with defaults, WARNING with custom
        for _ in range(85):
            tt.record_routing_attempt(success=True)
        for _ in range(15):
            tt.record_routing_attempt(success=False)
        alerts = tt.evaluate_alerts()
        assert alerts["routing"] == AlertLevel.WARNING


# ─── Snapshot and Trend ──────────────────────────────────────────────────

class TestSnapshotAndTrend:
    """Tests snapshot capture and trend analysis."""

    def test_snapshot_structure(self):
        """Snapshot contains all expected fields."""
        tt = ThroughputTracker()
        tt.record_completion(quality_score=0.8, bounty_usd=5.0)
        snap = tt.snapshot()

        assert isinstance(snap, ThroughputSnapshot)
        assert snap.tasks_per_hour > 0
        assert snap.quality_mean > 0
        assert isinstance(snap.alerts, dict)

    def test_snapshot_to_dict(self):
        """Snapshot serializes to dict."""
        tt = ThroughputTracker()
        tt.record_completion(quality_score=0.8)
        snap = tt.snapshot()
        d = snap.to_dict()

        assert "throughput" in d
        assert "routing" in d
        assert "quality" in d
        assert "budget" in d
        assert "agents" in d
        assert "alerts" in d

    def test_snapshot_history(self):
        """Snapshots accumulate in history."""
        tt = ThroughputTracker()
        for i in range(5):
            tt.record_completion(quality_score=0.7 + i * 0.05)
            tt.snapshot()

        assert len(tt._snapshot_history) == 5

    def test_trend_extraction(self):
        """Trend extracts metric values from history."""
        tt = ThroughputTracker()
        for i in range(5):
            tt.record_completion(quality_score=0.5 + i * 0.1)
            tt.snapshot()

        trend = tt.get_trend("quality_mean", last_n=5)
        assert len(trend) == 5
        # Quality mean should increase
        assert trend[-1] >= trend[0]

    def test_snapshot_cap(self):
        """Snapshot history capped at maxlen."""
        tt = ThroughputTracker()
        for _ in range(600):
            tt.snapshot()
        assert len(tt._snapshot_history) == 500

    def test_alert_callback(self):
        """Alert callbacks fire on warning/critical snapshots."""
        tt = ThroughputTracker()
        alerts_received = []

        def on_alert(signal, level, snap):
            alerts_received.append((signal, level))

        tt.on_alert(on_alert)

        # Trigger quality warning
        for _ in range(10):
            tt.record_completion(quality_score=0.35)  # Critical level

        tt.snapshot()
        assert len(alerts_received) > 0
        assert any(level == AlertLevel.CRITICAL for _, level in alerts_received)

    def test_alert_callback_error_isolation(self):
        """Bad callback doesn't break snapshot."""
        tt = ThroughputTracker()

        def bad_callback(signal, level, snap):
            raise RuntimeError("Callback failure!")

        tt.on_alert(bad_callback)

        for _ in range(10):
            tt.record_completion(quality_score=0.35)

        # Should not raise despite bad callback
        snap = tt.snapshot()
        assert snap is not None


# ─── Edge Cases ──────────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests boundary conditions and edge cases."""

    def test_zero_baseline(self):
        """Zero baseline doesn't divide by zero."""
        tt = ThroughputTracker(baseline_tasks_per_hour=0.0)
        alerts = tt.evaluate_alerts()
        assert alerts["throughput"] == AlertLevel.OK

    def test_zero_projected_spend(self):
        """Zero projected spend doesn't divide by zero."""
        tt = ThroughputTracker(projected_daily_spend_usd=0.0)
        tt.record_completion(bounty_usd=10.0)
        alerts = tt.evaluate_alerts()
        assert alerts["budget"] == AlertLevel.OK

    def test_deque_maxlen(self):
        """Deques don't exceed max_samples."""
        tt = ThroughputTracker(max_samples=100)
        for _ in range(200):
            tt.record_completion(quality_score=0.8)
        assert len(tt._completions) == 100
        assert len(tt._quality_scores) == 100

    def test_reset_clears_all(self):
        """Reset clears all tracked data."""
        tt = ThroughputTracker()
        for _ in range(10):
            tt.record_completion(quality_score=0.8, bounty_usd=5.0)
            tt.record_failure()
            tt.record_routing_attempt(success=True)
            tt.record_agent_health(1, is_healthy=True)
        tt.snapshot()

        tt.reset()

        assert tt.tasks_per_hour() == 0.0
        assert tt.failures_per_hour() == 0.0
        assert tt.burn_rate_per_hour() == 0.0
        assert tt.agent_health_summary()["total"] == 0
        assert len(tt._snapshot_history) == 0

    def test_zero_quality_scores(self):
        """Quality score of 0.0 treated as 'no quality data'."""
        tt = ThroughputTracker()
        tt.record_completion(quality_score=0.0)  # 0.0 is filtered out
        stats = tt.quality_stats()
        assert stats["count"] == 0

    def test_very_small_window(self):
        """Very small window doesn't error."""
        tt = ThroughputTracker(window_minutes=1)
        tt.record_completion()
        tph = tt.tasks_per_hour()
        assert tph == 60.0  # 1 task in 1 minute = 60/hour

    def test_many_agents_health(self):
        """Health tracking handles 100 agents."""
        tt = ThroughputTracker()
        for i in range(100):
            tt.record_agent_health(i, is_healthy=i < 80)
        health = tt.agent_health_summary()
        assert health["total"] == 100
        assert health["healthy"] == 80
        assert health["degraded"] == 20
        assert abs(health["degraded_pct"] - 20.0) < 0.1
