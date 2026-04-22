"""
Route Regret Compiler
=====================

Turns replayable coordinator decision events into compact operator-facing
route-regret reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteRegretReport:
    task_id: str
    coordination_session_id: str
    judgment: str
    regret_score: float
    selected_agent_id: int | None = None
    selected_score: float | None = None
    best_alternative_agent_id: int | None = None
    best_alternative_score: float | None = None
    outcome_status: str | None = None
    outcome_quality: float | None = None
    degradation_reasons: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
    tuning_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "task_id": self.task_id,
            "coordination_session_id": self.coordination_session_id,
            "judgment": self.judgment,
            "regret_score": round(self.regret_score, 3),
            "selected_agent_id": self.selected_agent_id,
            "selected_score": self.selected_score,
            "best_alternative_agent_id": self.best_alternative_agent_id,
            "best_alternative_score": self.best_alternative_score,
            "outcome": {
                "status": self.outcome_status,
                "quality": self.outcome_quality,
            },
            "degradation_reasons": self.degradation_reasons,
            "explanation": self.explanation,
            "tuning_hints": self.tuning_hints,
        }
        return {
            k: v
            for k, v in data.items()
            if v not in (None, [], {}) and not (k == "outcome" and all(val is None for val in v.values()))
        }


class RouteRegretCompiler:
    """Compile normalized coordinator events into route-regret reports."""

    def compile_episode(self, events: list[dict[str, Any]]) -> RouteRegretReport | None:
        if not events:
            return None

        ordered = sorted(events, key=lambda e: e.get("timestamp", 0.0))
        route = next((e for e in ordered if e.get("event_type") == "route"), None)
        if route is None:
            return None

        task_id = str(route.get("task_id") or "unknown")
        coordination_session_id = str(route.get("coordination_session_id") or f"coord_{task_id}")
        selected_agent_id = self._coerce_int(route.get("selected_agent_id") or route.get("agent_id") or route.get("worker_id"))
        selected_score = self._coerce_float(route.get("selected_score") or route.get("score"))

        alternatives = route.get("alternatives") or route.get("metadata", {}).get("alternatives") or []
        normalized_alts = [self._normalize_alternative(alt) for alt in alternatives]
        normalized_alts = [alt for alt in normalized_alts if alt.get("agent_id") is not None]
        normalized_alts.sort(key=lambda alt: alt.get("score", float("-inf")), reverse=True)
        best_alt = normalized_alts[0] if normalized_alts else None

        degrade_events = [e for e in ordered if e.get("event_type") == "degrade"]
        outcome = next((e for e in reversed(ordered) if e.get("event_type") == "outcome"), None)

        outcome_status = self._pick(outcome, "status") if outcome else None
        if not outcome_status and outcome:
            outcome_status = outcome.get("metadata", {}).get("status")
        outcome_quality = None
        if outcome:
            outcome_quality = self._coerce_float(outcome.get("quality"))
            if outcome_quality is None:
                outcome_quality = self._coerce_float(outcome.get("metadata", {}).get("quality"))

        degradation_reasons = []
        for event in degrade_events:
            reason = self._pick(event, "reason") or event.get("metadata", {}).get("reason") or event.get("metadata", {}).get("status")
            if reason and reason not in degradation_reasons:
                degradation_reasons.append(str(reason))
        if outcome:
            outcome_reason = (
                self._pick(outcome, "reason")
                or outcome.get("metadata", {}).get("reason")
                or outcome.get("metadata", {}).get("error")
            )
            if outcome_reason and str(outcome_reason) not in degradation_reasons:
                degradation_reasons.append(str(outcome_reason))

        judgment = "uncertain"
        regret_score = 0.0
        explanation: list[str] = []
        tuning_hints: list[str] = []

        alt_gap = None
        if best_alt and selected_score is not None and best_alt.get("score") is not None:
            alt_gap = round(selected_score - best_alt["score"], 3)

        if outcome_status == "completed" and not degradation_reasons:
            if outcome_quality is not None and outcome_quality >= 0.85:
                judgment = "validated"
                regret_score = -0.7 if (alt_gap is None or alt_gap >= 0.05) else -0.35
                explanation.append("Selected agent completed successfully with strong quality.")
            else:
                judgment = "matched"
                regret_score = -0.1 if outcome_quality is not None else 0.0
                explanation.append("Selected agent completed successfully without evidence of a materially better alternative.")
        elif degradation_reasons or outcome_status in {"failed", "expired", "reassigned", "degraded_then_reassigned"}:
            judgment = "regret"
            regret_score = 0.75 if best_alt else 0.55
            if degradation_reasons:
                explanation.append(f"Selected route degraded: {', '.join(degradation_reasons)}.")
            if outcome_status:
                explanation.append(f"Outcome status ended as {outcome_status}.")
            if best_alt and best_alt.get("agent_id") is not None:
                explanation.append(
                    f"Best alternative agent {best_alt['agent_id']} remained within the original shortlist"
                    + (f" at score {best_alt['score']:.2f}." if best_alt.get("score") is not None else ".")
                )
        else:
            judgment = "uncertain"
            regret_score = 0.15 if best_alt else 0.0
            explanation.append("Episode is missing enough follow-up evidence to judge the route confidently.")

        if best_alt and alt_gap is not None and abs(alt_gap) < 0.05:
            tuning_hints.append("Flag close-score routes for shadow evaluation when score gap is below 0.05.")
        if any("timeout" in reason.lower() for reason in degradation_reasons):
            tuning_hints.append("Increase timeout/cooldown penalties for agents that repeatedly degrade after assignment.")
        if outcome_quality is not None and outcome_quality < 0.6:
            tuning_hints.append("Raise outcome-quality weight for this task archetype in future routing decisions.")
        if not tuning_hints and best_alt:
            tuning_hints.append("Track runner-up outcomes in shadow mode to measure route regret instead of guessing.")

        return RouteRegretReport(
            task_id=task_id,
            coordination_session_id=coordination_session_id,
            judgment=judgment,
            regret_score=regret_score,
            selected_agent_id=selected_agent_id,
            selected_score=selected_score,
            best_alternative_agent_id=best_alt.get("agent_id") if best_alt else None,
            best_alternative_score=best_alt.get("score") if best_alt else None,
            outcome_status=outcome_status,
            outcome_quality=outcome_quality,
            degradation_reasons=degradation_reasons,
            explanation=explanation,
            tuning_hints=tuning_hints,
        )

    @staticmethod
    def _pick(event: dict[str, Any] | None, *keys: str) -> Any:
        if not event:
            return None
        for key in keys:
            if key in event and event[key] not in (None, ""):
                return event[key]
        return None

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_alternative(self, alt: Any) -> dict[str, Any]:
        if isinstance(alt, dict):
            return {
                "agent_id": self._coerce_int(alt.get("agent_id") or alt.get("worker_id") or alt.get("id")),
                "score": self._coerce_float(alt.get("score") or alt.get("selected_score") or alt.get("route_score")),
            }
        agent_id = self._coerce_int(alt)
        return {"agent_id": agent_id, "score": None}
