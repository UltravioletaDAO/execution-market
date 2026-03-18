"""
Tests for ExpiryAnalyzer — diagnoses task expiry patterns and recommends countermeasures.
"""

import pytest
from datetime import datetime, timezone, timedelta

from swarm.expiry_analyzer import (
    ExpiryAnalyzer,
    ExpiryReport,
    ExpiryReason,
    ExpiryDiagnosis,
    CategoryHealth,
    Countermeasure,
    CountermeasureType,
    Severity,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_task(
    task_id: str = "t1",
    category: str = "simple_action",
    bounty_usd: float = 0.10,
    status: str = "completed",
    executor_id: str = "worker-1",
    deadline_hours: float = 4.0,
    title: str = "Test task with sufficient description",
) -> dict:
    """Create a task dict for testing."""
    created = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    deadline = created + timedelta(hours=deadline_hours)
    return {
        "id": task_id,
        "title": title,
        "status": status,
        "category": category,
        "bounty_usd": bounty_usd,
        "created_at": created.isoformat(),
        "deadline": deadline.isoformat(),
        "executor_id": executor_id,
        "agent_id": "2106",
    }


def _make_completed(n: int = 10, category: str = "simple_action", worker: str = "worker-1") -> list[dict]:
    """Create N completed tasks."""
    return [
        _make_task(
            task_id=f"c-{i}",
            category=category,
            status="completed",
            executor_id=worker,
            bounty_usd=0.10 + i * 0.01,
        )
        for i in range(n)
    ]


def _make_expired(n: int = 5, category: str = "simple_action", bounty: float = 0.10) -> list[dict]:
    """Create N expired tasks."""
    return [
        _make_task(
            task_id=f"e-{i}",
            category=category,
            status="expired",
            executor_id="",
            bounty_usd=bounty,
        )
        for i in range(n)
    ]


@pytest.fixture
def analyzer():
    return ExpiryAnalyzer()


@pytest.fixture
def diverse_data():
    """Realistic diverse dataset."""
    completed = (
        _make_completed(50, "simple_action", "worker-1")
        + _make_completed(5, "physical_presence", "worker-2")
    )
    expired = (
        _make_expired(20, "simple_action", 0.10)
        + _make_expired(6, "knowledge_access", 0.02)
        + _make_expired(5, "code_execution", 0.05)
        + _make_expired(4, "research", 0.03)
    )
    cancelled = [_make_task(task_id=f"x-{i}", status="cancelled") for i in range(10)]
    return completed, expired, cancelled


# ─── CategoryHealth Tests ─────────────────────────────────────────────────────


class TestCategoryHealth:
    def test_expiry_rate_zero_when_no_tasks(self):
        ch = CategoryHealth(category="test")
        assert ch.expiry_rate == 0.0

    def test_expiry_rate_calculation(self):
        ch = CategoryHealth(category="test", completed=7, expired=3)
        assert ch.expiry_rate == pytest.approx(0.3)

    def test_severity_low(self):
        ch = CategoryHealth(category="test", completed=90, expired=10)
        assert ch.severity == Severity.LOW

    def test_severity_medium(self):
        ch = CategoryHealth(category="test", completed=75, expired=25)
        assert ch.severity == Severity.MEDIUM

    def test_severity_high(self):
        ch = CategoryHealth(category="test", completed=60, expired=40)
        assert ch.severity == Severity.HIGH

    def test_severity_critical(self):
        ch = CategoryHealth(category="test", completed=30, expired=70)
        assert ch.severity == Severity.CRITICAL

    def test_has_workers(self):
        ch = CategoryHealth(category="test", unique_workers=3)
        assert ch.has_workers is True

    def test_no_workers(self):
        ch = CategoryHealth(category="test", unique_workers=0)
        assert ch.has_workers is False

    def test_to_dict(self):
        ch = CategoryHealth(
            category="simple_action",
            completed=100,
            expired=20,
            unique_workers=3,
        )
        d = ch.to_dict()
        assert d["category"] == "simple_action"
        assert d["expiry_rate"] == pytest.approx(0.167, abs=0.001)
        assert d["severity"] == "medium"
        assert d["unique_workers"] == 3


# ─── ExpiryDiagnosis Tests ───────────────────────────────────────────────────


class TestExpiryDiagnosis:
    def test_to_dict(self):
        diag = ExpiryDiagnosis(
            task_id="t1",
            category="test",
            primary_reason=ExpiryReason.LOW_BOUNTY,
            confidence=0.75,
        )
        d = diag.to_dict()
        assert d["primary_reason"] == "low_bounty"
        assert d["confidence"] == 0.75

    def test_secondary_reasons(self):
        diag = ExpiryDiagnosis(
            task_id="t1",
            primary_reason=ExpiryReason.NO_WORKERS,
            secondary_reasons=[ExpiryReason.LOW_BOUNTY, ExpiryReason.SHORT_DEADLINE],
        )
        d = diag.to_dict()
        assert len(d["secondary_reasons"]) == 2


# ─── Offline Analysis Tests ──────────────────────────────────────────────────


class TestAnalyzeOffline:
    def test_basic_analysis(self, analyzer):
        completed = _make_completed(10)
        expired = _make_expired(5)
        report = analyzer.analyze_offline(completed, expired)

        assert report.total_completed == 10
        assert report.total_expired == 5
        assert report.overall_expiry_rate == pytest.approx(1 / 3, abs=0.01)
        assert report.overall_severity == Severity.HIGH

    def test_zero_expiry(self, analyzer):
        completed = _make_completed(20)
        report = analyzer.analyze_offline(completed, [])

        assert report.total_expired == 0
        assert report.overall_expiry_rate == 0.0
        assert report.overall_severity == Severity.LOW

    def test_all_expired(self, analyzer):
        expired = _make_expired(20)
        report = analyzer.analyze_offline([], expired)

        assert report.overall_expiry_rate == 1.0
        assert report.overall_severity == Severity.CRITICAL

    def test_category_health_computed(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        assert len(report.category_health) > 0
        categories = {ch.category for ch in report.category_health}
        assert "simple_action" in categories
        assert "knowledge_access" in categories

    def test_category_expiry_rates(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        cat_lookup = {ch.category: ch for ch in report.category_health}

        # knowledge_access: 0 completed, 6 expired → 100% expiry
        ka = cat_lookup.get("knowledge_access")
        assert ka is not None
        assert ka.expiry_rate == 1.0
        assert ka.severity == Severity.CRITICAL

        # simple_action: 50 completed, 20 expired → ~28.6% expiry
        sa = cat_lookup.get("simple_action")
        assert sa is not None
        assert 0.2 < sa.expiry_rate < 0.4

    def test_worker_concentration(self, analyzer):
        # All completions from one worker → HHI = 1.0
        completed = _make_completed(20, worker="worker-1")
        expired = _make_expired(5)
        report = analyzer.analyze_offline(completed, expired)

        assert report.worker_hhi == pytest.approx(1.0)
        assert report.top_worker_share == pytest.approx(1.0)
        assert report.total_workers == 1

    def test_diverse_workers(self, analyzer):
        completed = _make_completed(10, worker="w1") + _make_completed(10, worker="w2")
        report = analyzer.analyze_offline(completed, [])

        assert report.total_workers == 2
        assert report.worker_hhi == pytest.approx(0.5)
        assert report.top_worker_share == pytest.approx(0.5)

    def test_analysis_duration_recorded(self, analyzer):
        report = analyzer.analyze_offline(_make_completed(5), _make_expired(3))
        assert report.analysis_duration_ms > 0

    def test_generated_at_set(self, analyzer):
        report = analyzer.analyze_offline(_make_completed(5), _make_expired(3))
        assert report.generated_at != ""
        # Should be ISO format
        datetime.fromisoformat(report.generated_at)


# ─── Diagnosis Tests ──────────────────────────────────────────────────────────


class TestDiagnosis:
    def test_low_bounty_detected(self, analyzer):
        completed = _make_completed(10)
        expired = [
            _make_task(
                task_id="e1",
                status="expired",
                bounty_usd=0.01,
                executor_id="",
            )
        ]
        report = analyzer.analyze_offline(completed, expired)

        assert len(report.diagnoses) == 1
        diag = report.diagnoses[0]
        assert (
            diag.primary_reason == ExpiryReason.LOW_BOUNTY
            or ExpiryReason.LOW_BOUNTY in diag.secondary_reasons
        )

    def test_niche_category_detected(self, analyzer):
        completed = _make_completed(20, "simple_action")
        expired = _make_expired(10, "knowledge_access")
        report = analyzer.analyze_offline(completed, expired)

        ka_diags = [d for d in report.diagnoses if d.category == "knowledge_access"]
        assert len(ka_diags) > 0
        # Should detect niche category (no workers in knowledge_access)
        reasons = set()
        for d in ka_diags:
            reasons.add(d.primary_reason)
            reasons.update(d.secondary_reasons)
        assert ExpiryReason.NO_WORKERS in reasons or ExpiryReason.NICHE_CATEGORY in reasons

    def test_short_deadline_detected(self, analyzer):
        expired = [
            _make_task(
                task_id="e1",
                status="expired",
                deadline_hours=1.0,
                executor_id="",
            )
        ]
        report = analyzer.analyze_offline(_make_completed(5), expired)

        diag = report.diagnoses[0]
        assert (
            diag.primary_reason == ExpiryReason.SHORT_DEADLINE
            or ExpiryReason.SHORT_DEADLINE in diag.secondary_reasons
        )

    def test_unclear_task_short_title(self, analyzer):
        expired = [
            _make_task(
                task_id="e1",
                status="expired",
                title="Do task",
                executor_id="",
            )
        ]
        report = analyzer.analyze_offline(_make_completed(5), expired)

        diag = report.diagnoses[0]
        all_reasons = {diag.primary_reason} | set(diag.secondary_reasons)
        assert ExpiryReason.UNCLEAR_TASK in all_reasons

    def test_diagnosis_confidence_range(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        for diag in report.diagnoses:
            assert 0.0 <= diag.confidence <= 1.0

    def test_all_expired_get_diagnosed(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        assert len(report.diagnoses) == len(expired)


# ─── Countermeasure Tests ─────────────────────────────────────────────────────


class TestCountermeasures:
    def test_high_concentration_triggers_recruit(self, analyzer):
        completed = _make_completed(20, worker="worker-1")
        expired = _make_expired(5)
        report = analyzer.analyze_offline(completed, expired)

        recruit = [
            cm
            for cm in report.countermeasures
            if cm.type == CountermeasureType.RECRUIT_WORKERS
        ]
        assert len(recruit) > 0

    def test_zero_worker_categories_flagged(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        # knowledge_access, code_execution, research have zero workers
        recruit = [
            cm
            for cm in report.countermeasures
            if cm.type == CountermeasureType.RECRUIT_WORKERS
        ]
        assert len(recruit) >= 1

    def test_low_bounty_triggers_escalation(self, analyzer):
        completed = _make_completed(10)
        expired = _make_expired(10, bounty=0.05)
        report = analyzer.analyze_offline(completed, expired)

        escalate = [
            cm
            for cm in report.countermeasures
            if cm.type == CountermeasureType.ESCALATE_BOUNTY
        ]
        assert len(escalate) > 0

    def test_swarm_enablement_always_recommended(self, analyzer):
        report = analyzer.analyze_offline(_make_completed(10), _make_expired(5))

        batch = [
            cm
            for cm in report.countermeasures
            if cm.type == CountermeasureType.BATCH_TASKS
        ]
        assert len(batch) > 0
        assert "SWARM_ENABLED" in batch[0].description

    def test_countermeasures_have_priorities(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        priorities = [cm.priority for cm in report.countermeasures]
        # Priorities should be sequential starting from 1
        assert priorities == sorted(priorities)
        assert priorities[0] == 1

    def test_countermeasure_to_dict(self):
        cm = Countermeasure(
            type=CountermeasureType.ESCALATE_BOUNTY,
            priority=1,
            description="Increase bounties",
            expected_impact=0.25,
            estimated_effort="low",
        )
        d = cm.to_dict()
        assert d["type"] == "escalate_bounty"
        assert d["priority"] == 1
        assert d["expected_impact"] == 0.25


# ─── Report Tests ─────────────────────────────────────────────────────────────


class TestReport:
    def test_summary_output(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        summary = report.summary()
        assert "Expiry Analysis Report" in summary
        assert "expired" in summary.lower()
        assert len(summary) > 100

    def test_to_dict(self, analyzer, diverse_data):
        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        d = report.to_dict()
        assert "overall" in d
        assert "categories" in d
        assert "countermeasures" in d
        assert "workers" in d
        assert d["overall"]["expiry_rate"] > 0

    def test_report_serializable(self, analyzer, diverse_data):
        """Report should be JSON-serializable."""
        import json

        completed, expired, cancelled = diverse_data
        report = analyzer.analyze_offline(completed, expired, cancelled)

        d = report.to_dict()
        json_str = json.dumps(d)
        assert len(json_str) > 100

        # And parseable
        parsed = json.loads(json_str)
        assert parsed["overall"]["total_tasks"] > 0


# ─── Task Recommendation Tests ───────────────────────────────────────────────


class TestTaskRecommendation:
    def test_recommend_low_bounty_task(self, analyzer):
        task = _make_task(bounty_usd=0.01)
        recs = analyzer.recommend_for_task(task)

        assert len(recs) > 0
        rec_types = {r.type for r in recs}
        assert CountermeasureType.ESCALATE_BOUNTY in rec_types

    def test_recommend_no_workers_category(self, analyzer):
        task = _make_task(category="knowledge_access")
        cat_health = [
            CategoryHealth(category="knowledge_access", unique_workers=0, expired=5)
        ]
        recs = analyzer.recommend_for_task(task, category_health=cat_health)

        rec_types = {r.type for r in recs}
        assert CountermeasureType.RECRUIT_WORKERS in rec_types

    def test_recommend_short_title(self, analyzer):
        task = _make_task(title="Do")
        recs = analyzer.recommend_for_task(task)

        rec_types = {r.type for r in recs}
        assert CountermeasureType.IMPROVE_INSTRUCTIONS in rec_types

    def test_no_issues_no_recommendations(self, analyzer):
        task = _make_task(
            bounty_usd=1.00,
            title="Take a detailed photo of the building at the intersection",
        )
        recs = analyzer.recommend_for_task(task)
        # May have some recs but none should be high priority
        assert all(r.priority >= 2 for r in recs) or len(recs) == 0


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_data(self, analyzer):
        report = analyzer.analyze_offline([], [])
        assert report.total_tasks == 0
        assert report.overall_expiry_rate == 0.0
        assert report.overall_severity == Severity.LOW

    def test_missing_fields(self, analyzer):
        """Tasks with missing fields should not crash analysis."""
        completed = [{"id": "c1"}]
        expired = [{"id": "e1"}]
        report = analyzer.analyze_offline(completed, expired)
        assert report.total_tasks == 2

    def test_null_bounty(self, analyzer):
        completed = [_make_task(bounty_usd=0)]
        expired = [_make_task(task_id="e1", status="expired", bounty_usd=0, executor_id="")]
        report = analyzer.analyze_offline(completed, expired)
        assert report.total_expired == 1

    def test_very_large_dataset(self, analyzer):
        """Shouldn't choke on larger datasets."""
        completed = _make_completed(200)
        expired = _make_expired(100)
        report = analyzer.analyze_offline(completed, expired)
        assert report.total_tasks == 300
        assert len(report.diagnoses) == 100

    def test_single_task(self, analyzer):
        report = analyzer.analyze_offline([_make_task()], [])
        assert report.total_completed == 1
        assert report.overall_expiry_rate == 0.0


# ─── Integration with Report Summary ─────────────────────────────────────────


class TestIntegration:
    def test_full_pipeline_realistic_data(self, analyzer):
        """Simulate the exact EM production data distribution."""
        # Mimic production: 195 completed (97% simple_action, 3% physical_presence)
        completed = (
            _make_completed(189, "simple_action", "worker-1")
            + _make_completed(6, "physical_presence", "worker-2")
        )
        # 108 expired (85% simple_action, rest niche)
        expired = (
            _make_expired(92, "simple_action", 0.10)
            + _make_expired(6, "knowledge_access", 0.02)
            + _make_expired(5, "code_execution", 0.05)
            + _make_expired(4, "research", 0.03)
            + _make_expired(1, "physical_presence", 0.10)
        )
        cancelled = [_make_task(task_id=f"x-{i}", status="cancelled") for i in range(30)]

        report = analyzer.analyze_offline(completed, expired, cancelled)

        # Verify overall metrics match production
        assert report.total_completed == 195
        assert report.total_expired == 108
        assert 0.35 < report.overall_expiry_rate < 0.36
        assert report.overall_severity == Severity.HIGH

        # Verify worker concentration
        assert report.total_workers == 2
        assert report.worker_hhi > 0.9  # Very concentrated
        assert report.top_worker_share > 0.9

        # Verify niche categories flagged
        cat_lookup = {ch.category: ch for ch in report.category_health}
        assert cat_lookup["knowledge_access"].expiry_rate == 1.0
        assert cat_lookup["code_execution"].expiry_rate == 1.0
        assert cat_lookup["research"].expiry_rate == 1.0

        # Verify countermeasures generated
        assert len(report.countermeasures) >= 3

        # Verify summary is readable
        summary = report.summary()
        assert "35" in summary or "36" in summary  # expiry rate
        assert len(summary.split("\n")) > 5

        # Verify JSON serialization
        import json
        d = report.to_dict()
        json_str = json.dumps(d)
        assert len(json_str) > 500
