"""
Tests for WorkerDiscovery — Active Worker Recruitment & Supply Intelligence
============================================================================

Covers:
  - WorkerProfile: completion rate, is_active, churn_risk, to_dict
  - TaskDemandSignal: data model
  - TaskDemandTracker: recording, demand queries, velocity, expiry rate
  - WorkerCoverageMap: CRUD, coverage queries, concentration, churn, top performers
  - CoverageGap + RecruitmentRecommendation: data models, serialization
  - RecruitmentEngine: gap identification, severity calculation, recommendations
  - WorkerDiscovery (unified): full workflow, supply report, diagnostics
"""

import time
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "swarm"))

from worker_discovery import (
    WorkerProfile,
    TaskDemandSignal,
    TaskDemandTracker,
    WorkerCoverageMap,
    CoverageGap,
    RecruitmentRecommendation,
    RecruitmentEngine,
    WorkerDiscovery,
    RECRUITMENT_CHANNELS,
)


# ─── Helpers ─────────────────────────────────────────────────


def make_worker(
    wallet="0xAAA",
    name="Worker A",
    categories=None,
    locations=None,
    total_tasks=10,
    completed_tasks=8,
    avg_rating=4.5,
    last_active=None,
):
    return WorkerProfile(
        wallet=wallet,
        name=name,
        categories=categories or ["physical_verification"],
        locations=locations or ["Miami"],
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        avg_rating=avg_rating,
        last_active=last_active or time.time(),
    )


def make_signal(
    task_id="t1",
    category="physical_verification",
    location="Miami",
    bounty=5.0,
    status="open",
    created_at=None,
):
    return TaskDemandSignal(
        task_id=task_id,
        category=category,
        location=location,
        bounty_usd=bounty,
        status=status,
        created_at=created_at or time.time(),
    )


# ═══════════════════════════════════════════════════════════════
# WorkerProfile
# ═══════════════════════════════════════════════════════════════


class TestWorkerProfile:
    def test_completion_rate_normal(self):
        w = make_worker(total_tasks=10, completed_tasks=8)
        assert w.completion_rate == 0.8

    def test_completion_rate_zero_tasks(self):
        w = make_worker(total_tasks=0, completed_tasks=0)
        assert w.completion_rate == 0.0

    def test_is_active_recent(self):
        w = make_worker(last_active=time.time())
        assert w.is_active is True

    def test_is_active_stale(self):
        w = make_worker(last_active=time.time() - 8 * 86400)  # 8 days ago
        assert w.is_active is False

    def test_churn_risk_low(self):
        w = make_worker(last_active=time.time() - 86400)  # 1 day ago
        assert w.churn_risk == "low"

    def test_churn_risk_medium(self):
        w = make_worker(last_active=time.time() - 5 * 86400)  # 5 days
        assert w.churn_risk == "medium"

    def test_churn_risk_high(self):
        w = make_worker(last_active=time.time() - 10 * 86400)  # 10 days
        assert w.churn_risk == "high"

    def test_churn_risk_churned(self):
        w = make_worker(last_active=time.time() - 20 * 86400)  # 20 days
        assert w.churn_risk == "churned"

    def test_days_since_active(self):
        w = make_worker(last_active=time.time() - 3 * 86400)
        assert abs(w.days_since_active - 3.0) < 0.1

    def test_days_since_active_never(self):
        w = WorkerProfile(wallet="0xNEVER", last_active=0)
        assert w.days_since_active == float("inf")

    def test_to_dict(self):
        w = make_worker()
        d = w.to_dict()
        assert d["wallet"] == "0xAAA"
        assert d["is_active"] is True
        assert "completion_rate" in d
        assert "churn_risk" in d


# ═══════════════════════════════════════════════════════════════
# TaskDemandTracker
# ═══════════════════════════════════════════════════════════════


class TestTaskDemandTracker:
    def test_record_task(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal())
        assert len(tracker._signals) == 1

    def test_category_demand(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1", category="delivery"))
        tracker.record_task(make_signal(task_id="t2", category="delivery"))
        tracker.record_task(make_signal(task_id="t3", category="survey"))
        demand = tracker.category_demand()
        assert demand["delivery"] == 2
        assert demand["survey"] == 1

    def test_location_demand(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1", location="Miami"))
        tracker.record_task(make_signal(task_id="t2", location="NYC"))
        tracker.record_task(make_signal(task_id="t3", location="Miami"))
        demand = tracker.location_demand()
        assert demand["Miami"] == 2
        assert demand["NYC"] == 1

    def test_record_assignment(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1"))
        tracker.record_assignment("t1", "0xWORKER", 3600.0)
        assert tracker._signals[0].status == "assigned"
        assert tracker._signals[0].worker_wallet == "0xWORKER"
        assert tracker._signals[0].time_to_assign_seconds == 3600.0

    def test_record_completion(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1"))
        tracker.record_completion("t1")
        assert tracker._signals[0].status == "completed"

    def test_record_expiry(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1"))
        tracker.record_expiry("t1")
        assert tracker._signals[0].status == "expired"

    def test_avg_time_to_assign(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1"))
        tracker.record_task(make_signal(task_id="t2"))
        tracker.record_assignment("t1", "w1", 1000.0)
        tracker.record_assignment("t2", "w2", 3000.0)
        avg = tracker.avg_time_to_assign()
        assert avg == 2000.0

    def test_avg_time_to_assign_no_assignments(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1"))
        assert tracker.avg_time_to_assign() == 0.0

    def test_expiry_rate(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1"))
        tracker.record_task(make_signal(task_id="t2"))
        tracker.record_task(make_signal(task_id="t3"))
        tracker.record_completion("t1")
        tracker.record_expiry("t2")
        # t3 still open, so only t1+t2 are terminal
        rate = tracker.expiry_rate()
        assert rate == 0.5  # 1 expired / 2 terminal

    def test_expiry_rate_no_terminal(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1"))
        assert tracker.expiry_rate() == 0.0

    def test_avg_bounty(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1", bounty=3.0))
        tracker.record_task(make_signal(task_id="t2", bounty=7.0))
        assert tracker.avg_bounty() == 5.0

    def test_avg_bounty_by_category(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1", category="delivery", bounty=3.0))
        tracker.record_task(make_signal(task_id="t2", category="survey", bounty=1.0))
        assert tracker.avg_bounty(category="delivery") == 3.0

    def test_demand_velocity(self):
        tracker = TaskDemandTracker()
        now = time.time()
        # 7 tasks over 7 days = 7/week
        for i in range(7):
            tracker.record_task(
                make_signal(task_id=f"t{i}", created_at=now - i * 86400)
            )
        velocity = tracker.demand_velocity()
        assert abs(velocity - 7.0) < 2.0  # ~7 per week (tolerance for timing)

    def test_demand_velocity_empty(self):
        tracker = TaskDemandTracker()
        assert tracker.demand_velocity() == 0.0

    def test_window_filtering(self):
        tracker = TaskDemandTracker(window_days=7)
        now = time.time()
        # One recent, one old
        tracker.record_task(make_signal(task_id="t1", created_at=now))
        tracker.record_task(make_signal(task_id="t2", created_at=now - 10 * 86400))
        demand = tracker.category_demand()
        assert sum(demand.values()) == 1  # Only recent signal

    def test_max_signals_trimming(self):
        tracker = TaskDemandTracker(max_signals=5)
        for i in range(10):
            tracker.record_task(make_signal(task_id=f"t{i}"))
        assert len(tracker._signals) == 5

    def test_summary(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1", bounty=5.0))
        summary = tracker.summary()
        assert summary["total_tasks"] == 1
        assert "categories" in summary
        assert "locations" in summary

    def test_category_location_demand(self):
        tracker = TaskDemandTracker()
        tracker.record_task(make_signal(task_id="t1", category="delivery", location="Miami"))
        tracker.record_task(make_signal(task_id="t2", category="delivery", location="NYC"))
        demand = tracker.category_location_demand()
        assert demand[("delivery", "Miami")] == 1
        assert demand[("delivery", "NYC")] == 1


# ═══════════════════════════════════════════════════════════════
# WorkerCoverageMap
# ═══════════════════════════════════════════════════════════════


class TestWorkerCoverageMap:
    def test_add_and_get(self):
        cmap = WorkerCoverageMap()
        w = make_worker()
        cmap.add_worker(w)
        assert cmap.get_worker("0xAAA") is not None
        assert cmap.total_workers == 1

    def test_remove(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker())
        cmap.remove_worker("0xAAA")
        assert cmap.total_workers == 0
        assert cmap.get_worker("0xAAA") is None

    def test_remove_nonexistent(self):
        cmap = WorkerCoverageMap()
        cmap.remove_worker("0xNONE")  # Should not raise

    def test_active_workers(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", last_active=time.time()))
        cmap.add_worker(make_worker(wallet="0xB", last_active=time.time() - 10 * 86400))
        assert cmap.active_workers == 1

    def test_workers_for_category(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", categories=["delivery"]))
        cmap.add_worker(make_worker(wallet="0xB", categories=["survey"]))
        result = cmap.workers_for_category("delivery")
        assert len(result) == 1
        assert result[0].wallet == "0xA"

    def test_workers_for_location(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", locations=["Miami"]))
        cmap.add_worker(make_worker(wallet="0xB", locations=["NYC"]))
        result = cmap.workers_for_location("Miami")
        assert len(result) == 1

    def test_workers_for_category_location(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", categories=["delivery"], locations=["Miami"]))
        cmap.add_worker(make_worker(wallet="0xB", categories=["delivery"], locations=["NYC"]))
        result = cmap.workers_for_category_location("delivery", "Miami")
        assert len(result) == 1

    def test_category_coverage(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", categories=["delivery", "survey"]))
        cmap.add_worker(make_worker(wallet="0xB", categories=["delivery"]))
        coverage = cmap.category_coverage()
        assert coverage["delivery"] == 2
        assert coverage["survey"] == 1

    def test_location_coverage(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", locations=["Miami", "Fort Lauderdale"]))
        coverage = cmap.location_coverage()
        assert "Miami" in coverage
        assert "Fort Lauderdale" in coverage

    def test_concentration_no_workers(self):
        cmap = WorkerCoverageMap()
        assert cmap.concentration_index() == 0.0

    def test_concentration_one_worker(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", completed_tasks=100))
        # HHI = (100/100)^2 * 10000 = 10000 (maximum concentration)
        assert cmap.concentration_index() == 10000.0

    def test_concentration_equal_workers(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", completed_tasks=50))
        cmap.add_worker(make_worker(wallet="0xB", completed_tasks=50))
        # HHI = 2 * (0.5)^2 * 10000 = 5000
        assert cmap.concentration_index() == 5000.0

    def test_churn_risk_report(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", last_active=time.time()))
        cmap.add_worker(make_worker(wallet="0xB", last_active=time.time() - 20 * 86400))
        report = cmap.churn_risk_report()
        assert "0xA" in report["low"]
        assert "0xB" in report["churned"]

    def test_top_performers(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", completed_tasks=8, total_tasks=10, avg_rating=4.5))
        cmap.add_worker(make_worker(wallet="0xB", completed_tasks=10, total_tasks=10, avg_rating=5.0))
        top = cmap.top_performers(limit=2)
        # Worker B: 1.0 * 5.0 = 5.0, Worker A: 0.8 * 4.5 = 3.6
        assert top[0].wallet == "0xB"

    def test_top_performers_excludes_zero_tasks(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA", total_tasks=0, completed_tasks=0))
        top = cmap.top_performers()
        assert len(top) == 0

    def test_all_workers(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA"))
        cmap.add_worker(make_worker(wallet="0xB"))
        assert len(cmap.all_workers()) == 2

    def test_summary(self):
        cmap = WorkerCoverageMap()
        cmap.add_worker(make_worker(wallet="0xA"))
        summary = cmap.summary()
        assert summary["total_workers"] == 1
        assert "category_coverage" in summary
        assert "concentration_index" in summary


# ═══════════════════════════════════════════════════════════════
# RecruitmentEngine
# ═══════════════════════════════════════════════════════════════


class TestRecruitmentEngine:
    def _setup_engine(self):
        tracker = TaskDemandTracker()
        coverage = WorkerCoverageMap()
        engine = RecruitmentEngine(tracker, coverage)
        return tracker, coverage, engine

    def test_no_gaps_empty(self):
        _, _, engine = self._setup_engine()
        gaps = engine.identify_gaps()
        assert len(gaps) == 0

    def test_gap_no_workers(self):
        tracker, coverage, engine = self._setup_engine()
        tracker.record_task(make_signal(task_id="t1", category="delivery", location="Miami"))
        # No workers added → gap
        gaps = engine.identify_gaps()
        assert len(gaps) == 1
        assert gaps[0].category == "delivery"
        assert gaps[0].available_workers == 0
        assert gaps[0].severity == "critical"

    def test_gap_with_workers(self):
        tracker, coverage, engine = self._setup_engine()
        tracker.record_task(make_signal(task_id="t1", category="delivery", location="Miami"))
        coverage.add_worker(make_worker(wallet="0xA", categories=["delivery"], locations=["Miami"]))
        gaps = engine.identify_gaps()
        assert len(gaps) == 1
        assert gaps[0].available_workers == 1

    def test_severity_critical_no_workers(self):
        tracker, coverage, engine = self._setup_engine()
        tracker.record_task(make_signal(task_id="t1"))
        gaps = engine.identify_gaps()
        assert gaps[0].severity == "critical"

    def test_severity_high_expiry(self):
        tracker, coverage, engine = self._setup_engine()
        # 3 tasks, 2 expired = 66% expiry
        for i in range(3):
            tracker.record_task(make_signal(task_id=f"t{i}"))
        tracker.record_completion("t0")
        tracker.record_expiry("t1")
        tracker.record_expiry("t2")
        coverage.add_worker(make_worker(wallet="0xA"))
        gaps = engine.identify_gaps()
        assert gaps[0].severity in ("critical", "high")

    def test_recommendations_ordered_by_priority(self):
        tracker, coverage, engine = self._setup_engine()
        tracker.record_task(make_signal(task_id="t1", category="delivery", location="Miami"))
        tracker.record_task(make_signal(task_id="t2", category="survey", location="NYC"))
        recs = engine.generate_recommendations()
        assert len(recs) == 2
        assert recs[0].priority == 1
        assert recs[1].priority == 2

    def test_recommendations_includes_channels(self):
        tracker, coverage, engine = self._setup_engine()
        tracker.record_task(make_signal(task_id="t1", category="delivery", location="Miami"))
        recs = engine.generate_recommendations()
        assert len(recs[0].recommended_channels) > 0

    def test_recommendations_max_count(self):
        tracker, coverage, engine = self._setup_engine()
        for i in range(20):
            tracker.record_task(make_signal(task_id=f"t{i}", category=f"cat_{i}", location="remote"))
        recs = engine.generate_recommendations(max_count=3)
        assert len(recs) == 3

    def test_competition_level_none(self):
        tracker, coverage, engine = self._setup_engine()
        tracker.record_task(make_signal(task_id="t1"))
        recs = engine.generate_recommendations()
        assert recs[0].competition_level == "none"

    def test_competition_level_low(self):
        tracker, coverage, engine = self._setup_engine()
        tracker.record_task(make_signal(task_id="t1"))
        coverage.add_worker(make_worker(wallet="0xA"))
        recs = engine.generate_recommendations()
        assert recs[0].competition_level == "low"

    def test_gap_to_dict(self):
        gap = CoverageGap(
            category="delivery",
            location="Miami",
            demand_count=10,
            available_workers=1,
            avg_time_to_assign_seconds=3600,
            expiry_rate=0.3,
            severity="high",
            recommendation="Need more workers",
            estimated_weekly_tasks=5.0,
            avg_bounty_usd=5.0,
        )
        d = gap.to_dict()
        assert d["category"] == "delivery"
        assert d["avg_time_to_assign_hours"] == 1.0
        assert d["expiry_rate_pct"] == 30.0

    def test_recommendation_to_dict(self):
        rec = RecruitmentRecommendation(
            priority=1,
            target_category="delivery",
            target_location="Miami",
            reason="No workers",
            estimated_weekly_earnings_usd=25.0,
            competition_level="none",
            recommended_channels=["execution.market"],
        )
        d = rec.to_dict()
        assert d["priority"] == 1
        assert d["estimated_weekly_earnings_usd"] == 25.0


# ═══════════════════════════════════════════════════════════════
# WorkerDiscovery (Unified)
# ═══════════════════════════════════════════════════════════════


class TestWorkerDiscovery:
    def test_record_task(self):
        wd = WorkerDiscovery()
        signal = wd.record_task("t1", "delivery", "Miami", 5.0)
        assert signal.task_id == "t1"
        assert signal.category == "delivery"

    def test_add_worker(self):
        wd = WorkerDiscovery()
        profile = wd.add_worker("0xAAA", categories=["delivery"], locations=["Miami"])
        assert profile.wallet == "0xAAA"

    def test_update_worker_activity(self):
        wd = WorkerDiscovery()
        wd.add_worker("0xAAA")
        time.sleep(0.01)
        wd.update_worker_activity("0xAAA")
        w = wd._coverage_map.get_worker("0xAAA")
        assert w.is_active is True

    def test_remove_worker(self):
        wd = WorkerDiscovery()
        wd.add_worker("0xAAA")
        wd.remove_worker("0xAAA")
        assert wd._coverage_map.total_workers == 0

    def test_identify_gaps(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami", 5.0)
        gaps = wd.identify_gaps()
        assert len(gaps) == 1

    def test_get_recommendations(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami")
        recs = wd.get_recommendations()
        assert len(recs) == 1

    def test_demand_summary(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami", 5.0)
        summary = wd.demand_summary()
        assert summary["total_tasks"] == 1

    def test_coverage_summary(self):
        wd = WorkerDiscovery()
        wd.add_worker("0xA", categories=["delivery"])
        summary = wd.coverage_summary()
        assert summary["total_workers"] == 1

    def test_worker_concentration(self):
        wd = WorkerDiscovery()
        wd.add_worker("0xA", total_tasks=50, completed_tasks=50)
        wd.add_worker("0xB", total_tasks=50, completed_tasks=50)
        hhi = wd.worker_concentration()
        assert hhi == 5000.0

    def test_churn_risk(self):
        wd = WorkerDiscovery()
        wd.add_worker("0xA")
        risk = wd.churn_risk()
        assert risk["low"] == 1

    def test_top_performers(self):
        wd = WorkerDiscovery()
        wd.add_worker("0xA", total_tasks=10, completed_tasks=10, avg_rating=5.0)
        top = wd.top_performers(limit=1)
        assert len(top) == 1
        assert top[0]["wallet"] == "0xA"

    def test_supply_report_no_data(self):
        wd = WorkerDiscovery()
        report = wd.supply_report()
        assert report["health"] == "no_data"

    def test_supply_report_healthy(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami")
        wd.add_worker("0xA", categories=["delivery"], locations=["Miami"])
        wd.add_worker("0xB", categories=["delivery"], locations=["Miami"])
        report = wd.supply_report()
        assert report["health"] == "healthy"

    def test_supply_report_no_supply(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami")
        report = wd.supply_report()
        assert report["health"] == "no_supply"

    def test_supply_report_strained(self):
        wd = WorkerDiscovery()
        for i in range(4):
            wd.record_task(f"t{i}", "delivery", "Miami")
        wd.add_worker("0xA", categories=["delivery"], locations=["Miami"])
        wd.add_worker("0xB", categories=["delivery"], locations=["Miami"])
        report = wd.supply_report()
        assert report["health"] in ("strained", "healthy")

    def test_supply_report_has_gaps(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami")
        report = wd.supply_report()
        assert report["gaps"]["total"] == 1
        assert report["gaps"]["critical"] >= 1

    def test_supply_report_has_recommendations(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami")
        report = wd.supply_report()
        assert len(report["recommendations"]) > 0

    def test_diagnostic_report_string(self):
        wd = WorkerDiscovery()
        wd.record_task("t1", "delivery", "Miami")
        wd.add_worker("0xA", categories=["delivery"], locations=["Miami"])
        report = wd.diagnostic_report()
        assert "WORKER DISCOVERY" in report
        assert "Health" in report

    def test_full_lifecycle(self):
        """Test the complete task lifecycle through discovery."""
        wd = WorkerDiscovery()

        # Add workers
        wd.add_worker("0xA", categories=["physical_verification"], locations=["Miami"])

        # Create tasks
        wd.record_task("t1", "physical_verification", "Miami", 5.0)
        wd.record_task("t2", "physical_verification", "Miami", 3.0)

        # Assignment
        wd.record_assignment("t1", "0xA", 1800.0)  # 30 minutes

        # Completion
        wd.record_completion("t1")

        # Expiry
        wd.record_expiry("t2")

        # Check intelligence
        report = wd.supply_report()
        assert report["demand"]["total_tasks"] == 2
        assert report["coverage"]["total_workers"] == 1


# ═══════════════════════════════════════════════════════════════
# Recruitment Channels
# ═══════════════════════════════════════════════════════════════


class TestRecruitmentChannels:
    def test_channels_for_known_category(self):
        assert "delivery" in RECRUITMENT_CHANNELS
        assert len(RECRUITMENT_CHANNELS["delivery"]) > 0

    def test_default_channels_exist(self):
        assert "default" in RECRUITMENT_CHANNELS
        assert "execution.market" in RECRUITMENT_CHANNELS["default"]

    def test_all_categories_have_channels(self):
        expected = [
            "physical_verification", "delivery", "data_collection",
            "survey", "mystery_shopping", "quality_assurance", "content_creation",
        ]
        for cat in expected:
            assert cat in RECRUITMENT_CHANNELS, f"Missing channels for {cat}"
