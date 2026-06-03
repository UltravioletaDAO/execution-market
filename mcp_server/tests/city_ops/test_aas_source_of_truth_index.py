"""Tests for the AAS source-of-truth index."""

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
    AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA,
    AAS_SOURCE_OF_TRUTH_INDEX_STATUS,
    CURRENT_ENTRYPOINT_DOCS,
    HISTORICAL_CONTEXT_DOCS,
    INDEX_FALSE_FLAGS,
    SOURCE_OF_TRUTH_BLOCKED_CLAIMS,
    STALE_PATTERN_GLOBS,
    build_aas_source_of_truth_index,
    load_aas_source_of_truth_index,
    write_aas_source_of_truth_index,
)
from mcp_server.city_ops.aas_two_lane_no_cross_promotion_guard import (
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
    write_aas_two_lane_no_cross_promotion_guard,
)
from mcp_server.city_ops.aas_two_lane_operator_answer_schema import (
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM,
    DEFAULT_EFFECTIVE_DECISION,
    build_aas_two_lane_operator_answer_schema,
    write_aas_two_lane_operator_answer_schema,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_index() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_SOURCE_OF_TRUTH_INDEX_FILENAME).read_text(encoding="utf-8")
    )


def seed_sources(tmp_path: Path, proof_tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        if source.name in {
            AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
            AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
            AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
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


def test_source_of_truth_index_matches_persisted_artifact_and_loader() -> None:
    index = build_aas_source_of_truth_index()

    assert index == read_index()
    assert load_aas_source_of_truth_index() == index
    assert index["schema"] == AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA
    assert index["index_status"] == AAS_SOURCE_OF_TRUTH_INDEX_STATUS
    assert AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM in index["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM in index["claim_boundaries"][
        "safe_to_claim"
    ]


def test_source_of_truth_index_consumes_only_latest_answer_schema() -> None:
    index = build_aas_source_of_truth_index()
    source = index["source_schema"]

    assert source["file"] == AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME
    assert source["safe_claim"] == AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM
    assert source["effective_decision"] == DEFAULT_EFFECTIVE_DECISION
    assert len(source["digest_sha256"]) == 64


def test_source_of_truth_index_marks_current_entrypoints_with_digests() -> None:
    index = build_aas_source_of_truth_index()
    current = index["current_entrypoints"]

    assert [item["path"] for item in current] == [item["path"] for item in CURRENT_ENTRYPOINT_DOCS]
    for item in current:
        assert item["exists"] is True
        assert len(item["digest_sha256"]) == 64
        assert "launch" not in item["extension_policy"]


def test_source_of_truth_index_demotes_historical_docs_and_stale_patterns() -> None:
    index = build_aas_source_of_truth_index()
    historical = index["historical_context_only"]
    stale = index["stale_pattern_extension_ban_list"]

    assert [item["path"] for item in historical] == [item["path"] for item in HISTORICAL_CONTEXT_DOCS]
    for item in historical:
        assert "only" in item["historical_use"]
        assert "not" in item["ban"]
    assert [item["glob"] for item in stale] == STALE_PATTERN_GLOBS
    for item in stale:
        assert item["allowed_use"] == "historical_context_only"
        assert "do_not_extend" in item["ban"]


def test_source_of_truth_index_records_no_answer_approval_or_promotion() -> None:
    index = build_aas_source_of_truth_index()

    assert index["current_no_answer_posture"] == {
        "operator_answer_recorded": False,
        "operator_approval_recorded": False,
        "selected_decision": None,
        "effective_decision": DEFAULT_EFFECTIVE_DECISION,
        "safe_next_move_without_human_answer": (
            "hold_or_append_read_only_final_wrap_handoff; do not add product, runtime, "
            "dispatch, reputation, payment, location, private-context, authority, or stopped-project claims"
        ),
    }
    assert index["readiness"]["internal_admin_source_index_landed"] is True
    for flag, expected in INDEX_FALSE_FLAGS.items():
        assert index["readiness"][flag] is expected


def test_source_of_truth_index_preserves_claim_boundaries() -> None:
    index = build_aas_source_of_truth_index()
    safe = set(index["claim_boundaries"]["safe_to_claim"])
    blocked = set(index["claim_boundaries"]["do_not_claim_yet"])

    assert set(SOURCE_OF_TRUTH_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "treats_current_entrypoint_as_approval",
        "master_plan_to_launch_authority",
        "service_catalog_to_public_catalog",
        "stale_synthesis_to_current_driver",
        "runtime_memory_wiring",
        "customer_public_worker_surface",
        "catalog_pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_source_of_truth_index_preserves_stopped_project_firewall() -> None:
    index = build_aas_source_of_truth_index()
    firewall = index["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_source_of_truth_index_guidance_is_read_only_not_surface_spec() -> None:
    index = build_aas_source_of_truth_index()
    guidance = index["operator_guidance"]

    assert guidance["first_read"] == "DREAM-PRIORITIES.md"
    assert guidance["then_read"] == "docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md"
    assert guidance["if_no_real_answer"] == "stop_at_hold_or_read_only_final_wrap"
    assert guidance["not_customer_copy"] is True
    assert guidance["not_worker_instruction"] is True
    assert guidance["not_dashboard_spec"] is True


def test_source_of_truth_index_write_and_load_round_trip(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)

    path = write_aas_source_of_truth_index(artifact_dir=product_tmp_path)

    assert path == product_tmp_path / AAS_SOURCE_OF_TRUTH_INDEX_FILENAME
    assert load_aas_source_of_truth_index(artifact_dir=product_tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_of_truth_index_fails_closed_if_source_schema_records_answer() -> None:
    schema = copy.deepcopy(build_aas_two_lane_operator_answer_schema())
    schema["current_values"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator answer"):
        build_aas_source_of_truth_index(source_schema=schema)


def test_source_of_truth_index_fails_closed_if_source_schema_selects_decision() -> None:
    schema = copy.deepcopy(build_aas_two_lane_operator_answer_schema())
    schema["current_values"]["selected_decision"] = "pause_aas_proof_layering"

    with pytest.raises(CityOpsContractError, match="selected decision"):
        build_aas_source_of_truth_index(source_schema=schema)


def test_source_of_truth_index_loader_fails_closed_on_promoted_fixture(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)
    path = write_aas_source_of_truth_index(artifact_dir=product_tmp_path)
    index = json.loads(path.read_text(encoding="utf-8"))
    index["readiness"]["source_index_creates_customer_copy"] = True
    path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="source_index_creates_customer_copy"):
        load_aas_source_of_truth_index(artifact_dir=product_tmp_path)
