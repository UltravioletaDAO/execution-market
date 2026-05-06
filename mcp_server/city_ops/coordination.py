"""Coordination and continuity packaging for City-as-a-Service decisions.

The first CaaS proof ladder deliberately keeps runtime semantics local and
inspectable.  This module packages the projection-owned CompactDecisionObject
into the smallest coordination artifacts that later runtime, pickup, export,
rebuild, observability, and Acontext sinks can share without re-deriving trust.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .contracts import CityOpsContractError, CompactDecisionObject, PromotionClass

LEDGER_EVENT_SCHEMA = "city_ops.coordination_ledger_event.v1"
MORNING_PICKUP_BRIEF_SCHEMA = "city_ops.morning_pickup_brief.v1"


PICKUP_OBSERVATION_BY_PROMOTION: dict[PromotionClass, str] = {
    PromotionClass.CONFIDENT_MEMORY_DELTA: "confirmed",
    PromotionClass.CONSERVATIVE_MEMORY_DELTA: "cautious",
    PromotionClass.EPISODE_ONLY: "held",
    PromotionClass.BLOCKED_FROM_MEMORY: "suppressed",
}


def build_coordination_ledger_events(
    decision: CompactDecisionObject,
    *,
    occurred_at: str | None = None,
) -> list[dict[str, Any]]:
    """Build append-only coordination ledger rows from one compact decision.

    The rows intentionally mirror only compact, reviewed truth. They are safe to
    write to JSONL, later mirror into Acontext metadata, or use for restart
    rebuild previews without reading raw transcripts or replay bundles.
    """

    timestamp = occurred_at or _now_iso()
    return [
        _base_event(
            decision,
            event_name="city_compact_decision_projected",
            occurred_at=timestamp,
            event_index=1,
            payload={
                "summary_judgment": decision.summary_judgment,
                "learning_strength": decision.learning_strength.value,
                "memory_promotion_decision": (
                    decision.memory_promotion_decision.value
                ),
                "promotion_class": decision.promotion_class.value,
                "guidance_tone": decision.guidance_tone.value,
                "guidance_placement": decision.guidance_placement.value,
                "copyable_worker_instruction_allowed": (
                    decision.copyable_worker_instruction.allowed
                ),
                "source_episode_ids": list(decision.source_episode_ids),
            },
        ),
        _base_event(
            decision,
            event_name="city_session_rebuild_checkpoint_written",
            occurred_at=timestamp,
            event_index=2,
            payload={
                "rebuild_order": [
                    "coordination_ledger",
                    "dispatch_brief",
                    "review_packet",
                    "event_summary",
                    "morning_pickup_brief",
                ],
                "readiness": decision.readiness.to_dict(),
                "safe_to_claim": list(decision.safe_to_claim),
                "not_safe_to_claim": list(decision.not_safe_to_claim),
                "next_smallest_proof": list(decision.next_smallest_proof),
                "dangerous_drift_axes": list(decision.dangerous_drift_axes),
            },
        ),
    ]


def build_morning_pickup_brief(
    decision: CompactDecisionObject,
    ledger_events: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact next-session handoff from the same decision object.

    The brief is intentionally conservative: it carries the exact promotion,
    tone, placement, readiness, and anti-overclaim fields that should survive
    handoff. It does not strengthen runtime/reuse claims on its own.
    """

    events = list(ledger_events)
    _assert_event_chain(decision, events)
    return {
        "schema": MORNING_PICKUP_BRIEF_SCHEMA,
        "coordination_session_id": decision.coordination_session_id,
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "pickup_observation_class": PICKUP_OBSERVATION_BY_PROMOTION[
            decision.promotion_class
        ],
        "summary_judgment": decision.summary_judgment,
        "promotion": {
            "learning_strength": decision.learning_strength.value,
            "memory_promotion_decision": decision.memory_promotion_decision.value,
            "promotion_class": decision.promotion_class.value,
            "guidance_tone": decision.guidance_tone.value,
            "guidance_placement": decision.guidance_placement.value,
            "copyable_worker_instruction": (
                decision.copyable_worker_instruction.to_dict()
            ),
        },
        "readiness": decision.readiness.to_dict(),
        "safe_to_claim": list(decision.safe_to_claim),
        "not_safe_to_claim": list(decision.not_safe_to_claim),
        "next_smallest_proof": list(decision.next_smallest_proof),
        "dangerous_drift_axes": list(decision.dangerous_drift_axes),
        "source_episode_ids": list(decision.source_episode_ids),
        "ledger_event_names": [event["event_name"] for event in events],
        "provenance_refs": dict(decision.provenance_refs),
    }


def assert_carry_forward_integrity(
    decision: CompactDecisionObject,
    *,
    ledger_events: Iterable[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
) -> None:
    """Fail loudly when continuity artifacts drop or strengthen decision truth."""

    events = list(ledger_events)
    _assert_event_chain(decision, events)
    _require_equal(
        morning_pickup_brief.get("schema"),
        MORNING_PICKUP_BRIEF_SCHEMA,
        "morning_pickup_brief.schema",
    )
    for key in (
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
        "proof_anchor_id",
        "summary_judgment",
    ):
        _require_equal(
            morning_pickup_brief.get(key),
            getattr(decision, key),
            f"morning_pickup_brief.{key}",
        )

    promotion = _required_dict(morning_pickup_brief, "promotion")
    _require_equal(
        promotion.get("memory_promotion_decision"),
        decision.memory_promotion_decision.value,
        "morning_pickup_brief.promotion.memory_promotion_decision",
    )
    _require_equal(
        promotion.get("promotion_class"),
        decision.promotion_class.value,
        "morning_pickup_brief.promotion.promotion_class",
    )
    _require_equal(
        promotion.get("guidance_tone"),
        decision.guidance_tone.value,
        "morning_pickup_brief.promotion.guidance_tone",
    )
    _require_equal(
        promotion.get("guidance_placement"),
        decision.guidance_placement.value,
        "morning_pickup_brief.promotion.guidance_placement",
    )
    _require_equal(
        morning_pickup_brief.get("not_safe_to_claim"),
        list(decision.not_safe_to_claim),
        "morning_pickup_brief.not_safe_to_claim",
    )
    _require_equal(
        morning_pickup_brief.get("dangerous_drift_axes"),
        list(decision.dangerous_drift_axes),
        "morning_pickup_brief.dangerous_drift_axes",
    )


def _base_event(
    decision: CompactDecisionObject,
    *,
    event_name: str,
    occurred_at: str,
    event_index: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": LEDGER_EVENT_SCHEMA,
        "coordination_session_id": decision.coordination_session_id,
        "event_name": event_name,
        "event_index": event_index,
        "occurred_at": occurred_at,
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "promotion_class": decision.promotion_class.value,
        "guidance_tone": decision.guidance_tone.value,
        "guidance_placement": decision.guidance_placement.value,
        "payload": payload,
    }


def _assert_event_chain(
    decision: CompactDecisionObject,
    events: list[dict[str, Any]],
) -> None:
    if not events:
        raise CityOpsContractError("coordination ledger must contain events")
    seen_names: set[str] = set()
    for index, event in enumerate(events, start=1):
        _require_equal(event.get("schema"), LEDGER_EVENT_SCHEMA, "ledger.schema")
        _require_equal(
            event.get("coordination_session_id"),
            decision.coordination_session_id,
            "ledger.coordination_session_id",
        )
        _require_equal(
            event.get("compact_decision_id"),
            decision.compact_decision_id,
            "ledger.compact_decision_id",
        )
        _require_equal(
            event.get("review_packet_id"),
            decision.review_packet_id,
            "ledger.review_packet_id",
        )
        _require_equal(
            event.get("proof_anchor_id"),
            decision.proof_anchor_id,
            "ledger.proof_anchor_id",
        )
        _require_equal(event.get("event_index"), index, "ledger.event_index")
        name = event.get("event_name")
        if not isinstance(name, str) or not name:
            raise CityOpsContractError("ledger.event_name must be a non-empty string")
        if name in seen_names:
            raise CityOpsContractError(f"duplicate ledger.event_name {name!r}")
        seen_names.add(name)


def _required_dict(artifact: dict[str, Any], key: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{key} must be an object")
    return value


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
