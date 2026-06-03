"""Tests for the AAS two-lane operator answer schema."""

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
from mcp_server.city_ops.aas_two_lane_no_cross_promotion_guard import (
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM,
    build_aas_two_lane_no_cross_promotion_guard,
    write_aas_two_lane_no_cross_promotion_guard,
)
from mcp_server.city_ops.aas_two_lane_operator_answer_schema import (
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM,
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SCHEMA,
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_STATUS,
    ALLOWED_FUTURE_DECISIONS,
    ANSWER_SCHEMA_BLOCKED_CLAIMS,
    ANSWER_SCHEMA_FALSE_FLAGS,
    DEFAULT_EFFECTIVE_DECISION,
    FUTURE_ANSWER_RECORD_SCHEMA,
    FUTURE_ANSWER_REQUIRED_FIELDS,
    build_aas_two_lane_operator_answer_schema,
    load_aas_two_lane_operator_answer_schema,
    write_aas_two_lane_operator_answer_schema,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_schema() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path, proof_tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        if source.name in {
            AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
            AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
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


def test_answer_schema_matches_persisted_artifact_and_loader() -> None:
    schema = build_aas_two_lane_operator_answer_schema()

    assert schema == read_schema()
    assert load_aas_two_lane_operator_answer_schema() == schema
    assert schema["schema"] == AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SCHEMA
    assert schema["schema_status"] == AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_STATUS
    assert schema["future_answer_record_schema"] == FUTURE_ANSWER_RECORD_SCHEMA
    assert AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM in schema["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM in schema["claim_boundaries"][
        "safe_to_claim"
    ]


def test_answer_schema_consumes_only_two_lane_guard_source() -> None:
    schema = build_aas_two_lane_operator_answer_schema()
    source = schema["source_guard"]

    assert source["file"] == AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME
    assert source["safe_claim"] == AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM
    assert source["default_if_no_human_answer"] == DEFAULT_EFFECTIVE_DECISION
    assert len(source["digest_sha256"]) == 64


def test_answer_schema_constrains_exactly_four_future_decisions() -> None:
    schema = build_aas_two_lane_operator_answer_schema()
    decisions = schema["allowed_future_decisions"]

    assert [item["decision"] for item in decisions] == ALLOWED_FUTURE_DECISIONS
    for item in decisions:
        assert item["allowed_in_future_record"] is True
        assert item["selected_by_this_schema"] is False
        assert item["approval_granted_by_this_schema"] is False


def test_answer_schema_requires_future_record_fields_without_satisfying_them() -> None:
    schema = build_aas_two_lane_operator_answer_schema()
    fields = schema["future_answer_required_fields"]

    assert [item["field"] for item in fields] == FUTURE_ANSWER_REQUIRED_FIELDS
    for item in fields:
        assert item["required_in_future_answer_record"] is True
        assert item["satisfied_by_this_schema"] is False


def test_answer_schema_records_no_answer_approval_or_external_promotion() -> None:
    schema = build_aas_two_lane_operator_answer_schema()

    assert schema["current_values"] == {
        "operator_answer_recorded": False,
        "operator_approval_recorded": False,
        "selected_decision": None,
        "effective_decision": DEFAULT_EFFECTIVE_DECISION,
        "option_display_is_answer": False,
        "schema_is_approval_record": False,
    }
    assert schema["readiness"]["internal_admin_answer_schema_landed"] is True
    assert schema["readiness"]["future_answer_options_constrained"] is True
    for flag, expected in ANSWER_SCHEMA_FALSE_FLAGS.items():
        assert schema["readiness"][flag] is expected


def test_answer_schema_preserves_blocked_claim_boundaries() -> None:
    schema = build_aas_two_lane_operator_answer_schema()
    safe = set(schema["claim_boundaries"]["safe_to_claim"])
    blocked = set(schema["claim_boundaries"]["do_not_claim_yet"])

    assert set(ANSWER_SCHEMA_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "option_display_as_answer",
        "retail_reality_product_exposure",
        "runtime_memory_wiring",
        "design_only_wiring",
        "bounded_activation",
        "runtime_adapter",
        "irc_session_manager",
        "live_acontext",
        "customer_public_or_worker_surface",
        "catalog_pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_context",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_answer_schema_preserves_stopped_project_firewall() -> None:
    schema = build_aas_two_lane_operator_answer_schema()
    firewall = schema["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_answer_schema_operator_guidance_is_not_customer_worker_or_dashboard_spec() -> None:
    schema = build_aas_two_lane_operator_answer_schema()
    guidance = schema["operator_guidance"]

    assert "Choose exactly one future record type" in guidance["one_question"]
    assert guidance["answer_must_be_separate_artifact"] is True
    assert guidance["do_not_mutate_this_schema_into_answer"] is True
    assert guidance["not_customer_copy"] is True
    assert guidance["not_worker_instruction"] is True
    assert guidance["not_dashboard_spec"] is True


def test_answer_schema_write_and_load_round_trip(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)

    path = write_aas_two_lane_operator_answer_schema(artifact_dir=product_tmp_path)

    assert path == product_tmp_path / AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME
    assert load_aas_two_lane_operator_answer_schema(artifact_dir=product_tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_answer_schema_fails_closed_if_source_guard_records_answer() -> None:
    guard = copy.deepcopy(build_aas_two_lane_no_cross_promotion_guard())
    guard["no_answer_state"]["explicit_operator_answer_present"] = True

    with pytest.raises(CityOpsContractError, match="explicit_operator_answer_present"):
        build_aas_two_lane_operator_answer_schema(source_guard=guard)


def test_answer_schema_fails_closed_if_source_guard_records_runtime_promotion() -> None:
    guard = copy.deepcopy(build_aas_two_lane_no_cross_promotion_guard())
    guard["readiness"]["runtime_adapter_enabled"] = True

    with pytest.raises(CityOpsContractError, match="runtime_adapter_enabled"):
        build_aas_two_lane_operator_answer_schema(source_guard=guard)


def test_answer_schema_loader_fails_closed_on_selected_decision(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)
    schema = build_aas_two_lane_operator_answer_schema(artifact_dir=product_tmp_path)
    schema["current_values"]["selected_decision"] = "keep_both_lanes_held"
    (product_tmp_path / AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME).write_text(
        json.dumps(schema), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="selected decision"):
        load_aas_two_lane_operator_answer_schema(artifact_dir=product_tmp_path)
