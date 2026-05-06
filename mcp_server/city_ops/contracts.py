"""Typed contracts for the first City-as-a-Service decision projection seam.

The PR-A goal is deliberately narrow: one reviewed replay packet plus one frozen
proof-anchor note must emit a compact decision object that owns trust semantics.
Downstream runtime, reuse, pickup, and export consumers should read this object
instead of re-deriving promotion/tone/copyability decisions independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CityOpsContractError(ValueError):
    """Raised when a CaaS proof artifact violates the projection contract."""


class LearningStrength(str, Enum):
    NONE = "none"
    WEAK = "weak"
    CAUTIONARY = "cautionary"
    STRONG = "strong"


class MemoryPromotionDecision(str, Enum):
    PROMOTE_CONSERVATIVE_DELTA = "promote_conservative_delta"
    PROMOTE_CONFIDENT_DELTA = "promote_confident_delta"
    HOLD_EPISODE_ONLY = "hold_episode_only"
    BLOCK_MEMORY_WRITE = "block_memory_write"


class PromotionClass(str, Enum):
    CONSERVATIVE_MEMORY_DELTA = "conservative_memory_delta"
    CONFIDENT_MEMORY_DELTA = "confident_memory_delta"
    EPISODE_ONLY = "episode_only"
    BLOCKED_FROM_MEMORY = "blocked_from_memory"


class GuidanceTone(str, Enum):
    CAUTIONARY_OR_CORRECTIVE = "cautionary_or_corrective"
    CONFIDENT = "confident"
    HELD_FOR_OPERATOR_REVIEW = "held_for_operator_review"
    BLOCKED = "blocked"


class GuidancePlacement(str, Enum):
    OPERATOR_VISIBLE_BEFORE_WORKER_COPY = "operator_visible_before_worker_copy"
    OFFICE_MEMORY_DEBUG_ONLY = "office_memory_debug_only"
    WORKER_COPYABLE_AFTER_OPERATOR_CONFIRM = "worker_copyable_after_operator_confirm"
    BLOCKED_FROM_WORKER_COPY = "blocked_from_worker_copy"


PROMOTION_POLICY: dict[
    MemoryPromotionDecision,
    tuple[PromotionClass, GuidanceTone, GuidancePlacement, bool],
] = {
    MemoryPromotionDecision.PROMOTE_CONSERVATIVE_DELTA: (
        PromotionClass.CONSERVATIVE_MEMORY_DELTA,
        GuidanceTone.CAUTIONARY_OR_CORRECTIVE,
        GuidancePlacement.OPERATOR_VISIBLE_BEFORE_WORKER_COPY,
        False,
    ),
    MemoryPromotionDecision.PROMOTE_CONFIDENT_DELTA: (
        PromotionClass.CONFIDENT_MEMORY_DELTA,
        GuidanceTone.CONFIDENT,
        GuidancePlacement.WORKER_COPYABLE_AFTER_OPERATOR_CONFIRM,
        True,
    ),
    MemoryPromotionDecision.HOLD_EPISODE_ONLY: (
        PromotionClass.EPISODE_ONLY,
        GuidanceTone.HELD_FOR_OPERATOR_REVIEW,
        GuidancePlacement.OFFICE_MEMORY_DEBUG_ONLY,
        False,
    ),
    MemoryPromotionDecision.BLOCK_MEMORY_WRITE: (
        PromotionClass.BLOCKED_FROM_MEMORY,
        GuidanceTone.BLOCKED,
        GuidancePlacement.BLOCKED_FROM_WORKER_COPY,
        False,
    ),
}


@dataclass(frozen=True)
class CopyableWorkerInstruction:
    """Whether reviewed truth may become direct worker-copyable guidance."""

    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason}


@dataclass(frozen=True)
class ReadinessPosture:
    """Explicit claim boundaries for downstream consumers."""

    continuity_ready: bool = True
    export_ready: bool = False
    session_rebuild_ready: bool = False
    operator_surface_ready: bool = True

    def to_dict(self) -> dict[str, bool]:
        return {
            "continuity_ready": self.continuity_ready,
            "export_ready": self.export_ready,
            "session_rebuild_ready": self.session_rebuild_ready,
            "operator_surface_ready": self.operator_surface_ready,
        }


@dataclass(frozen=True)
class CompactDecisionObject:
    """Projection-owned compact truth object for the first CaaS proof ladder."""

    compact_decision_id: str
    coordination_session_id: str
    review_packet_id: str
    proof_anchor_id: str
    summary_judgment: str
    learning_strength: LearningStrength
    memory_promotion_decision: MemoryPromotionDecision
    promotion_class: PromotionClass
    guidance_tone: GuidanceTone
    guidance_placement: GuidancePlacement
    copyable_worker_instruction: CopyableWorkerInstruction
    readiness: ReadinessPosture
    safe_to_claim: list[str] = field(default_factory=lambda: ["projection_truth_landed"])
    not_safe_to_claim: list[str] = field(
        default_factory=lambda: [
            "runtime_parity_proven",
            "reuse_behavior_proven",
            "closure_proof_ready",
        ]
    )
    next_smallest_proof: list[str] = field(default_factory=list)
    dangerous_drift_axes: list[str] = field(default_factory=list)
    source_episode_ids: list[str] = field(default_factory=list)
    provenance_refs: dict[str, str] = field(default_factory=dict)
    schema: str = "city_ops.compact_decision_object.v1"

    @property
    def continuity_ready(self) -> bool:
        return self.readiness.continuity_ready

    @property
    def export_ready(self) -> bool:
        return self.readiness.export_ready

    @property
    def session_rebuild_ready(self) -> bool:
        return self.readiness.session_rebuild_ready

    @property
    def operator_surface_ready(self) -> bool:
        return self.readiness.operator_surface_ready

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "compact_decision_id": self.compact_decision_id,
            "coordination_session_id": self.coordination_session_id,
            "review_packet_id": self.review_packet_id,
            "proof_anchor_id": self.proof_anchor_id,
            "summary_judgment": self.summary_judgment,
            "learning_strength": self.learning_strength.value,
            "memory_promotion_decision": self.memory_promotion_decision.value,
            "promotion_class": self.promotion_class.value,
            "guidance_tone": self.guidance_tone.value,
            "guidance_placement": self.guidance_placement.value,
            "copyable_worker_instruction": self.copyable_worker_instruction.to_dict(),
            "readiness": self.readiness.to_dict(),
            "safe_to_claim": list(self.safe_to_claim),
            "not_safe_to_claim": list(self.not_safe_to_claim),
            "next_smallest_proof": list(self.next_smallest_proof),
            "dangerous_drift_axes": list(self.dangerous_drift_axes),
            "source_episode_ids": list(self.source_episode_ids),
            "provenance_refs": dict(self.provenance_refs),
        }
