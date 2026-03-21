"""
DecisionSynthesizer — Unified Multi-Signal Routing Decisions
=============================================================

The swarm has many intelligence signals scattered across modules:
- ReputationBridge: on-chain + internal reputation scores
- AvailabilityBridge: timezone-aware worker availability predictions
- SourceHealthAdapter: job source quality tiers
- RoutingOptimizer: evolutionary weight tuning
- CapacityPlanner: workload gap analysis
- WorkforceAnalytics: health scores and MVP detection
- AutoJobClient: SkillGraph-enriched matching

The DecisionSynthesizer is the **unified decision engine** that pulls
all these signals together into a single, explainable routing decision.

Key properties:
1. **Signal aggregation**: Normalizes 0-100 scores from all sources
2. **Confidence-weighted blending**: Signals with more data get more weight
3. **Explainable decisions**: Every routing decision comes with a rationale
4. **Degradation-tolerant**: Works with any subset of signals (graceful when modules down)
5. **Decision audit trail**: Logs every decision for replay and analysis

Architecture:
    Signals (reputation, availability, skill_match, source_quality, capacity)
        ↓
    DecisionSynthesizer.synthesize(task, candidates)
        ↓
    SignalVector per candidate (normalized, weighted)
        ↓
    RankedDecision with explanation + confidence

Usage:
    synthesizer = DecisionSynthesizer()
    synthesizer.register_signal("reputation", reputation_bridge.score)
    synthesizer.register_signal("availability", availability_bridge.predict)
    
    decision = synthesizer.synthesize(
        task={"id": "t1", "category": "physical_verification"},
        candidates=[agent_1, agent_2, agent_3],
    )
    print(decision.best_candidate)
    print(decision.explanation)
"""

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Any

logger = logging.getLogger("em.swarm.decision_synthesizer")


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


class SignalType(str, Enum):
    """Categories of decision signals."""
    REPUTATION = "reputation"         # On-chain + internal reputation
    SKILL_MATCH = "skill_match"       # How well skills match task
    AVAILABILITY = "availability"     # Worker likely online/responsive
    CAPACITY = "capacity"             # Worker not overloaded
    SOURCE_QUALITY = "source_quality" # Quality tier of task source
    SPEED = "speed"                   # Historical response time
    COST = "cost"                     # Budget efficiency
    RECENCY = "recency"              # How recently worker was active
    RELIABILITY = "reliability"       # Completion rate / on-time rate
    SPECIALIZATION = "specialization" # Category-specific expertise


class DecisionOutcome(str, Enum):
    """Possible decision outcomes."""
    ROUTED = "routed"           # Successfully assigned to best candidate
    HELD = "held"               # No suitable candidate, hold for later
    ESCALATED = "escalated"     # Needs human intervention
    SPLIT = "split"             # Task should be decomposed
    REJECTED = "rejected"       # Task doesn't meet minimum thresholds


class ConfidenceLevel(str, Enum):
    """Confidence in the routing decision."""
    HIGH = "high"       # 0.8+ — strong signal consensus
    MEDIUM = "medium"   # 0.5-0.8 — reasonable but some uncertainty
    LOW = "low"         # 0.3-0.5 — limited data, best guess
    GUESS = "guess"     # < 0.3 — very few signals, essentially random


@dataclass
class SignalValue:
    """A single signal measurement for a candidate."""
    signal_type: SignalType
    raw_value: float          # Original value from the source module
    normalized: float = 0.0  # 0.0-1.0 normalized
    weight: float = 1.0      # Importance weight for this signal
    confidence: float = 1.0  # How reliable is this particular measurement
    source: str = ""          # Which module produced this
    detail: str = ""          # Human-readable explanation

    @property
    def weighted_score(self) -> float:
        """Score contribution = normalized * weight * confidence."""
        return self.normalized * self.weight * self.confidence


@dataclass
class SignalVector:
    """Complete set of signals for one candidate."""
    candidate_id: str  # Agent/worker ID
    wallet: str = ""
    signals: list[SignalValue] = field(default_factory=list)
    composite_score: float = 0.0
    rank: int = 0

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def total_confidence(self) -> float:
        """Average confidence across all signals."""
        if not self.signals:
            return 0.0
        return sum(s.confidence for s in self.signals) / len(self.signals)

    def signal_by_type(self, stype: SignalType) -> Optional[SignalValue]:
        """Get a specific signal value."""
        for s in self.signals:
            if s.signal_type == stype:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "wallet": self.wallet,
            "composite_score": round(self.composite_score, 4),
            "rank": self.rank,
            "signal_count": self.signal_count,
            "total_confidence": round(self.total_confidence, 3),
            "signals": {
                s.signal_type.value: {
                    "raw": round(s.raw_value, 3),
                    "normalized": round(s.normalized, 3),
                    "weight": round(s.weight, 3),
                    "confidence": round(s.confidence, 3),
                    "weighted_score": round(s.weighted_score, 4),
                    "detail": s.detail,
                }
                for s in self.signals
            },
        }


@dataclass
class RankedDecision:
    """The synthesized routing decision."""
    task_id: str
    outcome: DecisionOutcome
    best_candidate: Optional[str] = None
    best_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_score: float = 0.0
    rankings: list[SignalVector] = field(default_factory=list)
    explanation: str = ""
    decision_time_ms: float = 0.0
    timestamp: str = ""
    signal_types_used: list[str] = field(default_factory=list)
    warning: str = ""

    @property
    def top_n(self) -> list[str]:
        """Top 3 candidate IDs."""
        return [r.candidate_id for r in self.rankings[:3]]

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "outcome": self.outcome.value,
            "best_candidate": self.best_candidate,
            "best_score": round(self.best_score, 4),
            "confidence": {
                "level": self.confidence_level.value,
                "score": round(self.confidence_score, 3),
            },
            "top_candidates": [
                r.to_dict() for r in self.rankings[:5]
            ],
            "explanation": self.explanation,
            "decision_time_ms": round(self.decision_time_ms, 2),
            "signal_types_used": self.signal_types_used,
            "timestamp": self.timestamp,
        }


@dataclass
class SignalProvider:
    """Registered signal source."""
    signal_type: SignalType
    scorer: Callable  # (task, candidate) -> float (0-100)
    weight: float = 1.0
    normalizer: Optional[Callable] = None  # Custom normalization
    default_confidence: float = 0.8
    enabled: bool = True
    description: str = ""


# ──────────────────────────────────────────────────────────────
# Default Signal Weights
# ──────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    SignalType.SKILL_MATCH: 0.30,       # Most important: can they do it?
    SignalType.REPUTATION: 0.20,         # Have they done well before?
    SignalType.RELIABILITY: 0.15,        # Do they finish on time?
    SignalType.AVAILABILITY: 0.10,       # Are they online now?
    SignalType.SPEED: 0.08,              # How fast do they respond?
    SignalType.SPECIALIZATION: 0.07,     # Category expertise
    SignalType.RECENCY: 0.05,            # Recent activity
    SignalType.CAPACITY: 0.03,           # Not overloaded
    SignalType.COST: 0.02,               # Budget efficiency
    SignalType.SOURCE_QUALITY: 0.00,     # Task source (not about candidate)
}

# Minimum composite score to route (below this = HELD)
MINIMUM_ROUTE_THRESHOLD = 0.15

# Minimum signals required for HIGH confidence
HIGH_CONFIDENCE_SIGNALS = 5

# Score gap between #1 and #2 for a "clear winner"
CLEAR_WINNER_GAP = 0.15


# ──────────────────────────────────────────────────────────────
# Decision Synthesizer
# ──────────────────────────────────────────────────────────────


class DecisionSynthesizer:
    """
    Unified multi-signal routing decision engine.
    
    Aggregates signals from all swarm intelligence modules into
    a single scored, ranked, and explained routing decision.
    """

    def __init__(
        self,
        weights: Optional[dict[SignalType, float]] = None,
        min_threshold: float = MINIMUM_ROUTE_THRESHOLD,
    ):
        self._providers: dict[SignalType, SignalProvider] = {}
        self._weights = weights or dict(DEFAULT_WEIGHTS)
        self._min_threshold = min_threshold
        self._decision_log: list[dict] = []
        self._max_log_size = 1000

    # ── Registration ─────────────────────────────────────────

    def register_signal(
        self,
        signal_type: SignalType,
        scorer: Callable,
        weight: Optional[float] = None,
        confidence: float = 0.8,
        description: str = "",
    ):
        """
        Register a signal provider.

        Args:
            signal_type: What kind of signal this provides.
            scorer: Function(task: dict, candidate: dict) -> float (0-100).
            weight: Override the default weight for this signal type.
            confidence: Default confidence level for measurements.
            description: Human-readable description.
        """
        w = weight if weight is not None else self._weights.get(
            signal_type, 0.1
        )
        self._providers[signal_type] = SignalProvider(
            signal_type=signal_type,
            scorer=scorer,
            weight=w,
            default_confidence=confidence,
            description=description,
        )
        logger.info(
            "Registered signal: %s (weight=%.2f, confidence=%.2f)",
            signal_type.value, w, confidence,
        )

    def unregister_signal(self, signal_type: SignalType):
        """Remove a signal provider."""
        self._providers.pop(signal_type, None)

    @property
    def registered_signals(self) -> list[str]:
        """List of registered signal type names."""
        return [s.value for s in self._providers]

    # ── Core Synthesis ───────────────────────────────────────

    def synthesize(
        self,
        task: dict,
        candidates: list[dict],
        override_weights: Optional[dict[SignalType, float]] = None,
    ) -> RankedDecision:
        """
        Synthesize a routing decision from all available signals.

        Args:
            task: EM task dict (id, category, title, bounty_usd, etc.)
            candidates: List of candidate dicts (id, wallet, skills, etc.)
            override_weights: Optional per-decision weight overrides.

        Returns:
            RankedDecision with scored, ranked candidates and explanation.
        """
        start = time.monotonic()
        task_id = task.get("id", task.get("task_id", "unknown"))
        weights = override_weights or self._weights

        if not candidates:
            return RankedDecision(
                task_id=task_id,
                outcome=DecisionOutcome.HELD,
                explanation="No candidates provided.",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Collect signals for each candidate
        vectors = []
        signals_used = set()

        for candidate in candidates:
            cid = str(
                candidate.get("id", candidate.get("agent_id", ""))
            )
            wallet = candidate.get("wallet", "")
            signals = []

            for stype, provider in self._providers.items():
                if not provider.enabled:
                    continue

                try:
                    raw = provider.scorer(task, candidate)
                    if raw is None:
                        continue

                    # Normalize to 0.0-1.0
                    if provider.normalizer:
                        normalized = provider.normalizer(raw)
                    else:
                        normalized = self._default_normalize(raw)

                    w = weights.get(stype, provider.weight)

                    signals.append(SignalValue(
                        signal_type=stype,
                        raw_value=float(raw),
                        normalized=normalized,
                        weight=w,
                        confidence=provider.default_confidence,
                        source=provider.description or stype.value,
                    ))
                    signals_used.add(stype.value)

                except Exception as e:
                    logger.warning(
                        "Signal %s failed for candidate %s: %s",
                        stype.value, cid, e,
                    )
                    # Degradation-tolerant: skip this signal, continue

            # Compute composite score
            composite = self._compute_composite(signals)

            vectors.append(SignalVector(
                candidate_id=cid,
                wallet=wallet,
                signals=signals,
                composite_score=composite,
            ))

        # Rank by composite score (highest first)
        vectors.sort(key=lambda v: v.composite_score, reverse=True)
        for i, v in enumerate(vectors):
            v.rank = i + 1

        # Determine outcome
        outcome, confidence_level, confidence_score = self._determine_outcome(
            vectors, signals_used
        )

        # Build explanation
        explanation = self._build_explanation(
            task, vectors, outcome, signals_used
        )

        elapsed = (time.monotonic() - start) * 1000

        decision = RankedDecision(
            task_id=task_id,
            outcome=outcome,
            best_candidate=vectors[0].candidate_id if vectors else None,
            best_score=vectors[0].composite_score if vectors else 0.0,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            rankings=vectors,
            explanation=explanation,
            decision_time_ms=elapsed,
            timestamp=datetime.now(timezone.utc).isoformat(),
            signal_types_used=sorted(signals_used),
        )

        # Audit log
        self._log_decision(decision)

        return decision

    def synthesize_quick(
        self,
        task: dict,
        candidates: list[dict],
    ) -> Optional[str]:
        """
        Quick synthesis: returns best candidate ID or None.
        
        Lightweight wrapper for simple routing decisions.
        """
        decision = self.synthesize(task, candidates)
        if decision.outcome == DecisionOutcome.ROUTED:
            return decision.best_candidate
        return None

    # ── Composite Scoring ────────────────────────────────────

    def _compute_composite(self, signals: list[SignalValue]) -> float:
        """
        Compute composite score from weighted signals.

        Uses confidence-weighted average: signals with higher confidence
        contribute more to the final score.
        """
        if not signals:
            return 0.0

        total_weighted = 0.0
        total_weight = 0.0

        for s in signals:
            effective_weight = s.weight * s.confidence
            total_weighted += s.normalized * effective_weight
            total_weight += effective_weight

        if total_weight == 0:
            return 0.0

        return total_weighted / total_weight

    @staticmethod
    def _default_normalize(value: float) -> float:
        """Normalize a 0-100 score to 0.0-1.0."""
        if value <= 0:
            return 0.0
        if value >= 100:
            return 1.0
        return value / 100.0

    # ── Outcome Determination ────────────────────────────────

    def _determine_outcome(
        self,
        vectors: list[SignalVector],
        signals_used: set,
    ) -> tuple[DecisionOutcome, ConfidenceLevel, float]:
        """Determine routing outcome and confidence."""
        if not vectors:
            return DecisionOutcome.HELD, ConfidenceLevel.GUESS, 0.0

        best = vectors[0]
        best_score = best.composite_score

        # Confidence based on number and quality of signals
        signal_count = len(signals_used)
        avg_confidence = best.total_confidence

        if signal_count >= HIGH_CONFIDENCE_SIGNALS and avg_confidence >= 0.7:
            confidence_level = ConfidenceLevel.HIGH
        elif signal_count >= 3 and avg_confidence >= 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        elif signal_count >= 1:
            confidence_level = ConfidenceLevel.LOW
        else:
            confidence_level = ConfidenceLevel.GUESS

        confidence_score = min(1.0, (
            (signal_count / HIGH_CONFIDENCE_SIGNALS) * 0.5
            + avg_confidence * 0.5
        ))

        # Determine outcome
        if best_score < self._min_threshold:
            return DecisionOutcome.HELD, confidence_level, confidence_score

        if signal_count == 0:
            return DecisionOutcome.HELD, ConfidenceLevel.GUESS, 0.0

        return DecisionOutcome.ROUTED, confidence_level, confidence_score

    # ── Explanation Builder ──────────────────────────────────

    def _build_explanation(
        self,
        task: dict,
        vectors: list[SignalVector],
        outcome: DecisionOutcome,
        signals_used: set,
    ) -> str:
        """Build human-readable explanation of the decision."""
        parts = []

        task_title = task.get("title", "Unknown task")[:60]
        parts.append(
            f"Task '{task_title}' evaluated against "
            f"{len(vectors)} candidate(s) using {len(signals_used)} signal(s)."
        )

        if outcome == DecisionOutcome.HELD:
            parts.append("No candidate met the minimum threshold. Task held.")
            return " ".join(parts)

        if outcome == DecisionOutcome.ROUTED and vectors:
            best = vectors[0]
            parts.append(
                f"Best: #{best.candidate_id} "
                f"(score={best.composite_score:.3f})."
            )

            # Explain top signals
            top_signals = sorted(
                best.signals, key=lambda s: s.weighted_score, reverse=True
            )[:3]
            signal_parts = []
            for s in top_signals:
                signal_parts.append(
                    f"{s.signal_type.value}={s.normalized:.2f}"
                )
            if signal_parts:
                parts.append(
                    f"Top signals: {', '.join(signal_parts)}."
                )

            # Gap analysis
            if len(vectors) >= 2:
                gap = best.composite_score - vectors[1].composite_score
                if gap > CLEAR_WINNER_GAP:
                    parts.append(
                        f"Clear winner (gap={gap:.3f} over #2)."
                    )
                elif gap < 0.02:
                    parts.append(
                        f"Very close race (gap={gap:.3f}). "
                        f"Consider both candidates."
                    )

        return " ".join(parts)

    # ── Audit Trail ──────────────────────────────────────────

    def _log_decision(self, decision: RankedDecision):
        """Add decision to audit log (circular buffer)."""
        entry = {
            "task_id": decision.task_id,
            "outcome": decision.outcome.value,
            "best": decision.best_candidate,
            "score": round(decision.best_score, 4),
            "confidence": decision.confidence_level.value,
            "signals": len(decision.signal_types_used),
            "candidates": len(decision.rankings),
            "time_ms": round(decision.decision_time_ms, 2),
            "ts": decision.timestamp,
        }
        self._decision_log.append(entry)
        if len(self._decision_log) > self._max_log_size:
            self._decision_log = self._decision_log[-self._max_log_size:]

    @property
    def decision_history(self) -> list[dict]:
        """Get decision audit trail."""
        return list(self._decision_log)

    @property
    def stats(self) -> dict:
        """Aggregated decision statistics."""
        if not self._decision_log:
            return {
                "total_decisions": 0,
                "providers_registered": len(self._providers),
            }

        outcomes = defaultdict(int)
        confidence_dist = defaultdict(int)
        total_time = 0.0
        total_signals = 0

        for entry in self._decision_log:
            outcomes[entry["outcome"]] += 1
            confidence_dist[entry["confidence"]] += 1
            total_time += entry["time_ms"]
            total_signals += entry["signals"]

        n = len(self._decision_log)
        return {
            "total_decisions": n,
            "providers_registered": len(self._providers),
            "outcomes": dict(outcomes),
            "confidence_distribution": dict(confidence_dist),
            "avg_decision_time_ms": round(total_time / n, 2),
            "avg_signals_per_decision": round(total_signals / n, 1),
            "route_rate": round(
                outcomes.get("routed", 0) / n, 3
            ) if n > 0 else 0,
        }

    # ── Weight Management ────────────────────────────────────

    def update_weights(self, new_weights: dict[SignalType, float]):
        """Update signal weights (e.g., from RoutingOptimizer)."""
        for stype, weight in new_weights.items():
            if isinstance(stype, str):
                stype = SignalType(stype)
            self._weights[stype] = weight
            if stype in self._providers:
                self._providers[stype].weight = weight
        logger.info("Updated weights: %s", {
            k.value: round(v, 3) for k, v in self._weights.items()
        })

    def get_weights(self) -> dict[str, float]:
        """Get current signal weights."""
        return {k.value: round(v, 3) for k, v in self._weights.items()}

    # ── Comparison / What-If ─────────────────────────────────

    def compare_candidates(
        self,
        task: dict,
        candidate_a: dict,
        candidate_b: dict,
    ) -> dict:
        """
        Head-to-head comparison of two candidates for a task.

        Returns a detailed breakdown showing where each candidate
        wins or loses, useful for understanding routing decisions.
        """
        decision = self.synthesize(task, [candidate_a, candidate_b])
        if len(decision.rankings) < 2:
            return {"error": "Need at least 2 candidates"}

        a = decision.rankings[0]
        b = decision.rankings[1]

        comparison = {
            "winner": a.candidate_id,
            "loser": b.candidate_id,
            "score_gap": round(a.composite_score - b.composite_score, 4),
            "signal_comparison": {},
        }

        all_types = set()
        for s in a.signals:
            all_types.add(s.signal_type)
        for s in b.signals:
            all_types.add(s.signal_type)

        for stype in sorted(all_types, key=lambda t: t.value):
            a_sig = a.signal_by_type(stype)
            b_sig = b.signal_by_type(stype)
            a_val = a_sig.normalized if a_sig else 0.0
            b_val = b_sig.normalized if b_sig else 0.0
            comparison["signal_comparison"][stype.value] = {
                "a": round(a_val, 3),
                "b": round(b_val, 3),
                "advantage": (
                    a.candidate_id if a_val > b_val
                    else b.candidate_id if b_val > a_val
                    else "tie"
                ),
            }

        return comparison

    def what_if(
        self,
        task: dict,
        candidates: list[dict],
        modified_weights: dict[SignalType, float],
    ) -> dict:
        """
        What-if analysis: how would the decision change with different weights?

        Useful for the RoutingOptimizer to test weight configurations
        before applying them.
        """
        # Run with current weights
        current = self.synthesize(task, candidates)

        # Run with modified weights
        modified = self.synthesize(
            task, candidates, override_weights=modified_weights
        )

        return {
            "current_best": current.best_candidate,
            "current_score": round(current.best_score, 4),
            "modified_best": modified.best_candidate,
            "modified_score": round(modified.best_score, 4),
            "ranking_changed": current.best_candidate != modified.best_candidate,
            "current_top3": current.top_n,
            "modified_top3": modified.top_n,
        }
