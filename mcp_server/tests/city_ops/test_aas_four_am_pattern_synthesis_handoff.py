"""Tests for the AAS 4 AM pattern-synthesis handoff."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_four_am_pattern_synthesis_handoff import (
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME,
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SCHEMA,
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_STATUS,
    PATTERN_CARDS,
    PATTERN_SYNTHESIS_BLOCKED_CLAIMS,
    PATTERN_SYNTHESIS_FALSE_FLAGS,
    build_aas_four_am_pattern_synthesis_handoff,
    load_aas_four_am_pattern_synthesis_handoff,
    write_aas_four_am_pattern_synthesis_handoff,
)
from mcp_server.city_ops.aas_no_answer_observability_rubric_fixture import (
    write_aas_no_answer_observability_rubric_fixture,
)
from mcp_server.city_ops.aas_product_exposure_boundary_candidate_review_gate import (
    write_aas_product_exposure_boundary_candidate_review_gate,
)
from mcp_server.city_ops.aas_source_of_truth_index import (
    AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
    write_aas_source_of_truth_index,
)
from mcp_server.city_ops.aas_system_integration_decision_support_map import (
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME,
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM,
    build_aas_system_integration_decision_support_map,
    write_aas_system_integration_decision_support_map,
)
from mcp_server.city_ops.aas_two_lane_no_cross_promotion_guard import (
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
    write_aas_two_lane_no_cross_promotion_guard,
)
from mcp_server.city_ops.aas_two_lane_operator_answer_schema import (
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
    ALLOWED_FUTURE_DECISIONS,
    DEFAULT_EFFECTIVE_DECISION,
    write_aas_two_lane_operator_answer_schema,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_handoff() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path, proof_tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        if source.name in {
            AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
            AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
            AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
            AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME,
            AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME,
        }:
            continue
        shutil.copy(source, tmp_path / source.name)
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, proof_tmp_path / source.name)

    write_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)
    write_aas_no_answer_observability_rubric_fixture(artifact_dir=proof_tmp_path)
    write_aas_two_lane_no_cross_promotion_guard(
        artifact_dir=tmp_path,
        no_answer_artifact_dir=proof_tmp_path,
    )
    write_aas_two_lane_operator_answer_schema(artifact_dir=tmp_path)
    write_aas_source_of_truth_index(artifact_dir=tmp_path)
    write_aas_system_integration_decision_support_map(artifact_dir=tmp_path)


def test_four_am_handoff_matches_persisted_artifact_and_loader() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()

    assert handoff == read_handoff()
    assert load_aas_four_am_pattern_synthesis_handoff() == handoff
    assert handoff["schema"] == AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SCHEMA
    assert handoff["handoff_status"] == AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_STATUS
    assert AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM in handoff[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM in handoff[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_four_am_handoff_consumes_only_decision_support_map() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()
    source = handoff["source_decision_support_map"]

    assert source["file"] == AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME
    assert source["safe_claim"] == AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM
    assert source["effective_decision"] == DEFAULT_EFFECTIVE_DECISION
    assert len(source["digest_sha256"]) == 64


def test_four_am_handoff_synthesizes_four_patterns_without_promoting_them() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()
    cards = handoff["pattern_cards"]

    assert [card["pattern"] for card in cards] == [card["pattern"] for card in PATTERN_CARDS]
    for card in cards:
        assert card["internal_admin_synthesis_only"] is True
        assert card["approved_by_this_handoff"] is False
        assert card["selected_by_this_handoff"] is False
        assert card["runtime_or_external_promotion_allowed"] is False


def test_four_am_handoff_displays_one_question_without_answering_it() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()
    question = handoff["one_question_handoff"]
    decisions = question["allowed_future_decisions"]

    assert [item["decision"] for item in decisions] == ALLOWED_FUTURE_DECISIONS
    assert question["default_if_no_human_answer"] == DEFAULT_EFFECTIVE_DECISION
    assert question["question_text_is_not_answer"] is True
    for item in decisions:
        assert item["displayed_by_this_handoff"] is True
        assert item["selected_by_this_handoff"] is False
        assert item["requires_separate_answer_record"] is True
        assert item["approval_granted_by_this_handoff"] is False


def test_four_am_handoff_records_no_answer_approval_or_external_promotion() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()

    assert handoff["current_no_answer_decision"] == {
        "operator_answer_recorded": False,
        "operator_approval_recorded": False,
        "selected_future_answer": None,
        "effective_decision": DEFAULT_EFFECTIVE_DECISION,
        "pattern_synthesis_is_approval": False,
        "handoff_is_answer_record": False,
    }
    assert handoff["readiness"]["internal_admin_four_am_handoff_landed"] is True
    assert handoff["readiness"]["pattern_cards_synthesized"] is True
    for flag, expected in PATTERN_SYNTHESIS_FALSE_FLAGS.items():
        assert handoff["readiness"][flag] is expected


def test_four_am_handoff_preserves_blocked_claim_boundaries() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()
    safe = set(handoff["claim_boundaries"]["safe_to_claim"])
    blocked = set(handoff["claim_boundaries"]["do_not_claim_yet"])

    assert set(PATTERN_SYNTHESIS_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "selects_future_answer",
        "pattern_as_approval",
        "question_as_answer",
        "approves_product_exposure",
        "runtime_memory_wiring",
        "runtime_adapter",
        "irc_session_manager",
        "live_acontext",
        "cross_project_autorouting",
        "customer_public_worker_surface",
        "dashboard_or_public_metric",
        "catalog_pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "payment_or_production",
        "exact_gps_or_raw_metadata",
        "private_context",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_four_am_handoff_preserves_stopped_project_firewall() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()
    firewall = handoff["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_four_am_handoff_guidance_is_internal_admin_only() -> None:
    handoff = build_aas_four_am_pattern_synthesis_handoff()
    guidance = handoff["operator_guidance"]

    assert guidance["first_read"] == "DREAM-PRIORITIES.md"
    assert guidance["use_this_handoff_for"] == "internal_admin_morning_pattern_synthesis_only"
    assert guidance["if_no_real_answer"] == "hold_both_lanes_or_pause_proof_layering"
    assert guidance["if_real_answer_exists"] == "create_separate_two_lane_operator_answer_record_first"
    assert guidance["do_not_extend_with_more_read_only_ceremony_unless_it_is_final_wrap"] is True
    assert guidance["not_customer_copy"] is True
    assert guidance["not_worker_instruction"] is True
    assert guidance["not_dashboard_spec"] is True


def test_four_am_handoff_write_and_load_round_trip(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)

    path = write_aas_four_am_pattern_synthesis_handoff(artifact_dir=product_tmp_path)

    assert path == product_tmp_path / AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME
    assert load_aas_four_am_pattern_synthesis_handoff(artifact_dir=product_tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_four_am_handoff_fails_closed_if_source_records_answer() -> None:
    source_map = copy.deepcopy(build_aas_system_integration_decision_support_map())
    source_map["current_no_answer_decision"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator answer"):
        build_aas_four_am_pattern_synthesis_handoff(source_decision_map=source_map)


def test_four_am_handoff_fails_closed_if_source_selects_lane_promotion() -> None:
    source_map = copy.deepcopy(build_aas_system_integration_decision_support_map())
    source_map["integration_lanes"][0]["runtime_or_external_promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="runtime_or_external_promotion_allowed"):
        build_aas_four_am_pattern_synthesis_handoff(source_decision_map=source_map)


def test_four_am_handoff_loader_fails_closed_on_promoted_fixture(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)
    handoff = build_aas_four_am_pattern_synthesis_handoff(artifact_dir=product_tmp_path)
    handoff["one_question_handoff"]["allowed_future_decisions"][0][
        "selected_by_this_handoff"
    ] = True
    (product_tmp_path / AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME).write_text(
        json.dumps(handoff), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="selected a decision"):
        load_aas_four_am_pattern_synthesis_handoff(artifact_dir=product_tmp_path)
