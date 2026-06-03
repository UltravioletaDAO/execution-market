"""Tests for the AAS system-integration decision-support map."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_no_answer_observability_rubric_fixture import (
    write_aas_no_answer_observability_rubric_fixture,
)
from mcp_server.city_ops.aas_product_exposure_boundary_candidate_review_gate import (
    write_aas_product_exposure_boundary_candidate_review_gate,
)
from mcp_server.city_ops.aas_source_of_truth_index import (
    AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
    AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM,
    build_aas_source_of_truth_index,
    write_aas_source_of_truth_index,
)
from mcp_server.city_ops.aas_system_integration_decision_support_map import (
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME,
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SCHEMA,
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_STATUS,
    DECISION_SUPPORT_BLOCKED_CLAIMS,
    DECISION_SUPPORT_FALSE_FLAGS,
    INTEGRATION_LANES,
    build_aas_system_integration_decision_support_map,
    load_aas_system_integration_decision_support_map,
    write_aas_system_integration_decision_support_map,
)
from mcp_server.city_ops.aas_two_lane_no_cross_promotion_guard import (
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
    write_aas_two_lane_no_cross_promotion_guard,
)
from mcp_server.city_ops.aas_two_lane_operator_answer_schema import (
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
    DEFAULT_EFFECTIVE_DECISION,
    write_aas_two_lane_operator_answer_schema,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_map() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME).read_text(
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


def test_decision_support_map_matches_persisted_artifact_and_loader() -> None:
    decision_map = build_aas_system_integration_decision_support_map()

    assert decision_map == read_map()
    assert load_aas_system_integration_decision_support_map() == decision_map
    assert decision_map["schema"] == AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SCHEMA
    assert decision_map["map_status"] == AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_STATUS
    assert AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM in decision_map["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM in decision_map[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_decision_support_map_consumes_only_source_index() -> None:
    decision_map = build_aas_system_integration_decision_support_map()
    source = decision_map["source_index"]

    assert source["file"] == AAS_SOURCE_OF_TRUTH_INDEX_FILENAME
    assert source["safe_claim"] == AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM
    assert source["effective_decision"] == DEFAULT_EFFECTIVE_DECISION
    assert len(source["digest_sha256"]) == 64


def test_decision_support_map_connects_five_strength_lanes_without_selecting_them() -> None:
    decision_map = build_aas_system_integration_decision_support_map()
    lanes = decision_map["integration_lanes"]

    assert [lane["lane"] for lane in lanes] == [lane["lane"] for lane in INTEGRATION_LANES]
    assert {lane["lane"] for lane in lanes} == {
        "memory_acontext_readiness",
        "irc_session_management",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
        "payment_production_context",
    }
    for lane in lanes:
        assert lane["decision_support_only"] is True
        assert lane["selected_by_this_map"] is False
        assert lane["approval_granted_by_this_map"] is False
        assert lane["runtime_or_external_promotion_allowed"] is False


def test_decision_support_map_records_no_answer_approval_or_future_selection() -> None:
    decision_map = build_aas_system_integration_decision_support_map()

    assert decision_map["current_no_answer_decision"] == {
        "operator_answer_recorded": False,
        "operator_approval_recorded": False,
        "selected_future_answer": None,
        "effective_decision": DEFAULT_EFFECTIVE_DECISION,
        "lane_selection_is_approval": False,
        "map_is_answer_record": False,
    }
    assert decision_map["readiness"]["internal_admin_decision_support_map_landed"] is True
    for flag, expected in DECISION_SUPPORT_FALSE_FLAGS.items():
        assert decision_map["readiness"][flag] is expected


def test_decision_support_questions_are_unanswered_and_require_separate_records() -> None:
    decision_map = build_aas_system_integration_decision_support_map()
    questions = decision_map["decision_support_questions"]

    assert len(questions) == 3
    assert all(question["answered_by_this_map"] is False for question in questions)
    assert questions[0]["requires_separate_answer_record"] is True
    assert questions[1]["requires_separate_answer_record"] is True
    assert questions[2]["requires_separate_approval_record"] is True


def test_decision_support_map_preserves_blocked_claim_boundaries() -> None:
    decision_map = build_aas_system_integration_decision_support_map()
    safe = set(decision_map["claim_boundaries"]["safe_to_claim"])
    blocked = set(decision_map["claim_boundaries"]["do_not_claim_yet"])

    assert set(DECISION_SUPPORT_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "lane_selection_as_approval",
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


def test_decision_support_map_preserves_stopped_project_firewall() -> None:
    decision_map = build_aas_system_integration_decision_support_map()
    firewall = decision_map["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_decision_support_guidance_is_internal_admin_only() -> None:
    decision_map = build_aas_system_integration_decision_support_map()
    guidance = decision_map["operator_guidance"]

    assert guidance["first_read"] == "DREAM-PRIORITIES.md"
    assert guidance["use_this_map_for"] == "internal_admin_decision_support_only"
    assert guidance["if_no_real_answer"] == "hold_both_lanes_or_pause_proof_layering"
    assert guidance["if_real_answer_exists"] == "create_separate_two_lane_operator_answer_record_first"
    assert guidance["not_customer_copy"] is True
    assert guidance["not_worker_instruction"] is True
    assert guidance["not_dashboard_spec"] is True


def test_decision_support_map_write_and_load_round_trip(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)

    path = write_aas_system_integration_decision_support_map(artifact_dir=product_tmp_path)

    assert path == product_tmp_path / AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME
    assert load_aas_system_integration_decision_support_map(
        artifact_dir=product_tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_decision_support_map_fails_closed_if_source_records_answer() -> None:
    source_index = copy.deepcopy(build_aas_source_of_truth_index())
    source_index["current_no_answer_posture"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator answer"):
        build_aas_system_integration_decision_support_map(source_index=source_index)


def test_decision_support_map_fails_closed_if_source_selects_decision() -> None:
    source_index = copy.deepcopy(build_aas_source_of_truth_index())
    source_index["current_no_answer_posture"]["selected_decision"] = "keep_both_lanes_held"

    with pytest.raises(CityOpsContractError, match="selected decision"):
        build_aas_system_integration_decision_support_map(source_index=source_index)


def test_decision_support_loader_fails_closed_on_promoted_fixture(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)
    path = write_aas_system_integration_decision_support_map(artifact_dir=product_tmp_path)
    decision_map = json.loads(path.read_text(encoding="utf-8"))
    decision_map["readiness"]["decision_support_writes_live_acontext"] = True
    path.write_text(json.dumps(decision_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="decision_support_writes_live_acontext"):
        load_aas_system_integration_decision_support_map(artifact_dir=product_tmp_path)
