"""
VerificationAdapter — PHOTINT Evidence Quality as a Swarm Signal
=================================================================

Bridges PHOTINT forensic verification data into the swarm's routing
decision engine. When the DecisionSynthesizer asks "how good is this
worker?", the VerificationAdapter answers with evidence quality metrics.

Signal Type: "verification_quality" (Signal #13 in the intelligence stack)

Key Insight: Evidence quality is a leading indicator of worker reliability.
Workers who consistently submit clear, EXIF-rich, GPS-matching photos
are statistically more likely to complete tasks successfully AND their
evidence is cheaper to verify (Tier 1 vs Tier 2/3).

Integration Points:
    - DecisionSynthesizer: register as signal provider
    - Coordinator: factor into routing decisions
    - BudgetController: verification cost savings inform budget
    - Dashboard: worker quality sparklines

Data Flow:
    PHOTINT verifies submission → inference log written
        → VerificationAdapter ingests inference
        → Worker profile updated (quality, tier, category competence)
        → DecisionSynthesizer queries verification_quality signal
        → Routing decision adjusts for evidence quality

Usage:
    adapter = VerificationAdapter()

    # Ingest from PHOTINT pipeline
    adapter.ingest_inference(worker_id, inference_data)

    # Score a worker for routing (0-100)
    score = adapter.score(worker_id, task)
    # -> 78.5 (good evidence history for this task category)

    # Register with DecisionSynthesizer
    synthesizer.register_signal("verification_quality", adapter.score)
"""

import logging
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("em.swarm.verification_adapter")

UTC = timezone.utc


# ──────────────────────────────────────────────────────────────
# Trust Tiers
# ──────────────────────────────────────────────────────────────

class VerificationTrust(str, Enum):
    """Worker trust level from verification history."""
    UNKNOWN = "unknown"          # No history
    LOW = "low"                  # High rejection / low quality
    STANDARD = "standard"        # Normal workflow
    HIGH = "high"                # Consistently clean
    EXCEPTIONAL = "exceptional"  # Perfect record


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────

@dataclass
class VerificationInference:
    """A single PHOTINT inference record."""
    submission_id: str = ""
    task_id: str = ""
    worker_id: str = ""
    tier: str = "tier_1"
    score: float = 0.0             # 0-1 from PHOTINT
    decision: str = "pending"      # approved, rejected, needs_human
    category: str = "general"
    bounty_usd: float = 0.0
    has_exif: bool = False
    has_gps: bool = False
    photo_source: str = "unknown"  # camera, screenshot, edited
    cost_usd: float = 0.0
    was_escalated: bool = False
    consensus_used: bool = False
    consensus_agreed: bool = False
    timestamp: float = 0.0        # Unix epoch


@dataclass
class WorkerVerificationState:
    """Aggregated verification metrics for a worker."""
    worker_id: str = ""
    total_inferences: int = 0
    avg_score: float = 0.0
    approval_rate: float = 0.0
    escalation_rate: float = 0.0
    exif_rate: float = 0.0
    camera_rate: float = 0.0
    avg_cost: float = 0.0
    trust: VerificationTrust = VerificationTrust.UNKNOWN
    category_scores: Dict[str, float] = field(default_factory=dict)
    trend: str = "stable"  # improving, stable, declining
    last_updated: float = 0.0


# ──────────────────────────────────────────────────────────────
# Scoring Constants
# ──────────────────────────────────────────────────────────────

# How we translate verification metrics to 0-100 score
QUALITY_WEIGHT = 0.40       # Raw PHOTINT score → 40%
APPROVAL_WEIGHT = 0.25      # Approval rate → 25%
EXIF_WEIGHT = 0.15          # EXIF compliance → 15%
ESCALATION_WEIGHT = 0.10    # Inverse escalation rate → 10%
TREND_WEIGHT = 0.10         # Trend bonus/penalty → 10%

# Trust tier thresholds
TRUST_THRESHOLDS = {
    "exceptional": {"min_inferences": 20, "min_score": 0.95, "max_escalation": 0.05},
    "high": {"min_inferences": 10, "min_score": 0.80, "max_escalation": 0.20},
    "standard": {"min_inferences": 3, "min_score": 0.50, "max_escalation": 0.50},
    "low": {"min_inferences": 3, "min_score": 0.0, "max_escalation": 1.0},
}

# Category importance for physical tasks
PHYSICAL_CATEGORIES = {
    "physical_verification", "physical_presence",
    "location_based", "emergency", "human_authority",
}


# ──────────────────────────────────────────────────────────────
# VerificationAdapter
# ──────────────────────────────────────────────────────────────

class VerificationAdapter:
    """
    Swarm signal adapter for PHOTINT verification quality.

    Maintains per-worker verification states and provides a 0-100
    score compatible with DecisionSynthesizer's signal interface.
    """

    def __init__(
        self,
        min_inferences_for_signal: int = 3,
        default_score: float = 50.0,
        trend_window: int = 10,
    ):
        """
        Args:
            min_inferences_for_signal: Minimum inferences before generating a signal.
            default_score: Score for workers with no verification history.
            trend_window: Number of recent records for trend detection.
        """
        self.min_inferences = min_inferences_for_signal
        self.default_score = default_score
        self.trend_window = trend_window

        # Storage: worker_id -> list of VerificationInference
        self._inferences: Dict[str, List[VerificationInference]] = defaultdict(list)
        # Cache: worker_id -> WorkerVerificationState
        self._states: Dict[str, WorkerVerificationState] = {}

    # -------------------------------------------------------------------
    # Ingestion
    # -------------------------------------------------------------------

    def ingest_inference(
        self,
        worker_id: str,
        inference: dict,
    ) -> bool:
        """
        Ingest a PHOTINT inference result.

        Args:
            worker_id: Worker identifier (wallet address or agent ID).
            inference: Dict with PHOTINT inference data.

        Returns:
            True if successfully ingested.
        """
        if not worker_id:
            return False

        wid = worker_id.lower()
        rec = VerificationInference(
            submission_id=inference.get("submission_id", ""),
            task_id=inference.get("task_id", ""),
            worker_id=wid,
            tier=inference.get("tier", inference.get("tier_used", "tier_1")),
            score=float(inference.get("score", 0.0)),
            decision=inference.get("decision", "pending"),
            category=inference.get("category", "general"),
            bounty_usd=float(inference.get("bounty_usd", 0.0)),
            has_exif=bool(inference.get("has_exif", False)),
            has_gps=bool(inference.get("has_gps", False)),
            photo_source=inference.get("photo_source", "unknown"),
            cost_usd=float(inference.get("cost_usd", 0.0)),
            was_escalated=bool(inference.get("was_escalated", False)),
            consensus_used=bool(inference.get("consensus_used", False)),
            consensus_agreed=bool(inference.get("consensus_agreed", False)),
            timestamp=inference.get("timestamp", datetime.now(UTC).timestamp()),
        )

        self._inferences[wid].append(rec)
        # Invalidate cache
        self._states.pop(wid, None)
        return True

    def ingest_batch(
        self,
        inferences: List[dict],
    ) -> int:
        """Ingest multiple inferences. Returns count ingested."""
        count = 0
        for inf in inferences:
            wid = inf.get("worker_id", inf.get("worker_wallet", ""))
            if self.ingest_inference(wid, inf):
                count += 1
        return count

    # -------------------------------------------------------------------
    # State Computation
    # -------------------------------------------------------------------

    def get_state(self, worker_id: str) -> WorkerVerificationState:
        """Get or compute worker verification state."""
        wid = worker_id.lower()
        if wid in self._states:
            return self._states[wid]

        records = self._inferences.get(wid, [])
        state = self._compute_state(wid, records)
        self._states[wid] = state
        return state

    def _compute_state(
        self,
        worker_id: str,
        records: List[VerificationInference],
    ) -> WorkerVerificationState:
        """Build WorkerVerificationState from inference records."""
        state = WorkerVerificationState(
            worker_id=worker_id,
            total_inferences=len(records),
            last_updated=datetime.now(UTC).timestamp(),
        )

        if not records:
            return state

        n = len(records)

        # Core metrics
        scores = [r.score for r in records if r.score > 0]
        state.avg_score = statistics.mean(scores) if scores else 0.0
        state.approval_rate = sum(1 for r in records if r.decision == "approved") / n
        state.escalation_rate = sum(1 for r in records if r.was_escalated) / n
        state.exif_rate = sum(1 for r in records if r.has_exif) / n
        state.camera_rate = sum(1 for r in records if r.photo_source == "camera") / n
        state.avg_cost = sum(r.cost_usd for r in records) / n

        # Per-category scores
        by_cat: Dict[str, List[float]] = defaultdict(list)
        for r in records:
            if r.score > 0:
                by_cat[r.category].append(r.score)
        state.category_scores = {
            cat: round(statistics.mean(sc), 3)
            for cat, sc in by_cat.items()
            if sc
        }

        # Trust tier
        state.trust = self._classify_trust(state)

        # Trend
        state.trend = self._detect_trend(records)

        return state

    def _classify_trust(self, state: WorkerVerificationState) -> VerificationTrust:
        """Classify trust tier from metrics."""
        n = state.total_inferences

        for tier_name in ["exceptional", "high", "standard", "low"]:
            thresholds = TRUST_THRESHOLDS[tier_name]
            if (
                n >= thresholds["min_inferences"]
                and state.avg_score >= thresholds["min_score"]
                and state.escalation_rate <= thresholds["max_escalation"]
            ):
                return VerificationTrust(tier_name)

        if n < 3:
            return VerificationTrust.UNKNOWN
        return VerificationTrust.LOW

    def _detect_trend(self, records: List[VerificationInference]) -> str:
        """Detect quality trend from recent records."""
        if len(records) < 6:
            return "stable"

        mid = len(records) // 2
        old_scores = [r.score for r in records[:mid] if r.score > 0]
        new_scores = [r.score for r in records[mid:] if r.score > 0]

        if not old_scores or not new_scores:
            return "stable"

        diff = statistics.mean(new_scores) - statistics.mean(old_scores)
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        return "stable"

    # -------------------------------------------------------------------
    # Scoring (DecisionSynthesizer Interface)
    # -------------------------------------------------------------------

    def score(
        self,
        worker_id: str,
        task: Optional[dict] = None,
    ) -> float:
        """
        Compute a 0-100 verification quality score for a worker.

        Compatible with DecisionSynthesizer's signal interface:
            synthesizer.register_signal("verification_quality", adapter.score)

        Args:
            worker_id: Worker identifier.
            task: Optional task context for category-specific scoring.

        Returns:
            Float 0-100. Default 50 for unknown workers.
        """
        state = self.get_state(worker_id)

        if state.total_inferences < self.min_inferences:
            return self.default_score

        # Component scores (0-1)
        quality_component = state.avg_score
        approval_component = state.approval_rate
        exif_component = state.exif_rate
        escalation_component = 1.0 - state.escalation_rate  # Lower escalation = better
        trend_component = self._trend_score(state.trend)

        # Category adjustment
        category = (task or {}).get("category", "general")
        if category in state.category_scores:
            # Use category-specific score instead of overall
            quality_component = state.category_scores[category]

        # Weighted combination
        raw = (
            quality_component * QUALITY_WEIGHT
            + approval_component * APPROVAL_WEIGHT
            + exif_component * EXIF_WEIGHT
            + escalation_component * ESCALATION_WEIGHT
            + trend_component * TREND_WEIGHT
        )

        # Scale to 0-100
        return round(min(100.0, max(0.0, raw * 100.0)), 1)

    def _trend_score(self, trend: str) -> float:
        """Convert trend to 0-1 score component."""
        if trend == "improving":
            return 0.8
        elif trend == "declining":
            return 0.2
        return 0.5  # stable

    # -------------------------------------------------------------------
    # Routing Recommendations
    # -------------------------------------------------------------------

    def recommend_tier(self, worker_id: str) -> str:
        """Recommend verification tier for this worker."""
        state = self.get_state(worker_id)

        if state.trust == VerificationTrust.EXCEPTIONAL:
            return "tier_1"
        elif state.trust == VerificationTrust.HIGH:
            return "tier_1"
        elif state.trust == VerificationTrust.STANDARD:
            return "tier_1"  # Standard can start with tier_1
        elif state.trust == VerificationTrust.LOW:
            return "tier_2"
        else:
            return "tier_2"  # Unknown defaults to more scrutiny

    def estimate_verification_cost(
        self,
        worker_id: str,
        photo_count: int = 1,
    ) -> float:
        """Estimate verification cost for this worker's next submission."""
        tier = self.recommend_tier(worker_id)
        tier_costs = {
            "tier_0": 0.0,
            "tier_1": 0.002,
            "tier_2": 0.01,
            "tier_3": 0.05,
            "tier_4": 0.15,
        }
        return tier_costs.get(tier, 0.002) * photo_count

    # -------------------------------------------------------------------
    # Fleet Analytics
    # -------------------------------------------------------------------

    def get_fleet_metrics(self) -> dict:
        """Get aggregated metrics across all workers."""
        if not self._inferences:
            return {
                "total_workers": 0,
                "total_inferences": 0,
                "trust_distribution": {},
            }

        all_states = [self.get_state(wid) for wid in self._inferences]
        trust_dist = Counter(s.trust.value for s in all_states)
        quality_scores = [s.avg_score for s in all_states if s.avg_score > 0]

        return {
            "total_workers": len(all_states),
            "total_inferences": sum(s.total_inferences for s in all_states),
            "trust_distribution": dict(trust_dist),
            "avg_quality": round(statistics.mean(quality_scores), 3) if quality_scores else 0.0,
            "avg_approval_rate": round(
                statistics.mean(s.approval_rate for s in all_states), 3
            ),
            "workers_improving": sum(1 for s in all_states if s.trend == "improving"),
            "workers_declining": sum(1 for s in all_states if s.trend == "declining"),
        }

    def get_category_performance(self) -> dict:
        """Get average verification quality per task category."""
        all_cat_scores: Dict[str, List[float]] = defaultdict(list)
        for wid in self._inferences:
            state = self.get_state(wid)
            for cat, score in state.category_scores.items():
                all_cat_scores[cat].append(score)

        return {
            cat: {
                "avg_score": round(statistics.mean(scores), 3),
                "worker_count": len(scores),
            }
            for cat, scores in all_cat_scores.items()
            if scores
        }

    # -------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------

    def diagnose(self) -> dict:
        """Full diagnostic snapshot for monitoring."""
        fleet = self.get_fleet_metrics()
        cat_perf = self.get_category_performance()

        # Cost analysis
        all_records = [r for recs in self._inferences.values() for r in recs]
        total_cost = sum(r.cost_usd for r in all_records)
        baseline_cost = len(all_records) * 0.01  # All at tier_2

        return {
            "fleet_metrics": fleet,
            "category_performance": cat_perf,
            "cost_analysis": {
                "actual_cost": round(total_cost, 4),
                "baseline_cost": round(baseline_cost, 4),
                "savings_pct": round(
                    (1 - total_cost / baseline_cost) * 100
                    if baseline_cost > 0
                    else 0.0,
                    1,
                ),
            },
            "adapter_config": {
                "min_inferences": self.min_inferences,
                "default_score": self.default_score,
                "trend_window": self.trend_window,
            },
        }
