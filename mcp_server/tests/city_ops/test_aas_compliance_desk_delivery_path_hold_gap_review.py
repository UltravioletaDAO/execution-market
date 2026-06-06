"""Tests for the internal/admin AAS Compliance Desk delivery-path hold gap review."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_compliance_desk_delivery_path_hold_gap_review import (
    AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_FILENAME,
    AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SAFE_CLAIM,
    AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SCHEMA,
    AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_STATUS,
    COMPLIANCE_DESK_HOLD_GAP_BLOCKED_CLAIMS,
    DELIVERY_HOLD_REASONS,
    FALSE_FLAGS,
    FORBIDDEN_LANGUAGE,
    NOTICE_PACKAGING_BOUNDARIES,
    build_aas_compliance_desk_delivery_path_hold_gap_review,
    load_aas_compliance_desk_delivery_path_hold_gap_review,
    write_aas_compliance_desk_delivery_path_hold_gap_review,
)
from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    build_aas_concept_gap_implementation_roadmap,
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_hold_gap_review() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_compliance_desk_hold_gap_review_matches_persisted_artifact_and_loader() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()

    assert review == read_hold_gap_review()
    assert load_aas_compliance_desk_delivery_path_hold_gap_review() == review
    assert review["schema"] == AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SCHEMA
    assert (
        review["hold_gap_review_status"]
        == AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_STATUS
    )
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in review["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SAFE_CLAIM in review[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_compliance_desk_hold_gap_review_consumes_rank_three_roadmap_row_by_digest() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()
    source = review["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_row_family"] == "compliance_desk"
    assert source["consumed_row_rank"] == 3
    assert len(source["digest_sha256"]) == 64


def test_compliance_desk_hold_gap_review_is_maintenance_only_not_approval_or_delivery() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()

    for key, expected in FALSE_FLAGS.items():
        assert review["readiness"][key] is expected
    assert review["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "maintenance_only_no_delivery_path",
    }

    gap = review["compliance_desk_hold_gap_review"]
    assert gap["aas_family"] == "compliance_desk"
    assert gap["allowed_use"] == "internal_admin_delivery_path_hold_gap_review_without_customer_copy"
    assert gap["maintenance_mode"] == "maintenance_only_no_delivery_path"
    assert gap["still_blocked"] is True
    assert gap["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_explicit_operator_answer_receipt_then_compliance_desk_delivery_publication_gate"
    )


def test_compliance_desk_hold_gap_review_preserves_delivery_notice_and_language_boundaries() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()
    gap = review["compliance_desk_hold_gap_review"]

    assert set(DELIVERY_HOLD_REASONS) <= set(gap["delivery_hold_reasons"])
    assert set(NOTICE_PACKAGING_BOUNDARIES) <= set(gap["notice_packaging_boundaries"])
    assert set(FORBIDDEN_LANGUAGE) <= set(gap["forbidden_language"])
    assert "delivery path remains held" in gap["safe_internal_language"]
    assert "publication route not authorized" in gap["safe_internal_language"]
    assert "regulator or legal acceptance not claimed" in gap["safe_internal_language"]
    assert "customer ready" not in gap["safe_internal_language"]
    assert "deliver to customer" not in gap["safe_internal_language"]
    assert "legally compliant" not in gap["safe_internal_language"]


def test_compliance_desk_hold_gap_review_preserves_claim_boundaries_and_firewall() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()
    safe = set(review["claim_boundaries"]["safe_to_claim"])
    blocked = set(review["claim_boundaries"]["do_not_claim_yet"])

    assert set(COMPLIANCE_DESK_HOLD_GAP_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "creates_customer_public_or_worker_copy",
        "authorizes_recipient_channel_delivery_or_acceptance",
        "authorizes_publication_or_regulator_submission_route",
        "legal_regulator_inspection_sufficiency_or_acceptance_authority",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert review["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_compliance_desk_hold_gap_review_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_compliance_desk_delivery_path_hold_gap_review(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_FILENAME
    assert load_aas_compliance_desk_delivery_path_hold_gap_review(artifact_dir=tmp_path)[
        "hold_gap_review_id"
    ] == "execution_market.aas.compliance_desk_delivery_path_hold_gap_review.2026_06_06_0100"


def test_compliance_desk_hold_gap_review_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_approval_recorded"):
        build_aas_compliance_desk_delivery_path_hold_gap_review(source_roadmap=roadmap)


def test_compliance_desk_hold_gap_review_rejects_delivery_promotion() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()
    review["readiness"]["hold_review_authorizes_delivery_path_or_recipient"] = True

    with pytest.raises(CityOpsContractError, match="authorizes_delivery_path_or_recipient"):
        load_aas_compliance_desk_delivery_path_hold_gap_review(
            artifact_dir=_write_fixture_triple(review)
        )


def test_compliance_desk_hold_gap_review_rejects_publication_promotion() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()
    review["readiness"]["hold_review_authorizes_publication_route"] = True

    with pytest.raises(CityOpsContractError, match="authorizes_publication_route"):
        load_aas_compliance_desk_delivery_path_hold_gap_review(
            artifact_dir=_write_fixture_triple(review)
        )


def test_compliance_desk_hold_gap_review_rejects_missing_delivery_hold_reason() -> None:
    review = build_aas_compliance_desk_delivery_path_hold_gap_review()
    review["compliance_desk_hold_gap_review"]["delivery_hold_reasons"] = [
        reason
        for reason in review["compliance_desk_hold_gap_review"]["delivery_hold_reasons"]
        if reason != "publication_route_not_approved"
    ]

    with pytest.raises(CityOpsContractError, match="missing hold reasons"):
        load_aas_compliance_desk_delivery_path_hold_gap_review(
            artifact_dir=_write_fixture_triple(review)
        )


def test_compliance_desk_hold_gap_review_rejects_wrong_source_row() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "compliance_desk":
            row["planning_sequence_rank"] = 4

    with pytest.raises(CityOpsContractError, match="source rank drift"):
        build_aas_compliance_desk_delivery_path_hold_gap_review(source_roadmap=roadmap)


def _write_fixture_triple(review: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_FILENAME).write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
