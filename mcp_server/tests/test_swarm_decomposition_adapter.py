"""
Tests for DecompositionAdapter — the 10th DecisionSynthesizer signal.
=====================================================================

Tests cover:
- DecompositionSnapshot skill coverage scoring
- Complexity multiplier effects
- Cache behavior (fresh, stale, miss)
- API failure graceful degradation
- Scorer factory integration
- Task hash stability
- SubTaskSnapshot construction
"""

import time
from unittest.mock import MagicMock

import pytest

from mcp_server.swarm.decomposition_adapter import (
    DecompositionAdapter,
    DecompositionSnapshot,
    SubTaskSnapshot,
    make_decomposition_scorer,
    _task_hash,
    FRESH_TTL,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def adapter():
    """DecompositionAdapter pointed at localhost (no real server)."""
    return DecompositionAdapter(
        autojob_base_url="http://localhost:9999",
        timeout_s=1.0,
    )


@pytest.fixture
def compound_snapshot():
    """A compound task snapshot with multiple sub-tasks."""
    return DecompositionSnapshot(
        task_hash="abc123",
        is_compound=True,
        sub_task_count=3,
        sub_tasks=[
            SubTaskSnapshot(
                title="Build React frontend",
                task_type="frontend",
                required_skills=["react", "css", "html"],
                estimated_hours=4.0,
                difficulty=0.6,
            ),
            SubTaskSnapshot(
                title="Build Python API",
                task_type="backend",
                required_skills=["python", "fastapi", "postgresql"],
                estimated_hours=3.0,
                difficulty=0.7,
            ),
            SubTaskSnapshot(
                title="Deploy to AWS",
                task_type="devops",
                required_skills=["docker", "aws", "ci_cd"],
                estimated_hours=2.0,
                difficulty=0.8,
            ),
        ],
        unique_skills=[
            "react",
            "css",
            "html",
            "python",
            "fastapi",
            "postgresql",
            "docker",
            "aws",
            "ci_cd",
        ],
        complexity="complex",
        team_strategy="specialist",
        estimated_hours=9.0,
        team_size=3,
        fetched_at=time.time(),
    )


@pytest.fixture
def simple_snapshot():
    """A simple (non-compound) task snapshot."""
    return DecompositionSnapshot(
        task_hash="def456",
        is_compound=False,
        sub_task_count=1,
        sub_tasks=[
            SubTaskSnapshot(
                title="Take photo of store",
                task_type="verification",
                required_skills=["photography"],
                estimated_hours=0.5,
                difficulty=0.2,
            ),
        ],
        unique_skills=["photography"],
        complexity="simple",
        fetched_at=time.time(),
    )


# ──────────────────────────────────────────────────────────────
# DecompositionSnapshot Tests
# ──────────────────────────────────────────────────────────────


class TestDecompositionSnapshot:
    def test_skill_coverage_full_match(self, compound_snapshot):
        """Candidate with all skills gets high coverage."""
        all_skills = [
            "react",
            "css",
            "html",
            "python",
            "fastapi",
            "postgresql",
            "docker",
            "aws",
            "ci_cd",
        ]
        score = compound_snapshot.skill_coverage_score(all_skills)
        assert score > 90.0

    def test_skill_coverage_no_match(self, compound_snapshot):
        """Candidate with no relevant skills gets zero coverage."""
        score = compound_snapshot.skill_coverage_score(["java", "spring", "oracle"])
        assert score == 0.0

    def test_skill_coverage_partial_match(self, compound_snapshot):
        """Candidate with some skills gets partial coverage."""
        score = compound_snapshot.skill_coverage_score(["react", "css", "html"])
        assert 20.0 < score < 60.0

    def test_skill_coverage_empty_skills(self, compound_snapshot):
        """Candidate with no skills gets zero."""
        score = compound_snapshot.skill_coverage_score([])
        assert score == 0.0

    def test_skill_coverage_no_requirements(self):
        """Task with no skills → neutral score."""
        snap = DecompositionSnapshot(task_hash="x", unique_skills=[])
        assert snap.skill_coverage_score(["python"]) == 50.0

    def test_skill_coverage_case_insensitive(self, compound_snapshot):
        """Skill matching is case-insensitive."""
        score_lower = compound_snapshot.skill_coverage_score(
            ["react", "python", "docker"]
        )
        score_upper = compound_snapshot.skill_coverage_score(
            ["React", "Python", "Docker"]
        )
        assert score_lower == score_upper

    def test_complexity_multiplier_simple(self):
        snap = DecompositionSnapshot(task_hash="x", complexity="simple")
        assert snap.complexity_multiplier == 0.7

    def test_complexity_multiplier_complex(self):
        snap = DecompositionSnapshot(task_hash="x", complexity="complex")
        assert snap.complexity_multiplier == 1.0

    def test_complexity_multiplier_expert(self):
        snap = DecompositionSnapshot(task_hash="x", complexity="expert")
        assert snap.complexity_multiplier == 1.15

    def test_age_seconds(self):
        snap = DecompositionSnapshot(task_hash="x", fetched_at=time.time() - 100)
        assert 99 < snap.age_seconds < 102

    def test_is_compound_flag(self, compound_snapshot, simple_snapshot):
        assert compound_snapshot.is_compound is True
        assert simple_snapshot.is_compound is False


# ──────────────────────────────────────────────────────────────
# Task Hash Tests
# ──────────────────────────────────────────────────────────────


class TestTaskHash:
    def test_deterministic(self):
        """Same task produces same hash."""
        task = {"title": "Build app", "description": "Full stack", "category": "tech"}
        h1 = _task_hash(task)
        h2 = _task_hash(task)
        assert h1 == h2

    def test_different_tasks_different_hashes(self):
        t1 = {"title": "Build app"}
        t2 = {"title": "Take photo"}
        assert _task_hash(t1) != _task_hash(t2)

    def test_hash_length(self):
        h = _task_hash({"title": "test"})
        assert len(h) == 16


# ──────────────────────────────────────────────────────────────
# Adapter Cache Tests
# ──────────────────────────────────────────────────────────────


class TestAdapterCache:
    def test_fresh_cache_hit(self, adapter, compound_snapshot):
        """Fresh cache entries are returned without API call."""
        th = _task_hash({"title": "Build app", "category": "tech"})
        compound_snapshot.task_hash = th
        adapter._cache[th] = compound_snapshot

        result = adapter.analyze({"title": "Build app", "category": "tech"})
        assert result.from_cache is True
        assert result.is_compound is True
        assert adapter._cache_hits == 1
        assert adapter._api_calls == 0

    def test_stale_cache_used_on_api_failure(self, adapter, compound_snapshot):
        """Stale cache is used when API fails."""
        th = _task_hash({"title": "Build app"})
        compound_snapshot.task_hash = th
        compound_snapshot.fetched_at = (
            time.time() - FRESH_TTL - 10
        )  # Expired fresh, still within stale
        adapter._cache[th] = compound_snapshot

        # API will fail (no server running)
        result = adapter.analyze({"title": "Build app"})
        assert result.from_cache is True
        assert adapter._api_errors >= 1

    def test_default_on_total_failure(self, adapter):
        """Default non-compound result when cache empty and API fails."""
        result = adapter.analyze({"title": "Nonexistent task"})
        assert result.is_compound is False
        assert result.sub_task_count == 1

    def test_stats_tracking(self, adapter, compound_snapshot):
        """Stats are properly tracked."""
        th = _task_hash({"title": "Test"})
        compound_snapshot.task_hash = th
        adapter._cache[th] = compound_snapshot

        adapter.analyze({"title": "Test"})
        adapter.analyze({"title": "Test"})

        stats = adapter.stats()
        assert stats["total_requests"] == 2
        assert stats["cache_hits"] == 2
        assert stats["cache_size"] == 1
        assert stats["hit_rate"] == 1.0


# ──────────────────────────────────────────────────────────────
# Scorer Factory Tests
# ──────────────────────────────────────────────────────────────


class TestDecompositionScorer:
    def test_scorer_returns_callable(self, adapter):
        scorer = make_decomposition_scorer(adapter)
        assert callable(scorer)

    def test_scorer_simple_task_neutral(self, adapter, simple_snapshot):
        """Simple tasks score neutral (50)."""
        th = _task_hash({"title": "Take photo"})
        simple_snapshot.task_hash = th
        adapter._cache[th] = simple_snapshot

        scorer = make_decomposition_scorer(adapter)
        score = scorer({"title": "Take photo"}, {"skills": ["photography"]})
        assert score == 50.0

    def test_scorer_compound_full_coverage(self, adapter, compound_snapshot):
        """Candidate with all skills scores high on compound task."""
        th = _task_hash({"title": "Build full stack"})
        compound_snapshot.task_hash = th
        adapter._cache[th] = compound_snapshot

        scorer = make_decomposition_scorer(adapter)
        all_skills = [
            "react",
            "css",
            "html",
            "python",
            "fastapi",
            "postgresql",
            "docker",
            "aws",
            "ci_cd",
        ]
        score = scorer({"title": "Build full stack"}, {"skills": all_skills})
        assert score > 80.0

    def test_scorer_compound_no_coverage(self, adapter, compound_snapshot):
        """Candidate with no relevant skills scores low on compound task."""
        th = _task_hash({"title": "Build full stack"})
        compound_snapshot.task_hash = th
        adapter._cache[th] = compound_snapshot

        scorer = make_decomposition_scorer(adapter)
        score = scorer(
            {"title": "Build full stack"}, {"skills": ["cooking", "cleaning"]}
        )
        assert score < 10.0

    def test_scorer_uses_skill_dna(self, adapter, compound_snapshot):
        """Scorer extracts skills from skill_dna field too."""
        th = _task_hash({"title": "Build app"})
        compound_snapshot.task_hash = th
        adapter._cache[th] = compound_snapshot

        scorer = make_decomposition_scorer(adapter)
        score = scorer(
            {"title": "Build app"},
            {"skills": [], "skill_dna": {"react": 0.9, "css": 0.8, "html": 0.7}},
        )
        assert score > 0.0

    def test_scorer_handles_error_gracefully(self, adapter):
        """Scorer returns neutral on internal errors."""
        # Force an error by breaking the adapter
        adapter.analyze = MagicMock(side_effect=RuntimeError("boom"))
        scorer = make_decomposition_scorer(adapter)
        score = scorer({"title": "test"}, {"skills": []})
        assert score == 50.0

    def test_scorer_capped_at_100(self, adapter):
        """Score never exceeds 100."""
        snap = DecompositionSnapshot(
            task_hash=_task_hash({"title": "Easy"}),
            is_compound=True,
            unique_skills=["python"],
            complexity="expert",  # multiplier 1.15
            sub_tasks=[
                SubTaskSnapshot(
                    title="Code",
                    task_type="code",
                    required_skills=["python"],
                    difficulty=0.1,
                )
            ],
            fetched_at=time.time(),
        )
        adapter._cache[snap.task_hash] = snap

        scorer = make_decomposition_scorer(adapter)
        score = scorer({"title": "Easy"}, {"skills": ["python"]})
        assert score <= 100.0


# ──────────────────────────────────────────────────────────────
# SubTaskSnapshot Tests
# ──────────────────────────────────────────────────────────────


class TestSubTaskSnapshot:
    def test_construction(self):
        st = SubTaskSnapshot(
            title="Build API",
            task_type="backend",
            required_skills=["python", "flask"],
            estimated_hours=3.0,
            difficulty=0.7,
        )
        assert st.title == "Build API"
        assert len(st.required_skills) == 2
        assert st.difficulty == 0.7

    def test_defaults(self):
        st = SubTaskSnapshot(title="Test", task_type="test")
        assert st.required_skills == []
        assert st.estimated_hours == 1.0
        assert st.difficulty == 0.5
        assert st.bounty_share == 0.0
