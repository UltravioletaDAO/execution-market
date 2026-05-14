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
)
from mcp_server.city_ops.incident_verification_internal_package_record import (
    COVERED_LADDER_STEPS,
    INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME,
    INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SCHEMA,
    NEXT_REQUIRED_LADDER_STEPS,
    PACKAGE_ID,
    PACKAGE_REVIEW_CHECKS,
    build_incident_verification_internal_package_record,
    load_incident_verification_internal_package_record,
    write_incident_verification_internal_package_record,
)
from mcp_server.city_ops.incident_verification_local_reviewed_fixture import (
    INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    build_incident_verification_local_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_package_record() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_incident_verification_internal_package_record_matches_persisted_artifact():
    record = build_incident_verification_internal_package_record()

    assert record == read_package_record()
    assert load_incident_verification_internal_package_record() == record
    assert record["schema"] == INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SCHEMA
    assert record["package_id"] == PACKAGE_ID
    assert record["scope"] == "internal_admin_incident_verification_package_record_only"
    assert record["offer_id"] == "one_location_incident_state_snapshot"
    assert INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in record["safe_to_claim"]
    assert INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM in record["safe_to_claim"]
    assert INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM in record["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in record["safe_to_claim"]


def test_package_record_advances_exactly_one_ladder_rung_without_promotion():
    record = build_incident_verification_internal_package_record()

    assert record["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert record["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert record["ladder_boundary"]["promotion_allowed"] is False
    assert record["internal_package_record"]["review_status"] == (
        "packaged_internal_only_not_promoted"
    )


def test_package_record_preserves_incident_evidence_and_reviewed_output_fields():
    record = build_incident_verification_internal_package_record()
    package = record["internal_package_record"]
    evidence = package["packaged_evidence_contract"]
    reviewed_output = package["packaged_reviewed_output"]

    for field in [
        "incident_question",
        "place_time_window_without_exact_public_coordinates",
        "wide_context_photo_or_permitted_visual_snapshot",
        "close_evidence_photo_where_allowed",
        "severity_taxonomy",
        "uncertainty_note",
        "what_was_not_checked",
        "recommended_next_action",
        "follow_on_task_trigger_if_another_visit_or_specialist_needed",
    ]:
        assert field in evidence

    for field in package["reviewed_output_schema"]["required_fields"]:
        assert field in reviewed_output
    assert "not emergency response" in reviewed_output["plain_language_status"]
    assert "not a safety certification" in reviewed_output["plain_language_status"]
    assert reviewed_output["severity_taxonomy"] == (
        "observed_minor_to_moderate_obstruction_unverified_safety_impact"
    )
    assert "do not auto-dispatch" in reviewed_output["follow_on_task_trigger"]


def test_package_record_blocks_customer_public_dispatch_reputation_emergency_and_worker_doctrine():
    record = build_incident_verification_internal_package_record()
    package = record["internal_package_record"]

    assert package["customer_copy_changed"] is False
    assert package["customer_delivery_allowed"] is False
    assert package["publication_allowed"] is False
    assert package["dispatch_allowed"] is False
    assert package["reputation_attachment_allowed"] is False
    assert package["worker_copyable_doctrine_allowed"] is False
    assert package["live_acontext_or_runtime_parity_claimed"] is False
    assert package["exact_gps_or_raw_metadata_exposure_allowed"] is False
    assert package["emergency_response_claimed"] is False
    assert package["safety_certification_claimed"] is False
    assert package["repair_diagnosis_or_completion_claimed"] is False
    assert package["insurance_adjustment_claimed"] is False
    assert package["sla_uptime_claimed"] is False
    assert package["official_incident_report_claimed"] is False

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "emergency_response",
        "safety_certification",
        "repair_diagnosis_or_completion",
        "insurance_adjustment",
        "sla_uptime",
        "official_incident_report",
        "worker_copyable_incident_doctrine",
        "incident_verification_internal_package_customer_delivery_ready",
        "incident_verification_internal_package_dispatch_ready",
        "incident_verification_internal_package_safety_certification_ready",
        "incident_verification_internal_package_official_report_ready",
    ]:
        assert claim in record["do_not_claim_yet"]
        assert claim not in record["safe_to_claim"]


def test_readiness_flags_remain_false():
    record = build_incident_verification_internal_package_record()

    assert record["readiness"]["customer_copy_ready"] is False
    assert record["readiness"]["public_service_catalog_ready"] is False
    assert record["readiness"]["live_acontext_ready"] is False
    assert record["readiness"]["runtime_parity_proven"] is False
    assert record["readiness"]["autonomous_dispatch_ready"] is False
    assert record["readiness"]["reputation_ready"] is False
    assert record["readiness"]["worker_skill_dna_ready"] is False
    assert record["readiness"]["worker_copyable_doctrine_ready"] is False
    assert record["readiness"]["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_package_review_checks_pass_only_for_internal_package_and_still_block_promotion():
    record = build_incident_verification_internal_package_record()

    assert [item["check_id"] for item in record["package_review_checks"]] == (
        PACKAGE_REVIEW_CHECKS
    )
    for item in record["package_review_checks"]:
        assert item["status"] == "passed_for_internal_package_record_only"
        assert item["blocks_promotion_until_later_gate"] is True


def test_write_incident_verification_internal_package_record_persists_valid_artifact(tmp_path):
    path = write_incident_verification_internal_package_record(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME
    assert load_incident_verification_internal_package_record(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_package_record_fails_closed_when_source_fixture_promotes_readiness():
    fixture = build_incident_verification_local_reviewed_fixture()
    fixture = copy.deepcopy(fixture)
    fixture["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_incident_verification_internal_package_record(local_fixture=fixture)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    record = build_incident_verification_internal_package_record()
    record["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_incident_verification_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    record = build_incident_verification_internal_package_record()
    record["safe_to_claim"].append("incident_verification_internal_package_dispatch_ready")
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_incident_verification_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_on_private_location_language(tmp_path):
    record = build_incident_verification_internal_package_record()
    record["internal_package_record"]["packaged_reviewed_output"][
        "place_time_window_summary"
    ] = "precise address: private unit location"
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private location"):
        load_incident_verification_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_on_incident_overclaim(tmp_path):
    record = build_incident_verification_internal_package_record()
    record["internal_package_record"]["packaged_reviewed_output"][
        "limitations_and_non_guarantees"
    ].append("official incident report filed and repair completed")
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="incident overclaim"):
        load_incident_verification_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_when_review_check_stops_blocking(tmp_path):
    record = build_incident_verification_internal_package_record()
    record["package_review_checks"][0]["blocks_promotion_until_later_gate"] = False
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="stopped blocking promotion"):
        load_incident_verification_internal_package_record(artifact_dir=tmp_path)
