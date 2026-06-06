"""Tests for the Retail Reality answer prerequisite checklist."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    build_aas_concept_gap_implementation_roadmap,
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_retail_reality_answer_prerequisite_checklist import (
    AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME,
    AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SAFE_CLAIM,
    AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SCHEMA,
    AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_STATUS,
    CHECKLIST_BLOCKED_CLAIMS,
    CHECKLIST_FALSE_FLAGS,
    EXPECTED_RANK_ONE_SLICE,
    PREREQUISITE_ROWS,
    build_aas_retail_reality_answer_prerequisite_checklist,
    load_aas_retail_reality_answer_prerequisite_checklist,
    write_aas_retail_reality_answer_prerequisite_checklist,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_checklist() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)


def test_retail_reality_answer_prerequisite_checklist_matches_persisted_artifact_and_loader() -> None:
    checklist = build_aas_retail_reality_answer_prerequisite_checklist()

    assert checklist == read_checklist()
    assert load_aas_retail_reality_answer_prerequisite_checklist() == checklist
    assert checklist["schema"] == AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SCHEMA
    assert checklist["checklist_status"] == (
        AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_STATUS
    )
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in checklist[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SAFE_CLAIM in checklist[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_retail_reality_answer_prerequisite_checklist_consumes_roadmap_by_digest() -> None:
    checklist = build_aas_retail_reality_answer_prerequisite_checklist()
    source = checklist["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert len(source["digest_sha256"]) == 64


def test_retail_reality_answer_prerequisite_checklist_freezes_rank_one_roadmap_slice() -> None:
    checklist = build_aas_retail_reality_answer_prerequisite_checklist()
    source_row = checklist["rank_one_source_row"]

    assert source_row == {
        "aas_family": "retail_reality",
        "planning_sequence_rank": 1,
        "roadmap_next_planning_slice": EXPECTED_RANK_ONE_SLICE,
        "still_blocked": True,
        "required_gate_before_any_delivery_or_runtime_movement": (
            "separate_explicit_operator_answer_receipt_then_specific_gate"
        ),
    }


def test_retail_reality_answer_prerequisite_checklist_lists_future_inputs_without_satisfying_them() -> None:
    checklist = build_aas_retail_reality_answer_prerequisite_checklist()
    rows = checklist["prerequisite_rows"]

    assert [row["check_order"] for row in rows] == list(range(1, len(PREREQUISITE_ROWS) + 1))
    assert [row["key"] for row in rows] == [row["key"] for row in PREREQUISITE_ROWS]
    assert rows[0]["key"] == "explicit_operator_answer"
    assert rows[0]["missing_default"] == "keep_both_lanes_held"
    assert rows[-1]["key"] == "runtime_and_cross_project_boundary"
    for row in rows:
        assert row["satisfied_by_this_checklist"] is False
        assert row["creates_answer_or_approval"] is False
        assert row["allows_external_or_runtime_promotion"] is False


def test_retail_reality_answer_prerequisite_checklist_records_no_answer_approval_product_or_runtime_movement() -> None:
    checklist = build_aas_retail_reality_answer_prerequisite_checklist()

    assert checklist["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "keep_both_lanes_held",
    }
    assert checklist["readiness"]["retail_reality_answer_prerequisite_checklist_landed"] is True
    for key, expected in CHECKLIST_FALSE_FLAGS.items():
        assert checklist["readiness"][key] is expected
    assert checklist["answer_record_creation_rule"] == {
        "may_create_answer_or_hold_record_from_this_checklist": False,
        "minimum_future_inputs_required": [row["key"] for row in PREREQUISITE_ROWS],
        "future_answer_must_be_separate_artifact": True,
        "missing_answer_default": "keep_both_lanes_held",
        "checklist_is_not_operator_answer": True,
        "checklist_is_not_operator_approval": True,
    }


def test_retail_reality_answer_prerequisite_checklist_preserves_claim_boundaries_and_firewall() -> None:
    checklist = build_aas_retail_reality_answer_prerequisite_checklist()
    safe = set(checklist["claim_boundaries"]["safe_to_claim"])
    blocked = set(checklist["claim_boundaries"]["do_not_claim_yet"])

    assert set(CHECKLIST_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "selects_future_answer",
        "approves_product_exposure",
        "creates_retail_reality_answer_or_hold_record",
        "customer_public_or_worker_surface",
        "catalog_pricing_quote_route_queue_or_dispatch",
        "runtime_acontext_or_irc_session_manager",
        "exact_gps_raw_metadata_or_private_context",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert checklist["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_retail_reality_answer_prerequisite_checklist_write_roundtrip(tmp_path: Path) -> None:
    seed_sources(tmp_path)

    path = write_aas_retail_reality_answer_prerequisite_checklist(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME
    assert load_aas_retail_reality_answer_prerequisite_checklist(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_retail_reality_answer_prerequisite_checklist_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["explicit_operator_answer_available"] = True

    with pytest.raises(CityOpsContractError, match="explicit_operator_answer_available"):
        build_aas_retail_reality_answer_prerequisite_checklist(source_roadmap=roadmap)


def test_retail_reality_answer_prerequisite_checklist_rejects_source_rank_drift() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["roadmap_rows"][0]["planning_sequence_rank"] = 2

    with pytest.raises(CityOpsContractError, match="rank drift"):
        build_aas_retail_reality_answer_prerequisite_checklist(source_roadmap=roadmap)


def test_retail_reality_answer_prerequisite_checklist_loader_rejects_satisfied_prerequisite(
    tmp_path: Path,
) -> None:
    seed_sources(tmp_path)
    checklist = build_aas_retail_reality_answer_prerequisite_checklist(artifact_dir=tmp_path)
    checklist["prerequisite_rows"][0]["satisfied_by_this_checklist"] = True
    (tmp_path / AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME).write_text(
        json.dumps(checklist), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="row satisfied early"):
        load_aas_retail_reality_answer_prerequisite_checklist(artifact_dir=tmp_path)


def test_retail_reality_answer_prerequisite_checklist_loader_rejects_forbidden_safe_claim(
    tmp_path: Path,
) -> None:
    seed_sources(tmp_path)
    checklist = build_aas_retail_reality_answer_prerequisite_checklist(artifact_dir=tmp_path)
    checklist["claim_boundaries"]["safe_to_claim"].append("dispatch_ready")
    (tmp_path / AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME).write_text(
        json.dumps(checklist), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_aas_retail_reality_answer_prerequisite_checklist(artifact_dir=tmp_path)
