"""Closure-preview artifacts for City-as-a-Service proof blocks.

The telemetry gate proves projection, coordination, and reuse parity can be
joined into one conservative row.  This module adds the next bounded closure
surface: previews that can be consumed by session rebuild and Acontext sinks
without reading raw transcripts, unreviewed memory, or strengthening readiness.
"""

from __future__ import annotations

from typing import Any, Iterable

from .contracts import CityOpsContractError, CompactDecisionObject
from .coordination import assert_carry_forward_integrity
from .observability import PROOF_BLOCK_TELEMETRY_GATE_SCHEMA

SESSION_REBUILD_PREVIEW_SCHEMA = "city_ops.session_rebuild_preview.v1"
ACONTEXT_EXPORT_PREVIEW_SCHEMA = "city_ops.acontext_export_preview.v1"

SESSION_REBUILD_ALLOWED_SOURCES = [
    "coordination_ledger",
    "morning_pickup_brief",
    "proof_block_telemetry_gate",
]
ACONTEXT_ALLOWED_SOURCES = [
    "compact_decision_object",
    "morning_pickup_brief",
    "proof_block_telemetry_gate",
]
FORBIDDEN_CLOSURE_SOURCES = [
    "raw_transcript",
    "unreviewed_memory",
    "freeform_worker_chat",
    "private_operator_context",
]


def build_session_rebuild_preview(
    decision: CompactDecisionObject,
    *,
    ledger_events: Iterable[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
    telemetry_gate: dict[str, Any],
) -> dict[str, Any]:
    """Build a restart/rebuild preview from ledger + pickup + telemetry only.

    This artifact is deliberately not a readiness flip.  It proves the rebuild
    surface can replay the same conservative proof block from allowed compact
    artifacts, while keeping the current readiness values bounded by the compact
    decision object and telemetry gate.
    """

    events = list(ledger_events)
    assert_carry_forward_integrity(
        decision,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
    )
    _assert_telemetry_gate_bounds(decision, telemetry_gate, events)

    event_by_name = {event["event_name"]: event for event in events}
    checkpoint_payload = event_by_name.get(
        "city_session_rebuild_checkpoint_written",
        {},
    ).get("payload", {})
    rebuild_order = list(
        checkpoint_payload.get(
            "rebuild_order",
            [
                "coordination_ledger",
                "dispatch_brief",
                "review_packet",
                "event_summary",
                "morning_pickup_brief",
            ],
        )
    )

    session_rebuild_ready = bool(telemetry_gate.get("session_rebuild_ready"))
    preview = {
        "schema": SESSION_REBUILD_PREVIEW_SCHEMA,
        "preview_id": f"session_rebuild_preview:{decision.proof_anchor_id}",
        "coordination_session_id": decision.coordination_session_id,
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "source_read_contract": {
            "allowed_sources": list(SESSION_REBUILD_ALLOWED_SOURCES),
            "forbidden_sources": list(FORBIDDEN_CLOSURE_SOURCES),
            "raw_transcript_required": False,
        },
        "ledger_event_names": [event["event_name"] for event in events],
        "rebuild_order": rebuild_order,
        "telemetry_verdict": telemetry_gate["combined_verdict"],
        "promotion": {
            "promotion_class": decision.promotion_class.value,
            "guidance_tone": decision.guidance_tone.value,
            "guidance_placement": decision.guidance_placement.value,
            "copyable_worker_instruction": (
                decision.copyable_worker_instruction.to_dict()
            ),
        },
        "readiness": {
            "decision": decision.readiness.to_dict(),
            "telemetry_session_rebuild_ready": session_rebuild_ready,
            "preview_promotes_readiness": False,
        },
        "safe_to_claim": list(telemetry_gate.get("safe_to_claim", [])),
        "not_safe_to_claim": list(decision.not_safe_to_claim),
        "next_smallest_proof": list(telemetry_gate.get("next_smallest_proof", [])),
        "preview_verdict": (
            "session_rebuild_ready"
            if session_rebuild_ready
            else "bounded_preview_only"
        ),
    }
    assert_closure_preview_artifacts(
        decision,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
        telemetry_gate=telemetry_gate,
        session_rebuild_preview=preview,
    )
    return preview


def build_acontext_export_preview(
    decision: CompactDecisionObject,
    *,
    morning_pickup_brief: dict[str, Any],
    telemetry_gate: dict[str, Any],
) -> dict[str, Any]:
    """Build a provenance-safe Acontext export preview.

    The preview exports only compact reviewed fields and explicit claim limits.
    It is safe to inspect before Docker/local Acontext is available because it
    does not require network writes and does not include raw transcripts.
    """

    _assert_pickup_identity(decision, morning_pickup_brief)
    _assert_telemetry_identity(decision, telemetry_gate)
    acontext_sink_ready = bool(telemetry_gate.get("acontext_sink_ready"))

    preview = {
        "schema": ACONTEXT_EXPORT_PREVIEW_SCHEMA,
        "export_id": f"acontext_export_preview:{decision.proof_anchor_id}",
        "coordination_session_id": decision.coordination_session_id,
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "source_read_contract": {
            "allowed_sources": list(ACONTEXT_ALLOWED_SOURCES),
            "forbidden_sources": list(FORBIDDEN_CLOSURE_SOURCES),
            "raw_transcript_required": False,
        },
        "export_status": (
            "acontext_sink_ready" if acontext_sink_ready else "preview_only"
        ),
        "preview_promotes_readiness": False,
        "namespace": "execution_market.city_ops.proof_blocks",
        "document_key": decision.proof_anchor_id,
        "provenance_safe_fields": {
            "summary_judgment": decision.summary_judgment,
            "learning_strength": decision.learning_strength.value,
            "memory_promotion_decision": decision.memory_promotion_decision.value,
            "promotion_class": decision.promotion_class.value,
            "guidance_tone": decision.guidance_tone.value,
            "guidance_placement": decision.guidance_placement.value,
            "copyable_worker_instruction": (
                decision.copyable_worker_instruction.to_dict()
            ),
            "telemetry_verdict": telemetry_gate["combined_verdict"],
            "behavior_change_class": telemetry_gate["behavior_change_class"],
            "supported_behavior_change_reason": list(
                telemetry_gate.get("supported_behavior_change_reason", [])
            ),
            "safe_to_claim": list(telemetry_gate.get("safe_to_claim", [])),
            "not_safe_to_claim": list(decision.not_safe_to_claim),
            "source_episode_ids": list(decision.source_episode_ids),
            "provenance_refs": dict(decision.provenance_refs),
        },
        "excluded_fields": list(FORBIDDEN_CLOSURE_SOURCES),
        "readiness": {
            "decision": decision.readiness.to_dict(),
            "telemetry_acontext_sink_ready": acontext_sink_ready,
        },
        "next_smallest_proof": list(telemetry_gate.get("next_smallest_proof", [])),
    }
    assert_closure_preview_artifacts(
        decision,
        ledger_events=[],
        morning_pickup_brief=morning_pickup_brief,
        telemetry_gate=telemetry_gate,
        acontext_export_preview=preview,
    )
    return preview


def assert_closure_preview_artifacts(
    decision: CompactDecisionObject,
    *,
    ledger_events: Iterable[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
    telemetry_gate: dict[str, Any],
    session_rebuild_preview: dict[str, Any] | None = None,
    acontext_export_preview: dict[str, Any] | None = None,
) -> None:
    """Validate closure previews stay bounded by compact decision truth."""

    events = list(ledger_events)
    if events:
        assert_carry_forward_integrity(
            decision,
            ledger_events=events,
            morning_pickup_brief=morning_pickup_brief,
        )
        _assert_telemetry_gate_bounds(decision, telemetry_gate, events)
    else:
        _assert_pickup_identity(decision, morning_pickup_brief)
        _assert_telemetry_identity(decision, telemetry_gate)

    for label, artifact, schema in (
        (
            "session_rebuild_preview",
            session_rebuild_preview,
            SESSION_REBUILD_PREVIEW_SCHEMA,
        ),
        (
            "acontext_export_preview",
            acontext_export_preview,
            ACONTEXT_EXPORT_PREVIEW_SCHEMA,
        ),
    ):
        if artifact is None:
            continue
        _require_equal(artifact.get("schema"), schema, f"{label}.schema")
        _assert_identity_fields(decision, artifact, label)
        _require_equal(
            artifact.get("not_safe_to_claim")
            or artifact.get("provenance_safe_fields", {}).get("not_safe_to_claim"),
            list(decision.not_safe_to_claim),
            f"{label}.not_safe_to_claim",
        )
        source_contract = _required_dict(artifact, "source_read_contract", label)
        _require_equal(
            source_contract.get("raw_transcript_required"),
            False,
            f"{label}.source_read_contract.raw_transcript_required",
        )
        forbidden_sources = source_contract.get("forbidden_sources")
        for forbidden in FORBIDDEN_CLOSURE_SOURCES:
            if forbidden not in forbidden_sources:
                raise CityOpsContractError(
                    f"{label} must forbid source {forbidden!r}"
                )
        if artifact.get("preview_promotes_readiness"):
            raise CityOpsContractError(
                f"{label} cannot promote readiness from a preview artifact"
            )

    if session_rebuild_preview is not None:
        telemetry_ready = bool(telemetry_gate.get("session_rebuild_ready"))
        preview_ready = (
            session_rebuild_preview.get("readiness", {}).get(
                "telemetry_session_rebuild_ready"
            )
        )
        _require_equal(
            preview_ready,
            telemetry_ready,
            "session_rebuild_preview.readiness.telemetry_session_rebuild_ready",
        )
        if session_rebuild_preview.get("preview_verdict") == "session_rebuild_ready":
            _require_equal(
                telemetry_ready,
                True,
                "session_rebuild_preview.preview_verdict",
            )

    if acontext_export_preview is not None:
        telemetry_ready = bool(telemetry_gate.get("acontext_sink_ready"))
        export_ready = (
            acontext_export_preview.get("readiness", {}).get(
                "telemetry_acontext_sink_ready"
            )
        )
        _require_equal(
            export_ready,
            telemetry_ready,
            "acontext_export_preview.readiness.telemetry_acontext_sink_ready",
        )
        if acontext_export_preview.get("export_status") == "acontext_sink_ready":
            _require_equal(
                telemetry_ready,
                True,
                "acontext_export_preview.export_status",
            )


def _assert_telemetry_gate_bounds(
    decision: CompactDecisionObject,
    telemetry_gate: dict[str, Any],
    ledger_events: list[dict[str, Any]],
) -> None:
    _assert_telemetry_identity(decision, telemetry_gate)
    _require_equal(
        telemetry_gate.get("ledger_event_names"),
        [event["event_name"] for event in ledger_events],
        "telemetry_gate.ledger_event_names",
    )
    if telemetry_gate.get("session_rebuild_ready") and not decision.session_rebuild_ready:
        raise CityOpsContractError(
            "telemetry_gate.session_rebuild_ready cannot exceed decision readiness"
        )
    if telemetry_gate.get("acontext_sink_ready") and not decision.export_ready:
        raise CityOpsContractError(
            "telemetry_gate.acontext_sink_ready cannot exceed export readiness"
        )


def _assert_telemetry_identity(
    decision: CompactDecisionObject,
    telemetry_gate: dict[str, Any],
) -> None:
    _require_equal(
        telemetry_gate.get("schema"),
        PROOF_BLOCK_TELEMETRY_GATE_SCHEMA,
        "telemetry_gate.schema",
    )
    _assert_identity_fields(decision, telemetry_gate, "telemetry_gate")
    _require_equal(
        telemetry_gate.get("do_not_claim_yet"),
        list(decision.not_safe_to_claim),
        "telemetry_gate.do_not_claim_yet",
    )


def _assert_pickup_identity(
    decision: CompactDecisionObject,
    morning_pickup_brief: dict[str, Any],
) -> None:
    _assert_identity_fields(decision, morning_pickup_brief, "morning_pickup_brief")
    _require_equal(
        morning_pickup_brief.get("not_safe_to_claim"),
        list(decision.not_safe_to_claim),
        "morning_pickup_brief.not_safe_to_claim",
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


def _required_dict(artifact: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{label}.{key} must be an object")
    return value


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")
