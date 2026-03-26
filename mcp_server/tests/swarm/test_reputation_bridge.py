"""
Comprehensive test suite for ReputationBridge — the scoring backbone.

Tests cover:
- OnChainReputation data model and computed properties
- InternalReputation data model and computed properties
- CompositeScore weighting and tier bonuses
- ReputationBridge.compute_composite() for all edge cases
- Tier determination (DIAMANTE → NUEVO)
- Skill score computation (category match, fallback)
- Reputation score blending (on-chain + internal)
- Reliability score (success rate, rating, volume, failure penalty)
- Recency score (exponential decay over time)
- rank_agents() multi-agent ranking
- calculate_category_multiplier()
"""

from datetime import datetime, timezone, timedelta


from mcp_server.swarm.reputation_bridge import (
    OnChainReputation,
    InternalReputation,
    CompositeScore,
    ReputationBridge,
    ReputationTier,
    TIER_BONUSES,
)


# ─── OnChainReputation Tests ─────────────────────────────────────────────


class TestOnChainReputation:
    def test_default_values(self):
        rep = OnChainReputation(agent_id=1, wallet_address="0xABC")
        assert rep.total_seals == 0
        assert rep.positive_seals == 0
        assert rep.negative_seals == 0
        assert rep.chains_active == []
        assert rep.registered_at is None
        assert rep.last_seal_at is None

    def test_seal_ratio_zero_seals(self):
        rep = OnChainReputation(agent_id=1, wallet_address="0xABC")
        assert rep.seal_ratio == 0.0

    def test_seal_ratio_all_positive(self):
        rep = OnChainReputation(
            agent_id=1, wallet_address="0xABC", total_seals=10, positive_seals=10
        )
        assert rep.seal_ratio == 1.0

    def test_seal_ratio_mixed(self):
        rep = OnChainReputation(
            agent_id=1,
            wallet_address="0xABC",
            total_seals=10,
            positive_seals=7,
            negative_seals=3,
        )
        assert abs(rep.seal_ratio - 0.7) < 1e-9

    def test_chain_diversity_empty(self):
        rep = OnChainReputation(agent_id=1, wallet_address="0xABC")
        assert rep.chain_diversity == 0.0

    def test_chain_diversity_one_chain(self):
        rep = OnChainReputation(
            agent_id=1, wallet_address="0xABC", chains_active=["base"]
        )
        assert abs(rep.chain_diversity - 0.125) < 1e-9

    def test_chain_diversity_max_at_eight(self):
        rep = OnChainReputation(
            agent_id=1,
            wallet_address="0xABC",
            chains_active=[
                "base",
                "eth",
                "polygon",
                "arb",
                "opt",
                "celo",
                "avax",
                "monad",
            ],
        )
        assert rep.chain_diversity == 1.0

    def test_chain_diversity_caps_beyond_eight(self):
        rep = OnChainReputation(
            agent_id=1,
            wallet_address="0xABC",
            chains_active=list(range(12)),  # 12 chains
        )
        assert rep.chain_diversity == 1.0


# ─── InternalReputation Tests ────────────────────────────────────────────


class TestInternalReputation:
    def test_default_values(self):
        rep = InternalReputation(agent_id=1)
        assert rep.bayesian_score == 0.5
        assert rep.total_tasks == 0
        assert rep.success_rate == 0.0

    def test_success_rate_zero_tasks(self):
        rep = InternalReputation(agent_id=1)
        assert rep.success_rate == 0.0

    def test_success_rate_normal(self):
        rep = InternalReputation(agent_id=1, total_tasks=10, successful_tasks=8)
        assert abs(rep.success_rate - 0.8) < 1e-9

    def test_success_rate_perfect(self):
        rep = InternalReputation(agent_id=1, total_tasks=50, successful_tasks=50)
        assert rep.success_rate == 1.0

    def test_on_time_rate_zero_time(self):
        rep = InternalReputation(agent_id=1, avg_completion_time_hours=0)
        assert rep.on_time_rate == 0.0

    def test_on_time_rate_fast(self):
        rep = InternalReputation(agent_id=1, avg_completion_time_hours=2)
        assert rep.on_time_rate == 1.0

    def test_on_time_rate_at_four_hours(self):
        rep = InternalReputation(agent_id=1, avg_completion_time_hours=4)
        assert rep.on_time_rate == 1.0

    def test_on_time_rate_slow(self):
        rep = InternalReputation(agent_id=1, avg_completion_time_hours=24)
        assert rep.on_time_rate == 0.2

    def test_on_time_rate_very_slow(self):
        rep = InternalReputation(agent_id=1, avg_completion_time_hours=100)
        assert rep.on_time_rate == 0.2

    def test_on_time_rate_midpoint(self):
        # At 14h, should be between 0.2 and 1.0
        rep = InternalReputation(agent_id=1, avg_completion_time_hours=14)
        assert 0.2 < rep.on_time_rate < 1.0


# ─── CompositeScore Tests ────────────────────────────────────────────────


class TestCompositeScore:
    def test_default_all_zero(self):
        score = CompositeScore(agent_id=1)
        assert score.total == 0.0
        assert score.tier == ReputationTier.NUEVO

    def test_total_weighted(self):
        score = CompositeScore(
            agent_id=1,
            skill_score=100,
            reputation_score=100,
            reliability_score=100,
            recency_score=100,
        )
        # 100*0.45 + 100*0.25 + 100*0.20 + 100*0.10 = 100
        assert abs(score.total - 100.0) < 1e-9

    def test_total_with_tier_bonus(self):
        score = CompositeScore(
            agent_id=1,
            skill_score=80,
            reputation_score=60,
            reliability_score=70,
            recency_score=90,
            tier=ReputationTier.ORO,
            tier_bonus=10,
        )
        expected = 80 * 0.45 + 60 * 0.25 + 70 * 0.20 + 90 * 0.10 + 10
        assert abs(score.total - expected) < 1e-9

    def test_to_dict(self):
        score = CompositeScore(
            agent_id=42,
            skill_score=75.333,
            reputation_score=60.111,
            reliability_score=80.999,
            recency_score=50.5,
            tier=ReputationTier.PLATA,
            tier_bonus=5,
        )
        d = score.to_dict()
        assert d["agent_id"] == 42
        assert d["tier"] == "plata"
        assert d["tier_bonus"] == 5
        assert isinstance(d["total"], float)
        assert isinstance(d["skill"], float)

    def test_weights_sum_to_one(self):
        weights = CompositeScore.WEIGHTS
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_all_tiers_have_bonuses(self):
        for tier in ReputationTier:
            assert tier in TIER_BONUSES


# ─── ReputationBridge._determine_tier Tests ──────────────────────────────


class TestDetermineTier:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_nuevo_no_tasks(self):
        rep = InternalReputation(agent_id=1)
        assert self.bridge._determine_tier(rep) == ReputationTier.NUEVO

    def test_bronce_minimum(self):
        rep = InternalReputation(
            agent_id=1, total_tasks=5, successful_tasks=3, avg_rating=3.0
        )
        assert self.bridge._determine_tier(rep) == ReputationTier.BRONCE

    def test_plata_minimum(self):
        rep = InternalReputation(
            agent_id=1, total_tasks=20, successful_tasks=16, avg_rating=4.0
        )
        assert self.bridge._determine_tier(rep) == ReputationTier.PLATA

    def test_oro_minimum(self):
        rep = InternalReputation(
            agent_id=1, total_tasks=50, successful_tasks=45, avg_rating=4.5
        )
        assert self.bridge._determine_tier(rep) == ReputationTier.ORO

    def test_diamante_minimum(self):
        rep = InternalReputation(
            agent_id=1, total_tasks=100, successful_tasks=95, avg_rating=4.8
        )
        assert self.bridge._determine_tier(rep) == ReputationTier.DIAMANTE

    def test_high_tasks_low_rating_stays_lower(self):
        # 100 tasks but rating 3.5 → can't be DIAMANTE or ORO (need 4.5+)
        rep = InternalReputation(
            agent_id=1, total_tasks=100, successful_tasks=95, avg_rating=3.5
        )
        tier = self.bridge._determine_tier(rep)
        assert tier in (ReputationTier.PLATA, ReputationTier.BRONCE)

    def test_high_rating_low_tasks_stays_lower(self):
        # Rating 5.0 but only 3 tasks → NUEVO (need 5 for BRONCE)
        rep = InternalReputation(
            agent_id=1, total_tasks=3, successful_tasks=3, avg_rating=5.0
        )
        assert self.bridge._determine_tier(rep) == ReputationTier.NUEVO

    def test_low_success_rate_blocks_tier(self):
        # 100 tasks, perfect rating, but only 50% success → below BRONCE threshold
        rep = InternalReputation(
            agent_id=1, total_tasks=100, successful_tasks=50, avg_rating=4.8
        )
        assert self.bridge._determine_tier(rep) == ReputationTier.NUEVO

    def test_tier_priority_is_highest_qualifying(self):
        # Qualifies for ALL tiers → should get DIAMANTE
        rep = InternalReputation(
            agent_id=1, total_tasks=200, successful_tasks=198, avg_rating=4.9
        )
        assert self.bridge._determine_tier(rep) == ReputationTier.DIAMANTE


# ─── ReputationBridge._compute_skill_score Tests ─────────────────────────


class TestComputeSkillScore:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_no_categories_fallback(self):
        internal = InternalReputation(agent_id=1, total_tasks=10, successful_tasks=8)
        score = self.bridge._compute_skill_score(internal, [])
        # Fallback: success_rate * 60 + volume * 40
        expected = 0.8 * 60 + min(10 / 50, 1.0) * 40
        assert abs(score - expected) < 1e-9

    def test_no_category_scores_fallback(self):
        internal = InternalReputation(agent_id=1, total_tasks=30)
        score = self.bridge._compute_skill_score(internal, ["photo_verification"])
        # No category_scores → partial credit based on experience
        # success_rate=0 but has task volume → gets partial credit
        assert 0 <= score <= 30  # Bounded by experience-only path

    def test_exact_category_match(self):
        internal = InternalReputation(
            agent_id=1, category_scores={"photo_verification": 0.9}
        )
        score = self.bridge._compute_skill_score(internal, ["photo_verification"])
        # avg_category=0.9, coverage=1.0 → 0.9*70 + 1.0*30 = 93.0
        assert abs(score - 93.0) < 1e-9

    def test_partial_category_match(self):
        internal = InternalReputation(
            agent_id=1, category_scores={"photo_verification": 0.8, "delivery": 0.6}
        )
        score = self.bridge._compute_skill_score(
            internal, ["photo_verification", "data_entry"]
        )
        # Only photo_verification matches: avg=0.8, coverage=0.5
        expected = 0.8 * 70 + 0.5 * 30
        assert abs(score - expected) < 1e-9

    def test_all_categories_match(self):
        internal = InternalReputation(agent_id=1, category_scores={"a": 0.7, "b": 0.9})
        score = self.bridge._compute_skill_score(internal, ["a", "b"])
        avg = (0.7 + 0.9) / 2
        expected = avg * 70 + 1.0 * 30
        assert abs(score - expected) < 1e-9

    def test_high_volume_boosts_fallback(self):
        # 50+ tasks maxes out the volume component
        internal = InternalReputation(agent_id=1, total_tasks=100, successful_tasks=90)
        score_high = self.bridge._compute_skill_score(internal, [])
        internal_low = InternalReputation(agent_id=1, total_tasks=5, successful_tasks=4)
        score_low = self.bridge._compute_skill_score(internal_low, [])
        assert score_high > score_low


# ─── ReputationBridge._compute_reputation_score Tests ────────────────────


class TestComputeReputationScore:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_no_seals_neutral_baseline(self):
        on_chain = OnChainReputation(agent_id=1, wallet_address="0x1")
        internal = InternalReputation(agent_id=1, bayesian_score=0.5)
        score = self.bridge._compute_reputation_score(on_chain, internal)
        # on_chain_score = 20 (neutral), internal = 50
        expected = 20 * 0.4 + 50 * 0.6
        assert abs(score - expected) < 1e-9

    def test_perfect_seals_and_bayesian(self):
        on_chain = OnChainReputation(
            agent_id=1,
            wallet_address="0x1",
            total_seals=20,
            positive_seals=20,
            chains_active=[
                "base",
                "eth",
                "polygon",
                "arb",
                "opt",
                "celo",
                "avax",
                "monad",
            ],
        )
        internal = InternalReputation(agent_id=1, bayesian_score=1.0)
        score = self.bridge._compute_reputation_score(on_chain, internal)
        # on_chain: 1.0*80 + 1.0*20 = 100; internal: 100
        expected = 100 * 0.4 + 100 * 0.6
        assert abs(score - expected) < 1e-9

    def test_low_bayesian_high_seals(self):
        on_chain = OnChainReputation(
            agent_id=1,
            wallet_address="0x1",
            total_seals=10,
            positive_seals=10,
            chains_active=["base"],
        )
        internal = InternalReputation(agent_id=1, bayesian_score=0.2)
        score = self.bridge._compute_reputation_score(on_chain, internal)
        on_chain_score = 1.0 * 80 + (1 / 8) * 20  # 82.5
        internal_score = 0.2 * 100
        expected = on_chain_score * 0.4 + internal_score * 0.6
        assert abs(score - expected) < 1e-9


# ─── ReputationBridge._compute_reliability_score Tests ───────────────────


class TestComputeReliabilityScore:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_zero_tasks_low_baseline(self):
        internal = InternalReputation(agent_id=1)
        score = self.bridge._compute_reliability_score(internal)
        assert score == 10

    def test_perfect_worker(self):
        internal = InternalReputation(
            agent_id=1,
            total_tasks=100,
            successful_tasks=100,
            avg_rating=5.0,
            consecutive_failures=0,
        )
        score = self.bridge._compute_reliability_score(internal)
        # 1.0*40 + (5/5)*40 + log10(100)/log10(100)*20 = 40+40+20 = 100
        assert abs(score - 100.0) < 1e-9

    def test_failure_penalty(self):
        internal_no_fail = InternalReputation(
            agent_id=1,
            total_tasks=20,
            successful_tasks=18,
            avg_rating=4.0,
            consecutive_failures=0,
        )
        internal_failing = InternalReputation(
            agent_id=1,
            total_tasks=20,
            successful_tasks=18,
            avg_rating=4.0,
            consecutive_failures=5,
        )
        score_ok = self.bridge._compute_reliability_score(internal_no_fail)
        score_bad = self.bridge._compute_reliability_score(internal_failing)
        assert score_ok - score_bad == 25  # 5 failures * 5 = 25 penalty

    def test_no_rating_zero_rating_pts(self):
        internal = InternalReputation(
            agent_id=1, total_tasks=10, successful_tasks=10, avg_rating=0
        )
        score = self.bridge._compute_reliability_score(internal)
        # success=40, rating=0, volume=log10(10)/log10(100)*20 = 10
        expected = 40 + 0 + 10
        assert abs(score - expected) < 1e-9

    def test_score_never_negative(self):
        internal = InternalReputation(
            agent_id=1,
            total_tasks=1,
            successful_tasks=0,
            avg_rating=1.0,
            consecutive_failures=5,
        )
        score = self.bridge._compute_reliability_score(internal)
        assert score >= 0


# ─── ReputationBridge._compute_recency_score Tests ───────────────────────


class TestComputeRecencyScore:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_none_returns_zero(self):
        assert self.bridge._compute_recency_score(None) == 0

    def test_just_now(self):
        now = datetime.now(timezone.utc)
        score = self.bridge._compute_recency_score(now)
        assert score == 100

    def test_one_day_ago(self):
        one_day = datetime.now(timezone.utc) - timedelta(days=1)
        score = self.bridge._compute_recency_score(one_day)
        assert score >= 99.9  # <=1 day ≈ 100 (floating point)

    def test_seven_days_ago(self):
        seven_days = datetime.now(timezone.utc) - timedelta(days=7)
        score = self.bridge._compute_recency_score(seven_days)
        assert 89 <= score <= 91  # ~90

    def test_thirty_days_ago(self):
        thirty_days = datetime.now(timezone.utc) - timedelta(days=30)
        score = self.bridge._compute_recency_score(thirty_days)
        assert 69 <= score <= 71  # ~70

    def test_ninety_days_ago(self):
        ninety_days = datetime.now(timezone.utc) - timedelta(days=90)
        score = self.bridge._compute_recency_score(ninety_days)
        assert 39 <= score <= 41  # ~40

    def test_long_inactive_near_zero(self):
        old = datetime.now(timezone.utc) - timedelta(days=365)
        score = self.bridge._compute_recency_score(old)
        assert score < 5

    def test_future_date_returns_100(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        score = self.bridge._compute_recency_score(future)
        assert score == 100

    def test_naive_datetime_treated_as_utc(self):
        naive = datetime.now(timezone.utc).replace(tzinfo=None)
        score = self.bridge._compute_recency_score(naive)
        assert score == 100

    def test_monotonically_decreasing(self):
        scores = []
        for days in [0, 1, 7, 14, 30, 60, 90, 120, 180, 365]:
            dt = datetime.now(timezone.utc) - timedelta(days=days)
            scores.append(self.bridge._compute_recency_score(dt))
        # Should be non-increasing
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]


# ─── ReputationBridge.compute_composite Tests ────────────────────────────


class TestComputeComposite:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_basic_composite(self):
        on_chain = OnChainReputation(agent_id=1, wallet_address="0x1")
        internal = InternalReputation(
            agent_id=1, total_tasks=10, successful_tasks=8, avg_rating=4.0
        )
        score = self.bridge.compute_composite(on_chain, internal)
        assert isinstance(score, CompositeScore)
        assert score.agent_id == 1
        assert score.total > 0

    def test_nuevo_agent_no_bonus(self):
        on_chain = OnChainReputation(agent_id=1, wallet_address="0x1")
        internal = InternalReputation(agent_id=1)
        score = self.bridge.compute_composite(on_chain, internal)
        assert score.tier == ReputationTier.NUEVO
        assert score.tier_bonus == 0

    def test_diamante_gets_bonus(self):
        on_chain = OnChainReputation(
            agent_id=1,
            wallet_address="0x1",
            total_seals=50,
            positive_seals=50,
        )
        internal = InternalReputation(
            agent_id=1,
            total_tasks=100,
            successful_tasks=96,
            avg_rating=4.9,
            bayesian_score=0.95,
        )
        score = self.bridge.compute_composite(
            on_chain, internal, last_active=datetime.now(timezone.utc)
        )
        assert score.tier == ReputationTier.DIAMANTE
        assert score.tier_bonus == 15

    def test_categories_affect_skill_score(self):
        on_chain = OnChainReputation(agent_id=1, wallet_address="0x1")
        internal = InternalReputation(
            agent_id=1,
            total_tasks=20,
            successful_tasks=18,
            avg_rating=4.5,
            category_scores={"photo_verification": 0.95},
        )
        score_match = self.bridge.compute_composite(
            on_chain, internal, task_categories=["photo_verification"]
        )
        score_no_match = self.bridge.compute_composite(
            on_chain, internal, task_categories=["blockchain_audit"]
        )
        assert score_match.skill_score > score_no_match.skill_score


# ─── ReputationBridge.rank_agents Tests ──────────────────────────────────


class TestRankAgents:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_rank_empty_list(self):
        result = self.bridge.rank_agents([])
        assert result == []

    def test_rank_single_agent(self):
        agents = [
            (
                OnChainReputation(agent_id=1, wallet_address="0x1"),
                InternalReputation(
                    agent_id=1, total_tasks=10, successful_tasks=8, avg_rating=4.0
                ),
            )
        ]
        result = self.bridge.rank_agents(agents)
        assert len(result) == 1
        assert result[0].agent_id == 1

    def test_rank_by_score_descending(self):
        agents = [
            (
                OnChainReputation(agent_id=1, wallet_address="0x1"),
                InternalReputation(
                    agent_id=1, total_tasks=5, successful_tasks=2, avg_rating=2.0
                ),
            ),
            (
                OnChainReputation(
                    agent_id=2, wallet_address="0x2", total_seals=20, positive_seals=20
                ),
                InternalReputation(
                    agent_id=2,
                    total_tasks=100,
                    successful_tasks=98,
                    avg_rating=4.9,
                    bayesian_score=0.95,
                ),
            ),
        ]
        result = self.bridge.rank_agents(
            agents, last_active_map={2: datetime.now(timezone.utc)}
        )
        assert result[0].agent_id == 2
        assert result[0].total > result[1].total

    def test_rank_with_categories(self):
        agents = [
            (
                OnChainReputation(agent_id=1, wallet_address="0x1"),
                InternalReputation(
                    agent_id=1,
                    total_tasks=20,
                    successful_tasks=18,
                    avg_rating=4.5,
                    category_scores={"photo_verification": 0.95},
                ),
            ),
            (
                OnChainReputation(agent_id=2, wallet_address="0x2"),
                InternalReputation(
                    agent_id=2,
                    total_tasks=20,
                    successful_tasks=18,
                    avg_rating=4.5,
                    category_scores={"data_entry": 0.95},
                ),
            ),
        ]
        result = self.bridge.rank_agents(agents, task_categories=["photo_verification"])
        # Agent 1 has exact category match, should rank higher
        assert result[0].agent_id == 1

    def test_rank_preserves_all_agents(self):
        agents = [
            (
                OnChainReputation(agent_id=i, wallet_address=f"0x{i}"),
                InternalReputation(
                    agent_id=i, total_tasks=10, successful_tasks=i + 1, avg_rating=3.0
                ),
            )
            for i in range(5)
        ]
        result = self.bridge.rank_agents(agents)
        assert len(result) == 5
        agent_ids = {s.agent_id for s in result}
        assert agent_ids == {0, 1, 2, 3, 4}


# ─── calculate_category_multiplier Tests ─────────────────────────────────


class TestCategoryMultiplier:
    def setup_method(self):
        self.bridge = ReputationBridge()

    def test_default_normal(self):
        result = self.bridge.calculate_category_multiplier("random", "NORMAL")
        assert result == 1.0

    def test_senior_boosts(self):
        result = self.bridge.calculate_category_multiplier("random", "SENIOR")
        assert result == 1.5

    def test_junior_discounts(self):
        result = self.bridge.calculate_category_multiplier("random", "JUNIOR")
        assert result == 0.8

    def test_technical_task_senior(self):
        result = self.bridge.calculate_category_multiplier("technical_task", "SENIOR")
        assert result == 1.5 * 1.2  # 1.8

    def test_notarization_senior(self):
        result = self.bridge.calculate_category_multiplier("notarization", "SENIOR")
        assert result == 1.5 * 1.5  # 2.25

    def test_data_collection_junior(self):
        result = self.bridge.calculate_category_multiplier("data_collection", "JUNIOR")
        assert result == 0.8 * 0.9  # 0.72

    def test_unknown_category_base_only(self):
        result = self.bridge.calculate_category_multiplier("totally_made_up", "SENIOR")
        assert result == 1.5
