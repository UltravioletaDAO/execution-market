import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_fixture_review_gate import (
    INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    build_incident_verification_fixture_review_gate,
)
from mcp_server.city_ops.incident_verification_local_reviewed_fixture import (
    COVERED_LADDER_STEPS,
    INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME,
    INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SCHEMA,
    LOCAL_FIXTURE_REVIEW_CHECKS,
    NEXT_REQUIRED_LADDER_STEPS,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    build_incident_verification_local_reviewed_fixture,
    load_incident_verification_local_reviewed_fixture,
    write_incident_verification_local_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_incident_verification_local_reviewed_fixture_matches_persisted_artifact():
    fixture = build_incident_verification_local_reviewed_fixture()

    assert fixture == read_fixture()
    assert load_incident_verification_local_reviewed_fixture() == fixture
    assert fixture["schema"] == INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SCHEMA
    assert fixture["scope"] == "internal_admin_incident_verification_local_reviewed_fixture_only"
    assert fixture["package_family_id"] == PACKAGE_FAMILY_ID
    assert fixture["offer_id"] == OFFER_ID
    assert INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in fixture["safe_to_claim"]


def test_local_fixture_advances_one_rung_and_blocks_promotion():
    fixture = build_incident_verification_local_reviewed_fixture()

    assert fixture["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert fixture["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert fixture["ladder_boundary"]["promotion_allowed"] is False
    assert fixture["local_fixture"]["review_status"] == "reviewed_internal_fixture_only_not_promoted"

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "emergency_response",
        "safety_certification",
        "repair_diagnosis_or_completion",
        "insurance_adjustment",
        "sla_uptime",
        "official_incident_report",
        "live_dispatch",
        "erc8004_reputation_receipt",
        "worker_copyable_incident_doctrine",
        "incident_verification_local_fixture_customer_delivery_ready",
        "incident_verification_local_fixture_dispatch_ready",
        "incident_verification_local_fixture_safety_certification_ready",
        "incident_verification_local_fixture_official_report_ready",
    ]:
        assert claim in fixture["do_not_claim_yet"]
        assert claim not in fixture["safe_to_claim"]


def test_local_fixture_evidence_schema_and_reviewed_output_are_complete():
    fixture = build_incident_verification_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]

    assert set(REQUIRED_EVIDENCE_FIELDS).issubset(
        set(local_fixture["evidence_contract_snapshot"])
    )
    assert set(REQUIRED_OUTPUT_FIELDS).issubset(
        set(local_fixture["reviewed_output_schema"]["required_fields"])
    )
    assert set(REQUIRED_OUTPUT_FIELDS).issubset(set(local_fixture["reviewed_output"]))
    for forbidden_field in [
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "precise_address_or_private_location",
        "emergency_response_instruction",
        "safety_certification_claim",
        "repair_diagnosis_claim",
        "repair_completion_claim",
        "insurance_adjustment_claim",
        "sla_uptime_claim",
        "official_incident_report_claim",
        "dispatch_instruction_or_assignment",
        "erc8004_reputation_receipt",
        "worker_copyable_incident_doctrine",
    ]:
        assert forbidden_field in local_fixture["reviewed_output_schema"]["forbidden_fields"]


def test_local_fixture_review_checks_pass_only_for_internal_fixture():
    fixture = build_incident_verification_local_reviewed_fixture()

    assert [item["check_id"] for item in fixture["local_review_checks"]] == (
        LOCAL_FIXTURE_REVIEW_CHECKS
    )
    for item in fixture["local_review_checks"]:
        assert item["status"] == "passed_for_local_fixture_only"
        assert item["blocks_promotion_until_later_gate"] is True

    local_fixture = fixture["local_fixture"]
    assert local_fixture["customer_copy_changed"] is False
    assert local_fixture["customer_delivery_allowed"] is False
    assert local_fixture["publication_allowed"] is False
    assert local_fixture["dispatch_allowed"] is False
    assert local_fixture["reputation_attachment_allowed"] is False
    assert local_fixture["worker_copyable_doctrine_allowed"] is False
    assert local_fixture["emergency_or_safety_claim_allowed"] is False
    assert local_fixture["repair_or_insurance_claim_allowed"] is False
    assert local_fixture["sla_or_official_report_claim_allowed"] is False


def test_readiness_flags_remain_false():
    fixture = build_incident_verification_local_reviewed_fixture()

    assert fixture["readiness"]["customer_copy_ready"] is False
    assert fixture["readiness"]["public_service_catalog_ready"] is False
    assert fixture["readiness"]["controlled_concierge_pilot_ready"] is False
    assert fixture["readiness"]["customer_pilot_exposure_allowed"] is False
    assert fixture["readiness"]["live_acontext_ready"] is False
    assert fixture["readiness"]["runtime_parity_proven"] is False
    assert fixture["readiness"]["autonomous_dispatch_ready"] is False
    assert fixture["readiness"]["reputation_ready"] is False
    assert fixture["readiness"]["worker_skill_dna_ready"] is False
    assert fixture["readiness"]["worker_copyable_doctrine_ready"] is False
    assert fixture["readiness"]["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_write_incident_verification_local_reviewed_fixture_persists_valid_artifact(tmp_path):
    path = write_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME
    assert load_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_local_fixture_fails_closed_when_source_gate_promotes_readiness():
    gate = build_incident_verification_fixture_review_gate()
    gate["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source gate promoted readiness"):
        build_incident_verification_local_reviewed_fixture(gate=gate)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    fixture = build_incident_verification_local_reviewed_fixture()
    fixture["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    fixture = build_incident_verification_local_reviewed_fixture()
    fixture["safe_to_claim"].append("incident_verification_local_fixture_dispatch_ready")
    (tmp_path / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_dropped_blocked_claim(tmp_path):
    fixture = build_incident_verification_local_reviewed_fixture()
    fixture["do_not_claim_yet"] = [
        claim
        for claim in fixture["do_not_claim_yet"]
        if claim != "worker_copyable_incident_doctrine"
    ]
    (tmp_path / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        load_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_review_check_promotion(tmp_path):
    fixture = build_incident_verification_local_reviewed_fixture()
    fixture["local_review_checks"][0]["status"] = "passed_for_customer_output"
    (tmp_path / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="review check status drift"):
        load_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_private_location_or_incident_overclaim(tmp_path):
    fixture = copy.deepcopy(build_incident_verification_local_reviewed_fixture())
    fixture["local_fixture"]["reviewed_output"]["place_time_window_summary"] = (
        "GPS: hidden test leak"
    )
    (tmp_path / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private location or incident overclaim"):
        load_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_live_dispatch_enablement(tmp_path):
    fixture = build_incident_verification_local_reviewed_fixture()
    fixture["local_fixture"]["dispatch_allowed"] = True
    (tmp_path / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted dispatch_allowed"):
        load_incident_verification_local_reviewed_fixture(artifact_dir=tmp_path)
