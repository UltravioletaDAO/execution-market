"""
CalibratorBridge — Server-Side Outcome-Driven Weight Optimization

Module #73 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's SignalCalibrator (Signal #26).
Correlates routing decisions with actual task outcomes to identify which
swarm intelligence bridges (geo, quality, affinity, comm, fpq) are
actually predictive of success.

Closes the feedback loop:
1. ExplainerBridge records routing decisions with signal contributions
2. CalibratorBridge matches decisions with outcomes from EM task lifecycle
3. Point-biserial correlation identifies which signals predict success
4. Recommended weight adjustments for the coordinator

Key capabilities:
    1. record_decision() — Feed routing decision from ExplainerBridge
    2. record_outcome() — Feed task completion/failure from EventListener
    3. signal_accuracy() — Per-signal correlation with success
    4. recommend_adjustments() — Suggested weight changes
    5. drift_detection() — Alert when signal predictiveness shifts
    6. calibration_report() — Full diagnostic
    7. save/load — JSON persistence
    8. health() — Status endpoint

Architecture:
    - Mirrors AutoJob's SignalCalibrator for consistency
    - Minimum observations threshold before recommendations (default: 20)
    - Conservative adjustments (max ±15%)
    - Statistical significance via point-biserial correlation
    - Drift detection by comparing recent vs historical correlation

Integration with SwarmCoordinator:
    coordinator.calibrator_bridge.record_decision(...)
    coordinator.calibrator_bridge.record_outcome(...)
    report = coordinator.calibrator_bridge.calibration_report()

Author: Clawd (Dream Session, April 4 2026)
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("swarm.calibrator_bridge")

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class DecisionRecord:
    """A routing decision with bridge contributions."""
    task_id: str
    worker_id: str
    final_score: float
    signal_contributions: dict  # bridge_name → bonus
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "final_score": round(self.final_score, 4),
            "signal_contributions": {k: round(v, 4) for k, v in self.signal_contributions.items()},
            "timestamp": self.timestamp,
        }


@dataclass
class OutcomeRecord:
    """Actual outcome of a routed task."""
    task_id: str
    worker_id: str
    success: bool
    quality_score: float = 0.0
    completion_time_hours: float = 0.0
    revision_count: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "success": self.success,
            "quality_score": round(self.quality_score, 4),
            "completion_time_hours": round(self.completion_time_hours, 2),
            "revision_count": self.revision_count,
            "timestamp": self.timestamp,
        }


@dataclass
class SignalAccuracy:
    """How well a bridge predicts outcomes."""
    bridge_name: str
    correlation: float
    avg_bonus_success: float
    avg_bonus_failure: float
    predictive_power: float
    sample_size: int = 0
    is_significant: bool = False
    recommendation: str = ""
    adjustment: float = 0.0

    def to_dict(self) -> dict:
        return {
            "bridge_name": self.bridge_name,
            "correlation": round(self.correlation, 4),
            "avg_bonus_success": round(self.avg_bonus_success, 4),
            "avg_bonus_failure": round(self.avg_bonus_failure, 4),
            "predictive_power": round(self.predictive_power, 4),
            "sample_size": self.sample_size,
            "is_significant": self.is_significant,
            "recommendation": self.recommendation,
            "adjustment": round(self.adjustment, 4),
        }


@dataclass
class DriftAlert:
    """Alert when a bridge's predictiveness changes."""
    bridge_name: str
    direction: str
    old_correlation: float
    new_correlation: float
    change: float
    severity: str
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "bridge_name": self.bridge_name,
            "direction": self.direction,
            "old_correlation": round(self.old_correlation, 4),
            "new_correlation": round(self.new_correlation, 4),
            "change": round(self.change, 4),
            "severity": self.severity,
            "message": self.message,
        }


@dataclass
class CalibrationReport:
    """Full calibration diagnostic."""
    signal_accuracies: list = field(default_factory=list)
    recommendations: dict = field(default_factory=dict)
    drift_alerts: list = field(default_factory=list)
    total_decisions: int = 0
    total_outcomes: int = 0
    matched_pairs: int = 0
    success_rate: float = 0.0
    avg_quality: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "signal_accuracies": [a.to_dict() for a in self.signal_accuracies],
            "recommendations": {k: round(v, 4) for k, v in self.recommendations.items()},
            "drift_alerts": [d.to_dict() for d in self.drift_alerts],
            "total_decisions": self.total_decisions,
            "total_outcomes": self.total_outcomes,
            "matched_pairs": self.matched_pairs,
            "success_rate": round(self.success_rate, 4),
            "avg_quality": round(self.avg_quality, 4),
            "timestamp": self.timestamp,
        }

    @property
    def has_drift(self) -> bool:
        return len(self.drift_alerts) > 0

    @property
    def needs_recalibration(self) -> bool:
        return any(abs(v) > 0.05 for v in self.recommendations.values())


# ---------------------------------------------------------------------------
# CalibratorBridge
# ---------------------------------------------------------------------------

class CalibratorBridge:
    """Server-side outcome-driven weight optimization for the swarm coordinator."""

    def __init__(
        self,
        *,
        min_observations: int = 20,
        max_adjustment: float = 0.15,
        drift_window: int = 50,
        drift_threshold: float = 0.15,
    ):
        self._min_obs = min_observations
        self._max_adj = max_adjustment
        self._drift_window = drift_window
        self._drift_threshold = drift_threshold

        self._decisions: dict[str, DecisionRecord] = {}
        self._outcomes: dict[str, OutcomeRecord] = {}
        self._total_decisions = 0
        self._total_outcomes = 0

    # ----- Input -----

    def record_decision(
        self,
        task_id: str,
        worker_id: str,
        final_score: float,
        signal_contributions: dict,
    ) -> None:
        """Record a routing decision."""
        key = f"{task_id}:{worker_id}"
        self._decisions[key] = DecisionRecord(
            task_id=task_id,
            worker_id=worker_id,
            final_score=final_score,
            signal_contributions=dict(signal_contributions),
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._total_decisions += 1

    def record_decision_from_explainer(self, decision_dict: dict) -> None:
        """Record from ExplainerBridge decision dict."""
        task_id = decision_dict.get("task_id", "")
        worker_id = decision_dict.get("worker_id", "")
        final_score = decision_dict.get("final_score", 0.0)
        signals = {}
        for sig in decision_dict.get("signals", []):
            name = sig.get("bridge_name", sig.get("signal_name", ""))
            bonus = sig.get("bonus", 0.0)
            if name:
                signals[name] = bonus
        self.record_decision(task_id, worker_id, final_score, signals)

    def record_outcome(
        self,
        task_id: str,
        worker_id: str,
        success: bool,
        quality_score: float = 0.0,
        completion_time_hours: float = 0.0,
        revision_count: int = 0,
    ) -> None:
        """Record actual task outcome."""
        key = f"{task_id}:{worker_id}"
        self._outcomes[key] = OutcomeRecord(
            task_id=task_id,
            worker_id=worker_id,
            success=success,
            quality_score=max(0.0, min(1.0, quality_score)),
            completion_time_hours=max(0.0, completion_time_hours),
            revision_count=max(0, revision_count),
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._total_outcomes += 1

    # ----- Analysis -----

    def signal_accuracy(self, bridge_name: str) -> SignalAccuracy:
        """Compute accuracy for a specific bridge."""
        pairs = self._matched_pairs()
        success_bonuses = []
        failure_bonuses = []

        for key, decision in pairs.items():
            outcome = self._outcomes[key]
            bonus = decision.signal_contributions.get(bridge_name, 0.0)
            if outcome.success:
                success_bonuses.append(bonus)
            else:
                failure_bonuses.append(bonus)

        n = len(success_bonuses) + len(failure_bonuses)
        if n == 0:
            return SignalAccuracy(bridge_name=bridge_name, correlation=0.0,
                                 avg_bonus_success=0.0, avg_bonus_failure=0.0,
                                 predictive_power=0.0, sample_size=0)

        avg_s = sum(success_bonuses) / len(success_bonuses) if success_bonuses else 0.0
        avg_f = sum(failure_bonuses) / len(failure_bonuses) if failure_bonuses else 0.0
        corr = self._point_biserial(success_bonuses, failure_bonuses)
        is_sig = n >= self._min_obs

        rec = "maintain"
        adj = 0.0
        if is_sig:
            if corr > 0.1:
                rec = "increase"
                adj = min(self._max_adj, corr * 0.1)
            elif corr < -0.1:
                rec = "decrease"
                adj = max(-self._max_adj, corr * 0.1)

        return SignalAccuracy(
            bridge_name=bridge_name, correlation=corr,
            avg_bonus_success=avg_s, avg_bonus_failure=avg_f,
            predictive_power=abs(corr), sample_size=n,
            is_significant=is_sig, recommendation=rec, adjustment=adj,
        )

    def all_signal_accuracies(self) -> list[SignalAccuracy]:
        all_names = set()
        for d in self._decisions.values():
            all_names.update(d.signal_contributions.keys())
        return [self.signal_accuracy(n) for n in sorted(all_names)]

    def recommend_adjustments(self) -> dict[str, float]:
        return {
            a.bridge_name: a.adjustment
            for a in self.all_signal_accuracies()
            if a.is_significant and abs(a.adjustment) > 0.001
        }

    def drift_detection(self) -> list[DriftAlert]:
        pairs = self._matched_pairs()
        if len(pairs) < self._drift_window * 2:
            return []

        sorted_keys = sorted(pairs.keys(), key=lambda k: self._outcomes[k].timestamp)
        mid = len(sorted_keys) // 2
        old_keys = sorted_keys[:mid]
        new_keys = sorted_keys[mid:]

        all_names = set()
        for d in self._decisions.values():
            all_names.update(d.signal_contributions.keys())

        alerts = []
        for name in all_names:
            old_c = self._corr_subset(name, old_keys)
            new_c = self._corr_subset(name, new_keys)
            change = new_c - old_c
            if abs(change) >= self._drift_threshold:
                direction = "improving" if change > 0 else "degrading"
                severity = "high" if abs(change) >= 0.3 else ("medium" if abs(change) >= 0.2 else "low")
                alerts.append(DriftAlert(
                    bridge_name=name, direction=direction,
                    old_correlation=old_c, new_correlation=new_c,
                    change=change, severity=severity,
                    message=f"Bridge '{name}' {direction}: {old_c:.2f} → {new_c:.2f}",
                ))
        return alerts

    def calibration_report(self) -> CalibrationReport:
        pairs = self._matched_pairs()
        outcomes = [self._outcomes[k] for k in pairs]
        sc = sum(1 for o in outcomes if o.success)
        sr = sc / len(outcomes) if outcomes else 0.0
        aq = sum(o.quality_score for o in outcomes) / len(outcomes) if outcomes else 0.0

        return CalibrationReport(
            signal_accuracies=self.all_signal_accuracies(),
            recommendations=self.recommend_adjustments(),
            drift_alerts=self.drift_detection(),
            total_decisions=self._total_decisions,
            total_outcomes=self._total_outcomes,
            matched_pairs=len(pairs),
            success_rate=sr,
            avg_quality=aq,
            timestamp=datetime.now(UTC).isoformat(),
        )

    # ----- Persistence -----

    def save(self, path: str) -> None:
        data = {
            "decisions": {k: v.to_dict() for k, v in self._decisions.items()},
            "outcomes": {k: v.to_dict() for k, v in self._outcomes.items()},
            "total_decisions": self._total_decisions,
            "total_outcomes": self._total_outcomes,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("CalibratorBridge saved %d decisions to %s", self._total_decisions, path)

    @classmethod
    def load(cls, path: str) -> "CalibratorBridge":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        bridge = cls()
        for key, d_data in data.get("decisions", {}).items():
            bridge._decisions[key] = DecisionRecord(**d_data)
        for key, o_data in data.get("outcomes", {}).items():
            bridge._outcomes[key] = OutcomeRecord(**o_data)
        bridge._total_decisions = data.get("total_decisions", len(bridge._decisions))
        bridge._total_outcomes = data.get("total_outcomes", len(bridge._outcomes))
        return bridge

    # ----- Health -----

    def health(self) -> dict:
        pairs = self._matched_pairs()
        return {
            "status": "healthy",
            "module": "calibrator_bridge",
            "module_number": 73,
            "total_decisions": self._total_decisions,
            "total_outcomes": self._total_outcomes,
            "matched_pairs": len(pairs),
            "ready_for_calibration": len(pairs) >= self._min_obs,
        }

    @property
    def decision_count(self) -> int:
        return self._total_decisions

    @property
    def outcome_count(self) -> int:
        return self._total_outcomes

    @property
    def matched_count(self) -> int:
        return len(self._matched_pairs())

    # ----- Internal -----

    def _matched_pairs(self) -> dict[str, DecisionRecord]:
        return {k: d for k, d in self._decisions.items() if k in self._outcomes}

    def _point_biserial(self, success_vals, failure_vals) -> float:
        n1, n0 = len(success_vals), len(failure_vals)
        n = n1 + n0
        if n < 2 or n1 == 0 or n0 == 0:
            return 0.0
        m1 = sum(success_vals) / n1
        m0 = sum(failure_vals) / n0
        all_v = success_vals + failure_vals
        mu = sum(all_v) / n
        var = sum((x - mu) ** 2 for x in all_v) / n
        if var < 1e-12:
            return 0.0
        return max(-1.0, min(1.0, (m1 - m0) / math.sqrt(var) * math.sqrt(n1 * n0 / n**2)))

    def _corr_subset(self, name, keys):
        s, f = [], []
        for k in keys:
            if k in self._decisions and k in self._outcomes:
                b = self._decisions[k].signal_contributions.get(name, 0.0)
                (s if self._outcomes[k].success else f).append(b)
        return self._point_biserial(s, f)
