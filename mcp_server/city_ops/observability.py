"""Telemetry gate rows for City-as-a-Service proof blocks.

The projection, coordination, and reuse seams each preserve a slice of reviewed
city truth.  This module joins those slices into one compact observability row so
a later pickup, Acontext export review, IRC/session rebuild, or cross-project
control plane can inspect the same proof block without re-reading transcripts or
re-deriving trust posture.
"""

from __future__ import annotations

from typing import Any, Iterable

from .contracts import CityOpsContractError, CompactDecisionObject
from .coordination import assert_carry_forward_integrity
from .reuse import assert_reuse_alignment

PROOF_BLOCK_TELEMETRY_GATE_SCHEMA = "city_ops.proof_block_telemetry_gate.v1"


def build_proof_block_telemetry_gate(
    decision: CompactDecisionObject,
    *,
    ledger_events: Iterable[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
    reuse_observability_row: dict[str, Any] | None = None,
    reuse_behavior_scoreboard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one queryable proof-block closure row from shared decision truth.

    The row is intentionally conservative.  It can mark reuse parity as landed,
    but it refuses to infer session rebuild or Acontext readiness unless the
    underlying CompactDecisionObject already says those surfaces are ready.
    """

    events = list(ledger_events)
    assert_carry_forward_integrity(
        decision,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
    )

    behavior_change_class = "not_emitted"
    trust_preservation_result = "pass"
    supported_behavior_change_reason: list[str] = []
    reuse_mode = None
    reuse_scoreboard_id = None
    smarter_for_right_reason = False

    if reuse_observability_row is not None or reuse_behavior_scoreboard is not None:
        if reuse_observability_row is None or reuse_behavior_scoreboard is None:
            raise CityOpsContractError(
                "reuse telemetry requires both reuse_observability_row and "
                "reuse_behavior_scoreboard"
            )
        _assert_reuse_scoreboard(decision, reuse_observability_row, reuse_behavior_scoreboard)
        assert_reuse_alignment(decision, reuse_event=_reuse_event_mirror(reuse_observability_row))
        behavior_change_class = reuse_behavior_scoreboard["behavior_change_class"]
        reuse_mode = reuse_behavior_scoreboard["reuse_mode"]
        reuse_scoreboard_id = reuse_behavior_scoreboard["scoreboard_id"]
        smarter_for_right_reason = bool(
            reuse_behavior_scoreboard.get("smarter_for_right_reason")
        )
        supported_behavior_change_reason = list(
            reuse_behavior_scoreboard.get("supporting_evidence", [])
        )
        if not reuse_behavior_scoreboard.get("trust_posture_preserved"):
            trust_preservation_result = "fail"

    promotion_rendering_aligned = _promotion_rendering_aligned(
        decision,
        events,
        morning_pickup_brief,
        reuse_observability_row,
        reuse_behavior_scoreboard,
    )
    coordination_trace_complete = _coordination_trace_complete(decision, events)
    session_rebuild_ready = bool(
        decision.session_rebuild_ready and coordination_trace_complete
    )
    acontext_sink_ready = bool(decision.export_ready and coordination_trace_complete)
    cross_project_event_reusable = _cross_project_event_reusable(
        decision,
        behavior_change_class,
        promotion_rendering_aligned,
    )
    dangerous_axes_failed = _dangerous_axes_failed(
        decision,
        promotion_rendering_aligned=promotion_rendering_aligned,
        coordination_trace_complete=coordination_trace_complete,
        trust_preservation_result=trust_preservation_result,
    )
    explicit_downgrade_count = sum(
        1
        for ready in (
            session_rebuild_ready,
            acontext_sink_ready,
            cross_project_event_reusable,
        )
        if not ready
    )

    combined_verdict = _combined_verdict(
        behavior_change_class=behavior_change_class,
        smarter_for_right_reason=smarter_for_right_reason,
        trust_preservation_result=trust_preservation_result,
        dangerous_axes_failed=dangerous_axes_failed,
        session_rebuild_ready=session_rebuild_ready,
        acontext_sink_ready=acontext_sink_ready,
    )

    row = {
        "schema": PROOF_BLOCK_TELEMETRY_GATE_SCHEMA,
        "proof_block_version": "v1",
        "coordination_session_id": decision.coordination_session_id,
        "review_packet_id": decision.review_packet_id,
        "compact_decision_id": decision.compact_decision_id,
        "proof_anchor_id": decision.proof_anchor_id,
        "combined_verdict": combined_verdict,
        "behavior_change_class": behavior_change_class,
        "reuse_mode": reuse_mode,
        "trust_preservation_result": trust_preservation_result,
        "promotion_rendering_aligned": promotion_rendering_aligned,
        "dangerous_axes_failed": dangerous_axes_failed,
        "explicit_downgrade_count": explicit_downgrade_count,
        "coordination_trace_complete": coordination_trace_complete,
        "session_rebuild_ready": session_rebuild_ready,
        "acontext_sink_ready": acontext_sink_ready,
        "cross_project_event_reusable": cross_project_event_reusable,
        "supported_behavior_change_reason": supported_behavior_change_reason,
        "do_not_claim_yet": list(decision.not_safe_to_claim),
        "next_smallest_proof": _merge_lists(
            decision.next_smallest_proof,
            []
            if reuse_behavior_scoreboard is None
            else reuse_behavior_scoreboard.get("next_review_need", []),
        ),
        "safe_to_claim": _merge_lists(
            decision.safe_to_claim,
            [combined_verdict],
        ),
        "readiness": decision.readiness.to_dict(),
        "reuse_scoreboard_id": reuse_scoreboard_id,
        "ledger_event_names": [event["event_name"] for event in events],
    }
    assert_proof_block_telemetry_gate(
        decision,
        row,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
        reuse_observability_row=reuse_observability_row,
        reuse_behavior_scoreboard=reuse_behavior_scoreboard,
    )
    return row


def assert_proof_block_telemetry_gate(
    decision: CompactDecisionObject,
    telemetry_gate: dict[str, Any],
    *,
    ledger_events: Iterable[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
    reuse_observability_row: dict[str, Any] | None = None,
    reuse_behavior_scoreboard: dict[str, Any] | None = None,
) -> None:
    """Validate that the telemetry row did not strengthen or drop proof truth."""

    events = list(ledger_events)
    assert_carry_forward_integrity(
        decision,
        ledger_events=events,
        morning_pickup_brief=morning_pickup_brief,
    )
    _require_equal(
        telemetry_gate.get("schema"),
        PROOF_BLOCK_TELEMETRY_GATE_SCHEMA,
        "telemetry_gate.schema",
    )
    for key in (
        "coordination_session_id",
        "review_packet_id",
        "compact_decision_id",
        "proof_anchor_id",
    ):
        _require_equal(
            telemetry_gate.get(key),
            getattr(decision, key),
            f"telemetry_gate.{key}",
        )
    _require_equal(
        telemetry_gate.get("do_not_claim_yet"),
        list(decision.not_safe_to_claim),
        "telemetry_gate.do_not_claim_yet",
    )
    _require_equal(
        telemetry_gate.get("ledger_event_names"),
        [event["event_name"] for event in events],
        "telemetry_gate.ledger_event_names",
    )
    _require_equal(
        telemetry_gate.get("coordination_trace_complete"),
        _coordination_trace_complete(decision, events),
        "telemetry_gate.coordination_trace_complete",
    )
    if telemetry_gate.get("session_rebuild_ready") and not decision.session_rebuild_ready:
        raise CityOpsContractError(
            "telemetry_gate.session_rebuild_ready cannot exceed decision readiness"
        )
    if telemetry_gate.get("acontext_sink_ready") and not decision.export_ready:
        raise CityOpsContractError(
            "telemetry_gate.acontext_sink_ready cannot exceed export readiness"
        )
    if reuse_observability_row is None and reuse_behavior_scoreboard is None:
        _require_equal(
            telemetry_gate.get("behavior_change_class"),
            "not_emitted",
            "telemetry_gate.behavior_change_class",
        )
    else:
        if reuse_observability_row is None or reuse_behavior_scoreboard is None:
            raise CityOpsContractError("telemetry validation needs complete reuse artifacts")
        _assert_reuse_scoreboard(decision, reuse_observability_row, reuse_behavior_scoreboard)
        _require_equal(
            telemetry_gate.get("behavior_change_class"),
            reuse_behavior_scoreboard.get("behavior_change_class"),
            "telemetry_gate.behavior_change_class",
        )
        _require_equal(
            telemetry_gate.get("reuse_scoreboard_id"),
            reuse_behavior_scoreboard.get("scoreboard_id"),
            "telemetry_gate.reuse_scoreboard_id",
        )
    if telemetry_gate.get("dangerous_axes_failed"):
        _require_equal(
            telemetry_gate.get("trust_preservation_result"),
            "fail",
            "telemetry_gate.trust_preservation_result",
        )


def _assert_reuse_scoreboard(
    decision: CompactDecisionObject,
    reuse_observability_row: dict[str, Any],
    reuse_behavior_scoreboard: dict[str, Any],
) -> None:
    for artifact_name, artifact in (
        ("reuse_observability_row", reuse_observability_row),
        ("reuse_behavior_scoreboard", reuse_behavior_scoreboard),
    ):
        for key in (
            "coordination_session_id",
            "review_packet_id",
            "compact_decision_id",
            "proof_anchor_id",
        ):
            _require_equal(artifact.get(key), getattr(decision, key), f"{artifact_name}.{key}")
    _require_equal(
        reuse_observability_row.get("behavior_change_class"),
        reuse_behavior_scoreboard.get("behavior_change_class"),
        "reuse.behavior_change_class",
    )
    _require_equal(
        reuse_observability_row.get("promotion_class"),
        decision.promotion_class.value,
        "reuse_observability_row.promotion_class",
    )
    _require_equal(
        reuse_behavior_scoreboard.get("governing_promotion_class"),
        decision.promotion_class.value,
        "reuse_behavior_scoreboard.governing_promotion_class",
    )
    if reuse_behavior_scoreboard.get("overclaim_detected"):
        raise CityOpsContractError("reuse scoreboard reports overclaim_detected")


def _reuse_event_mirror(reuse_observability_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "city_ops.reuse_event.v1",
        "coordination_session_id": reuse_observability_row["coordination_session_id"],
        "task_id": reuse_observability_row["task_id"],
        "compact_decision_id": reuse_observability_row["compact_decision_id"],
        "review_packet_id": reuse_observability_row["review_packet_id"],
        "proof_anchor_id": reuse_observability_row["proof_anchor_id"],
        "reuse_mode": reuse_observability_row["reuse_mode"],
        "behavior_change_class": reuse_observability_row["behavior_change_class"],
        "promotion_class": reuse_observability_row["promotion_class"],
        "guidance_tone": reuse_observability_row["guidance_tone"],
        "guidance_placement": reuse_observability_row["guidance_placement"],
        "copyable_worker_instruction": {
            "allowed": reuse_observability_row["copyable_worker_instruction_allowed"],
        },
        "not_safe_to_claim": reuse_observability_row["not_safe_to_claim"],
    }


def _promotion_rendering_aligned(
    decision: CompactDecisionObject,
    ledger_events: list[dict[str, Any]],
    morning_pickup_brief: dict[str, Any],
    reuse_observability_row: dict[str, Any] | None,
    reuse_behavior_scoreboard: dict[str, Any] | None,
) -> bool:
    expected = (
        decision.promotion_class.value,
        decision.guidance_tone.value,
        decision.guidance_placement.value,
    )
    pickup_promotion = morning_pickup_brief.get("promotion", {})
    if (
        pickup_promotion.get("promotion_class"),
        pickup_promotion.get("guidance_tone"),
        pickup_promotion.get("guidance_placement"),
    ) != expected:
        return False
    for event in ledger_events:
        if (
            event.get("promotion_class"),
            event.get("guidance_tone"),
            event.get("guidance_placement"),
        ) != expected:
            return False
    if reuse_observability_row is not None and (
        reuse_observability_row.get("promotion_class"),
        reuse_observability_row.get("guidance_tone"),
        reuse_observability_row.get("guidance_placement"),
    ) != expected:
        return False
    if reuse_behavior_scoreboard is not None and (
        reuse_behavior_scoreboard.get("governing_promotion_class"),
        reuse_behavior_scoreboard.get("governing_guidance_tone"),
        reuse_behavior_scoreboard.get("governing_guidance_placement"),
    ) != expected:
        return False
    return True


def _coordination_trace_complete(
    decision: CompactDecisionObject, ledger_events: list[dict[str, Any]]) -> bool:
    event_names = {event.get("event_name") for event in ledger_events}
    return {
        "city_compact_decision_projected",
        "city_session_rebuild_checkpoint_written",
    }.issubset(event_names) and all(
        event.get("coordination_session_id") == decision.coordination_session_id
        for event in ledger_events
    )


def _cross_project_event_reusable(
    decision: CompactDecisionObject,
    behavior_change_class: str,
    promotion_rendering_aligned: bool,
) -> bool:
    return bool(
        promotion_rendering_aligned
        and decision.coordination_session_id
        and decision.review_packet_id
        and decision.compact_decision_id
        and behavior_change_class
    )


def _dangerous_axes_failed(
    decision: CompactDecisionObject,
    *,
    promotion_rendering_aligned: bool,
    coordination_trace_complete: bool,
    trust_preservation_result: str,
) -> list[str]:
    failed: list[str] = []
    if not promotion_rendering_aligned:
        failed.append("promotion_rendering_drift")
    if not coordination_trace_complete:
        failed.append("coordination_trace_incomplete")
    if trust_preservation_result != "pass":
        failed.extend(decision.dangerous_drift_axes)
    return _merge_lists(failed, [])


def _combined_verdict(
    *,
    behavior_change_class: str,
    smarter_for_right_reason: bool,
    trust_preservation_result: str,
    dangerous_axes_failed: list[str],
    session_rebuild_ready: bool,
    acontext_sink_ready: bool,
) -> str:
    if trust_preservation_result != "pass" or dangerous_axes_failed:
        return "blocked_by_drift"
    if behavior_change_class != "not_emitted" and smarter_for_right_reason:
        return "reuse_parity_landed"
    if session_rebuild_ready and acontext_sink_ready:
        return "portable_closure_ready"
    if session_rebuild_ready:
        return "session_rebuild_ready"
    return "decision_carry_forward_landed"


def _merge_lists(primary: Iterable[str], secondary: Iterable[str]) -> list[str]:
    merged: list[str] = []
    for item in [*list(primary), *list(secondary)]:
        if isinstance(item, str) and item and item not in merged:
            merged.append(item)
    return merged


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")
