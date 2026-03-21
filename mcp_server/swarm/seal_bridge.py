"""
SealBridge — Analytics-to-On-Chain Reputation Pipeline
======================================================

Bridges the gap between SwarmAnalytics (off-chain performance data)
and describe-net's SealRegistry (on-chain categorical reputation seals).

This creates the bidirectional flywheel:
  Task completion → Analytics metrics → Seal recommendations → On-chain seals
  On-chain seals → ReputationBridge input → Better routing → More completions

Architecture:
    SwarmAnalytics    → SealBridge.evaluate_agent()  → SealRecommendation[]
    SealBridge        → SealRegistry (on-chain)      → Issued seals
    SealRegistry      → ReputationBridge.on_chain     → Composite routing scores

Seal Types Mapped:
    SKILLFUL    ← avg_quality (task completion quality)
    RELIABLE    ← success_rate × task_volume (consistency + track record)
    THOROUGH    ← evidence_richness × quality (completeness)
    ENGAGED     ← task_frequency × category_diversity (active participation)
    RESPONSIVE  ← avg_duration (speed of completion)
    CURIOUS     ← category_count × category_diversity (breadth of work)

All scores are 0-100, matching SealRegistry's uint8 score range.
"""

import hashlib
import json
import math
import time
from dataclasses import dataclass, field, asdict
from enum import Enum


# ──────────────────────────────────────────────────────────────
# Constants: describe-net seal types (keccak256 hashes)
# ──────────────────────────────────────────────────────────────

SEAL_TYPES = {
    "SKILLFUL": "skillful",
    "RELIABLE": "reliable",
    "THOROUGH": "thorough",
    "ENGAGED": "engaged",
    "RESPONSIVE": "responsive",
    "CURIOUS": "curious",
    "HELPFUL": "helpful",
    "FAIR": "fair",
    "ACCURATE": "accurate",
    "ETHICAL": "ethical",
    "CREATIVE": "creative",
    "PROFESSIONAL": "professional",
    "FRIENDLY": "friendly",
}

# A2H seals (agent evaluates human worker)
A2H_SEALS = {"SKILLFUL", "RELIABLE", "THOROUGH", "ENGAGED", "HELPFUL", "CURIOUS"}

# H2A seals (human evaluates agent)
H2A_SEALS = {"FAIR", "ACCURATE", "RESPONSIVE", "ETHICAL"}


class SealQuadrant(str, Enum):
    """Matches SealRegistry.sol Quadrant enum."""

    H2H = "H2H"  # 0
    H2A = "H2A"  # 1
    A2H = "A2H"  # 2
    A2A = "A2A"  # 3


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class SealRecommendation:
    """A recommended seal to issue based on analytics data."""

    seal_type: str  # e.g., "SKILLFUL"
    quadrant: SealQuadrant
    subject_address: str  # Who receives the seal
    evaluator_agent_id: str  # Who issues the seal
    score: int  # 0-100
    confidence: float  # 0.0-1.0 (how much data backs this)
    evidence_summary: str  # Human-readable evidence
    evidence_hash: str  # SHA256 of evidence JSON
    reasoning: str  # Why this score
    metrics_snapshot: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quadrant"] = self.quadrant.value
        return d

    @property
    def is_high_confidence(self) -> bool:
        """Confidence >= 0.7 means enough data to issue."""
        return self.confidence >= 0.7

    @property
    def is_positive(self) -> bool:
        """Score >= 60 is a positive seal."""
        return self.score >= 60


@dataclass
class SealProfile:
    """Complete seal profile for an agent/worker."""

    address: str
    agent_id: str
    recommendations: list[SealRecommendation] = field(default_factory=list)
    overall_score: float = 0.0
    evaluated_at: float = field(default_factory=time.time)
    data_points: int = 0  # How many tasks informed this

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "agent_id": self.agent_id,
            "overall_score": round(self.overall_score, 2),
            "evaluated_at": self.evaluated_at,
            "data_points": self.data_points,
            "seal_count": len(self.recommendations),
            "high_confidence_seals": sum(
                1 for r in self.recommendations if r.is_high_confidence
            ),
            "seals": [r.to_dict() for r in self.recommendations],
        }

    @property
    def issuable_seals(self) -> list[SealRecommendation]:
        """Seals with enough confidence to issue on-chain."""
        return [r for r in self.recommendations if r.is_high_confidence]


@dataclass
class BatchSealRequest:
    """A batch of seals ready for on-chain submission."""

    seals: list[SealRecommendation]
    total_gas_estimate: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "seal_count": len(self.seals),
            "total_gas_estimate": self.total_gas_estimate,
            "created_at": self.created_at,
            "seals": [s.to_dict() for s in self.seals],
        }


@dataclass
class SealIssuanceRecord:
    """Record of a seal that was issued on-chain."""

    seal_id: int  # On-chain seal ID
    tx_hash: str
    seal_type: str
    subject_address: str
    score: int
    quadrant: SealQuadrant
    issued_at: float = field(default_factory=time.time)
    block_number: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quadrant"] = self.quadrant.value
        return d


# ──────────────────────────────────────────────────────────────
# Scoring Functions
# ──────────────────────────────────────────────────────────────


def _compute_evidence_hash(evidence: dict) -> str:
    """Deterministic hash of evidence data for on-chain anchoring."""
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _sigmoid(x: float, midpoint: float = 0.5, steepness: float = 10.0) -> float:
    """Sigmoid function for smooth score transitions."""
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
    except OverflowError:
        return 0.0 if x < midpoint else 1.0


def _log_scale(value: float, reference: float) -> float:
    """Logarithmic scaling: grows fast initially, then plateaus."""
    if value <= 0 or reference <= 0:
        return 0.0
    return min(math.log(1 + value) / math.log(1 + reference), 1.0)


# ──────────────────────────────────────────────────────────────
# SealBridge
# ──────────────────────────────────────────────────────────────


class SealBridge:
    """
    Bridges SwarmAnalytics data to describe-net seal recommendations.

    Evaluates agent/worker performance from analytics metrics and produces
    SealRecommendation objects ready for on-chain submission to SealRegistry.

    Usage:
        from mcp_server.swarm.seal_bridge import SealBridge
        from mcp_server.swarm.analytics import SwarmAnalytics

        bridge = SealBridge(evaluator_agent_id="agent_2106")
        analytics = SwarmAnalytics()

        # Evaluate a worker based on their analytics data
        metrics = analytics.get_agent_detail("worker_42")
        profile = bridge.evaluate_worker(
            worker_address="0x1234...",
            agent_id="worker_42",
            metrics=metrics,
        )

        # Get seals ready for on-chain submission
        batch = bridge.prepare_batch(profile.issuable_seals)
    """

    # Minimum thresholds for seal evaluation
    MIN_TASKS_FOR_EVALUATION = 3
    MIN_TASKS_FOR_HIGH_CONFIDENCE = 10
    CONFIDENCE_FULL_AT = 50  # Tasks needed for full confidence

    # Score anchors (what constitutes "good" performance)
    QUALITY_EXCELLENT = 4.5  # out of 5.0
    QUALITY_GOOD = 3.5
    QUALITY_POOR = 2.0

    SPEED_FAST_HOURS = 2.0  # Under 2h = fast
    SPEED_NORMAL_HOURS = 12.0  # Under 12h = normal
    SPEED_SLOW_HOURS = 48.0  # Over 48h = slow

    CATEGORY_DIVERSE = 5  # 5+ categories = diverse
    CATEGORY_SPECIALIST = 1  # 1 category = specialist

    def __init__(
        self,
        evaluator_agent_id: str = "swarm_coordinator",
        min_confidence: float = 0.5,
        gas_per_seal: int = 80000,
    ):
        self._evaluator_agent_id = evaluator_agent_id
        self._min_confidence = min_confidence
        self._gas_per_seal = gas_per_seal
        self._issuance_history: list[SealIssuanceRecord] = []
        self._max_issuance_history = 5000

    # ──────────────────────────────────────────────────────────
    # Evaluation
    # ──────────────────────────────────────────────────────────

    def evaluate_worker(
        self,
        worker_address: str,
        agent_id: str,
        metrics: dict,
        quadrant: SealQuadrant = SealQuadrant.A2H,
    ) -> SealProfile:
        """
        Evaluate a worker and generate seal recommendations.

        Args:
            worker_address: On-chain address of the worker
            agent_id: Internal agent/worker ID
            metrics: Dict from SwarmAnalytics.get_agent_detail()
            quadrant: Seal quadrant (default A2H for agent evaluating human)

        Returns:
            SealProfile with recommendations for each seal type
        """
        profile = SealProfile(
            address=worker_address,
            agent_id=agent_id,
        )

        total_tasks = metrics.get("tasks_completed", 0) + metrics.get("tasks_failed", 0)
        profile.data_points = total_tasks

        if total_tasks < self.MIN_TASKS_FOR_EVALUATION:
            return profile  # Not enough data

        # Base confidence from task volume
        base_confidence = self._compute_confidence(total_tasks)

        # Generate each seal recommendation
        seal_fns = {
            "SKILLFUL": self._score_skillful,
            "RELIABLE": self._score_reliable,
            "THOROUGH": self._score_thorough,
            "ENGAGED": self._score_engaged,
            "HELPFUL": self._score_helpful,
            "RESPONSIVE": self._score_responsive,
            "CURIOUS": self._score_curious,
        }

        seal_set = A2H_SEALS if quadrant == SealQuadrant.A2H else H2A_SEALS

        for seal_type, score_fn in seal_fns.items():
            if seal_type not in seal_set:
                continue

            score, reasoning, evidence = score_fn(metrics)
            score = max(0, min(100, score))  # Clamp

            # Adjust confidence based on score extremes
            confidence = base_confidence
            if score > 90 or score < 20:
                confidence *= 0.9  # Extreme scores need more data
            if metrics.get("tasks_completed", 0) == 0 and score > 50:
                confidence *= 0.5  # No completions but positive score? Lower confidence

            evidence_data = {
                "agent_id": agent_id,
                "seal_type": seal_type,
                "metrics": {
                    k: v
                    for k, v in metrics.items()
                    if k
                    in (
                        "tasks_completed",
                        "tasks_failed",
                        "tasks_expired",
                        "avg_quality",
                        "avg_duration_seconds",
                        "success_rate",
                        "categories",
                        "total_revenue_usd",
                    )
                },
                "evaluated_at": time.time(),
            }

            rec = SealRecommendation(
                seal_type=seal_type,
                quadrant=quadrant,
                subject_address=worker_address,
                evaluator_agent_id=self._evaluator_agent_id,
                score=int(round(score)),
                confidence=round(min(confidence, 1.0), 3),
                evidence_summary=evidence,
                evidence_hash=_compute_evidence_hash(evidence_data),
                reasoning=reasoning,
                metrics_snapshot=evidence_data["metrics"],
            )
            profile.recommendations.append(rec)

        # Overall score: weighted average of all seal scores
        if profile.recommendations:
            total_weight = sum(r.confidence for r in profile.recommendations)
            if total_weight > 0:
                profile.overall_score = (
                    sum(r.score * r.confidence for r in profile.recommendations)
                    / total_weight
                )

        return profile

    def evaluate_agent_for_worker(
        self,
        agent_address: str,
        agent_id: str,
        metrics: dict,
    ) -> SealProfile:
        """
        Generate H2A seal recommendations (human evaluating agent).

        Uses different seal types: FAIR, ACCURATE, RESPONSIVE, ETHICAL.
        Typically called when a worker wants to rate the agent that assigned them tasks.
        """
        profile = SealProfile(
            address=agent_address,
            agent_id=agent_id,
        )

        total_tasks = metrics.get("tasks_assigned", 0)
        profile.data_points = total_tasks

        if total_tasks < self.MIN_TASKS_FOR_EVALUATION:
            return profile

        base_confidence = self._compute_confidence(total_tasks)

        # H2A seal scoring
        h2a_scorers = {
            "FAIR": self._score_fair,
            "ACCURATE": self._score_accurate,
            "RESPONSIVE": self._score_responsive_h2a,
            "ETHICAL": self._score_ethical,
        }

        for seal_type, score_fn in h2a_scorers.items():
            score, reasoning, evidence = score_fn(metrics)
            score = max(0, min(100, score))

            evidence_data = {
                "agent_id": agent_id,
                "seal_type": seal_type,
                "quadrant": "H2A",
                "metrics": {
                    k: v
                    for k, v in metrics.items()
                    if k
                    in (
                        "tasks_assigned",
                        "tasks_completed",
                        "tasks_failed",
                        "avg_quality",
                        "success_rate",
                        "categories",
                    )
                },
                "evaluated_at": time.time(),
            }

            rec = SealRecommendation(
                seal_type=seal_type,
                quadrant=SealQuadrant.H2A,
                subject_address=agent_address,
                evaluator_agent_id=self._evaluator_agent_id,
                score=int(round(score)),
                confidence=round(min(base_confidence, 1.0), 3),
                evidence_summary=evidence,
                evidence_hash=_compute_evidence_hash(evidence_data),
                reasoning=reasoning,
                metrics_snapshot=evidence_data["metrics"],
            )
            profile.recommendations.append(rec)

        if profile.recommendations:
            total_weight = sum(r.confidence for r in profile.recommendations)
            if total_weight > 0:
                profile.overall_score = (
                    sum(r.score * r.confidence for r in profile.recommendations)
                    / total_weight
                )

        return profile

    # ──────────────────────────────────────────────────────────
    # A2H Seal Scorers
    # ──────────────────────────────────────────────────────────

    def _score_skillful(self, metrics: dict) -> tuple[float, str, str]:
        """
        SKILLFUL: Technical competency and expertise.
        Derived from avg_quality and success_rate.
        """
        avg_quality = metrics.get("avg_quality", 0)
        success_rate = metrics.get("success_rate", 0)
        tasks = metrics.get("tasks_completed", 0)

        # Quality is 70% of SKILLFUL, success_rate is 30%
        if avg_quality > 0:
            quality_score = (avg_quality / 5.0) * 100
        else:
            quality_score = 50  # Neutral if no ratings

        success_score = success_rate * 100

        score = quality_score * 0.7 + success_score * 0.3

        # Volume adjustment: slight boost for high task count
        volume_factor = _log_scale(tasks, 100)
        score = score * (0.85 + 0.15 * volume_factor)

        reasoning = (
            f"Quality {avg_quality:.1f}/5.0 ({quality_score:.0f}pts), "
            f"success {success_rate:.0%} ({success_score:.0f}pts), "
            f"volume factor {volume_factor:.2f}"
        )
        evidence = f"{tasks} tasks completed, avg quality {avg_quality:.1f}, {success_rate:.0%} success"

        return score, reasoning, evidence

    def _score_reliable(self, metrics: dict) -> tuple[float, str, str]:
        """
        RELIABLE: Consistent performance and dependability.
        Derived from success_rate, task volume, and consecutive failures.
        """
        success_rate = metrics.get("success_rate", 0)
        completed = metrics.get("tasks_completed", 0)
        failed = metrics.get("tasks_failed", 0)
        expired = metrics.get("tasks_expired", 0)

        # Base: success rate is king for reliability
        score = success_rate * 80

        # Volume bonus: more tasks = more data = more trust
        volume_bonus = _log_scale(completed, 50) * 20
        score += volume_bonus

        # Penalty for expirations (worse than failures — shows abandonment)
        if expired > 0:
            expiry_ratio = expired / max(completed + failed + expired, 1)
            expiry_penalty = expiry_ratio * 30
            score -= expiry_penalty

        reasoning = (
            f"Success rate {success_rate:.0%} (×80={success_rate * 80:.0f}), "
            f"volume bonus {volume_bonus:.1f}/20, "
            f"expired: {expired}"
        )
        evidence = f"{completed}/{completed + failed + expired} tasks successful, {expired} expired"

        return score, reasoning, evidence

    def _score_thorough(self, metrics: dict) -> tuple[float, str, str]:
        """
        THOROUGH: Attention to detail and completeness.
        Derived from quality ratings and consistency of high performance.
        """
        avg_quality = metrics.get("avg_quality", 0)
        quality_scores = metrics.get("quality_scores", [])
        completed = metrics.get("tasks_completed", 0)

        if not quality_scores and avg_quality > 0:
            # Synthesize from average
            quality_scores = [avg_quality] * min(completed, 10)

        if not quality_scores:
            return 50, "No quality data available", "No quality ratings recorded"

        # Consistency: low variance = thorough
        mean_q = sum(quality_scores) / len(quality_scores)
        if len(quality_scores) > 1:
            variance = sum((q - mean_q) ** 2 for q in quality_scores) / len(
                quality_scores
            )
            std_dev = math.sqrt(variance)
            consistency = max(
                0, 1.0 - std_dev / 2.5
            )  # Normalize: std 0 → 1.0, std 2.5 → 0
        else:
            consistency = 0.5

        # Quality baseline
        quality_pct = (mean_q / 5.0) * 100

        # Score: 60% quality, 40% consistency
        score = quality_pct * 0.6 + consistency * 100 * 0.4

        reasoning = (
            f"Mean quality {mean_q:.2f}/5 ({quality_pct:.0f}pts), "
            f"consistency {consistency:.2f} (std={std_dev if len(quality_scores) > 1 else 'N/A'})"
        )
        evidence = f"Avg quality {mean_q:.1f}/5 over {len(quality_scores)} ratings, consistency {consistency:.0%}"

        return score, reasoning, evidence

    def _score_engaged(self, metrics: dict) -> tuple[float, str, str]:
        """
        ENGAGED: Active participation and involvement.
        Derived from task frequency and breadth of activity.
        """
        completed = metrics.get("tasks_completed", 0)
        categories = metrics.get("categories", {})
        revenue = metrics.get("total_revenue_usd", 0)
        last_active = metrics.get("last_active", 0)

        # Task volume (0-50 points, log scale)
        volume_pts = _log_scale(completed, 100) * 50

        # Category diversity (0-30 points)
        cat_count = len(categories) if isinstance(categories, dict) else 0
        diversity_pts = min(cat_count / self.CATEGORY_DIVERSE, 1.0) * 30

        # Recency (0-20 points)
        if last_active > 0:
            days_since = (time.time() - last_active) / 86400
            if days_since <= 1:
                recency_pts = 20
            elif days_since <= 7:
                recency_pts = 20 - (days_since / 7) * 10
            elif days_since <= 30:
                recency_pts = 10 - ((days_since - 7) / 23) * 10
            else:
                recency_pts = 0
        else:
            recency_pts = 0

        score = volume_pts + diversity_pts + recency_pts

        reasoning = (
            f"Volume {volume_pts:.1f}/50, "
            f"diversity {diversity_pts:.1f}/30 ({cat_count} categories), "
            f"recency {recency_pts:.1f}/20"
        )
        evidence = (
            f"{completed} tasks across {cat_count} categories, ${revenue:.2f} revenue"
        )

        return score, reasoning, evidence

    def _score_helpful(self, metrics: dict) -> tuple[float, str, str]:
        """
        HELPFUL: Willingness to assist and support.
        Derived from task volume, completion rate, and category breadth.
        A helpful worker takes on tasks reliably and across diverse needs.
        """
        completed = metrics.get("tasks_completed", 0)
        failed = metrics.get("tasks_failed", 0)
        expired = metrics.get("tasks_expired", 0)
        total = completed + failed + expired
        categories = metrics.get("categories", {})

        if total == 0:
            return 30, "No tasks attempted", "No task history"

        # Completion willingness (0-50 points)
        completion_rate = completed / total if total > 0 else 0
        willingness_pts = completion_rate * 50

        # Volume of help (0-30 points, log scale)
        volume_pts = _log_scale(completed, 50) * 30

        # Breadth of help (0-20 points)
        cat_count = len(categories) if isinstance(categories, dict) else 0
        breadth_pts = min(cat_count / 4, 1.0) * 20

        score = willingness_pts + volume_pts + breadth_pts

        reasoning = (
            f"Completion {completion_rate:.0%} ({willingness_pts:.0f}/50), "
            f"volume {volume_pts:.0f}/30, "
            f"breadth {breadth_pts:.0f}/20 ({cat_count} categories)"
        )
        evidence = f"{completed}/{total} tasks completed across {cat_count} categories"

        return score, reasoning, evidence

    def _score_responsive(self, metrics: dict) -> tuple[float, str, str]:
        """
        RESPONSIVE: Timely completion of tasks.
        Derived from average completion duration.
        """
        avg_duration = metrics.get("avg_duration_seconds", 0)
        durations = metrics.get("durations", [])
        completed = metrics.get("tasks_completed", 0)

        if completed == 0 or avg_duration <= 0:
            return 50, "No completion time data", "No tasks with duration recorded"

        avg_hours = avg_duration / 3600.0

        # Speed scoring
        if avg_hours <= self.SPEED_FAST_HOURS:
            speed_score = 100
        elif avg_hours <= self.SPEED_NORMAL_HOURS:
            # Linear interpolation: 2h=100, 12h=60
            t = (avg_hours - self.SPEED_FAST_HOURS) / (
                self.SPEED_NORMAL_HOURS - self.SPEED_FAST_HOURS
            )
            speed_score = 100 - t * 40
        elif avg_hours <= self.SPEED_SLOW_HOURS:
            # 12h=60, 48h=20
            t = (avg_hours - self.SPEED_NORMAL_HOURS) / (
                self.SPEED_SLOW_HOURS - self.SPEED_NORMAL_HOURS
            )
            speed_score = 60 - t * 40
        else:
            speed_score = max(0, 20 - (avg_hours - self.SPEED_SLOW_HOURS) / 24 * 10)

        # Consistency bonus (low variance in durations)
        if len(durations) > 1:
            mean_d = sum(durations) / len(durations)
            var_d = sum((d - mean_d) ** 2 for d in durations) / len(durations)
            cv = (
                math.sqrt(var_d) / mean_d if mean_d > 0 else 1.0
            )  # Coefficient of variation
            consistency_bonus = max(0, (1 - cv) * 10)
        else:
            consistency_bonus = 0

        score = speed_score + consistency_bonus

        reasoning = (
            f"Avg {avg_hours:.1f}h → speed score {speed_score:.0f}, "
            f"consistency bonus {consistency_bonus:.1f}"
        )
        evidence = f"Average completion: {avg_hours:.1f} hours across {completed} tasks"

        return score, reasoning, evidence

    def _score_curious(self, metrics: dict) -> tuple[float, str, str]:
        """
        CURIOUS: Breadth of task categories attempted.
        Derived from category diversity and willingness to try new types.
        """
        categories = metrics.get("categories", {})

        if not categories or not isinstance(categories, dict):
            return 30, "No category data", "No category distribution recorded"

        cat_count = len(categories)
        total_in_cats = sum(categories.values())

        # Diversity: more categories = more curious
        diversity_score = min(cat_count / self.CATEGORY_DIVERSE, 1.0) * 60

        # Evenness: balanced distribution across categories (Shannon entropy)
        if total_in_cats > 0 and cat_count > 1:
            max_entropy = math.log(cat_count)
            entropy = -sum(
                (c / total_in_cats) * math.log(c / total_in_cats)
                for c in categories.values()
                if c > 0
            )
            evenness = entropy / max_entropy if max_entropy > 0 else 0
        else:
            evenness = 0

        evenness_score = evenness * 40

        score = diversity_score + evenness_score

        reasoning = (
            f"{cat_count} categories → diversity {diversity_score:.0f}/60, "
            f"evenness {evenness:.2f} → {evenness_score:.0f}/40"
        )
        evidence = f"{cat_count} task categories, distribution evenness {evenness:.0%}"

        return score, reasoning, evidence

    # ──────────────────────────────────────────────────────────
    # H2A Seal Scorers (human evaluating agent)
    # ──────────────────────────────────────────────────────────

    def _score_fair(self, metrics: dict) -> tuple[float, str, str]:
        """
        FAIR: Agent distributes work fairly across workers.
        Proxy: category diversity of tasks assigned (not concentrated on one type).
        """
        categories = metrics.get("categories", {})
        assigned = metrics.get("tasks_assigned", 0)

        if not categories or assigned == 0:
            return 50, "Insufficient data for fairness evaluation", "No assignment data"

        # Fairness proxy: does the agent work across categories?
        cat_count = len(categories)
        total = sum(categories.values())

        # Gini coefficient (0 = perfect equality, 1 = complete inequality)
        if cat_count > 1 and total > 0:
            sorted_vals = sorted(categories.values())
            n = len(sorted_vals)
            cumulative = sum((2 * (i + 1) - n - 1) * sorted_vals[i] for i in range(n))
            gini = cumulative / (n * total) if total > 0 else 0
            fairness = (1 - gini) * 100
        else:
            fairness = 50

        reasoning = f"Category Gini: {1 - fairness / 100:.2f}, {cat_count} categories"
        evidence = f"Tasks distributed across {cat_count} categories"

        return fairness, reasoning, evidence

    def _score_accurate(self, metrics: dict) -> tuple[float, str, str]:
        """
        ACCURATE: Agent's task descriptions match actual work needed.
        Proxy: low failure/expiration rate (good tasks get completed).
        """
        completed = metrics.get("tasks_completed", 0)
        failed = metrics.get("tasks_failed", 0)
        expired = metrics.get("tasks_expired", 0)
        total = completed + failed + expired

        if total == 0:
            return 50, "No task data", "No tasks tracked"

        completion_rate = completed / total
        score = completion_rate * 90 + min(total / 50, 1.0) * 10

        reasoning = f"Completion rate {completion_rate:.0%}, volume {total}"
        evidence = f"{completed}/{total} tasks successfully completed"

        return score, reasoning, evidence

    def _score_responsive_h2a(self, metrics: dict) -> tuple[float, str, str]:
        """
        RESPONSIVE (H2A): Agent responds to worker questions quickly.
        Proxy: duration metrics (faster = more responsive coordination).
        """
        avg_duration = metrics.get("avg_duration_seconds", 0)
        completed = metrics.get("tasks_completed", 0)

        if completed == 0:
            return 50, "No completion data", "No tasks completed"

        avg_hours = avg_duration / 3600 if avg_duration > 0 else 12

        # Agents that coordinate fast tasks = responsive
        if avg_hours <= 4:
            score = 90
        elif avg_hours <= 24:
            score = 90 - (avg_hours - 4) / 20 * 30
        else:
            score = max(20, 60 - (avg_hours - 24) / 48 * 40)

        reasoning = f"Avg task duration {avg_hours:.1f}h"
        evidence = f"Average coordination cycle: {avg_hours:.1f} hours"

        return score, reasoning, evidence

    def _score_ethical(self, metrics: dict) -> tuple[float, str, str]:
        """
        ETHICAL: Agent operates transparently and fairly.
        Proxy: task completion + no suspicious patterns.
        """
        completed = metrics.get("tasks_completed", 0)
        failed = metrics.get("tasks_failed", 0)
        expired = metrics.get("tasks_expired", 0)
        total = completed + failed + expired

        if total == 0:
            return 50, "No data", "No tasks to evaluate"

        # High completion = ethical (pays workers, doesn't cancel)
        completion_rate = completed / total
        score = completion_rate * 70

        # No expirations = bonus (doesn't leave workers hanging)
        if expired == 0 and total > 5:
            score += 20
        elif expired / total < 0.1:
            score += 10

        # Volume trust
        score += min(total / 100, 1.0) * 10

        reasoning = f"Completion {completion_rate:.0%}, expirations {expired}/{total}"
        evidence = f"{completed} completed, {expired} expired out of {total} total"

        return score, reasoning, evidence

    # ──────────────────────────────────────────────────────────
    # Confidence & Batching
    # ──────────────────────────────────────────────────────────

    def _compute_confidence(self, total_tasks: int) -> float:
        """
        Confidence grows with task count.
        3 tasks = 0.3, 10 tasks = 0.7, 50+ tasks = 1.0
        """
        if total_tasks < self.MIN_TASKS_FOR_EVALUATION:
            return 0.0
        if total_tasks >= self.CONFIDENCE_FULL_AT:
            return 1.0

        # Smooth growth from min to full
        progress = (total_tasks - self.MIN_TASKS_FOR_EVALUATION) / (
            self.CONFIDENCE_FULL_AT - self.MIN_TASKS_FOR_EVALUATION
        )
        return 0.3 + progress * 0.7

    def prepare_batch(
        self,
        recommendations: list[SealRecommendation],
        min_confidence: float | None = None,
    ) -> BatchSealRequest:
        """
        Prepare a batch of seal recommendations for on-chain submission.
        Filters by confidence threshold and estimates gas.
        """
        threshold = (
            min_confidence if min_confidence is not None else self._min_confidence
        )
        eligible = [r for r in recommendations if r.confidence >= threshold]

        # Sort by score descending (issue best seals first)
        eligible.sort(key=lambda r: r.score, reverse=True)

        # SealRegistry batch limit is 50
        eligible = eligible[:50]

        return BatchSealRequest(
            seals=eligible,
            total_gas_estimate=len(eligible) * self._gas_per_seal,
        )

    def record_issuance(self, record: SealIssuanceRecord) -> None:
        """Record an on-chain seal issuance for tracking."""
        self._issuance_history.append(record)
        if len(self._issuance_history) > self._max_issuance_history:
            self._issuance_history = self._issuance_history[
                -self._max_issuance_history :
            ]

    @property
    def issuance_count(self) -> int:
        return len(self._issuance_history)

    def get_issuance_history(self, limit: int = 100) -> list[dict]:
        """Get recent issuance history."""
        return [r.to_dict() for r in self._issuance_history[-limit:]]

    # ──────────────────────────────────────────────────────────
    # Fleet Evaluation
    # ──────────────────────────────────────────────────────────

    def evaluate_fleet(
        self,
        agent_metrics: dict[str, dict],
        address_map: dict[str, str] | None = None,
    ) -> list[SealProfile]:
        """
        Evaluate all agents in the fleet and generate seal profiles.

        Args:
            agent_metrics: Dict of agent_id → metrics dict
            address_map: Optional dict of agent_id → wallet address

        Returns:
            List of SealProfile objects, sorted by overall_score
        """
        address_map = address_map or {}
        profiles = []

        for agent_id, metrics in agent_metrics.items():
            address = address_map.get(agent_id, f"0x{agent_id}")
            profile = self.evaluate_worker(
                worker_address=address,
                agent_id=agent_id,
                metrics=metrics,
            )
            if profile.recommendations:
                profiles.append(profile)

        profiles.sort(key=lambda p: p.overall_score, reverse=True)
        return profiles

    def fleet_summary(
        self,
        profiles: list[SealProfile],
    ) -> dict:
        """
        Summarize fleet-wide seal evaluation results.
        """
        if not profiles:
            return {"agents_evaluated": 0, "total_seals": 0}

        total_seals = sum(len(p.recommendations) for p in profiles)
        issuable_seals = sum(len(p.issuable_seals) for p in profiles)
        avg_score = sum(p.overall_score for p in profiles) / len(profiles)

        # Seal type distribution
        type_counts: dict[str, int] = {}
        type_avg_scores: dict[str, list] = {}
        for p in profiles:
            for r in p.recommendations:
                type_counts[r.seal_type] = type_counts.get(r.seal_type, 0) + 1
                if r.seal_type not in type_avg_scores:
                    type_avg_scores[r.seal_type] = []
                type_avg_scores[r.seal_type].append(r.score)

        seal_breakdown = {}
        for st, scores in type_avg_scores.items():
            seal_breakdown[st] = {
                "count": type_counts[st],
                "avg_score": round(sum(scores) / len(scores), 1),
                "min": min(scores),
                "max": max(scores),
            }

        return {
            "agents_evaluated": len(profiles),
            "total_seals": total_seals,
            "issuable_seals": issuable_seals,
            "avg_overall_score": round(avg_score, 1),
            "seal_breakdown": seal_breakdown,
            "top_performers": [
                {"agent_id": p.agent_id, "score": round(p.overall_score, 1)}
                for p in profiles[:5]
            ],
        }
