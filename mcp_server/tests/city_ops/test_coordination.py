import copy
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.coordination import (
    build_coordination_ledger_events,
    build_morning_pickup_brief,
    assert_carry_forward_integrity,
)
from mcp_server.city_ops.decision_projection import (
    load_json_artifact,
    project_compact_decision,
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


def test_coordination_ledger_preserves_compact_decision_truth():
    decision = load_decision()

    events = build_coordination_ledger_events(
        decision,
        occurred_at="2026-05-06T04:10:00Z",
    )

    assert [event["event_name"] for event in events] == [
        "city_compact_decision_projected",
        "city_session_rebuild_checkpoint_written",
    ]
    assert [event["event_index"] for event in events] == [1, 2]
    for event in events:
        assert event["schema"] == "city_ops.coordination_ledger_event.v1"
        assert event["coordination_session_id"] == decision.coordination_session_id
        assert event["compact_decision_id"] == decision.compact_decision_id
        assert event["review_packet_id"] == decision.review_packet_id
        assert event["proof_anchor_id"] == decision.proof_anchor_id
        assert event["promotion_class"] == decision.promotion_class.value
        assert event["guidance_tone"] == decision.guidance_tone.value
        assert event["guidance_placement"] == decision.guidance_placement.value

    projected = events[0]["payload"]
    assert projected["memory_promotion_decision"] == "promote_conservative_delta"
    assert projected["copyable_worker_instruction_allowed"] is False
    assert projected["source_episode_ids"] == [
        "reviewed_episode_redirect_outdated_packet_001"
    ]


def test_morning_pickup_brief_carries_anti_overclaim_boundaries():
    decision = load_decision()
    events = build_coordination_ledger_events(
        decision,
        occurred_at="2026-05-06T04:10:00Z",
    )

    pickup = build_morning_pickup_brief(decision, events)

    assert pickup["schema"] == "city_ops.morning_pickup_brief.v1"
    assert pickup["pickup_observation_class"] == "cautious"
    assert pickup["promotion"]["promotion_class"] == "conservative_memory_delta"
    assert pickup["promotion"]["guidance_tone"] == "cautionary_or_corrective"
    assert (
        pickup["promotion"]["guidance_placement"]
        == "operator_visible_before_worker_copy"
    )
    assert pickup["promotion"]["copyable_worker_instruction"]["allowed"] is False
    assert pickup["readiness"]["continuity_ready"] is True
    assert pickup["readiness"]["export_ready"] is False
    assert pickup["readiness"]["session_rebuild_ready"] is False
    assert "projection_truth_landed" in pickup["safe_to_claim"]
    assert "runtime_parity_proven" in pickup["not_safe_to_claim"]
    assert "reuse_claim_without_behavior_change" in pickup["dangerous_drift_axes"]
    assert pickup["ledger_event_names"] == [
        "city_compact_decision_projected",
        "city_session_rebuild_checkpoint_written",
    ]


def test_carry_forward_integrity_accepts_aligned_artifacts():
    decision = load_decision()
    events = build_coordination_ledger_events(decision)
    pickup = build_morning_pickup_brief(decision, events)

    assert_carry_forward_integrity(
        decision,
        ledger_events=events,
        morning_pickup_brief=pickup,
    )


def test_carry_forward_integrity_fails_on_guidance_tone_drift():
    decision = load_decision()
    events = build_coordination_ledger_events(decision)
    pickup = build_morning_pickup_brief(decision, events)
    broken = copy.deepcopy(pickup)
    broken["promotion"]["guidance_tone"] = "confident"

    with pytest.raises(CityOpsContractError, match="guidance_tone"):
        assert_carry_forward_integrity(
            decision,
            ledger_events=events,
            morning_pickup_brief=broken,
        )


def test_carry_forward_integrity_fails_on_ledger_join_drift():
    decision = load_decision()
    events = build_coordination_ledger_events(decision)
    broken_events = copy.deepcopy(events)
    broken_events[0]["compact_decision_id"] = "cdo_wrong"
    pickup = build_morning_pickup_brief(decision, events)

    with pytest.raises(CityOpsContractError, match="compact_decision_id"):
        assert_carry_forward_integrity(
            decision,
            ledger_events=broken_events,
            morning_pickup_brief=pickup,
        )
