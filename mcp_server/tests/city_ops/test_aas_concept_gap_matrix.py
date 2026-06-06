"""Tests for the internal/admin AAS concept gap matrix."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_matrix import (
    AAS_CONCEPT_GAP_MATRIX_FILENAME,
    AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM,
    AAS_CONCEPT_GAP_MATRIX_SCHEMA,
    AAS_CONCEPT_GAP_MATRIX_STATUS,
    BLOCKED_CLAIMS,
    CONCEPT_ROWS,
    FALSE_FLAGS,
    SOURCE_DOCUMENTS,
    build_aas_concept_gap_matrix,
    load_aas_concept_gap_matrix,
    write_aas_concept_gap_matrix,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_matrix() -> dict:
    return json.loads((ARTIFACT_DIR / AAS_CONCEPT_GAP_MATRIX_FILENAME).read_text())


def test_concept_gap_matrix_matches_persisted_artifact_and_loader() -> None:
    matrix = build_aas_concept_gap_matrix()

    assert matrix == read_matrix()
    assert load_aas_concept_gap_matrix() == matrix
    assert matrix["schema"] == AAS_CONCEPT_GAP_MATRIX_SCHEMA
    assert matrix["matrix_status"] == AAS_CONCEPT_GAP_MATRIX_STATUS
    assert AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM in matrix["claim_boundaries"]["safe_to_claim"]


def test_concept_gap_matrix_is_source_backed_by_reviewed_planning_docs() -> None:
    matrix = build_aas_concept_gap_matrix()
    docs = matrix["source_documents"]

    assert [doc["file"] for doc in docs] == [source["file"] for source in SOURCE_DOCUMENTS]
    assert all(len(doc["digest_sha256"]) == 64 for doc in docs)
    assert all(doc["source_use"].endswith("no_private_context_no_runtime_probe") for doc in docs)


def test_concept_gap_matrix_covers_aas_families_without_no_answer_promotion() -> None:
    matrix = build_aas_concept_gap_matrix()
    rows = {row["aas_family"]: row for row in matrix["concept_gap_rows"]}

    assert set(rows) == {
        "retail_reality",
        "local_data_collection",
        "field_asset_ops",
        "event_readiness",
        "property_ops",
        "document_handoff",
        "compliance_desk",
        "incident_verification",
        "system_integration_runtime_memory",
    }
    assert rows["field_asset_ops"]["next_allowed_without_human_answer"] == "concept_outline_only"
    assert rows["event_readiness"]["next_allowed_without_human_answer"] == "concept_outline_only"
    assert rows["property_ops"]["next_allowed_without_human_answer"] == "blocked_claim_quarantine_only"
    assert rows["system_integration_runtime_memory"]["next_allowed_without_human_answer"] == "pause_aas_proof_layering"


def test_concept_gap_matrix_records_no_answer_approval_product_or_runtime_movement() -> None:
    matrix = build_aas_concept_gap_matrix()

    for key, expected in FALSE_FLAGS.items():
        assert matrix["readiness"][key] is expected
    assert matrix["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "recommended_no_human_posture": "pause_aas_proof_layering_or_keep_both_lanes_held",
        "reason": "June 5 final wrap says the useful next unit is an answer receipt only after a real explicit operator answer; this matrix is planning only.",
    }


def test_concept_gap_matrix_preserves_blocked_claims_and_firewall() -> None:
    matrix = build_aas_concept_gap_matrix()
    safe = set(matrix["claim_boundaries"]["safe_to_claim"])
    blocked = set(matrix["claim_boundaries"]["do_not_claim_yet"])

    assert set(BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "concept_gap_matrix_integrates_or_expands_stopped_projects" in blocked
    assert "concept_gap_matrix_mutates_runtime_acontext_or_irc_session_manager" in blocked
    assert "concept_gap_matrix_authorizes_catalog_pricing_quote_queue_or_dispatch" in blocked
    assert matrix["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_concept_gap_matrix_write_roundtrip(tmp_path: Path) -> None:
    path = write_aas_concept_gap_matrix(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_CONCEPT_GAP_MATRIX_FILENAME
    assert load_aas_concept_gap_matrix(artifact_dir=tmp_path)[
        "matrix_id"
    ] == "execution_market.aas.concept_gap_matrix.2026_06_05_2200"


def test_concept_gap_matrix_rejects_missing_family() -> None:
    rows = [row for row in CONCEPT_ROWS if row["aas_family"] != "property_ops"]

    with pytest.raises(CityOpsContractError, match="missing families"):
        build_aas_concept_gap_matrix(concept_rows=rows)


def test_concept_gap_matrix_rejects_without_human_promotion() -> None:
    rows = copy.deepcopy(CONCEPT_ROWS)
    rows[0]["next_allowed_without_human_answer"] = "dispatch_ready"

    with pytest.raises(CityOpsContractError, match="promotes without human answer"):
        build_aas_concept_gap_matrix(concept_rows=rows)
