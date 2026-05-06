import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.closure import (
    ACONTEXT_ALLOWED_SOURCES,
    FORBIDDEN_CLOSURE_SOURCES,
    SESSION_REBUILD_ALLOWED_SOURCES,
    assert_closure_preview_artifacts,
    build_acontext_export_preview,
    build_session_rebuild_preview,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.coordination import (
    build_coordination_ledger_events,
    build_morning_pickup_brief,
)
from mcp_server.city_ops.decision_projection import (
    load_json_artifact,
    project_compact_decision,
)
from mcp_server.city_ops.observability import build_proof_block_telemetry_gate
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
PROOF_BLOCK_GATE_FIXTURE = (
    FIXTURES
    / "proof_blocks"
    / "redirect_outdated_packet_001"
    / "proof_block_telemetry_gate.json"
)


def load_decision():
    review_packet = load_json_artifact(REVIEW_PACKET)
    freeze_note = load_json_artifact(FREEZE_NOTE)
    return project_compact_decision(review_packet, freeze_note)


def build_closure_artifacts():
    decision = load_decision()
    ledger = build_coordination_ledger_events(
        decision,
        occurred_at="2026-05-06T08:20:00Z",
    )
    pickup = build_morning_pickup_brief(decision, ledger)
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
    session_preview = build_session_rebuild_preview(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
    )
    acontext_preview = build_acontext_export_preview(
        decision,
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
    )
    return decision, ledger, pickup, telemetry_gate, session_preview, acontext_preview


def test_session_rebuild_preview_reads_only_ledger_pickup_and_telemetry():
    decision, ledger, pickup, telemetry_gate, session_preview, _acontext_preview = (
        build_closure_artifacts()
    )

    assert session_preview["schema"] == "city_ops.session_rebuild_preview.v1"
    assert session_preview["coordination_session_id"] == decision.coordination_session_id
    assert session_preview["source_read_contract"]["allowed_sources"] == (
        SESSION_REBUILD_ALLOWED_SOURCES
    )
    assert session_preview["source_read_contract"]["forbidden_sources"] == (
        FORBIDDEN_CLOSURE_SOURCES
    )
    assert session_preview["source_read_contract"]["raw_transcript_required"] is False
    assert session_preview["ledger_event_names"] == [
        "city_compact_decision_projected",
        "city_session_rebuild_checkpoint_written",
    ]
    assert session_preview["telemetry_verdict"] == "reuse_parity_landed"
    assert session_preview["preview_verdict"] == "bounded_preview_only"
    assert session_preview["readiness"]["telemetry_session_rebuild_ready"] is False
    assert session_preview["readiness"]["preview_promotes_readiness"] is False
    assert session_preview["not_safe_to_claim"] == decision.not_safe_to_claim

    assert_closure_preview_artifacts(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
        session_rebuild_preview=session_preview,
    )


def test_acontext_export_preview_uses_only_provenance_safe_fields():
    decision, _ledger, pickup, telemetry_gate, _session_preview, acontext_preview = (
        build_closure_artifacts()
    )

    assert acontext_preview["schema"] == "city_ops.acontext_export_preview.v1"
    assert acontext_preview["source_read_contract"]["allowed_sources"] == (
        ACONTEXT_ALLOWED_SOURCES
    )
    assert acontext_preview["source_read_contract"]["forbidden_sources"] == (
        FORBIDDEN_CLOSURE_SOURCES
    )
    assert acontext_preview["source_read_contract"]["raw_transcript_required"] is False
    assert acontext_preview["export_status"] == "preview_only"
    assert acontext_preview["preview_promotes_readiness"] is False
    safe_fields = acontext_preview["provenance_safe_fields"]
    assert safe_fields["telemetry_verdict"] == "reuse_parity_landed"
    assert safe_fields["not_safe_to_claim"] == decision.not_safe_to_claim
    assert safe_fields["copyable_worker_instruction"]["allowed"] is False
    assert "raw_transcript" not in safe_fields
    assert "private_operator_context" not in safe_fields

    assert_closure_preview_artifacts(
        decision,
        ledger_events=[],
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
        acontext_export_preview=acontext_preview,
    )


def test_closure_previews_refuse_readiness_overclaim_from_telemetry_gate():
    decision, ledger, pickup, telemetry_gate, _session_preview, _acontext_preview = (
        build_closure_artifacts()
    )
    broken_gate = copy.deepcopy(telemetry_gate)
    broken_gate["session_rebuild_ready"] = True

    with pytest.raises(CityOpsContractError, match="session_rebuild_ready"):
        build_session_rebuild_preview(
            decision,
            ledger_events=ledger,
            morning_pickup_brief=pickup,
            telemetry_gate=broken_gate,
        )


def test_closure_previews_refuse_source_contract_that_requires_raw_transcript():
    decision, ledger, pickup, telemetry_gate, session_preview, _acontext_preview = (
        build_closure_artifacts()
    )
    broken_preview = copy.deepcopy(session_preview)
    broken_preview["source_read_contract"]["raw_transcript_required"] = True

    with pytest.raises(CityOpsContractError, match="raw_transcript_required"):
        assert_closure_preview_artifacts(
            decision,
            ledger_events=ledger,
            morning_pickup_brief=pickup,
            telemetry_gate=telemetry_gate,
            session_rebuild_preview=broken_preview,
        )


def test_proof_block_telemetry_gate_fixture_matches_builder_output():
    _decision, _ledger, _pickup, telemetry_gate, _session_preview, _acontext_preview = (
        build_closure_artifacts()
    )

    with PROOF_BLOCK_GATE_FIXTURE.open("r", encoding="utf-8") as fh:
        fixture_gate = json.load(fh)

    assert fixture_gate == telemetry_gate
