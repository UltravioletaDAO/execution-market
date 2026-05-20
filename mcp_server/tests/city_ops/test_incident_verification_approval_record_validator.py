import copy
import hashlib
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_approval_record_schema_gate import (
    FUTURE_RECORD_MUST_KEEP_FALSE,
    FUTURE_RECORD_SCHEMA_NAME,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
    build_incident_verification_approval_record_schema_gate,
)
from mcp_server.city_ops.incident_verification_approval_record_validator import (
    APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
    APPROVAL_RECORD_ALLOWED_SCOPE,
    APPROVAL_RECORD_ALLOWED_STATUS,
    APPROVAL_RECORD_REQUIRED_FIELDS,
    INCIDENT_AUTHORITY_LIMITS,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SCHEMA,
    REQUIRED_BLOCKED_CLAIMS,
    VALIDATOR_STATUS,
    build_incident_verification_approval_record_validator,
    load_incident_verification_approval_record_validator,
    validate_incident_verification_human_operator_approval_record,
    write_incident_verification_approval_record_validator,
)
from mcp_server.city_ops.incident_verification_approval_request_read_surface import (
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
    build_incident_verification_approval_request_read_surface,
)
from mcp_server.city_ops.incident_verification_human_operator_approval_request import (
    INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    SELECTED_TEXT_BOUNDARY_KEY,
    build_incident_verification_human_operator_approval_request,
)
from mcp_server.city_ops.incident_verification_package_review_decision import (
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME,
    build_incident_verification_package_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_validator() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_chain(tmp_path: Path) -> dict:
    decision = build_incident_verification_package_review_decision()
    (tmp_path / INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )
    request = build_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)
    (tmp_path / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )
    surface = build_incident_verification_approval_request_read_surface(artifact_dir=tmp_path)
    (tmp_path / INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )
    gate = build_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)
    (tmp_path / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )
    return gate


def valid_candidate_record(gate: dict | None = None) -> dict:
    source = gate or build_incident_verification_approval_record_schema_gate()
    boundary = source["selected_text_boundary"]
    return {
        "schema": FUTURE_RECORD_SCHEMA_NAME,
        "record_status": APPROVAL_RECORD_ALLOWED_STATUS,
        "source_gate_id": source["gate_id"],
        "source_gate_digest_sha256": digest(source),
        "source_safe_claim": INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
        "source_surface_id": source["source_surface_id"],
        "source_request_id": source["source_request_id"],
        "source_surface_digest_sha256": source["source_surface_digest_sha256"],
        "selected_text_boundary_key": boundary["key"],
        "approved_text_boundary": boundary["candidate_text_boundary"],
        "exact_approved_text": boundary["candidate_text_value"],
        "human_operator_approval_recorded": True,
        "human_operator_approval_reference": "operator-review-ref-incident-001",
        "approval_timestamp_utc": "2026-05-20T06:35:00Z",
        "pre_approval_checks_passed": [
            {
                "check": check,
                "passed": True,
                "evidence_reference": f"incident-precheck-evidence:{check}",
            }
            for check in REQUIRED_PRE_APPROVAL_CHECKS
        ],
        "redaction_and_authority_checks_passed": [
            {
                "check": check,
                "passed": True,
                "evidence_reference": f"incident-redaction-authority-evidence:{check}",
                "authorizes_delivery_or_publication": False,
                "authorizes_incident_authority_claim": False,
                "authorizes_execution_market_action": False,
            }
            for check in REDACTION_AND_AUTHORITY_REQUIREMENTS
        ],
        "incident_authority_limits": INCIDENT_AUTHORITY_LIMITS,
        "authorized_delivery_path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
        "approval_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "approvals_not_granted": list(FUTURE_RECORD_MUST_KEEP_FALSE),
        "still_blocked_claims": source["still_blocked_claims"],
        "future_record_must_keep_false": {flag: False for flag in FUTURE_RECORD_MUST_KEEP_FALSE},
    }


def test_validator_matches_persisted_artifact_and_loader():
    validator = build_incident_verification_approval_record_validator()

    assert validator == read_validator()
    assert load_incident_verification_approval_record_validator() == validator
    assert validator["schema"] == INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SCHEMA
    assert validator["validator_status"] == VALIDATOR_STATUS
    assert INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM in validator["safe_to_claim"]
    assert INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM in validator["safe_to_claim"]


def test_validator_contract_creates_no_approval_and_satisfies_no_future_fields():
    validator = build_incident_verification_approval_record_validator()

    assert [field["field"] for field in validator["record_field_contract"]] == (
        APPROVAL_RECORD_REQUIRED_FIELDS
    )
    assert all(
        field["satisfied_by_validator_artifact"] is False
        for field in validator["record_field_contract"]
    )
    assert [item["check"] for item in validator["precheck_evidence_contract"]] == (
        REQUIRED_PRE_APPROVAL_CHECKS
    )
    assert [item["check"] for item in validator["redaction_authority_evidence_contract"]] == (
        REDACTION_AND_AUTHORITY_REQUIREMENTS
    )
    assert all(value is False for value in validator["readiness"].values())
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in validator["do_not_claim_yet"]
        assert claim not in validator["safe_to_claim"]


def test_valid_future_candidate_record_only_approves_selected_incident_label_boundary():
    record = valid_candidate_record()

    result = validate_incident_verification_human_operator_approval_record(record)

    assert result == {
        "record_valid": True,
        "validated_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "selected_text_boundary_key": SELECTED_TEXT_BOUNDARY_KEY,
        "exact_text_approved": "One-location incident state snapshot",
        "customer_delivery_authorized": False,
        "publication_authorized": False,
        "dispatch_authorized": False,
        "reputation_authorized": False,
        "runtime_or_acontext_authorized": False,
        "incident_authority_authorized": False,
        "exact_gps_or_raw_metadata_authorized": False,
        "raw_transcript_authority_authorized": False,
    }


def test_write_validator_persists_valid_artifact(tmp_path):
    seed_source_chain(tmp_path)

    path = write_incident_verification_approval_record_validator(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME
    assert load_incident_verification_approval_record_validator(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_gate_human_approval_promotion_fails_closed():
    gate = copy.deepcopy(build_incident_verification_approval_record_schema_gate())
    gate["current_gate_values"]["human_operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="source promoted current value human_operator_approval_recorded"):
        build_incident_verification_approval_record_validator(source_gate=gate)


def test_candidate_record_text_drift_fails_closed():
    record = valid_candidate_record()
    record["exact_approved_text"] = "Different incident label"

    with pytest.raises(CityOpsContractError, match="approved text drift"):
        validate_incident_verification_human_operator_approval_record(record)


def test_candidate_record_delivery_authorization_fails_closed():
    record = valid_candidate_record()
    record["authorized_delivery_path"] = "email_customer_directly"

    with pytest.raises(CityOpsContractError, match="delivery path not allowed"):
        validate_incident_verification_human_operator_approval_record(record)


def test_candidate_record_missing_precheck_evidence_fails_closed():
    record = valid_candidate_record()
    record["pre_approval_checks_passed"][0]["evidence_reference"] = ""

    with pytest.raises(CityOpsContractError, match="pre_approval_checks_passed evidence reference"):
        validate_incident_verification_human_operator_approval_record(record)


def test_candidate_record_incident_authority_claim_fails_closed():
    record = valid_candidate_record()
    record["redaction_and_authority_checks_passed"][0]["authorizes_incident_authority_claim"] = True

    with pytest.raises(CityOpsContractError, match="forbidden authority authorizes_incident_authority_claim"):
        validate_incident_verification_human_operator_approval_record(record)


def test_candidate_record_promoted_false_flag_fails_closed():
    record = valid_candidate_record()
    record["future_record_must_keep_false"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="promoted false flag dispatch_enabled"):
        validate_incident_verification_human_operator_approval_record(record)


def test_candidate_record_public_route_field_fails_closed():
    record = valid_candidate_record()
    record["public_route_ready"] = True

    with pytest.raises(CityOpsContractError, match="forbidden promotion public_route_ready"):
        validate_incident_verification_human_operator_approval_record(record)


def test_candidate_record_coordinate_leak_fails_closed():
    record = valid_candidate_record()
    record["operator_note"] = "latitude value must never appear"

    with pytest.raises(CityOpsContractError, match="leaked coordinate"):
        validate_incident_verification_human_operator_approval_record(record)
