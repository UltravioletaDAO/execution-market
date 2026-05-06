import copy
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
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


def load_pair():
    return load_json_artifact(REVIEW_PACKET), load_json_artifact(FREEZE_NOTE)


def test_redirect_anchor_projects_compact_decision_deterministically():
    review_packet, freeze_note = load_pair()

    first = project_compact_decision(review_packet, freeze_note)
    second = project_compact_decision(review_packet, freeze_note)

    assert first.to_dict() == second.to_dict()
    assert first.proof_anchor_id == "redirect_outdated_packet_001"
    assert first.learning_strength.value == "cautionary"
    assert first.memory_promotion_decision.value == "promote_conservative_delta"
    assert first.promotion_class.value == "conservative_memory_delta"
    assert first.guidance_tone.value == "cautionary_or_corrective"
    assert first.guidance_placement.value == "operator_visible_before_worker_copy"
    assert first.copyable_worker_instruction.allowed is False
    assert first.continuity_ready is True
    assert first.export_ready is False
    assert first.session_rebuild_ready is False
    assert first.operator_surface_ready is True
    assert "projection_truth_landed" in first.safe_to_claim
    assert "runtime_parity_proven" in first.not_safe_to_claim
    assert "reuse_behavior_proven" in first.not_safe_to_claim
    assert "closure_proof_ready" in first.not_safe_to_claim


def test_freeze_note_drift_axes_are_carried_into_compact_object():
    review_packet, freeze_note = load_pair()

    decision = project_compact_decision(review_packet, freeze_note)

    assert decision.dangerous_drift_axes == freeze_note["dangerous_drift_axes"]
    assert "trust_inflation" in decision.dangerous_drift_axes
    assert "worker_copyability_overreach" in decision.dangerous_drift_axes
    assert decision.provenance_refs["source_fixture"] == freeze_note["source_fixture"]
    assert (
        decision.provenance_refs["proof_anchor_freeze_note"]
        == freeze_note["proof_anchor_freeze_note"]
    )


def test_missing_learning_strength_fails_loudly():
    review_packet, freeze_note = load_pair()
    broken = copy.deepcopy(review_packet)
    broken.pop("learning_strength")

    with pytest.raises(CityOpsContractError, match="learning_strength"):
        project_compact_decision(broken, freeze_note)


def test_unknown_memory_promotion_decision_fails_loudly():
    review_packet, freeze_note = load_pair()
    broken = copy.deepcopy(review_packet)
    broken["memory_promotion_decision"] = "definitely_promote_to_worker_copy"

    with pytest.raises(CityOpsContractError, match="unknown value"):
        project_compact_decision(broken, freeze_note)


def test_freeze_expectation_drift_fails_before_consumers_can_overclaim():
    review_packet, freeze_note = load_pair()
    broken = copy.deepcopy(freeze_note)
    broken["compact_decision_expectations"]["guidance_tone"] = "confident"

    with pytest.raises(CityOpsContractError, match="drifted from freeze note"):
        project_compact_decision(review_packet, broken)


def test_reviewed_outcome_class_must_match_frozen_anchor():
    review_packet, freeze_note = load_pair()
    broken = copy.deepcopy(review_packet)
    broken["reviewed_outcome_class"] = "clean_acceptance"

    with pytest.raises(CityOpsContractError, match="reviewed_outcome_class"):
        project_compact_decision(broken, freeze_note)
