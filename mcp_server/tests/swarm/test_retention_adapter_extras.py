"""
Tests for RetentionAdapter — the 11th DecisionSynthesizer signal.
=================================================================

Tests cover:
- RetentionSnapshot stability scoring
- Tenure bonus and risk level adjustments
- Cache behavior (fresh, stale, default)
- Scorer factory integration
- API failure graceful degradation
"""

import time
from unittest.mock import MagicMock

import pytest

from mcp_server.swarm.retention_adapter import (
    RetentionAdapter,
    RetentionSnapshot,
    make_retention_scorer,
    FRESH_TTL,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def adapter():
    return RetentionAdapter(
        autojob_base_url="http://localhost:9999",
        timeout_s=1.0,
    )


@pytest.fixture
def stable_snapshot():
    return RetentionSnapshot(
        wallet="0xStable",
        churn_probability=0.1,
        risk_level="stable",
        tenure_days=180,
        active_categories=3,
        confidence=0.85,
        fetched_at=time.time(),
    )


@pytest.fixture
def critical_snapshot():
    return RetentionSnapshot(
        wallet="0xCritical",
        churn_probability=0.9,
        risk_level="critical",
        estimated_days_to_churn=5.0,
        tenure_days=20,
        active_categories=1,
        confidence=0.7,
        fetched_at=time.time(),
    )


# ──────────────────────────────────────────────────────────────
# Stability Score Tests
# ──────────────────────────────────────────────────────────────


class TestStabilityScore:
    def test_stable_worker_high_score(self, stable_snapshot):
        """Stable worker with long tenure gets high stability score."""
        score = stable_snapshot.stability_score
        assert score > 80.0

    def test_critical_worker_low_score(self, critical_snapshot):
        """Critical risk worker gets low stability score."""
        score = critical_snapshot.stability_score
        assert score < 20.0

    def test_score_bounded_0_100(self):
        """Score always between 0 and 100."""
        for churn in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for risk in ["stable", "at_risk", "high_risk", "critical"]:
                snap = RetentionSnapshot(
                    wallet="0xTest",
                    churn_probability=churn,
                    risk_level=risk,
                    tenure_days=90,
                    fetched_at=time.time(),
                )
                assert 0.0 <= snap.stability_score <= 100.0

    def test_tenure_bonus(self):
        """Longer tenure provides stability bonus."""
        short = RetentionSnapshot(
            wallet="0xShort",
            churn_probability=0.3,
            risk_level="at_risk",
            tenure_days=10,
            fetched_at=time.time(),
        )
        long = RetentionSnapshot(
            wallet="0xLong",
            churn_probability=0.3,
            risk_level="at_risk",
            tenure_days=365,
            fetched_at=time.time(),
        )
        assert long.stability_score > short.stability_score

    def test_risk_adjustment(self):
        """Risk level adjusts score independently of churn probability."""
        base = RetentionSnapshot(
            wallet="0xBase",
            churn_probability=0.3,
            risk_level="at_risk",
            tenure_days=90,
            fetched_at=time.time(),
        )
        stable = RetentionSnapshot(
            wallet="0xBase",
            churn_probability=0.3,
            risk_level="stable",
            tenure_days=90,
            fetched_at=time.time(),
        )
        assert stable.stability_score > base.stability_score

    def test_zero_churn_max_score(self):
        """Zero churn with stable risk → near maximum score."""
        snap = RetentionSnapshot(
            wallet="0xPerfect",
            churn_probability=0.0,
            risk_level="stable",
            tenure_days=365,
            fetched_at=time.time(),
        )
        assert snap.stability_score >= 95.0


# ──────────────────────────────────────────────────────────────
# Cache Tests
# ──────────────────────────────────────────────────────────────


class TestAdapterCache:
    def test_stale_cache_on_failure(self, adapter, stable_snapshot):
        """Stale cache used when API unavailable."""
        stable_snapshot.fetched_at = time.time() - FRESH_TTL - 10
        adapter._cache["0xstable"] = stable_snapshot

        result = adapter.analyze("0xStable")
        assert result.from_cache is True

    def test_default_on_total_failure(self, adapter):
        """Default result when no cache and API fails."""
        result = adapter.analyze("0xUnknown")
        assert result.churn_probability == 0.3
        assert result.risk_level == "at_risk"
        assert result.confidence == 0.1

    def test_stats_tracking(self, adapter, stable_snapshot):
        """Statistics properly tracked."""
        adapter._cache["0xstable"] = stable_snapshot
        adapter.analyze("0xStable")
        adapter.analyze("0xStable")

        stats = adapter.stats()
        assert stats["total_requests"] == 2
        assert stats["cache_hits"] == 2
        assert stats["hit_rate"] == 1.0

    def test_case_insensitive_cache(self, adapter, stable_snapshot):
        """Cache lookups are case-insensitive."""
        adapter._cache["0xstable"] = stable_snapshot
        r1 = adapter.analyze("0xStable")
        r2 = adapter.analyze("0xSTABLE")
        assert r1.from_cache is True
        assert r2.from_cache is True


# ──────────────────────────────────────────────────────────────
# Scorer Tests
# ──────────────────────────────────────────────────────────────


class TestRetentionScorer:
    def test_scorer_returns_callable(self, adapter):
        scorer = make_retention_scorer(adapter)
        assert callable(scorer)

    def test_stable_worker_scores_high(self, adapter, stable_snapshot):
        """Stable worker gets high routing score."""
        adapter._cache["0xstable"] = stable_snapshot
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {"wallet": "0xStable"})
        assert score > 80.0

    def test_critical_worker_scores_low(self, adapter, critical_snapshot):
        """Critical risk worker gets low routing score."""
        adapter._cache["0xcritical"] = critical_snapshot
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {"wallet": "0xCritical"})
        assert score < 20.0

    def test_no_wallet_neutral(self, adapter):
        """No wallet → neutral score."""
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {})
        assert score == 50.0

    def test_error_neutral(self, adapter):
        """Errors return neutral score."""
        adapter.analyze = MagicMock(side_effect=RuntimeError("boom"))
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {"wallet": "0xTest"})
        assert score == 50.0

    def test_uses_address_field(self, adapter, stable_snapshot):
        """Scorer also checks 'address' field for wallet."""
        adapter._cache["0xstable"] = stable_snapshot
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {"address": "0xStable"})
        assert score > 80.0


# ──────────────────────────────────────────────────────────────
# Snapshot Tests
# ──────────────────────────────────────────────────────────────


class TestRetentionSnapshot:
    def test_age_seconds(self):
        snap = RetentionSnapshot(wallet="0x", fetched_at=time.time() - 100)
        assert 99 < snap.age_seconds < 102

    def test_defaults(self):
        snap = RetentionSnapshot(wallet="0xDefault")
        assert snap.churn_probability == 0.3
        assert snap.risk_level == "at_risk"
        assert snap.estimated_days_to_churn is None
