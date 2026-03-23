"""Tests for RetentionAdapter — 11th signal: worker churn prediction."""

import time
import pytest

from mcp_server.swarm.retention_adapter import (
    RetentionAdapter,
    RetentionSnapshot,
    make_retention_scorer,
)


@pytest.fixture
def adapter():
    return RetentionAdapter(autojob_base_url="http://localhost:19999", timeout_s=0.5)


@pytest.fixture
def stable_snapshot():
    return RetentionSnapshot(
        wallet="0xStable",
        churn_probability=0.1,
        risk_level="stable",
        tenure_days=90,
        active_categories=3,
        signal_count=6,
        confidence=0.8,
        fetched_at=time.time(),
    )


@pytest.fixture
def risky_snapshot():
    return RetentionSnapshot(
        wallet="0xRisky",
        churn_probability=0.85,
        risk_level="critical",
        tenure_days=15,
        active_categories=1,
        signal_count=4,
        confidence=0.7,
        fetched_at=time.time(),
    )


class TestRetentionSnapshot:
    def test_age_seconds(self, stable_snapshot):
        assert 0 <= stable_snapshot.age_seconds < 5

    def test_stability_score_stable(self, stable_snapshot):
        score = stable_snapshot.stability_score
        assert score > 50  # High stability for low churn

    def test_stability_score_critical(self, risky_snapshot):
        score = risky_snapshot.stability_score
        assert score < 50  # Low stability for high churn

    def test_stable_higher_than_risky(self, stable_snapshot, risky_snapshot):
        assert stable_snapshot.stability_score > risky_snapshot.stability_score


class TestRetentionAdapter:
    def test_init(self):
        adapter = RetentionAdapter()
        assert hasattr(adapter, 'base_url')

    def test_analyze_returns_snapshot_on_failure(self, adapter):
        result = adapter.analyze("0xTest")
        assert isinstance(result, RetentionSnapshot)
        assert result.wallet == "0xTest"

    def test_analyze_consistent_wallet(self, adapter):
        """Same wallet returns snapshot with correct wallet field."""
        r1 = adapter.analyze("0xCached")
        r2 = adapter.analyze("0xCached")
        assert r1.wallet == r2.wallet == "0xCached"

    def test_stats(self, adapter):
        stats = adapter.stats()
        assert isinstance(stats, dict)


class TestRetentionScorer:
    def test_scorer_callable(self, adapter):
        scorer = make_retention_scorer(adapter)
        assert callable(scorer)

    def test_scorer_returns_float(self, adapter):
        scorer = make_retention_scorer(adapter)
        score = scorer({"category": "test"}, {"wallet": "0xW"})
        assert isinstance(score, (int, float))

    def test_scorer_consistent(self, adapter):
        scorer = make_retention_scorer(adapter)
        task = {"category": "test"}
        cand = {"wallet": "0xSame"}
        assert scorer(task, cand) == scorer(task, cand)
