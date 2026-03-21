"""
ReputationBridge — Connects on-chain ERC-8004 reputation with internal scoring.

Bridges three data sources into a unified agent capability profile:
1. On-chain ERC-8004 reputation seals (immutable, cross-platform)
2. Internal Bayesian reputation scores (real-time, platform-specific)
3. Task completion history (evidence-based Skill DNA)

The bridge produces a CompositeScore that the SwarmOrchestrator uses
for task routing decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import math


class ReputationTier(str, Enum):
    """On-chain reputation tiers from ERC-8004 seals."""

    DIAMANTE = "diamante"
    ORO = "oro"
    PLATA = "plata"
    BRONCE = "bronce"
    NUEVO = "nuevo"  # No seals yet


# Tier bonus points (out of 100)
TIER_BONUSES = {
    ReputationTier.DIAMANTE: 15,
    ReputationTier.ORO: 10,
    ReputationTier.PLATA: 5,
    ReputationTier.BRONCE: 2,
    ReputationTier.NUEVO: 0,
}

# Minimum tasks to qualify for each tier
TIER_THRESHOLDS = {
    ReputationTier.DIAMANTE: {
        "min_tasks": 100,
        "min_rating": 4.8,
        "min_success_rate": 0.95,
    },
    ReputationTier.ORO: {"min_tasks": 50, "min_rating": 4.5, "min_success_rate": 0.90},
    ReputationTier.PLATA: {
        "min_tasks": 20,
        "min_rating": 4.0,
        "min_success_rate": 0.80,
    },
    ReputationTier.BRONCE: {
        "min_tasks": 5,
        "min_rating": 3.0,
        "min_success_rate": 0.60,
    },
}


@dataclass
class OnChainReputation:
    """Data from ERC-8004 identity + reputation contracts."""

    agent_id: int
    wallet_address: str
    total_seals: int = 0
    positive_seals: int = 0
    negative_seals: int = 0
    chains_active: list[str] = field(default_factory=list)
    registered_at: Optional[datetime] = None
    last_seal_at: Optional[datetime] = None

    @property
    def seal_ratio(self) -> float:
        """Positive seal ratio (0.0 to 1.0)."""
        if self.total_seals == 0:
            return 0.0
        return self.positive_seals / self.total_seals

    @property
    def chain_diversity(self) -> float:
        """Normalized chain diversity score (0.0 to 1.0). Max at 8 chains."""
        return min(len(self.chains_active) / 8.0, 1.0)


@dataclass
class InternalReputation:
    """Data from the internal Bayesian reputation system."""

    agent_id: int
    bayesian_score: float = 0.5  # 0.0 to 1.0, starts at neutral
    total_tasks: int = 0
    successful_tasks: int = 0
    avg_rating: float = 0.0  # 1.0 to 5.0
    avg_completion_time_hours: float = 0.0
    consecutive_failures: int = 0
    category_scores: dict[str, float] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def on_time_rate(self) -> float:
        """Proxy for on-time delivery. Tasks completed under 24h threshold."""
        if self.avg_completion_time_hours <= 0:
            return 0.0
        # Perfect score if avg under 4h, degrades linearly to 24h
        if self.avg_completion_time_hours <= 4:
            return 1.0
        if self.avg_completion_time_hours >= 24:
            return 0.2
        return 1.0 - 0.8 * ((self.avg_completion_time_hours - 4) / 20)


@dataclass
class CompositeScore:
    """
    Unified reputation score used for task routing.

    Weights:
    - skill_match: 45% — How well does the agent match the task?
    - reputation: 25% — On-chain + internal reputation
    - reliability: 20% — Completion rate, on-time, consistency
    - recency: 10% — How recently active?
    """

    agent_id: int
    skill_score: float = 0.0  # 0-100
    reputation_score: float = 0.0  # 0-100
    reliability_score: float = 0.0  # 0-100
    recency_score: float = 0.0  # 0-100
    tier: ReputationTier = ReputationTier.NUEVO
    tier_bonus: float = 0.0

    WEIGHTS = {
        "skill": 0.45,
        "reputation": 0.25,
        "reliability": 0.20,
        "recency": 0.10,
    }

    @property
    def total(self) -> float:
        """Weighted total score (0-100 base + tier bonus)."""
        raw = (
            self.skill_score * self.WEIGHTS["skill"]
            + self.reputation_score * self.WEIGHTS["reputation"]
            + self.reliability_score * self.WEIGHTS["reliability"]
            + self.recency_score * self.WEIGHTS["recency"]
            + self.tier_bonus
        )
        return raw

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "total": round(self.total, 2),
            "skill": round(self.skill_score, 2),
            "reputation": round(self.reputation_score, 2),
            "reliability": round(self.reliability_score, 2),
            "recency": round(self.recency_score, 2),
            "tier": self.tier.value,
            "tier_bonus": self.tier_bonus,
        }


class ReputationBridge:
    """
    Bridges on-chain and internal reputation into composite scores.

    Usage:
        bridge = ReputationBridge()
        score = bridge.compute_composite(
            on_chain=on_chain_data,
            internal=internal_data,
            task_categories=["photo_verification"],
            last_active=datetime(2026, 3, 10),
        )
        print(f"Agent {score.agent_id}: {score.total:.1f}")
    """

    def compute_composite(
        self,
        on_chain: OnChainReputation,
        internal: InternalReputation,
        task_categories: list[str] | None = None,
        last_active: datetime | None = None,
    ) -> CompositeScore:
        """Compute unified composite score for task routing."""
        tier = self._determine_tier(internal)

        score = CompositeScore(
            agent_id=on_chain.agent_id,
            skill_score=self._compute_skill_score(internal, task_categories or []),
            reputation_score=self._compute_reputation_score(on_chain, internal),
            reliability_score=self._compute_reliability_score(internal),
            recency_score=self._compute_recency_score(last_active),
            tier=tier,
            tier_bonus=TIER_BONUSES[tier],
        )
        return score

    def _determine_tier(self, internal: InternalReputation) -> ReputationTier:
        """Determine reputation tier from internal metrics."""
        for tier in [
            ReputationTier.DIAMANTE,
            ReputationTier.ORO,
            ReputationTier.PLATA,
            ReputationTier.BRONCE,
        ]:
            thresholds = TIER_THRESHOLDS[tier]
            if (
                internal.total_tasks >= thresholds["min_tasks"]
                and internal.avg_rating >= thresholds["min_rating"]
                and internal.success_rate >= thresholds["min_success_rate"]
            ):
                return tier
        return ReputationTier.NUEVO

    def _compute_skill_score(
        self,
        internal: InternalReputation,
        task_categories: list[str],
    ) -> float:
        """
        Skill match score (0-100).
        Based on category-specific success rates from task history.
        """
        if not task_categories or not internal.category_scores:
            # Fallback: use global success rate as rough proxy
            return internal.success_rate * 60 + min(internal.total_tasks / 50, 1.0) * 40

        # Average category-specific scores
        category_hits = []
        for cat in task_categories:
            if cat in internal.category_scores:
                category_hits.append(internal.category_scores[cat])

        if not category_hits:
            # Agent has no experience in requested categories
            # Give partial credit based on general experience
            return min(internal.total_tasks / 100, 1.0) * 30

        avg_category = sum(category_hits) / len(category_hits)
        coverage = len(category_hits) / len(task_categories)

        # Weighted: 70% category match quality, 30% coverage breadth
        return avg_category * 70 + coverage * 30

    def _compute_reputation_score(
        self,
        on_chain: OnChainReputation,
        internal: InternalReputation,
    ) -> float:
        """
        Reputation score (0-100).
        Blends on-chain seal data with internal Bayesian score.
        """
        # On-chain component (40% of reputation score)
        if on_chain.total_seals == 0:
            on_chain_score = 20  # Neutral baseline for new agents
        else:
            on_chain_score = on_chain.seal_ratio * 80 + on_chain.chain_diversity * 20

        # Internal Bayesian component (60% of reputation score)
        internal_score = internal.bayesian_score * 100

        # Blend: internal data is richer, but on-chain is tamper-proof
        return on_chain_score * 0.4 + internal_score * 0.6

    def _compute_reliability_score(self, internal: InternalReputation) -> float:
        """
        Reliability score (0-100).
        Based on success rate, rating, and task volume.
        """
        if internal.total_tasks == 0:
            return 10  # Low baseline for untested agents

        # Success rate (0-40 points)
        success_pts = internal.success_rate * 40

        # Average rating (0-40 points)
        if internal.avg_rating > 0:
            rating_pts = (internal.avg_rating / 5.0) * 40
        else:
            rating_pts = 0

        # Task volume (0-20 points, logarithmic scale)
        # 1 task = ~0, 10 tasks = ~13, 50 tasks = ~17, 100+ = 20
        volume_pts = min(
            math.log10(max(internal.total_tasks, 1)) / math.log10(100) * 20, 20
        )

        # Penalty for consecutive failures
        failure_penalty = min(internal.consecutive_failures * 5, 25)

        return max(0, success_pts + rating_pts + volume_pts - failure_penalty)

    def _compute_recency_score(self, last_active: datetime | None) -> float:
        """
        Recency score (0-100).
        How recently was the agent active? Exponential decay.
        """
        if last_active is None:
            return 0

        now = datetime.now(timezone.utc)
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)

        days_since = (now - last_active).total_seconds() / 86400

        if days_since < 0:
            return 100  # Active in the future? Treat as just now.
        if days_since <= 1:
            return 100
        if days_since <= 7:
            return 100 - (days_since - 1) * (10 / 6)  # 100 → 90 over 6 days
        if days_since <= 30:
            return 90 - (days_since - 7) * (20 / 23)  # 90 → 70 over 23 days
        if days_since <= 90:
            return 70 - (days_since - 30) * (30 / 60)  # 70 → 40 over 60 days

        # After 90 days: exponential decay toward 0
        return max(0, 40 * math.exp(-(days_since - 90) / 60))

    def rank_agents(
        self,
        agents: list[tuple[OnChainReputation, InternalReputation]],
        task_categories: list[str] | None = None,
        last_active_map: dict[int, datetime] | None = None,
    ) -> list[CompositeScore]:
        """
        Rank multiple agents for a task. Returns sorted list (best first).
        """
        last_active_map = last_active_map or {}
        scores = []

        for on_chain, internal in agents:
            score = self.compute_composite(
                on_chain=on_chain,
                internal=internal,
                task_categories=task_categories,
                last_active=last_active_map.get(on_chain.agent_id),
            )
            scores.append(score)

        scores.sort(key=lambda s: s.total, reverse=True)
        return scores

    def calculate_category_multiplier(
        self, category: str, complexity_tier: str
    ) -> float:
        """
        Dynamically adjust the reputation requirements based on task complexity.
        Senior technical tasks require a higher reputation bridge multiplier.
        """
        base_multiplier = 1.0
        if complexity_tier == "SENIOR":
            base_multiplier = 1.5
        elif complexity_tier == "JUNIOR":
            base_multiplier = 0.8

        category_weights = {
            "technical_task": 1.2,
            "notarization": 1.5,
            "physical_verification": 1.1,
            "data_collection": 0.9,
        }

        return base_multiplier * category_weights.get(category, 1.0)
