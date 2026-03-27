"""Tests for MarketIntelligenceAdapter — 12th signal: market conditions."""

import time
import pytest

from mcp_server.swarm.market_intelligence_adapter import (
    MarketIntelligenceAdapter,
    MarketSnapshot,
    TimingSnapshot,
    SupplyGapSnapshot,
    make_market_scorer,
)


@pytest.fixture
def adapter():
    return MarketIntelligenceAdapter(
        autojob_base_url="http://localhost:19999", timeout_s=0.5
    )


@pytest.fixture
def healthy_market():
    return MarketSnapshot(
        category="physical_presence",
        demand_score=0.5,
        completion_rate=0.85,
        expiry_rate=0.1,
        trend="growing",
        avg_bounty_usd=0.75,
        active_tasks=15,
        unique_workers=5,
        confidence=0.8,
        fetched_at=time.time(),
    )


@pytest.fixture
def unhealthy_market():
    return MarketSnapshot(
        category="delivery",
        demand_score=0.9,
        completion_rate=0.2,
        expiry_rate=0.7,
        trend="declining",
        avg_bounty_usd=1.50,
        active_tasks=2,
        unique_workers=1,
        confidence=0.5,
        fetched_at=time.time(),
    )


class TestMarketSnapshot:
    def test_age_seconds(self, healthy_market):
        assert 0 <= healthy_market.age_seconds < 5

    def test_health_score_range(self, healthy_market):
        score = healthy_market.market_health_score
        assert 0 <= score <= 100

    def test_healthy_higher_than_unhealthy(self, healthy_market, unhealthy_market):
        assert healthy_market.market_health_score > unhealthy_market.market_health_score


class TestTimingSnapshot:
    def test_basic_fields(self):
        snap = TimingSnapshot(
            category="test",
            best_day="Wednesday",
            best_hour_utc=14,
            acceptance_likelihood=0.75,
            confidence=0.8,
            fetched_at=time.time(),
        )
        assert snap.category == "test"
        assert snap.best_hour_utc == 14
        assert 0 <= snap.age_seconds < 5


class TestSupplyGapSnapshot:
    def test_creation(self):
        gap = SupplyGapSnapshot(
            category="delivery",
            gap_severity=0.8,
            worker_deficit=5,
            avg_wait_hours=48,
            fetched_at=time.time(),
        )
        assert gap.gap_severity == 0.8
        assert gap.category == "delivery"


class TestMarketIntelligenceAdapter:
    def test_init(self):
        adapter = MarketIntelligenceAdapter()
        assert hasattr(adapter, "base_url")

    def test_analyze_returns_snapshot(self, adapter):
        result = adapter.analyze("physical_presence")
        assert isinstance(result, MarketSnapshot)
        assert result.category == "physical_presence"

    def test_analyze_consistent_category(self, adapter):
        r1 = adapter.analyze("digital")
        r2 = adapter.analyze("digital")
        assert r1.category == r2.category == "digital"

    def test_different_categories(self, adapter):
        r1 = adapter.analyze("physical_presence")
        r2 = adapter.analyze("digital_physical")
        assert r1.category != r2.category

    def test_get_timing(self, adapter):
        result = adapter.get_timing("physical_presence")
        assert isinstance(result, TimingSnapshot)

    def test_get_supply_gaps(self, adapter):
        result = adapter.get_supply_gaps()
        assert isinstance(result, list)

    def test_stats(self, adapter):
        assert isinstance(adapter.stats(), dict)


class TestMarketScorer:
    def test_callable(self, adapter):
        scorer = make_market_scorer(adapter)
        assert callable(scorer)

    def test_returns_float(self, adapter):
        scorer = make_market_scorer(adapter)
        score = scorer({"category": "test"}, {"wallet": "0xW"})
        assert isinstance(score, (int, float))

    def test_task_level_signal(self, adapter):
        """Market score is task-level — same for all candidates."""
        scorer = make_market_scorer(adapter)
        task = {"category": "physical_presence"}
        s1 = scorer(task, {"wallet": "0xA"})
        s2 = scorer(task, {"wallet": "0xB"})
        assert s1 == s2

    def test_consistent(self, adapter):
        scorer = make_market_scorer(adapter)
        task = {"category": "test"}
        c = {"wallet": "0xSame"}
        assert scorer(task, c) == scorer(task, c)
