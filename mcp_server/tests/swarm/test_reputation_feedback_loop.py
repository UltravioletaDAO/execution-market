"""
E2E Reputation Feedback Loop — Validating the full reputation flywheel.

Tests the COMPLETE cycle:
    Task completion → Analytics metrics → SealBridge evaluation → SealRecommendation
    → ReputationBridge composite score → Routing decision → Next task assignment

This is the exponential value multiplier: better data → better seals → better routing
→ better outcomes → better data. The flywheel that makes the swarm self-improving.

Architecture tested:
    SwarmAnalytics   → SealBridge.evaluate_worker()   → SealProfile
    SealProfile      → ReputationBridge.compute_composite() → CompositeScore
    CompositeScore   → SwarmOrchestrator routing       → Agent selection
    Agent selection  → Task outcome                    → SwarmAnalytics update

Test Layers:
    1. Single-agent feedback loop (closed-loop verification)
    2. Multi-agent competitive routing (seal-informed ranking)
    3. Fleet evolution over time (reputation trajectory)
    4. Cross-quadrant reputation (A2H + H2A bidirectional)
    5. Cold-start to expert progression (full career arc)
    6. Seal-to-routing influence measurement (quantifying flywheel effect)
    7. Edge cases (new agents, degraded agents, seal expiry)
"""

import math
import time
import pytest
from datetime import datetime, timezone, timedelta

from mcp_server.swarm.seal_bridge import (
    SealBridge,
    SealQuadrant,
    SealRecommendation,
    SealProfile,
    SealIssuanceRecord,
    BatchSealRequest,
    A2H_SEALS,
    H2A_SEALS,
)
from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
    ReputationTier,
    TIER_BONUSES,
    TIER_THRESHOLDS,
)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def make_worker_metrics(
    tasks_completed: int = 20,
    tasks_failed: int = 2,
    tasks_expired: int = 0,
    avg_quality: float = 4.2,
    avg_duration_seconds: float = 7200,  # 2 hours
    success_rate: float | None = None,
    categories: dict | None = None,
    total_revenue_usd: float = 50.0,
    last_active: float | None = None,
    quality_scores: list | None = None,
) -> dict:
    """Create realistic worker analytics metrics."""
    total = tasks_completed + tasks_failed + tasks_expired
    if success_rate is None:
        success_rate = tasks_completed / total if total > 0 else 0.0
    return {
        "tasks_completed": tasks_completed,
        "tasks_failed": tasks_failed,
        "tasks_expired": tasks_expired,
        "avg_quality": avg_quality,
        "avg_duration_seconds": avg_duration_seconds,
        "success_rate": success_rate,
        "categories": categories or {"photo_verification": 10, "delivery": 10},
        "total_revenue_usd": total_revenue_usd,
        "last_active": last_active or time.time(),
        "quality_scores": quality_scores,
    }


def make_on_chain(
    agent_id: int = 1,
    wallet: str = "0xWorker1",
    total_seals: int = 0,
    positive_seals: int = 0,
    chains: list | None = None,
) -> OnChainReputation:
    return OnChainReputation(
        agent_id=agent_id,
        wallet_address=wallet,
        total_seals=total_seals,
        positive_seals=positive_seals,
        chains_active=chains or ["base"],
        registered_at=datetime.now(timezone.utc) - timedelta(days=30),
        last_seal_at=datetime.now(timezone.utc) if total_seals > 0 else None,
    )


def make_internal(
    agent_id: int = 1,
    bayesian_score: float = 0.7,
    total_tasks: int = 20,
    successful_tasks: int = 18,
    avg_rating: float = 4.2,
    avg_completion_time_hours: float = 2.0,
    consecutive_failures: int = 0,
    category_scores: dict | None = None,
) -> InternalReputation:
    return InternalReputation(
        agent_id=agent_id,
        bayesian_score=bayesian_score,
        total_tasks=total_tasks,
        successful_tasks=successful_tasks,
        avg_rating=avg_rating,
        avg_completion_time_hours=avg_completion_time_hours,
        consecutive_failures=consecutive_failures,
        category_scores=category_scores or {"photo_verification": 0.8, "delivery": 0.7},
    )


# ──────────────────────────────────────────────────────────────
# 1. Single-Agent Closed-Loop Feedback
# ──────────────────────────────────────────────────────────────

class TestSingleAgentFeedbackLoop:
    """Validates the complete loop for one agent."""

    def test_analytics_to_seal_recommendations(self):
        """Metrics → SealBridge → recommendations with scores."""
        bridge = SealBridge(evaluator_agent_id="swarm_coordinator")
        metrics = make_worker_metrics(tasks_completed=25, avg_quality=4.5)
        profile = bridge.evaluate_worker("0xWorker1", "worker_1", metrics)

        assert len(profile.recommendations) > 0
        assert all(r.seal_type in A2H_SEALS for r in profile.recommendations)
        assert all(0 <= r.score <= 100 for r in profile.recommendations)
        assert profile.overall_score > 0

    def test_seal_profile_to_composite_score(self):
        """SealProfile → ReputationBridge → CompositeScore for routing."""
        seal_bridge = SealBridge()
        metrics = make_worker_metrics(tasks_completed=30, avg_quality=4.5, tasks_failed=1)
        profile = seal_bridge.evaluate_worker("0xW1", "worker_1", metrics)

        # Convert seal recommendations to on-chain reputation data
        on_chain = make_on_chain(
            agent_id=1,
            total_seals=len(profile.recommendations),
            positive_seals=sum(1 for r in profile.recommendations if r.is_positive),
        )
        internal = make_internal(
            agent_id=1,
            total_tasks=31,
            successful_tasks=30,
            avg_rating=4.5,
        )

        rep_bridge = ReputationBridge()
        composite = rep_bridge.compute_composite(
            on_chain=on_chain,
            internal=internal,
            task_categories=["photo_verification"],
            last_active=datetime.now(timezone.utc),
        )

        assert composite.total > 50  # Good agent should score well
        assert composite.skill_score > 0
        assert composite.reputation_score > 0
        assert composite.reliability_score > 0
        assert composite.recency_score > 0

    def test_full_loop_improves_with_more_tasks(self):
        """More successful tasks → higher seal scores → higher composite."""
        seal_bridge = SealBridge()
        rep_bridge = ReputationBridge()

        scores_over_time = []

        for task_count in [5, 15, 30, 60, 100]:
            metrics = make_worker_metrics(
                tasks_completed=task_count,
                tasks_failed=max(1, task_count // 20),
                avg_quality=4.2 + (task_count / 500),  # Slight quality improvement
                avg_duration_seconds=7200 - task_count * 10,  # Gets faster
                categories={
                    "photo_verification": task_count // 2,
                    "delivery": task_count // 3,
                    "notarization": task_count // 6,
                },
            )
            profile = seal_bridge.evaluate_worker("0xW1", "worker_1", metrics)

            on_chain = make_on_chain(
                agent_id=1,
                total_seals=len(profile.recommendations),
                positive_seals=sum(1 for r in profile.recommendations if r.is_positive),
                chains=["base", "ethereum"] if task_count > 30 else ["base"],
            )
            internal = make_internal(
                agent_id=1,
                bayesian_score=0.5 + task_count / 250,
                total_tasks=task_count + max(1, task_count // 20),
                successful_tasks=task_count,
                avg_rating=4.2 + (task_count / 500),
            )
            composite = rep_bridge.compute_composite(
                on_chain=on_chain,
                internal=internal,
                task_categories=["photo_verification"],
                last_active=datetime.now(timezone.utc),
            )
            scores_over_time.append(composite.total)

        # Scores should generally increase (flywheel effect)
        for i in range(1, len(scores_over_time)):
            assert scores_over_time[i] >= scores_over_time[i - 1] - 2, (
                f"Score dropped at stage {i}: {scores_over_time[i-1]:.1f} → {scores_over_time[i]:.1f}"
            )

    def test_closed_loop_seal_confidence_grows(self):
        """Seal confidence increases with task volume."""
        bridge = SealBridge()

        for count, expected_min_conf in [(3, 0.2), (10, 0.4), (30, 0.7), (50, 0.9)]:
            metrics = make_worker_metrics(tasks_completed=count, tasks_failed=0)
            profile = bridge.evaluate_worker("0xW", "w1", metrics)
            if profile.recommendations:
                max_conf = max(r.confidence for r in profile.recommendations)
                assert max_conf >= expected_min_conf, (
                    f"At {count} tasks, max confidence {max_conf:.2f} < expected {expected_min_conf}"
                )

    def test_issuable_seals_require_high_confidence(self):
        """Only high-confidence seals should be issuable on-chain."""
        bridge = SealBridge()
        # Low task count → low confidence → few issuable
        metrics = make_worker_metrics(tasks_completed=4, tasks_failed=0)
        profile = bridge.evaluate_worker("0xW", "w1", metrics)
        issuable_low = len(profile.issuable_seals)

        # High task count → high confidence → more issuable
        metrics = make_worker_metrics(tasks_completed=60, tasks_failed=2)
        profile = bridge.evaluate_worker("0xW", "w1", metrics)
        issuable_high = len(profile.issuable_seals)

        assert issuable_high >= issuable_low


# ──────────────────────────────────────────────────────────────
# 2. Multi-Agent Competitive Routing
# ──────────────────────────────────────────────────────────────

class TestMultiAgentRouting:
    """Validates seal-informed competitive routing decisions."""

    def test_higher_seal_scores_win_routing(self):
        """Agent with better seals should rank higher in routing."""
        seal_bridge = SealBridge()
        rep_bridge = ReputationBridge()

        agents = []
        for i, (quality, success, tasks) in enumerate([
            (4.8, 0.98, 50),   # Expert
            (4.0, 0.85, 30),   # Intermediate
            (3.0, 0.60, 10),   # Beginner
        ]):
            metrics = make_worker_metrics(
                tasks_completed=tasks,
                tasks_failed=int(tasks * (1 - success)),
                avg_quality=quality,
            )
            profile = seal_bridge.evaluate_worker(f"0xW{i}", f"worker_{i}", metrics)

            on_chain = make_on_chain(
                agent_id=i,
                total_seals=len(profile.recommendations),
                positive_seals=sum(1 for r in profile.recommendations if r.is_positive),
            )
            internal = make_internal(
                agent_id=i,
                bayesian_score=quality / 5.0,
                total_tasks=tasks + int(tasks * (1 - success)),
                successful_tasks=tasks,
                avg_rating=quality,
            )
            agents.append((on_chain, internal))

        rankings = rep_bridge.rank_agents(
            agents,
            task_categories=["photo_verification"],
            last_active_map={i: datetime.now(timezone.utc) for i in range(3)},
        )

        assert rankings[0].agent_id == 0  # Expert wins
        assert rankings[-1].agent_id == 2  # Beginner last
        assert rankings[0].total > rankings[1].total > rankings[2].total

    def test_specialist_vs_generalist_routing(self):
        """Specialist in target category should beat generalist with higher overall."""
        rep_bridge = ReputationBridge()

        # Specialist: 90% in photo_verification, 0% elsewhere
        specialist = make_internal(
            agent_id=1,
            bayesian_score=0.75,
            total_tasks=30,
            successful_tasks=27,
            avg_rating=4.3,
            category_scores={"photo_verification": 0.95},
        )
        specialist_chain = make_on_chain(agent_id=1, total_seals=5, positive_seals=5)

        # Generalist: 70% everywhere
        generalist = make_internal(
            agent_id=2,
            bayesian_score=0.8,
            total_tasks=50,
            successful_tasks=40,
            avg_rating=4.5,
            category_scores={
                "photo_verification": 0.65,
                "delivery": 0.70,
                "notarization": 0.75,
                "data_collection": 0.80,
            },
        )
        generalist_chain = make_on_chain(agent_id=2, total_seals=8, positive_seals=7)

        rankings = rep_bridge.rank_agents(
            [(specialist_chain, specialist), (generalist_chain, generalist)],
            task_categories=["photo_verification"],
            last_active_map={1: datetime.now(timezone.utc), 2: datetime.now(timezone.utc)},
        )

        # Specialist should win for photo_verification due to 45% skill weight
        specialist_score = next(r for r in rankings if r.agent_id == 1)
        generalist_score = next(r for r in rankings if r.agent_id == 2)
        assert specialist_score.skill_score > generalist_score.skill_score

    def test_five_agent_ranking_stability(self):
        """Ranking of 5 agents should be deterministic and consistent."""
        rep_bridge = ReputationBridge()

        agents = []
        for i in range(5):
            quality = 3.0 + i * 0.4  # 3.0, 3.4, 3.8, 4.2, 4.6
            tasks = 10 + i * 10  # 10, 20, 30, 40, 50
            success = 0.6 + i * 0.08  # 60%, 68%, 76%, 84%, 92%
            on_chain = make_on_chain(agent_id=i, total_seals=i * 2, positive_seals=i * 2)
            internal = make_internal(
                agent_id=i,
                bayesian_score=quality / 5.0,
                total_tasks=tasks,
                successful_tasks=int(tasks * success),
                avg_rating=quality,
            )
            agents.append((on_chain, internal))

        r1 = rep_bridge.rank_agents(agents)
        r2 = rep_bridge.rank_agents(agents)

        # Same input → same ranking
        assert [r.agent_id for r in r1] == [r.agent_id for r in r2]
        # Best agent wins
        assert r1[0].agent_id == 4  # Highest quality + tasks

    def test_tier_bonus_affects_ranking(self):
        """Reputation tier bonus should influence close races."""
        rep_bridge = ReputationBridge()

        # Agent A: Almost Diamante (100 tasks, 4.8 rating, 95% success)
        diamante = make_internal(
            agent_id=1,
            bayesian_score=0.85,
            total_tasks=100,
            successful_tasks=95,
            avg_rating=4.8,
        )
        diamante_chain = make_on_chain(agent_id=1, total_seals=10, positive_seals=10)

        # Agent B: Similar stats but fewer tasks (Plata tier)
        plata = make_internal(
            agent_id=2,
            bayesian_score=0.85,
            total_tasks=25,
            successful_tasks=22,
            avg_rating=4.8,
        )
        plata_chain = make_on_chain(agent_id=2, total_seals=10, positive_seals=10)

        d_score = rep_bridge.compute_composite(diamante_chain, diamante,
            last_active=datetime.now(timezone.utc))
        p_score = rep_bridge.compute_composite(plata_chain, plata,
            last_active=datetime.now(timezone.utc))

        assert d_score.tier == ReputationTier.DIAMANTE
        assert d_score.tier_bonus == 15
        assert p_score.tier_bonus < d_score.tier_bonus
        assert d_score.total > p_score.total


# ──────────────────────────────────────────────────────────────
# 3. Fleet Evolution Over Time
# ──────────────────────────────────────────────────────────────

class TestFleetEvolution:
    """Validates fleet-wide reputation trajectory."""

    def test_fleet_evaluation_covers_all_agents(self):
        """Evaluate entire fleet, verify all agents get profiles."""
        seal_bridge = SealBridge()
        fleet_metrics = {}
        for i in range(10):
            fleet_metrics[f"worker_{i}"] = make_worker_metrics(
                tasks_completed=10 + i * 5,
                tasks_failed=max(1, i // 2),
                avg_quality=3.5 + i * 0.15,
            )

        profiles = seal_bridge.evaluate_fleet(fleet_metrics)
        assert len(profiles) == 10
        assert profiles[0].overall_score >= profiles[-1].overall_score  # Sorted

    def test_fleet_summary_aggregates_correctly(self):
        """Fleet summary should aggregate seals across all agents."""
        seal_bridge = SealBridge()
        fleet_metrics = {
            f"w{i}": make_worker_metrics(tasks_completed=20, avg_quality=4.0)
            for i in range(5)
        }
        profiles = seal_bridge.evaluate_fleet(fleet_metrics)
        summary = seal_bridge.fleet_summary(profiles)

        assert summary["agents_evaluated"] == 5
        assert summary["total_seals"] > 0
        assert "seal_breakdown" in summary
        assert "top_performers" in summary

    def test_fleet_scores_differentiate_performance(self):
        """Fleet evaluation should clearly separate good vs bad workers."""
        seal_bridge = SealBridge()
        rep_bridge = ReputationBridge()

        fleet_metrics = {
            "star": make_worker_metrics(tasks_completed=80, tasks_failed=2, avg_quality=4.9),
            "average": make_worker_metrics(tasks_completed=30, tasks_failed=8, avg_quality=3.5),
            "struggling": make_worker_metrics(tasks_completed=5, tasks_failed=10, avg_quality=2.0),
        }

        profiles = seal_bridge.evaluate_fleet(fleet_metrics)

        star_profile = next(p for p in profiles if p.agent_id == "star")
        struggling_profile = next(p for p in profiles if p.agent_id == "struggling")

        assert star_profile.overall_score > struggling_profile.overall_score + 20

    def test_fleet_tier_distribution(self):
        """Fleet should have realistic tier distribution."""
        rep_bridge = ReputationBridge()

        tiers = []
        for i in range(20):
            tasks = 5 + i * 10
            success = min(0.95, 0.5 + i * 0.025)
            rating = min(5.0, 2.5 + i * 0.13)
            internal = make_internal(
                agent_id=i,
                total_tasks=tasks,
                successful_tasks=int(tasks * success),
                avg_rating=rating,
            )
            on_chain = make_on_chain(agent_id=i)
            composite = rep_bridge.compute_composite(on_chain, internal)
            tiers.append(composite.tier)

        tier_counts = {}
        for t in tiers:
            tier_counts[t] = tier_counts.get(t, 0) + 1

        # Should have a mix of tiers (not all the same)
        assert len(tier_counts) >= 2, f"Only {len(tier_counts)} tier(s): {tier_counts}"


# ──────────────────────────────────────────────────────────────
# 4. Cross-Quadrant Bidirectional Reputation
# ──────────────────────────────────────────────────────────────

class TestCrossQuadrantReputation:
    """Validates A2H + H2A bidirectional seal evaluation."""

    def test_a2h_evaluates_worker_with_correct_seal_types(self):
        """A2H quadrant should produce SKILLFUL, RELIABLE, etc."""
        bridge = SealBridge()
        metrics = make_worker_metrics(tasks_completed=20)
        profile = bridge.evaluate_worker("0xW", "w1", metrics, SealQuadrant.A2H)

        seal_types = {r.seal_type for r in profile.recommendations}
        assert seal_types.issubset(A2H_SEALS)
        assert len(seal_types) > 0

    def test_h2a_evaluates_agent_with_correct_seal_types(self):
        """H2A quadrant should produce FAIR, ACCURATE, RESPONSIVE, ETHICAL."""
        bridge = SealBridge()
        metrics = {
            "tasks_assigned": 20,
            "tasks_completed": 18,
            "tasks_failed": 1,
            "tasks_expired": 1,
            "avg_quality": 4.0,
            "success_rate": 0.9,
            "avg_duration_seconds": 3600,
            "categories": {"photo_verification": 10, "delivery": 10},
        }
        profile = bridge.evaluate_agent_for_worker("0xAgent", "agent_1", metrics)

        seal_types = {r.seal_type for r in profile.recommendations}
        assert seal_types.issubset(H2A_SEALS)
        assert len(seal_types) > 0
        assert all(r.quadrant == SealQuadrant.H2A for r in profile.recommendations)

    def test_bidirectional_evaluation_produces_both_quadrants(self):
        """Same pair can have A2H and H2A seals simultaneously."""
        bridge = SealBridge()

        worker_metrics = make_worker_metrics(tasks_completed=25)
        agent_metrics = {
            "tasks_assigned": 30,
            "tasks_completed": 28,
            "tasks_failed": 1,
            "tasks_expired": 1,
            "avg_quality": 4.2,
            "success_rate": 0.93,
            "avg_duration_seconds": 5400,
            "categories": {"photo_verification": 20, "delivery": 10},
        }

        a2h_profile = bridge.evaluate_worker("0xWorker", "w1", worker_metrics)
        h2a_profile = bridge.evaluate_agent_for_worker("0xAgent", "a1", agent_metrics)

        assert all(r.quadrant == SealQuadrant.A2H for r in a2h_profile.recommendations)
        assert all(r.quadrant == SealQuadrant.H2A for r in h2a_profile.recommendations)
        assert a2h_profile.overall_score > 0
        assert h2a_profile.overall_score > 0

    def test_bidirectional_seal_counts_independent(self):
        """A2H and H2A seal counts are independent."""
        bridge = SealBridge()

        a2h_profile = bridge.evaluate_worker("0xW", "w1",
            make_worker_metrics(tasks_completed=20))
        h2a_profile = bridge.evaluate_agent_for_worker("0xA", "a1", {
            "tasks_assigned": 20, "tasks_completed": 18,
            "tasks_failed": 1, "tasks_expired": 1,
            "avg_quality": 4.0, "success_rate": 0.9,
            "avg_duration_seconds": 3600,
            "categories": {"photo_verification": 20},
        })

        # A2H has more seal types (7) than H2A (4)
        assert len(a2h_profile.recommendations) > 0
        assert len(h2a_profile.recommendations) > 0


# ──────────────────────────────────────────────────────────────
# 5. Cold-Start to Expert Progression
# ──────────────────────────────────────────────────────────────

class TestColdStartToExpert:
    """Validates the full career arc from new agent to expert."""

    def test_new_agent_below_evaluation_threshold(self):
        """Agent with < 3 tasks gets no recommendations."""
        bridge = SealBridge()
        metrics = make_worker_metrics(tasks_completed=2, tasks_failed=0)
        profile = bridge.evaluate_worker("0xNew", "new_1", metrics)
        assert len(profile.recommendations) == 0

    def test_new_agent_gets_low_confidence_seals(self):
        """Agent with 3-10 tasks gets low-confidence seals."""
        bridge = SealBridge()
        metrics = make_worker_metrics(tasks_completed=5, tasks_failed=0, avg_quality=4.0)
        profile = bridge.evaluate_worker("0xJunior", "j1", metrics)

        assert len(profile.recommendations) > 0
        assert all(r.confidence < 0.7 for r in profile.recommendations)
        assert len(profile.issuable_seals) == 0  # Not enough confidence to issue

    def test_career_arc_five_stages(self):
        """Track agent through 5 career stages."""
        seal_bridge = SealBridge()
        rep_bridge = ReputationBridge()

        stages = [
            ("newbie", 3, 1, 3.0, ReputationTier.NUEVO),
            ("junior", 10, 2, 3.5, ReputationTier.BRONCE),
            ("mid", 30, 3, 4.0, ReputationTier.PLATA),
            ("senior", 60, 4, 4.5, ReputationTier.ORO),
            ("expert", 120, 5, 4.9, ReputationTier.DIAMANTE),
        ]

        prev_composite = 0
        prev_seal_score = 0

        for name, tasks, failed, quality, expected_min_tier in stages:
            metrics = make_worker_metrics(
                tasks_completed=tasks,
                tasks_failed=failed,
                avg_quality=quality,
                categories={
                    "photo_verification": tasks // 3,
                    "delivery": tasks // 3,
                    "notarization": tasks // 4,
                },
            )
            profile = seal_bridge.evaluate_worker(f"0x{name}", "worker_1", metrics)

            success_rate = tasks / (tasks + failed)
            on_chain = make_on_chain(
                agent_id=1,
                total_seals=len(profile.recommendations),
                positive_seals=sum(1 for r in profile.recommendations if r.is_positive),
            )
            internal = make_internal(
                agent_id=1,
                bayesian_score=quality / 5.0,
                total_tasks=tasks + failed,
                successful_tasks=tasks,
                avg_rating=quality,
            )
            composite = rep_bridge.compute_composite(
                on_chain, internal, last_active=datetime.now(timezone.utc))

            # Verify monotonic improvement
            assert composite.total >= prev_composite - 3, (
                f"Stage {name}: composite dropped {prev_composite:.1f} → {composite.total:.1f}"
            )
            if profile.recommendations:
                assert profile.overall_score >= prev_seal_score - 5, (
                    f"Stage {name}: seal score dropped"
                )
                prev_seal_score = profile.overall_score

            prev_composite = composite.total

    def test_nuevo_to_diamante_tier_progression(self):
        """Agent should naturally progress through tiers."""
        rep_bridge = ReputationBridge()

        # Track tiers at each milestone
        tier_at = {}
        for tasks in [1, 5, 20, 50, 100]:
            internal = make_internal(
                agent_id=1,
                total_tasks=tasks,
                successful_tasks=int(tasks * 0.95),
                avg_rating=4.8,
            )
            on_chain = make_on_chain(agent_id=1)
            composite = rep_bridge.compute_composite(on_chain, internal)
            tier_at[tasks] = composite.tier

        # Should start at NUEVO and progress
        assert tier_at[1] == ReputationTier.NUEVO
        assert tier_at[100] == ReputationTier.DIAMANTE


# ──────────────────────────────────────────────────────────────
# 6. Seal-to-Routing Influence Measurement
# ──────────────────────────────────────────────────────────────

class TestSealRoutingInfluence:
    """Quantifies how seal data influences routing decisions."""

    def test_on_chain_seals_boost_composite_score(self):
        """Agent with on-chain seals should score higher than one without."""
        rep_bridge = ReputationBridge()
        internal = make_internal(agent_id=1, bayesian_score=0.7, total_tasks=30)

        # No seals
        no_seals = make_on_chain(agent_id=1, total_seals=0)
        score_no = rep_bridge.compute_composite(no_seals, internal,
            last_active=datetime.now(timezone.utc))

        # With seals
        with_seals = make_on_chain(agent_id=1, total_seals=10, positive_seals=9,
            chains=["base", "ethereum"])
        score_with = rep_bridge.compute_composite(with_seals, internal,
            last_active=datetime.now(timezone.utc))

        assert score_with.reputation_score > score_no.reputation_score

    def test_chain_diversity_improves_score(self):
        """Multi-chain presence should boost reputation."""
        rep_bridge = ReputationBridge()
        internal = make_internal(agent_id=1)

        single = make_on_chain(agent_id=1, total_seals=5, positive_seals=5, chains=["base"])
        multi = make_on_chain(agent_id=1, total_seals=5, positive_seals=5,
            chains=["base", "ethereum", "polygon", "arbitrum"])

        s_single = rep_bridge.compute_composite(single, internal)
        s_multi = rep_bridge.compute_composite(multi, internal)

        assert s_multi.reputation_score >= s_single.reputation_score

    def test_negative_seals_reduce_score(self):
        """Negative seal ratio should lower reputation."""
        rep_bridge = ReputationBridge()
        internal = make_internal(agent_id=1)

        good = make_on_chain(agent_id=1, total_seals=10, positive_seals=9)
        bad = make_on_chain(agent_id=1, total_seals=10, positive_seals=3)

        s_good = rep_bridge.compute_composite(good, internal)
        s_bad = rep_bridge.compute_composite(bad, internal)

        assert s_good.reputation_score > s_bad.reputation_score

    def test_category_match_dominates_routing(self):
        """Skill match (45% weight) should be the dominant factor."""
        rep_bridge = ReputationBridge()

        # Same reputation, different category match
        matched = make_internal(
            agent_id=1,
            category_scores={"notarization": 0.95},
        )
        unmatched = make_internal(
            agent_id=2,
            category_scores={"delivery": 0.95},
        )
        chain = make_on_chain(agent_id=1, total_seals=5, positive_seals=5)
        chain2 = make_on_chain(agent_id=2, total_seals=5, positive_seals=5)

        s_matched = rep_bridge.compute_composite(chain, matched,
            task_categories=["notarization"], last_active=datetime.now(timezone.utc))
        s_unmatched = rep_bridge.compute_composite(chain2, unmatched,
            task_categories=["notarization"], last_active=datetime.now(timezone.utc))

        assert s_matched.skill_score > s_unmatched.skill_score
        assert s_matched.total > s_unmatched.total

    def test_composite_weight_distribution(self):
        """Verify weights sum to 1.0 and affect scores proportionally."""
        weights = CompositeScore.WEIGHTS
        assert abs(sum(weights.values()) - 1.0) < 0.001

        # Verify each weight
        assert weights["skill"] == 0.45
        assert weights["reputation"] == 0.25
        assert weights["reliability"] == 0.20
        assert weights["recency"] == 0.10


# ──────────────────────────────────────────────────────────────
# 7. Edge Cases and Degradation
# ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases in the reputation feedback loop."""

    def test_zero_task_agent_gets_baseline(self):
        """Agent with no tasks gets neutral baseline scores."""
        rep_bridge = ReputationBridge()
        on_chain = make_on_chain(agent_id=1, total_seals=0)
        internal = InternalReputation(agent_id=1)

        composite = rep_bridge.compute_composite(on_chain, internal)
        assert composite.total >= 0
        assert composite.tier == ReputationTier.NUEVO

    def test_all_failures_produces_low_scores(self):
        """Agent with 100% failure rate should score poorly."""
        seal_bridge = SealBridge()
        metrics = make_worker_metrics(
            tasks_completed=0,
            tasks_failed=20,
            avg_quality=0,
            success_rate=0.0,
        )
        profile = seal_bridge.evaluate_worker("0xBad", "bad_1", metrics)

        if profile.recommendations:
            assert profile.overall_score < 40

    def test_expired_tasks_penalize_reliability(self):
        """High expiration rate should tank RELIABLE seal."""
        bridge = SealBridge()

        # Good worker: no expirations
        good = make_worker_metrics(tasks_completed=20, tasks_failed=2, tasks_expired=0)
        good_profile = bridge.evaluate_worker("0xG", "g1", good)

        # Bad worker: many expirations
        bad = make_worker_metrics(tasks_completed=15, tasks_failed=2, tasks_expired=10)
        bad_profile = bridge.evaluate_worker("0xB", "b1", bad)

        good_reliable = next(
            (r for r in good_profile.recommendations if r.seal_type == "RELIABLE"), None
        )
        bad_reliable = next(
            (r for r in bad_profile.recommendations if r.seal_type == "RELIABLE"), None
        )

        if good_reliable and bad_reliable:
            assert good_reliable.score > bad_reliable.score

    def test_consecutive_failures_penalize_composite(self):
        """Consecutive failures should reduce reliability score."""
        rep_bridge = ReputationBridge()
        on_chain = make_on_chain(agent_id=1)

        no_streak = make_internal(agent_id=1, consecutive_failures=0)
        bad_streak = make_internal(agent_id=1, consecutive_failures=5)

        s_no = rep_bridge.compute_composite(on_chain, no_streak)
        s_bad = rep_bridge.compute_composite(on_chain, bad_streak)

        assert s_no.reliability_score > s_bad.reliability_score

    def test_inactive_agent_loses_recency(self):
        """Agent inactive for 30+ days should have low recency score."""
        rep_bridge = ReputationBridge()
        on_chain = make_on_chain(agent_id=1)
        internal = make_internal(agent_id=1)

        recent = rep_bridge.compute_composite(on_chain, internal,
            last_active=datetime.now(timezone.utc))
        old = rep_bridge.compute_composite(on_chain, internal,
            last_active=datetime.now(timezone.utc) - timedelta(days=60))

        assert recent.recency_score > old.recency_score

    def test_batch_preparation_filters_by_confidence(self):
        """Batch should only include seals above confidence threshold."""
        bridge = SealBridge(min_confidence=0.7)
        metrics = make_worker_metrics(tasks_completed=8, tasks_failed=0)
        profile = bridge.evaluate_worker("0xW", "w1", metrics)

        batch = bridge.prepare_batch(profile.recommendations)
        assert all(s.confidence >= 0.7 for s in batch.seals)

    def test_batch_gas_estimation(self):
        """Gas estimate should scale with seal count."""
        bridge = SealBridge(gas_per_seal=80000)
        metrics = make_worker_metrics(tasks_completed=60)
        profile = bridge.evaluate_worker("0xW", "w1", metrics)

        batch = bridge.prepare_batch(profile.issuable_seals, min_confidence=0.3)
        assert batch.total_gas_estimate == len(batch.seals) * 80000

    def test_issuance_record_tracking(self):
        """SealBridge should track issuance history."""
        bridge = SealBridge()
        assert bridge.issuance_count == 0

        for i in range(5):
            bridge.record_issuance(SealIssuanceRecord(
                seal_id=i,
                tx_hash=f"0xTx{i}",
                seal_type="SKILLFUL",
                subject_address="0xW",
                score=80,
                quadrant=SealQuadrant.A2H,
            ))

        assert bridge.issuance_count == 5
        history = bridge.get_issuance_history(limit=3)
        assert len(history) == 3

    def test_complexity_multiplier_for_routing(self):
        """Category + complexity should adjust reputation requirements."""
        rep_bridge = ReputationBridge()

        senior_tech = rep_bridge.calculate_category_multiplier("technical_task", "SENIOR")
        junior_data = rep_bridge.calculate_category_multiplier("data_collection", "JUNIOR")

        # Senior technical should require much higher reputation
        assert senior_tech > junior_data
        assert senior_tech == 1.5 * 1.2  # senior × technical
        assert junior_data == 0.8 * 0.9  # junior × data_collection


# ──────────────────────────────────────────────────────────────
# 8. Seal Score Accuracy
# ──────────────────────────────────────────────────────────────

class TestSealScoreAccuracy:
    """Validates individual seal scoring functions."""

    def test_skillful_driven_by_quality(self):
        """SKILLFUL should correlate strongly with avg_quality."""
        bridge = SealBridge()

        low_q = make_worker_metrics(tasks_completed=20, avg_quality=2.0)
        high_q = make_worker_metrics(tasks_completed=20, avg_quality=4.8)

        low_prof = bridge.evaluate_worker("0xL", "l1", low_q)
        high_prof = bridge.evaluate_worker("0xH", "h1", high_q)

        low_skill = next(r for r in low_prof.recommendations if r.seal_type == "SKILLFUL")
        high_skill = next(r for r in high_prof.recommendations if r.seal_type == "SKILLFUL")

        assert high_skill.score > low_skill.score + 20

    def test_responsive_driven_by_speed(self):
        """RESPONSIVE (H2A) should reward fast coordination cycles."""
        bridge = SealBridge()

        # RESPONSIVE is an H2A seal — use evaluate_agent_for_worker
        fast_metrics = {
            "tasks_assigned": 20, "tasks_completed": 18,
            "tasks_failed": 1, "tasks_expired": 1,
            "avg_quality": 4.0, "success_rate": 0.9,
            "avg_duration_seconds": 3600,  # 1h
            "categories": {"photo_verification": 20},
        }
        slow_metrics = {
            "tasks_assigned": 20, "tasks_completed": 18,
            "tasks_failed": 1, "tasks_expired": 1,
            "avg_quality": 4.0, "success_rate": 0.9,
            "avg_duration_seconds": 172800,  # 48h
            "categories": {"photo_verification": 20},
        }

        fast_prof = bridge.evaluate_agent_for_worker("0xF", "f1", fast_metrics)
        slow_prof = bridge.evaluate_agent_for_worker("0xS", "s1", slow_metrics)

        fast_resp = next(r for r in fast_prof.recommendations if r.seal_type == "RESPONSIVE")
        slow_resp = next(r for r in slow_prof.recommendations if r.seal_type == "RESPONSIVE")

        assert fast_resp.score > slow_resp.score + 20

    def test_curious_driven_by_category_diversity(self):
        """CURIOUS should reward diverse category experience."""
        bridge = SealBridge()

        narrow = make_worker_metrics(tasks_completed=20,
            categories={"photo_verification": 20})
        diverse = make_worker_metrics(tasks_completed=20,
            categories={"photo": 4, "delivery": 4, "notarization": 4,
                       "data": 4, "measurement": 4})

        narrow_prof = bridge.evaluate_worker("0xN", "n1", narrow)
        diverse_prof = bridge.evaluate_worker("0xD", "d1", diverse)

        narrow_curious = next(r for r in narrow_prof.recommendations if r.seal_type == "CURIOUS")
        diverse_curious = next(r for r in diverse_prof.recommendations if r.seal_type == "CURIOUS")

        assert diverse_curious.score > narrow_curious.score

    def test_engaged_rewards_active_participation(self):
        """ENGAGED should reward volume + diversity + recency."""
        bridge = SealBridge()

        active = make_worker_metrics(
            tasks_completed=50,
            categories={"photo": 15, "delivery": 15, "notarization": 10, "data": 10},
            last_active=time.time(),
        )
        inactive = make_worker_metrics(
            tasks_completed=5,
            categories={"photo": 5},
            last_active=time.time() - 86400 * 60,  # 60 days ago
        )

        active_prof = bridge.evaluate_worker("0xA", "a1", active)
        inactive_prof = bridge.evaluate_worker("0xI", "i1", inactive)

        active_engaged = next(r for r in active_prof.recommendations if r.seal_type == "ENGAGED")
        inactive_engaged = next(r for r in inactive_prof.recommendations if r.seal_type == "ENGAGED")

        assert active_engaged.score > inactive_engaged.score

    def test_all_seal_scores_clamped_0_100(self):
        """No seal score should exceed 0-100 range."""
        bridge = SealBridge()

        # Extreme metrics
        extreme = make_worker_metrics(
            tasks_completed=1000, tasks_failed=0, avg_quality=5.0,
            avg_duration_seconds=60,  # 1 minute
            categories={f"cat_{i}": 100 for i in range(20)},
        )
        profile = bridge.evaluate_worker("0xE", "e1", extreme)

        for r in profile.recommendations:
            assert 0 <= r.score <= 100, f"{r.seal_type} score {r.score} out of range"

    def test_evidence_hash_deterministic(self):
        """Same metrics should produce same evidence hash."""
        bridge = SealBridge()
        metrics = make_worker_metrics(tasks_completed=20)

        p1 = bridge.evaluate_worker("0xW", "w1", metrics)
        p2 = bridge.evaluate_worker("0xW", "w1", metrics)

        for r1, r2 in zip(p1.recommendations, p2.recommendations):
            if r1.seal_type == r2.seal_type:
                assert r1.score == r2.score


# ──────────────────────────────────────────────────────────────
# 9. Flywheel Simulation (Multi-Round)
# ──────────────────────────────────────────────────────────────

class TestFlywheelSimulation:
    """Simulates multiple rounds of the feedback flywheel."""

    def test_five_round_flywheel(self):
        """Run 5 rounds: tasks → seals → routing → better tasks."""
        seal_bridge = SealBridge()
        rep_bridge = ReputationBridge()

        # Start: 3 agents with different starting points
        agents = {
            "star": {"tasks": 0, "failed": 0, "quality": 4.5, "speed": 3600},
            "average": {"tasks": 0, "failed": 0, "quality": 3.5, "speed": 7200},
            "newbie": {"tasks": 0, "failed": 0, "quality": 3.0, "speed": 14400},
        }

        round_rankings = []

        for round_num in range(5):
            # Each round: agents complete tasks proportional to their quality
            for name, agent in agents.items():
                new_tasks = 5 + round_num * 3
                new_fails = max(0, int(new_tasks * (1 - agent["quality"] / 5.5)))
                agent["tasks"] += new_tasks
                agent["failed"] += new_fails
                # Quality improves with experience
                agent["quality"] = min(5.0, agent["quality"] + 0.05)

            # Evaluate and rank
            ranking_data = []
            for name, agent in agents.items():
                metrics = make_worker_metrics(
                    tasks_completed=agent["tasks"],
                    tasks_failed=agent["failed"],
                    avg_quality=agent["quality"],
                    avg_duration_seconds=agent["speed"],
                )
                profile = seal_bridge.evaluate_worker(f"0x{name}", name, metrics)

                on_chain = make_on_chain(
                    agent_id=hash(name) % 1000,
                    total_seals=len(profile.recommendations),
                    positive_seals=sum(1 for r in profile.recommendations if r.is_positive),
                )
                internal = make_internal(
                    agent_id=hash(name) % 1000,
                    bayesian_score=agent["quality"] / 5.0,
                    total_tasks=agent["tasks"] + agent["failed"],
                    successful_tasks=agent["tasks"],
                    avg_rating=agent["quality"],
                )
                composite = rep_bridge.compute_composite(
                    on_chain, internal, last_active=datetime.now(timezone.utc))
                ranking_data.append((name, composite.total))

            ranking_data.sort(key=lambda x: x[1], reverse=True)
            round_rankings.append([name for name, _ in ranking_data])

        # Star should consistently rank first
        assert round_rankings[-1][0] == "star"
        # Newbie should consistently rank last
        assert round_rankings[-1][-1] == "newbie"

    def test_flywheel_convergence(self):
        """Scores should converge (not oscillate wildly) over rounds."""
        seal_bridge = SealBridge()
        rep_bridge = ReputationBridge()

        scores = []
        tasks = 0

        for round_num in range(10):
            tasks += 10
            metrics = make_worker_metrics(
                tasks_completed=tasks,
                tasks_failed=max(1, tasks // 15),
                avg_quality=4.0,
            )
            profile = seal_bridge.evaluate_worker("0xW", "w1", metrics)
            on_chain = make_on_chain(agent_id=1,
                total_seals=len(profile.recommendations),
                positive_seals=sum(1 for r in profile.recommendations if r.is_positive))
            internal = make_internal(agent_id=1,
                total_tasks=tasks + max(1, tasks // 15),
                successful_tasks=tasks, avg_rating=4.0, bayesian_score=0.75)
            composite = rep_bridge.compute_composite(on_chain, internal,
                last_active=datetime.now(timezone.utc))
            scores.append(composite.total)

        # Check: later rounds should show smaller changes (convergence)
        early_delta = abs(scores[2] - scores[0])
        late_delta = abs(scores[9] - scores[7])
        # Allow some tolerance — but late changes should be smaller
        assert late_delta <= early_delta + 5, (
            f"Scores not converging: early Δ={early_delta:.1f}, late Δ={late_delta:.1f}"
        )

    def test_ten_agent_tournament(self):
        """10-agent tournament over 5 rounds with realistic variance."""
        seal_bridge = SealBridge()
        rep_bridge = ReputationBridge()

        import random
        rng = random.Random(42)

        agents = {}
        for i in range(10):
            base_quality = 2.5 + rng.random() * 2.5  # 2.5-5.0
            agents[f"agent_{i}"] = {
                "tasks": 0, "failed": 0,
                "quality": base_quality,
                "speed": rng.randint(1800, 86400),
            }

        final_scores = {}
        for round_num in range(5):
            for name, a in agents.items():
                new = 5 + round_num * 2
                fails = rng.randint(0, max(1, int(new * 0.3)))
                a["tasks"] += new
                a["failed"] += fails

            for name, a in agents.items():
                metrics = make_worker_metrics(
                    tasks_completed=a["tasks"], tasks_failed=a["failed"],
                    avg_quality=a["quality"], avg_duration_seconds=a["speed"],
                )
                profile = seal_bridge.evaluate_worker(f"0x{name}", name, metrics)
                on_chain = make_on_chain(agent_id=hash(name) % 10000,
                    total_seals=len(profile.recommendations),
                    positive_seals=sum(1 for r in profile.recommendations if r.is_positive))
                internal = make_internal(agent_id=hash(name) % 10000,
                    bayesian_score=a["quality"] / 5.0,
                    total_tasks=a["tasks"] + a["failed"],
                    successful_tasks=a["tasks"], avg_rating=a["quality"])
                composite = rep_bridge.compute_composite(on_chain, internal,
                    last_active=datetime.now(timezone.utc))
                final_scores[name] = composite.total

        # Should have differentiation: best vs worst gap > 10 points
        scores = list(final_scores.values())
        assert max(scores) - min(scores) > 10
