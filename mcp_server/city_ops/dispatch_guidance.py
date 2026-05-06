"""Dispatch-brief guidance consumer for City-as-a-Service compact decisions.

This module is the first deliberately small runtime-consumer seam after compact
projection and continuity packaging.  It proves that a dispatch brief composer can
read the CompactDecisionObject instead of re-deriving promotion, tone, placement,
or copyability from raw replay artifacts.
"""

from __future__ import annotations

from typing import Any, Iterable

from .contracts import CityOpsContractError, CompactDecisionObject, PromotionClass
from .coordination import assert_carry_forward_integrity

DISPATCH_GUIDANCE_BLOCK_SCHEMA = "city_ops.dispatch_guidance_block.v1"
DISPATCH_GUIDANCE_CONSUMER = "dispatch_brief_composer"


OPERATOR_PREFACE_BY_PROMOTION: dict[PromotionClass, str] = {
    PromotionClass.CONFIDENT_MEMORY_DELTA: (
        "Reviewed municipal learning is strong enough to present as "
        "operator-confirmed guidance before worker copy."
    ),
    PromotionClass.CONSERVATIVE_MEMORY_DELTA: (
        "Reviewed municipal learning should change operator routing or evidence "
        "guidance, but must stay visible before worker-copyable instructions."
    ),
    PromotionClass.EPISODE_ONLY: (
        "Reviewed municipal learning should remain an operator/debug note until "
        "another proof strengthens it."
    ),
    PromotionClass.BLOCKED_FROM_MEMORY: (
        "Reviewed municipal learning is blocked from dispatch guidance and must "
        "not become worker instruction."
    ),
}


def build_dispatch_guidance_block(
    decision: CompactDecisionObject,
    *,
    ledger_events: Iterable[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
) -> dict[str, Any]:
    """Emit the first dispatch-brief consumer block from compact decision truth.

    The composer refuses to emit if the coordination ledger and pickup brief do
    not already preserve compact truth.  This keeps runtime guidance downstream
    of the same integrity gate used by continuity packaging.
    """

    events = list(ledger_events)
    assert_carry_forward_integrity(
        decision,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
    )

    return {
        "schema": DISPATCH_GUIDANCE_BLOCK_SCHEMA,
        "runtime_consumer": DISPATCH_GUIDANCE_CONSUMER,
        "coordination_session_id": decision.coordination_session_id,
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "source_episode_ids": list(decision.source_episode_ids),
        "summary_judgment": decision.summary_judgment,
        "promotion_class": decision.promotion_class.value,
        "guidance": {
            "tone": decision.guidance_tone.value,
            "placement": decision.guidance_placement.value,
            "operator_preface": OPERATOR_PREFACE_BY_PROMOTION[
                decision.promotion_class
            ],
            "copyable_worker_instruction": (
                decision.copyable_worker_instruction.to_dict()
            ),
            "worker_instruction_text": _worker_instruction_text(decision),
        },
        "claim_limits": {
            "safe_to_claim": list(decision.safe_to_claim),
            "not_safe_to_claim": list(decision.not_safe_to_claim),
            "dangerous_drift_axes": list(decision.dangerous_drift_axes),
            "next_smallest_proof": list(decision.next_smallest_proof),
        },
        "pickup_observation_class": morning_pickup_brief[
            "pickup_observation_class"
        ],
        "ledger_event_names": [event["event_name"] for event in events],
        "provenance_refs": dict(decision.provenance_refs),
    }


def assert_dispatch_guidance_parity(
    decision: CompactDecisionObject,
    *,
    dispatch_guidance_block: dict[str, Any],
    morning_pickup_brief: dict[str, Any],
) -> None:
    """Fail when a dispatch guidance consumer strengthens compact truth."""

    _require_equal(
        dispatch_guidance_block.get("schema"),
        DISPATCH_GUIDANCE_BLOCK_SCHEMA,
        "dispatch_guidance.schema",
    )
    _require_equal(
        dispatch_guidance_block.get("runtime_consumer"),
        DISPATCH_GUIDANCE_CONSUMER,
        "dispatch_guidance.runtime_consumer",
    )
    for key in (
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
        "proof_anchor_id",
        "summary_judgment",
    ):
        _require_equal(
            dispatch_guidance_block.get(key),
            getattr(decision, key),
            f"dispatch_guidance.{key}",
        )

    guidance = _required_dict(dispatch_guidance_block, "guidance")
    pickup_promotion = _required_dict(morning_pickup_brief, "promotion")
    _require_equal(
        guidance.get("tone"),
        decision.guidance_tone.value,
        "dispatch_guidance.guidance.tone",
    )
    _require_equal(
        guidance.get("tone"),
        pickup_promotion.get("guidance_tone"),
        "dispatch_guidance.guidance.tone_vs_pickup",
    )
    _require_equal(
        guidance.get("placement"),
        decision.guidance_placement.value,
        "dispatch_guidance.guidance.placement",
    )
    _require_equal(
        guidance.get("placement"),
        pickup_promotion.get("guidance_placement"),
        "dispatch_guidance.guidance.placement_vs_pickup",
    )

    copyable = _required_dict(guidance, "copyable_worker_instruction")
    _require_equal(
        copyable.get("allowed"),
        decision.copyable_worker_instruction.allowed,
        "dispatch_guidance.copyable_worker_instruction.allowed",
    )
    _require_equal(
        copyable.get("reason"),
        decision.copyable_worker_instruction.reason,
        "dispatch_guidance.copyable_worker_instruction.reason",
    )
    if not decision.copyable_worker_instruction.allowed:
        _require_equal(
            guidance.get("worker_instruction_text"),
            None,
            "dispatch_guidance.guidance.worker_instruction_text",
        )

    claim_limits = _required_dict(dispatch_guidance_block, "claim_limits")
    for key in (
        "safe_to_claim",
        "not_safe_to_claim",
        "dangerous_drift_axes",
        "next_smallest_proof",
    ):
        _require_equal(
            claim_limits.get(key),
            list(getattr(decision, key)),
            f"dispatch_guidance.claim_limits.{key}",
        )


def _worker_instruction_text(decision: CompactDecisionObject) -> str | None:
    if not decision.copyable_worker_instruction.allowed:
        return None
    return decision.summary_judgment


def _required_dict(artifact: dict[str, Any], key: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{key} must be an object")
    return value


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")
