"""Tests for the AAS two-lane no-cross-promotion guard."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_no_answer_observability_rubric_fixture import (
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME,
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM,
    build_aas_no_answer_observability_rubric_fixture,
    write_aas_no_answer_observability_rubric_fixture,
)
from mcp_server.city_ops.aas_product_exposure_boundary_candidate_review_gate import (
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME,
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
    SELECTED_FAMILY_ID,
    build_aas_product_exposure_boundary_candidate_review_gate,
    write_aas_product_exposure_boundary_candidate_review_gate,
)
from mcp_server.city_ops.aas_two_lane_no_cross_promotion_guard import (
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM,
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SCHEMA,
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_STATUS,
    CROSS_PROMOTION_BLOCKED_CLAIMS,
    GUARD_FALSE_FLAGS,
    GUARD_STOP_LINE,
    build_aas_two_lane_no_cross_promotion_guard,
    load_aas_two_lane_no_cross_promotion_guard,
    write_aas_two_lane_no_cross_promotion_guard,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_guard() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path, proof_tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        if source.name == AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, proof_tmp_path / source.name)

    write_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)
    write_aas_no_answer_observability_rubric_fixture(artifact_dir=proof_tmp_path)


def test_two_lane_guard_matches_persisted_artifact_and_loader() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()

    assert guard == read_guard()
    assert load_aas_two_lane_no_cross_promotion_guard() == guard
    assert guard["schema"] == AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SCHEMA
    assert guard["guard_status"] == AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_STATUS
    assert AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM in guard[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM in guard[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM in guard["claim_boundaries"][
        "safe_to_claim"
    ]


def test_two_lane_guard_links_exactly_two_sources_and_preserves_digests() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()
    sources = guard["source_artifacts"]

    assert set(sources) == {
        "no_answer_observability_rubric",
        "product_exposure_boundary_candidate_review_gate",
    }
    assert sources["no_answer_observability_rubric"]["file"] == (
        AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME
    )
    assert sources["product_exposure_boundary_candidate_review_gate"]["file"] == (
        AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME
    )
    assert sources["no_answer_observability_rubric"]["effective_decision"] == (
        "hold_no_runtime_mutation"
    )
    assert sources["product_exposure_boundary_candidate_review_gate"]["selected_family_id"] == (
        SELECTED_FAMILY_ID
    )


def test_two_lane_guard_allows_each_lane_only_its_internal_admin_output() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()
    lanes = {lane["lane"]: lane for lane in guard["lane_contracts"]}

    runtime_lane = lanes["runtime_memory_no_answer_observability"]
    assert runtime_lane["may_score_handoff_quality"] is True
    assert runtime_lane["may_approve_product_exposure"] is False
    assert runtime_lane["may_create_customer_public_worker_surface"] is False
    assert runtime_lane["may_register_or_enable_runtime_adapter"] is False
    assert runtime_lane["effective_decision"] == "hold_no_runtime_mutation"

    product_lane = lanes["retail_reality_product_exposure_candidate"]
    assert product_lane["may_select_candidate_for_human_review"] is True
    assert product_lane["may_infer_approval_from_selection"] is False
    assert product_lane["may_approve_runtime_memory_wiring"] is False
    assert product_lane["may_register_or_enable_runtime_adapter"] is False
    assert product_lane["may_create_customer_public_worker_surface"] is False


def test_two_lane_guard_cross_promotion_matrix_is_closed() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()

    assert len(guard["cross_promotion_matrix"]) == 2
    for row in guard["cross_promotion_matrix"]:
        assert row["promotion_allowed"] is False
        assert row["next_required_gate"].startswith("separate_")
    assert {
        row["forbidden_promotion"] for row in guard["cross_promotion_matrix"]
    } == {
        "rubric_score_as_product_exposure_approval",
        "candidate_selection_as_runtime_memory_wiring_approval",
    }


def test_two_lane_guard_records_no_answer_approval_or_external_promotion() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()

    assert guard["no_answer_state"] == {
        "explicit_operator_answer_present": False,
        "operator_approval_record_present": False,
        "observability_score_can_approve_product_exposure": False,
        "candidate_selection_can_approve_runtime_memory": False,
        "default_if_no_human_answer": "keep_both_lanes_held_internal_admin_only",
    }
    assert guard["readiness"]["internal_admin_guard_landed"] is True
    assert guard["readiness"]["two_lanes_separated"] is True
    for flag, expected in GUARD_FALSE_FLAGS.items():
        assert guard["readiness"][flag] is expected


def test_two_lane_guard_preserves_blocked_claim_boundaries() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()
    safe = set(guard["claim_boundaries"]["safe_to_claim"])
    blocked = set(guard["claim_boundaries"]["do_not_claim_yet"])

    assert set(CROSS_PROMOTION_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "observability_score_as_product_approval",
        "candidate_selection_as_runtime_approval",
        "retail_reality_product_exposure",
        "design_only_wiring",
        "bounded_activation",
        "runtime_adapter",
        "irc_session_manager",
        "live_acontext",
        "dashboard_or_public_metric",
        "customer_public_or_worker_surface",
        "catalog_pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_context",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_two_lane_guard_preserves_stopped_project_firewall() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()
    firewall = guard["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_two_lane_guard_stop_line_remains_fail_closed() -> None:
    guard = build_aas_two_lane_no_cross_promotion_guard()

    assert guard["operator_guidance"]["stop_line"] == GUARD_STOP_LINE
    assert "observability score cannot approve Retail Reality product exposure" in GUARD_STOP_LINE
    assert "selected Retail Reality candidate cannot approve runtime-memory wiring" in GUARD_STOP_LINE
    assert guard["operator_guidance"]["not_customer_copy"] is True
    assert guard["operator_guidance"]["not_worker_instruction"] is True
    assert guard["operator_guidance"]["not_dashboard_spec"] is True


def test_two_lane_guard_write_and_load_round_trip(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)

    path = write_aas_two_lane_no_cross_promotion_guard(
        artifact_dir=product_tmp_path,
        no_answer_artifact_dir=proof_tmp_path,
    )

    assert path == product_tmp_path / AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME
    assert load_aas_two_lane_no_cross_promotion_guard(
        artifact_dir=product_tmp_path,
        no_answer_artifact_dir=proof_tmp_path,
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_two_lane_guard_fails_closed_if_rubric_score_becomes_approval() -> None:
    rubric = copy.deepcopy(build_aas_no_answer_observability_rubric_fixture())
    gate = build_aas_product_exposure_boundary_candidate_review_gate()
    rubric["no_answer_observability_rubric"]["score_treated_as_approval"] = True

    with pytest.raises(CityOpsContractError, match="score_treated_as_approval"):
        build_aas_two_lane_no_cross_promotion_guard(
            no_answer_rubric=rubric,
            candidate_gate=gate,
        )


def test_two_lane_guard_fails_closed_if_candidate_selection_becomes_approval() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    gate = copy.deepcopy(build_aas_product_exposure_boundary_candidate_review_gate())
    gate["selection_contract"]["selection_is_approval"] = True

    with pytest.raises(CityOpsContractError, match="selection promoted selection_is_approval"):
        build_aas_two_lane_no_cross_promotion_guard(
            no_answer_rubric=rubric,
            candidate_gate=gate,
        )


def test_two_lane_guard_loader_fails_closed_on_runtime_promotion(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)
    guard = build_aas_two_lane_no_cross_promotion_guard(
        artifact_dir=product_tmp_path,
        no_answer_artifact_dir=proof_tmp_path,
    )
    guard["readiness"]["runtime_adapter_enabled"] = True
    (product_tmp_path / AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME).write_text(
        json.dumps(guard), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="readiness promoted runtime_adapter_enabled"):
        load_aas_two_lane_no_cross_promotion_guard(
            artifact_dir=product_tmp_path,
            no_answer_artifact_dir=proof_tmp_path,
        )
