import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_single_boundary_approval_record_schema_gate import (
    FUTURE_RECORD_MUST_KEEP_FALSE,
    FUTURE_RECORD_SCHEMA_NAME,
    REQUIRED_REDACTION_CHECKS,
)
from mcp_server.city_ops.aas_single_boundary_operator_review_brief import (
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
    build_aas_single_boundary_operator_review_brief,
)
from mcp_server.city_ops.aas_single_boundary_approval_record_validator import (
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SCHEMA,
    APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
    APPROVAL_RECORD_ALLOWED_SCOPE,
    APPROVAL_RECORD_ALLOWED_STATUS,
    APPROVAL_RECORD_REQUIRED_FIELDS,
    REQUIRED_BLOCKED_CLAIMS,
    VALIDATOR_STATUS,
    build_aas_single_boundary_approval_record_validator,
    load_aas_single_boundary_approval_record_validator,
    validate_aas_single_boundary_human_operator_approval_record,
    write_aas_single_boundary_approval_record_validator,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_validator() -> dict:
    with (ARTIFACT_DIR / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_brief(tmp_path: Path) -> dict:
    brief = build_aas_single_boundary_operator_review_brief()
    (tmp_path / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME).write_text(
        json.dumps(brief), encoding="utf-8"
    )
    return brief


def valid_candidate_record(brief: dict | None = None) -> dict:
    source = brief or build_aas_single_boundary_operator_review_brief()
    boundary = source["selected_boundary"]
    return {
        "schema": FUTURE_RECORD_SCHEMA_NAME,
        "record_status": APPROVAL_RECORD_ALLOWED_STATUS,
        "source_brief_id": source["brief_id"],
        "source_brief_digest_sha256": _digest(source),
        "source_safe_claim": AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
        "source_request_id": source["source_gate_id"],
        "source_request_digest_sha256": source["source_gate_digest_sha256"],
        "selected_boundary_key": boundary["key"],
        "approved_text_boundary": boundary["text_boundary_under_review"],
        "exact_approved_text": boundary["exact_text_under_review"],
        "approved_text_fields": boundary["candidate_text_fields"],
        "human_operator_approval_recorded": True,
        "human_operator_approval_reference": "operator-review-ref-001",
        "approval_timestamp_utc": "2026-05-15T06:45:00Z",
        "redaction_checks_passed": [
            {"check": check, "passed": True, "evidence_reference": f"redaction-evidence:{check}"}
            for check in REQUIRED_REDACTION_CHECKS
        ],
        "authorized_delivery_path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
        "approval_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "approvals_not_granted": list(FUTURE_RECORD_MUST_KEEP_FALSE),
        "still_blocked_claims": source["still_blocked_claims"],
        "future_record_must_keep_false": {flag: False for flag in FUTURE_RECORD_MUST_KEEP_FALSE},
    }


def _digest(payload: dict) -> str:
    import hashlib

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_validator_matches_persisted_artifact():
    validator = build_aas_single_boundary_approval_record_validator()

    assert validator == read_validator()
    assert load_aas_single_boundary_approval_record_validator() == validator
    assert validator["schema"] == AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SCHEMA
    assert validator["validator_status"] == VALIDATOR_STATUS
    assert AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM in validator["safe_to_claim"]
    assert AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM in validator["safe_to_claim"]


def test_validator_contract_creates_no_approval_and_satisfies_no_future_fields():
    validator = build_aas_single_boundary_approval_record_validator()

    assert [field["field"] for field in validator["record_field_contract"]] == (
        APPROVAL_RECORD_REQUIRED_FIELDS
    )
    assert all(
        field["satisfied_by_validator_artifact"] is False
        for field in validator["record_field_contract"]
    )
    assert [item["check"] for item in validator["redaction_evidence_contract"]] == (
        REQUIRED_REDACTION_CHECKS
    )
    assert all(
        item["satisfied_by_validator_artifact"] is False
        for item in validator["redaction_evidence_contract"]
    )
    assert validator["allowed_delivery_path"] == APPROVAL_RECORD_ALLOWED_DELIVERY_PATH
    assert all(value is False for value in validator["readiness"].values())
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in validator["do_not_claim_yet"]
        assert claim not in validator["safe_to_claim"]


def test_valid_future_candidate_record_only_approves_selected_label_boundary():
    record = valid_candidate_record()

    result = validate_aas_single_boundary_human_operator_approval_record(record)

    assert result == {
        "record_valid": True,
        "validated_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "selected_boundary_key": "compliance_desk",
        "exact_text_approved": "Visible posting / notice compliance snapshot",
        "customer_delivery_authorized": False,
        "publication_authorized": False,
        "dispatch_authorized": False,
        "reputation_authorized": False,
        "runtime_or_acontext_authorized": False,
    }


def test_write_validator_persists_valid_artifact(tmp_path):
    seed_source_brief(tmp_path)

    path = write_aas_single_boundary_approval_record_validator(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME
    assert load_aas_single_boundary_approval_record_validator(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_brief_self_approval_fails_closed():
    brief = build_aas_single_boundary_operator_review_brief()
    brief["selected_boundary"] = copy.deepcopy(brief["selected_boundary"])
    brief["selected_boundary"]["human_operator_approval_recorded_by_this_brief"] = True

    with pytest.raises(CityOpsContractError, match="recorded human approval"):
        build_aas_single_boundary_approval_record_validator(source_brief=brief)


def test_candidate_record_text_drift_fails_closed():
    record = valid_candidate_record()
    record["exact_approved_text"] = "Different label"

    with pytest.raises(CityOpsContractError, match="approved text drift"):
        validate_aas_single_boundary_human_operator_approval_record(record)


def test_candidate_record_delivery_authorization_fails_closed():
    record = valid_candidate_record()
    record["authorized_delivery_path"] = "email_customer_directly"

    with pytest.raises(CityOpsContractError, match="delivery path not allowed"):
        validate_aas_single_boundary_human_operator_approval_record(record)


def test_candidate_record_missing_redaction_evidence_fails_closed():
    record = valid_candidate_record()
    record["redaction_checks_passed"][0]["evidence_reference"] = ""

    with pytest.raises(CityOpsContractError, match="redaction evidence reference"):
        validate_aas_single_boundary_human_operator_approval_record(record)


def test_candidate_record_promoted_false_flag_fails_closed():
    record = valid_candidate_record()
    record["future_record_must_keep_false"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="promoted false flag dispatch_enabled"):
        validate_aas_single_boundary_human_operator_approval_record(record)


def test_candidate_record_public_route_field_fails_closed():
    record = valid_candidate_record()
    record["public_route_ready"] = True

    with pytest.raises(CityOpsContractError, match="forbidden promotion public_route_ready"):
        validate_aas_single_boundary_human_operator_approval_record(record)
