"""Tests for the internal/admin AAS Incident Verification observation/uncertainty maintenance."""

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
from mcp_server.city_ops.aas_incident_verification_observation_uncertainty_maintenance import (
    AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_FILENAME,
    AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SAFE_CLAIM,
    AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SCHEMA,
    AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_STATUS,
    FALSE_FLAGS,
    FORBIDDEN_LANGUAGE,
    INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_BLOCKED_CLAIMS,
    MAINTENANCE_BOUNDARIES,
    OBSERVATION_UNCERTAINTY_FIELDS,
    build_aas_incident_verification_observation_uncertainty_maintenance,
    load_aas_incident_verification_observation_uncertainty_maintenance,
    write_aas_incident_verification_observation_uncertainty_maintenance,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_maintenance() -> dict:
    return json.loads(
        (
            ARTIFACT_DIR
            / AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_FILENAME
        ).read_text(encoding="utf-8")
    )


def test_incident_verification_maintenance_matches_persisted_artifact_and_loader() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()

    assert maintenance == read_fixture_maintenance()
    assert load_aas_incident_verification_observation_uncertainty_maintenance() == maintenance
    assert maintenance["schema"] == AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SCHEMA
    assert maintenance["maintenance_status"] == AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_STATUS
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in maintenance[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SAFE_CLAIM in maintenance[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_incident_verification_maintenance_consumes_rank_six_roadmap_row_by_digest() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()
    source = maintenance["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_row_family"] == "incident_verification"
    assert source["consumed_row_rank"] == 6
    assert len(source["digest_sha256"]) == 64


def test_incident_verification_maintenance_is_no_approval_not_emergency_or_dispatch() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()

    for key, expected in FALSE_FLAGS.items():
        assert maintenance["readiness"][key] is expected
    assert maintenance["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "maintenance_only_no_approval_record",
    }

    fixture = maintenance["incident_verification_observation_uncertainty_maintenance"]
    assert fixture["aas_family"] == "incident_verification"
    assert fixture["allowed_use"] == (
        "internal_admin_observation_uncertainty_language_maintenance_no_approval_record"
    )
    assert fixture["maintenance_mode"] == "maintenance_only_no_approval_record"
    assert fixture["still_blocked"] is True
    assert fixture["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_explicit_operator_answer_receipt_then_incident_verification_customer_or_dispatch_gate"
    )


def test_incident_verification_maintenance_preserves_observation_uncertainty_boundaries() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()
    fixture = maintenance["incident_verification_observation_uncertainty_maintenance"]

    assert set(OBSERVATION_UNCERTAINTY_FIELDS) <= set(
        fixture["observation_uncertainty_fields"]
    )
    assert set(MAINTENANCE_BOUNDARIES) <= set(fixture["maintenance_boundaries"])
    assert set(FORBIDDEN_LANGUAGE) <= set(fixture["forbidden_language"])
    assert "incident observation uncertainty language maintenance only" in fixture[
        "safe_internal_language"
    ]
    assert "emergency official-report fault and repair claims blocked" in fixture[
        "safe_internal_language"
    ]
    assert "visible condition does not assign cause or liability" in fixture[
        "safe_internal_language"
    ]
    assert "emergency verified" not in fixture["safe_internal_language"]
    assert "official report complete" not in fixture["safe_internal_language"]
    assert "fault assigned" not in fixture["safe_internal_language"]
    assert "dispatch ready" not in fixture["safe_internal_language"]


def test_incident_verification_maintenance_preserves_claim_boundaries_and_firewall() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()
    safe = set(maintenance["claim_boundaries"]["safe_to_claim"])
    blocked = set(maintenance["claim_boundaries"]["do_not_claim_yet"])

    assert set(INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "authorizes_incident_site_access_recipient_or_customer_use",
        "authorizes_emergency_response_or_safety_decision",
        "official_report_fault_liability_or_insurance_claim",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert maintenance["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_incident_verification_maintenance_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_incident_verification_observation_uncertainty_maintenance(
        artifact_dir=tmp_path
    )

    assert path == tmp_path / AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_FILENAME
    assert load_aas_incident_verification_observation_uncertainty_maintenance(
        artifact_dir=tmp_path
    )["maintenance_id"] == (
        "execution_market.aas.incident_verification_observation_uncertainty_maintenance.2026_06_06_2200"
    )


def test_incident_verification_maintenance_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_approval_recorded"):
        build_aas_incident_verification_observation_uncertainty_maintenance(
            source_roadmap=roadmap
        )


def test_incident_verification_maintenance_rejects_emergency_promotion() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()
    maintenance["readiness"]["maintenance_authorizes_emergency_response_or_safety_decision"] = True

    with pytest.raises(CityOpsContractError, match="emergency_response_or_safety_decision"):
        load_aas_incident_verification_observation_uncertainty_maintenance(
            artifact_dir=_write_fixture_triple(maintenance)
        )


def test_incident_verification_maintenance_rejects_official_fault_or_insurance_claim() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()
    maintenance["readiness"][
        "maintenance_creates_official_report_fault_liability_or_insurance_claim"
    ] = True

    with pytest.raises(CityOpsContractError, match="official_report_fault_liability_or_insurance_claim"):
        load_aas_incident_verification_observation_uncertainty_maintenance(
            artifact_dir=_write_fixture_triple(maintenance)
        )


def test_incident_verification_maintenance_rejects_missing_uncertainty_field() -> None:
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance()
    maintenance["incident_verification_observation_uncertainty_maintenance"][
        "observation_uncertainty_fields"
    ] = [
        field
        for field in maintenance["incident_verification_observation_uncertainty_maintenance"][
            "observation_uncertainty_fields"
        ]
        if field != "uncertainty_or_ambiguity_statement_required"
    ]

    with pytest.raises(CityOpsContractError, match="missing observation uncertainty fields"):
        load_aas_incident_verification_observation_uncertainty_maintenance(
            artifact_dir=_write_fixture_triple(maintenance)
        )


def test_incident_verification_maintenance_rejects_wrong_source_row() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "incident_verification":
            row["planning_sequence_rank"] = 7

    with pytest.raises(CityOpsContractError, match="source rank drift"):
        build_aas_incident_verification_observation_uncertainty_maintenance(
            source_roadmap=roadmap
        )


def _write_fixture_triple(maintenance: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_FILENAME).write_text(
        json.dumps(maintenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
