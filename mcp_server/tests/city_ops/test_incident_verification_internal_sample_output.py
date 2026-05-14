import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_customer_output_schema_gate import (
    ALLOWED_CUSTOMER_OUTPUT_FIELDS,
    FORBIDDEN_CUSTOMER_OUTPUT_FIELDS,
    INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME,
    INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM,
    build_incident_verification_customer_output_schema_gate,
)
from mcp_server.city_ops.incident_verification_internal_sample_output import (
    INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME,
    INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
    INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SCHEMA,
    NEXT_REQUIRED_LADDER_STEPS,
    SAMPLE_OUTPUT_ID,
    build_incident_verification_internal_sample_output,
    load_incident_verification_internal_sample_output,
    write_incident_verification_internal_sample_output,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_sample() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_schema_gate(tmp_path: Path) -> None:
    gate = build_incident_verification_customer_output_schema_gate()
    (tmp_path / INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )


def test_incident_verification_internal_sample_output_matches_persisted_artifact():
    sample = build_incident_verification_internal_sample_output()

    assert sample == read_sample()
    assert load_incident_verification_internal_sample_output() == sample
    assert sample["schema"] == INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SCHEMA
    assert sample["sample_output_id"] == SAMPLE_OUTPUT_ID
    assert sample["scope"] == "internal_admin_incident_verification_sample_output_only"
    assert sample["sample_status"] == (
        "internal_sample_output_landed_not_customer_copy_not_public_not_approved"
    )
    assert INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM in sample[
        "safe_to_claim"
    ]
    assert INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM in sample["safe_to_claim"]
    assert sample["safe_to_claim"][-1] == INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM


def test_sample_consumes_only_customer_output_schema_gate():
    sample = build_incident_verification_internal_sample_output()
    contract = sample["source_contract"]

    assert sample["source_schema_gate_file"] == INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME
    assert contract["consumes_only"] == [INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME]
    assert contract["source_loader"] == "load_incident_verification_customer_output_schema_gate"
    assert contract["source_is_schema_gate_only"] is True
    assert contract["reads_operator_surface_directly"] is False
    assert contract["reads_raw_review_fixture"] is False
    assert contract["reads_raw_transcripts"] is False
    assert contract["reads_raw_metadata"] is False
    assert contract["reads_private_operator_context"] is False
    assert contract["creates_emergency_response_claim"] is False
    assert contract["creates_safety_certification_claim"] is False
    assert contract["creates_repair_or_insurance_claim"] is False
    assert contract["creates_sla_or_official_report_claim"] is False
    assert contract["assigns_fault_or_liability"] is False


def test_sample_populates_only_allowed_schema_fields():
    sample = build_incident_verification_internal_sample_output()
    output = sample["sample_output"]

    assert output["sample_offer"] == "one_location_incident_state_snapshot"
    assert output["jurisdiction_specific"] is False
    assert output["synthetic_fixture_only"] is True
    assert output["allowed_customer_output_fields"] == ALLOWED_CUSTOMER_OUTPUT_FIELDS
    assert list(output["field_values"].keys()) == ALLOWED_CUSTOMER_OUTPUT_FIELDS
    assert output["forbidden_customer_output_fields_absent"] == FORBIDDEN_CUSTOMER_OUTPUT_FIELDS
    assert "incident_question_summary" in output["field_values"]
    assert "privacy_redaction_notice" in output["field_values"]
    assert "limitations_and_non_guarantees" in output["field_values"]
    for forbidden in FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        assert forbidden not in output["field_values"]


def test_sample_preserves_limitations_privacy_uncertainty_and_non_authority():
    output = build_incident_verification_internal_sample_output()["sample_output"]
    values = output["field_values"]
    reviews = output["separate_reviews"]

    assert reviews["privacy_redaction_review_passed"] is True
    assert reviews["limitations_preserved_review_passed"] is True
    assert reviews["non_authoritative_language_review_passed"] is True
    assert (
        reviews[
            "emergency_safety_repair_insurance_sla_and_official_report_exclusion_review_passed"
        ]
        is True
    )
    assert reviews["operator_publish_approval"] is False
    assert reviews["customer_delivery_approval"] is False
    assert reviews["explicit_hold_or_approval_decision_recorded"] is False
    assert "not customer-ready copy" in " ".join(values["limitations_and_non_guarantees"])
    assert "separate explicit hold/approval decision" in " ".join(
        values["limitations_and_non_guarantees"]
    )
    assert "Privacy-sensitive details" in values["privacy_redaction_notice"]
    assert "non-authoritative" in values["uncertainty_note"] or "official" in values[
        "uncertainty_note"
    ]
    assert "not publication" in build_incident_verification_internal_sample_output()[
        "next_smallest_proof"
    ]


def test_sample_keeps_all_readiness_and_approval_flags_false():
    sample = build_incident_verification_internal_sample_output()

    assert all(value is False for value in sample["readiness"].values())
    assert all(value is False for value in sample["sample_output_readiness"].values())
    for flag in [
        "customer_copy_created",
        "customer_copy_ready",
        "public_route_registered",
        "dispatch_enabled",
        "emits_reputation_receipts",
        "live_acontext_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "raw_metadata_release_ready",
        "emergency_response_ready",
        "safety_certification_ready",
        "repair_diagnosis_ready",
        "repair_completion_ready",
        "insurance_adjustment_ready",
        "sla_uptime_ready",
        "official_incident_report_ready",
        "fault_or_liability_assignment_ready",
        "worker_copyable_doctrine_ready",
        "customer_public_launch_ready",
        "catalog_or_pilot_readiness_ready",
        "explicit_hold_or_approval_decision_recorded",
    ]:
        assert sample["sample_output_readiness"][flag] is False


def test_sample_blocks_external_product_and_incident_outcome_claims():
    sample = build_incident_verification_internal_sample_output()
    blocked = set(sample["do_not_claim_yet"])

    for claim in [
        "internal_sample_customer_copy_ready",
        "internal_sample_publication_ready",
        "internal_sample_catalog_ready",
        "internal_sample_controlled_pilot_ready",
        "internal_sample_public_route_ready",
        "internal_sample_dispatch_ready",
        "internal_sample_reputation_ready",
        "internal_sample_live_acontext_ready",
        "internal_sample_exact_gps_or_raw_metadata_release_ready",
        "internal_sample_emergency_response_ready",
        "internal_sample_safety_certification_ready",
        "internal_sample_repair_diagnosis_ready",
        "internal_sample_repair_completion_ready",
        "internal_sample_insurance_adjustment_ready",
        "internal_sample_sla_uptime_ready",
        "internal_sample_official_incident_report_ready",
        "internal_sample_fault_or_liability_assignment_ready",
        "internal_sample_worker_doctrine_ready",
        "internal_sample_operator_approval_ready",
        "internal_sample_hold_decision_ready",
    ]:
        assert claim in blocked
        assert claim not in sample["safe_to_claim"]
    assert not set(sample["safe_to_claim"]) & set(sample["do_not_claim_yet"])


def test_sample_advances_ladder_to_hold_decision_only():
    sample = build_incident_verification_internal_sample_output()

    assert sample["ladder_boundary"]["covered_steps"][-1] == "internal_sample_output"
    assert sample["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert sample["ladder_boundary"]["promotion_allowed"] is False
    assert sample["next_smallest_proof"].startswith("Record a separate explicit hold")


def test_write_incident_verification_internal_sample_output_persists_valid_artifact(tmp_path):
    seed_schema_gate(tmp_path)

    path = write_incident_verification_internal_sample_output(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME
    assert load_incident_verification_internal_sample_output(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_gate_readiness_promotion_fails_closed():
    gate = copy.deepcopy(build_incident_verification_customer_output_schema_gate())
    gate["schema_gate_readiness"]["customer_copy_created"] = True

    with pytest.raises(CityOpsContractError, match="source promoted schema readiness"):
        build_incident_verification_internal_sample_output(schema_gate=gate)


def test_loader_fails_closed_on_sample_publication_flip(tmp_path):
    seed_schema_gate(tmp_path)
    sample = build_incident_verification_internal_sample_output()
    sample["sample_output_readiness"]["publication_approved"] = True
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME).write_text(
        json.dumps(sample), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted sample readiness"):
        load_incident_verification_internal_sample_output(artifact_dir=tmp_path)


def test_loader_fails_closed_on_disallowed_field_value(tmp_path):
    seed_schema_gate(tmp_path)
    sample = build_incident_verification_internal_sample_output()
    sample["sample_output"]["field_values"]["emergency_response_instruction"] = "blocked"
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME).write_text(
        json.dumps(sample), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="populated disallowed field"):
        load_incident_verification_internal_sample_output(artifact_dir=tmp_path)


def test_loader_fails_closed_on_missing_review_gate(tmp_path):
    seed_schema_gate(tmp_path)
    sample = build_incident_verification_internal_sample_output()
    sample["sample_output"]["separate_reviews"]["non_authoritative_language_review_passed"] = False
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME).write_text(
        json.dumps(sample), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing review gates"):
        load_incident_verification_internal_sample_output(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    seed_schema_gate(tmp_path)
    sample = build_incident_verification_internal_sample_output()
    sample["safe_to_claim"].append("internal_sample_safety_certification_ready")
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME).write_text(
        json.dumps(sample), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_incident_verification_internal_sample_output(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_outcome_language(tmp_path):
    seed_schema_gate(tmp_path)
    sample = build_incident_verification_internal_sample_output()
    sample["sample_output"]["field_values"]["plain_language_status"] += " Certified safe."
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME).write_text(
        json.dumps(sample), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden text fragment"):
        load_incident_verification_internal_sample_output(artifact_dir=tmp_path)
