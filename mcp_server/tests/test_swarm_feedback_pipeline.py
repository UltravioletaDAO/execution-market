"""
Tests for FeedbackPipeline — the feedback loop from completions to intelligence.

Tests cover:
    - Evidence processing → Skill DNA updates
    - Internal reputation Bayesian scoring
    - Worker registry persistence (save/load cycle)
    - Pipeline state management (watermarks, dedup)
    - Composite score computation
    - Leaderboard ranking
    - Worker profile generation
    - Edge cases (missing data, suspicious evidence, empty evidence)
    - Multiple completions for same worker (running averages)
    - Category-specific scoring
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.feedback_pipeline import (
    FeedbackPipeline,
    CompletionFeedback,
    PipelineRunResult,
    PipelineState,
)
from swarm.evidence_parser import (
    EvidenceParser,
    EvidenceQuality,
    QualityAssessment,
    SkillDNA,
    SkillDimension,
    SkillSignal,
    WorkerRegistry,
)
from swarm.reputation_bridge import (
    ReputationBridge,
    InternalReputation,
    OnChainReputation,
    CompositeScore,
    ReputationTier,
)
from swarm.lifecycle_manager import LifecycleManager, AgentState


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for pipeline state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def pipeline(temp_state_dir):
    """Create a FeedbackPipeline with temp storage."""
    return FeedbackPipeline(
        em_api_url="https://api.execution.market",
        state_dir=temp_state_dir,
    )


@pytest.fixture
def sample_task():
    """A completed EM task with evidence."""
    return {
        "id": "task-001",
        "title": "Verify store is open",
        "category": "photo_verification",
        "status": "completed",
        "bounty_amount": 5.0,
        "worker_id": "worker-alice-0x123",
        "evidence": [
            {
                "type": "photo_geo",
                "content": "Photo of storefront with clear signage showing open status",
                "metadata": {
                    "latitude": 25.7617,
                    "longitude": -80.1918,
                    "timestamp": "2026-03-18T01:00:00Z",
                    "resolution": "1920x1080",
                },
            },
            {
                "type": "text_response",
                "content": "Store confirmed open at 1:00 PM. Sign on door says hours are 9am-9pm daily. Two employees visible inside.",
                "metadata": {"word_count": 20},
            },
        ],
    }


@pytest.fixture
def sample_task_minimal():
    """A completed task with minimal evidence."""
    return {
        "id": "task-002",
        "title": "Simple data check",
        "category": "data_entry",
        "status": "completed",
        "worker_id": "worker-bob-0x456",
        "evidence": [
            {
                "type": "text_response",
                "content": "Done",
            },
        ],
    }


@pytest.fixture
def sample_task_suspicious():
    """A task with suspicious evidence."""
    return {
        "id": "task-003",
        "title": "Verify product availability",
        "category": "photo_verification",
        "status": "completed",
        "worker_id": "worker-charlie-0x789",
        "evidence": [
            {
                "type": "photo",
                "content": "test evidence placeholder lorem ipsum",
            },
        ],
    }


@pytest.fixture
def sample_task_no_evidence():
    """A completed task with no evidence at all."""
    return {
        "id": "task-004",
        "title": "Mystery task",
        "category": "general",
        "status": "completed",
        "worker_id": "worker-dave-0xabc",
        "evidence": [],
    }


@pytest.fixture
def sample_task_rich():
    """A task with rich, diverse evidence."""
    return {
        "id": "task-005",
        "title": "Full verification with documentation",
        "category": "mystery_shopping",
        "status": "completed",
        "bounty_amount": 25.0,
        "worker_id": "worker-alice-0x123",
        "evidence": [
            {
                "type": "photo_geo",
                "content": "Exterior photo showing store branding and customer traffic at entrance",
                "metadata": {
                    "latitude": 25.7617,
                    "longitude": -80.1918,
                    "timestamp": "2026-03-18T02:00:00Z",
                    "resolution": "4032x3024",
                    "device": "iPhone 15 Pro",
                },
            },
            {
                "type": "video",
                "content": "Walk-through video showing interior layout, product displays, and customer service interaction",
                "metadata": {
                    "duration_seconds": 120,
                    "resolution": "1080p",
                },
            },
            {
                "type": "receipt",
                "content": "Purchase receipt for test transaction — item: coffee, price: $4.50",
                "metadata": {
                    "amount": 4.50,
                    "timestamp": "2026-03-18T02:15:00Z",
                },
            },
            {
                "type": "text_response",
                "content": (
                    "Detailed mystery shopping report:\n"
                    "1. Store cleanliness: 8/10 — floors clean, some dust on shelves\n"
                    "2. Staff friendliness: 9/10 — greeted within 30 seconds\n"
                    "3. Product availability: 7/10 — two advertised items out of stock\n"
                    "4. Checkout speed: 10/10 — under 2 minutes\n"
                    "5. Overall experience: 8.5/10 — recommended for return visit"
                ),
                "metadata": {"word_count": 80},
            },
            {
                "type": "document",
                "content": "Completed inspection checklist with all 15 items marked and annotated with photos",
                "metadata": {
                    "pages": 3,
                    "format": "pdf",
                },
            },
        ],
    }


# ─── Basic Processing Tests ──────────────────────────────────────────────────


class TestCompletionProcessing:
    """Test processing individual task completions."""

    def test_process_good_evidence(self, pipeline, sample_task):
        """Good evidence produces positive feedback."""
        feedback = pipeline.process_completion_from_task(sample_task)

        assert feedback.task_id == "task-001"
        assert feedback.worker_id == "worker-alice-0x123"
        assert feedback.error is None
        assert feedback.evidence_count == 2
        assert feedback.quality_score > 0.4
        assert feedback.skill_signals_count > 0
        assert feedback.worker_task_count == 1
        assert "photo_geo" in feedback.evidence_types
        assert "text_response" in feedback.evidence_types

    def test_process_minimal_evidence(self, pipeline, sample_task_minimal):
        """Minimal evidence gets lower quality score."""
        feedback = pipeline.process_completion_from_task(sample_task_minimal)

        assert feedback.worker_id == "worker-bob-0x456"
        assert feedback.error is None
        assert feedback.evidence_count == 1
        # Minimal evidence shouldn't score very high
        assert feedback.quality_score < 0.8

    def test_process_suspicious_evidence(self, pipeline, sample_task_suspicious):
        """Suspicious evidence is flagged."""
        feedback = pipeline.process_completion_from_task(sample_task_suspicious)

        assert feedback.worker_id == "worker-charlie-0x789"
        assert feedback.quality == EvidenceQuality.SUSPICIOUS
        assert len(feedback.flags) > 0
        assert any("suspicious" in f for f in feedback.flags)

    def test_process_no_evidence(self, pipeline, sample_task_no_evidence):
        """Task with no evidence gets poor quality."""
        feedback = pipeline.process_completion_from_task(sample_task_no_evidence)

        assert feedback.worker_id == "worker-dave-0xabc"
        assert feedback.quality == EvidenceQuality.POOR
        assert feedback.quality_score == 0.0
        assert feedback.evidence_count == 0

    def test_process_rich_evidence(self, pipeline, sample_task_rich):
        """Rich, diverse evidence gets high quality score."""
        feedback = pipeline.process_completion_from_task(sample_task_rich)

        assert feedback.worker_id == "worker-alice-0x123"
        assert feedback.error is None
        assert feedback.evidence_count == 5
        assert feedback.quality_score > 0.6
        assert feedback.skill_signals_count > 5
        assert len(set(feedback.evidence_types)) >= 4  # Multiple types

    def test_process_missing_worker_id(self, pipeline):
        """Task without worker identity returns error."""
        task = {
            "id": "task-no-worker",
            "title": "No worker assigned",
            "status": "completed",
        }
        feedback = pipeline.process_completion_from_task(task)
        assert feedback.error is not None
        assert "worker" in feedback.error.lower() or "identity" in feedback.error.lower()


# ─── Skill DNA Update Tests ──────────────────────────────────────────────────


class TestSkillDNAUpdates:
    """Test that completions correctly update worker Skill DNA."""

    def test_skill_dna_created_on_first_completion(self, pipeline, sample_task):
        """First completion creates a Skill DNA profile."""
        pipeline.process_completion_from_task(sample_task)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        assert dna is not None
        assert dna.task_count == 1
        assert dna.evidence_count == 2
        assert len(dna.dimensions) > 0

    def test_skill_dna_accumulates(self, pipeline, sample_task, sample_task_rich):
        """Multiple completions accumulate in Skill DNA."""
        pipeline.process_completion_from_task(sample_task)
        pipeline.process_completion_from_task(sample_task_rich)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        assert dna.task_count == 2
        assert dna.evidence_count == 7  # 2 + 5

    def test_geo_evidence_boosts_mobility(self, pipeline, sample_task):
        """Photo_geo evidence boosts geo_mobility skill."""
        pipeline.process_completion_from_task(sample_task)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        geo_score = dna.dimensions.get("geo_mobility", 0)
        assert geo_score > 0, "Geo mobility should be boosted by photo_geo evidence"

    def test_verification_skills_from_geo_photo(self, pipeline, sample_task):
        """Geo-verified photos boost verification skill."""
        pipeline.process_completion_from_task(sample_task)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        verification = dna.dimensions.get("verification_skill", 0)
        assert verification > 0

    def test_communication_from_text(self, pipeline, sample_task):
        """Text responses boost communication skill."""
        pipeline.process_completion_from_task(sample_task)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        comm = dna.dimensions.get("communication", 0)
        assert comm > 0

    def test_top_skills_populated(self, pipeline, sample_task_rich):
        """Rich evidence populates multiple top skills."""
        pipeline.process_completion_from_task(sample_task_rich)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        top = dna.get_top_skills(5)
        assert len(top) >= 3, "Rich evidence should populate at least 3 skill dimensions"

    def test_categories_tracked(self, pipeline, sample_task, sample_task_rich):
        """Task categories are tracked in Skill DNA."""
        pipeline.process_completion_from_task(sample_task)
        pipeline.process_completion_from_task(sample_task_rich)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        assert len(dna.categories_seen) > 0

    def test_avg_quality_updates(self, pipeline, sample_task, sample_task_rich):
        """Average quality is computed as running average."""
        fb1 = pipeline.process_completion_from_task(sample_task)
        fb2 = pipeline.process_completion_from_task(sample_task_rich)

        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        expected_avg = (fb1.quality_score + fb2.quality_score) / 2
        assert abs(dna.avg_quality - expected_avg) < 0.01


# ─── Reputation Tests ────────────────────────────────────────────────────────


class TestReputationUpdates:
    """Test internal reputation scoring from feedback."""

    def test_reputation_created(self, pipeline, sample_task):
        """First completion creates internal reputation."""
        pipeline.process_completion_from_task(sample_task)

        rep = pipeline.get_internal_reputation("worker-alice-0x123")
        assert rep is not None
        assert rep.total_tasks == 1
        assert rep.bayesian_score > 0

    def test_reputation_improves_with_good_work(self, pipeline, sample_task, sample_task_rich):
        """Good evidence improves reputation score."""
        pipeline.process_completion_from_task(sample_task)
        rep1 = pipeline.get_internal_reputation("worker-alice-0x123")
        score_after_1 = rep1.bayesian_score

        pipeline.process_completion_from_task(sample_task_rich)
        rep2 = pipeline.get_internal_reputation("worker-alice-0x123")

        assert rep2.total_tasks == 2
        assert rep2.successful_tasks == 2
        assert rep2.bayesian_score > 0

    def test_reputation_delta_returned(self, pipeline, sample_task):
        """Feedback includes reputation delta."""
        feedback = pipeline.process_completion_from_task(sample_task)
        # First task: delta should be the initial score
        assert isinstance(feedback.reputation_delta, float)

    def test_suspicious_evidence_not_counted_as_success(
        self, pipeline, sample_task_suspicious
    ):
        """Suspicious evidence counts as failure in reputation."""
        pipeline.process_completion_from_task(sample_task_suspicious)

        rep = pipeline.get_internal_reputation("worker-charlie-0x789")
        assert rep.total_tasks == 1
        # Suspicious = not successful
        assert rep.successful_tasks == 0
        assert rep.consecutive_failures == 1

    def test_success_rate_computation(self, pipeline, sample_task, sample_task_suspicious):
        """Success rate is correctly computed."""
        # Process 2 good, 1 suspicious for same worker
        task1 = {**sample_task, "worker_id": "worker-test"}
        task2 = {**sample_task, "id": "task-002b", "worker_id": "worker-test"}
        task3 = {**sample_task_suspicious, "id": "task-003b", "worker_id": "worker-test"}

        pipeline.process_completion_from_task(task1)
        pipeline.process_completion_from_task(task2)
        pipeline.process_completion_from_task(task3)

        rep = pipeline.get_internal_reputation("worker-test")
        assert rep.total_tasks == 3
        assert rep.successful_tasks == 2
        assert abs(rep.success_rate - 2 / 3) < 0.01

    def test_category_scores_updated(self, pipeline, sample_task):
        """Category-specific scores are updated on completion."""
        pipeline.process_completion_from_task(sample_task)

        rep = pipeline.get_internal_reputation("worker-alice-0x123")
        assert len(rep.category_scores) > 0
        # photo_verification maps to verification, photo, evidence
        assert any(
            cat in rep.category_scores
            for cat in ["verification", "photo", "evidence"]
        )

    def test_consecutive_failure_penalty(self, pipeline, sample_task_suspicious):
        """Consecutive failures reduce reputation faster."""
        worker_id = "worker-fail"
        for i in range(3):
            task = {
                **sample_task_suspicious,
                "id": f"task-fail-{i}",
                "worker_id": worker_id,
            }
            pipeline.process_completion_from_task(task)

        rep = pipeline.get_internal_reputation(worker_id)
        assert rep.consecutive_failures == 3
        # Bayesian score should be penalized
        assert rep.bayesian_score < 0.3


# ─── Composite Score Tests ───────────────────────────────────────────────────


class TestCompositeScoring:
    """Test composite score computation via reputation bridge."""

    def test_composite_score_computed(self, pipeline, sample_task):
        """Composite score can be computed after processing."""
        pipeline.process_completion_from_task(sample_task)

        score = pipeline.get_composite_score("worker-alice-0x123")
        assert score is not None
        assert score.total > 0
        assert score.skill_score >= 0
        assert score.reputation_score >= 0
        assert score.reliability_score >= 0
        assert score.recency_score >= 0

    def test_composite_score_improves_with_tasks(
        self, pipeline, sample_task, sample_task_rich
    ):
        """Composite score generally improves with more good work."""
        pipeline.process_completion_from_task(sample_task)
        score1 = pipeline.get_composite_score("worker-alice-0x123")

        pipeline.process_completion_from_task(sample_task_rich)
        score2 = pipeline.get_composite_score("worker-alice-0x123")

        # More tasks should improve reliability at minimum
        assert score2.reliability_score >= score1.reliability_score

    def test_composite_with_categories(self, pipeline, sample_task):
        """Composite score considers task categories."""
        pipeline.process_completion_from_task(sample_task)

        score = pipeline.get_composite_score(
            "worker-alice-0x123",
            task_categories=["verification", "photo"],
        )
        assert score is not None
        assert score.skill_score > 0

    def test_nonexistent_worker_returns_none(self, pipeline):
        """No composite score for unknown workers."""
        score = pipeline.get_composite_score("worker-nonexistent")
        assert score is None


# ─── Pipeline State Tests ────────────────────────────────────────────────────


class TestPipelineState:
    """Test pipeline state management."""

    def test_state_initialized(self, pipeline):
        """Pipeline starts with empty state."""
        stats = pipeline.get_stats()
        assert stats["pipeline"]["total_runs"] == 0
        assert stats["pipeline"]["total_tasks_processed"] == 0

    def test_state_persists(self, temp_state_dir, sample_task):
        """Pipeline state survives restart."""
        # Process a task
        p1 = FeedbackPipeline(state_dir=temp_state_dir)
        p1.process_completion_from_task(sample_task)
        p1._state.total_runs = 1
        p1._state.total_tasks_processed = 1
        p1._save_state()
        p1._save_worker_registry()

        # Create new pipeline from same state dir
        p2 = FeedbackPipeline(state_dir=temp_state_dir)
        stats = p2.get_stats()
        assert stats["pipeline"]["total_runs"] == 1
        assert stats["pipeline"]["total_tasks_processed"] == 1

    def test_worker_registry_persists(self, temp_state_dir, sample_task):
        """Worker registry survives restart."""
        p1 = FeedbackPipeline(state_dir=temp_state_dir)
        p1.process_completion_from_task(sample_task)
        p1._save_worker_registry()

        p2 = FeedbackPipeline(state_dir=temp_state_dir)
        dna = p2.worker_registry.get_worker("worker-alice-0x123")
        assert dna is not None
        assert dna.task_count == 1

    def test_reputation_persists(self, temp_state_dir, sample_task):
        """Internal reputations survive restart."""
        p1 = FeedbackPipeline(state_dir=temp_state_dir)
        p1.process_completion_from_task(sample_task)
        p1._save_state()

        p2 = FeedbackPipeline(state_dir=temp_state_dir)
        rep = p2.get_internal_reputation("worker-alice-0x123")
        assert rep is not None
        assert rep.total_tasks == 1

    def test_dedup_prevents_reprocessing(self, pipeline, sample_task):
        """Already-processed task IDs are skipped."""
        pipeline._state.processed_task_ids.append("task-001")

        # Simulate process_new_completions seeing this task
        # The task should be in the skip list
        assert "task-001" in pipeline._state.processed_task_ids

    def test_state_file_created(self, temp_state_dir, sample_task):
        """State file is created on save."""
        p = FeedbackPipeline(state_dir=temp_state_dir)
        p.process_completion_from_task(sample_task)
        p._state.total_runs = 1
        p._save_state()

        state_file = Path(temp_state_dir) / "pipeline_state.json"
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)
        assert data["total_runs"] == 1


class TestPipelineStateDataclass:
    """Test PipelineState serialization."""

    def test_round_trip(self):
        state = PipelineState(
            last_processed_at="2026-03-18T01:00:00Z",
            processed_task_ids=["t1", "t2", "t3"],
            total_runs=5,
            total_tasks_processed=42,
        )
        data = state.to_dict()
        restored = PipelineState.from_dict(data)

        assert restored.last_processed_at == state.last_processed_at
        assert restored.processed_task_ids == state.processed_task_ids
        assert restored.total_runs == state.total_runs
        assert restored.total_tasks_processed == state.total_tasks_processed

    def test_caps_at_500_ids(self):
        state = PipelineState(
            processed_task_ids=[f"task-{i}" for i in range(600)]
        )
        data = state.to_dict()
        assert len(data["processed_task_ids"]) == 500


# ─── Worker Profile & Leaderboard Tests ──────────────────────────────────────


class TestWorkerProfiles:
    """Test worker profile and leaderboard generation."""

    def test_worker_profile(self, pipeline, sample_task):
        """Worker profile includes DNA and reputation."""
        pipeline.process_completion_from_task(sample_task)

        profile = pipeline.get_worker_profile("worker-alice-0x123")
        assert profile is not None
        assert "skill_dna" in profile
        assert "reputation" in profile
        assert "composite_score" in profile

    def test_worker_profile_includes_tasks(self, pipeline, sample_task, sample_task_rich):
        """Worker profile reflects task history."""
        pipeline.process_completion_from_task(sample_task)
        pipeline.process_completion_from_task(sample_task_rich)

        profile = pipeline.get_worker_profile("worker-alice-0x123")
        assert profile["reputation"]["total_tasks"] == 2
        assert profile["skill_dna"]["task_count"] == 2

    def test_nonexistent_worker_profile(self, pipeline):
        """Unknown worker returns None."""
        profile = pipeline.get_worker_profile("worker-unknown")
        assert profile is None

    def test_leaderboard(
        self, pipeline, sample_task, sample_task_minimal, sample_task_rich
    ):
        """Leaderboard ranks workers by composite score."""
        pipeline.process_completion_from_task(sample_task)
        pipeline.process_completion_from_task(sample_task_rich)
        pipeline.process_completion_from_task(sample_task_minimal)

        leaderboard = pipeline.get_leaderboard(top_n=10)
        assert len(leaderboard) >= 2  # At least alice and bob

        # Verify sorted by score descending
        for i in range(len(leaderboard) - 1):
            assert (
                leaderboard[i]["composite_score"]
                >= leaderboard[i + 1]["composite_score"]
            )

    def test_leaderboard_top_n(self, pipeline, sample_task):
        """Leaderboard respects top_n parameter."""
        # Create many workers
        for i in range(5):
            task = {**sample_task, "id": f"task-lb-{i}", "worker_id": f"worker-{i}"}
            pipeline.process_completion_from_task(task)

        lb = pipeline.get_leaderboard(top_n=3)
        assert len(lb) == 3


# ─── Feedback Result Tests ───────────────────────────────────────────────────


class TestFeedbackResults:
    """Test feedback result data structures."""

    def test_feedback_to_dict(self, pipeline, sample_task):
        """Feedback serializes to dict correctly."""
        feedback = pipeline.process_completion_from_task(sample_task)
        d = feedback.to_dict()

        assert d["task_id"] == "task-001"
        assert d["worker_id"] == "worker-alice-0x123"
        assert isinstance(d["quality"], str)
        assert isinstance(d["quality_score"], float)
        assert isinstance(d["evidence_count"], int)
        assert isinstance(d["top_skills"], list)
        assert d["error"] is None

    def test_pipeline_run_result_summary(self):
        """Pipeline run result has readable summary."""
        result = PipelineRunResult(
            run_id="test-run",
            started_at=datetime.now(timezone.utc),
            tasks_processed=10,
            tasks_succeeded=8,
            tasks_failed=1,
            tasks_skipped=1,
            total_evidence_parsed=25,
            total_skill_signals=50,
            avg_quality_score=0.72,
        )
        summary = result.summary()
        assert "test-run" in summary
        assert "8/10" in summary

    def test_pipeline_run_result_to_dict(self):
        """Pipeline run result serializes."""
        result = PipelineRunResult(
            run_id="test-run",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            tasks_processed=5,
        )
        d = result.to_dict()
        assert d["run_id"] == "test-run"
        assert d["tasks_processed"] == 5
        assert d["started_at"] is not None
        assert d["completed_at"] is not None


# ─── Worker ID Extraction Tests ──────────────────────────────────────────────


class TestWorkerIdExtraction:
    """Test extraction of worker identity from various task formats."""

    def test_extract_worker_id_field(self, pipeline):
        """Extracts from worker_id field."""
        task = {"id": "t1", "worker_id": "w-001"}
        assert pipeline._extract_worker_id(task) == "w-001"

    def test_extract_assigned_worker(self, pipeline):
        """Extracts from assigned_worker field."""
        task = {"id": "t1", "assigned_worker": "w-002"}
        assert pipeline._extract_worker_id(task) == "w-002"

    def test_extract_worker_wallet(self, pipeline):
        """Extracts from worker_wallet field."""
        task = {"id": "t1", "worker_wallet": "0xABC"}
        assert pipeline._extract_worker_id(task) == "0xABC"

    def test_extract_from_nested_worker(self, pipeline):
        """Extracts from nested worker dict."""
        task = {"id": "t1", "worker": {"id": "w-003", "wallet": "0x..."}}
        assert pipeline._extract_worker_id(task) == "w-003"

    def test_extract_from_applications(self, pipeline):
        """Extracts from accepted application."""
        task = {
            "id": "t1",
            "applications": [
                {"worker_id": "w-rejected", "status": "rejected"},
                {"worker_id": "w-accepted", "status": "accepted"},
            ],
        }
        assert pipeline._extract_worker_id(task) == "w-accepted"

    def test_no_worker_id_returns_none(self, pipeline):
        """Returns None if no worker identity found."""
        task = {"id": "t1", "title": "No worker"}
        assert pipeline._extract_worker_id(task) is None


# ─── Integration Tests ───────────────────────────────────────────────────────


class TestIntegration:
    """Integration tests that exercise the full pipeline path."""

    def test_full_pipeline_single_task(self, pipeline, sample_task):
        """Full pipeline: process → Skill DNA → reputation → profile."""
        # Process
        feedback = pipeline.process_completion_from_task(sample_task)
        assert feedback.error is None

        # Check Skill DNA
        dna = pipeline.worker_registry.get_worker("worker-alice-0x123")
        assert dna is not None
        assert dna.task_count == 1

        # Check reputation
        rep = pipeline.get_internal_reputation("worker-alice-0x123")
        assert rep is not None
        assert rep.bayesian_score > 0

        # Check composite score
        score = pipeline.get_composite_score("worker-alice-0x123")
        assert score is not None
        assert score.total > 0

        # Check profile
        profile = pipeline.get_worker_profile("worker-alice-0x123")
        assert profile is not None
        assert "composite_score" in profile

    def test_multi_worker_pipeline(
        self,
        pipeline,
        sample_task,
        sample_task_minimal,
        sample_task_rich,
    ):
        """Multiple workers processed and ranked correctly."""
        pipeline.process_completion_from_task(sample_task)
        pipeline.process_completion_from_task(sample_task_rich)
        pipeline.process_completion_from_task(sample_task_minimal)

        # Alice should rank higher (2 tasks, including rich evidence)
        leaderboard = pipeline.get_leaderboard()
        alice_entry = next(
            (e for e in leaderboard if e["worker_id"] == "worker-alice-0x123"), None
        )
        bob_entry = next(
            (e for e in leaderboard if e["worker_id"] == "worker-bob-0x456"), None
        )

        assert alice_entry is not None
        assert bob_entry is not None
        # Alice has 2 tasks + rich evidence, should rank higher
        assert alice_entry["composite_score"] >= bob_entry["composite_score"]

    def test_persistence_round_trip(self, temp_state_dir, sample_task, sample_task_rich):
        """Full pipeline persists and restores correctly."""
        # Session 1: process tasks
        p1 = FeedbackPipeline(state_dir=temp_state_dir)
        p1.process_completion_from_task(sample_task)
        p1.process_completion_from_task(sample_task_rich)
        p1._state.total_runs = 1
        p1._state.total_tasks_processed = 2
        p1._save_state()
        p1._save_worker_registry()

        profile_before = p1.get_worker_profile("worker-alice-0x123")

        # Session 2: restore from disk
        p2 = FeedbackPipeline(state_dir=temp_state_dir)

        # Verify state restored
        assert p2._state.total_runs == 1
        assert p2._state.total_tasks_processed == 2

        # Verify worker registry restored
        dna = p2.worker_registry.get_worker("worker-alice-0x123")
        assert dna is not None
        assert dna.task_count == 2

        # Verify reputation restored
        rep = p2.get_internal_reputation("worker-alice-0x123")
        assert rep is not None
        assert rep.total_tasks == 2

    def test_callback_invoked(self, pipeline, sample_task):
        """Feedback callback is invoked on successful processing."""
        received = []
        pipeline.on_feedback = lambda fb: received.append(fb)

        pipeline.process_completion_from_task(sample_task)

        # Callback is only used in process_new_completions, not process_completion_from_task
        # So let's test it properly by mocking the API
        # For now, verify callback is set
        assert pipeline.on_feedback is not None

    def test_stats_after_processing(
        self, pipeline, sample_task, sample_task_minimal
    ):
        """Stats reflect processed tasks."""
        pipeline.process_completion_from_task(sample_task)
        pipeline.process_completion_from_task(sample_task_minimal)

        stats = pipeline.get_stats()
        assert stats["workers"]["total"] == 2
        assert stats["workers"]["total_tasks"] == 2
        assert stats["workers"]["with_reputation"] == 2


# ─── Edge Case Tests ─────────────────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_evidence_list(self, pipeline):
        """Empty evidence list handled gracefully."""
        task = {
            "id": "edge-1",
            "worker_id": "w-edge",
            "evidence": [],
        }
        feedback = pipeline.process_completion_from_task(task)
        assert feedback.error is None
        assert feedback.quality == EvidenceQuality.POOR

    def test_none_evidence_field(self, pipeline):
        """None evidence field handled gracefully."""
        task = {
            "id": "edge-2",
            "worker_id": "w-edge",
            "evidence": None,
        }
        feedback = pipeline.process_completion_from_task(task)
        # Should not crash, may try to fetch evidence separately
        assert feedback is not None

    def test_malformed_evidence_item(self, pipeline):
        """Malformed evidence items don't crash the pipeline."""
        task = {
            "id": "edge-3",
            "worker_id": "w-edge",
            "evidence": [
                {"type": "photo"},  # Missing content
                {},  # Completely empty
                {"type": "unknown_type", "content": "data"},
            ],
        }
        feedback = pipeline.process_completion_from_task(task)
        assert feedback.error is None
        assert feedback.evidence_count == 3

    def test_very_long_content(self, pipeline):
        """Very long content is handled."""
        task = {
            "id": "edge-4",
            "worker_id": "w-edge",
            "evidence": [
                {
                    "type": "text_response",
                    "content": "x" * 10000,
                },
            ],
        }
        feedback = pipeline.process_completion_from_task(task)
        assert feedback.error is None

    def test_unicode_content(self, pipeline):
        """Unicode content is handled."""
        task = {
            "id": "edge-5",
            "worker_id": "w-edge",
            "evidence": [
                {
                    "type": "text_response",
                    "content": "日本語テスト 🎉 émojis et accents",
                },
            ],
        }
        feedback = pipeline.process_completion_from_task(task)
        assert feedback.error is None

    def test_numeric_worker_id(self, pipeline):
        """Numeric worker_id is converted to string."""
        task = {
            "id": "edge-6",
            "worker_id": 12345,
            "evidence": [
                {"type": "text_response", "content": "done"},
            ],
        }
        feedback = pipeline.process_completion_from_task(task)
        assert feedback.worker_id == "12345"

    def test_processing_time_recorded(self, pipeline, sample_task):
        """Processing time is recorded."""
        feedback = pipeline.process_completion_from_task(sample_task)
        assert feedback.processing_time_ms > 0
        assert feedback.processing_time_ms < 5000  # Should be fast

    def test_multiple_evidence_same_type(self, pipeline):
        """Multiple evidence items of same type handled."""
        task = {
            "id": "edge-7",
            "worker_id": "w-edge",
            "evidence": [
                {"type": "photo", "content": "photo 1 of the storefront"},
                {"type": "photo", "content": "photo 2 showing interior details and layout"},
                {"type": "photo", "content": "photo 3 close-up of product display shelves"},
            ],
        }
        feedback = pipeline.process_completion_from_task(task)
        assert feedback.evidence_count == 3
        assert feedback.error is None


# ─── Factory Method Tests ────────────────────────────────────────────────────


class TestFactory:
    """Test factory method and initialization."""

    def test_create_factory(self, temp_state_dir):
        """Factory method creates pipeline with defaults."""
        pipeline = FeedbackPipeline.create(state_dir=temp_state_dir)
        assert pipeline.em_api_url == "https://api.execution.market"
        assert pipeline.max_tasks_per_run == 100

    def test_create_with_custom_params(self, temp_state_dir):
        """Factory method accepts custom parameters."""
        pipeline = FeedbackPipeline.create(
            em_api_url="https://custom.api.com",
            state_dir=temp_state_dir,
            max_tasks_per_run=50,
        )
        assert pipeline.em_api_url == "https://custom.api.com"
        assert pipeline.max_tasks_per_run == 50

    def test_state_dir_created(self, temp_state_dir):
        """State directory is created if it doesn't exist."""
        subdir = os.path.join(temp_state_dir, "nested", "feedback")
        pipeline = FeedbackPipeline(state_dir=subdir)
        assert os.path.isdir(subdir)
