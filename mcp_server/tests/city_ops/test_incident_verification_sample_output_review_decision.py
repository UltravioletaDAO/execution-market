import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_internal_sample_output import (
    INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME,
    INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
    build_incident_verification_internal_sample_output,
)
from mcp_server.city_ops.incident_verification_sample_output_review_decision import (
    DECISION_ID,
    DECISION_READINESS_FALSE_FLAGS,
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
    HOLD_REASONS,
    NEXT_REQUIRED_LADDER_STEPS,
    REQUIRED_REVIEW_FINDINGS,
    REVIEW_DECISION,
    build_incident_verification_sample_output_review_decision,
    load_incident_verification_sample_output_review_decision,
    write_incident_verification_sample_output_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_decision() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sample(tmp_path: Path) -> None:
    sample = build_incident_verification_internal_sample_output()
    (tmp_path / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME).write_text(
        json.dumps(sample), encoding="utf-8"
    )


def test_incident_verification_sample_output_review_decision_matches_persisted_artifact():
    decision = build_incident_verification_sample_output_review_decision()

    assert decision == read_decision()
    assert load_incident_verification_sample_output_review_decision() == decision
    assert decision["schema"] == INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA
    assert decision["decision_id"] == DECISION_ID
    assert decision["scope"] == "internal_admin_incident_verification_sample_output_hold_decision_only"
    assert INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM in decision["safe_to_claim"]
    assert INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM in decision["safe_to_claim"]


def test_decision_records_explicit_hold_not_approval():
    decision = build_incident_verification_sample_output_review_decision()

    assert decision["decision_status"] == "explicit_hold_recorded_not_approved_not_publishable"
    assert decision["review_decision"] == REVIEW_DECISION
    assert decision["explicit_hold_decision_recorded"] is True
    assert decision["operator_review_recorded"] is True
    assert decision["operator_approval_granted"] is False
    assert decision["operator_publish_approval"] is False
    assert decision["customer_delivery_approval"] is False
    assert decision["publication_approved"] is False
    assert decision["sample_output_publishable"] is False
    assert decision["customer_copy_ready"] is False
    assert decision["public_service_catalog_ready"] is False


def test_decision_completes_hold_decision_ladder_step_without_promotion():
    decision = build_incident_verification_sample_output_review_decision()

    assert decision["ladder_boundary"]["covered_steps"][-1] == "explicit_approval_or_hold_decision"
    assert decision["ladder_boundary"]["next_required_steps_before_promotion"] == NEXT_REQUIRED_LADDER_STEPS
    assert decision["ladder_boundary"]["promotion_allowed"] is False


def test_decision_consumes_only_internal_sample_output():
    decision = build_incident_verification_sample_output_review_decision()
    boundary = decision["sample_output_boundary"]

    assert decision["source_sample_output_file"] == INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME
    assert boundary["consumes_only"] == [INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME]
    assert boundary["source_sample_review_status"] == (
        "internal_admin_sample_against_schema_gate_not_customer_copy"
    )
    assert boundary["source_sample_is_synthetic"] is True
    assert boundary["source_sample_is_jurisdiction_specific"] is False
    assert boundary["sample_text_approved_for_customer"] is False
    assert boundary["sample_text_publishable"] is False
    assert boundary["customer_delivery_allowed"] is False
    assert boundary["public_route_allowed"] is False
    assert boundary["dispatch_allowed"] is False
    assert boundary["reputation_attachment_allowed"] is False
    assert boundary["exact_gps_or_raw_metadata_allowed"] is False
    assert boundary[
        "emergency_safety_repair_insurance_sla_official_report_fault_or_liability_claim_allowed"
    ] is False


def test_review_findings_are_verified_but_hold_required():
    decision = build_incident_verification_sample_output_review_decision()

    assert [item["finding"] for item in decision["review_findings"]] == REQUIRED_REVIEW_FINDINGS
    for item in decision["review_findings"]:
        assert item["verified"] is True
        assert item["approval_granted"] is False
        assert item["hold_required"] is True
    assert decision["hold_reasons"] == HOLD_REASONS


def test_decision_keeps_external_product_and_outcome_flags_false():
    decision = build_incident_verification_sample_output_review_decision()

    for flag in DECISION_READINESS_FALSE_FLAGS:
        assert decision.get(flag, decision["decision_readiness"].get(flag)) is False
    assert all(value is False for value in decision["readiness"].values())
    assert all(value is False for value in decision["decision_readiness"].values())


def test_claim_boundaries_stay_adjacent_and_conservative():
    decision = build_incident_verification_sample_output_review_decision()
    key_order = list(decision.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(decision["safe_to_claim"]) & set(decision["do_not_claim_yet"])
    for claim in [
        "sample_output_customer_copy_ready",
        "sample_output_customer_delivery_ready",
        "sample_output_publication_ready",
        "sample_output_dispatch_ready",
        "sample_output_reputation_ready",
        "sample_output_worker_doctrine_ready",
        "sample_output_emergency_response_ready",
        "sample_output_safety_certification_ready",
        "sample_output_repair_diagnosis_ready",
        "sample_output_repair_completion_ready",
        "sample_output_insurance_adjustment_ready",
        "sample_output_sla_uptime_ready",
        "sample_output_official_incident_report_ready",
        "sample_output_fault_or_liability_assignment_ready",
    ]:
        assert claim in decision["do_not_claim_yet"]
        assert claim not in decision["safe_to_claim"]
    assert decision["still_blocked_claims"] == decision["do_not_claim_yet"]


def test_write_sample_output_review_decision_persists_valid_artifact(tmp_path):
    seed_sample(tmp_path)

    path = write_incident_verification_sample_output_review_decision(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME
    assert load_incident_verification_sample_output_review_decision(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_sample_publication_flip_fails_closed():
    sample = copy.deepcopy(build_incident_verification_internal_sample_output())
    sample["sample_output_readiness"]["publication_approved"] = True

    with pytest.raises(CityOpsContractError, match="source promoted sample readiness"):
        build_incident_verification_sample_output_review_decision(sample_output=sample)


def test_source_sample_approval_review_flag_fails_closed():
    sample = copy.deepcopy(build_incident_verification_internal_sample_output())
    sample["sample_output"]["separate_reviews"]["operator_publish_approval"] = True

    with pytest.raises(CityOpsContractError, match="source promoted review flag"):
        build_incident_verification_sample_output_review_decision(sample_output=sample)


def test_loader_fails_closed_on_customer_delivery_flip(tmp_path):
    decision = build_incident_verification_sample_output_review_decision()
    decision["customer_delivery_approval"] = True
    (tmp_path / INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_incident_verification_sample_output_review_decision(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    decision = build_incident_verification_sample_output_review_decision()
    decision["safe_to_claim"].append("sample_output_customer_delivery_ready")
    (tmp_path / INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_incident_verification_sample_output_review_decision(artifact_dir=tmp_path)


def test_loader_fails_closed_on_boundary_public_route_flip(tmp_path):
    decision = build_incident_verification_sample_output_review_decision()
    decision["sample_output_boundary"]["public_route_allowed"] = True
    (tmp_path / INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="boundary overclaims"):
        load_incident_verification_sample_output_review_decision(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_authority_language(tmp_path):
    decision = build_incident_verification_sample_output_review_decision()
    decision["operator_instruction"] += " Certified safe."
    (tmp_path / INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden text fragment"):
        load_incident_verification_sample_output_review_decision(artifact_dir=tmp_path)
