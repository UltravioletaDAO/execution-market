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
    CoverageGap,
    RecruitmentRecommendation,
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

    def test_record_task(self, tracker):
        signal = TaskDemandSignal("t1", "photo", "Miami", 5.00)
        tracker.record_task(signal)
        assert len(tracker._signals) == 1

    def test_category_demand(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "photo", "NYC", 3.00))
        tracker.record_task(TaskDemandSignal("t3", "delivery", "Miami", 4.00))
        demand = tracker.category_demand()
        assert demand["photo"] == 2
        assert demand["delivery"] == 1

    def test_location_demand(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "delivery", "Miami", 3.00))
        tracker.record_task(TaskDemandSignal("t3", "photo", "NYC", 4.00))
        demand = tracker.location_demand()
        assert demand["Miami"] == 2
        assert demand["NYC"] == 1

    def test_category_location_demand(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "photo", "Miami", 3.00))
        demand = tracker.category_location_demand()
        assert demand[("photo", "Miami")] == 2

    def test_record_assignment(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_assignment("t1", "0xAlice", 3600.0)
        assert tracker._signals[0].status == "assigned"
        assert tracker._signals[0].time_to_assign_seconds == 3600.0

    def test_record_completion(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_completion("t1")
        assert tracker._signals[0].status == "completed"

    def test_record_expiry(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_expiry("t1")
        assert tracker._signals[0].status == "expired"

    def test_avg_time_to_assign(self, tracker):
        s1 = TaskDemandSignal("t1", "photo", "Miami", 5.00)
        s1.time_to_assign_seconds = 1800  # 30 min
        tracker.record_task(s1)
        tracker.record_assignment("t1", "0xA", 1800)

        s2 = TaskDemandSignal("t2", "photo", "Miami", 5.00)
        tracker.record_task(s2)
        tracker.record_assignment("t2", "0xB", 3600)

        avg = tracker.avg_time_to_assign(category="photo")
        assert avg == pytest.approx(2700, abs=1)  # avg of 1800 and 3600

    def test_avg_time_to_assign_empty(self, tracker):
        assert tracker.avg_time_to_assign() == 0.0

    def test_expiry_rate(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t3", "photo", "Miami", 5.00))
        tracker.record_completion("t1")
        tracker.record_expiry("t2")
        tracker.record_expiry("t3")
        rate = tracker.expiry_rate(category="photo")
        assert rate == pytest.approx(2 / 3, abs=0.01)

    def test_expiry_rate_empty(self, tracker):
        assert tracker.expiry_rate() == 0.0

    def test_avg_bounty(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "photo", "Miami", 3.00))
        assert tracker.avg_bounty() == pytest.approx(4.0, abs=0.01)

    def test_avg_bounty_filtered(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        tracker.record_task(TaskDemandSignal("t2", "delivery", "Miami", 3.00))
        assert tracker.avg_bounty(category="photo") == pytest.approx(5.0, abs=0.01)
        assert tracker.avg_bounty(category="delivery") == pytest.approx(3.0, abs=0.01)

    def test_demand_velocity(self, tracker):
        # Create signals spread over time
        now = time.time()
        for i in range(7):
            s = TaskDemandSignal(f"t{i}", "photo", "Miami", 5.00)
            s.created_at = now - (i * 86400)  # One per day for 7 days
            tracker.record_task(s)
        velocity = tracker.demand_velocity("photo")
        # 7 signals over ~6 days = ~8.2/week (signals at day 0-6 = 6-day span)
        assert velocity == pytest.approx(8.17, abs=1.0)

    def test_demand_velocity_empty(self, tracker):
        assert tracker.demand_velocity() == 0.0

    def test_summary(self, tracker):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        summary = tracker.summary()
        assert summary["total_tasks"] == 1
        assert "categories" in summary
        assert "locations" in summary

    def test_window_filtering(self):
        tracker = TaskDemandTracker(window_days=1)
        # Old signal
        old = TaskDemandSignal("old", "photo", "Miami", 5.00)
        old.created_at = time.time() - 2 * 86400
        tracker.record_task(old)
        # New signal
        tracker.record_task(TaskDemandSignal("new", "photo", "Miami", 5.00))
        assert tracker.category_demand()["photo"] == 1  # Only the new one

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

    def test_is_active_recent(self):
        w = WorkerProfile(wallet="0xA", last_active=time.time())
        assert w.is_active is True

    def test_is_active_stale(self):
        w = WorkerProfile(wallet="0xA", last_active=time.time() - 8 * 86400)
        assert w.is_active is False

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

    def test_to_dict(self):
        w = WorkerProfile(
            wallet="0xA",
            name="Alice",
            categories=["photo"],
            avg_rating=4.5,
        )
        d = w.to_dict()
        assert d["wallet"] == "0xA"
        assert d["name"] == "Alice"
        assert "churn_risk" in d
        assert "completion_rate" in d

    def test_days_since_active(self):
        w = WorkerProfile(wallet="0xA", last_active=time.time() - 3 * 86400)
        assert w.days_since_active == pytest.approx(3.0, abs=0.01)


# ─── WorkerCoverageMap ────────────────────────────────────────


class TestWorkerCoverageMap:

    def test_add_worker(self, coverage):
        w = WorkerProfile(wallet="0xA", categories=["photo"], locations=["Miami"])
        coverage.add_worker(w)
        assert coverage.total_workers == 1

    def test_remove_worker(self, coverage):
        w = WorkerProfile(wallet="0xA")
        coverage.add_worker(w)
        coverage.remove_worker("0xA")
        assert coverage.total_workers == 0

    def test_get_worker(self, coverage):
        w = WorkerProfile(wallet="0xA", name="Alice")
        coverage.add_worker(w)
        found = coverage.get_worker("0xA")
        assert found is not None
        assert found.name == "Alice"

    def test_get_worker_not_found(self, coverage):
        assert coverage.get_worker("0xNotExist") is None

    def test_active_workers(self, coverage):
        active = WorkerProfile(wallet="0xA", last_active=time.time())
        stale = WorkerProfile(wallet="0xB", last_active=time.time() - 30 * 86400)
        coverage.add_worker(active)
        coverage.add_worker(stale)
        assert coverage.total_workers == 2
        assert coverage.active_workers == 1

    def test_workers_for_category(self, coverage):
        w1 = WorkerProfile(wallet="0xA", categories=["photo", "delivery"], last_active=time.time())
        w2 = WorkerProfile(wallet="0xB", categories=["delivery"], last_active=time.time())
        coverage.add_worker(w1)
        coverage.add_worker(w2)
        photo_workers = coverage.workers_for_category("photo")
        assert len(photo_workers) == 1
        delivery_workers = coverage.workers_for_category("delivery")
        assert len(delivery_workers) == 2

    def test_workers_for_location(self, coverage):
        w1 = WorkerProfile(wallet="0xA", locations=["Miami", "remote"], last_active=time.time())
        w2 = WorkerProfile(wallet="0xB", locations=["NYC"], last_active=time.time())
        coverage.add_worker(w1)
        coverage.add_worker(w2)
        miami_workers = coverage.workers_for_location("Miami")
        assert len(miami_workers) == 1
        nyc_workers = coverage.workers_for_location("NYC")
        assert len(nyc_workers) == 1

    def test_workers_for_category_location(self, coverage):
        w1 = WorkerProfile(
            wallet="0xA",
            categories=["photo"],
            locations=["Miami"],
            last_active=time.time(),
        )
        w2 = WorkerProfile(
            wallet="0xB",
            categories=["photo"],
            locations=["NYC"],
            last_active=time.time(),
        )
        coverage.add_worker(w1)
        coverage.add_worker(w2)
        workers = coverage.workers_for_category_location("photo", "Miami")
        assert len(workers) == 1
        assert workers[0].wallet == "0xA"

    def test_category_coverage(self, coverage):
        w1 = WorkerProfile(wallet="0xA", categories=["photo", "delivery"], last_active=time.time())
        w2 = WorkerProfile(wallet="0xB", categories=["delivery"], last_active=time.time())
        coverage.add_worker(w1)
        coverage.add_worker(w2)
        cov = coverage.category_coverage()
        assert cov["photo"] == 1
        assert cov["delivery"] == 2

    def test_location_coverage(self, coverage):
        w1 = WorkerProfile(wallet="0xA", locations=["Miami"], last_active=time.time())
        w2 = WorkerProfile(wallet="0xB", locations=["Miami", "NYC"], last_active=time.time())
        coverage.add_worker(w1)
        coverage.add_worker(w2)
        cov = coverage.location_coverage()
        assert cov["Miami"] == 2
        assert cov["NYC"] == 1

    def test_concentration_index_single_worker(self, coverage):
        w = WorkerProfile(wallet="0xA", completed_tasks=100, last_active=time.time())
        coverage.add_worker(w)
        hhi = coverage.concentration_index()
        assert hhi == 10000  # Total monopoly

    def test_concentration_index_equal_workers(self, coverage):
        for i in range(4):
            w = WorkerProfile(wallet=f"0x{i}", completed_tasks=25, last_active=time.time())
            coverage.add_worker(w)
        hhi = coverage.concentration_index()
        assert hhi == 2500  # 4 equal workers: (0.25^2 * 4) * 10000

    def test_concentration_index_empty(self, coverage):
        assert coverage.concentration_index() == 0.0

    def test_churn_risk_report(self, coverage):
        w1 = WorkerProfile(wallet="0xA", last_active=time.time())
        w2 = WorkerProfile(wallet="0xB", last_active=time.time() - 10 * 86400)
        w3 = WorkerProfile(wallet="0xC", last_active=time.time() - 30 * 86400)
        coverage.add_worker(w1)
        coverage.add_worker(w2)
        coverage.add_worker(w3)
        report = coverage.churn_risk_report()
        assert len(report["low"]) == 1
        assert len(report["high"]) == 1
        assert len(report["churned"]) == 1

    def test_top_performers(self, coverage):
        w1 = WorkerProfile(
            wallet="0xA", avg_rating=4.5, total_tasks=50, completed_tasks=48,
            last_active=time.time(),
        )
        w2 = WorkerProfile(
            wallet="0xB", avg_rating=3.0, total_tasks=20, completed_tasks=15,
            last_active=time.time(),
        )
        coverage.add_worker(w1)
        coverage.add_worker(w2)
        top = coverage.top_performers(limit=2)
        assert top[0].wallet == "0xA"  # Higher score

    def test_summary(self, coverage):
        w = WorkerProfile(
            wallet="0xA",
            categories=["photo"],
            locations=["Miami"],
            last_active=time.time(),
        )
        coverage.add_worker(w)
        summary = coverage.summary()
        assert summary["total_workers"] == 1
        assert summary["active_workers"] == 1
        assert "category_coverage" in summary
        assert "concentration_index" in summary


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

    def test_recommendation_to_dict(self, tracker, coverage):
        tracker.record_task(TaskDemandSignal("t1", "photo", "Miami", 5.00))
        engine = RecruitmentEngine(tracker, coverage)
        recs = engine.generate_recommendations()
        d = recs[0].to_dict()
        assert "priority" in d
        assert "target_category" in d
        assert "recommended_channels" in d


# ─── WorkerDiscovery (Unified) ────────────────────────────────


class TestWorkerDiscovery:

    def test_record_task(self, discovery):
        signal = discovery.record_task("t1", "photo", "Miami", 5.00)
        assert isinstance(signal, TaskDemandSignal)
        summary = discovery.demand_summary()
        assert summary["total_tasks"] == 1

    def test_add_worker(self, discovery):
        profile = discovery.add_worker(
            "0xAlice",
            name="Alice",
            categories=["photo"],
            locations=["Miami"],
        )
        assert isinstance(profile, WorkerProfile)
        summary = discovery.coverage_summary()
        assert summary["total_workers"] == 1

    def test_remove_worker(self, discovery):
        discovery.add_worker("0xAlice")
        discovery.remove_worker("0xAlice")
        assert discovery.coverage_summary()["total_workers"] == 0

    def test_update_worker_activity(self, discovery):
        discovery.add_worker("0xAlice")
        discovery.update_worker_activity("0xAlice")
        worker = discovery._coverage_map.get_worker("0xAlice")
        assert worker.is_active

    def test_record_full_lifecycle(self, discovery):
        discovery.record_task("t1", "photo", "Miami", 5.00)
        discovery.record_assignment("t1", "0xAlice", 3600)
        discovery.record_completion("t1")
        # Should be tracked
        demand = discovery.demand_summary()
        assert demand["total_tasks"] == 1

    def test_identify_gaps(self, populated_discovery):
        gaps = populated_discovery.identify_gaps()
        assert len(gaps) > 0
        # Survey and delivery in NYC should have gaps (no workers)
        categories_with_gaps = [g.category for g in gaps]
        assert "survey" in categories_with_gaps or "delivery" in categories_with_gaps

    def test_get_recommendations(self, populated_discovery):
        recs = populated_discovery.get_recommendations()
        assert len(recs) > 0
        assert recs[0].priority == 1

    def test_worker_concentration(self, populated_discovery):
        hhi = populated_discovery.worker_concentration()
        assert hhi > 0  # We have workers with completed tasks

    def test_churn_risk(self, populated_discovery):
        risk = populated_discovery.churn_risk()
        assert "low" in risk
        assert isinstance(risk["low"], int)

    def test_top_performers(self, populated_discovery):
        top = populated_discovery.top_performers(limit=3)
        assert len(top) > 0
        assert "wallet" in top[0]

    def test_supply_report(self, populated_discovery):
        report = populated_discovery.supply_report()
        assert "health" in report
        assert "supply_ratio" in report
        assert "gaps" in report
        assert "recommendations" in report
        assert "concentration_index" in report
        assert "churn_risk" in report

    def test_supply_report_no_data(self, discovery):
        report = discovery.supply_report()
        assert report["health"] == "no_data"

    def test_supply_report_no_supply(self, discovery):
        discovery.record_task("t1", "photo", "Miami", 5.00)
        report = discovery.supply_report()
        assert report["health"] == "no_supply"

    def test_diagnostic_report(self, populated_discovery):
        report = populated_discovery.diagnostic_report()
        assert "WORKER DISCOVERY" in report
        assert "Health" in report

    def test_diagnostic_report_empty(self, discovery):
        report = discovery.diagnostic_report()
        assert "WORKER DISCOVERY" in report


# ─── CoverageGap ─────────────────────────────────────────────


class TestCoverageGap:

    def test_to_dict(self):
        gap = CoverageGap(
            category="photo",
            location="Miami",
            demand_count=10,
            available_workers=1,
            avg_time_to_assign_seconds=3600,
            expiry_rate=0.30,
            severity="high",
            recommendation="Need more workers",
            estimated_weekly_tasks=5.0,
            avg_bounty_usd=5.00,
        )
        d = gap.to_dict()
        assert d["category"] == "photo"
        assert d["avg_time_to_assign_hours"] == 1.0
        assert d["expiry_rate_pct"] == 30.0


# ─── RECRUITMENT_CHANNELS ────────────────────────────────────


class TestRecruitmentChannels:

    def test_known_categories_have_channels(self):
        for cat in ["physical_verification", "delivery", "data_collection",
                     "survey", "mystery_shopping", "content_creation"]:
            assert cat in RECRUITMENT_CHANNELS
            assert len(RECRUITMENT_CHANNELS[cat]) > 0

    def test_default_channels_exist(self):
        assert "default" in RECRUITMENT_CHANNELS
        assert "execution.market" in RECRUITMENT_CHANNELS["default"]


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
