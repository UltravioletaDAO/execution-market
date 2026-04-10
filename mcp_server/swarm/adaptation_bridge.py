from __future__ import annotations
"""
AdaptationBridge — Server-Side Contextual Signal Adaptation

Module #76 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's ContextualAdaptation (Signal #29).
Analyzes task context across 5 dimensions and produces signal weight
modifiers that make the entire routing system context-aware.

The Fixed-Weight Problem
========================

Signals #1-28 each use fixed parameters regardless of task context.
A physical delivery in downtown Manhattan during rush hour and a midnight
audio transcription get identical signal weights. This is like running
the same SQL query against every table in a database — technically works,
but massively inefficient.

Signal #29 introduces contextual intelligence: before routing, analyze
the task and adjust signal weights so the routing system focuses on
what ACTUALLY matters for this specific task.

Five Context Dimensions:

1. Task Type — Physical tasks amplify spatial/temporal/sustainability;
   digital tasks amplify quality/competence, dampen spatial
2. Urgency — Urgent tasks amplify temporal, relax sustainability;
   scheduled tasks amplify quality and sustainability
3. Value — High-value tasks amplify fraud/quality/transparency;
   low-value tasks relax thresholds for fill rate
4. Market — High supply enables selectivity; low supply relaxes
   standards to ensure completion
5. Historical — High failure rates tighten integrity; low rates relax

Integration with SwarmCoordinator:
    modifiers = coordinator.adaptation_bridge.compute_modifiers(task, fleet)
    # modifiers.modifiers = {signal_name: float, ...}
    # modifiers.context.task_type = "physical" | "digital" | "hybrid" | "unknown"
    # modifiers.confidence = 0.0-1.0

    # Apply in routing loop:
    for signal_name, base_bonus in signals.items():
        adjusted = base_bonus * modifiers.modifiers.get(signal_name, 1.0)

Author: Clawd (Dream Session, April 4 2026)
"""

import json
import logging
import math
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("swarm.adaptation_bridge")

UTC = timezone.utc

# ===========================================================================
# Signal Group Definitions
# ===========================================================================

SIGNAL_GROUPS = {
    "competence": [
        "capability_match", "market_fit", "credential_resolve",
        "reputation_match", "skill_graph", "competitive_position",
    ],
    "spatial": ["geo_proximity"],
    "temporal": ["availability_predict", "lifecycle_intel", "workload_forecast"],
    "quality": ["evidence_quality", "first_pass_quality", "communication_quality"],
    "social": ["social_trust", "task_affinity", "exploration"],
    "meta_transparency": ["explainer"],
    "meta_calibration": ["calibrator"],
    "meta_integrity": ["fraud_detector"],
    "meta_sustainability": ["load_balancer"],
}

SIGNAL_TO_GROUP = {}
for _grp, _sigs in SIGNAL_GROUPS.items():
    for _s in _sigs:
        SIGNAL_TO_GROUP[_s] = _grp

ALL_SIGNALS = [s for sigs in SIGNAL_GROUPS.values() for s in sigs]

PHYSICAL_KEYWORDS = {
    "physical", "verification", "photograph", "photo", "deliver", "delivery",
    "inspect", "visit", "storefront", "location", "pickup", "drop-off",
    "survey", "field", "onsite", "in-person", "walk", "drive",
}
DIGITAL_KEYWORDS = {
    "digital", "transcribe", "transcription", "review", "document", "code",
    "analysis", "research", "writing", "translate", "data", "entry",
    "annotation", "label", "moderate", "categorize", "online",
}
PHYSICAL_EVIDENCE = {"photo", "photo_geo", "video", "measurement", "signature", "notarized"}
DIGITAL_EVIDENCE = {"text_response", "document", "screenshot"}

MIN_MODIFIER = 0.3
MAX_MODIFIER = 3.0


# ===========================================================================
# Configuration
# ===========================================================================

@dataclass
class AdaptationBridgeConfig:
    """Configuration for the server-side adaptation bridge."""

    # Task type context
    physical_amplify_spatial: float = 2.0
    physical_amplify_temporal: float = 1.5
    physical_amplify_sustainability: float = 1.4
    physical_dampen_social: float = 0.7
    digital_amplify_quality: float = 1.8
    digital_amplify_competence: float = 1.5
    digital_dampen_spatial: float = 0.4

    # Urgency context
    urgency_amplify_temporal: float = 1.8
    urgency_dampen_sustainability: float = 0.6
    urgency_amplify_competence: float = 1.3
    scheduled_amplify_sustainability: float = 1.6
    scheduled_amplify_quality: float = 1.3

    # Value context
    high_value_threshold_usd: float = 20.0
    low_value_threshold_usd: float = 2.0
    high_value_amplify_integrity: float = 2.0
    high_value_amplify_quality: float = 1.6
    high_value_amplify_transparency: float = 1.5
    low_value_dampen_integrity: float = 0.6
    low_value_dampen_quality: float = 0.7

    # Market context
    high_supply_threshold: int = 10
    low_supply_threshold: int = 2
    high_supply_amplify_quality: float = 1.5
    high_supply_amplify_competence: float = 1.3
    low_supply_dampen_quality: float = 0.6
    low_supply_dampen_competence: float = 0.7

    # Historical context
    high_failure_rate: float = 0.3
    low_failure_rate: float = 0.05
    high_failure_amplify_integrity: float = 1.8
    high_failure_amplify_quality: float = 1.4
    low_failure_dampen_integrity: float = 0.7

    # Bounds
    min_history_tasks: int = 5
    history_window_days: int = 30


# ===========================================================================
# Data Structures
# ===========================================================================

@dataclass
class TaskContext:
    """Extracted context from a task."""
    task_type: str  # physical, digital, hybrid, unknown
    urgency: str  # urgent, scheduled, normal
    value_tier: str  # high, medium, low
    bounty_usd: float
    category: str
    evidence_types: list[str] = field(default_factory=list)
    deadline_hours: Optional[float] = None
    location: Optional[dict] = None


@dataclass
class FleetState:
    """Current state of the worker fleet."""
    available_workers: int = 0
    workers_in_area: int = 0
    avg_utilization: float = 0.0
    task_type_failure_rate: float = 0.0
    task_type_history_count: int = 0


@dataclass
class ModifierResult:
    """Result of contextual adaptation computation."""
    modifiers: dict[str, float]  # signal_name → modifier
    group_modifiers: dict[str, float]  # group_name → modifier
    context: TaskContext
    dimensions_applied: list[str]
    explanation: dict[str, str]
    confidence: float
    computed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "modifiers": self.modifiers,
            "group_modifiers": self.group_modifiers,
            "context": asdict(self.context),
            "dimensions_applied": self.dimensions_applied,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "computed_at": self.computed_at,
        }


@dataclass
class OutcomeRecord:
    """Record of a task outcome for historical learning."""
    task_id: str
    task_type: str
    category: str
    outcome: str  # success, failure, timeout, cancelled
    bounty_usd: float
    recorded_at: float = field(default_factory=time.time)


# ===========================================================================
# Core Engine
# ===========================================================================

class AdaptationBridge:
    """
    Server-side contextual adaptation engine (Module #76).

    Mirrors AutoJob's ContextualAdaptation for server-side use in
    the SwarmCoordinator. Analyzes task context and produces signal
    weight modifiers for context-aware routing.
    """

    def __init__(self, config: Optional[AdaptationBridgeConfig] = None):
        self.config = config or AdaptationBridgeConfig()
        self._task_type_stats: dict[str, dict[str, Any]] = {}
        self._history: list[OutcomeRecord] = []
        self._adaptation_count = 0

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def compute_modifiers(
        self,
        task: dict,
        fleet_state: Optional[FleetState] = None,
    ) -> ModifierResult:
        """Compute signal weight modifiers for a task."""
        fleet = fleet_state or FleetState()
        context = self._extract_context(task)

        group_mods: dict[str, float] = {g: 1.0 for g in SIGNAL_GROUPS}
        explanations: dict[str, str] = {}
        dimensions: list[str] = []

        # Dimension 1: Task Type
        mods, expl = self._task_type_context(context)
        if mods:
            dimensions.append("task_type")
            self._merge(group_mods, mods)
            explanations.update(expl)

        # Dimension 2: Urgency
        mods, expl = self._urgency_context(context)
        if mods:
            dimensions.append("urgency")
            self._merge(group_mods, mods)
            explanations.update(expl)

        # Dimension 3: Value
        mods, expl = self._value_context(context)
        if mods:
            dimensions.append("value")
            self._merge(group_mods, mods)
            explanations.update(expl)

        # Dimension 4: Market
        mods, expl = self._market_context(context, fleet)
        if mods:
            dimensions.append("market")
            self._merge(group_mods, mods)
            explanations.update(expl)

        # Dimension 5: Historical
        mods, expl = self._historical_context(context, fleet)
        if mods:
            dimensions.append("historical")
            self._merge(group_mods, mods)
            explanations.update(expl)

        # Clamp
        for g in group_mods:
            group_mods[g] = max(MIN_MODIFIER, min(MAX_MODIFIER, group_mods[g]))

        # Expand to per-signal
        signal_mods: dict[str, float] = {}
        for group, signals in SIGNAL_GROUPS.items():
            for sig in signals:
                signal_mods[sig] = group_mods[group]

        confidence = self._compute_confidence(context, fleet, dimensions)
        self._adaptation_count += 1

        return ModifierResult(
            modifiers=signal_mods,
            group_modifiers=group_mods,
            context=context,
            dimensions_applied=dimensions,
            explanation=explanations,
            confidence=confidence,
        )

    def record_outcome(
        self,
        task_id: str,
        task: dict,
        outcome: str,
    ) -> None:
        """Record a task outcome for historical learning."""
        context = self._extract_context(task)
        record = OutcomeRecord(
            task_id=task_id,
            task_type=context.task_type,
            category=context.category,
            outcome=outcome,
            bounty_usd=context.bounty_usd,
        )
        self._history.append(record)

        cat = context.category or context.task_type
        if cat not in self._task_type_stats:
            self._task_type_stats[cat] = {"total": 0, "failures": 0, "bounty_sum": 0.0}
        stats = self._task_type_stats[cat]
        stats["total"] += 1
        stats["bounty_sum"] += context.bounty_usd
        if outcome in ("failure", "timeout"):
            stats["failures"] += 1

    def get_failure_rate(self, category: str) -> tuple[float, int]:
        """Get historical failure rate for a task category."""
        stats = self._task_type_stats.get(category, {})
        total = stats.get("total", 0)
        if total == 0:
            return 0.0, 0
        return stats.get("failures", 0) / total, total

    def health(self) -> dict:
        """Health check."""
        return {
            "status": "healthy",
            "module": "adaptation_bridge",
            "module_number": 76,
            "signal": "contextual_adaptation",
            "meta_layer": 5,
            "dimension": "intelligence",
            "adaptations": self._adaptation_count,
            "history_size": len(self._history),
            "task_types_tracked": len(self._task_type_stats),
            "signal_groups": len(SIGNAL_GROUPS),
            "total_signals": len(ALL_SIGNALS),
        }

    def report(self) -> dict:
        """Activity report."""
        type_counts: dict[str, int] = {}
        outcome_counts: dict[str, int] = {}
        for rec in self._history:
            type_counts[rec.task_type] = type_counts.get(rec.task_type, 0) + 1
            outcome_counts[rec.outcome] = outcome_counts.get(rec.outcome, 0) + 1

        return {
            "total_adaptations": self._adaptation_count,
            "total_outcomes": len(self._history),
            "task_type_distribution": type_counts,
            "outcome_distribution": outcome_counts,
            "task_type_stats": dict(self._task_type_stats),
        }

    # -------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save state to JSON."""
        data = {
            "version": 1,
            "task_type_stats": self._task_type_stats,
            "adaptation_count": self._adaptation_count,
            "recent_history": [
                asdict(r) for r in self._history[-100:]
            ],
            "saved_at": time.time(),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> bool:
        """Load state from JSON."""
        if not os.path.exists(path):
            return False
        try:
            with open(path) as f:
                data = json.load(f)
            self._task_type_stats = data.get("task_type_stats", {})
            self._adaptation_count = data.get("adaptation_count", 0)
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    # -------------------------------------------------------------------
    # Context Extraction
    # -------------------------------------------------------------------

    def _extract_context(self, task: dict) -> TaskContext:
        title = (task.get("title") or "").lower()
        description = (task.get("description") or "").lower()
        category = (task.get("category") or "").lower()
        bounty = float(task.get("bounty_usd", 0) or task.get("bounty", 0) or 0)
        evidence_types = task.get("evidence_types", [])
        if isinstance(evidence_types, str):
            evidence_types = [evidence_types]
        evidence_types = [e.lower() for e in evidence_types]

        task_type = self._classify_task_type(title, description, category, evidence_types)
        urgency = self._classify_urgency(task)
        value_tier = self._classify_value(bounty)

        location = None
        if task.get("latitude") and task.get("longitude"):
            location = {"lat": task["latitude"], "lon": task["longitude"]}

        deadline_hours = None
        if task.get("deadline"):
            dl = task["deadline"]
            if isinstance(dl, (int, float)) and dl > 0:
                deadline_hours = dl

        return TaskContext(
            task_type=task_type,
            urgency=urgency,
            value_tier=value_tier,
            bounty_usd=bounty,
            category=category,
            evidence_types=evidence_types,
            deadline_hours=deadline_hours,
            location=location,
        )

    def _classify_task_type(
        self, title: str, desc: str, category: str, evidence_types: list[str]
    ) -> str:
        text = f"{title} {desc} {category}"
        words = set(text.split())

        phys = len(words & PHYSICAL_KEYWORDS)
        digi = len(words & DIGITAL_KEYWORDS)

        ev_set = set(evidence_types)
        phys += len(ev_set & PHYSICAL_EVIDENCE) * 2
        digi += len(ev_set & DIGITAL_EVIDENCE) * 2

        if category in ("physical_verification", "delivery", "field_work", "inspection"):
            phys += 5
        elif category in ("digital_review", "transcription", "data_entry", "research"):
            digi += 5

        if phys > 0 and digi > 0:
            ratio = phys / (phys + digi)
            if ratio > 0.65:
                return "physical"
            elif ratio < 0.35:
                return "digital"
            return "hybrid"
        elif phys > 0:
            return "physical"
        elif digi > 0:
            return "digital"
        return "unknown"

    def _classify_urgency(self, task: dict) -> str:
        urgency = (task.get("urgency") or "").lower()
        if urgency in ("urgent", "critical", "asap"):
            return "urgent"
        if urgency in ("scheduled", "planned", "low"):
            return "scheduled"

        priority = task.get("priority", 0)
        if isinstance(priority, str):
            if priority.lower() in ("high", "critical"):
                return "urgent"
            if priority.lower() in ("low", "planned"):
                return "scheduled"
            try:
                priority = int(priority)
            except ValueError:
                priority = 0
        if isinstance(priority, (int, float)):
            if priority >= 8:
                return "urgent"
            if 0 < priority <= 2:
                return "scheduled"

        return "normal"

    def _classify_value(self, bounty: float) -> str:
        if bounty >= self.config.high_value_threshold_usd:
            return "high"
        if bounty <= self.config.low_value_threshold_usd:
            return "low"
        return "medium"

    # -------------------------------------------------------------------
    # Context Dimensions
    # -------------------------------------------------------------------

    def _task_type_context(self, ctx: TaskContext) -> tuple[dict, dict]:
        mods, expl = {}, {}
        c = self.config

        if ctx.task_type == "physical":
            mods["spatial"] = c.physical_amplify_spatial
            mods["temporal"] = c.physical_amplify_temporal
            mods["meta_sustainability"] = c.physical_amplify_sustainability
            mods["social"] = c.physical_dampen_social
            expl["spatial"] = f"Physical: geo amplified ×{c.physical_amplify_spatial}"
        elif ctx.task_type == "digital":
            mods["quality"] = c.digital_amplify_quality
            mods["competence"] = c.digital_amplify_competence
            mods["spatial"] = c.digital_dampen_spatial
            expl["quality"] = f"Digital: quality amplified ×{c.digital_amplify_quality}"
        elif ctx.task_type == "hybrid":
            mods["spatial"] = 1.3
            mods["quality"] = 1.3
            mods["competence"] = 1.2

        return mods, expl

    def _urgency_context(self, ctx: TaskContext) -> tuple[dict, dict]:
        mods, expl = {}, {}
        c = self.config

        if ctx.urgency == "urgent":
            mods["temporal"] = c.urgency_amplify_temporal
            mods["meta_sustainability"] = c.urgency_dampen_sustainability
            mods["competence"] = c.urgency_amplify_competence
            expl["temporal"] = f"Urgent: availability amplified ×{c.urgency_amplify_temporal}"
        elif ctx.urgency == "scheduled":
            mods["meta_sustainability"] = c.scheduled_amplify_sustainability
            mods["quality"] = c.scheduled_amplify_quality
            expl["meta_sustainability"] = f"Scheduled: load balance amplified ×{c.scheduled_amplify_sustainability}"

        return mods, expl

    def _value_context(self, ctx: TaskContext) -> tuple[dict, dict]:
        mods, expl = {}, {}
        c = self.config

        if ctx.value_tier == "high":
            mods["meta_integrity"] = c.high_value_amplify_integrity
            mods["quality"] = c.high_value_amplify_quality
            mods["meta_transparency"] = c.high_value_amplify_transparency
            expl["meta_integrity"] = f"High-value (${ctx.bounty_usd:.2f}): fraud amplified ×{c.high_value_amplify_integrity}"
        elif ctx.value_tier == "low":
            mods["meta_integrity"] = c.low_value_dampen_integrity
            mods["quality"] = c.low_value_dampen_quality
            expl["meta_integrity"] = f"Low-value (${ctx.bounty_usd:.2f}): integrity relaxed ×{c.low_value_dampen_integrity}"

        return mods, expl

    def _market_context(self, ctx: TaskContext, fleet: FleetState) -> tuple[dict, dict]:
        mods, expl = {}, {}
        c = self.config

        workers = fleet.workers_in_area if fleet.workers_in_area > 0 else fleet.available_workers
        if workers <= 0:
            return mods, expl

        if workers >= c.high_supply_threshold:
            mods["quality"] = c.high_supply_amplify_quality
            mods["competence"] = c.high_supply_amplify_competence
            expl["quality"] = f"High supply ({workers}): selective ×{c.high_supply_amplify_quality}"
        elif workers <= c.low_supply_threshold:
            mods["quality"] = c.low_supply_dampen_quality
            mods["competence"] = c.low_supply_dampen_competence
            expl["quality"] = f"Low supply ({workers}): relaxed ×{c.low_supply_dampen_quality}"

        return mods, expl

    def _historical_context(self, ctx: TaskContext, fleet: FleetState) -> tuple[dict, dict]:
        mods, expl = {}, {}
        c = self.config

        failure_rate = fleet.task_type_failure_rate
        count = fleet.task_type_history_count

        if count == 0 and ctx.category:
            failure_rate, count = self.get_failure_rate(ctx.category)

        if count < c.min_history_tasks:
            return mods, expl

        if failure_rate >= c.high_failure_rate:
            mods["meta_integrity"] = c.high_failure_amplify_integrity
            mods["quality"] = c.high_failure_amplify_quality
            expl["meta_integrity"] = f"High failure ({failure_rate:.0%}): integrity amplified ×{c.high_failure_amplify_integrity}"
        elif failure_rate <= c.low_failure_rate:
            mods["meta_integrity"] = c.low_failure_dampen_integrity
            expl["meta_integrity"] = f"Low failure ({failure_rate:.0%}): integrity relaxed ×{c.low_failure_dampen_integrity}"

        return mods, expl

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _merge(self, base: dict[str, float], new: dict[str, float]) -> None:
        for k, v in new.items():
            base[k] = base.get(k, 1.0) * v

    def _compute_confidence(
        self, ctx: TaskContext, fleet: FleetState, dims: list[str]
    ) -> float:
        conf = 0.3
        if ctx.task_type in ("physical", "digital"):
            conf += 0.15
        elif ctx.task_type == "hybrid":
            conf += 0.10
        conf += len(dims) * 0.08
        if fleet.available_workers > 0:
            conf += 0.10
        if fleet.task_type_history_count >= self.config.min_history_tasks:
            conf += 0.10
        if ctx.urgency != "normal":
            conf += 0.05
        return min(1.0, conf)
