"""Reuse and redispatch proof helpers for City-as-a-Service decisions.

The projection, coordination, and dispatch-guidance seams prove that reviewed
city truth can be packaged without semantic drift.  This module closes the next
small runtime gap: proving that the same CompactDecisionObject can change a
later dispatch or redispatch for the right reason without becoming more
confident, more copyable, or less bounded than the reviewed decision allowed.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

from .contracts import CityOpsContractError, CompactDecisionObject, PromotionClass

REUSE_EVENT_SCHEMA = "city_ops.reuse_event.v1"
WORKER_INSTRUCTION_BLOCK_SCHEMA = "city_ops.worker_instruction_block.v1"
REUSE_OBSERVABILITY_ROW_SCHEMA = "city_ops.reuse_observability_row.v1"
REUSE_BEHAVIOR_SCOREBOARD_SCHEMA = "city_ops.reuse_behavior_scoreboard.v1"

VALID_REUSE_MODES = {
    "dispatch",
    "redispatch",
    "instruction_build",
    "resume",
}

VALID_BEHAVIOR_CHANGE_CLASSES = {
    "shown_only",
    "routing_changed",
    "instruction_changed",
    "evidence_guidance_changed",
    "redispatch_changed",
    "escalation_changed",
}

SUPPORTED_BEHAVIOR_BY_PROMOTION: dict[PromotionClass, set[str]] = {
    PromotionClass.CONFIDENT_MEMORY_DELTA: set(VALID_BEHAVIOR_CHANGE_CLASSES),
    PromotionClass.CONSERVATIVE_MEMORY_DELTA: {
        "shown_only",
        "routing_changed",
        "evidence_guidance_changed",
        "redispatch_changed",
        "escalation_changed",
    },
    PromotionClass.EPISODE_ONLY: {"shown_only"},
    PromotionClass.BLOCKED_FROM_MEMORY: {"shown_only"},
}


def build_reuse_event(
    decision: CompactDecisionObject,
    *,
    task_id: str,
    reuse_mode: str,
    behavior_change_class: str,
    reused_guidance_ids: Iterable[str] | None = None,
    notes: Iterable[str] | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Mirror a reuse moment without reinterpreting compact decision truth.

    The event records whether the prior reviewed learning was merely shown or
    materially changed dispatch behavior.  It refuses unsupported behavior-change
    classes so a cautious city lesson cannot silently become worker doctrine.
    """

    _require_non_empty_str(task_id, "task_id")
    _require_allowed(reuse_mode, VALID_REUSE_MODES, "reuse_mode")
    _require_allowed(
        behavior_change_class,
        VALID_BEHAVIOR_CHANGE_CLASSES,
        "behavior_change_class",
    )
    _assert_behavior_supported(decision, behavior_change_class)
    guidance_ids = _optional_str_list(reused_guidance_ids, "reused_guidance_ids")
    note_list = _optional_str_list(notes, "notes")

    return {
        "schema": REUSE_EVENT_SCHEMA,
        "coordination_session_id": decision.coordination_session_id,
        "task_id": task_id,
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "reuse_mode": reuse_mode,
        "behavior_change_class": behavior_change_class,
        "promotion_class": decision.promotion_class.value,
        "guidance_tone": decision.guidance_tone.value,
        "guidance_placement": decision.guidance_placement.value,
        "copyable_worker_instruction": decision.copyable_worker_instruction.to_dict(),
        "safe_to_claim": list(decision.safe_to_claim),
        "not_safe_to_claim": list(decision.not_safe_to_claim),
        "dangerous_drift_axes": list(decision.dangerous_drift_axes),
        "reused_guidance_ids": guidance_ids,
        "notes": note_list,
        "occurred_at": occurred_at or _now_iso(),
    }


def build_worker_instruction_block(
    decision: CompactDecisionObject,
    *,
    reuse_event: dict[str, Any],
) -> dict[str, Any]:
    """Build the worker-handoff block governed by reuse copyability limits."""

    assert_reuse_alignment(decision, reuse_event=reuse_event)
    allowed = decision.copyable_worker_instruction.allowed
    return {
        "schema": WORKER_INSTRUCTION_BLOCK_SCHEMA,
        "coordination_session_id": decision.coordination_session_id,
        "task_id": reuse_event["task_id"],
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "reuse_mode": reuse_event["reuse_mode"],
        "promotion_class": decision.promotion_class.value,
        "guidance_tone": decision.guidance_tone.value,
        "guidance_placement": decision.guidance_placement.value,
        "copyable": allowed,
        "worker_instruction_text": decision.summary_judgment if allowed else None,
        "operator_visible_guidance": (
            None
            if decision.guidance_placement.value == "blocked_from_worker_copy"
            else decision.summary_judgment
        ),
        "exclusion_reason": None if allowed else decision.copyable_worker_instruction.reason,
        "excluded_claims": list(decision.not_safe_to_claim),
        "reused_guidance_ids": list(reuse_event["reused_guidance_ids"]),
    }


def build_reuse_observability_row(
    decision: CompactDecisionObject,
    *,
    reuse_event: dict[str, Any],
) -> dict[str, Any]:
    """Emit the compact row that lets reviewers query reuse materiality."""

    assert_reuse_alignment(decision, reuse_event=reuse_event)
    behavior_change_class = reuse_event["behavior_change_class"]
    return {
        "schema": REUSE_OBSERVABILITY_ROW_SCHEMA,
        "coordination_session_id": decision.coordination_session_id,
        "task_id": reuse_event["task_id"],
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "reuse_mode": reuse_event["reuse_mode"],
        "behavior_change_class": behavior_change_class,
        "material_behavior_change": behavior_change_class != "shown_only",
        "behavior_change_supported": _behavior_supported(decision, behavior_change_class),
        "promotion_class": decision.promotion_class.value,
        "guidance_tone": decision.guidance_tone.value,
        "guidance_placement": decision.guidance_placement.value,
        "copyable_worker_instruction_allowed": (
            decision.copyable_worker_instruction.allowed
        ),
        "safe_to_claim": list(decision.safe_to_claim),
        "not_safe_to_claim": list(decision.not_safe_to_claim),
        "dangerous_drift_axes": list(decision.dangerous_drift_axes),
    }


def build_reuse_behavior_scoreboard(
    decision: CompactDecisionObject,
    *,
    reuse_event: dict[str, Any],
    worker_instruction_block: dict[str, Any],
    observability_row: dict[str, Any],
    supporting_evidence: Iterable[str],
    next_review_need: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Compress reuse proof into one reviewer-facing verdict object."""

    evidence = _required_str_list(supporting_evidence, "supporting_evidence")
    review_need = _optional_str_list(next_review_need, "next_review_need")
    assert_reuse_alignment(
        decision,
        reuse_event=reuse_event,
        worker_instruction_block=worker_instruction_block,
        observability_row=observability_row,
    )
    behavior_change_class = reuse_event["behavior_change_class"]
    behavior_supported = _behavior_supported(decision, behavior_change_class)
    if not behavior_supported:
        raise CityOpsContractError(
            "reuse behavior_change_class is not supported by promotion_class "
            f"({behavior_change_class!r} under {decision.promotion_class.value!r})"
        )
    overclaim_detected = _overclaim_detected(
        decision,
        reuse_event=reuse_event,
        worker_instruction_block=worker_instruction_block,
        observability_row=observability_row,
    )
    if overclaim_detected:
        raise CityOpsContractError("reuse proof detected overclaim or trust drift")

    smarter_for_right_reason = behavior_change_class != "shown_only"
    return {
        "schema": REUSE_BEHAVIOR_SCOREBOARD_SCHEMA,
        "scoreboard_id": _stable_scoreboard_id(reuse_event),
        "coordination_session_id": decision.coordination_session_id,
        "task_id": reuse_event["task_id"],
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "reuse_mode": reuse_event["reuse_mode"],
        "behavior_change_class": behavior_change_class,
        "governing_promotion_class": decision.promotion_class.value,
        "governing_guidance_tone": decision.guidance_tone.value,
        "governing_guidance_placement": decision.guidance_placement.value,
        "copyable_worker_instruction": decision.copyable_worker_instruction.allowed,
        "behavior_change_supported": behavior_supported,
        "trust_posture_preserved": True,
        "overclaim_detected": False,
        "smarter_for_right_reason": smarter_for_right_reason,
        "supporting_evidence": evidence,
        "risk_flags": [],
        "next_review_need": review_need,
        "not_safe_to_claim": list(decision.not_safe_to_claim),
    }


def assert_reuse_alignment(
    decision: CompactDecisionObject,
    *,
    reuse_event: dict[str, Any],
    worker_instruction_block: dict[str, Any] | None = None,
    observability_row: dict[str, Any] | None = None,
) -> None:
    """Fail when reuse artifacts strengthen or drop compact truth."""

    _require_equal(reuse_event.get("schema"), REUSE_EVENT_SCHEMA, "reuse_event.schema")
    _assert_identity_fields(decision, reuse_event, "reuse_event")
    _require_equal(
        reuse_event.get("promotion_class"),
        decision.promotion_class.value,
        "reuse_event.promotion_class",
    )
    _require_equal(
        reuse_event.get("guidance_tone"),
        decision.guidance_tone.value,
        "reuse_event.guidance_tone",
    )
    _require_equal(
        reuse_event.get("guidance_placement"),
        decision.guidance_placement.value,
        "reuse_event.guidance_placement",
    )
    _require_equal(
        _required_dict(reuse_event, "copyable_worker_instruction").get("allowed"),
        decision.copyable_worker_instruction.allowed,
        "reuse_event.copyable_worker_instruction.allowed",
    )
    _require_equal(
        reuse_event.get("not_safe_to_claim"),
        list(decision.not_safe_to_claim),
        "reuse_event.not_safe_to_claim",
    )
    _assert_behavior_supported(decision, reuse_event.get("behavior_change_class"))

    if worker_instruction_block is not None:
        _require_equal(
            worker_instruction_block.get("schema"),
            WORKER_INSTRUCTION_BLOCK_SCHEMA,
            "worker_instruction_block.schema",
        )
        _assert_identity_fields(decision, worker_instruction_block, "worker_instruction_block")
        _require_equal(
            worker_instruction_block.get("copyable"),
            decision.copyable_worker_instruction.allowed,
            "worker_instruction_block.copyable",
        )
        if not decision.copyable_worker_instruction.allowed:
            _require_equal(
                worker_instruction_block.get("worker_instruction_text"),
                None,
                "worker_instruction_block.worker_instruction_text",
            )
        _require_equal(
            worker_instruction_block.get("excluded_claims"),
            list(decision.not_safe_to_claim),
            "worker_instruction_block.excluded_claims",
        )

    if observability_row is not None:
        _require_equal(
            observability_row.get("schema"),
            REUSE_OBSERVABILITY_ROW_SCHEMA,
            "observability_row.schema",
        )
        _assert_identity_fields(decision, observability_row, "observability_row")
        _require_equal(
            observability_row.get("behavior_change_class"),
            reuse_event.get("behavior_change_class"),
            "observability_row.behavior_change_class",
        )
        _require_equal(
            observability_row.get("behavior_change_supported"),
            True,
            "observability_row.behavior_change_supported",
        )
        _require_equal(
            observability_row.get("not_safe_to_claim"),
            list(decision.not_safe_to_claim),
            "observability_row.not_safe_to_claim",
        )


def _assert_identity_fields(
    decision: CompactDecisionObject,
    artifact: dict[str, Any],
    label: str,
) -> None:
    for key in (
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
        "proof_anchor_id",
    ):
        _require_equal(artifact.get(key), getattr(decision, key), f"{label}.{key}")


def _assert_behavior_supported(
    decision: CompactDecisionObject,
    behavior_change_class: Any,
) -> None:
    if not isinstance(behavior_change_class, str):
        raise CityOpsContractError("behavior_change_class must be a string")
    if not _behavior_supported(decision, behavior_change_class):
        raise CityOpsContractError(
            "behavior_change_class is unsupported for promotion_class "
            f"({behavior_change_class!r} under {decision.promotion_class.value!r})"
        )


def _behavior_supported(
    decision: CompactDecisionObject,
    behavior_change_class: str,
) -> bool:
    return behavior_change_class in SUPPORTED_BEHAVIOR_BY_PROMOTION[
        decision.promotion_class
    ]


def _overclaim_detected(
    decision: CompactDecisionObject,
    *,
    reuse_event: dict[str, Any],
    worker_instruction_block: dict[str, Any],
    observability_row: dict[str, Any],
) -> bool:
    if worker_instruction_block.get("copyable") != decision.copyable_worker_instruction.allowed:
        return True
    if not decision.copyable_worker_instruction.allowed and worker_instruction_block.get(
        "worker_instruction_text"
    ):
        return True
    if reuse_event.get("not_safe_to_claim") != list(decision.not_safe_to_claim):
        return True
    if observability_row.get("not_safe_to_claim") != list(decision.not_safe_to_claim):
        return True
    return False


def _required_dict(artifact: dict[str, Any], key: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{key} must be an object")
    return value


def _required_str_list(items: Iterable[str], label: str) -> list[str]:
    values = list(items)
    if not values or any(not isinstance(item, str) or not item.strip() for item in values):
        raise CityOpsContractError(f"{label} must be a non-empty string list")
    return values


def _optional_str_list(items: Iterable[str] | None, label: str) -> list[str]:
    if items is None:
        return []
    values = list(items)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise CityOpsContractError(f"{label} must contain only non-empty strings")
    return values


def _require_non_empty_str(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CityOpsContractError(f"{label} must be a non-empty string")


def _require_allowed(value: str, allowed: set[str], label: str) -> None:
    _require_non_empty_str(value, label)
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise CityOpsContractError(
            f"{label} has unknown value {value!r}; allowed: {allowed_values}"
        )


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")


def _stable_scoreboard_id(reuse_event: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        "\n".join(
            [
                reuse_event["coordination_session_id"],
                reuse_event["task_id"],
                reuse_event["compact_decision_id"],
                reuse_event["reuse_mode"],
                reuse_event["behavior_change_class"],
            ]
        ).encode("utf-8")
    ).hexdigest()[:12]
    return f"rbps_{digest}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
