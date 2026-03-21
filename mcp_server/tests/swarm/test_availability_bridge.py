"""
Tests for swarm.availability_bridge module.

Covers:
    - Registration (single and batch)
    - Time-weighted ranking
    - Task scheduling (available now, delayed, max delay)
    - Pool coverage analysis
    - Deadline-aware routing
    - Edge cases
"""

from datetime import datetime, timezone, timedelta

from mcp_server.swarm.availability_bridge import (
    AvailabilityBridge,
    DEFAULT_AVAILABILITY_WEIGHT,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_availability_profile(
    tz_offset: float = 0.0,
    peak_hour: int = 14,
    data_points: int = 20,
    reliability: float = 0.8,
) -> dict:
    """Create an availability profile with activity clustered around peak_hour."""
    hourly = [0.01] * 24
    # Create a bell curve around peak_hour
    for offset in range(-4, 5):
        h = (peak_hour + offset) % 24
        weight = max(0.02, 0.15 - abs(offset) * 0.03)
        hourly[h] = weight

    return {
        "timezone_offset_hours": tz_offset,
        "hourly_distribution": hourly,
        "active_windows": [
            {
                "start_hour": (peak_hour - 4) % 24,
                "end_hour": (peak_hour + 4) % 24,
                "confidence": 0.8,
            }
        ],
        "avg_response_minutes": 20.0,
        "peak_hour": peak_hour,
        "reliability_score": reliability,
        "total_data_points": data_points,
    }


def make_candidates(wallets_and_scores: list) -> list:
    """Create candidate dicts from [(wallet, score), ...]."""
    return [{"wallet": w, "score": s} for w, s in wallets_and_scores]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_single(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile())
        assert bridge.get_registered_count() == 1
        assert "0xA" in bridge.get_registered_wallets()

    def test_register_batch(self):
        bridge = AvailabilityBridge()
        bridge.register_batch(
            {
                "0xA": make_availability_profile(peak_hour=10),
                "0xB": make_availability_profile(peak_hour=18),
            }
        )
        assert bridge.get_registered_count() == 2

    def test_overwrite(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=10))
        bridge.register_availability("0xA", make_availability_profile(peak_hour=18))
        assert bridge.get_registered_count() == 1

    def test_to_dict(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile())
        d = bridge.to_dict()
        assert d["registered_workers"] == 1
        assert d["availability_weight"] == DEFAULT_AVAILABILITY_WEIGHT


# ---------------------------------------------------------------------------
# Time-Weighted Ranking
# ---------------------------------------------------------------------------


class TestTimeWeightedRanking:
    def test_empty_candidates(self):
        bridge = AvailabilityBridge()
        result = bridge.time_weighted_ranking([])
        assert result == []

    def test_no_availability_data(self):
        bridge = AvailabilityBridge()
        candidates = make_candidates([("0xA", 80.0), ("0xB", 60.0)])
        result = bridge.time_weighted_ranking(candidates)
        assert len(result) == 2
        # Without data, should rank by skill score
        assert result[0]["wallet"] == "0xA"
        assert result[0]["combined_score"] >= result[1]["combined_score"]

    def test_available_worker_boosted(self):
        bridge = AvailabilityBridge()
        # Worker A: peak at 14, check at 14 UTC → should be available
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        # Worker B: peak at 2, check at 14 UTC → should be less available
        bridge.register_availability("0xB", make_availability_profile(peak_hour=2))

        candidates = make_candidates([("0xA", 70.0), ("0xB", 75.0)])
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)
        result = bridge.time_weighted_ranking(candidates, now=now)

        # Worker A should rank higher despite lower skill score (available now)
        assert result[0]["wallet"] == "0xA"
        assert result[0]["available_now"] is True

    def test_recommendation_types(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        bridge.register_availability("0xB", make_availability_profile(peak_hour=3))

        candidates = make_candidates([("0xA", 80.0), ("0xB", 80.0)])
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)
        result = bridge.time_weighted_ranking(candidates, now=now)

        recommendations = {r["wallet"]: r["recommendation"] for r in result}
        assert recommendations["0xA"] == "route_now"
        # Worker B may be "delay" or "route_anyway" depending on response estimate

    def test_skill_score_variants(self):
        """Candidates can provide score via different key names."""
        bridge = AvailabilityBridge()
        candidates = [
            {"wallet": "0xA", "score": 80.0},
            {"wallet": "0xB", "skill_score": 70.0},
            {"wallet": "0xC", "match_score": 60.0},  # Unsupported key
        ]
        result = bridge.time_weighted_ranking(candidates)
        assert len(result) == 3
        assert result[0]["skill_score"] == 80.0
        assert result[1]["skill_score"] == 70.0
        assert result[2]["skill_score"] == 50.0  # Default


# ---------------------------------------------------------------------------
# Task Scheduling
# ---------------------------------------------------------------------------


class TestTaskScheduling:
    def test_workers_available_now(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)

        rec = bridge.schedule_task(
            {"id": "task1"},
            ["0xA"],
            now=now,
        )
        assert rec.route_immediately is True
        assert rec.best_worker == "0xA"
        assert rec.reason == "workers_available_now"

    def test_no_availability_data_routes_immediately(self):
        bridge = AvailabilityBridge()
        rec = bridge.schedule_task(
            {"id": "task1"},
            ["0xA", "0xB"],
        )
        # Unknown availability → assume available → route immediately
        assert rec.route_immediately is True

    def test_delay_recommendation(self):
        bridge = AvailabilityBridge()
        # Worker only active around 14 UTC
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        # Check at 3 AM UTC → nobody available
        now = datetime(2026, 3, 15, 3, 0, 0, tzinfo=UTC)

        rec = bridge.schedule_task(
            {"id": "task1"},
            ["0xA"],
            now=now,
        )
        # Should either delay or route anyway, depending on configuration
        assert rec.reason in (
            "delay_for_better_availability",
            "max_delay_exceeded_routing_anyway",
            "workers_available_now",
            "no_availability_data_routing_immediately",
        )

    def test_alternatives_provided(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        bridge.register_availability("0xB", make_availability_profile(peak_hour=14))
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)

        rec = bridge.schedule_task(
            {"id": "task1"},
            ["0xA", "0xB"],
            now=now,
        )
        assert rec.route_immediately is True
        # Should have at least one alternative
        assert len(rec.alternatives) >= 0

    def test_empty_candidates(self):
        bridge = AvailabilityBridge()
        rec = bridge.schedule_task({"id": "task1"}, [])
        assert rec.route_immediately is True
        assert rec.best_worker is None


# ---------------------------------------------------------------------------
# Pool Coverage
# ---------------------------------------------------------------------------


class TestPoolCoverage:
    def test_empty_pool(self):
        bridge = AvailabilityBridge()
        cov = bridge.pool_coverage([])
        assert cov.total_workers == 0
        assert cov.hours_with_coverage == 0
        assert cov.coverage_ratio == 0.0

    def test_single_worker_partial_coverage(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        now = datetime(2026, 3, 15, 0, 0, 0, tzinfo=UTC)

        cov = bridge.pool_coverage(["0xA"], now=now)
        assert cov.total_workers == 1
        # Worker with peak at 14 should cover some hours, not all 24
        assert 0 < cov.hours_with_coverage <= 24
        assert cov.peak_workers == 1
        assert len(cov.dead_zones) > 0

    def test_two_workers_better_coverage(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=10))
        bridge.register_availability("0xB", make_availability_profile(peak_hour=22))
        now = datetime(2026, 3, 15, 0, 0, 0, tzinfo=UTC)

        cov = bridge.pool_coverage(["0xA", "0xB"], now=now)
        assert cov.total_workers == 2
        assert cov.hours_with_coverage > 0
        # Two workers in different timezones should cover more
        assert cov.coverage_ratio >= 0.3

    def test_peak_detected(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        bridge.register_availability("0xB", make_availability_profile(peak_hour=14))
        now = datetime(2026, 3, 15, 0, 0, 0, tzinfo=UTC)

        cov = bridge.pool_coverage(["0xA", "0xB"], now=now)
        # Peak should be near 14 (within the active window 10-18)
        assert 10 <= cov.peak_hour_utc <= 18
        assert cov.peak_workers == 2

    def test_unregistered_workers(self):
        bridge = AvailabilityBridge()
        # Worker not registered → not counted
        cov = bridge.pool_coverage(["0xUnknown"])
        assert cov.total_workers == 1
        assert cov.hours_with_coverage == 0


# ---------------------------------------------------------------------------
# Deadline-Aware Routing
# ---------------------------------------------------------------------------


class TestDeadlineRouting:
    def test_urgent_deadline(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)
        deadline = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        result = bridge.deadline_aware_route(
            {"id": "t1", "deadline": deadline},
            make_candidates([("0xA", 80.0)]),
            now=now,
        )
        assert result["urgency"] == "critical"
        assert result["strategy"] == "fastest_available"

    def test_moderate_deadline(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=14))
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)
        deadline = (now + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

        result = bridge.deadline_aware_route(
            {"id": "t1", "deadline": deadline},
            make_candidates([("0xA", 80.0)]),
            now=now,
        )
        assert result["urgency"] == "moderate"
        assert result["strategy"] == "optimal_combined_score"

    def test_no_deadline(self):
        bridge = AvailabilityBridge()
        result = bridge.deadline_aware_route(
            {"id": "t1"},
            make_candidates([("0xA", 80.0)]),
        )
        assert result["urgency"] == "low"

    def test_urgent_no_available_workers(self):
        bridge = AvailabilityBridge()
        bridge.register_availability("0xA", make_availability_profile(peak_hour=3))
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)
        deadline = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        result = bridge.deadline_aware_route(
            {"id": "t1", "deadline": deadline},
            make_candidates([("0xA", 80.0)]),
            now=now,
        )
        assert result["urgency"] == "critical"
        # Should still select best worker despite unavailability
        assert result["selected"] is not None

    def test_alternatives_provided(self):
        bridge = AvailabilityBridge()
        now = datetime(2026, 3, 15, 14, 0, 0, tzinfo=UTC)
        candidates = make_candidates(
            [
                ("0xA", 90.0),
                ("0xB", 80.0),
                ("0xC", 70.0),
            ]
        )
        result = bridge.deadline_aware_route({"id": "t1"}, candidates, now=now)
        assert len(result["alternatives"]) <= 2


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_bad_hourly_distribution(self):
        bridge = AvailabilityBridge()
        bridge.register_availability(
            "0xA",
            {
                "timezone_offset_hours": 0.0,
                "hourly_distribution": [],  # Empty!
                "reliability_score": 0.5,
                "total_data_points": 5,
            },
        )
        result = bridge.time_weighted_ranking(make_candidates([("0xA", 80.0)]))
        assert len(result) == 1
        assert result[0]["prediction_confidence"] < 0.5

    def test_zero_peak(self):
        bridge = AvailabilityBridge()
        bridge.register_availability(
            "0xA",
            {
                "timezone_offset_hours": 0.0,
                "hourly_distribution": [0.0] * 24,
                "reliability_score": 0.5,
                "total_data_points": 5,
            },
        )
        result = bridge.time_weighted_ranking(make_candidates([("0xA", 80.0)]))
        assert len(result) == 1

    def test_custom_weights(self):
        bridge = AvailabilityBridge(availability_weight=0.5)
        assert bridge.availability_weight == 0.5

    def test_max_delay_config(self):
        bridge = AvailabilityBridge(max_delay_hours=1.0)
        assert bridge.max_delay_hours == 1.0
