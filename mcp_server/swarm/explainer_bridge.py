"""
ExplainerBridge — Server-Side Decision Transparency

Module #72 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's RoutingExplainer (Signal #25).
Decomposes routing decisions into human-readable explanations, providing
transparency into *why* the SwarmCoordinator chose Worker A over Worker B.

After 24 signals across 10 dimensions — capability, market fit, temporal,
self-optimization, discovery, social trust, motivation, spatial, quality,
communication, and efficiency — Signal #25 adds the meta-layer:
*decision explainability*.

The ExplainerBridge doesn't generate its own routing signal. Instead, it
observes ALL other bridge outputs and produces structured explanations:

    1. Per-decision decomposition — which signals contributed what bonus
    2. Comparative analysis — why winner beat runner-up
    3. Counterfactual analysis — "if Signal X were disabled, would result change?"
    4. Audit trail — aggregate signal impact over time
    5. Natural-language explanations — task-type aware (physical vs digital)

Key capabilities:
    1. record_decision() — Record a routing decision with signal contributions
    2. explain_decision() — Get structured explanation for a single decision
    3. compare_decisions() — Why Worker A was chosen over Worker B
    4. explain_ranking() — Full ranking decomposition for a task
    5. audit_summary() — Aggregate stats on which signals matter most
    6. save/load — JSON state persistence
    7. health() — Status endpoint

Architecture:
    - Mirrors AutoJob's RoutingExplainer API for consistency
    - Uses coordinator bridge outputs as signal contributions
    - Task-type aware explanations (physical tasks get location language,
      digital tasks get timezone language)
    - Zero overhead when no decisions are recorded
    - Thread-safe: decisions are independent, audit is append-only

Integration with SwarmCoordinator:
    coordinator.explainer_bridge.record_decision(...)
    explanation = coordinator.explainer_bridge.explain_decision(task_id, worker_id)

Author: Clawd (Dream Session, April 4 2026)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("swarm.explainer_bridge")

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Signal Labels
# ---------------------------------------------------------------------------

BRIDGE_LABELS = {
    "base_match": "Base Skill Match",
    "reputation": "On-Chain Reputation",
    "geo": "Geographic Proximity",
    "quality": "Evidence Quality",
    "affinity": "Task Affinity",
    "comm": "Communication Quality",
    "fpq": "First-Pass Quality",
    "lifecycle": "Lifecycle Stage",
    "availability": "Availability Window",
    "budget": "Budget Fit",
}

PHYSICAL_PHRASES = {
    "geo": "located near the task",
    "quality": "produces strong photographic evidence",
    "comm": "communicates clearly about field conditions",
    "fpq": "completes physical verifications on the first try",
    "affinity": "gravitates toward physical tasks",
    "reputation": "has strong on-chain reputation",
    "base_match": "skilled in the required domain",
    "lifecycle": "in their peak performance phase",
    "availability": "available during task window",
    "budget": "within the budget range",
}

DIGITAL_PHRASES = {
    "geo": "in a compatible timezone",
    "quality": "produces thorough digital documentation",
    "comm": "communicates technical details effectively",
    "fpq": "delivers clean digital work without revisions",
    "affinity": "drawn to digital task categories",
    "reputation": "has strong on-chain reputation",
    "base_match": "skilled in the required domain",
    "lifecycle": "experienced and currently active",
    "availability": "available for digital work",
    "budget": "pricing aligns with budget",
}

GENERAL_PHRASES = {
    "geo": "geographically well-positioned",
    "quality": "produces high-quality evidence",
    "comm": "communicates effectively",
    "fpq": "delivers on the first attempt",
    "affinity": "motivated by this type of work",
    "reputation": "trusted on-chain",
    "base_match": "skilled in the required area",
    "lifecycle": "at a productive stage",
    "availability": "currently available",
    "budget": "within budget",
}


def _get_phrases(task_type: str) -> dict:
    if task_type == "physical":
        return PHYSICAL_PHRASES
    elif task_type == "digital":
        return DIGITAL_PHRASES
    return GENERAL_PHRASES


def _infer_task_type(task: dict) -> str:
    cat = (task.get("category") or "").lower()
    ev_type = (task.get("evidence_type") or "").lower()
    title = (task.get("title") or "").lower()

    physical = {"physical_verification", "store_check", "photo", "photo_geo", "delivery", "field"}
    digital = {"digital_task", "text_response", "screenshot", "research", "survey", "document"}

    combined = f"{cat} {ev_type} {title}"
    if any(p in combined for p in physical):
        return "physical"
    if any(d in combined for d in digital):
        return "digital"
    return "general"


def _short_id(s: str) -> str:
    if s.startswith("0x") and len(s) > 10:
        return f"{s[:6]}...{s[-4:]}"
    return s[:16] + ("..." if len(s) > 16 else "")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SignalContribution:
    """A single bridge's contribution to a routing decision."""
    bridge_name: str
    bonus: float
    weight: float = 1.0
    confidence: float = 1.0
    detail: dict = field(default_factory=dict)

    @property
    def human_label(self) -> str:
        return BRIDGE_LABELS.get(self.bridge_name, self.bridge_name)

    def to_dict(self) -> dict:
        return {
            "bridge_name": self.bridge_name,
            "label": self.human_label,
            "bonus": round(self.bonus, 6),
            "weight": round(self.weight, 4),
            "confidence": round(self.confidence, 4),
            "detail": self.detail,
        }


@dataclass
class Decision:
    """Complete decomposition of one routing decision."""
    task_id: str
    worker_id: str
    final_score: float
    base_score: float = 0.0
    signals: list = field(default_factory=list)
    total_bonus: float = 0.0
    deciding_signals: list = field(default_factory=list)
    explanation: str = ""
    task_type: str = "general"
    timestamp: str = ""
    decision_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "final_score": round(self.final_score, 4),
            "base_score": round(self.base_score, 4),
            "total_bonus": round(self.total_bonus, 4),
            "deciding_signals": self.deciding_signals,
            "explanation": self.explanation,
            "task_type": self.task_type,
            "timestamp": self.timestamp,
            "decision_time_ms": round(self.decision_time_ms, 2),
            "signals": [s.to_dict() if hasattr(s, "to_dict") else s for s in self.signals],
        }

    @property
    def positive_signals(self):
        return [s for s in self.signals if s.bonus > 0.001]

    @property
    def negative_signals(self):
        return [s for s in self.signals if s.bonus < -0.001]


@dataclass
class Comparison:
    """Why Worker A was chosen over Worker B."""
    winner: Decision
    loser: Decision
    score_gap: float = 0.0
    signal_deltas: list = field(default_factory=list)
    decisive_advantages: list = field(default_factory=list)
    decisive_disadvantages: list = field(default_factory=list)
    summary: str = ""
    counterfactual: str = ""

    def to_dict(self) -> dict:
        return {
            "winner_id": self.winner.worker_id,
            "winner_score": round(self.winner.final_score, 4),
            "loser_id": self.loser.worker_id,
            "loser_score": round(self.loser.final_score, 4),
            "score_gap": round(self.score_gap, 4),
            "signal_deltas": self.signal_deltas,
            "decisive_advantages": self.decisive_advantages,
            "decisive_disadvantages": self.decisive_disadvantages,
            "summary": self.summary,
            "counterfactual": self.counterfactual,
        }


# ---------------------------------------------------------------------------
# ExplainerBridge
# ---------------------------------------------------------------------------

class ExplainerBridge:
    """Server-side decision transparency for the swarm coordinator.

    Usage:
        bridge = ExplainerBridge()

        # During routing:
        bridge.begin_decision("task_1", "0xAAA", base_score=0.65, task=task)
        bridge.record_signal("geo", 0.08, weight=0.12)
        bridge.record_signal("quality", 0.06, weight=0.10)
        decision = bridge.finalize_decision(final_score=0.79)

        # Analysis:
        comparison = bridge.compare(decision_a, decision_b)
        audit = bridge.audit_summary()
    """

    def __init__(
        self,
        *,
        max_decisions: int = 1000,
        top_n_deciding: int = 3,
        enable_counterfactual: bool = True,
    ):
        self._max_decisions = max_decisions
        self._top_n = top_n_deciding
        self._enable_counterfactual = enable_counterfactual
        self._decisions: list[Decision] = []
        self._signal_impact_sum: dict[str, float] = {}
        self._signal_deciding_count: dict[str, int] = {}
        self._total_decisions = 0

        # Live recording state
        self._current_task_id: Optional[str] = None
        self._current_worker_id: Optional[str] = None
        self._current_signals: list[SignalContribution] = []
        self._current_base_score: float = 0.0
        self._current_task_type: str = "general"
        self._current_start: float = 0.0

    # ----- Live Recording API -----

    def begin_decision(
        self,
        task_id: str,
        worker_id: str,
        base_score: float = 0.0,
        task: Optional[dict] = None,
    ) -> None:
        """Start recording a routing decision."""
        self._current_task_id = task_id
        self._current_worker_id = worker_id
        self._current_signals = []
        self._current_base_score = base_score
        self._current_task_type = _infer_task_type(task or {})
        self._current_start = time.monotonic()

    def record_signal(
        self,
        bridge_name: str,
        bonus: float,
        *,
        weight: float = 1.0,
        confidence: float = 1.0,
        detail: Optional[dict] = None,
    ) -> None:
        """Record a bridge's contribution to the current decision."""
        if self._current_task_id is None:
            logger.warning("record_signal called without begin_decision")
            return
        self._current_signals.append(SignalContribution(
            bridge_name=bridge_name,
            bonus=bonus,
            weight=weight,
            confidence=confidence,
            detail=detail or {},
        ))

    def finalize_decision(self, final_score: float) -> Decision:
        """Complete the current decision and generate explanation."""
        if self._current_task_id is None:
            raise ValueError("finalize_decision called without begin_decision")

        elapsed = (time.monotonic() - self._current_start) * 1000

        sorted_signals = sorted(
            self._current_signals,
            key=lambda s: abs(s.bonus),
            reverse=True,
        )

        deciding = [s.bridge_name for s in sorted_signals[:self._top_n] if abs(s.bonus) > 0.001]
        total_bonus = sum(s.bonus for s in self._current_signals)

        explanation = self._generate_explanation(
            self._current_worker_id,
            self._current_task_id,
            final_score,
            self._current_base_score,
            sorted_signals,
            deciding,
            self._current_task_type,
        )

        decision = Decision(
            task_id=self._current_task_id,
            worker_id=self._current_worker_id,
            final_score=final_score,
            base_score=self._current_base_score,
            signals=sorted_signals,
            total_bonus=total_bonus,
            deciding_signals=deciding,
            explanation=explanation,
            task_type=self._current_task_type,
            timestamp=datetime.now(UTC).isoformat(),
            decision_time_ms=elapsed,
        )

        self._store_decision(decision)
        self._reset_current()
        return decision

    # ----- Analysis API -----

    def compare(self, decision_a: Decision, decision_b: Decision) -> Comparison:
        """Compare two decisions — explain why A beats B (or auto-swap)."""
        if decision_b.final_score > decision_a.final_score:
            decision_a, decision_b = decision_b, decision_a

        score_gap = decision_a.final_score - decision_b.final_score
        b_lookup = {s.bridge_name: s for s in decision_b.signals}

        deltas = []
        advantages = []
        disadvantages = []

        for sig_a in decision_a.signals:
            sig_b = b_lookup.get(sig_a.bridge_name)
            b_bonus = sig_b.bonus if sig_b else 0.0
            delta = sig_a.bonus - b_bonus

            deltas.append({
                "signal": sig_a.bridge_name,
                "label": sig_a.human_label,
                "winner_bonus": round(sig_a.bonus, 4),
                "loser_bonus": round(b_bonus, 4),
                "delta": round(delta, 4),
            })
            if delta > 0.005:
                advantages.append(sig_a.bridge_name)
            elif delta < -0.005:
                disadvantages.append(sig_a.bridge_name)

        deltas.sort(key=lambda d: abs(d["delta"]), reverse=True)

        summary = self._comparison_summary(decision_a, decision_b, advantages, disadvantages)
        counterfactual = self._counterfactual(decision_a, decision_b, deltas) if self._enable_counterfactual else ""

        return Comparison(
            winner=decision_a,
            loser=decision_b,
            score_gap=score_gap,
            signal_deltas=deltas,
            decisive_advantages=advantages[:3],
            decisive_disadvantages=disadvantages[:3],
            summary=summary,
            counterfactual=counterfactual,
        )

    def explain_ranking(self, decisions: list[Decision], task_id: Optional[str] = None) -> dict:
        """Explain a full ranking (why #1 > #2 > #3...)."""
        if not decisions:
            return {"task_id": task_id, "explanation": "No candidates evaluated.", "pairs": []}

        sorted_d = sorted(decisions, key=lambda d: d.final_score, reverse=True)
        pairs = []
        for i in range(len(sorted_d) - 1):
            comp = self.compare(sorted_d[i], sorted_d[i + 1])
            pairs.append({
                "rank_a": i + 1,
                "rank_b": i + 2,
                "worker_a": sorted_d[i].worker_id,
                "worker_b": sorted_d[i + 1].worker_id,
                "gap": round(comp.score_gap, 4),
                "summary": comp.summary,
                "counterfactual": comp.counterfactual,
            })

        winner = sorted_d[0]
        labels = [BRIDGE_LABELS.get(s, s) for s in winner.deciding_signals[:3]]
        overall = (
            f"Worker {_short_id(winner.worker_id)} ranked #1 at "
            f"{winner.final_score:.0%}. Key: {', '.join(labels) if labels else 'base match'}."
        )

        return {
            "task_id": task_id or (sorted_d[0].task_id if sorted_d else None),
            "explanation": overall,
            "total_candidates": len(sorted_d),
            "pairs": pairs,
        }

    # ----- Audit API -----

    def audit_summary(self) -> dict:
        """Aggregate stats on decision making."""
        if not self._decisions:
            return {
                "total_decisions": 0,
                "avg_score": 0.0,
                "most_impactful_signal": "",
                "signal_frequency": {},
                "decisions": [],
            }

        avg = sum(d.final_score for d in self._decisions) / len(self._decisions)
        most_impactful = ""
        if self._signal_impact_sum:
            most_impactful = max(self._signal_impact_sum, key=lambda k: abs(self._signal_impact_sum[k]))

        return {
            "total_decisions": self._total_decisions,
            "avg_score": round(avg, 4),
            "most_impactful_signal": most_impactful,
            "signal_frequency": dict(self._signal_deciding_count),
            "decisions": [d.to_dict() for d in self._decisions],
        }

    def reset(self) -> None:
        """Clear all decisions and stats."""
        self._decisions.clear()
        self._signal_impact_sum.clear()
        self._signal_deciding_count.clear()
        self._total_decisions = 0

    @property
    def decision_count(self) -> int:
        return self._total_decisions

    # ----- Persistence -----

    def save(self, path: str) -> None:
        """Save state to JSON."""
        data = self.audit_summary()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("ExplainerBridge saved %d decisions to %s", self._total_decisions, path)

    @classmethod
    def load(cls, path: str) -> "ExplainerBridge":
        """Load state from JSON."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        bridge = cls()
        for d_data in data.get("decisions", []):
            signals = [
                SignalContribution(
                    bridge_name=s.get("bridge_name", s.get("signal_name", "")),
                    bonus=s.get("bonus", 0.0),
                    weight=s.get("weight", 1.0),
                    confidence=s.get("confidence", 1.0),
                    detail=s.get("detail", {}),
                )
                for s in d_data.get("signals", [])
            ]
            decision = Decision(
                task_id=d_data.get("task_id", ""),
                worker_id=d_data.get("worker_id", ""),
                final_score=d_data.get("final_score", 0.0),
                base_score=d_data.get("base_score", 0.0),
                signals=signals,
                total_bonus=d_data.get("total_bonus", 0.0),
                deciding_signals=d_data.get("deciding_signals", []),
                explanation=d_data.get("explanation", ""),
                task_type=d_data.get("task_type", "general"),
                timestamp=d_data.get("timestamp", ""),
                decision_time_ms=d_data.get("decision_time_ms", 0.0),
            )
            bridge._store_decision(decision)

        return bridge

    # ----- Health -----

    def health(self) -> dict:
        """Health status endpoint."""
        return {
            "status": "healthy",
            "module": "explainer_bridge",
            "module_number": 72,
            "total_decisions": self._total_decisions,
            "tracked_signals": len(self._signal_impact_sum),
            "most_decisive_signal": (
                max(self._signal_deciding_count, key=self._signal_deciding_count.get)
                if self._signal_deciding_count else None
            ),
        }

    # ----- Internal -----

    def _generate_explanation(
        self,
        worker_id: str,
        task_id: str,
        final_score: float,
        base_score: float,
        signals: list[SignalContribution],
        deciding: list[str],
        task_type: str,
    ) -> str:
        phrases = _get_phrases(task_type)
        short = _short_id(worker_id)
        pct = f"{final_score:.0%}"
        parts = [f"Worker {short} scored {pct} for task {task_id}."]

        if base_score > 0:
            parts.append(f"Base match: {base_score:.0%}.")

        positive = [s for s in signals if s.bonus > 0.001]
        if positive:
            top_pos = positive[:3]
            strs = [f"{phrases.get(s.bridge_name, s.human_label)} (+{s.bonus:.1%})" for s in top_pos]
            parts.append(f"Advantages: {'; '.join(strs)}.")

        negative = [s for s in signals if s.bonus < -0.001]
        if negative:
            strs = [f"{s.human_label} ({s.bonus:+.1%})" for s in negative[:2]]
            parts.append(f"Concerns: {'; '.join(strs)}.")

        if deciding:
            labels = [BRIDGE_LABELS.get(s, s) for s in deciding]
            parts.append(f"Primary drivers: {', '.join(labels)}.")

        return " ".join(parts)

    def _comparison_summary(self, winner, loser, advantages, disadvantages) -> str:
        w = _short_id(winner.worker_id)
        l = _short_id(loser.worker_id)
        gap = winner.final_score - loser.final_score
        parts = [f"Worker {w} ({winner.final_score:.0%}) beat Worker {l} ({loser.final_score:.0%}) by {gap:.1%}."]

        if advantages:
            labels = [BRIDGE_LABELS.get(s, s) for s in advantages[:3]]
            parts.append(f"Advantages: {', '.join(labels)}.")
        if disadvantages:
            labels = [BRIDGE_LABELS.get(s, s) for s in disadvantages[:2]]
            parts.append(f"Runner-up edge: {', '.join(labels)}.")

        return " ".join(parts)

    def _counterfactual(self, winner, loser, deltas) -> str:
        gap = winner.final_score - loser.final_score
        for d in deltas:
            if d["delta"] > gap:
                label = BRIDGE_LABELS.get(d["signal"], d["signal"])
                return (
                    f"If {label} were disabled, Worker {_short_id(loser.worker_id)} "
                    f"would have won (delta {d['delta']:.1%} > gap {gap:.1%})."
                )
        return "No single signal removal would flip this decision."

    def _store_decision(self, decision: Decision) -> None:
        self._total_decisions += 1
        for sig in decision.signals:
            self._signal_impact_sum[sig.bridge_name] = (
                self._signal_impact_sum.get(sig.bridge_name, 0.0) + abs(sig.bonus)
            )
        for name in decision.deciding_signals:
            self._signal_deciding_count[name] = self._signal_deciding_count.get(name, 0) + 1

        if len(self._decisions) >= self._max_decisions:
            self._decisions = self._decisions[-(self._max_decisions // 2):]
        self._decisions.append(decision)

    def _reset_current(self) -> None:
        self._current_task_id = None
        self._current_worker_id = None
        self._current_signals = []
        self._current_base_score = 0.0
        self._current_start = 0.0
