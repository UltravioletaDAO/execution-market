"""Tests for SwarmOrchestrator ReputationBridge."""
import pytest
from datetime import datetime, timezone, timedelta

from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
    ReputationTier,
    TIER_BONUSES,
)


@pytest.fixture
def bridge():
    return ReputationBridge()


@pytest.fixture
def veteran_on_chain():
    return OnChainReputation(
        agent_id=1,
        wallet_address="0xabc",
        total_seals=120,
        positive_seals=115,
        negative_seals=5,
        chains_active=["base", "ethereum", "polygon", "arbitrum"],
        registered_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        last_seal_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )


@pytest.fixture
def veteran_internal():
    return InternalReputation(
        agent_id=1,
        bayesian_score=0.92,
        total_tasks=150,
        successful_tasks=145,
        avg_rating=4.9,
        avg_completion_time_hours=2.5,
        consecutive_failures=0,
        category_scores={"photo_verification": 0.95, "delivery": 0.88, "survey": 0.82},
    )


@pytest.fixture
def newbie_on_chain():
    return OnChainReputation(
        agent_id=2,
        wallet_address="0xdef",
        total_seals=0,
        positive_seals=0,
        negative_seals=0,
        chains_active=["base"],
    )


@pytest.fixture
def newbie_internal():
    return InternalReputation(
        agent_id=2,
        bayesian_score=0.5,
        total_tasks=2,
        successful_tasks=2,
        avg_rating=4.0,
        avg_completion_time_hours=6,
        consecutive_failures=0,
    )


class TestOnChainReputation:
    def test_seal_ratio_positive(self, veteran_on_chain):
        assert abs(veteran_on_chain.seal_ratio - 115 / 120) < 0.001

    def test_seal_ratio_zero_seals(self, newbie_on_chain):
        assert newbie_on_chain.seal_ratio == 0.0

    def test_chain_diversity_partial(self, veteran_on_chain):
        assert abs(veteran_on_chain.chain_diversity - 4 / 8) < 0.001

    def test_chain_diversity_single(self, newbie_on_chain):
        assert abs(newbie_on_chain.chain_diversity - 1 / 8) < 0.001

    def test_chain_diversity_max(self):
        rep = OnChainReputation(
            agent_id=3,
            wallet_address="0x123",
            chains_active=["base", "eth", "poly", "arb", "avax", "sol", "celo", "opt", "extra"],
        )
        assert rep.chain_diversity == 1.0  # Capped at 1.0


class TestInternalReputation:
    def test_success_rate(self, veteran_internal):
        assert abs(veteran_internal.success_rate - 145 / 150) < 0.001

    def test_success_rate_zero_tasks(self, newbie_internal):
        empty = InternalReputation(agent_id=99, total_tasks=0)
        assert empty.success_rate == 0.0

    def test_on_time_rate_fast(self, veteran_internal):
        assert veteran_internal.on_time_rate == 1.0  # 2.5h < 4h

    def test_on_time_rate_slow(self):
        rep = InternalReputation(agent_id=5, avg_completion_time_hours=20)
        assert 0.2 < rep.on_time_rate < 0.5

    def test_on_time_rate_very_slow(self):
        rep = InternalReputation(agent_id=5, avg_completion_time_hours=30)
        assert rep.on_time_rate == 0.2


class TestTierDetermination:
    def test_diamante_tier(self, bridge, veteran_internal):
        tier = bridge._determine_tier(veteran_internal)
        assert tier == ReputationTier.DIAMANTE

    def test_oro_tier(self, bridge):
        rep = InternalReputation(
            agent_id=3, total_tasks=60, successful_tasks=55,
            avg_rating=4.6,
        )
        tier = bridge._determine_tier(rep)
        assert tier == ReputationTier.ORO

    def test_plata_tier(self, bridge):
        rep = InternalReputation(
            agent_id=4, total_tasks=25, successful_tasks=22,
            avg_rating=4.1,
        )
        tier = bridge._determine_tier(rep)
        assert tier == ReputationTier.PLATA

    def test_bronce_tier(self, bridge):
        rep = InternalReputation(
            agent_id=5, total_tasks=8, successful_tasks=6,
            avg_rating=3.5,
        )
        tier = bridge._determine_tier(rep)
        assert tier == ReputationTier.BRONCE

    def test_nuevo_tier(self, bridge, newbie_internal):
        tier = bridge._determine_tier(newbie_internal)
        assert tier == ReputationTier.NUEVO

    def test_nuevo_high_rating_low_tasks(self, bridge):
        """Perfect rating but not enough tasks → still NUEVO."""
        rep = InternalReputation(
            agent_id=6, total_tasks=4, successful_tasks=4,
            avg_rating=5.0,
        )
        tier = bridge._determine_tier(rep)
        assert tier == ReputationTier.NUEVO


class TestCompositeScore:
    def test_total_calculation(self):
        score = CompositeScore(
            agent_id=1,
            skill_score=80,
            reputation_score=90,
            reliability_score=85,
            recency_score=100,
            tier=ReputationTier.ORO,
            tier_bonus=10,
        )
        expected = (
            80 * 0.45 + 90 * 0.25 + 85 * 0.20 + 100 * 0.10 + 10
        )
        assert abs(score.total - expected) < 0.001

    def test_total_with_tier_bonus(self):
        score = CompositeScore(
            agent_id=1,
            skill_score=100,
            reputation_score=100,
            reliability_score=100,
            recency_score=100,
            tier=ReputationTier.DIAMANTE,
            tier_bonus=15,
        )
        # 100*0.45 + 100*0.25 + 100*0.20 + 100*0.10 + 15 = 115
        assert score.total == 115.0

    def test_to_dict_shape(self):
        score = CompositeScore(agent_id=1)
        d = score.to_dict()
        assert set(d.keys()) == {
            "agent_id", "total", "skill", "reputation",
            "reliability", "recency", "tier", "tier_bonus",
        }


class TestSkillScore:
    def test_category_match(self, bridge, veteran_internal):
        score = bridge._compute_skill_score(
            veteran_internal, ["photo_verification"]
        )
        # Should be high: 0.95 * 70 + (1/1) * 30 = 66.5 + 30 = 96.5
        assert score > 90

    def test_partial_category_match(self, bridge, veteran_internal):
        score = bridge._compute_skill_score(
            veteran_internal, ["photo_verification", "unknown_category"]
        )
        # One match out of two: 0.95 * 70 + (1/2) * 30 = 66.5 + 15 = 81.5
        assert 75 < score < 90

    def test_no_category_match(self, bridge, veteran_internal):
        score = bridge._compute_skill_score(
            veteran_internal, ["totally_new_category"]
        )
        # No matches, fallback to general experience
        assert score <= 30

    def test_no_categories_requested(self, bridge, veteran_internal):
        score = bridge._compute_skill_score(veteran_internal, [])
        # Fallback: success_rate * 60 + volume * 40
        assert score > 50

    def test_newbie_no_category_scores(self, bridge, newbie_internal):
        score = bridge._compute_skill_score(newbie_internal, ["photo"])
        # Empty category_scores, fallback to global
        assert score >= 0


class TestReputationScore:
    def test_veteran_high_score(self, bridge, veteran_on_chain, veteran_internal):
        score = bridge._compute_reputation_score(veteran_on_chain, veteran_internal)
        assert score > 75

    def test_newbie_neutral_score(self, bridge, newbie_on_chain, newbie_internal):
        score = bridge._compute_reputation_score(newbie_on_chain, newbie_internal)
        # Neutral: on_chain gets 20 baseline, internal gets 50% Bayesian
        assert 25 < score < 50

    def test_bad_reputation(self, bridge):
        on_chain = OnChainReputation(
            agent_id=99, wallet_address="0xbad",
            total_seals=50, positive_seals=10, negative_seals=40,
        )
        internal = InternalReputation(agent_id=99, bayesian_score=0.15)
        score = bridge._compute_reputation_score(on_chain, internal)
        assert score < 30


class TestReliabilityScore:
    def test_veteran_reliable(self, bridge, veteran_internal):
        score = bridge._compute_reliability_score(veteran_internal)
        assert score > 80

    def test_newbie_low_reliability(self, bridge, newbie_internal):
        score = bridge._compute_reliability_score(newbie_internal)
        # Newbie: 2 tasks at 100% success (40) + 4.0 rating (32) + low volume (~6)
        # Still decent because they have perfect success, just low volume
        assert score < 80
        # But lower than a veteran
        veteran = InternalReputation(
            agent_id=99, total_tasks=150, successful_tasks=145,
            avg_rating=4.9,
        )
        assert score < bridge._compute_reliability_score(veteran)

    def test_zero_tasks(self, bridge):
        rep = InternalReputation(agent_id=0, total_tasks=0)
        score = bridge._compute_reliability_score(rep)
        assert score == 10  # Baseline

    def test_consecutive_failures_penalty(self, bridge):
        rep = InternalReputation(
            agent_id=0, total_tasks=50, successful_tasks=45,
            avg_rating=4.0, consecutive_failures=4,
        )
        score_with = bridge._compute_reliability_score(rep)
        rep.consecutive_failures = 0
        score_without = bridge._compute_reliability_score(rep)
        assert score_with < score_without


class TestRecencyScore:
    def test_just_active(self, bridge):
        score = bridge._compute_recency_score(datetime.now(timezone.utc))
        assert score == 100

    def test_active_yesterday(self, bridge):
        score = bridge._compute_recency_score(
            datetime.now(timezone.utc) - timedelta(hours=12)
        )
        assert score == 100

    def test_active_week_ago(self, bridge):
        score = bridge._compute_recency_score(
            datetime.now(timezone.utc) - timedelta(days=5)
        )
        assert 90 < score < 100

    def test_active_month_ago(self, bridge):
        score = bridge._compute_recency_score(
            datetime.now(timezone.utc) - timedelta(days=25)
        )
        assert 70 < score < 90

    def test_inactive_long_time(self, bridge):
        score = bridge._compute_recency_score(
            datetime.now(timezone.utc) - timedelta(days=180)
        )
        assert score < 20

    def test_none_activity(self, bridge):
        score = bridge._compute_recency_score(None)
        assert score == 0

    def test_naive_datetime(self, bridge):
        """Naive datetimes should be treated as UTC."""
        score = bridge._compute_recency_score(
            datetime.now() - timedelta(hours=1)
        )
        assert score > 90


class TestCompositeComputation:
    def test_veteran_gets_high_composite(
        self, bridge, veteran_on_chain, veteran_internal
    ):
        score = bridge.compute_composite(
            veteran_on_chain, veteran_internal,
            task_categories=["photo_verification"],
            last_active=datetime.now(timezone.utc),
        )
        assert score.total > 80
        assert score.tier == ReputationTier.DIAMANTE
        assert score.tier_bonus == 15

    def test_newbie_gets_lower_composite(
        self, bridge, newbie_on_chain, newbie_internal,
        veteran_on_chain, veteran_internal,
    ):
        newbie_score = bridge.compute_composite(
            newbie_on_chain, newbie_internal,
            task_categories=["photo_verification"],
        )
        veteran_score = bridge.compute_composite(
            veteran_on_chain, veteran_internal,
            task_categories=["photo_verification"],
            last_active=datetime.now(timezone.utc),
        )
        assert newbie_score.total < veteran_score.total
        assert newbie_score.tier == ReputationTier.NUEVO
        assert newbie_score.tier_bonus == 0


class TestRankAgents:
    def test_rank_ordering(
        self, bridge, veteran_on_chain, veteran_internal,
        newbie_on_chain, newbie_internal,
    ):
        agents = [
            (newbie_on_chain, newbie_internal),    # Worse
            (veteran_on_chain, veteran_internal),  # Better
        ]
        ranked = bridge.rank_agents(
            agents,
            task_categories=["photo_verification"],
            last_active_map={1: datetime.now(timezone.utc)},
        )
        assert len(ranked) == 2
        assert ranked[0].agent_id == 1  # Veteran first
        assert ranked[1].agent_id == 2  # Newbie second
        assert ranked[0].total > ranked[1].total
