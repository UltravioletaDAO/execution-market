import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_single_boundary_approval_record_schema_gate import (
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA,
    FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    FUTURE_RECORD_MUST_KEEP_FALSE,
    GATE_STATUS,
    REQUIRED_BLOCKED_CLAIMS,
    build_aas_single_boundary_approval_record_schema_gate,
    load_aas_single_boundary_approval_record_schema_gate,
    write_aas_single_boundary_approval_record_schema_gate,
)
from mcp_server.city_ops.aas_single_boundary_human_operator_approval_request import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    AUTHORIZED_DELIVERY_PATH,
    REQUIRED_REDACTION_CHECKS,
    SELECTED_BOUNDARY_KEY,
    build_aas_single_boundary_human_operator_approval_request,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_gate() -> dict:
    with (ARTIFACT_DIR / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_request(tmp_path: Path) -> None:
    request = build_aas_single_boundary_human_operator_approval_request()
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )


def test_schema_gate_matches_persisted_artifact():
    gate = build_aas_single_boundary_approval_record_schema_gate()

    assert gate == read_gate()
    assert load_aas_single_boundary_approval_record_schema_gate() == gate
    assert gate["schema"] == AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA
    assert gate["scope"] == "internal_admin_schema_gate_for_future_human_approval_record_only"
    assert gate["gate_status"] == GATE_STATUS
    assert AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in gate[
        "safe_to_claim"
    ]
    assert AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM in gate[
        "safe_to_claim"
    ]


def test_gate_names_future_record_fields_without_satisfying_them():
    gate = build_aas_single_boundary_approval_record_schema_gate()
    fields = gate["future_approval_record_required_fields"]

    assert [field["field"] for field in fields] == FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS
    assert all(field["required_in_future_record"] is True for field in fields)
    assert all(field["satisfied_by_this_gate"] is False for field in fields)

    field_map = {field["field"]: field for field in fields}
    assert field_map["selected_boundary_key"]["expected_value_or_constraint"] == SELECTED_BOUNDARY_KEY
    assert field_map["exact_approved_text"]["expected_value_or_constraint"] == (
        "Visible posting / notice compliance snapshot"
    )
    assert field_map["approval_scope"]["expected_value_or_constraint"] == (
        "text_boundary_only_not_customer_delivery_or_publication"
    )
    assert field_map["approvals_not_granted"]["expected_value_or_constraint"] == (
        FUTURE_RECORD_MUST_KEEP_FALSE
    )


def test_selected_boundary_and_redaction_contract_are_not_approval():
    gate = build_aas_single_boundary_approval_record_schema_gate()
    boundary = gate["selected_boundary"]

    assert boundary["key"] == SELECTED_BOUNDARY_KEY == "compliance_desk"
    assert boundary["candidate_text_boundary"] == "internal_package_label_only"
    assert boundary["candidate_text_value"] == "Visible posting / notice compliance snapshot"
    assert boundary["selected_boundary_approved_here"] is False
    assert boundary["human_operator_approval_recorded_here"] is False

    assert [item["check"] for item in gate["redaction_contract"]] == REQUIRED_REDACTION_CHECKS
    assert all(item["required_in_future_approval_record"] is True for item in gate["redaction_contract"])
    assert all(item["passed_by_this_gate"] is False for item in gate["redaction_contract"])


def test_current_gate_values_and_false_flags_block_customer_public_runtime_claims():
    gate = build_aas_single_boundary_approval_record_schema_gate()

    assert gate["current_gate_values"] == {
        "human_operator_approval_recorded": False,
        "selected_boundary_approved": False,
        "approved_text_boundary_recorded": False,
        "redaction_checks_passed": False,
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


def test_write_schema_gate_persists_valid_artifact(tmp_path):
    seed_source_request(tmp_path)

    path = write_aas_single_boundary_approval_record_schema_gate(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME
    assert load_aas_single_boundary_approval_record_schema_gate(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_request_human_approval_promotion_fails_closed():
    request = build_aas_single_boundary_human_operator_approval_request()
    request["human_operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="already records approval"):
        build_aas_single_boundary_approval_record_schema_gate(source_request=request)


def test_source_request_selected_boundary_promotion_fails_closed():
    request = build_aas_single_boundary_human_operator_approval_request()
    request["selected_boundary"] = copy.deepcopy(request["selected_boundary"])
    request["selected_boundary"]["selected_boundary_approved"] = True

    with pytest.raises(CityOpsContractError, match="selected boundary approved"):
        build_aas_single_boundary_approval_record_schema_gate(source_request=request)


def test_source_request_redaction_pass_fails_closed():
    request = build_aas_single_boundary_human_operator_approval_request()
    request["redaction_requirements"] = copy.deepcopy(request["redaction_requirements"])
    request["redaction_requirements"][0]["passed_here"] = True

    with pytest.raises(CityOpsContractError, match="passed redactions"):
        build_aas_single_boundary_approval_record_schema_gate(source_request=request)


def test_source_request_delivery_path_expansion_fails_closed():
    request = build_aas_single_boundary_human_operator_approval_request()
    request["authorized_delivery_path"] = copy.deepcopy(request["authorized_delivery_path"])
    request["authorized_delivery_path"]["customer_delivery_allowed"] = True

    with pytest.raises(CityOpsContractError, match="promoted customer_delivery_allowed"):
        build_aas_single_boundary_approval_record_schema_gate(source_request=request)


def test_loader_fails_closed_on_future_field_satisfied(tmp_path):
    gate = build_aas_single_boundary_approval_record_schema_gate()
    gate["future_approval_record_required_fields"][0]["satisfied_by_this_gate"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="satisfied a future field"):
        load_aas_single_boundary_approval_record_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_current_approval_flip(tmp_path):
    gate = build_aas_single_boundary_approval_record_schema_gate()
    gate["current_gate_values"]["human_operator_approval_recorded"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted current value"):
        load_aas_single_boundary_approval_record_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_redaction_passed_by_gate(tmp_path):
    gate = build_aas_single_boundary_approval_record_schema_gate()
    gate["redaction_contract"][0]["passed_by_this_gate"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="passed redactions"):
        load_aas_single_boundary_approval_record_schema_gate(artifact_dir=tmp_path)
