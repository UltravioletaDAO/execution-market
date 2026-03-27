"""Tests for DecompositionAdapter — 10th signal: compound task analysis."""

import time
import pytest

from mcp_server.swarm.decomposition_adapter import (
    DecompositionAdapter,
    DecompositionSnapshot,
    SubTaskSnapshot,
    make_decomposition_scorer,
    _task_hash,
)


@pytest.fixture
def adapter():
    return DecompositionAdapter(
        autojob_base_url="http://localhost:19999", timeout_s=0.5
    )


@pytest.fixture
def simple_task():
    return {"title": "Take a photo", "description": "Photo of the sky"}


@pytest.fixture
def compound_task():
    return {
        "title": "Build Flask API with tests and deploy",
        "description": "Create REST API with PostgreSQL, write tests, deploy with Docker to AWS ECS",
    }


@pytest.fixture
def snapshot():
    return DecompositionSnapshot(
        task_hash="abc123",
        is_compound=True,
        sub_task_count=3,
        sub_tasks=[
            SubTaskSnapshot(
                title="Build API",
                task_type="coding",
                required_skills=["python", "flask"],
            ),
            SubTaskSnapshot(
                title="Write tests", task_type="testing", required_skills=["pytest"]
            ),
            SubTaskSnapshot(
                title="Deploy", task_type="devops", required_skills=["docker", "aws"]
            ),
        ],
        unique_skills=["python", "flask", "pytest", "docker", "aws"],
        complexity="complex",
        fetched_at=time.time(),
    )


class TestSubTaskSnapshot:
    def test_creation(self):
        st = SubTaskSnapshot(
            title="Test", task_type="coding", required_skills=["python"]
        )
        assert st.title == "Test"
        assert st.required_skills == ["python"]
        assert st.task_type == "coding"


class TestDecompositionSnapshot:
    def test_age_seconds(self, snapshot):
        assert 0 <= snapshot.age_seconds < 5

    def test_skill_coverage_full(self, snapshot):
        score = snapshot.skill_coverage_score(
            ["python", "flask", "pytest", "docker", "aws"]
        )
        assert score == 100.0

    def test_skill_coverage_partial(self, snapshot):
        score = snapshot.skill_coverage_score(["python", "flask"])
        assert 0 < score < 100.0

    def test_skill_coverage_none(self, snapshot):
        score = snapshot.skill_coverage_score(["javascript"])
        assert score == 0.0

    def test_skill_coverage_empty(self, snapshot):
        score = snapshot.skill_coverage_score([])
        assert score == 0.0

    def test_complexity_multiplier_complex(self, snapshot):
        assert snapshot.complexity_multiplier >= 1.0  # "complex" = 1.0

    def test_complexity_multiplier_simple(self):
        snap = DecompositionSnapshot(
            task_hash="x",
            is_compound=False,
            sub_task_count=1,
            sub_tasks=[],
            unique_skills=[],
            complexity="simple",
            fetched_at=time.time(),
        )
        assert snap.complexity_multiplier < 1.0  # "simple" = 0.7

    def test_complexity_multiplier_expert(self):
        snap = DecompositionSnapshot(
            task_hash="x",
            is_compound=True,
            sub_task_count=5,
            sub_tasks=[],
            unique_skills=[],
            complexity="expert",
            fetched_at=time.time(),
        )
        assert snap.complexity_multiplier > 1.0  # "expert" = 1.15


class TestDecompositionAdapter:
    def test_init(self):
        adapter = DecompositionAdapter()
        assert hasattr(adapter, "base_url")

    def test_analyze_returns_snapshot(self, adapter, simple_task):
        result = adapter.analyze(simple_task)
        assert isinstance(result, DecompositionSnapshot)

    def test_analyze_consistent_hash(self, adapter, simple_task):
        r1 = adapter.analyze(simple_task)
        r2 = adapter.analyze(simple_task)
        assert r1.task_hash == r2.task_hash

    def test_different_hashes(self, simple_task, compound_task):
        assert _task_hash(simple_task) != _task_hash(compound_task)

    def test_stats(self, adapter):
        assert isinstance(adapter.stats(), dict)


class TestTaskHash:
    def test_deterministic(self):
        task = {"title": "Hello", "description": "World"}
        assert _task_hash(task) == _task_hash(task)

    def test_different_tasks(self):
        assert _task_hash({"title": "A"}) != _task_hash({"title": "B"})

    def test_missing_fields(self):
        h = _task_hash({"title": "Only title"})
        assert isinstance(h, str) and len(h) > 0


class TestDecompositionScorer:
    def test_callable(self, adapter):
        scorer = make_decomposition_scorer(adapter)
        assert callable(scorer)

    def test_returns_float(self, adapter, simple_task):
        scorer = make_decomposition_scorer(adapter)
        score = scorer(simple_task, {"wallet": "0xW"})
        assert isinstance(score, (int, float))

    def test_consistent(self, adapter, simple_task):
        scorer = make_decomposition_scorer(adapter)
        c = {"wallet": "0xSame"}
        assert scorer(simple_task, c) == scorer(simple_task, c)
