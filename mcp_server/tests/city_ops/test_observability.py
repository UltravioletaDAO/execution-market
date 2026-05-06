import copy
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.coordination import (
    build_coordination_ledger_events,
    build_morning_pickup_brief,
)
from mcp_server.city_ops.decision_projection import (
    load_json_artifact,
    project_compact_decision,
)
from mcp_server.city_ops.observability import (
    assert_proof_block_telemetry_gate,
    build_proof_block_telemetry_gate,
)
from mcp_server.city_ops.reuse import (
    build_reuse_behavior_scoreboard,
    build_reuse_event,
    build_reuse_observability_row,
    build_worker_instruction_block,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEW_PACKET = FIXTURES / "city_ops_review_cases" / "redirect_outdated_packet_001.json"
FREEZE_NOTE = (
    FIXTURES
    / "proof_anchors"
    / "redirect_outdated_packet_001"
    / "proof_anchor_freeze_note.json"
)


def load_decision():
    review_packet = load_json_artifact(REVIEW_PACKET)
    freeze_note = load_json_artifact(FREEZE_NOTE)
    return project_compact_decision(review_packet, freeze_note)


def build_full_gate_artifacts():
    decision = load_decision()
    ledger = build_coordination_ledger_events(
        decision,
        occurred_at="2026-05-06T07:15:00Z",
    )
    pickup = build_morning_pickup_brief(decision, ledger)
    reuse_event = build_reuse_event(
        decision,
        task_id="city_task_next_dispatch_001",
        reuse_mode="dispatch",
        behavior_change_class="routing_changed",
        reused_guidance_ids=["guidance_redirect_outdated_packet_001"],
        notes=["prior reviewed redirect learning changed operator-visible routing prep"],
        occurred_at="2026-05-06T07:16:00Z",
    )
    worker_block = build_worker_instruction_block(decision, reuse_event=reuse_event)
    reuse_row = build_reuse_observability_row(decision, reuse_event=reuse_event)
    reuse_scoreboard = build_reuse_behavior_scoreboard(
        decision,
        reuse_event=reuse_event,
        worker_instruction_block=worker_block,
        observability_row=reuse_row,
        supporting_evidence=[
            "prior reviewed redirect episode reused",
            "dispatch routing guidance changed while staying operator-visible",
            "worker-copyable block excluded cautious municipal doctrine",
        ],
        next_review_need=[
            "one repeated redirect case needed before confident worker-copyable promotion"
        ],
    )
    gate = build_proof_block_telemetry_gate(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        reuse_observability_row=reuse_row,
        reuse_behavior_scoreboard=reuse_scoreboard,
    )
    return decision, ledger, pickup, reuse_row, reuse_scoreboard, gate


def test_proof_block_telemetry_gate_joins_memory_session_reuse_and_observability():
    decision, ledger, pickup, reuse_row, reuse_scoreboard, gate = build_full_gate_artifacts()

    assert gate["schema"] == "city_ops.proof_block_telemetry_gate.v1"
    assert gate["coordination_session_id"] == decision.coordination_session_id
    assert gate["review_packet_id"] == decision.review_packet_id
    assert gate["compact_decision_id"] == decision.compact_decision_id
    assert gate["combined_verdict"] == "reuse_parity_landed"
    assert gate["behavior_change_class"] == "routing_changed"
    assert gate["reuse_mode"] == "dispatch"
    assert gate["trust_preservation_result"] == "pass"
    assert gate["promotion_rendering_aligned"] is True
    assert gate["dangerous_axes_failed"] == []
    assert gate["coordination_trace_complete"] is True
    assert gate["session_rebuild_ready"] is False
    assert gate["acontext_sink_ready"] is False
    assert gate["cross_project_event_reusable"] is True
    assert gate["explicit_downgrade_count"] == 2
    assert gate["do_not_claim_yet"] == decision.not_safe_to_claim
    assert "reuse_parity_landed" in gate["safe_to_claim"]
    assert gate["reuse_scoreboard_id"] == reuse_scoreboard["scoreboard_id"]
    assert gate["ledger_event_names"] == [event["event_name"] for event in ledger]
    assert "one repeated redirect case" in gate["next_smallest_proof"][-1]

    assert_proof_block_telemetry_gate(
        decision,
        gate,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        reuse_observability_row=reuse_row,
        reuse_behavior_scoreboard=reuse_scoreboard,
    )


def test_gate_can_emit_decision_carry_forward_without_reuse_artifacts():
    decision = load_decision()
    ledger = build_coordination_ledger_events(decision)
    pickup = build_morning_pickup_brief(decision, ledger)

    gate = build_proof_block_telemetry_gate(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
    )

    assert gate["combined_verdict"] == "decision_carry_forward_landed"
    assert gate["behavior_change_class"] == "not_emitted"
    assert gate["reuse_scoreboard_id"] is None
    assert gate["supported_behavior_change_reason"] == []
    assert gate["do_not_claim_yet"] == decision.not_safe_to_claim


def test_gate_refuses_pickup_brief_that_drops_claim_limits():
    decision, ledger, pickup, reuse_row, reuse_scoreboard, _gate = build_full_gate_artifacts()
    broken_pickup = copy.deepcopy(pickup)
    broken_pickup["not_safe_to_claim"] = ["runtime_parity_proven"]

    with pytest.raises(CityOpsContractError, match="not_safe_to_claim"):
        build_proof_block_telemetry_gate(
            decision,
            ledger_events=ledger,
            morning_pickup_brief=broken_pickup,
            reuse_observability_row=reuse_row,
            reuse_behavior_scoreboard=reuse_scoreboard,
        )


def test_gate_refuses_reuse_scoreboard_overclaim():
    decision, ledger, pickup, reuse_row, reuse_scoreboard, _gate = build_full_gate_artifacts()
    broken_scoreboard = copy.deepcopy(reuse_scoreboard)
    broken_scoreboard["overclaim_detected"] = True

    with pytest.raises(CityOpsContractError, match="overclaim"):
        build_proof_block_telemetry_gate(
            decision,
            ledger_events=ledger,
            morning_pickup_brief=pickup,
            reuse_observability_row=reuse_row,
            reuse_behavior_scoreboard=broken_scoreboard,
        )


def test_gate_refuses_reuse_behavior_class_drift():
    decision, ledger, pickup, reuse_row, reuse_scoreboard, _gate = build_full_gate_artifacts()
    broken_row = copy.deepcopy(reuse_row)
    broken_row["behavior_change_class"] = "shown_only"

    with pytest.raises(CityOpsContractError, match="behavior_change_class"):
        build_proof_block_telemetry_gate(
            decision,
            ledger_events=ledger,
            morning_pickup_brief=pickup,
            reuse_observability_row=broken_row,
            reuse_behavior_scoreboard=reuse_scoreboard,
        )
