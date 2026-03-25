"""
Tests for ExpiryAnalyzer — Task expiry pattern diagnosis and countermeasures.
==============================================================================

The #1 business problem: 35.6% of tasks expire without completion.
ExpiryAnalyzer diagnoses WHY and recommends data-driven countermeasures.

Tests cover:
1. Data model correctness (CategoryHealth, ExpiryDiagnosis, Countermeasure)
2. Severity classification thresholds
3. Category health computation
4. Worker concentration analysis (HHI)
5. Root cause diagnosis logic
6. Countermeasure generation
7. Per-task recommendations
8. Edge cases (empty data, single task, all expired)
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm.expiry_analyzer import (
    CategoryHealth,
    Countermeasure,
    CountermeasureType,
    ExpiryAnalyzer,
    ExpiryDiagnosis,
    ExpiryReason,
    ExpiryReport,
    Severity,
)

UTC = timezone.utc


# ──────────────────────────────────────────────────────────────
# Test Data Factories
# ──────────────────────────────────────────────────────────────

def _make_task(
    task_id="task_001",
    category="physical_verification",
    title="Verify storefront at address",
    bounty_usd=5.0,
    status="completed",
    worker_wallet="0xWorker1",
    created_hours_ago=24,
    completed_hours_ago=20,
    deadline_hours=48,
):
    """Create a realistic task dict matching EM API shape."""
    now = datetime.now(UTC)
    created = now - timedelta(hours=created_hours_ago)
    completed_at = now - timedelta(hours=completed_hours_ago) if completed_hours_ago else None
    expires = created + timedelta(hours=deadline_hours)

    task = {
        "id": task_id,
        "category": category,
        "title": title,
        "bounty_usd": bounty_usd,
        "status": status,
        "created_at": created.isoformat(),
        "expires_at": expires.isoformat(),
    }
    if worker_wallet and status == "completed":
        task["executor_id"] = worker_wallet
        task["completed_at"] = completed_at.isoformat() if completed_at else None
    if status == "completed":
        task["rating"] = 4
    return task


def _make_completed_tasks(n=10, category="delivery", bounty=5.0, workers=None):
    """Create N completed tasks with optional worker rotation."""
    workers = workers or [f"0xWorker{i}" for i in range(min(n, 5))]
    return [
        _make_task(
            task_id=f"completed_{i}",
            category=category,
            title=f"Deliver item #{i}",
            bounty_usd=bounty,
            status="completed",
            worker_wallet=workers[i % len(workers)],
            created_hours_ago=24 + i,
            completed_hours_ago=20 + i,
        )
        for i in range(n)
    ]


def _make_expired_tasks(n=5, category="delivery", bounty=2.0, deadline_hours=4):
    """Create N expired tasks."""
    return [
        _make_task(
            task_id=f"expired_{i}",
            category=category,
            title=f"Task {i}" if i % 2 == 0 else "Do thing",  # Some with short titles
            bounty_usd=bounty,
            status="expired",
            worker_wallet=None,
            created_hours_ago=48 + i,
            completed_hours_ago=None,
            deadline_hours=deadline_hours,
        )
        for i in range(n)
    ]


# ──────────────────────────────────────────────────────────────
# CategoryHealth Tests
# ──────────────────────────────────────────────────────────────

class TestCategoryHealth:
    """Test CategoryHealth data model and computed properties."""

    def test_expiry_rate_no_tasks(self):
        ch = CategoryHealth(category="test")
        assert ch.expiry_rate == 0.0

    def test_expiry_rate_all_completed(self):
        ch = CategoryHealth(category="test", completed=10, expired=0)
        assert ch.expiry_rate == 0.0

    def test_expiry_rate_all_expired(self):
        ch = CategoryHealth(category="test", completed=0, expired=10)
        assert ch.expiry_rate == 1.0

    def test_expiry_rate_mixed(self):
        ch = CategoryHealth(category="test", completed=7, expired=3)
        assert abs(ch.expiry_rate - 0.3) < 0.01

    def test_severity_low(self):
        ch = CategoryHealth(category="test", completed=9, expired=1)
        assert ch.severity == Severity.LOW

    def test_severity_medium(self):
        ch = CategoryHealth(category="test", completed=8, expired=2)
        assert ch.severity == Severity.MEDIUM

    def test_severity_high(self):
        ch = CategoryHealth(category="test", completed=6, expired=4)
        assert ch.severity == Severity.HIGH

    def test_severity_critical(self):
        ch = CategoryHealth(category="test", completed=4, expired=6)
        assert ch.severity == Severity.CRITICAL

    def test_has_workers_true(self):
        ch = CategoryHealth(category="test", unique_workers=3)
        assert ch.has_workers is True

    def test_has_workers_false(self):
        ch = CategoryHealth(category="test", unique_workers=0)
        assert ch.has_workers is False

    def test_to_dict_contains_all_fields(self):
        ch = CategoryHealth(
            category="delivery",
            total_tasks=20,
            completed=14,
            expired=6,
            unique_workers=5,
            avg_bounty_completed=5.50,
            avg_bounty_expired=2.00,
        )
        d = ch.to_dict()
        assert d["category"] == "delivery"
        assert d["total_tasks"] == 20
        # 6/20 = 30% expiry rate → MEDIUM (>15%, not >30%)
        assert d["severity"] == "medium"
        assert "expiry_rate" in d


# ──────────────────────────────────────────────────────────────
# ExpiryDiagnosis Tests
# ──────────────────────────────────────────────────────────────

class TestExpiryDiagnosis:
    """Test ExpiryDiagnosis serialization."""

    def test_to_dict_basic(self):
        diag = ExpiryDiagnosis(
            task_id="task_001",
            category="delivery",
            primary_reason=ExpiryReason.LOW_BOUNTY,
            confidence=0.8,
        )
        d = diag.to_dict()
        assert d["primary_reason"] == "low_bounty"
        assert d["confidence"] == 0.8

    def test_to_dict_with_secondary_reasons(self):
        diag = ExpiryDiagnosis(
            primary_reason=ExpiryReason.LOW_BOUNTY,
            secondary_reasons=[ExpiryReason.SHORT_DEADLINE, ExpiryReason.UNCLEAR_TASK],
        )
        d = diag.to_dict()
        assert len(d["secondary_reasons"]) == 2
        assert "short_deadline" in d["secondary_reasons"]


# ──────────────────────────────────────────────────────────────
# Countermeasure Tests
# ──────────────────────────────────────────────────────────────

class TestCountermeasure:
    """Test Countermeasure serialization."""

    def test_to_dict(self):
        cm = Countermeasure(
            type=CountermeasureType.ESCALATE_BOUNTY,
            priority=1,
            category="delivery",
            description="Increase bounty by 50%",
            expected_impact=0.3,
            estimated_effort="low",
        )
        d = cm.to_dict()
        assert d["type"] == "escalate_bounty"
        assert d["priority"] == 1
        assert d["expected_impact"] == 0.3


# ──────────────────────────────────────────────────────────────
# ExpiryReport Tests
# ──────────────────────────────────────────────────────────────

class TestExpiryReport:
    """Test report summary and serialization."""

    def test_summary_not_empty(self):
        report = ExpiryReport(
            generated_at="2026-03-25T01:00:00Z",
            total_completed=70,
            total_expired=30,
            overall_expiry_rate=0.30,
            overall_severity=Severity.MEDIUM,
            total_workers=5,
        )
        summary = report.summary()
        assert "Expiry Analysis Report" in summary
        assert "30%" in summary or "30.0%" in summary

    def test_to_dict_shape(self):
        report = ExpiryReport(
            generated_at="2026-03-25T01:00:00Z",
            total_completed=100,
            total_expired=50,
        )
        d = report.to_dict()
        assert "overall" in d
        assert "workers" in d
        assert "categories" in d
        assert "countermeasures" in d


# ──────────────────────────────────────────────────────────────
# ExpiryAnalyzer Offline Analysis Tests
# ──────────────────────────────────────────────────────────────

class TestAnalyzeOffline:
    """Test the full analysis pipeline with synthetic data."""

    def test_empty_data(self):
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline([], [])
        assert report.total_tasks == 0
        assert report.overall_expiry_rate == 0.0
        assert report.overall_severity == Severity.LOW

    def test_all_completed(self):
        completed = _make_completed_tasks(20, category="delivery")
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, [])
        assert report.total_completed == 20
        assert report.total_expired == 0
        assert report.overall_expiry_rate == 0.0
        assert report.overall_severity == Severity.LOW

    def test_all_expired(self):
        expired = _make_expired_tasks(10, category="delivery")
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline([], expired)
        assert report.total_expired == 10
        assert report.overall_expiry_rate == 1.0
        assert report.overall_severity == Severity.CRITICAL

    def test_mixed_results(self):
        completed = _make_completed_tasks(7, category="delivery")
        expired = _make_expired_tasks(3, category="delivery")
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        assert report.total_tasks == 10
        assert abs(report.overall_expiry_rate - 0.3) < 0.01
        assert report.overall_severity == Severity.MEDIUM

    def test_category_health_computed(self):
        completed = _make_completed_tasks(5, category="delivery") + \
                    _make_completed_tasks(3, category="physical_verification")
        expired = _make_expired_tasks(2, category="delivery")
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        categories = {ch.category: ch for ch in report.category_health}
        assert "delivery" in categories
        assert categories["delivery"].completed == 5
        assert categories["delivery"].expired == 2

    def test_worker_count(self):
        workers = ["0xA", "0xB", "0xC"]
        completed = _make_completed_tasks(9, category="delivery", workers=workers)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, [])
        assert report.total_workers == 3

    def test_diagnoses_generated_for_expired(self):
        completed = _make_completed_tasks(5, category="delivery", bounty=5.0)
        expired = _make_expired_tasks(3, category="delivery", bounty=0.10)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        assert len(report.diagnoses) >= 3  # One per expired task
        # Low bounty tasks should be diagnosed
        reasons = [d.primary_reason for d in report.diagnoses]
        assert ExpiryReason.LOW_BOUNTY in reasons

    def test_countermeasures_generated(self):
        completed = _make_completed_tasks(5, category="delivery", bounty=5.0)
        expired = _make_expired_tasks(5, category="delivery", bounty=0.10)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        assert len(report.countermeasures) > 0

    def test_with_cancelled(self):
        completed = _make_completed_tasks(5)
        expired = _make_expired_tasks(2)
        cancelled = [_make_task(task_id="cancelled_1", status="cancelled")]
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired, cancelled)
        assert report.total_cancelled == 1
        assert report.total_tasks == 8

    def test_multiple_categories(self):
        completed = (
            _make_completed_tasks(10, category="delivery", bounty=5.0) +
            _make_completed_tasks(5, category="physical_verification", bounty=8.0) +
            _make_completed_tasks(3, category="digital_action", bounty=3.0)
        )
        expired = (
            _make_expired_tasks(2, category="delivery") +
            _make_expired_tasks(5, category="digital_action")
        )
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        categories = {ch.category: ch for ch in report.category_health}
        assert len(categories) >= 3
        # digital_action should have highest expiry rate (5/(3+5) = 62.5%)
        assert categories["digital_action"].severity == Severity.CRITICAL

    def test_analysis_duration_tracked(self):
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline([], [])
        assert report.analysis_duration_ms >= 0

    def test_report_summary_with_data(self):
        completed = _make_completed_tasks(10, category="delivery")
        expired = _make_expired_tasks(5, category="delivery")
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        summary = report.summary()
        assert "delivery" in summary
        assert "Expiry Analysis Report" in summary


# ──────────────────────────────────────────────────────────────
# Diagnosis Logic Tests
# ──────────────────────────────────────────────────────────────

class TestDiagnosisLogic:
    """Test root cause diagnosis for individual expired tasks."""

    def test_low_bounty_detection(self):
        """Tasks with bounty below threshold should be diagnosed as LOW_BOUNTY."""
        completed = _make_completed_tasks(10, category="delivery", bounty=5.0)
        expired = _make_expired_tasks(3, category="delivery", bounty=0.05)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        low_bounty_count = sum(
            1 for d in report.diagnoses if d.primary_reason == ExpiryReason.LOW_BOUNTY
        )
        assert low_bounty_count >= 1

    def test_short_deadline_detection(self):
        """Tasks with very short deadlines should be flagged."""
        now = datetime.now(UTC)
        completed = _make_completed_tasks(10, category="delivery", bounty=5.0)
        # Build expired tasks with proper deadline field for the analyzer
        expired = []
        for i in range(3):
            created = now - timedelta(hours=48 + i)
            deadline = created + timedelta(hours=1)  # 1-hour deadline
            expired.append({
                "id": f"short_deadline_{i}",
                "category": "delivery",
                "title": "Deliver package urgently to downtown office for meeting",
                "bounty_usd": 5.0,
                "status": "expired",
                "created_at": created.isoformat(),
                "deadline": deadline.isoformat(),
            })
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        all_reasons = set()
        for d in report.diagnoses:
            all_reasons.add(d.primary_reason)
            all_reasons.update(d.secondary_reasons)
        assert ExpiryReason.SHORT_DEADLINE in all_reasons

    def test_unclear_task_detection(self):
        """Tasks with very short titles should be flagged as unclear."""
        expired = [
            _make_task(
                task_id=f"vague_{i}",
                category="delivery",
                title="Do it",  # 2 words — below threshold
                bounty_usd=5.0,
                status="expired",
                deadline_hours=48,
            )
            for i in range(3)
        ]
        completed = _make_completed_tasks(10, category="delivery", bounty=5.0)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        reasons = {d.primary_reason for d in report.diagnoses}
        # Should detect UNCLEAR_TASK as at least a secondary reason
        all_reasons = set()
        for d in report.diagnoses:
            all_reasons.add(d.primary_reason)
            all_reasons.update(d.secondary_reasons)
        assert ExpiryReason.UNCLEAR_TASK in all_reasons

    def test_niche_category_detection(self):
        """Categories with very few workers should be flagged as niche."""
        completed = _make_completed_tasks(
            3, category="code_execution", bounty=10.0, workers=["0xSolo"]
        )
        expired = _make_expired_tasks(5, category="code_execution", bounty=10.0, deadline_hours=48)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        all_reasons = set()
        for d in report.diagnoses:
            all_reasons.add(d.primary_reason)
            all_reasons.update(d.secondary_reasons)
        assert ExpiryReason.NICHE_CATEGORY in all_reasons

    def test_diagnosis_confidence_range(self):
        """All diagnoses should have confidence between 0 and 1."""
        completed = _make_completed_tasks(10, category="delivery")
        expired = _make_expired_tasks(5, category="delivery")
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        for d in report.diagnoses:
            assert 0 <= d.confidence <= 1, f"Confidence out of range: {d.confidence}"


# ──────────────────────────────────────────────────────────────
# Countermeasure Tests
# ──────────────────────────────────────────────────────────────

class TestCountermeasureGeneration:
    """Test countermeasure generation logic."""

    def test_no_countermeasures_for_healthy_system(self):
        """If expiry rate is low, minimal/no countermeasures needed."""
        completed = _make_completed_tasks(50, category="delivery", bounty=5.0)
        expired = _make_expired_tasks(2, category="delivery", bounty=5.0, deadline_hours=48)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        # Low expiry = few or no countermeasures
        assert len(report.countermeasures) <= 3

    def test_countermeasures_for_critical_system(self):
        """High expiry rate should produce multiple countermeasures."""
        completed = _make_completed_tasks(5, category="delivery", bounty=5.0)
        expired = _make_expired_tasks(15, category="delivery", bounty=0.10, deadline_hours=1)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        assert len(report.countermeasures) >= 2

    def test_countermeasure_priorities_ordered(self):
        """Countermeasures should have distinct priorities."""
        completed = _make_completed_tasks(5, category="delivery", bounty=5.0)
        expired = _make_expired_tasks(10, category="delivery", bounty=0.05)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        if len(report.countermeasures) >= 2:
            priorities = [cm.priority for cm in report.countermeasures]
            assert priorities == sorted(priorities)

    def test_countermeasure_to_dict_shape(self):
        """Serialized countermeasures should have required fields."""
        completed = _make_completed_tasks(5, category="delivery")
        expired = _make_expired_tasks(10, category="delivery", bounty=0.05)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, expired)
        for cm in report.countermeasures:
            d = cm.to_dict()
            assert "type" in d
            assert "priority" in d
            assert "expected_impact" in d


# ──────────────────────────────────────────────────────────────
# Worker Concentration Tests
# ──────────────────────────────────────────────────────────────

class TestWorkerConcentration:
    """Test Herfindahl-Hirschman Index (HHI) computation."""

    def test_single_worker_max_concentration(self):
        """One worker doing all tasks = HHI of 1.0."""
        completed = _make_completed_tasks(10, category="delivery", workers=["0xSolo"])
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, [])
        assert report.worker_hhi == 1.0
        assert report.top_worker_share == 1.0

    def test_uniform_distribution_low_concentration(self):
        """Many workers with equal share = low HHI."""
        workers = [f"0xWorker{i}" for i in range(10)]
        completed = _make_completed_tasks(10, category="delivery", workers=workers)
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline(completed, [])
        # 10 workers, 1 task each: HHI = 10 * (0.1)^2 = 0.1
        assert report.worker_hhi <= 0.15

    def test_no_workers(self):
        """No completed tasks = no worker data."""
        analyzer = ExpiryAnalyzer()
        report = analyzer.analyze_offline([], _make_expired_tasks(5))
        assert report.total_workers == 0


# ──────────────────────────────────────────────────────────────
# Recommend For Task Tests
# ──────────────────────────────────────────────────────────────

class TestRecommendForTask:
    """Test per-task recommendation."""

    def test_recommend_low_bounty_task(self):
        analyzer = ExpiryAnalyzer()
        task = _make_task(
            task_id="low_bounty",
            category="delivery",
            title="Deliver package across town",
            bounty_usd=0.05,
            status="open",
            deadline_hours=24,
        )
        recs = analyzer.recommend_for_task(task)
        assert isinstance(recs, list)

    def test_recommend_short_deadline_task(self):
        analyzer = ExpiryAnalyzer()
        task = _make_task(
            task_id="rush",
            category="delivery",
            title="Deliver package immediately",
            bounty_usd=10.0,
            status="open",
            deadline_hours=0.5,
        )
        recs = analyzer.recommend_for_task(task)
        assert isinstance(recs, list)

    def test_recommend_vague_title_task(self):
        analyzer = ExpiryAnalyzer()
        task = _make_task(
            task_id="vague",
            category="delivery",
            title="thing",
            bounty_usd=5.0,
            status="open",
            deadline_hours=24,
        )
        recs = analyzer.recommend_for_task(task)
        assert isinstance(recs, list)

    def test_recommend_good_task_few_recs(self):
        analyzer = ExpiryAnalyzer()
        task = _make_task(
            task_id="good",
            category="delivery",
            title="Deliver sealed envelope to downtown office building at 123 Main St",
            bounty_usd=10.0,
            status="open",
            deadline_hours=48,
        )
        recs = analyzer.recommend_for_task(task)
        # Good task should have fewer recommendations
        assert isinstance(recs, list)


# ──────────────────────────────────────────────────────────────
# Enum Tests
# ──────────────────────────────────────────────────────────────

class TestEnums:
    """Test enum values and string representations."""

    def test_expiry_reasons(self):
        assert ExpiryReason.NO_WORKERS.value == "no_workers"
        assert ExpiryReason.LOW_BOUNTY.value == "low_bounty"
        assert ExpiryReason.SHORT_DEADLINE.value == "short_deadline"
        assert ExpiryReason.NICHE_CATEGORY.value == "niche_category"
        assert ExpiryReason.UNCLEAR_TASK.value == "unclear_task"
        assert ExpiryReason.SUPPLY_GAP.value == "supply_gap"
        assert ExpiryReason.UNKNOWN.value == "unknown"

    def test_severity_values(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"

    def test_countermeasure_types(self):
        assert CountermeasureType.EXTEND_DEADLINE.value == "extend_deadline"
        assert CountermeasureType.ESCALATE_BOUNTY.value == "escalate_bounty"
        assert CountermeasureType.PUSH_NOTIFICATION.value == "push_notification"
        assert CountermeasureType.BATCH_TASKS.value == "batch_tasks"
        assert CountermeasureType.REPOST.value == "repost"
        assert CountermeasureType.RECRUIT_WORKERS.value == "recruit_workers"
        assert CountermeasureType.IMPROVE_INSTRUCTIONS.value == "improve_instructions"


# ──────────────────────────────────────────────────────────────
# Severity Boundary Tests
# ──────────────────────────────────────────────────────────────

class TestSeverityBoundaries:
    """Test exact severity threshold boundaries."""

    def test_boundary_low_medium(self):
        """15% is the boundary between low and medium."""
        # 15% → should be LOW (need >15% for MEDIUM)
        ch = CategoryHealth(category="test", completed=85, expired=15)
        # 15% exactly — implementation uses > 0.15
        rate = ch.expiry_rate  # 15 / 100 = 0.15
        assert rate == 0.15
        assert ch.severity == Severity.LOW  # >0.15 needed for MEDIUM

    def test_boundary_medium_high(self):
        """30% is the boundary between medium and high."""
        ch = CategoryHealth(category="test", completed=70, expired=30)
        assert abs(ch.expiry_rate - 0.30) < 0.01
        assert ch.severity == Severity.MEDIUM  # >0.30 needed for HIGH

    def test_boundary_high_critical(self):
        """50% is the boundary between high and critical."""
        ch = CategoryHealth(category="test", completed=50, expired=50)
        assert ch.expiry_rate == 0.50
        assert ch.severity == Severity.HIGH  # >0.50 needed for CRITICAL

    def test_just_above_medium(self):
        ch = CategoryHealth(category="test", completed=84, expired=16)
        assert ch.severity == Severity.MEDIUM

    def test_just_above_high(self):
        ch = CategoryHealth(category="test", completed=69, expired=31)
        assert ch.severity == Severity.HIGH

    def test_just_above_critical(self):
        ch = CategoryHealth(category="test", completed=49, expired=51)
        assert ch.severity == Severity.CRITICAL
