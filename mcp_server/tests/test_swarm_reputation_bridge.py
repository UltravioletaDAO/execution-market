"""
Tests for ReputationBridge — on-chain + internal reputation → composite scoring.

Covers:
- ReputationTier determination (5 tiers)
- OnChainReputation properties
- InternalReputation properties
- CompositeScore weighting & serialization
- ReputationBridge scoring (skill, reputation, reliability, recency)
- Agent ranking
- Category multiplier
"""

import math
from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    ReputationTier,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
    TIER_BONUSES,
    TIER_THRESHOLDS,
)


# ──────────────────────────── Fixtures ────────────────────────────


def _on_chain(
    agent_id=1,
    wallet="0xAAA",
    total_seals=50,
    positive_seals=45,
    negative_seals=5,
    chains=None,
    registered_at=None,
    last_seal_at=None,
):
    return OnChainReputation(
        agent_id=agent_id,
        wallet_address=wallet,
        total_seals=total_seals,
        positive_seals=positive_seals,
        negative_seals=negative_seals,
        chains_active=chains or ["base", "ethereum"],
        registered_at=registered_at,
        last_seal_at=last_seal_at,
    )


def _internal(
    agent_id=1,
    bayesian=0.75,
    total_tasks=60,
    successful=54,
    avg_rating=4.6,
    avg_time=6.0,
    consec_fails=0,
    categories=None,
):
    return InternalReputation(
        agent_id=agent_id,
        bayesian_score=bayesian,
        total_tasks=total_tasks,
        successful_tasks=successful,
        avg_rating=avg_rating,
        avg_completion_time_hours=avg_time,
        consecutive_failures=consec_fails,
        category_scores=categories or {},
    )


# ──────────────────── OnChainReputation Tests ─────────────────────


class TestOnChainReputation:
    def test_seal_ratio_positive(self):
        oc = _on_chain(total_seals=100, positive_seals=90)
        assert oc.seal_ratio == pytest.approx(0.9)

    def test_seal_ratio_zero_seals(self):
        oc = _on_chain(total_seals=0, positive_seals=0)
        assert oc.seal_ratio == 0.0

    def test_seal_ratio_all_positive(self):
        oc = _on_chain(total_seals=50, positive_seals=50)
        assert oc.seal_ratio == 1.0

    def test_chain_diversity_two_chains(self):
        oc = _on_chain(chains=["base", "ethereum"])
        assert oc.chain_diversity == pytest.approx(0.25)

    def test_chain_diversity_max_at_eight(self):
        oc = _on_chain(
            chains=[
                "base",
                "ethereum",
                "polygon",
                "arbitrum",
                "celo",
                "monad",
                "avalanche",
                "optimism",
            ]
        )
        assert oc.chain_diversity == 1.0

    def test_chain_diversity_over_eight_capped(self):
        oc = _on_chain(chains=["c" + str(i) for i in range(12)])
        assert oc.chain_diversity == 1.0

    def test_chain_diversity_empty(self):
        oc = OnChainReputation(agent_id=1, wallet_address="0xAAA", chains_active=[])
        assert oc.chain_diversity == 0.0


# ──────────────────── InternalReputation Tests ────────────────────


class TestInternalReputation:
    def test_success_rate(self):
        ir = _internal(total_tasks=100, successful=85)
        assert ir.success_rate == pytest.approx(0.85)

    def test_success_rate_zero_tasks(self):
        ir = _internal(total_tasks=0, successful=0)
        assert ir.success_rate == 0.0

    def test_on_time_rate_fast(self):
        """Under 4h → perfect 1.0"""
        ir = _internal(avg_time=2.0)
        assert ir.on_time_rate == 1.0

    def test_on_time_rate_slow(self):
        """Over 24h → minimum 0.2"""
        ir = _internal(avg_time=48.0)
        assert ir.on_time_rate == 0.2

    def test_on_time_rate_medium(self):
        """Between 4h and 24h → linear decay"""
        ir = _internal(avg_time=14.0)
        expected = 1.0 - 0.8 * ((14 - 4) / 20)
        assert ir.on_time_rate == pytest.approx(expected)

    def test_on_time_rate_zero(self):
        ir = _internal(avg_time=0.0)
        assert ir.on_time_rate == 0.0

    def test_on_time_rate_exact_4h(self):
        ir = _internal(avg_time=4.0)
        assert ir.on_time_rate == 1.0


# ──────────────────── CompositeScore Tests ────────────────────────


class TestCompositeScore:
    def test_total_weighting(self):
        cs = CompositeScore(
            agent_id=1,
            skill_score=80,
            reputation_score=60,
            reliability_score=70,
            recency_score=90,
            tier=ReputationTier.PLATA,
            tier_bonus=5,
        )
        expected = 80 * 0.45 + 60 * 0.25 + 70 * 0.20 + 90 * 0.10 + 5
        assert cs.total == pytest.approx(expected)

    def test_total_all_zero(self):
        cs = CompositeScore(agent_id=1, tier=ReputationTier.NUEVO)
        assert cs.total == 0.0

    def test_total_perfect_scores(self):
        cs = CompositeScore(
            agent_id=1,
            skill_score=100,
            reputation_score=100,
            reliability_score=100,
            recency_score=100,
            tier=ReputationTier.DIAMANTE,
            tier_bonus=15,
        )
        assert cs.total == pytest.approx(115.0)

    def test_to_dict_keys(self):
        cs = CompositeScore(
            agent_id=42,
            skill_score=50,
            reputation_score=60,
            reliability_score=70,
            recency_score=80,
            tier=ReputationTier.ORO,
            tier_bonus=10,
        )
        d = cs.to_dict()
        assert d["agent_id"] == 42
        assert d["tier"] == "oro"
        assert d["tier_bonus"] == 10
        assert "total" in d
        assert "skill" in d
        assert "reputation" in d
        assert "reliability" in d
        assert "recency" in d

    def test_to_dict_rounding(self):
        cs = CompositeScore(
            agent_id=1,
            skill_score=33.33333,
            reputation_score=66.66667,
            tier=ReputationTier.NUEVO,
        )
        d = cs.to_dict()
        assert d["skill"] == 33.33
        assert d["reputation"] == 66.67

    def test_weights_sum_to_one(self):
        assert sum(CompositeScore.WEIGHTS.values()) == pytest.approx(1.0)


# ───────────────────── ReputationTier Tests ───────────────────────


class TestReputationTier:
    def test_tier_values(self):
        assert ReputationTier.DIAMANTE.value == "diamante"
        assert ReputationTier.ORO.value == "oro"
        assert ReputationTier.PLATA.value == "plata"
        assert ReputationTier.BRONCE.value == "bronce"
        assert ReputationTier.NUEVO.value == "nuevo"

    def test_tier_bonus_values(self):
        assert TIER_BONUSES[ReputationTier.DIAMANTE] == 15
        assert TIER_BONUSES[ReputationTier.ORO] == 10
        assert TIER_BONUSES[ReputationTier.NUEVO] == 0

    def test_tier_thresholds_ordering(self):
        """Higher tiers require more tasks and better metrics."""
        d = TIER_THRESHOLDS[ReputationTier.DIAMANTE]
        o = TIER_THRESHOLDS[ReputationTier.ORO]
        p = TIER_THRESHOLDS[ReputationTier.PLATA]
        b = TIER_THRESHOLDS[ReputationTier.BRONCE]
        assert d["min_tasks"] > o["min_tasks"] > p["min_tasks"] > b["min_tasks"]
        assert d["min_rating"] > o["min_rating"] > p["min_rating"] > b["min_rating"]


# ──────────────────── ReputationBridge Tests ──────────────────────


class TestReputationBridge:
    def setup_method(self):
        self.bridge = ReputationBridge()

    # ── Tier determination ──

    def test_determine_tier_diamante(self):
        ir = _internal(total_tasks=150, successful=145, avg_rating=4.9)
        tier = self.bridge._determine_tier(ir)
        assert tier == ReputationTier.DIAMANTE

    def test_determine_tier_oro(self):
        ir = _internal(total_tasks=55, successful=50, avg_rating=4.6)
        tier = self.bridge._determine_tier(ir)
        assert tier == ReputationTier.ORO

    def test_determine_tier_plata(self):
        ir = _internal(total_tasks=25, successful=21, avg_rating=4.2)
        tier = self.bridge._determine_tier(ir)
        assert tier == ReputationTier.PLATA

    def test_determine_tier_bronce(self):
        ir = _internal(total_tasks=8, successful=6, avg_rating=3.5)
        tier = self.bridge._determine_tier(ir)
        assert tier == ReputationTier.BRONCE

    def test_determine_tier_nuevo(self):
        ir = _internal(total_tasks=2, successful=1, avg_rating=2.0)
        tier = self.bridge._determine_tier(ir)
        assert tier == ReputationTier.NUEVO

    def test_determine_tier_high_tasks_low_rating(self):
        """Many tasks but low rating → stuck at lower tier."""
        ir = _internal(total_tasks=200, successful=190, avg_rating=3.8)
        tier = self.bridge._determine_tier(ir)
        # 200 tasks, 95% success, but 3.8 rating → doesn't qualify for Plata (needs 4.0)
        # Falls to Bronce (needs 3.0 rating, 5 tasks, 60% success)
        assert tier == ReputationTier.BRONCE

    def test_determine_tier_boundary_exact_oro(self):
        """Exactly meets Oro thresholds."""
        ir = _internal(total_tasks=50, successful=45, avg_rating=4.5)
        tier = self.bridge._determine_tier(ir)
        assert tier == ReputationTier.ORO

    # ── Skill scoring ──

    def test_skill_score_no_categories(self):
        ir = _internal(total_tasks=60, successful=54)
        score = self.bridge._compute_skill_score(ir, [])
        # Fallback formula: success_rate * 60 + min(total/50, 1.0) * 40
        expected = (54 / 60) * 60 + min(60 / 50, 1.0) * 40
        assert score == pytest.approx(expected)

    def test_skill_score_with_matching_categories(self):
        ir = _internal(categories={"photo_verification": 0.85, "data_collection": 0.70})
        score = self.bridge._compute_skill_score(ir, ["photo_verification"])
        # avg_category = 0.85, coverage = 1/1 = 1.0
        expected = 0.85 * 70 + 1.0 * 30
        assert score == pytest.approx(expected)

    def test_skill_score_partial_category_match(self):
        ir = _internal(categories={"photo_verification": 0.85})
        score = self.bridge._compute_skill_score(
            ir, ["photo_verification", "notarization"]
        )
        # avg_category = 0.85 (only 1 hit), coverage = 0.5
        expected = 0.85 * 70 + 0.5 * 30
        assert score == pytest.approx(expected)

    def test_skill_score_no_category_match(self):
        ir = _internal(total_tasks=50, categories={"data_collection": 0.9})
        score = self.bridge._compute_skill_score(ir, ["notarization"])
        # No hits → partial credit: min(50/100, 1.0) * 30 = 15
        assert score == pytest.approx(15.0)

    def test_skill_score_no_category_experience_new_agent(self):
        ir = _internal(total_tasks=0, categories={})
        score = self.bridge._compute_skill_score(ir, ["anything"])
        assert score == pytest.approx(0.0)

    # ── Reputation scoring ──

    def test_reputation_score_blend(self):
        oc = _on_chain(total_seals=100, positive_seals=90, chains=["base", "ethereum"])
        ir = _internal(bayesian=0.8)
        score = self.bridge._compute_reputation_score(oc, ir)
        # on_chain: 0.9 * 80 + 0.25 * 20 = 77.0 → 40% = 30.8
        # internal: 0.8 * 100 = 80.0 → 60% = 48.0
        expected = 77.0 * 0.4 + 80.0 * 0.6
        assert score == pytest.approx(expected)

    def test_reputation_score_no_seals(self):
        oc = _on_chain(total_seals=0, positive_seals=0, chains=[])
        ir = _internal(bayesian=0.5)
        score = self.bridge._compute_reputation_score(oc, ir)
        # on_chain: 20 (neutral baseline) → 40% = 8.0
        # internal: 50.0 → 60% = 30.0
        expected = 20 * 0.4 + 50.0 * 0.6
        assert score == pytest.approx(expected)

    def test_reputation_score_perfect(self):
        oc = _on_chain(
            total_seals=200,
            positive_seals=200,
            chains=["c" + str(i) for i in range(8)],
        )
        ir = _internal(bayesian=1.0)
        score = self.bridge._compute_reputation_score(oc, ir)
        # on_chain: 1.0 * 80 + 1.0 * 20 = 100 → 40% = 40
        # internal: 100 → 60% = 60
        assert score == pytest.approx(100.0)

    # ── Reliability scoring ──

    def test_reliability_score_good_agent(self):
        ir = _internal(total_tasks=50, successful=48, avg_rating=4.8, consec_fails=0)
        score = self.bridge._compute_reliability_score(ir)
        success_pts = (48 / 50) * 40
        rating_pts = (4.8 / 5.0) * 40
        volume_pts = min(math.log10(50) / math.log10(100) * 20, 20)
        expected = success_pts + rating_pts + volume_pts
        assert score == pytest.approx(expected)

    def test_reliability_score_no_tasks(self):
        ir = _internal(total_tasks=0, successful=0, avg_rating=0)
        score = self.bridge._compute_reliability_score(ir)
        assert score == 10  # Low baseline

    def test_reliability_consecutive_failure_penalty(self):
        ir = _internal(total_tasks=50, successful=45, avg_rating=4.0, consec_fails=3)
        score_with_fails = self.bridge._compute_reliability_score(ir)
        ir2 = _internal(total_tasks=50, successful=45, avg_rating=4.0, consec_fails=0)
        score_no_fails = self.bridge._compute_reliability_score(ir2)
        assert score_no_fails > score_with_fails
        assert score_no_fails - score_with_fails == pytest.approx(15.0)  # 3 * 5

    def test_reliability_failure_penalty_capped(self):
        """Max penalty is 25 even with many consecutive failures."""
        ir = _internal(total_tasks=50, successful=45, avg_rating=4.0, consec_fails=10)
        score = self.bridge._compute_reliability_score(ir)
        # Penalty = min(10*5, 25) = 25
        assert score >= 0  # Never goes negative

    def test_reliability_score_floored_at_zero(self):
        ir = _internal(total_tasks=1, successful=0, avg_rating=1.0, consec_fails=10)
        score = self.bridge._compute_reliability_score(ir)
        assert score >= 0

    # ── Recency scoring ──

    def test_recency_just_active(self):
        now = datetime.now(timezone.utc)
        score = self.bridge._compute_recency_score(now)
        assert score == pytest.approx(100.0, abs=1)

    def test_recency_one_day_ago(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        score = self.bridge._compute_recency_score(yesterday)
        assert score == pytest.approx(100.0, abs=1)

    def test_recency_one_week(self):
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        score = self.bridge._compute_recency_score(week_ago)
        assert 89 <= score <= 91  # ~90

    def test_recency_one_month(self):
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        score = self.bridge._compute_recency_score(month_ago)
        assert 69 <= score <= 71  # ~70

    def test_recency_three_months(self):
        three_months = datetime.now(timezone.utc) - timedelta(days=90)
        score = self.bridge._compute_recency_score(three_months)
        assert 39 <= score <= 41  # ~40

    def test_recency_very_old(self):
        old = datetime.now(timezone.utc) - timedelta(days=365)
        score = self.bridge._compute_recency_score(old)
        assert score < 5  # Near zero

    def test_recency_none(self):
        score = self.bridge._compute_recency_score(None)
        assert score == 0

    def test_recency_naive_datetime(self):
        """Naive datetimes should be treated as UTC."""
        recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        score = self.bridge._compute_recency_score(recent)
        assert score >= 95

    # ── Full composite computation ──

    def test_compute_composite_full(self):
        oc = _on_chain()
        ir = _internal(categories={"photo": 0.85})
        now = datetime.now(timezone.utc)
        score = self.bridge.compute_composite(oc, ir, ["photo"], now)
        assert isinstance(score, CompositeScore)
        assert score.agent_id == 1
        assert score.total > 0
        assert score.tier in ReputationTier

    def test_compute_composite_new_agent(self):
        oc = _on_chain(total_seals=0, positive_seals=0, chains=[])
        ir = _internal(total_tasks=0, successful=0, bayesian=0.5, avg_rating=0)
        score = self.bridge.compute_composite(oc, ir)
        assert score.tier == ReputationTier.NUEVO
        assert score.tier_bonus == 0
        assert score.total > 0  # At least some baseline from neutral bayesian

    def test_compute_composite_diamante(self):
        oc = _on_chain(
            total_seals=200,
            positive_seals=198,
            chains=["base", "ethereum", "polygon", "arbitrum"],
        )
        ir = _internal(total_tasks=150, successful=145, avg_rating=4.9, bayesian=0.95)
        score = self.bridge.compute_composite(oc, ir)
        assert score.tier == ReputationTier.DIAMANTE
        assert score.tier_bonus == 15
        assert score.total > 80  # High-performing agent

    # ── Agent ranking ──

    def test_rank_agents_ordering(self):
        agents = [
            (
                _on_chain(agent_id=1, total_seals=10, positive_seals=5, chains=[]),
                _internal(
                    agent_id=1,
                    total_tasks=5,
                    successful=3,
                    avg_rating=3.0,
                    bayesian=0.4,
                ),
            ),
            (
                _on_chain(
                    agent_id=2,
                    total_seals=100,
                    positive_seals=95,
                    chains=["base", "ethereum", "polygon"],
                ),
                _internal(
                    agent_id=2,
                    total_tasks=80,
                    successful=76,
                    avg_rating=4.7,
                    bayesian=0.9,
                ),
            ),
        ]
        rankings = self.bridge.rank_agents(agents, ["photo"])
        assert rankings[0].agent_id == 2  # Better agent first
        assert rankings[1].agent_id == 1
        assert rankings[0].total > rankings[1].total

    def test_rank_agents_with_last_active(self):
        agents = [
            (_on_chain(agent_id=1), _internal(agent_id=1)),
            (_on_chain(agent_id=2), _internal(agent_id=2)),
        ]
        last_active = {
            1: datetime.now(timezone.utc),
            2: datetime.now(timezone.utc) - timedelta(days=60),
        }
        rankings = self.bridge.rank_agents(agents, last_active_map=last_active)
        # Agent 1 has recency advantage
        assert len(rankings) == 2
        # Both have same reputation, but 1 is more recent
        assert rankings[0].agent_id == 1

    def test_rank_agents_empty(self):
        rankings = self.bridge.rank_agents([])
        assert rankings == []

    def test_rank_agents_single(self):
        agents = [(_on_chain(agent_id=42), _internal(agent_id=42))]
        rankings = self.bridge.rank_agents(agents)
        assert len(rankings) == 1
        assert rankings[0].agent_id == 42

    # ── Category multiplier ──

    def test_category_multiplier_senior_technical(self):
        mult = self.bridge.calculate_category_multiplier("technical_task", "SENIOR")
        assert mult == pytest.approx(1.5 * 1.2)

    def test_category_multiplier_junior_data(self):
        mult = self.bridge.calculate_category_multiplier("data_collection", "JUNIOR")
        assert mult == pytest.approx(0.8 * 0.9)

    def test_category_multiplier_unknown_category(self):
        mult = self.bridge.calculate_category_multiplier("unknown_cat", "SENIOR")
        assert mult == pytest.approx(1.5 * 1.0)  # Default 1.0

    def test_category_multiplier_notarization(self):
        mult = self.bridge.calculate_category_multiplier("notarization", "SENIOR")
        assert mult == pytest.approx(1.5 * 1.5)  # Highest combo
