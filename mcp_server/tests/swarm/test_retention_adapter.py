"""Tests for RetentionAdapter — 11th signal: worker churn prediction.

Coverage targets:
- RetentionSnapshot: stability_score formula, boundaries, tenure bonus, risk adjustments
- RetentionAdapter: 4-tier fallback, caching (fresh/stale/expired), wallet normalization, stats
- make_retention_scorer: worker-level signal, error handling, neutral defaults
"""

import time
import pytest

from mcp_server.swarm.retention_adapter import (
    RetentionAdapter,
    RetentionSnapshot,
    make_retention_scorer,
    FRESH_TTL,
    STALE_TTL,
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


# ──────────────────────────────────────────────────────────────
# RetentionSnapshot Tests
# ──────────────────────────────────────────────────────────────


class TestRetentionSnapshot:
    def test_age_seconds_fresh(self, stable_snapshot):
        assert 0 <= stable_snapshot.age_seconds < 5

    def test_age_seconds_zero_fetched_at(self):
        snap = RetentionSnapshot(wallet="0xTest", fetched_at=0.0)
        assert snap.age_seconds == float("inf")

    def test_stability_score_stable(self, stable_snapshot):
        score = stable_snapshot.stability_score
        assert score > 50  # High stability for low churn

    def test_stability_score_critical(self, risky_snapshot):
        score = risky_snapshot.stability_score
        assert score < 50  # Low stability for high churn

    def test_stable_higher_than_risky(self, stable_snapshot, risky_snapshot):
        assert stable_snapshot.stability_score > risky_snapshot.stability_score

    def test_stability_score_perfect_worker(self):
        """Zero churn, long tenure, stable → near max."""
        snap = RetentionSnapshot(
            wallet="0xPerfect",
            churn_probability=0.0,
            risk_level="stable",
            tenure_days=365,
            fetched_at=time.time(),
        )
        score = snap.stability_score
        # base: 100, tenure: +10 (capped), risk: +5 = capped at 100
        assert score >= 95

    def test_stability_score_worst_worker(self):
        """Max churn, critical risk → near zero."""
        snap = RetentionSnapshot(
            wallet="0xWorst",
            churn_probability=1.0,
            risk_level="critical",
            tenure_days=0,
            fetched_at=time.time(),
        )
        score = snap.stability_score
        # base: 0, tenure: 0, risk: -20 → clamped to 0
        assert score == 0.0

    def test_stability_score_clamped_to_100(self):
        snap = RetentionSnapshot(
            wallet="0xMax",
            churn_probability=0.0,
            risk_level="stable",
            tenure_days=1000,  # Very long tenure
            fetched_at=time.time(),
        )
        assert snap.stability_score <= 100.0

    def test_stability_score_clamped_to_0(self):
        snap = RetentionSnapshot(
            wallet="0xMin",
            churn_probability=1.0,
            risk_level="critical",
            fetched_at=time.time(),
        )
        assert snap.stability_score >= 0.0

    def test_tenure_bonus_increases_score(self):
        """Longer tenure → higher stability."""
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
            tenure_days=180,
            fetched_at=time.time(),
        )
        assert long.stability_score > short.stability_score

    def test_tenure_bonus_capped(self):
        """Tenure bonus maxes at 10 (1 year ≈ 365 days)."""
        one_year = RetentionSnapshot(
            wallet="0x1Y",
            churn_probability=0.3,
            risk_level="at_risk",
            tenure_days=365,
            fetched_at=time.time(),
        )
        ten_years = RetentionSnapshot(
            wallet="0x10Y",
            churn_probability=0.3,
            risk_level="at_risk",
            tenure_days=3650,
            fetched_at=time.time(),
        )
        # Both should have the same tenure bonus (capped at 10)
        assert one_year.stability_score == pytest.approx(
            ten_years.stability_score, abs=0.1
        )

    def test_risk_level_ordering(self):
        """stable > at_risk > high_risk > critical for same churn."""

        def make(risk):
            return RetentionSnapshot(
                wallet="0xTest",
                churn_probability=0.3,
                risk_level=risk,
                tenure_days=30,
                fetched_at=time.time(),
            )

        assert make("stable").stability_score > make("at_risk").stability_score
        assert make("at_risk").stability_score > make("high_risk").stability_score
        assert make("high_risk").stability_score > make("critical").stability_score

    def test_unknown_risk_level(self):
        """Unknown risk level uses 0 adjustment (same as at_risk)."""
        at_risk = RetentionSnapshot(
            wallet="0xTest",
            risk_level="at_risk",
            churn_probability=0.3,
            tenure_days=30,
            fetched_at=time.time(),
        )
        unknown = RetentionSnapshot(
            wallet="0xTest",
            risk_level="something_new",
            churn_probability=0.3,
            tenure_days=30,
            fetched_at=time.time(),
        )
        assert at_risk.stability_score == unknown.stability_score

    def test_default_values(self):
        snap = RetentionSnapshot(wallet="0xDefault")
        assert snap.churn_probability == 0.3
        assert snap.risk_level == "at_risk"
        assert snap.estimated_days_to_churn is None
        assert snap.tenure_days == 0.0
        assert snap.confidence == 0.3
        assert snap.from_cache is False

    def test_from_cache_flag(self):
        snap = RetentionSnapshot(wallet="0xCached", from_cache=True)
        assert snap.from_cache is True


# ──────────────────────────────────────────────────────────────
# Adapter Core Tests
# ──────────────────────────────────────────────────────────────


class TestRetentionAdapter:
    def test_init(self):
        adapter = RetentionAdapter()
        assert hasattr(adapter, "base_url")
        assert adapter._total_requests == 0

    def test_init_custom_url(self):
        adapter = RetentionAdapter(
            autojob_base_url="http://custom:5000",
            timeout_s=10.0,
        )
        assert adapter.base_url == "http://custom:5000"
        assert adapter.timeout_s == 10.0

    def test_init_strips_trailing_slash(self):
        adapter = RetentionAdapter(autojob_base_url="http://host:9999/")
        assert adapter.base_url == "http://host:9999"

    def test_analyze_returns_snapshot_on_failure(self, adapter):
        """When API is unreachable, returns default (tier 4)."""
        result = adapter.analyze("0xTest")
        assert isinstance(result, RetentionSnapshot)
        assert result.wallet == "0xTest"

    def test_analyze_default_has_low_confidence(self, adapter):
        result = adapter.analyze("0xUnknown")
        assert result.confidence <= 0.2

    def test_analyze_consistent_wallet(self, adapter):
        """Same wallet returns snapshot with correct wallet field."""
        r1 = adapter.analyze("0xCached")
        r2 = adapter.analyze("0xCached")
        assert r1.wallet == r2.wallet == "0xCached"

    def test_different_wallets(self, adapter):
        r1 = adapter.analyze("0xAlice")
        r2 = adapter.analyze("0xBob")
        assert r1.wallet != r2.wallet

    def test_stats(self, adapter):
        stats = adapter.stats()
        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "cache_hits" in stats
        assert "api_calls" in stats
        assert "api_errors" in stats
        assert "cache_size" in stats
        assert "hit_rate" in stats

    def test_stats_after_operations(self, adapter):
        adapter.analyze("0xA")
        adapter.analyze("0xB")
        stats = adapter.stats()
        assert stats["total_requests"] == 2
        assert stats["api_calls"] >= 2
        assert stats["api_errors"] >= 2

    def test_stats_hit_rate_zero_initially(self, adapter):
        assert adapter.stats()["hit_rate"] == 0


# ──────────────────────────────────────────────────────────────
# Adapter Caching Tests
# ──────────────────────────────────────────────────────────────


class TestAdapterCaching:
    def test_fresh_cache_hit(self, adapter):
        """Inject a fresh snapshot → analyze returns it."""
        fresh = RetentionSnapshot(
            wallet="0xFresh",
            churn_probability=0.15,
            confidence=0.9,
            fetched_at=time.time(),
        )
        adapter._cache["0xfresh"] = fresh

        result = adapter.analyze("0xFresh")
        assert result.churn_probability == 0.15
        assert result.from_cache is True
        assert adapter._cache_hits == 1

    def test_stale_cache_fallback(self, adapter):
        """Stale but not expired → used when API fails."""
        stale = RetentionSnapshot(
            wallet="0xStale",
            churn_probability=0.4,
            risk_level="high_risk",
            confidence=0.7,
            fetched_at=time.time() - FRESH_TTL - 10,
        )
        adapter._cache["0xstale"] = stale

        result = adapter.analyze("0xStale")
        assert result.churn_probability == 0.4
        assert result.from_cache is True

    def test_expired_cache_returns_default(self, adapter):
        """Fully expired cache → returns default."""
        expired = RetentionSnapshot(
            wallet="0xExpired",
            churn_probability=0.9,
            fetched_at=time.time() - STALE_TTL - 10,
        )
        adapter._cache["0xexpired"] = expired

        result = adapter.analyze("0xExpired")
        assert result.confidence <= 0.2  # Default confidence

    def test_cache_key_normalization(self, adapter):
        """Wallet keys are lowercased."""
        adapter._cache["0xabc123"] = RetentionSnapshot(
            wallet="0xABC123",
            churn_probability=0.2,
            fetched_at=time.time(),
        )

        result = adapter.analyze("0xABC123")
        assert result.churn_probability == 0.2

    def test_multiple_wallets_cached_independently(self, adapter):
        adapter._cache["0xalice"] = RetentionSnapshot(
            wallet="0xAlice", churn_probability=0.1, fetched_at=time.time()
        )
        adapter._cache["0xbob"] = RetentionSnapshot(
            wallet="0xBob", churn_probability=0.8, fetched_at=time.time()
        )

        alice = adapter.analyze("0xAlice")
        bob = adapter.analyze("0xBob")
        assert alice.churn_probability == 0.1
        assert bob.churn_probability == 0.8


# ──────────────────────────────────────────────────────────────
# Scorer Tests
# ──────────────────────────────────────────────────────────────


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

    def test_scorer_worker_level(self, adapter):
        """Same wallet → same score regardless of task."""
        scorer = make_retention_scorer(adapter)
        cand = {"wallet": "0xWorker"}
        s1 = scorer({"category": "delivery"}, cand)
        s2 = scorer({"category": "verification"}, cand)
        assert s1 == s2

    def test_scorer_different_workers(self, adapter):
        """Different workers with different retention data → different scores."""
        adapter._cache["0xgood"] = RetentionSnapshot(
            wallet="0xGood",
            churn_probability=0.05,
            risk_level="stable",
            tenure_days=200,
            fetched_at=time.time(),
        )
        adapter._cache["0xbad"] = RetentionSnapshot(
            wallet="0xBad",
            churn_probability=0.9,
            risk_level="critical",
            tenure_days=5,
            fetched_at=time.time(),
        )

        scorer = make_retention_scorer(adapter)
        good_score = scorer({}, {"wallet": "0xGood"})
        bad_score = scorer({}, {"wallet": "0xBad"})
        assert good_score > bad_score

    def test_scorer_uses_address_key(self, adapter):
        """Falls back to 'address' if 'wallet' not present."""
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {"address": "0xAddr"})
        assert isinstance(score, (int, float))

    def test_scorer_no_wallet_neutral(self, adapter):
        """No wallet key → neutral score (50)."""
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {})
        assert score == 50.0

    def test_scorer_empty_wallet_neutral(self, adapter):
        """Empty wallet string → neutral score."""
        scorer = make_retention_scorer(adapter)
        score = scorer({}, {"wallet": ""})
        assert score == 50.0


# ──────────────────────────────────────────────────────────────
# Constants Sanity
# ──────────────────────────────────────────────────────────────


class TestConstants:
    def test_fresh_ttl_reasonable(self):
        assert 300 <= FRESH_TTL <= 28800  # 5 min to 8 hours

    def test_stale_ttl_greater_than_fresh(self):
        assert STALE_TTL > FRESH_TTL

    def test_stale_ttl_reasonable(self):
        assert STALE_TTL <= 86400  # Max 24 hours
