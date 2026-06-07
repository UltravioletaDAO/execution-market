"""Tests for the internal/admin AAS Property Ops quarantine vocabulary."""

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
from mcp_server.city_ops.aas_property_ops_blocked_claim_quarantine_vocabulary import (
    AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_FILENAME,
    AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SAFE_CLAIM,
    AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SCHEMA,
    AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_STATUS,
    FALSE_FLAGS,
    FORBIDDEN_LANGUAGE,
    PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_BLOCKED_CLAIMS,
    QUARANTINE_VOCABULARY_FIELDS,
    VOCABULARY_BOUNDARIES,
    build_aas_property_ops_blocked_claim_quarantine_vocabulary,
    load_aas_property_ops_blocked_claim_quarantine_vocabulary,
    write_aas_property_ops_blocked_claim_quarantine_vocabulary,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_vocabulary() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_property_ops_vocabulary_matches_persisted_artifact_and_loader() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()

    assert vocabulary == read_fixture_vocabulary()
    assert load_aas_property_ops_blocked_claim_quarantine_vocabulary() == vocabulary
    assert vocabulary["schema"] == AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SCHEMA
    assert vocabulary["vocabulary_status"] == AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_STATUS
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in vocabulary["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SAFE_CLAIM in vocabulary[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_property_ops_vocabulary_consumes_rank_eight_roadmap_row_by_digest() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()
    source = vocabulary["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_row_family"] == "property_ops"
    assert source["consumed_row_rank"] == 8
    assert len(source["digest_sha256"]) == 64


def test_property_ops_vocabulary_is_planning_only_not_access_authority_or_dispatch() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()

    for key, expected in FALSE_FLAGS.items():
        assert vocabulary["readiness"][key] is expected
    assert vocabulary["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "blocked_claim_quarantine_only",
    }

    fixture = vocabulary["property_ops_blocked_claim_quarantine_vocabulary"]
    assert fixture["aas_family"] == "property_ops"
    assert fixture["allowed_use"] == "internal_admin_blocked_claim_quarantine_vocabulary_only"
    assert fixture["planning_mode"] == "blocked_claim_quarantine_only"
    assert fixture["still_blocked"] is True
    assert fixture["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_explicit_operator_answer_receipt_then_property_ops_customer_or_dispatch_gate"
    )


def test_property_ops_vocabulary_preserves_quarantine_boundaries() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()
    fixture = vocabulary["property_ops_blocked_claim_quarantine_vocabulary"]

    assert set(QUARANTINE_VOCABULARY_FIELDS) <= set(
        fixture["quarantine_vocabulary_fields"]
    )
    assert set(VOCABULARY_BOUNDARIES) <= set(fixture["vocabulary_boundaries"])
    assert set(FORBIDDEN_LANGUAGE) <= set(fixture["forbidden_language"])
    assert "property ops blocked-claim quarantine vocabulary only" in fixture[
        "safe_internal_language"
    ]
    assert "property access and authority claims blocked" in fixture[
        "safe_internal_language"
    ]
    assert "exact location, private context, and raw metadata remain redacted or absent" in fixture[
        "safe_internal_language"
    ]
    assert "property access authorized" not in fixture["safe_internal_language"]
    assert "inspection complete" not in fixture["safe_internal_language"]
    assert "appraisal ready" not in fixture["safe_internal_language"]
    assert "dispatch ready" not in fixture["safe_internal_language"]


def test_property_ops_vocabulary_preserves_claim_boundaries_and_firewall() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()
    safe = set(vocabulary["claim_boundaries"]["safe_to_claim"])
    blocked = set(vocabulary["claim_boundaries"]["do_not_claim_yet"])

    assert set(PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "authorizes_property_access_site_entry_recipient_or_customer_use",
        "authorizes_inspection_appraisal_code_review_legal_review_or_worker_visit",
        "certifies_property_condition_value_compliance_or_safety",
        "commits_to_repair_remediation_maintenance_or_insurance_outcome",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert vocabulary["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_property_ops_vocabulary_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_property_ops_blocked_claim_quarantine_vocabulary(
        artifact_dir=tmp_path
    )

    assert path == tmp_path / AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_FILENAME
    assert load_aas_property_ops_blocked_claim_quarantine_vocabulary(
        artifact_dir=tmp_path
    )["vocabulary_id"] == (
        "execution_market.aas.property_ops.blocked_claim_quarantine_vocabulary.2026_06_07_0000"
    )


def test_property_ops_vocabulary_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_approval_recorded"):
        build_aas_property_ops_blocked_claim_quarantine_vocabulary(
            source_roadmap=roadmap
        )


def test_property_ops_vocabulary_rejects_property_access_authorization() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()
    vocabulary["readiness"]["vocabulary_authorizes_property_access_site_entry_or_recipient"] = True

    with pytest.raises(CityOpsContractError, match="authorizes_property_access_site_entry_or_recipient"):
        load_aas_property_ops_blocked_claim_quarantine_vocabulary(
            artifact_dir=_write_fixture_triple(vocabulary)
        )


def test_property_ops_vocabulary_rejects_property_authority() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()
    vocabulary["readiness"][
        "vocabulary_grants_property_legal_code_appraisal_insurance_or_remediation_authority"
    ] = True

    with pytest.raises(CityOpsContractError, match="grants_property_legal_code_appraisal_insurance_or_remediation_authority"):
        load_aas_property_ops_blocked_claim_quarantine_vocabulary(
            artifact_dir=_write_fixture_triple(vocabulary)
        )


def test_property_ops_vocabulary_rejects_missing_quarantine_field() -> None:
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary()
    vocabulary["property_ops_blocked_claim_quarantine_vocabulary"][
        "quarantine_vocabulary_fields"
    ] = [
        field
        for field in vocabulary["property_ops_blocked_claim_quarantine_vocabulary"][
            "quarantine_vocabulary_fields"
        ]
        if field != "code_compliance_appraisal_insurance_and_legal_claims_quarantined"
    ]

    with pytest.raises(CityOpsContractError, match="missing quarantine fields"):
        load_aas_property_ops_blocked_claim_quarantine_vocabulary(
            artifact_dir=_write_fixture_triple(vocabulary)
        )


def test_property_ops_vocabulary_rejects_wrong_source_row() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "property_ops":
            row["planning_sequence_rank"] = 9

    with pytest.raises(CityOpsContractError, match="source rank drift"):
        build_aas_property_ops_blocked_claim_quarantine_vocabulary(source_roadmap=roadmap)


def _write_fixture_triple(vocabulary: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_FILENAME).write_text(
        json.dumps(vocabulary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return tmp
