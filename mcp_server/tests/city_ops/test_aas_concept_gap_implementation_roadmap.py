"""Tests for the internal/admin AAS concept-gap implementation roadmap."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS,
    FALSE_FLAGS,
    ROADMAP_BLOCKED_CLAIMS,
    build_aas_concept_gap_implementation_roadmap,
    load_aas_concept_gap_implementation_roadmap,
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import (
    AAS_CONCEPT_GAP_MATRIX_FILENAME,
    AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM,
    build_aas_concept_gap_matrix,
    write_aas_concept_gap_matrix,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_roadmap() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_concept_gap_implementation_roadmap_matches_persisted_artifact_and_loader() -> None:
    roadmap = build_aas_concept_gap_implementation_roadmap()

    assert roadmap == read_roadmap()
    assert load_aas_concept_gap_implementation_roadmap() == roadmap
    assert roadmap["schema"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA
    assert roadmap["roadmap_status"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS
    assert AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM in roadmap["claim_boundaries"]["safe_to_claim"]
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in roadmap["claim_boundaries"][
        "safe_to_claim"
    ]


def test_concept_gap_implementation_roadmap_consumes_gap_matrix_by_digest() -> None:
    roadmap = build_aas_concept_gap_implementation_roadmap()
    source = roadmap["source_matrix"]

    assert source["file"] == AAS_CONCEPT_GAP_MATRIX_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM
    assert len(source["digest_sha256"]) == 64


def test_concept_gap_implementation_roadmap_orders_all_lanes_as_planning_only() -> None:
    roadmap = build_aas_concept_gap_implementation_roadmap()
    rows = roadmap["roadmap_rows"]

    assert [row["planning_sequence_rank"] for row in rows] == list(range(1, 10))
    assert [row["aas_family"] for row in rows] == [
        "retail_reality",
        "document_handoff",
        "compliance_desk",
        "field_asset_ops",
        "event_readiness",
        "incident_verification",
        "local_data_collection",
        "property_ops",
        "system_integration_runtime_memory",
    ]
    assert rows[0]["roadmap_next_planning_slice"] == (
        "answer_receipt_prerequisite_checklist_only_if_explicit_operator_answer_arrives"
    )
    assert rows[3]["roadmap_next_planning_slice"] == (
        "visible_asset_state_fixture_outline_no_repair_or_sla_language"
    )
    assert rows[-1]["roadmap_next_planning_slice"] == (
        "read_only_runtime_prerequisite_inventory_only_after_explicit_runtime_memory_answer"
    )
    assert all(row["still_blocked"] is True for row in rows)
    assert all(
        row["required_gate_before_any_delivery_or_runtime_movement"]
        == "separate_explicit_operator_answer_receipt_then_specific_gate"
        for row in rows
    )


def test_concept_gap_implementation_roadmap_records_no_answer_approval_product_or_runtime_movement() -> None:
    roadmap = build_aas_concept_gap_implementation_roadmap()

    for key, expected in FALSE_FLAGS.items():
        assert roadmap["readiness"][key] is expected
    assert roadmap["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "pause_aas_proof_layering_or_keep_both_lanes_held",
    }


def test_concept_gap_implementation_roadmap_preserves_claim_boundaries_and_firewall() -> None:
    roadmap = build_aas_concept_gap_implementation_roadmap()
    safe = set(roadmap["claim_boundaries"]["safe_to_claim"])
    blocked = set(roadmap["claim_boundaries"]["do_not_claim_yet"])

    assert set(ROADMAP_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "treats_sequence_rank_as_approval",
        "customer_public_or_worker_surface",
        "catalog_pricing_quote_route_queue_or_dispatch",
        "runtime_acontext_or_irc_session_manager",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert roadmap["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_concept_gap_implementation_roadmap_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    path = write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert load_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)["roadmap_id"] == (
        "execution_market.aas.concept_gap_implementation_roadmap.2026_06_05_2300"
    )


def test_concept_gap_implementation_roadmap_rejects_promoted_source_matrix() -> None:
    matrix = copy.deepcopy(build_aas_concept_gap_matrix())
    matrix["current_operator_state"]["answer_receipt_created"] = True

    with pytest.raises(CityOpsContractError, match="answer_receipt_created"):
        build_aas_concept_gap_implementation_roadmap(source_matrix=matrix)


def test_concept_gap_implementation_roadmap_rejects_unblocked_row() -> None:
    roadmap = build_aas_concept_gap_implementation_roadmap()
    roadmap["roadmap_rows"][0]["still_blocked"] = False

    with pytest.raises(CityOpsContractError, match="row unblocked"):
        load_aas_concept_gap_implementation_roadmap(artifact_dir=_write_fixture_pair(roadmap))


def _write_fixture_pair(roadmap: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    (tmp / AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME).write_text(
        json.dumps(roadmap, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
