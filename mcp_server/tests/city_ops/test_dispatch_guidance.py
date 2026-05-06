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
from mcp_server.city_ops.dispatch_guidance import (
    assert_dispatch_guidance_parity,
    build_dispatch_guidance_block,
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


def build_artifacts():
    decision = load_decision()
    events = build_coordination_ledger_events(
        decision,
        occurred_at="2026-05-06T05:25:00Z",
    )
    pickup = build_morning_pickup_brief(decision, events)
    guidance = build_dispatch_guidance_block(
        decision,
        ledger_events=events,
        morning_pickup_brief=pickup,
    )
    return decision, events, pickup, guidance


def test_dispatch_guidance_block_reads_compact_decision_truth():
    decision, events, pickup, guidance = build_artifacts()

    assert guidance["schema"] == "city_ops.dispatch_guidance_block.v1"
    assert guidance["runtime_consumer"] == "dispatch_brief_composer"
    assert guidance["coordination_session_id"] == decision.coordination_session_id
    assert guidance["compact_decision_id"] == decision.compact_decision_id
    assert guidance["promotion_class"] == "conservative_memory_delta"
    assert guidance["guidance"]["tone"] == "cautionary_or_corrective"
    assert (
        guidance["guidance"]["placement"]
        == "operator_visible_before_worker_copy"
    )
    assert guidance["guidance"]["copyable_worker_instruction"]["allowed"] is False
    assert guidance["guidance"]["worker_instruction_text"] is None
    assert "must stay visible" in guidance["guidance"]["operator_preface"]
    assert guidance["claim_limits"]["not_safe_to_claim"] == decision.not_safe_to_claim
    assert guidance["claim_limits"]["dangerous_drift_axes"] == (
        decision.dangerous_drift_axes
    )
    assert guidance["pickup_observation_class"] == pickup["pickup_observation_class"]
    assert guidance["ledger_event_names"] == [event["event_name"] for event in events]


def test_dispatch_guidance_parity_accepts_aligned_consumer_block():
    decision, _events, pickup, guidance = build_artifacts()

    assert_dispatch_guidance_parity(
        decision,
        dispatch_guidance_block=guidance,
        morning_pickup_brief=pickup,
    )


def test_dispatch_guidance_builder_refuses_drifted_pickup_brief():
    decision = load_decision()
    events = build_coordination_ledger_events(decision)
    pickup = build_morning_pickup_brief(decision, events)
    broken_pickup = copy.deepcopy(pickup)
    broken_pickup["promotion"]["guidance_placement"] = (
        "worker_copyable_after_operator_confirm"
    )

    with pytest.raises(CityOpsContractError, match="guidance_placement"):
        build_dispatch_guidance_block(
            decision,
            ledger_events=events,
            morning_pickup_brief=broken_pickup,
        )


def test_dispatch_guidance_parity_fails_on_worker_copyability_overreach():
    decision, _events, pickup, guidance = build_artifacts()
    broken_guidance = copy.deepcopy(guidance)
    broken_guidance["guidance"]["copyable_worker_instruction"]["allowed"] = True
    broken_guidance["guidance"]["worker_instruction_text"] = decision.summary_judgment

    with pytest.raises(CityOpsContractError, match="copyable_worker_instruction"):
        assert_dispatch_guidance_parity(
            decision,
            dispatch_guidance_block=broken_guidance,
            morning_pickup_brief=pickup,
        )


def test_dispatch_guidance_parity_fails_when_consumer_drops_claim_limits():
    decision, _events, pickup, guidance = build_artifacts()
    broken_guidance = copy.deepcopy(guidance)
    broken_guidance["claim_limits"]["not_safe_to_claim"] = ["closure_proof_ready"]

    with pytest.raises(CityOpsContractError, match="not_safe_to_claim"):
        assert_dispatch_guidance_parity(
            decision,
            dispatch_guidance_block=broken_guidance,
            morning_pickup_brief=pickup,
        )
