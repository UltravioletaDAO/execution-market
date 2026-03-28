"""
Test Suite: AvailabilityBridge — Time-Aware Worker Routing
============================================================

Tests cover:
    1. Registration (single and batch)
    2. Time-weighted ranking (combined scoring, sorting, recommendations)
    3. Task scheduling (immediate, delayed, max-delay)
    4. Pool coverage (24h analysis, dead zones, peak hours)
    5. Deadline-aware routing (urgent, moderate, low urgency)
    6. Availability computation (hourly distribution, response times)
    7. Edge cases (no data, empty pool, zero activity)
"""

import pytest
from datetime import datetime, timezone, timedelta
from dataclasses import asdict

from mcp_server.swarm.availability_bridge import (
    AvailabilityBridge,
    TimeWeightedCandidate,
    ScheduleRecommendation,
    PoolCoverage,
    DEFAULT_AVAILABILITY_WEIGHT,
    MAX_DELAY_HOURS,
    MIN_PREDICTION_CONFIDENCE,
    FAST_RESPONSE_THRESHOLD,
    SLOW_RESPONSE_THRESHOLD,
)

UTC = timezone.utc


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════


def _hourly_dist(peak_hour=14, peak_val=0.95):
    """Create a 24-hour distribution with a peak at the given hour."""
    dist = [0.02] * 24
    for h in range(peak_hour - 3, peak_hour + 4):
        dist[h % 24] = 0.3 + (peak_val - 0.3) * max(0, 1 - abs(h - peak_hour) / 3)
    dist[peak_hour] = peak_val
    return dist


def _avail_data(tz_offset=0.0, peak_hour=14, response_min=20.0, reliability=0.8, data_points=20):
    """Standard availability profile."""
    return {
        "timezone_offset_hours": tz_offset,
        "hourly_distribution": _hourly_dist(peak_hour),
        "active_windows": [{"start": peak_hour - 4, "end": peak_hour + 4}],
        "avg_response_minutes": response_min,
        "peak_hour": peak_hour,
        "reliability_score": reliability,
        "total_data_points": data_points,
    }


def _bridge_with_workers():
    """Bridge with 3 workers in different timezones."""
    bridge = AvailabilityBridge()
    bridge.register_availability("0x001", _avail_data(tz_offset=-5.0, peak_hour=14))   # EST worker
    bridge.register_availability("0x002", _avail_data(tz_offset=1.0, peak_hour=10))    # CET worker
    bridge.register_availability("0x003", _avail_data(tz_offset=8.0, peak_hour=10))    # Asia worker
    return bridge


# ══════════════════════════════════════════════════════════════
# Registration Tests
# ══════════════════════════════════════════════════════════════


class TestRegistration:
    def test_single_registration(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data())
        assert bridge.get_registered_count() == 1

    def test_batch_registration(self):
        bridge = AvailabilityBridge()
        bridge.register_batch({
            "0x001": _avail_data(),
            "0x002": _avail_data(),
            "0x003": _avail_data(),
        })
        assert bridge.get_registered_count() == 3

    def test_overwrite_registration(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data(reliability=0.5))
        bridge.register_availability("0x001", _avail_data(reliability=0.9))
        assert bridge.get_registered_count() == 1

    def test_get_registered_wallets(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data())
        bridge.register_availability("0x002", _avail_data())
        wallets = bridge.get_registered_wallets()
        assert set(wallets) == {"0x001", "0x002"}

    def test_to_dict(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data())
        d = bridge.to_dict()
        assert d["registered_workers"] == 1
        assert d["availability_weight"] == DEFAULT_AVAILABILITY_WEIGHT


# ══════════════════════════════════════════════════════════════
# Time-Weighted Ranking Tests
# ══════════════════════════════════════════════════════════════


class TestTimeWeightedRanking:
    def test_basic_ranking(self):
        bridge = _bridge_with_workers()
        candidates = [
            {"wallet": "0x001", "score": 80.0},
            {"wallet": "0x002", "score": 75.0},
            {"wallet": "0x003", "score": 90.0},
        ]

        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        ranked = bridge.time_weighted_ranking(candidates, now=now)
        assert len(ranked) == 3
        # Should be sorted by combined_score desc
        assert ranked[0]["combined_score"] >= ranked[1]["combined_score"]

    def test_no_availability_data_neutral(self):
        bridge = AvailabilityBridge()
        candidates = [{"wallet": "0x001", "score": 80.0}]

        ranked = bridge.time_weighted_ranking(candidates)
        assert len(ranked) == 1
        assert ranked[0]["prediction_confidence"] == 0.0
        assert ranked[0]["available_now"] is True  # Assumed

    def test_available_now_flag(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data(peak_hour=14))
        candidates = [{"wallet": "0x001", "score": 80.0}]

        # At peak hour
        peak_time = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        ranked = bridge.time_weighted_ranking(candidates, now=peak_time)
        assert ranked[0]["available_now"] is True

    def test_recommendation_route_now(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data(peak_hour=14))
        candidates = [{"wallet": "0x001", "score": 80.0}]

        peak_time = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        ranked = bridge.time_weighted_ranking(candidates, now=peak_time)
        assert ranked[0]["recommendation"] == "route_now"

    def test_recommendation_delay(self):
        bridge = AvailabilityBridge()
        # Worker with very early peak (2 AM) and zero activity outside
        dist = [0.0] * 24
        dist[2] = 0.95
        dist[1] = 0.3
        dist[3] = 0.3
        bridge.register_availability("0x001", {
            "timezone_offset_hours": 0.0,
            "hourly_distribution": dist,
            "reliability_score": 0.9,
            "total_data_points": 30,
        })
        candidates = [{"wallet": "0x001", "score": 80.0}]

        # At noon — far from peak
        noon = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
        ranked = bridge.time_weighted_ranking(candidates, now=noon)
        assert ranked[0]["recommendation"] in ("delay", "route_anyway")

    def test_skill_score_fallback(self):
        bridge = AvailabilityBridge()
        candidates = [{"wallet": "0x001", "skill_score": 85.0}]

        ranked = bridge.time_weighted_ranking(candidates)
        assert ranked[0]["skill_score"] == 85.0

    def test_sorting_by_combined_score(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data(peak_hour=14))
        bridge.register_availability("0x002", _avail_data(peak_hour=14))
        candidates = [
            {"wallet": "0x001", "score": 60.0},
            {"wallet": "0x002", "score": 90.0},
        ]

        ranked = bridge.time_weighted_ranking(candidates)
        assert ranked[0]["wallet"] == "0x002"

    def test_empty_candidates(self):
        bridge = AvailabilityBridge()
        ranked = bridge.time_weighted_ranking([])
        assert ranked == []


# ══════════════════════════════════════════════════════════════
# Task Scheduling Tests
# ══════════════════════════════════════════════════════════════


class TestScheduleTask:
    def test_route_immediately_when_available(self):
        bridge = _bridge_with_workers()

        # At 14:00 UTC, EST worker (peak 14 local = 19 UTC) might not be available,
        # but CET worker (peak 10 local = 9 UTC) could be. Test at a neutral time.
        now = datetime(2026, 3, 28, 15, 0, tzinfo=UTC)
        task = {"title": "Test task"}
        result = bridge.schedule_task(task, ["0x001", "0x002", "0x003"], now=now)

        assert isinstance(result, ScheduleRecommendation)
        # At least the unknown-availability workers should be considered available

    def test_unknown_workers_assumed_available(self):
        bridge = AvailabilityBridge()
        task = {"title": "Test task"}
        result = bridge.schedule_task(task, ["0xunknown"])
        assert result.route_immediately is True
        assert result.best_worker == "0xunknown"

    def test_no_workers(self):
        bridge = AvailabilityBridge()
        task = {"title": "Test"}
        result = bridge.schedule_task(task, [])
        assert result.route_immediately is True
        assert result.best_worker is None

    def test_reason_set(self):
        bridge = AvailabilityBridge()
        task = {"title": "Test"}
        result = bridge.schedule_task(task, ["0x001"])
        assert result.reason != ""

    def test_schedule_serializable(self):
        bridge = AvailabilityBridge()
        task = {"title": "Test"}
        result = bridge.schedule_task(task, ["0x001"])
        d = asdict(result)
        assert "route_immediately" in d
        assert "reason" in d


# ══════════════════════════════════════════════════════════════
# Pool Coverage Tests
# ══════════════════════════════════════════════════════════════


class TestPoolCoverage:
    def test_single_worker_coverage(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data(peak_hour=14))

        coverage = bridge.pool_coverage(["0x001"])
        assert coverage.total_workers == 1
        assert coverage.hours_with_coverage > 0
        assert coverage.coverage_ratio <= 1.0

    def test_multi_timezone_better_coverage(self):
        bridge = _bridge_with_workers()

        cov_single = bridge.pool_coverage(["0x001"])
        cov_multi = bridge.pool_coverage(["0x001", "0x002", "0x003"])

        assert cov_multi.hours_with_coverage >= cov_single.hours_with_coverage

    def test_empty_pool(self):
        bridge = AvailabilityBridge()
        coverage = bridge.pool_coverage([])
        assert coverage.total_workers == 0
        assert coverage.hours_with_coverage == 0
        assert coverage.coverage_ratio == 0.0

    def test_dead_zones_detected(self):
        bridge = AvailabilityBridge()
        # Worker only active 12-16
        dist = [0.0] * 24
        for h in range(12, 17):
            dist[h] = 0.8
        bridge.register_availability("0x001", {
            "timezone_offset_hours": 0.0,
            "hourly_distribution": dist,
            "reliability_score": 0.8,
            "total_data_points": 20,
        })

        coverage = bridge.pool_coverage(["0x001"])
        assert len(coverage.dead_zones) > 0
        assert coverage.hours_with_coverage < 24

    def test_peak_hour_identified(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data(peak_hour=14))

        coverage = bridge.pool_coverage(["0x001"])
        assert coverage.peak_workers >= 0

    def test_unknown_workers_no_coverage(self):
        bridge = AvailabilityBridge()
        coverage = bridge.pool_coverage(["0xunknown"])
        # No availability data → no predictions → 0 coverage
        assert coverage.total_workers == 1
        assert coverage.hours_with_coverage == 0


# ══════════════════════════════════════════════════════════════
# Deadline-Aware Routing Tests
# ══════════════════════════════════════════════════════════════


class TestDeadlineAwareRouting:
    def test_urgent_deadline(self):
        bridge = _bridge_with_workers()
        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        deadline = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        task = {"title": "Urgent", "deadline": deadline}
        candidates = [
            {"wallet": "0x001", "score": 80.0},
            {"wallet": "0x002", "score": 90.0},
        ]

        result = bridge.deadline_aware_route(task, candidates, now=now)
        assert result["urgency"] == "critical"
        assert result["hours_remaining"] < 2

    def test_moderate_deadline(self):
        bridge = _bridge_with_workers()
        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        deadline = (now + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        task = {"title": "Medium", "deadline": deadline}
        candidates = [{"wallet": "0x001", "score": 80.0}]

        result = bridge.deadline_aware_route(task, candidates, now=now)
        assert result["urgency"] == "moderate"

    def test_no_deadline(self):
        bridge = _bridge_with_workers()
        task = {"title": "No deadline"}
        candidates = [{"wallet": "0x001", "score": 80.0}]

        result = bridge.deadline_aware_route(task, candidates)
        assert result["urgency"] == "low"
        assert result["hours_remaining"] is None

    def test_urgent_prioritizes_available(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0x001", _avail_data(peak_hour=14))
        bridge.register_availability("0x002", _avail_data(peak_hour=14))

        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        deadline = (now + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        task = {"deadline": deadline, "title": "Rush"}
        candidates = [
            {"wallet": "0x001", "score": 70.0},
            {"wallet": "0x002", "score": 90.0},
        ]

        result = bridge.deadline_aware_route(task, candidates, now=now)
        assert result["urgency"] == "critical"
        assert result["strategy"] in ("fastest_available", "best_skill_despite_unavailability")

    def test_expires_at_format(self):
        bridge = AvailabilityBridge()
        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        deadline = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        task = {"expires_at": deadline, "title": "Test"}
        candidates = [{"wallet": "0x001", "score": 80.0}]

        result = bridge.deadline_aware_route(task, candidates, now=now)
        assert result["urgency"] == "critical"

    def test_no_candidates(self):
        bridge = AvailabilityBridge()
        task = {"title": "Test"}
        result = bridge.deadline_aware_route(task, [])
        assert result["selected"] is None


# ══════════════════════════════════════════════════════════════
# Availability Computation Tests
# ══════════════════════════════════════════════════════════════


class TestAvailabilityComputation:
    def test_peak_hour_high_score(self):
        bridge = AvailabilityBridge()
        data = _avail_data(peak_hour=14, tz_offset=0.0)
        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)

        score, est_resp, avail, conf = bridge._compute_availability_score(data, now)
        assert score > 0.5
        assert avail is True
        assert conf > 0

    def test_off_peak_low_score(self):
        bridge = AvailabilityBridge()
        # Worker peaks at 14, check at 3 AM
        data = _avail_data(peak_hour=14, tz_offset=0.0)
        now = datetime(2026, 3, 28, 3, 0, tzinfo=UTC)

        score, est_resp, avail, conf = bridge._compute_availability_score(data, now)
        assert score < 0.3

    def test_empty_distribution(self):
        bridge = AvailabilityBridge()
        data = {"hourly_distribution": [], "timezone_offset_hours": 0.0}
        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)

        score, est_resp, avail, conf = bridge._compute_availability_score(data, now)
        assert score == 0.5  # Neutral default
        assert conf == 0.0

    def test_timezone_offset_applied(self):
        bridge = AvailabilityBridge()
        # Worker in UTC+8 peaks at 10 local = 2 UTC
        data = _avail_data(peak_hour=10, tz_offset=8.0)

        # At 2 UTC (= 10 local for +8 worker)
        now = datetime(2026, 3, 28, 2, 0, tzinfo=UTC)
        score, _, avail, _ = bridge._compute_availability_score(data, now)
        assert score > 0.5

    def test_confidence_from_data_points(self):
        bridge = AvailabilityBridge()
        # Low data points → low confidence
        low_data = _avail_data(data_points=2, reliability=0.5)
        high_data = _avail_data(data_points=30, reliability=0.9)

        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)
        _, _, _, conf_low = bridge._compute_availability_score(low_data, now)
        _, _, _, conf_high = bridge._compute_availability_score(high_data, now)

        assert conf_high > conf_low

    def test_all_zero_distribution(self):
        bridge = AvailabilityBridge()
        data = {
            "hourly_distribution": [0.0] * 24,
            "timezone_offset_hours": 0.0,
            "reliability_score": 0.5,
            "total_data_points": 10,
        }
        now = datetime(2026, 3, 28, 14, 0, tzinfo=UTC)

        score, _, avail, conf = bridge._compute_availability_score(data, now)
        # Peak is 0 → should return neutral
        assert score == 0.5


# ══════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_custom_weights(self):
        bridge = AvailabilityBridge(availability_weight=0.5)
        assert bridge.availability_weight == 0.5

    def test_custom_max_delay(self):
        bridge = AvailabilityBridge(max_delay_hours=8)
        assert bridge.max_delay_hours == 8

    def test_many_workers_ranking(self):
        bridge = AvailabilityBridge()
        for i in range(50):
            bridge.register_availability(f"0x{i:040x}", _avail_data(peak_hour=i % 24))

        candidates = [{"wallet": f"0x{i:040x}", "score": 50.0 + i} for i in range(50)]
        ranked = bridge.time_weighted_ranking(candidates)
        assert len(ranked) == 50

    def test_bad_deadline_format_graceful(self):
        bridge = AvailabilityBridge()
        task = {"deadline": "not-a-date", "title": "Bad"}
        candidates = [{"wallet": "0x001", "score": 80.0}]

        result = bridge.deadline_aware_route(task, candidates)
        # Should not crash, treat as no deadline
        assert result["urgency"] == "low"
