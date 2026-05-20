import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_approval_record_schema_gate import (
    FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    FUTURE_RECORD_MUST_KEEP_FALSE,
    GATE_STATUS,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA,
    REQUIRED_BLOCKED_CLAIMS,
    build_incident_verification_approval_record_schema_gate,
    load_incident_verification_approval_record_schema_gate,
    write_incident_verification_approval_record_schema_gate,
)
from mcp_server.city_ops.incident_verification_approval_request_read_surface import (
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
    build_incident_verification_approval_request_read_surface,
)
from mcp_server.city_ops.incident_verification_human_operator_approval_request import (
    AUTHORIZED_DELIVERY_PATH,
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


def read_gate() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_chain(tmp_path: Path) -> None:
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


def test_schema_gate_matches_persisted_artifact_and_loader():
    gate = build_incident_verification_approval_record_schema_gate()

    assert gate == read_gate()
    assert load_incident_verification_approval_record_schema_gate() == gate
    assert gate["schema"] == INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA
    assert gate["gate_status"] == GATE_STATUS
    assert gate["source_surface_file"] == INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME
    assert INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM in gate["safe_to_claim"]
    assert INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM in gate["safe_to_claim"]


def test_gate_names_future_incident_record_fields_without_satisfying_them():
    gate = build_incident_verification_approval_record_schema_gate()
    fields = gate["future_approval_record_required_fields"]

    assert [field["field"] for field in fields] == FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS
    assert all(field["required_in_future_record"] is True for field in fields)
    assert all(field["satisfied_by_this_gate"] is False for field in fields)

    field_map = {field["field"]: field for field in fields}
    assert field_map["selected_text_boundary_key"]["expected_value_or_constraint"] == SELECTED_TEXT_BOUNDARY_KEY
    assert field_map["exact_approved_text"]["expected_value_or_constraint"] == (
        "One-location incident state snapshot"
    )
    assert field_map["approval_scope"]["expected_value_or_constraint"] == (
        "incident_verification_text_boundary_only_not_customer_delivery_publication_dispatch_or_incident_authority"
    )
    assert field_map["approvals_not_granted"]["expected_value_or_constraint"] == FUTURE_RECORD_MUST_KEEP_FALSE


def test_selected_boundary_prechecks_and_redactions_are_not_approval():
    gate = build_incident_verification_approval_record_schema_gate()
    boundary = gate["selected_text_boundary"]

    assert boundary["key"] == SELECTED_TEXT_BOUNDARY_KEY
    assert boundary["candidate_text_boundary"] == "internal_package_label_only"
    assert boundary["candidate_text_value"] == "One-location incident state snapshot"
    assert boundary["selected_text_boundary_approved_here"] is False
    assert boundary["human_operator_approval_recorded_here"] is False
    assert boundary["incident_authority_claim_authorized_here"] is False

    assert [item["check"] for item in gate["pre_approval_contract"]] == REQUIRED_PRE_APPROVAL_CHECKS
    assert all(item["required_in_future_approval_record"] is True for item in gate["pre_approval_contract"])
    assert all(item["passed_by_this_gate"] is False for item in gate["pre_approval_contract"])
    assert all(
        item["authorizes_execution_market_action_here"] is False for item in gate["pre_approval_contract"]
    )

    assert [item["check"] for item in gate["redaction_and_authority_contract"]] == (
        REDACTION_AND_AUTHORITY_REQUIREMENTS
    )
    assert all(
        item["required_in_future_approval_record"] is True
        for item in gate["redaction_and_authority_contract"]
    )
    assert all(item["passed_by_this_gate"] is False for item in gate["redaction_and_authority_contract"])
    assert all(
        item["authorizes_incident_authority_claim_here"] is False
        for item in gate["redaction_and_authority_contract"]
    )


def test_current_gate_values_and_false_flags_block_delivery_incident_authority_and_runtime_claims():
    gate = build_incident_verification_approval_record_schema_gate()

    assert gate["current_gate_values"] == {
        "human_operator_approval_recorded": False,
        "selected_text_boundary_approved": False,
        "approved_text_boundary_recorded": False,
        "pre_approval_checks_passed": False,
        "redaction_and_authority_checks_passed": False,
        "incident_authority_claim_authorized": False,
        "authorized_delivery_path": AUTHORIZED_DELIVERY_PATH,
        "customer_delivery_path_authorized": False,
        "operator_publish_approval_recorded": False,
        "publication_approved": False,
    }
    for flag in FUTURE_RECORD_MUST_KEEP_FALSE:
        assert flag in gate["future_record_must_keep_false"]
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in gate["do_not_claim_yet"]
        assert claim not in gate["safe_to_claim"]
    assert gate["still_blocked_claims"] == gate["do_not_claim_yet"]
    assert "incident_verification_emergency_response_ready" not in gate["safe_to_claim"]
    assert "incident_verification_exact_gps_or_raw_metadata_release_ready" not in gate["safe_to_claim"]


def test_write_schema_gate_persists_valid_artifact(tmp_path):
    seed_source_chain(tmp_path)

    path = write_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME
    assert load_incident_verification_approval_record_schema_gate(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_surface_human_approval_promotion_fails_closed():
    surface = copy.deepcopy(build_incident_verification_approval_request_read_surface())
    surface["approval_request_snapshot"]["human_operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="source snapshot promoted human_operator_approval_recorded"):
        build_incident_verification_approval_record_schema_gate(source_surface=surface)


def test_source_surface_redaction_pass_fails_closed():
    surface = copy.deepcopy(build_incident_verification_approval_request_read_surface())
    cards = {card["card"]: card for card in surface["operator_cards"]}
    cards["redaction_and_authority_requirements"]["values"][0]["passed_here"] = True

    with pytest.raises(CityOpsContractError, match="source redaction promoted passed_here"):
        build_incident_verification_approval_record_schema_gate(source_surface=surface)


def test_source_surface_delivery_path_expansion_fails_closed():
    surface = copy.deepcopy(build_incident_verification_approval_request_read_surface())
    cards = {card["card"]: card for card in surface["operator_cards"]}
    cards["authorized_delivery_path"]["values"]["customer_delivery_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source delivery promoted customer_delivery_allowed"):
        build_incident_verification_approval_record_schema_gate(source_surface=surface)


def test_source_surface_forbidden_safe_claim_fails_closed():
    surface = copy.deepcopy(build_incident_verification_approval_request_read_surface())
    surface["safe_to_claim"].append("emergency_response_ready")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_incident_verification_approval_record_schema_gate(source_surface=surface)


def test_loader_fails_closed_on_future_field_satisfied(tmp_path):
    seed_source_chain(tmp_path)
    gate = build_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)
    gate["future_approval_record_required_fields"][0]["satisfied_by_this_gate"] = True
    (tmp_path / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="satisfied a future field"):
        load_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_current_approval_flip(tmp_path):
    seed_source_chain(tmp_path)
    gate = build_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)
    gate["current_gate_values"]["human_operator_approval_recorded"] = True
    (tmp_path / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted current value human_operator_approval_recorded"):
        load_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_incident_authority_claim(tmp_path):
    seed_source_chain(tmp_path)
    gate = build_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)
    gate["redaction_and_authority_contract"][0]["authorizes_incident_authority_claim_here"] = True
    (tmp_path / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted redaction authorizes_incident_authority_claim_here"):
        load_incident_verification_approval_record_schema_gate(artifact_dir=tmp_path)
