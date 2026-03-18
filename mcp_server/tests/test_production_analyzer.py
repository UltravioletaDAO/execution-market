"""
Tests for the Production Analyzer module.

Tests the analysis pipeline without needing live API access:
- Task analysis with category diversity scoring
- Worker specialization (Herfindahl-Hirschman Index)
- Evidence quality assessment
- Timeline analysis
- Swarm readiness checks
- Routing simulation
"""

import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts/kk to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "kk"))

from production_analyzer import (
    ProductionAnalyzer,
    AnalysisReport,
    TaskAnalysis,
    WorkerProfile,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def make_task(
    task_id="t1",
    title="Test Task",
    status="completed",
    category="simple_action",
    bounty=0.10,
    network="base",
    worker_wallet="0xWORKER1",
    created_at=None,
    completed_at=None,
    quality_rating=None,
    required_evidence=None,
):
    """Create a mock EM task dict."""
    now = datetime.now(timezone.utc)
    return {
        "id": task_id,
        "title": title,
        "status": status,
        "category": category,
        "bounty_amount": bounty,
        "bounty_usd": bounty,
        "payment_network": network,
        "worker_wallet": worker_wallet,
        "worker_address": worker_wallet,
        "created_at": created_at or (now - timedelta(hours=24)).isoformat(),
        "completed_at": completed_at or now.isoformat(),
        "updated_at": completed_at or now.isoformat(),
        "quality_rating": quality_rating,
        "required_evidence": required_evidence or [],
    }


def make_diverse_tasks(n=50):
    """Create a diverse set of tasks for testing."""
    categories = [
        "simple_action", "physical_presence", "knowledge_access",
        "code_execution", "research", "content_generation",
    ]
    networks = ["base", "ethereum", "polygon", "arbitrum"]
    statuses = ["completed", "submitted", "expired", "cancelled"]
    
    tasks = []
    for i in range(n):
        cat = categories[i % len(categories)]
        net = networks[i % len(networks)]
        status = statuses[i % len(statuses)]
        worker = f"0xWORKER{(i % 5) + 1:02d}"
        bounty = 0.10 + (i * 0.05)
        
        evidence = []
        if cat == "physical_presence":
            evidence = ["photo_geo", "text_response"]
        elif cat == "code_execution":
            evidence = ["screenshot", "text_response"]
        elif cat == "research":
            evidence = ["document", "text_response"]
        
        now = datetime.now(timezone.utc)
        created = now - timedelta(days=n - i, hours=i % 24)
        completed = created + timedelta(hours=2 + (i % 10))
        
        tasks.append(make_task(
            task_id=f"t{i:03d}",
            title=f"Task {i}: {cat}",
            status=status,
            category=cat,
            bounty=bounty,
            network=net,
            worker_wallet=worker,
            created_at=created.isoformat(),
            completed_at=completed.isoformat(),
            quality_rating=3.0 + (i % 5) * 0.5 if status == "completed" else None,
            required_evidence=evidence,
        ))
    
    return tasks


# ─── Task Analysis Tests ──────────────────────────────────────────────────────


class TestTaskAnalysis:
    """Test task distribution and category diversity scoring."""

    def test_empty_tasks(self):
        """Empty task list produces zeroed report."""
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_tasks([], report)
        
        assert report.total_tasks == 0
        assert report.tasks_by_status == {}
        assert report.tasks_by_category == {}
        assert report.total_volume_usd == 0.0
        assert report.category_diversity_score == 0.0

    def test_single_category(self):
        """All tasks in one category → diversity near 0."""
        tasks = [make_task(category="simple_action") for _ in range(10)]
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        report.total_tasks = len(tasks)
        analyzer._analyze_tasks(tasks, report)
        
        assert report.tasks_by_category == {"simple_action": 10}
        # Single category: entropy = 0, diversity = 0
        assert report.category_diversity_score == 0.0

    def test_perfect_diversity(self):
        """Equal distribution across categories → diversity near 1."""
        categories = ["a", "b", "c", "d"]
        tasks = []
        for cat in categories:
            for _ in range(25):
                tasks.append(make_task(category=cat))
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        report.total_tasks = len(tasks)
        analyzer._analyze_tasks(tasks, report)
        
        # Perfect uniform distribution → diversity = 1.0
        assert abs(report.category_diversity_score - 1.0) < 0.001

    def test_skewed_diversity(self):
        """Skewed distribution → intermediate diversity."""
        tasks = (
            [make_task(category="a") for _ in range(80)] +
            [make_task(category="b") for _ in range(15)] +
            [make_task(category="c") for _ in range(5)]
        )
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        report.total_tasks = len(tasks)
        analyzer._analyze_tasks(tasks, report)
        
        # Skewed but multi-category → intermediate diversity
        assert 0.1 < report.category_diversity_score < 0.8

    def test_bounty_statistics(self):
        """Volume, avg, and median bounty calculations."""
        tasks = [
            make_task(bounty=1.0),
            make_task(bounty=2.0),
            make_task(bounty=3.0),
            make_task(bounty=10.0),
            make_task(bounty=0.50),
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        report.total_tasks = len(tasks)
        analyzer._analyze_tasks(tasks, report)
        
        assert report.total_volume_usd == 16.50
        assert abs(report.avg_bounty_usd - 3.30) < 0.01
        # Sorted: [0.5, 1.0, 2.0, 3.0, 10.0] → median = 2.0
        assert report.median_bounty_usd == 2.0

    def test_status_counting(self):
        """Status counts are accurate."""
        tasks = (
            [make_task(status="completed") for _ in range(50)] +
            [make_task(status="expired") for _ in range(30)] +
            [make_task(status="cancelled") for _ in range(10)] +
            [make_task(status="submitted") for _ in range(5)]
        )
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        report.total_tasks = len(tasks)
        analyzer._analyze_tasks(tasks, report)
        
        assert report.tasks_by_status["completed"] == 50
        assert report.tasks_by_status["expired"] == 30
        assert report.tasks_by_status["cancelled"] == 10
        assert report.tasks_by_status["submitted"] == 5

    def test_network_counting(self):
        """Network distribution is tracked correctly."""
        tasks = (
            [make_task(network="base") for _ in range(40)] +
            [make_task(network="ethereum") for _ in range(30)] +
            [make_task(network="polygon") for _ in range(20)] +
            [make_task(network="arbitrum") for _ in range(10)]
        )
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        report.total_tasks = len(tasks)
        analyzer._analyze_tasks(tasks, report)
        
        assert report.tasks_by_network["base"] == 40
        assert report.tasks_by_network["ethereum"] == 30
        assert report.tasks_by_network["polygon"] == 20
        assert report.tasks_by_network["arbitrum"] == 10


# ─── Worker Analysis Tests ────────────────────────────────────────────────────


class TestWorkerAnalysis:
    """Test worker specialization and profiling."""

    def test_no_workers(self):
        """Tasks with no worker data → 0 workers."""
        tasks = [make_task(worker_wallet="", status="published")]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        assert report.total_workers == 0

    def test_single_worker(self):
        """One worker with multiple tasks."""
        tasks = [
            make_task(task_id=f"t{i}", worker_wallet="0xABC", status="completed",
                     category="simple_action", bounty=1.0)
            for i in range(5)
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        assert report.total_workers == 1
        assert report.worker_profiles[0].tasks_completed == 5
        assert report.worker_profiles[0].total_earned_usd == 5.0
        assert report.worker_profiles[0].wallet == "0xABC"

    def test_specialist_worker(self):
        """Worker who only does one category → high specialization."""
        tasks = [
            make_task(task_id=f"t{i}", worker_wallet="0xSPEC", status="completed",
                     category="code_execution")
            for i in range(10)
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        wp = report.worker_profiles[0]
        # HHI for single category = 1.0
        assert wp.specialization_score == 1.0

    def test_generalist_worker(self):
        """Worker across many categories → low specialization."""
        categories = ["a", "b", "c", "d", "e"]
        tasks = [
            make_task(task_id=f"t{i}", worker_wallet="0xGEN", status="completed",
                     category=categories[i % len(categories)])
            for i in range(10)
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        wp = report.worker_profiles[0]
        # Uniform across 5 categories: HHI = 5 * (2/10)^2 = 5 * 0.04 = 0.2
        assert wp.specialization_score < 0.5  # Generalist

    def test_multiple_workers_sorted(self):
        """Workers sorted by task count descending."""
        tasks = (
            [make_task(task_id=f"a{i}", worker_wallet="0xTOP", status="completed") for i in range(10)] +
            [make_task(task_id=f"b{i}", worker_wallet="0xMID", status="completed") for i in range(5)] +
            [make_task(task_id=f"c{i}", worker_wallet="0xBOT", status="completed") for i in range(2)]
        )
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        assert report.total_workers == 3
        assert report.worker_profiles[0].wallet == "0xTOP"
        assert report.worker_profiles[1].wallet == "0xMID"
        assert report.worker_profiles[2].wallet == "0xBOT"

    def test_avg_tasks_per_worker(self):
        """Average tasks per worker calculation."""
        tasks = (
            [make_task(task_id=f"a{i}", worker_wallet="0xA", status="completed") for i in range(6)] +
            [make_task(task_id=f"b{i}", worker_wallet="0xB", status="completed") for i in range(4)]
        )
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        assert report.total_workers == 2
        assert report.avg_tasks_per_worker == 5.0  # (6 + 4) / 2

    def test_worker_ratings(self):
        """Worker average rating calculation."""
        tasks = [
            make_task(task_id="t1", worker_wallet="0xR", status="completed", quality_rating=4.0),
            make_task(task_id="t2", worker_wallet="0xR", status="completed", quality_rating=5.0),
            make_task(task_id="t3", worker_wallet="0xR", status="completed", quality_rating=3.0),
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        assert abs(report.worker_profiles[0].avg_rating - 4.0) < 0.01

    def test_non_completed_tasks_excluded(self):
        """Only completed/submitted tasks count for worker profiles."""
        tasks = [
            make_task(task_id="t1", worker_wallet="0xW", status="completed"),
            make_task(task_id="t2", worker_wallet="0xW", status="expired"),
            make_task(task_id="t3", worker_wallet="0xW", status="published"),
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_workers(tasks, report)
        
        assert report.total_workers == 1
        assert report.worker_profiles[0].tasks_completed == 1


# ─── Evidence Analysis Tests ──────────────────────────────────────────────────


class TestEvidenceAnalysis:
    """Test evidence quality assessment."""

    def test_no_evidence(self):
        """Tasks without evidence → zero metrics."""
        tasks = [make_task() for _ in range(5)]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_evidence(tasks, report)
        
        assert report.avg_evidence_per_task == 0.0
        assert report.gps_evidence_pct == 0.0

    def test_evidence_types_counted(self):
        """Evidence types are properly counted."""
        tasks = [
            make_task(required_evidence=["photo_geo", "text_response"]),
            make_task(required_evidence=["photo_geo", "receipt"]),
            make_task(required_evidence=["screenshot"]),
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_evidence(tasks, report)
        
        assert report.evidence_type_distribution["photo_geo"] == 2
        assert report.evidence_type_distribution["text_response"] == 1
        assert report.evidence_type_distribution["receipt"] == 1
        assert report.evidence_type_distribution["screenshot"] == 1

    def test_gps_evidence_percentage(self):
        """GPS evidence percentage calculation."""
        tasks = [
            make_task(required_evidence=["photo_geo"]),       # 1 GPS out of 1
            make_task(required_evidence=["text_response"]),    # 0 GPS out of 1
            make_task(required_evidence=["photo_geo", "receipt"]),  # 1 GPS out of 2
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_evidence(tasks, report)
        
        # 2 GPS out of 4 total = 50%
        assert abs(report.gps_evidence_pct - 50.0) < 0.1

    def test_avg_evidence_per_task(self):
        """Average evidence items per task."""
        tasks = [
            make_task(required_evidence=["a", "b", "c"]),  # 3
            make_task(required_evidence=["d"]),             # 1
            make_task(required_evidence=[]),                # 0 (not counted)
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_evidence(tasks, report)
        
        # 4 items across 2 tasks with evidence = 2.0
        assert abs(report.avg_evidence_per_task - 2.0) < 0.01

    def test_dict_evidence_format(self):
        """Handle evidence as list of dicts (alternative format)."""
        tasks = [
            make_task(required_evidence=[
                {"type": "photo_geo", "required": True},
                {"type": "text_response", "required": True},
            ]),
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_evidence(tasks, report)
        
        assert report.evidence_type_distribution["photo_geo"] == 1
        assert report.evidence_type_distribution["text_response"] == 1


# ─── Timeline Analysis Tests ─────────────────────────────────────────────────


class TestTimelineAnalysis:
    """Test timeline and completion time analysis."""

    def test_empty_timeline(self):
        """No tasks → zero timeline metrics."""
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_timeline([], report)
        
        assert report.avg_completion_hours == 0.0
        assert report.busiest_day == ""

    def test_completion_time_calculation(self):
        """Average completion time from created_at to completed_at."""
        now = datetime.now(timezone.utc)
        tasks = [
            make_task(
                status="completed",
                created_at=(now - timedelta(hours=4)).isoformat(),
                completed_at=now.isoformat(),
            ),
            make_task(
                status="completed",
                created_at=(now - timedelta(hours=8)).isoformat(),
                completed_at=now.isoformat(),
            ),
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_timeline(tasks, report)
        
        # (4 + 8) / 2 = 6 hours
        assert abs(report.avg_completion_hours - 6.0) < 0.5

    def test_busiest_day(self):
        """Identifies the busiest day by task creation."""
        tasks = (
            [make_task(created_at="2026-03-15T10:00:00Z") for _ in range(5)] +
            [make_task(created_at="2026-03-16T10:00:00Z") for _ in range(10)] +
            [make_task(created_at="2026-03-17T10:00:00Z") for _ in range(3)]
        )
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_timeline(tasks, report)
        
        assert report.busiest_day == "2026-03-16"

    def test_outlier_completion_times_excluded(self):
        """Tasks with >30 day completion are excluded from avg."""
        now = datetime.now(timezone.utc)
        tasks = [
            make_task(
                status="completed",
                created_at=(now - timedelta(hours=2)).isoformat(),
                completed_at=now.isoformat(),
            ),
            make_task(
                status="completed",
                created_at=(now - timedelta(days=60)).isoformat(),  # >30d outlier
                completed_at=now.isoformat(),
            ),
        ]
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport()
        analyzer._analyze_timeline(tasks, report)
        
        # Only the 2-hour task should be included
        assert report.avg_completion_hours < 5.0


# ─── Swarm Readiness Tests ───────────────────────────────────────────────────


class TestSwarmReadiness:
    """Test swarm readiness assessment logic."""

    def test_full_readiness(self):
        """Healthy system with ample data passes all checks."""
        report = AnalysisReport(
            em_api_healthy=True,
            tasks_by_status={"completed": 200},
            tasks_by_category={"a": 50, "b": 50, "c": 50, "d": 50},
            category_diversity_score=0.95,
            total_workers=15,
            avg_evidence_per_task=2.5,
        )
        
        analyzer = ProductionAnalyzer()
        analyzer._assess_swarm_readiness(report)
        
        passed = sum(1 for r in report.swarm_readiness.values() if r.get("pass"))
        assert passed >= 5  # At least 5 of 6 checks should pass

    def test_minimal_readiness(self):
        """Barely meets thresholds."""
        report = AnalysisReport(
            em_api_healthy=True,
            tasks_by_status={"completed": 100},
            tasks_by_category={"a": 40, "b": 30, "c": 30},
            category_diversity_score=0.6,
            total_workers=10,
            avg_evidence_per_task=1.5,
        )
        
        analyzer = ProductionAnalyzer()
        analyzer._assess_swarm_readiness(report)
        
        passed = sum(1 for r in report.swarm_readiness.values() if r.get("pass"))
        assert passed >= 5

    def test_unhealthy_api(self):
        """Unhealthy API → api_connectivity check fails."""
        report = AnalysisReport(em_api_healthy=False)
        
        analyzer = ProductionAnalyzer()
        analyzer._assess_swarm_readiness(report)
        
        assert not report.swarm_readiness["api_connectivity"]["pass"]

    def test_insufficient_volume(self):
        """Too few completed tasks → volume check fails."""
        report = AnalysisReport(
            em_api_healthy=True,
            tasks_by_status={"completed": 5},
            tasks_by_category={"a": 5},
            total_workers=0,
        )
        
        analyzer = ProductionAnalyzer()
        analyzer._assess_swarm_readiness(report)
        
        assert not report.swarm_readiness["task_volume"]["pass"]


# ─── Report Export Tests ──────────────────────────────────────────────────────


class TestReportExport:
    """Test report serialization to JSON and Markdown."""

    def test_to_dict_structure(self):
        """Report dict has expected top-level keys."""
        report = AnalysisReport(
            generated_at="2026-03-18T00:00:00Z",
            em_api_healthy=True,
            total_tasks=100,
        )
        
        d = report.to_dict()
        
        assert "generated_at" in d
        assert "tasks" in d
        assert "workers" in d
        assert "evidence" in d
        assert "swarm_readiness" in d
        assert "timeline" in d

    def test_to_dict_serializable(self):
        """Report dict is JSON-serializable."""
        report = AnalysisReport(
            generated_at="2026-03-18T00:00:00Z",
            total_tasks=50,
            tasks_by_status={"completed": 30, "expired": 20},
            tasks_by_category={"simple_action": 40, "research": 10},
        )
        
        d = report.to_dict()
        json_str = json.dumps(d)
        assert len(json_str) > 0
        parsed = json.loads(json_str)
        assert parsed["tasks"]["total"] == 50

    def test_to_markdown(self):
        """Report generates valid markdown."""
        report = AnalysisReport(
            generated_at="2026-03-18T00:00:00Z",
            em_api_healthy=True,
            total_tasks=100,
            total_volume_usd=50.0,
            avg_bounty_usd=0.50,
            median_bounty_usd=0.30,
            tasks_by_status={"completed": 80, "expired": 20},
            tasks_by_category={"simple_action": 90, "research": 10},
            tasks_by_network={"base": 60, "ethereum": 40},
            total_workers=5,
            avg_tasks_per_worker=16.0,
            specialization_index=0.4,
            swarm_readiness={
                "test_check": {"pass": True, "message": "OK"},
            },
        )
        
        md = report.to_markdown()
        
        assert "# Execution Market Production Analysis" in md
        assert "✅ Healthy" in md
        assert "100" in md
        assert "$50.00" in md
        assert "simple_action" in md


# ─── Integration Tests ────────────────────────────────────────────────────────


class TestFullAnalysis:
    """Integration tests with diverse mock data."""

    def test_full_pipeline_diverse_tasks(self):
        """Run full analysis pipeline with diverse task set."""
        tasks = make_diverse_tasks(50)
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            em_api_healthy=True,
        )
        report.total_tasks = len(tasks)
        
        analyzer._analyze_tasks(tasks, report)
        analyzer._analyze_workers(tasks, report)
        analyzer._analyze_evidence(tasks, report)
        analyzer._analyze_timeline(tasks, report)
        analyzer._assess_swarm_readiness(report)
        
        # Task analysis
        assert report.total_tasks == 50
        assert len(report.tasks_by_category) == 6  # 6 categories in make_diverse_tasks
        assert report.category_diversity_score > 0.5  # Should be fairly diverse
        
        # Worker analysis
        assert report.total_workers > 0
        assert report.avg_tasks_per_worker > 0
        
        # Evidence analysis
        assert len(report.evidence_type_distribution) > 0
        
        # Timeline
        assert report.busiest_day != ""
        
        # Export works
        d = report.to_dict()
        assert json.dumps(d)  # Serializable
        
        md = report.to_markdown()
        assert len(md) > 100  # Non-trivial markdown

    def test_large_dataset(self):
        """Performance test with larger dataset."""
        tasks = make_diverse_tasks(500)
        
        analyzer = ProductionAnalyzer()
        report = AnalysisReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            em_api_healthy=True,
        )
        report.total_tasks = len(tasks)
        
        import time
        start = time.monotonic()
        
        analyzer._analyze_tasks(tasks, report)
        analyzer._analyze_workers(tasks, report)
        analyzer._analyze_evidence(tasks, report)
        analyzer._analyze_timeline(tasks, report)
        
        elapsed_ms = (time.monotonic() - start) * 1000
        
        # Should complete in under 500ms even for 500 tasks
        assert elapsed_ms < 500
        assert report.total_tasks == 500
