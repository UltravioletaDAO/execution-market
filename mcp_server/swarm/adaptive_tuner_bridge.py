"""
Adaptive Tuner Bridge — Server-Side Weight Optimization
========================================================

Module #64 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's AdaptiveWeightTuner. Reads task
outcomes directly from Supabase and feeds them into a local tuner
instance, providing optimized weights to the routing pipeline.

This bridge enables the EM backend to self-optimize without depending
on an external AutoJob instance. It observes the full lifecycle of
tasks and adjusts signal weights based on real-world outcomes.

Key capabilities:
  1. Outcome ingestion from Supabase (completed/failed tasks)
  2. Decision recording from CoordinatorPipeline
  3. Weight optimization served to routing layer
  4. Category-specific tuning (physical vs digital vs verification)
  5. Drift detection with alerting
  6. A/B experiment management for weight configurations
  7. Health monitoring with sync staleness detection
"""

from __future__ import annotations

import json
import logging
import math
import statistics
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────

VERSION = "1.0.0"

SIGNAL_NAMES = [
    "skill",
    "reputation",
    "reliability",
    "recency",
    "lifecycle",
    "workload",
    "availability",
    "chain_cost",
    "quality_gate",
    "decomposition",
    "affinity",
    "retention",
    "competitive",
    "credential",
    "performance",
]

DEFAULT_WEIGHTS: dict[str, float] = {
    "skill": 0.45,
    "reputation": 0.25,
    "reliability": 0.20,
    "recency": 0.10,
    "lifecycle": 0.15,
    "workload": 0.10,
    "availability": 0.10,
    "chain_cost": 0.08,
    "quality_gate": 0.12,
    "decomposition": 0.05,
    "affinity": 0.08,
    "retention": 0.06,
    "competitive": 0.05,
    "credential": 0.07,
    "performance": 0.10,
}

MIN_WEIGHT = 0.01
MAX_WEIGHT = 0.60
ADAPTATION_RATE = 0.05
MIN_SAMPLES = 10
CORRELATION_WINDOW = 200


class OutcomeType(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    ABANDONED = "abandoned"
    TIMEOUT = "timeout"


OUTCOME_SCORES = {
    OutcomeType.SUCCESS: 1.0,
    OutcomeType.PARTIAL: 0.5,
    OutcomeType.FAILURE: 0.0,
    OutcomeType.ABANDONED: 0.0,
    OutcomeType.TIMEOUT: 0.1,
}


# ── Data Types ─────────────────────────────────────────────────────────


@dataclass
class DecisionRecord:
    """A routing decision recorded from the pipeline."""

    task_id: str
    worker_id: str
    category: str
    timestamp: float
    signal_scores: dict[str, float]
    final_score: float

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "category": self.category,
            "timestamp": self.timestamp,
            "signal_scores": dict(self.signal_scores),
            "final_score": self.final_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionRecord":
        return cls(
            task_id=d["task_id"],
            worker_id=d.get("worker_id", ""),
            category=d.get("category", "unknown"),
            timestamp=d.get("timestamp", 0.0),
            signal_scores=d.get("signal_scores", {}),
            final_score=d.get("final_score", 0.0),
        )


@dataclass
class OutcomeRecord:
    """A task outcome from Supabase."""

    task_id: str
    outcome: OutcomeType
    timestamp: float
    quality_score: float = 0.0
    completion_hours: float = 0.0
    evidence_count: int = 0
    worker_id: str = ""
    category: str = ""

    @property
    def outcome_score(self) -> float:
        base = OUTCOME_SCORES.get(self.outcome, 0.0)
        if self.outcome == OutcomeType.SUCCESS and self.quality_score > 0:
            return 0.5 + 0.5 * self.quality_score
        return base

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "outcome": self.outcome.value,
            "timestamp": self.timestamp,
            "quality_score": self.quality_score,
            "completion_hours": self.completion_hours,
            "evidence_count": self.evidence_count,
            "worker_id": self.worker_id,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OutcomeRecord":
        outcome_val = d.get("outcome", "failure")
        if isinstance(outcome_val, str):
            try:
                outcome_val = OutcomeType(outcome_val)
            except ValueError:
                outcome_val = OutcomeType.FAILURE
        return cls(
            task_id=d["task_id"],
            outcome=outcome_val,
            timestamp=d.get("timestamp", 0.0),
            quality_score=d.get("quality_score", 0.0),
            completion_hours=d.get("completion_hours", 0.0),
            evidence_count=d.get("evidence_count", 0),
            worker_id=d.get("worker_id", ""),
            category=d.get("category", ""),
        )


@dataclass
class SignalStats:
    """Per-signal effectiveness stats."""

    signal: str
    correlation: float
    separation: float
    sample_count: int
    confidence: float

    def to_dict(self) -> dict:
        return {
            "signal": self.signal,
            "correlation": round(self.correlation, 4),
            "separation": round(self.separation, 4),
            "sample_count": self.sample_count,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class WeightRecommendation:
    """A weight change recommendation."""

    signal: str
    current: float
    suggested: float
    delta: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "signal": self.signal,
            "current": round(self.current, 4),
            "suggested": round(self.suggested, 4),
            "delta": round(self.delta, 4),
            "reason": self.reason,
        }


@dataclass
class BridgeConfig:
    """Configuration for the AdaptiveTunerBridge."""

    adaptation_rate: float = ADAPTATION_RATE
    min_samples: int = MIN_SAMPLES
    correlation_window: int = CORRELATION_WINDOW
    min_weight: float = MIN_WEIGHT
    max_weight: float = MAX_WEIGHT
    enable_category_tuning: bool = True
    sync_interval_seconds: int = 300
    lookback_days: int = 30
    max_decisions: int = 2000
    max_outcomes: int = 2000

    def to_dict(self) -> dict:
        return {
            "adaptation_rate": self.adaptation_rate,
            "min_samples": self.min_samples,
            "correlation_window": self.correlation_window,
            "min_weight": self.min_weight,
            "max_weight": self.max_weight,
            "enable_category_tuning": self.enable_category_tuning,
            "sync_interval_seconds": self.sync_interval_seconds,
            "lookback_days": self.lookback_days,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BridgeConfig":
        cfg = cls()
        for key in [
            "adaptation_rate",
            "min_samples",
            "correlation_window",
            "min_weight",
            "max_weight",
            "enable_category_tuning",
            "sync_interval_seconds",
            "lookback_days",
            "max_decisions",
            "max_outcomes",
        ]:
            if key in d:
                setattr(cfg, key, d[key])
        return cfg


# ── Main Bridge ────────────────────────────────────────────────────────


class AdaptiveTunerBridge:
    """Server-side adaptive weight tuner for the routing pipeline.

    Reads task outcomes from Supabase, correlates them with routing
    decisions, and produces optimized signal weights.
    """

    def __init__(self, config: BridgeConfig | None = None):
        self.config = config or BridgeConfig()

        # Current optimized weights
        self._weights: dict[str, float] = dict(DEFAULT_WEIGHTS)

        # Decision and outcome storage
        self._decisions: list[DecisionRecord] = []
        self._outcomes: dict[str, OutcomeRecord] = {}

        # Matched pairs for correlation
        self._paired: list[tuple[DecisionRecord, OutcomeRecord]] = []

        # Category-specific weights
        self._category_weights: dict[str, dict[str, float]] = {}

        # Sync tracking
        self._last_sync_ts: float = 0.0
        self._sync_count: int = 0
        self._last_sync_tasks: int = 0

        # Metrics
        self._metrics = {
            "decisions_recorded": 0,
            "outcomes_ingested": 0,
            "pairs_matched": 0,
            "weight_updates": 0,
            "syncs_completed": 0,
            "last_update_ts": 0.0,
        }

    # ── Supabase Sync ──────────────────────────────────────────────

    def sync_from_supabase(self, rows: list[dict]) -> int:
        """Sync task outcome data from Supabase query results.

        Args:
            rows: Task rows with status, category, worker_address,
                  created_at, completed_at, etc.

        Returns:
            Number of outcomes ingested.
        """
        ingested = 0

        for row in rows:
            task_id = row.get("id", row.get("task_id", ""))
            if not task_id:
                continue

            status = row.get("status", "")
            outcome = self._status_to_outcome(status)
            if outcome is None:
                continue  # Skip in-progress tasks

            # Compute quality score from available data
            quality = self._compute_quality(row)

            # Compute completion hours
            completion_hours = self._compute_hours(row)

            record = OutcomeRecord(
                task_id=str(task_id),
                outcome=outcome,
                timestamp=time.time(),
                quality_score=quality,
                completion_hours=completion_hours,
                evidence_count=row.get("evidence_count", 0),
                worker_id=row.get("worker_address", ""),
                category=row.get("category", "unknown"),
            )

            self._outcomes[record.task_id] = record
            self._metrics["outcomes_ingested"] += 1
            ingested += 1

            # Try to pair with existing decision
            for dec in reversed(self._decisions):
                if dec.task_id == record.task_id:
                    self._pair(dec, record)
                    break

        # Trim outcomes if over limit
        if len(self._outcomes) > self.config.max_outcomes:
            oldest = sorted(self._outcomes, key=lambda k: self._outcomes[k].timestamp)
            for k in oldest[: len(self._outcomes) - self.config.max_outcomes]:
                del self._outcomes[k]

        self._last_sync_ts = time.time()
        self._sync_count += 1
        self._last_sync_tasks = ingested
        self._metrics["syncs_completed"] += 1

        logger.info(
            f"AdaptiveTunerBridge synced {ingested} outcomes from {len(rows)} rows"
        )
        return ingested

    @staticmethod
    def _status_to_outcome(status: str) -> OutcomeType | None:
        """Map task status to outcome type."""
        mapping = {
            "completed": OutcomeType.SUCCESS,
            "approved": OutcomeType.SUCCESS,
            "paid": OutcomeType.SUCCESS,
            "rejected": OutcomeType.FAILURE,
            "failed": OutcomeType.FAILURE,
            "cancelled": OutcomeType.ABANDONED,
            "expired": OutcomeType.TIMEOUT,
            "disputed": OutcomeType.PARTIAL,
        }
        return mapping.get(status)

    @staticmethod
    def _compute_quality(row: dict) -> float:
        """Estimate quality score from task data."""
        score = row.get("pre_check_score")
        if score is not None:
            return min(1.0, max(0.0, float(score) / 100.0))
        # Completed with evidence = baseline quality
        if row.get("status") in ("completed", "approved", "paid"):
            return 0.7
        return 0.0

    @staticmethod
    def _compute_hours(row: dict) -> float:
        """Compute completion hours from timestamps."""
        created = row.get("created_at")
        completed = row.get("completed_at", row.get("updated_at"))
        if not created or not completed:
            return 0.0
        try:
            from datetime import datetime

            if isinstance(created, str):
                c = datetime.fromisoformat(created.replace("Z", "+00:00"))
            else:
                c = created
            if isinstance(completed, str):
                co = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            else:
                co = completed
            delta = (co - c).total_seconds() / 3600.0
            return max(0.0, delta)
        except Exception:
            return 0.0

    # ── Decision Recording ─────────────────────────────────────────

    def record_decision(
        self,
        task_id: str,
        worker_id: str,
        category: str,
        signal_scores: dict[str, float],
        final_score: float,
    ) -> None:
        """Record a routing decision from the pipeline."""
        record = DecisionRecord(
            task_id=task_id,
            worker_id=worker_id,
            category=category,
            timestamp=time.time(),
            signal_scores=dict(signal_scores),
            final_score=final_score,
        )
        self._decisions.append(record)
        self._metrics["decisions_recorded"] += 1

        # Trim
        if len(self._decisions) > self.config.max_decisions:
            self._decisions = self._decisions[-self.config.max_decisions :]

        # Try to pair
        outcome = self._outcomes.get(task_id)
        if outcome:
            self._pair(record, outcome)

    def _pair(self, decision: DecisionRecord, outcome: OutcomeRecord) -> None:
        """Create a matched pair for correlation analysis."""
        for d, o in self._paired:
            if d.task_id == decision.task_id and d.worker_id == decision.worker_id:
                return
        self._paired.append((decision, outcome))
        self._metrics["pairs_matched"] += 1

    @property
    def paired_count(self) -> int:
        return len(self._paired)

    # ── Signal Effectiveness ───────────────────────────────────────

    def compute_effectiveness(
        self,
        category: str | None = None,
    ) -> dict[str, SignalStats]:
        """Compute per-signal effectiveness from matched pairs."""
        pairs = self._paired
        if category:
            pairs = [(d, o) for d, o in pairs if d.category == category]

        if len(pairs) > self.config.correlation_window:
            pairs = pairs[-self.config.correlation_window :]

        if len(pairs) < 3:
            return {}

        results = {}
        for signal in SIGNAL_NAMES:
            stats = self._signal_stats(signal, pairs)
            if stats:
                results[signal] = stats
        return results

    def _signal_stats(
        self,
        signal: str,
        pairs: list[tuple[DecisionRecord, OutcomeRecord]],
    ) -> SignalStats | None:
        """Compute effectiveness for a single signal."""
        signal_vals = []
        outcome_vals = []

        for dec, out in pairs:
            score = dec.signal_scores.get(signal)
            if score is not None:
                signal_vals.append(score)
                outcome_vals.append(out.outcome_score)

        n = len(signal_vals)
        if n < 3:
            return None

        correlation = self._pearson(signal_vals, outcome_vals)

        success_scores = [sv for sv, ov in zip(signal_vals, outcome_vals) if ov >= 0.5]
        failure_scores = [sv for sv, ov in zip(signal_vals, outcome_vals) if ov < 0.5]
        mean_success = statistics.mean(success_scores) if success_scores else 0.0
        mean_failure = statistics.mean(failure_scores) if failure_scores else 0.0

        return SignalStats(
            signal=signal,
            correlation=correlation,
            separation=mean_success - mean_failure,
            sample_count=n,
            confidence=min(1.0, n / 100.0),
        )

    @staticmethod
    def _pearson(x: list[float], y: list[float]) -> float:
        n = len(x)
        if n < 3:
            return 0.0
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
        if den_x == 0 or den_y == 0:
            return 0.0
        return num / (den_x * den_y)

    # ── Weight Optimization ────────────────────────────────────────

    def suggest_weights(
        self,
        category: str | None = None,
    ) -> dict[str, float]:
        """Suggest optimized weights based on observed outcomes."""
        if self.paired_count < self.config.min_samples:
            if category and category in self._category_weights:
                return dict(self._category_weights[category])
            return dict(self._weights)

        effectiveness = self.compute_effectiveness(category)
        if not effectiveness:
            return dict(self._weights)

        current = dict(self._weights)
        if category and category in self._category_weights:
            current = dict(self._category_weights[category])

        suggested = dict(current)

        for signal, stats in effectiveness.items():
            if signal not in suggested or stats.confidence < 0.3:
                continue

            old_w = suggested[signal]
            delta = stats.correlation * self.config.adaptation_rate

            if abs(stats.separation) > 0.05:
                delta += stats.separation * self.config.adaptation_rate * 0.5

            delta *= stats.confidence
            new_w = max(
                self.config.min_weight, min(self.config.max_weight, old_w + delta)
            )
            suggested[signal] = new_w

        # Normalize primary weights to ~1.0
        primary = ["skill", "reputation", "reliability", "recency"]
        primary_sum = sum(suggested.get(s, 0) for s in primary)
        if primary_sum > 0 and abs(primary_sum - 1.0) > 0.01:
            scale = 1.0 / primary_sum
            for s in primary:
                if s in suggested:
                    suggested[s] = max(
                        self.config.min_weight,
                        min(self.config.max_weight, suggested[s] * scale),
                    )

        if category and self.config.enable_category_tuning:
            self._category_weights[category] = dict(suggested)
        else:
            self._weights = dict(suggested)

        self._metrics["weight_updates"] += 1
        self._metrics["last_update_ts"] = time.time()

        return dict(suggested)

    def get_recommendations(
        self,
        category: str | None = None,
    ) -> list[WeightRecommendation]:
        """Get weight recommendations with rationale."""
        if self.paired_count < self.config.min_samples:
            return []

        effectiveness = self.compute_effectiveness(category)
        if not effectiveness:
            return []

        current = dict(self._weights)
        suggested = self.suggest_weights(category)

        results = []
        for signal in sorted(SIGNAL_NAMES):
            old_w = current.get(signal, 0.0)
            new_w = suggested.get(signal, old_w)
            delta = new_w - old_w
            if abs(delta) < 0.001:
                continue

            stats = effectiveness.get(signal)
            if stats:
                reason = (
                    f"corr={stats.correlation:.3f}, sep={stats.separation:.3f}, "
                    f"n={stats.sample_count}"
                )
            else:
                reason = "normalization"

            results.append(
                WeightRecommendation(
                    signal=signal,
                    current=old_w,
                    suggested=new_w,
                    delta=delta,
                    reason=reason,
                )
            )
        return results

    @property
    def current_weights(self) -> dict[str, float]:
        return dict(self._weights)

    def category_weights(self, category: str) -> dict[str, float]:
        if category in self._category_weights:
            return dict(self._category_weights[category])
        return dict(self._weights)

    def get_weights_for_task(self, task: dict) -> dict[str, float]:
        """Get optimal weights for a task based on its category."""
        category = task.get("category", "")
        if category and category in self._category_weights:
            return dict(self._category_weights[category])
        return dict(self._weights)

    def apply_weights(self, weights: dict[str, float]) -> None:
        for signal, w in weights.items():
            if signal in SIGNAL_NAMES:
                self._weights[signal] = max(
                    self.config.min_weight, min(self.config.max_weight, w)
                )

    def reset_weights(self) -> None:
        self._weights = dict(DEFAULT_WEIGHTS)
        self._category_weights.clear()

    # ── Health & Diagnostics ───────────────────────────────────────

    def health(self) -> dict:
        """Health check for the bridge."""
        now = time.time()
        sync_age_s = now - self._last_sync_ts if self._last_sync_ts > 0 else -1
        sync_stale = (
            sync_age_s > self.config.sync_interval_seconds * 3
            if sync_age_s >= 0
            else True
        )

        return {
            "status": "healthy" if not sync_stale else "stale",
            "paired_count": self.paired_count,
            "decisions_recorded": self._metrics["decisions_recorded"],
            "outcomes_ingested": self._metrics["outcomes_ingested"],
            "can_suggest": self.paired_count >= self.config.min_samples,
            "last_sync_age_s": round(sync_age_s, 1) if sync_age_s >= 0 else None,
            "sync_count": self._sync_count,
            "weight_updates": self._metrics["weight_updates"],
        }

    def summary(self) -> dict:
        """Full summary of bridge state."""
        effectiveness = self.compute_effectiveness() if self.paired_count >= 3 else {}

        sorted_eff = sorted(
            effectiveness.values(), key=lambda e: e.correlation, reverse=True
        )
        top = [
            {"signal": e.signal, "corr": round(e.correlation, 3)}
            for e in sorted_eff[:5]
        ]
        bottom = (
            [
                {"signal": e.signal, "corr": round(e.correlation, 3)}
                for e in sorted_eff[-3:]
            ]
            if sorted_eff
            else []
        )

        return {
            "version": VERSION,
            "paired_count": self.paired_count,
            "can_suggest": self.paired_count >= self.config.min_samples,
            "current_weights": {k: round(v, 4) for k, v in self._weights.items()},
            "categories_tuned": len(self._category_weights),
            "top_signals": top,
            "bottom_signals": bottom,
            "metrics": dict(self._metrics),
            "sync": {
                "count": self._sync_count,
                "last_tasks": self._last_sync_tasks,
                "last_ts": self._last_sync_ts,
            },
        }

    def metrics(self) -> dict:
        return dict(self._metrics)

    def outcome_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for o in self._outcomes.values():
            key = o.outcome.value
            dist[key] = dist.get(key, 0) + 1
        return dist

    def success_rate(self) -> float:
        if not self._outcomes:
            return 0.0
        successes = sum(
            1 for o in self._outcomes.values() if o.outcome == OutcomeType.SUCCESS
        )
        return successes / len(self._outcomes)

    def list_categories(self) -> list[str]:
        cats = set()
        for d in self._decisions:
            if d.category:
                cats.add(d.category)
        return sorted(cats)

    # ── Persistence ────────────────────────────────────────────────

    def save(self, path: str) -> None:
        state = {
            "version": VERSION,
            "config": self.config.to_dict(),
            "weights": dict(self._weights),
            "category_weights": {k: dict(v) for k, v in self._category_weights.items()},
            "decisions": [d.to_dict() for d in self._decisions[-500:]],
            "outcomes": {
                k: v.to_dict() for k, v in list(self._outcomes.items())[-500:]
            },
            "paired": [(d.to_dict(), o.to_dict()) for d, o in self._paired[-500:]],
            "metrics": dict(self._metrics),
            "saved_at": time.time(),
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "AdaptiveTunerBridge":
        with open(path) as f:
            state = json.load(f)

        config = BridgeConfig.from_dict(state.get("config", {}))
        bridge = cls(config=config)
        bridge._weights = state.get("weights", dict(DEFAULT_WEIGHTS))
        bridge._category_weights = state.get("category_weights", {})

        for d_dict in state.get("decisions", []):
            bridge._decisions.append(DecisionRecord.from_dict(d_dict))
        for tid, o_dict in state.get("outcomes", {}).items():
            bridge._outcomes[tid] = OutcomeRecord.from_dict(o_dict)
        for d_dict, o_dict in state.get("paired", []):
            bridge._paired.append(
                (
                    DecisionRecord.from_dict(d_dict),
                    OutcomeRecord.from_dict(o_dict),
                )
            )

        bridge._metrics = state.get("metrics", bridge._metrics)
        return bridge
