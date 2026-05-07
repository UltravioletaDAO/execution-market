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
from mcp_server.city_ops.dispatch_guidance import build_dispatch_guidance_block
from mcp_server.city_ops.closure import (
    build_acontext_export_preview,
    build_session_rebuild_preview,
)
from mcp_server.city_ops.observability import build_proof_block_telemetry_gate
from mcp_server.city_ops.parity_scoreboard import (
    assert_shared_decision_parity_scoreboard,
    build_shared_decision_parity_scoreboard,
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


def build_scoreboard_artifacts():
    review_packet = load_json_artifact(REVIEW_PACKET)
    freeze_note = load_json_artifact(FREEZE_NOTE)
    decision = project_compact_decision(review_packet, freeze_note)
    ledger = build_coordination_ledger_events(
        decision,
        occurred_at="2026-05-06T08:20:00Z",
    )
    pickup = build_morning_pickup_brief(decision, ledger)
    dispatch_guidance = build_dispatch_guidance_block(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
    )
    reuse_event = build_reuse_event(
        decision,
        task_id="city_task_next_dispatch_001",
        reuse_mode="dispatch",
        behavior_change_class="routing_changed",
        reused_guidance_ids=["guidance_redirect_outdated_packet_001"],
        notes=["prior reviewed redirect learning changed operator-visible routing prep"],
        occurred_at="2026-05-06T08:21:00Z",
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
    telemetry_gate = build_proof_block_telemetry_gate(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        reuse_observability_row=reuse_row,
        reuse_behavior_scoreboard=reuse_scoreboard,
    )
    session_rebuild_preview = build_session_rebuild_preview(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
    )
    acontext_export_preview = build_acontext_export_preview(
        decision,
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
    )
    return {
        "decision": decision,
        "ledger": ledger,
        "pickup": pickup,
        "dispatch_guidance": dispatch_guidance,
        "reuse_event": reuse_event,
        "worker_block": worker_block,
        "reuse_row": reuse_row,
        "reuse_scoreboard": reuse_scoreboard,
        "telemetry_gate": telemetry_gate,
        "session_rebuild_preview": session_rebuild_preview,
        "acontext_export_preview": acontext_export_preview,
    }


def build_scoreboard(**overrides):
    artifacts = build_scoreboard_artifacts()
    artifacts.update(overrides)
    return build_shared_decision_parity_scoreboard(
        artifacts["decision"],
        ledger_events=artifacts["ledger"],
        morning_pickup_brief=artifacts["pickup"],
        dispatch_guidance_block=artifacts["dispatch_guidance"],
        reuse_event=artifacts["reuse_event"],
        worker_instruction_block=artifacts["worker_block"],
        reuse_observability_row=artifacts["reuse_row"],
        reuse_behavior_scoreboard=artifacts["reuse_scoreboard"],
        telemetry_gate=artifacts["telemetry_gate"],
        session_rebuild_preview=artifacts["session_rebuild_preview"],
        acontext_export_preview=artifacts["acontext_export_preview"],
    )


def test_shared_decision_parity_scoreboard_passes_first_replay_case():
    artifacts = build_scoreboard_artifacts()
    scoreboard = build_scoreboard(**artifacts)
    decision = artifacts["decision"]

    assert scoreboard["schema"] == "city_ops.shared_decision_parity_scoreboard.v1"
    assert scoreboard["case_id"] == "redirect_outdated_packet_001"
    assert scoreboard["semantic_parity"] == "pass"
    assert scoreboard["behavior_change"] == "routing_changed"
    assert scoreboard["trust_preservation"] == "pass"
    assert scoreboard["rebuild_parity"] == "pass"
    assert scoreboard["observability_parity"] == "pass"
    assert scoreboard["combined_verdict"] == "ship_same_seam"
    assert scoreboard["consumer_checks"]["worker_instruction_or_redispatch"] == "partial"
    assert scoreboard["invariant_field_checks"]["not_safe_to_claim"] == "pass"
    assert scoreboard["failure_triggers"] == []
    assert scoreboard["do_not_claim_yet"] == decision.not_safe_to_claim
    assert "shared_decision_parity_scoreboard_landed" in scoreboard["safe_to_claim"]
    assert scoreboard["downgrades"] == [
        {
            "consumer": "worker_instruction_or_redispatch",
            "kind": "explicit_downgrade",
            "note": "cautious reviewed city learning stayed operator-visible and non-copyable during worker-instruction rendering",
        }
    ]

    assert_shared_decision_parity_scoreboard(decision, scoreboard)


def test_scoreboard_refuses_dispatch_guidance_copyability_overreach():
    artifacts = build_scoreboard_artifacts()
    broken_dispatch = copy.deepcopy(artifacts["dispatch_guidance"])
    broken_dispatch["guidance"]["copyable_worker_instruction"]["allowed"] = True

    with pytest.raises(CityOpsContractError, match="copyable_worker_instruction"):
        build_scoreboard(**{**artifacts, "dispatch_guidance": broken_dispatch})


def test_scoreboard_marks_rebuild_preview_readiness_promotion_as_drift():
    artifacts = build_scoreboard_artifacts()
    broken_preview = copy.deepcopy(artifacts["session_rebuild_preview"])
    broken_preview["readiness"]["preview_promotes_readiness"] = True

    scoreboard = build_scoreboard(**{**artifacts, "session_rebuild_preview": broken_preview})

    assert scoreboard["semantic_parity"] == "fail"
    assert scoreboard["rebuild_parity"] == "fail"
    assert scoreboard["combined_verdict"] == "fix_drift_before_expand"
    assert "readiness_drift" in scoreboard["failure_triggers"]
