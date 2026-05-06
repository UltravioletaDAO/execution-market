import copy
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.decision_projection import (
    load_json_artifact,
    project_compact_decision,
)
from mcp_server.city_ops.reuse import (
    assert_reuse_alignment,
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


def build_reuse_artifacts():
    decision = load_decision()
    event = build_reuse_event(
        decision,
        task_id="city_task_next_dispatch_001",
        reuse_mode="dispatch",
        behavior_change_class="routing_changed",
        reused_guidance_ids=["guidance_redirect_outdated_packet_001"],
        notes=["prior redirect learning changed operator-visible routing prep"],
        occurred_at="2026-05-06T06:20:00Z",
    )
    block = build_worker_instruction_block(decision, reuse_event=event)
    row = build_reuse_observability_row(decision, reuse_event=event)
    scoreboard = build_reuse_behavior_scoreboard(
        decision,
        reuse_event=event,
        worker_instruction_block=block,
        observability_row=row,
        supporting_evidence=[
            "prior reviewed redirect episode reused",
            "dispatch routing guidance changed while staying operator-visible",
            "worker-copyable block excluded cautious municipal doctrine",
        ],
        next_review_need=[
            "one repeated redirect case needed before confident worker-copyable promotion"
        ],
    )
    return decision, event, block, row, scoreboard


def test_reuse_event_preserves_compact_decision_truth():
    decision, event, _block, _row, _scoreboard = build_reuse_artifacts()

    assert event["schema"] == "city_ops.reuse_event.v1"
    assert event["coordination_session_id"] == decision.coordination_session_id
    assert event["compact_decision_id"] == decision.compact_decision_id
    assert event["review_packet_id"] == decision.review_packet_id
    assert event["behavior_change_class"] == "routing_changed"
    assert event["promotion_class"] == "conservative_memory_delta"
    assert event["guidance_tone"] == "cautionary_or_corrective"
    assert event["guidance_placement"] == "operator_visible_before_worker_copy"
    assert event["copyable_worker_instruction"]["allowed"] is False
    assert event["not_safe_to_claim"] == decision.not_safe_to_claim
    assert "reuse_claim_without_behavior_change" in event["dangerous_drift_axes"]


def test_worker_instruction_block_filters_noncopyable_guidance():
    decision, event, block, _row, _scoreboard = build_reuse_artifacts()

    assert block["schema"] == "city_ops.worker_instruction_block.v1"
    assert block["copyable"] is False
    assert block["worker_instruction_text"] is None
    assert block["operator_visible_guidance"] == decision.summary_judgment
    assert block["excluded_claims"] == decision.not_safe_to_claim
    assert "not safe as direct worker-copyable" in block["exclusion_reason"]

    assert_reuse_alignment(
        decision,
        reuse_event=event,
        worker_instruction_block=block,
    )


def test_reuse_observability_marks_material_supported_behavior_change():
    decision, event, _block, row, _scoreboard = build_reuse_artifacts()

    assert row["schema"] == "city_ops.reuse_observability_row.v1"
    assert row["behavior_change_class"] == "routing_changed"
    assert row["material_behavior_change"] is True
    assert row["behavior_change_supported"] is True
    assert row["promotion_class"] == decision.promotion_class.value
    assert row["not_safe_to_claim"] == decision.not_safe_to_claim


def test_reuse_behavior_scoreboard_proves_right_reason_without_overclaim():
    decision, _event, _block, _row, scoreboard = build_reuse_artifacts()

    assert scoreboard["schema"] == "city_ops.reuse_behavior_scoreboard.v1"
    assert scoreboard["coordination_session_id"] == decision.coordination_session_id
    assert scoreboard["behavior_change_class"] == "routing_changed"
    assert scoreboard["governing_promotion_class"] == "conservative_memory_delta"
    assert scoreboard["copyable_worker_instruction"] is False
    assert scoreboard["behavior_change_supported"] is True
    assert scoreboard["trust_posture_preserved"] is True
    assert scoreboard["overclaim_detected"] is False
    assert scoreboard["smarter_for_right_reason"] is True
    assert scoreboard["risk_flags"] == []
    assert scoreboard["not_safe_to_claim"] == decision.not_safe_to_claim


def test_reuse_builder_refuses_instruction_change_when_copyability_is_false():
    decision = load_decision()

    with pytest.raises(CityOpsContractError, match="unsupported"):
        build_reuse_event(
            decision,
            task_id="city_task_next_dispatch_001",
            reuse_mode="dispatch",
            behavior_change_class="instruction_changed",
            reused_guidance_ids=["guidance_redirect_outdated_packet_001"],
        )


def test_reuse_alignment_fails_on_trust_upgrade():
    decision, event, _block, _row, _scoreboard = build_reuse_artifacts()
    broken_event = copy.deepcopy(event)
    broken_event["promotion_class"] = "confident_memory_delta"

    with pytest.raises(CityOpsContractError, match="promotion_class"):
        assert_reuse_alignment(decision, reuse_event=broken_event)


def test_reuse_alignment_fails_when_worker_block_leaks_copyable_text():
    decision, event, block, _row, _scoreboard = build_reuse_artifacts()
    broken_block = copy.deepcopy(block)
    broken_block["copyable"] = True
    broken_block["worker_instruction_text"] = decision.summary_judgment

    with pytest.raises(CityOpsContractError, match="copyable"):
        assert_reuse_alignment(
            decision,
            reuse_event=event,
            worker_instruction_block=broken_block,
        )


def test_reuse_alignment_fails_when_observability_drops_claim_limits():
    decision, event, _block, row, _scoreboard = build_reuse_artifacts()
    broken_row = copy.deepcopy(row)
    broken_row["not_safe_to_claim"] = ["closure_proof_ready"]

    with pytest.raises(CityOpsContractError, match="not_safe_to_claim"):
        assert_reuse_alignment(
            decision,
            reuse_event=event,
            observability_row=broken_row,
        )
