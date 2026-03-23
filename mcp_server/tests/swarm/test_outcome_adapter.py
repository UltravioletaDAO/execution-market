"""Tests for OutcomeAdapter — 9th signal: success probability prediction."""

import time
import pytest

from mcp_server.swarm.outcome_adapter import (
    OutcomeAdapter,
    PredictionSnapshot,
    make_outcome_scorer,
)


@pytest.fixture
def adapter():
    return OutcomeAdapter(autojob_url="http://localhost:19999", timeout_seconds=0.5)


@pytest.fixture
def snapshot():
    return PredictionSnapshot(
        wallet="0xTest",
        category="physical_presence",
        success_probability=0.82,
        confidence=0.75,
        recommendation="proceed",
        risk_count=1,
        risk_names=["timing_risk"],
        fetched_at=time.time(),
        source="api",
    )


class TestPredictionSnapshot:
    def test_is_fresh_recent(self, snapshot):
        assert snapshot.is_fresh is True

    def test_is_fresh_expired(self, snapshot):
        snapshot.fetched_at = time.time() - 2000
        assert snapshot.is_fresh is False

    def test_is_stale_usable(self, snapshot):
        snapshot.fetched_at = time.time() - 7200
        assert snapshot.is_stale_usable is True

    def test_is_stale_too_old(self, snapshot):
        snapshot.fetched_at = time.time() - 20000
        assert snapshot.is_stale_usable is False

    def test_age_seconds(self, snapshot):
        assert 0 <= snapshot.age_seconds < 5


class TestOutcomeAdapter:
    def test_init_defaults(self):
        adapter = OutcomeAdapter()
        assert hasattr(adapter, 'autojob_url') or hasattr(adapter, '_autojob_url')

    def test_predict_returns_snapshot_on_failure(self, adapter):
        result = adapter.predict("0xTest", "physical_presence")
        assert isinstance(result, PredictionSnapshot)
        assert result.source == "default"

    def test_predict_default_values(self, adapter):
        result = adapter.predict("0xTest", "physical_presence")
        assert result.success_probability == 0.5
        assert result.confidence == 0.1

    def test_predict_caches(self, adapter):
        r1 = adapter.predict("0xCached", "digital")
        r2 = adapter.predict("0xCached", "digital")
        assert r1.fetched_at == r2.fetched_at

    def test_predict_batch(self, adapter):
        results = adapter.predict_batch("physical_presence", ["0xA", "0xB", "0xC"])
        assert len(results) == 3
        assert all(isinstance(r, PredictionSnapshot) for r in results)

    def test_stats(self, adapter):
        stats = adapter.get_stats()
        assert isinstance(stats, dict)

    def test_clear_cache(self, adapter):
        adapter.predict("0xA", "cat1")
        cleared = adapter.clear_cache()
        assert cleared >= 0


class TestOutcomeScorer:
    def test_scorer_callable(self, adapter):
        scorer = make_outcome_scorer(adapter)
        assert callable(scorer)

    def test_scorer_returns_float(self, adapter):
        scorer = make_outcome_scorer(adapter)
        score = scorer({"category": "physical_presence"}, {"wallet": "0xW"})
        assert isinstance(score, (int, float))

    def test_scorer_consistent(self, adapter):
        scorer = make_outcome_scorer(adapter)
        task = {"category": "test"}
        candidate = {"wallet": "0xSame"}
        assert scorer(task, candidate) == scorer(task, candidate)
