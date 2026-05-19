import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_package_review_decision import (
    ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS,
    FOLLOW_ON_ESCALATION_BOUNDARIES,
    FORBIDDEN_FIELD_CLASSES,
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME,
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SCHEMA,
    NEXT_REQUIRED_GATE,
    PACKAGE_REVIEW_BLOCKED_CLAIMS,
    PACKAGE_REVIEW_DECISION,
    PACKAGE_REVIEW_FALSE_FLAGS,
    SELECTED_INTERNAL_LABEL,
    build_incident_verification_package_review_decision,
    load_incident_verification_package_review_decision,
    write_incident_verification_package_review_decision,
)
from mcp_server.city_ops.incident_verification_sample_output_review_decision import (
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    build_incident_verification_sample_output_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_decision() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_decision(tmp_path: Path) -> None:
    (tmp_path / INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(build_incident_verification_sample_output_review_decision()),
        encoding="utf-8",
    )


def test_package_review_decision_matches_persisted_artifact_and_loader():
    decision = build_incident_verification_package_review_decision()

    assert decision == read_decision()
    assert load_incident_verification_package_review_decision() == decision
    assert decision["schema"] == INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SCHEMA
    assert decision["scope"] == "internal_admin_incident_verification_package_review_decision_only"
    assert decision["source_policy"] == "consume_only_incident_verification_sample_output_review_decision_json"
    assert decision["source_decision_file"] == INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME
    assert INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM in decision["safe_to_claim"]
    assert INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM in decision["safe_to_claim"]


def test_package_review_answers_label_fields_forbidden_classes_follow_on_and_next_gate():
    decision = build_incident_verification_package_review_decision()

    assert decision["package_review_decision"] == PACKAGE_REVIEW_DECISION
    assert decision["selected_internal_label"] == SELECTED_INTERNAL_LABEL
    assert decision["selected_internal_label_customer_copy_approved"] is False
    assert decision["allowed_future_customer_output_fields"] == ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS
    assert "observational_severity_taxonomy" in decision["allowed_future_customer_output_fields"]
    assert "follow_on_task_trigger" in decision["allowed_future_customer_output_fields"]
    assert "exact_gps_or_raw_metadata" in decision["forbidden_field_classes"]
    assert "fault_or_liability_assignment" in decision["forbidden_field_classes"]
    assert set(FORBIDDEN_FIELD_CLASSES) <= set(decision["forbidden_field_classes"])
    assert decision["follow_on_escalation_boundaries"] == FOLLOW_ON_ESCALATION_BOUNDARIES
    assert all(row["execution_market_action_authorized"] is False for row in decision["follow_on_escalation_boundaries"])
    assert decision["next_required_gate_before_any_delivery_path"] == NEXT_REQUIRED_GATE
    assert decision["next_gate_satisfied"] is False
    assert len(decision["review_questions"]) == 5
    assert all(row["approval_granted"] is False for row in decision["review_questions"])


def test_package_review_keeps_summary_and_readiness_held():
    decision = build_incident_verification_package_review_decision()
    summary = decision["package_review_summary"]

    assert summary["source_hold_preserved"] is True
    assert summary["internal_label_reviewed"] is True
    assert summary["allowed_future_fields_named"] is True
    assert summary["forbidden_authority_classes_named"] is True
    assert summary["follow_on_boundaries_named"] is True
    assert summary["next_gate_named"] is True
    assert summary["customer_copy_approved"] is False
    assert summary["customer_delivery_approved"] is False
    assert summary["publication_approved"] is False
    assert summary["public_price_or_customer_quote_approved"] is False
    assert summary[
        "queue_dispatch_reputation_runtime_gps_incident_authority_worker_doctrine_approved"
    ] is False
    for flag in PACKAGE_REVIEW_FALSE_FLAGS:
        assert decision["readiness"][flag] is False


def test_package_review_claim_boundaries_preserve_blocked_claims():
    decision = build_incident_verification_package_review_decision()

    assert not set(decision["safe_to_claim"]) & set(decision["do_not_claim_yet"])
    assert decision["still_blocked_claims"] == decision["do_not_claim_yet"]
    for claim in PACKAGE_REVIEW_BLOCKED_CLAIMS:
        assert claim in decision["do_not_claim_yet"]
        assert claim not in decision["safe_to_claim"]
    assert "incident_verification_customer_delivery_ready" not in decision["safe_to_claim"]
    assert "incident_verification_emergency_response_ready" not in decision["safe_to_claim"]
    assert "incident_verification_worker_copyable_doctrine_ready" not in decision["safe_to_claim"]


def test_write_package_review_persists_valid_artifact(tmp_path):
    seed_source_decision(tmp_path)

    path = write_incident_verification_package_review_decision(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME
    assert load_incident_verification_package_review_decision(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_decision_promotion_fails_closed():
    source = build_incident_verification_sample_output_review_decision()
    source = copy.deepcopy(source)
    source["review_decision"] = "approved_publishable"

    with pytest.raises(CityOpsContractError, match="source decision promoted from hold"):
        build_incident_verification_package_review_decision(source_decision=source)


def test_source_forbidden_safe_claim_fails_closed():
    source = build_incident_verification_sample_output_review_decision()
    source = copy.deepcopy(source)
    source["safe_to_claim"].append("emergency_response")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_incident_verification_package_review_decision(source_decision=source)


def test_source_missing_blocked_claim_fails_closed():
    source = build_incident_verification_sample_output_review_decision()
    source = copy.deepcopy(source)
    source["do_not_claim_yet"] = [
        claim
        for claim in source["do_not_claim_yet"]
        if claim != "sample_output_emergency_response_ready"
    ]

    with pytest.raises(CityOpsContractError, match="source missing blocked claims"):
        build_incident_verification_package_review_decision(source_decision=source)


def test_loader_fails_closed_on_customer_copy_promotion(tmp_path):
    seed_source_decision(tmp_path)
    decision = build_incident_verification_package_review_decision(artifact_dir=tmp_path)
    decision["readiness"]["customer_copy_ready"] = True
    (tmp_path / INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted customer_copy_ready"):
        load_incident_verification_package_review_decision(artifact_dir=tmp_path)


def test_loader_fails_closed_on_follow_on_authorization_drift(tmp_path):
    seed_source_decision(tmp_path)
    decision = build_incident_verification_package_review_decision(artifact_dir=tmp_path)
    decision["follow_on_escalation_boundaries"][0]["execution_market_action_authorized"] = True
    (tmp_path / INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="follow-on boundary authorized action"):
        load_incident_verification_package_review_decision(artifact_dir=tmp_path)
