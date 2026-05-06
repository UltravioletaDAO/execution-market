"""Deterministic CaaS compact decision projection helper."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import (
    CityOpsContractError,
    CompactDecisionObject,
    CopyableWorkerInstruction,
    GuidancePlacement,
    GuidanceTone,
    LearningStrength,
    MemoryPromotionDecision,
    PROMOTION_POLICY,
    PromotionClass,
    ReadinessPosture,
)

REVIEW_PACKET_SCHEMA = "city_ops.review_packet.v1"
FREEZE_NOTE_SCHEMA = "city_ops.proof_anchor_freeze_note.v1"


def load_json_artifact(path: str | Path) -> dict[str, Any]:
    """Load a JSON artifact as a dictionary with loud type failure."""

    artifact_path = Path(path)
    with artifact_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise CityOpsContractError(f"{artifact_path} must contain a JSON object")
    return data


def project_compact_decision(
    review_packet: dict[str, Any],
    freeze_note: dict[str, Any],
    *,
    coordination_session_id: str | None = None,
) -> CompactDecisionObject:
    """Emit the projection-owned compact decision object for PR A.

    The function intentionally accepts plain dictionaries so replay-bundle JSON can
    be projected without a database, network, or transcript dependency.
    """

    _require_schema(review_packet, REVIEW_PACKET_SCHEMA, "review_packet")
    _require_schema(freeze_note, FREEZE_NOTE_SCHEMA, "freeze_note")

    anchor_id = _required_str(freeze_note, "anchor_id", "freeze_note")
    review_packet_id = _required_str(review_packet, "review_packet_id", "review_packet")
    summary_judgment = _required_str(review_packet, "summary_judgment", "review_packet")
    learning_strength = _required_enum(
        LearningStrength,
        review_packet,
        "learning_strength",
        "review_packet",
    )
    memory_promotion_decision = _required_enum(
        MemoryPromotionDecision,
        review_packet,
        "memory_promotion_decision",
        "review_packet",
    )
    source_episode_ids = _required_str_list(
        review_packet,
        "source_episode_ids",
        "review_packet",
    )
    dangerous_drift_axes = _required_str_list(
        freeze_note,
        "dangerous_drift_axes",
        "freeze_note",
    )

    expected = _required_dict(
        freeze_note,
        "compact_decision_expectations",
        "freeze_note",
    )
    promotion_class, guidance_tone, guidance_placement, copy_allowed = PROMOTION_POLICY[
        memory_promotion_decision
    ]
    _assert_expected(expected, "promotion_class", promotion_class.value)
    _assert_expected(expected, "guidance_tone", guidance_tone.value)
    _assert_expected(expected, "guidance_placement", guidance_placement.value)

    expected_reviewed_class = freeze_note.get("reviewed_outcome_class")
    actual_reviewed_class = review_packet.get("reviewed_outcome_class")
    if expected_reviewed_class and actual_reviewed_class != expected_reviewed_class:
        raise CityOpsContractError(
            "review_packet.reviewed_outcome_class must match "
            "freeze_note.reviewed_outcome_class "
            f"({actual_reviewed_class!r} != {expected_reviewed_class!r})"
        )

    copy_reason = _copyability_reason(
        memory_promotion_decision,
        copy_allowed,
        review_packet,
    )
    provenance_refs = _provenance_refs(review_packet, freeze_note)
    cdo_id = _stable_compact_id(anchor_id, review_packet_id, summary_judgment)

    return CompactDecisionObject(
        compact_decision_id=cdo_id,
        coordination_session_id=coordination_session_id
        or review_packet.get("coordination_session_id")
        or f"city_session_{anchor_id}",
        review_packet_id=review_packet_id,
        proof_anchor_id=anchor_id,
        summary_judgment=summary_judgment,
        learning_strength=learning_strength,
        memory_promotion_decision=memory_promotion_decision,
        promotion_class=promotion_class,
        guidance_tone=guidance_tone,
        guidance_placement=guidance_placement,
        copyable_worker_instruction=CopyableWorkerInstruction(
            allowed=copy_allowed,
            reason=copy_reason,
        ),
        readiness=ReadinessPosture(),
        next_smallest_proof=list(
            review_packet.get(
                "next_smallest_proof",
                [
                    "wire runtime consumers through this compact decision object "
                    "without strengthening trust semantics"
                ],
            )
        ),
        dangerous_drift_axes=dangerous_drift_axes,
        source_episode_ids=source_episode_ids,
        provenance_refs=provenance_refs,
    )


def _require_schema(artifact: dict[str, Any], expected: str, label: str) -> None:
    actual = artifact.get("schema")
    if actual != expected:
        raise CityOpsContractError(
            f"{label}.schema must be {expected!r}; got {actual!r}"
        )


def _required_str(artifact: dict[str, Any], key: str, label: str) -> str:
    value = artifact.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CityOpsContractError(f"{label}.{key} must be a non-empty string")
    return value


def _required_dict(artifact: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{label}.{key} must be an object")
    return value


def _required_str_list(artifact: dict[str, Any], key: str, label: str) -> list[str]:
    value = artifact.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise CityOpsContractError(f"{label}.{key} must be a non-empty string list")
    return list(value)


def _required_enum(
    enum_type: type[LearningStrength]
    | type[MemoryPromotionDecision]
    | type[PromotionClass]
    | type[GuidanceTone]
    | type[GuidancePlacement],
    artifact: dict[str, Any],
    key: str,
    label: str,
):
    raw = _required_str(artifact, key, label)
    try:
        return enum_type(raw)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise CityOpsContractError(
            f"{label}.{key} has unknown value {raw!r}; allowed: {allowed}"
        ) from exc


def _assert_expected(expected: dict[str, Any], key: str, actual: str) -> None:
    wanted = expected.get(key)
    if wanted != actual:
        raise CityOpsContractError(
            f"compact decision {key} drifted from freeze note "
            f"({actual!r} != {wanted!r})"
        )


def _copyability_reason(
    decision: MemoryPromotionDecision,
    copy_allowed: bool,
    review_packet: dict[str, Any],
) -> str:
    explicit = review_packet.get("copyability_reason")
    if isinstance(explicit, str) and explicit.strip():
        return explicit
    if copy_allowed:
        return (
            "Reviewed truth is strong enough for operator-confirmed "
            "worker-copyable guidance."
        )
    if decision == MemoryPromotionDecision.PROMOTE_CONSERVATIVE_DELTA:
        return (
            "Reviewed truth supports operator guidance but not direct "
            "worker-copyable instruction yet."
        )
    if decision == MemoryPromotionDecision.HOLD_EPISODE_ONLY:
        return (
            "Reviewed truth should remain visible for operator review, "
            "not durable instructions."
        )
    return "Reviewed truth blocks memory promotion and worker-copyable guidance."


def _provenance_refs(
    review_packet: dict[str, Any],
    freeze_note: dict[str, Any],
) -> dict[str, str]:
    refs: dict[str, str] = {}
    for source in (
        freeze_note.get("source_fixture"),
        review_packet.get("source_fixture"),
    ):
        if isinstance(source, str) and source.strip():
            refs.setdefault("source_fixture", source)
    freeze_path = freeze_note.get("proof_anchor_freeze_note") or freeze_note.get(
        "artifact_path"
    )
    if isinstance(freeze_path, str) and freeze_path.strip():
        refs["proof_anchor_freeze_note"] = freeze_path
    review_packet_path = review_packet.get("artifact_path")
    if isinstance(review_packet_path, str) and review_packet_path.strip():
        refs["review_packet"] = review_packet_path
    return refs


def _stable_compact_id(
    anchor_id: str,
    review_packet_id: str,
    summary_judgment: str,
) -> str:
    digest = hashlib.sha256(
        f"{anchor_id}\n{review_packet_id}\n{summary_judgment}".encode("utf-8")
    ).hexdigest()[:12]
    return f"cdo_{digest}"
