"""Shared decision parity scoreboard for City-as-a-Service proof blocks.

The existing proof-block helpers each validate one seam: compact projection,
coordination carry-forward, dispatch guidance, reuse, telemetry, and closure
previews.  This module emits the reviewer-facing scoreboard that reads those
same artifacts together and answers the product question: did one reviewed city
judgment survive every consumer without semantic drift, and did it change the
next dispatch for the right reason?
"""

from __future__ import annotations

from typing import Any, Iterable

from .closure import assert_closure_preview_artifacts
from .contracts import CityOpsContractError, CompactDecisionObject
from .coordination import assert_carry_forward_integrity
from .dispatch_guidance import assert_dispatch_guidance_parity
from .observability import assert_proof_block_telemetry_gate
from .reuse import assert_reuse_alignment

SHARED_DECISION_PARITY_SCOREBOARD_SCHEMA = (
    "city_ops.shared_decision_parity_scoreboard.v1"
)
MATERIAL_BEHAVIOR_CHANGES = {
    "routing_changed",
    "instruction_changed",
    "evidence_guidance_changed",
    "redispatch_changed",
    "escalation_changed",
}


def build_shared_decision_parity_scoreboard(
    decision: CompactDecisionObject,
    *,
    ledger_events: Iterable[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
    dispatch_guidance_block: dict[str, Any],
    reuse_event: dict[str, Any],
    worker_instruction_block: dict[str, Any],
    reuse_observability_row: dict[str, Any],
    reuse_behavior_scoreboard: dict[str, Any],
    telemetry_gate: dict[str, Any],
    session_rebuild_preview: dict[str, Any],
    acontext_export_preview: dict[str, Any],
) -> dict[str, Any]:
    """Build one parity scoreboard from the already-validated proof artifacts.

    The function intentionally reuses the stricter seam validators before it
    scores anything.  A dangerous drift should fail before a polished scoreboard
    can hide it as a low-severity note.
    """

    events = list(ledger_events)
    assert_carry_forward_integrity(
        decision,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
    )
    assert_dispatch_guidance_parity(
        decision,
        dispatch_guidance_block=dispatch_guidance_block,
        morning_pickup_brief=morning_pickup_brief,
    )
    assert_reuse_alignment(
        decision,
        reuse_event=reuse_event,
        worker_instruction_block=worker_instruction_block,
        observability_row=reuse_observability_row,
    )
    assert_proof_block_telemetry_gate(
        decision,
        telemetry_gate,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
        reuse_observability_row=reuse_observability_row,
        reuse_behavior_scoreboard=reuse_behavior_scoreboard,
    )
    assert_closure_preview_artifacts(
        decision,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
        telemetry_gate=telemetry_gate,
        session_rebuild_preview=session_rebuild_preview,
        acontext_export_preview=acontext_export_preview,
    )

    consumer_checks = _consumer_checks(
        decision,
        events=events,
        dispatch_guidance_block=dispatch_guidance_block,
        morning_pickup_brief=morning_pickup_brief,
        reuse_observability_row=reuse_observability_row,
        reuse_behavior_scoreboard=reuse_behavior_scoreboard,
        worker_instruction_block=worker_instruction_block,
        telemetry_gate=telemetry_gate,
        session_rebuild_preview=session_rebuild_preview,
        acontext_export_preview=acontext_export_preview,
    )
    invariant_field_checks = _invariant_field_checks(
        decision,
        morning_pickup_brief=morning_pickup_brief,
        dispatch_guidance_block=dispatch_guidance_block,
        reuse_observability_row=reuse_observability_row,
        telemetry_gate=telemetry_gate,
        session_rebuild_preview=session_rebuild_preview,
        acontext_export_preview=acontext_export_preview,
    )
    downgrades = _downgrades(decision, worker_instruction_block)
    failure_triggers = _failure_triggers(
        decision,
        invariant_field_checks=invariant_field_checks,
        telemetry_gate=telemetry_gate,
        reuse_behavior_scoreboard=reuse_behavior_scoreboard,
        session_rebuild_preview=session_rebuild_preview,
        acontext_export_preview=acontext_export_preview,
    )

    semantic_parity = _semantic_parity(
        consumer_checks,
        invariant_field_checks,
        failure_triggers,
    )
    behavior_change = reuse_behavior_scoreboard["behavior_change_class"]
    trust_preservation = _trust_preservation(
        reuse_behavior_scoreboard,
        telemetry_gate,
    )
    rebuild_parity = _rebuild_parity(session_rebuild_preview)
    observability_parity = _observability_parity(
        telemetry_gate,
        reuse_observability_row,
        reuse_behavior_scoreboard,
    )
    combined_verdict = _combined_verdict(
        semantic_parity=semantic_parity,
        behavior_change=behavior_change,
        trust_preservation=trust_preservation,
        rebuild_parity=rebuild_parity,
        observability_parity=observability_parity,
        failure_triggers=failure_triggers,
    )

    return {
        "schema": SHARED_DECISION_PARITY_SCOREBOARD_SCHEMA,
        "case_id": decision.proof_anchor_id,
        "coordination_session_id": decision.coordination_session_id,
        "compact_decision_id": decision.compact_decision_id,
        "review_packet_id": decision.review_packet_id,
        "semantic_parity": semantic_parity,
        "behavior_change": behavior_change,
        "trust_preservation": trust_preservation,
        "rebuild_parity": rebuild_parity,
        "observability_parity": observability_parity,
        "combined_verdict": combined_verdict,
        "consumer_checks": consumer_checks,
        "invariant_field_checks": invariant_field_checks,
        "downgrades": downgrades,
        "supported_behavior_change_reason": list(
            reuse_behavior_scoreboard.get("supporting_evidence", [])
        ),
        "failure_triggers": failure_triggers,
        "dangerous_axes_failed": list(telemetry_gate.get("dangerous_axes_failed", [])),
        "do_not_claim_yet": list(decision.not_safe_to_claim),
        "safe_to_claim": _dedupe(
            [*telemetry_gate.get("safe_to_claim", []), "shared_decision_parity_scoreboard_landed"]
        ),
        "next_smallest_proof": _dedupe(
            [
                *telemetry_gate.get("next_smallest_proof", []),
                "run the same shared-decision parity scoreboard against a second replay-backed city fixture",
            ]
        ),
        "source_artifacts": {
            "compact_decision_object": "in_memory_projection",
            "dispatch_guidance_block": dispatch_guidance_block["schema"],
            "morning_pickup_brief": morning_pickup_brief["schema"],
            "reuse_observability_row": reuse_observability_row["schema"],
            "reuse_behavior_scoreboard": reuse_behavior_scoreboard["schema"],
            "proof_block_telemetry_gate": telemetry_gate["schema"],
            "session_rebuild_preview": session_rebuild_preview["schema"],
            "acontext_export_preview": acontext_export_preview["schema"],
        },
    }


def assert_shared_decision_parity_scoreboard(
    decision: CompactDecisionObject,
    scoreboard: dict[str, Any],
) -> None:
    """Validate that a persisted scoreboard still names the same decision seam."""

    _require_equal(
        scoreboard.get("schema"),
        SHARED_DECISION_PARITY_SCOREBOARD_SCHEMA,
        "shared_decision_parity_scoreboard.schema",
    )
    for key in (
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
    ):
        _require_equal(
            scoreboard.get(key),
            getattr(decision, key),
            f"shared_decision_parity_scoreboard.{key}",
        )
    _require_equal(
        scoreboard.get("case_id"),
        decision.proof_anchor_id,
        "shared_decision_parity_scoreboard.case_id",
    )
    _require_equal(
        scoreboard.get("do_not_claim_yet"),
        list(decision.not_safe_to_claim),
        "shared_decision_parity_scoreboard.do_not_claim_yet",
    )
    if scoreboard.get("semantic_parity") == "pass" and scoreboard.get("failure_triggers"):
        raise CityOpsContractError(
            "shared_decision_parity_scoreboard cannot pass with failure_triggers"
        )


def _consumer_checks(
    decision: CompactDecisionObject,
    *,
    events: list[dict[str, Any]],
    dispatch_guidance_block: dict[str, Any],
    morning_pickup_brief: dict[str, Any],
    reuse_observability_row: dict[str, Any],
    reuse_behavior_scoreboard: dict[str, Any],
    worker_instruction_block: dict[str, Any],
    telemetry_gate: dict[str, Any],
    session_rebuild_preview: dict[str, Any],
    acontext_export_preview: dict[str, Any],
) -> dict[str, str]:
    return {
        "dispatch_brief": "pass",
        "pickup_brief": "pass",
        "memory_export": _pass_if(
            acontext_export_preview["source_read_contract"]["raw_transcript_required"] is False
            and acontext_export_preview["provenance_safe_fields"]["promotion_class"]
            == decision.promotion_class.value
        ),
        "session_rebuild": _pass_if(
            session_rebuild_preview["source_read_contract"]["raw_transcript_required"] is False
            and session_rebuild_preview["readiness"].get("preview_promotes_readiness") is False
        ),
        "runtime_observability": _pass_if(
            telemetry_gate["promotion_rendering_aligned"] is True
            and telemetry_gate["trust_preservation_result"] == "pass"
        ),
        "reuse_observability": _pass_if(
            reuse_observability_row["behavior_change_class"]
            == reuse_behavior_scoreboard["behavior_change_class"]
            and reuse_observability_row["promotion_class"] == decision.promotion_class.value
        ),
        "dispatch_reuse": _pass_if(
            reuse_behavior_scoreboard["behavior_change_supported"] is True
            and reuse_behavior_scoreboard["smarter_for_right_reason"] is True
        ),
        "worker_instruction_or_redispatch": (
            "partial"
            if not decision.copyable_worker_instruction.allowed
            and worker_instruction_block["copyable"] is False
            else "pass"
        ),
        "ledger_mirror": _pass_if(
            [event["event_name"] for event in events]
            == morning_pickup_brief["ledger_event_names"]
        ),
    }


def _invariant_field_checks(
    decision: CompactDecisionObject,
    *,
    morning_pickup_brief: dict[str, Any],
    dispatch_guidance_block: dict[str, Any],
    reuse_observability_row: dict[str, Any],
    telemetry_gate: dict[str, Any],
    session_rebuild_preview: dict[str, Any],
    acontext_export_preview: dict[str, Any],
) -> dict[str, str]:
    pickup_promotion = morning_pickup_brief["promotion"]
    dispatch_guidance = dispatch_guidance_block["guidance"]
    safe_fields = acontext_export_preview["provenance_safe_fields"]
    return {
        "promotion_class": _pass_if(
            pickup_promotion["promotion_class"]
            == dispatch_guidance_block["promotion_class"]
            == reuse_observability_row["promotion_class"]
            == safe_fields["promotion_class"]
            == decision.promotion_class.value
        ),
        "guidance_tone": _pass_if(
            pickup_promotion["guidance_tone"]
            == dispatch_guidance["tone"]
            == reuse_observability_row["guidance_tone"]
            == safe_fields["guidance_tone"]
            == decision.guidance_tone.value
        ),
        "guidance_placement": _pass_if(
            pickup_promotion["guidance_placement"]
            == dispatch_guidance["placement"]
            == reuse_observability_row["guidance_placement"]
            == safe_fields["guidance_placement"]
            == decision.guidance_placement.value
        ),
        "copyable_worker_instruction_eligibility": _pass_if(
            dispatch_guidance["copyable_worker_instruction"]["allowed"]
            == reuse_observability_row["copyable_worker_instruction_allowed"]
            == safe_fields["copyable_worker_instruction"]["allowed"]
            == decision.copyable_worker_instruction.allowed
        ),
        "continuity_ready": _pass_if(
            morning_pickup_brief["readiness"]["continuity_ready"]
            == decision.continuity_ready
        ),
        "export_ready": _pass_if(
            telemetry_gate["acontext_sink_ready"] is False
            and decision.export_ready is False
        ),
        "session_rebuild_ready": _pass_if(
            session_rebuild_preview["readiness"]["telemetry_session_rebuild_ready"]
            == telemetry_gate["session_rebuild_ready"]
            == decision.session_rebuild_ready
        ),
        "safe_to_claim": _pass_if(
            morning_pickup_brief["safe_to_claim"] == decision.safe_to_claim
        ),
        "not_safe_to_claim": _pass_if(
            morning_pickup_brief["not_safe_to_claim"]
            == telemetry_gate["do_not_claim_yet"]
            == safe_fields["not_safe_to_claim"]
            == decision.not_safe_to_claim
        ),
        "next_smallest_proof": _pass_if(
            bool(telemetry_gate.get("next_smallest_proof"))
            and bool(morning_pickup_brief.get("next_smallest_proof"))
        ),
        "provenance_refs": _pass_if(bool(safe_fields.get("provenance_refs"))),
    }


def _downgrades(
    decision: CompactDecisionObject,
    worker_instruction_block: dict[str, Any],
) -> list[dict[str, str]]:
    if decision.copyable_worker_instruction.allowed:
        return []
    if worker_instruction_block.get("copyable") is not False:
        return []
    return [
        {
            "consumer": "worker_instruction_or_redispatch",
            "kind": "explicit_downgrade",
            "note": "cautious reviewed city learning stayed operator-visible and non-copyable during worker-instruction rendering",
        }
    ]


def _failure_triggers(
    decision: CompactDecisionObject,
    *,
    invariant_field_checks: dict[str, str],
    telemetry_gate: dict[str, Any],
    reuse_behavior_scoreboard: dict[str, Any],
    session_rebuild_preview: dict[str, Any],
    acontext_export_preview: dict[str, Any],
) -> list[str]:
    triggers: list[str] = []
    trigger_by_invariant = {
        "promotion_class": "promotion_drift",
        "guidance_tone": "tone_drift",
        "guidance_placement": "placement_drift",
        "copyable_worker_instruction_eligibility": "copyability_drift",
        "not_safe_to_claim": "anti_overclaim_loss",
        "export_ready": "readiness_drift",
        "session_rebuild_ready": "readiness_drift",
        "provenance_refs": "provenance_loss",
    }
    for invariant, trigger in trigger_by_invariant.items():
        if invariant_field_checks.get(invariant) != "pass":
            triggers.append(trigger)
    if telemetry_gate.get("dangerous_axes_failed"):
        triggers.append("dangerous_axis_failed")
    if telemetry_gate.get("trust_preservation_result") != "pass":
        triggers.append("observability_trust_inflation")
    if not reuse_behavior_scoreboard.get("trust_posture_preserved"):
        triggers.append("reuse_trust_drift")
    if session_rebuild_preview["source_read_contract"].get("raw_transcript_required"):
        triggers.append("rebuild_transcript_dependency")
    if acontext_export_preview["source_read_contract"].get("raw_transcript_required"):
        triggers.append("export_transcript_dependency")
    if session_rebuild_preview["readiness"].get("preview_promotes_readiness"):
        triggers.append("readiness_drift")
    if acontext_export_preview.get("preview_promotes_readiness"):
        triggers.append("readiness_drift")
    if decision.copyable_worker_instruction.allowed is False and reuse_behavior_scoreboard.get(
        "copyable_worker_instruction"
    ):
        triggers.append("copyability_drift")
    return _dedupe(triggers)


def _semantic_parity(
    consumer_checks: dict[str, str],
    invariant_field_checks: dict[str, str],
    failure_triggers: list[str],
) -> str:
    if failure_triggers:
        return "fail"
    if any(status == "fail" for status in consumer_checks.values()):
        return "fail"
    if any(status == "fail" for status in invariant_field_checks.values()):
        return "fail"
    return "pass"


def _trust_preservation(
    reuse_behavior_scoreboard: dict[str, Any],
    telemetry_gate: dict[str, Any],
) -> str:
    if (
        reuse_behavior_scoreboard.get("trust_posture_preserved") is True
        and reuse_behavior_scoreboard.get("overclaim_detected") is False
        and telemetry_gate.get("trust_preservation_result") == "pass"
    ):
        return "pass"
    return "fail"


def _rebuild_parity(session_rebuild_preview: dict[str, Any]) -> str:
    source_contract = session_rebuild_preview["source_read_contract"]
    readiness = session_rebuild_preview["readiness"]
    if source_contract.get("raw_transcript_required"):
        return "fail"
    if readiness.get("preview_promotes_readiness"):
        return "fail"
    return "pass"


def _observability_parity(
    telemetry_gate: dict[str, Any],
    reuse_observability_row: dict[str, Any],
    reuse_behavior_scoreboard: dict[str, Any],
) -> str:
    if telemetry_gate.get("dangerous_axes_failed"):
        return "fail"
    if telemetry_gate.get("trust_preservation_result") != "pass":
        return "fail"
    if telemetry_gate.get("behavior_change_class") != reuse_observability_row.get(
        "behavior_change_class"
    ):
        return "fail"
    if telemetry_gate.get("behavior_change_class") != reuse_behavior_scoreboard.get(
        "behavior_change_class"
    ):
        return "fail"
    return "pass"


def _combined_verdict(
    *,
    semantic_parity: str,
    behavior_change: str,
    trust_preservation: str,
    rebuild_parity: str,
    observability_parity: str,
    failure_triggers: list[str],
) -> str:
    if (
        failure_triggers
        or semantic_parity == "fail"
        or trust_preservation == "fail"
        or rebuild_parity == "fail"
        or observability_parity == "fail"
    ):
        return "fix_drift_before_expand"
    if behavior_change in MATERIAL_BEHAVIOR_CHANGES and semantic_parity == "pass":
        return "ship_same_seam"
    return "tighten_same_seam"


def _pass_if(condition: bool) -> str:
    return "pass" if condition else "fail"


def _dedupe(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")
