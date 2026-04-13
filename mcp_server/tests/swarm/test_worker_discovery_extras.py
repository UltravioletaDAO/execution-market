"""
Tests for WorkerDiscovery — active worker recruitment & supply intelligence.
"""

import time
import pytest

from mcp_server.swarm.worker_discovery import (
    WorkerDiscovery,
    TaskDemandTracker,
    TaskDemandSignal,
    WorkerCoverageMap,
    WorkerProfile,
    RecruitmentEngine,
    RECRUITMENT_CHANNELS,
)


# ─── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def tracker():
    return TaskDemandTracker(window_days=30)


@pytest.fixture
def coverage():
    return WorkerCoverageMap()


@pytest.fixture
def discovery():
    return WorkerDiscovery(window_days=30)


@pytest.fixture
def populated_discovery():
    """Discovery with some tasks and workers pre-populated."""
    d = WorkerDiscovery(window_days=30)

    # Add workers
    d.add_worker(
        "0xAlice",
        name="Alice",
        categories=["physical_verification", "delivery"],
        locations=["Miami", "remote"],
        avg_rating=4.5,
        total_tasks=50,
        completed_tasks=47,
    )
    d.add_worker(
        "0xBob",
        name="Bob",
        categories=["physical_verification"],
        locations=["Miami"],
        avg_rating=3.8,
        total_tasks=10,
        completed_tasks=8,
    )

    # Add task demand
    for i in range(15):
        d.record_task(f"t_photo_{i}", "physical_verification", "Miami", 5.00)
    for i in range(8):
        d.record_task(f"t_delivery_{i}", "delivery", "NYC", 3.50)
    for i in range(5):
        d.record_task(f"t_survey_{i}", "survey", "remote", 2.00)

    # Record some assignments
    for i in range(10):
        d.record_assignment(f"t_photo_{i}", "0xAlice", 3600.0)  # 1 hour
    for i in range(5):
        d.record_completion(f"t_photo_{i}")
    for i in range(5, 8):
        d.record_expiry(f"t_delivery_{i}")

    return d


# ─── TaskDemandSignal ─────────────────────────────────────────


class TestTaskDemandSignal:
    def test_signal_creation(self):
        signal = TaskDemandSignal(
            task_id="t1",
            category="photo",
            location="Miami",
            bounty_usd=5.00,
        )
        assert signal.status == "open"
        assert signal.time_to_assign_seconds is None

    def test_signal_to_dict(self):
        signal = TaskDemandSignal(
            task_id="t1",
            category="photo",
            location="Miami",
            bounty_usd=5.00,
        )
        d = signal.to_dict()
        assert d["task_id"] == "t1"
        assert d["bounty_usd"] == 5.00


# ─── TaskDemandTracker ────────────────────────────────────────


class TestTaskDemandTracker:
    def test_avg_time_to_assign_empty(self, tracker):
        assert tracker.avg_time_to_assign() == 0.0

    def test_expiry_rate_empty(self, tracker):
        assert tracker.expiry_rate() == 0.0

    def test_avg_bounty_filtered(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "delivery", "Miami", 3.00))
        assert tracker.avg_bounty(category="photo") == pytest.approx(5.0, abs=0.01)
        assert tracker.avg_bounty(category="delivery") == pytest.approx(3.0, abs=0.01)

    def test_max_signals(self):
        tracker = TaskDemandTracker(max_signals=5)
        for i in range(10):
            tracker.record_task(TaskDemandSignal(f"t{i}", "photo", "Miami", 1.0))
        assert len(tracker._signals) == 5


# ─── WorkerProfile ────────────────────────────────────────────


class TestWorkerProfile:
    def test_completion_rate(self):
        w = WorkerProfile(
            wallet="0xA",
            total_tasks=10,
            completed_tasks=8,
        )
        assert w.completion_rate == 0.8

    def test_completion_rate_zero(self):
        w = WorkerProfile(wallet="0xA")
        assert w.completion_rate == 0.0

    def test_churn_risk_levels(self):
        low = WorkerProfile(wallet="0xA", last_active=time.time() - 86400)
        assert low.churn_risk == "low"

        medium = WorkerProfile(wallet="0xB", last_active=time.time() - 5 * 86400)
        assert medium.churn_risk == "medium"

        high = WorkerProfile(wallet="0xC", last_active=time.time() - 10 * 86400)
        assert high.churn_risk == "high"

        churned = WorkerProfile(wallet="0xD", last_active=time.time() - 20 * 86400)
        assert churned.churn_risk == "churned"

    def test_churn_risk_never_active(self):
        w = WorkerProfile(wallet="0xA", last_active=0)
        assert w.churn_risk == "churned"


# ─── WorkerCoverageMap ────────────────────────────────────────


class TestWorkerCoverageMap:
    def test_get_worker(self, coverage):
        w = WorkerProfile(wallet="0xA", name="Alice")
        coverage.add_worker(w)
        found = coverage.get_worker("0xA")
        assert found is not None
        assert found.name == "Alice"

    def test_get_worker_not_found(self, coverage):
        assert coverage.get_worker("0xNotExist") is None

    def test_concentration_index_single_worker(self, coverage):
        w = WorkerProfile(wallet="0xA", completed_tasks=100, last_active=time.time())
        coverage.add_worker(w)
        hhi = coverage.concentration_index()
        assert hhi == 10000  # Total monopoly

    def test_concentration_index_equal_workers(self, coverage):
        for i in range(4):
            w = WorkerProfile(
                wallet=f"0x{i}", completed_tasks=25, last_active=time.time()
            )
            coverage.add_worker(w)
        hhi = coverage.concentration_index()
        assert hhi == 2500  # 4 equal workers: (0.25^2 * 4) * 10000

    def test_concentration_index_empty(self, coverage):
        assert coverage.concentration_index() == 0.0


# ─── RecruitmentEngine ────────────────────────────────────────


class TestRecruitmentEngine:
    def test_identify_gaps_no_workers(self, tracker, coverage):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "photo", "Miami", 5.00))
        engine = RecruitmentEngine(tracker, coverage)
        gaps = engine.identify_gaps()
        assert len(gaps) == 1
        assert gaps[0].severity == "critical"  # No workers = critical
        assert gaps[0].available_workers == 0

    def test_identify_gaps_with_coverage(self, tracker, coverage):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        w = WorkerProfile(
            wallet="0xA",
            categories=["photo"],
            locations=["Miami"],
            last_active=time.time(),
        )
        coverage.add_worker(w)
        engine = RecruitmentEngine(tracker, coverage)
        gaps = engine.identify_gaps()
        assert len(gaps) == 1
        assert gaps[0].available_workers == 1
        assert gaps[0].severity != "critical"

    def test_identify_gaps_high_expiry(self, tracker, coverage):
        for i in range(10):
            s = TaskDemandSignal(f"t{i}", "photo", "Miami", 5.00)
            tracker.record_task(s)
        # Expire 60%
        for i in range(6):
            tracker.record_expiry(f"t{i}")
        for i in range(6, 10):
            tracker.record_completion(f"t{i}")

        w = WorkerProfile(
            wallet="0xA",
            categories=["photo"],
            locations=["Miami"],
            last_active=time.time(),
        )
        coverage.add_worker(w)
        engine = RecruitmentEngine(tracker, coverage)
        gaps = engine.identify_gaps()
        assert len(gaps) == 1
        assert gaps[0].expiry_rate == pytest.approx(0.6, abs=0.01)

    def test_generate_recommendations(self, tracker, coverage):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "delivery", "NYC", 3.50))
        engine = RecruitmentEngine(tracker, coverage)
        recs = engine.generate_recommendations(max_count=5)
        assert len(recs) == 2
        assert recs[0].priority == 1

    def test_recommendation_channels(self, tracker, coverage):
        tracker.record_task(TaskDemandSignal("t1", "delivery", "Miami", 5.00))
        engine = RecruitmentEngine(tracker, coverage)
        recs = engine.generate_recommendations()
        assert len(recs) == 1
        assert "DoorDash" in recs[0].recommended_channels

    def test_recommendation_earnings_estimate(self, tracker, coverage):
        for i in range(7):
            s = TaskDemandSignal(f"t{i}", "photo", "Miami", 10.00)
            s.created_at = time.time() - (i * 86400)
            tracker.record_task(s)
        engine = RecruitmentEngine(tracker, coverage)
        recs = engine.generate_recommendations()
        assert recs[0].estimated_weekly_earnings_usd > 0

    def test_recommendation_competition_level(self, tracker, coverage):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        engine = RecruitmentEngine(tracker, coverage)
        recs = engine.generate_recommendations()
        assert recs[0].competition_level == "none"  # No workers


# ─── WorkerDiscovery (Unified) ────────────────────────────────


class TestWorkerDiscovery:
    def test_record_full_lifecycle(self, discovery):
        discovery.record_task("t1", "photo", "Miami", 5.00)
        discovery.record_assignment("t1", "0xAlice", 3600)
        discovery.record_completion("t1")
        # Should be tracked
        demand = discovery.demand_summary()
        assert demand["total_tasks"] == 1

    def test_supply_report(self, populated_discovery):
        report = populated_discovery.supply_report()
        assert "health" in report
        assert "supply_ratio" in report
        assert "gaps" in report
        assert "recommendations" in report
        assert "concentration_index" in report
        assert "churn_risk" in report

    def test_diagnostic_report(self, populated_discovery):
        report = populated_discovery.diagnostic_report()
        assert "WORKER DISCOVERY" in report
        assert "Health" in report

    def test_diagnostic_report_empty(self, discovery):
        report = discovery.diagnostic_report()
        assert "WORKER DISCOVERY" in report


# ─── CoverageGap ─────────────────────────────────────────────


# ─── RECRUITMENT_CHANNELS ────────────────────────────────────


class TestRecruitmentChannels:
    def test_known_categories_have_channels(self):
        for cat in [
            "physical_verification",
            "delivery",
            "data_collection",
            "survey",
            "mystery_shopping",
            "content_creation",
        ]:
            assert cat in RECRUITMENT_CHANNELS
            assert len(RECRUITMENT_CHANNELS[cat]) > 0


# ─── Edge Cases ───────────────────────────────────────────────


class TestEdgeCases:
    def test_record_assignment_unknown_task(self, discovery):
        # Should not crash
        discovery.record_assignment("nonexistent", "0xA", 100)

    def test_record_completion_unknown_task(self, discovery):
        discovery.record_completion("nonexistent")

    def test_record_expiry_unknown_task(self, discovery):
        discovery.record_expiry("nonexistent")

    def test_update_activity_unknown_worker(self, discovery):
        discovery.update_worker_activity("nonexistent")

    def test_many_tasks(self, discovery):
        for i in range(100):
            discovery.record_task(f"t{i}", "photo", "Miami", 1.0)
        demand = discovery.demand_summary()
        assert demand["total_tasks"] == 100

    def test_many_workers(self, discovery):
        for i in range(50):
            discovery.add_worker(
                f"0x{i}",
                categories=["photo"],
                locations=["Miami"],
            )
        summary = discovery.coverage_summary()
        assert summary["total_workers"] == 50

    def test_remote_location(self, discovery):
        discovery.record_task("t1", "survey", bounty_usd=2.0)
        # Default location is "remote"
        demand = discovery.demand_summary()
        assert "remote" in demand["locations"]


# ─── Full Integration Test ────────────────────────────────────


class TestFullIntegration:
    def test_complete_supply_intelligence_cycle(self):
        """Walk through a complete supply intelligence cycle."""
        d = WorkerDiscovery(window_days=7)

        # Phase 1: Demand arrives
        for i in range(20):
            d.record_task(f"photo_{i}", "physical_verification", "Miami", 5.00)
        for i in range(10):
            d.record_task(f"delivery_{i}", "delivery", "NYC", 3.50)
        for i in range(5):
            d.record_task(f"survey_{i}", "survey", "remote", 2.00)

        # Check initial supply report
        report = d.supply_report()
        assert report["health"] == "no_supply"

        # Phase 2: First workers arrive
        d.add_worker(
            "0xAlice",
            name="Alice",
            categories=["physical_verification"],
            locations=["Miami"],
            avg_rating=4.5,
            total_tasks=20,
            completed_tasks=19,
        )

        # Check gaps
        gaps = d.identify_gaps()
        assert len(gaps) > 0

        # Delivery in NYC should be a critical gap
        nyc_gaps = [g for g in gaps if g.location == "NYC"]
        assert len(nyc_gaps) > 0
        assert nyc_gaps[0].available_workers == 0

        # Phase 3: Record some assignments and completions
        for i in range(15):
            d.record_assignment(f"photo_{i}", "0xAlice", 1800)
        for i in range(10):
            d.record_completion(f"photo_{i}")
        for i in range(5):
            d.record_expiry(f"delivery_{i}")

        # Phase 4: Get recommendations
        recs = d.get_recommendations()
        assert len(recs) > 0
        # NYC delivery should be high priority (no workers, tasks expiring)
        nyc_recs = [r for r in recs if r.target_location == "NYC"]
        assert len(nyc_recs) > 0

        # Phase 5: Check concentration
        hhi = d.worker_concentration()
        assert hhi == 10000  # Alice is the only worker with completions

        # Phase 6: More workers join
        d.add_worker(
            "0xBob",
            name="Bob",
            categories=["delivery"],
            locations=["NYC"],
            total_tasks=5,
            completed_tasks=5,
        )

        # Supply should improve
        report = d.supply_report()
        assert report["coverage"]["active_workers"] == 2

        # Diagnostic report should render
        diag = d.diagnostic_report()
        assert "WORKER DISCOVERY" in diag
