import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_single_boundary_approval_record_schema_gate import (
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
    AUTHORIZED_DELIVERY_PATH,
    FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    FUTURE_RECORD_MUST_KEEP_FALSE,
    REQUIRED_REDACTION_CHECKS,
    build_aas_single_boundary_approval_record_schema_gate,
)
from mcp_server.city_ops.aas_single_boundary_human_operator_approval_request import (
    SELECTED_BOUNDARY_KEY,
)
from mcp_server.city_ops.aas_single_boundary_operator_review_brief import (
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA,
    BRIEF_STATUS,
    CURRENT_BRIEF_VALUES,
    HUMAN_REVIEW_CHECKLIST,
    REQUIRED_BLOCKED_CLAIMS,
    build_aas_single_boundary_operator_review_brief,
    load_aas_single_boundary_operator_review_brief,
    write_aas_single_boundary_operator_review_brief,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_brief() -> dict:
    with (ARTIFACT_DIR / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_gate(tmp_path: Path) -> None:
    gate = build_aas_single_boundary_approval_record_schema_gate()
    (tmp_path / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )


def test_operator_review_brief_matches_persisted_artifact():
    brief = build_aas_single_boundary_operator_review_brief()

    assert brief == read_brief()
    assert load_aas_single_boundary_operator_review_brief() == brief
    assert brief["schema"] == AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA
    assert brief["scope"] == "internal_admin_operator_review_brief_for_pending_single_boundary_only"
    assert brief["brief_status"] == BRIEF_STATUS
    assert AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM in brief["safe_to_claim"]
    assert AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM in brief["safe_to_claim"]


def test_brief_keeps_single_boundary_unapproved_and_exact():
    brief = build_aas_single_boundary_operator_review_brief()
    boundary = brief["selected_boundary"]

    assert boundary["key"] == SELECTED_BOUNDARY_KEY == "compliance_desk"
    assert boundary["text_boundary_under_review"] == "internal_package_label_only"
    assert boundary["exact_text_under_review"] == "Visible posting / notice compliance snapshot"
    assert boundary["selected_boundary_approved_by_this_brief"] is False
    assert boundary["human_operator_approval_recorded_by_this_brief"] is False


def test_human_review_checklist_requires_operator_action_without_satisfying_it():
    brief = build_aas_single_boundary_operator_review_brief()
    checklist = brief["human_review_checklist"]

    assert [item["check"] for item in checklist] == HUMAN_REVIEW_CHECKLIST
    assert all(item["required_for_future_human_record"] is True for item in checklist)
    assert all(item["satisfied_by_this_brief"] is False for item in checklist)
    assert all(item["operator_action_required"] is True for item in checklist)


def test_redactions_and_future_fields_are_not_satisfied_by_brief():
    brief = build_aas_single_boundary_operator_review_brief()

    assert [item["check"] for item in brief["redaction_review_items"]] == REQUIRED_REDACTION_CHECKS
    assert all(item["passed_by_this_brief"] is False for item in brief["redaction_review_items"])
    assert [field["field"] for field in brief["future_record_required_fields"]] == (
        FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS
    )
    assert all(
        field["satisfied_by_this_gate"] is False
        for field in brief["future_record_required_fields"]
    )


def test_current_values_and_false_flags_block_customer_public_runtime_claims():
    brief = build_aas_single_boundary_operator_review_brief()

    assert brief["current_brief_values"] == CURRENT_BRIEF_VALUES
    assert brief["current_brief_values"]["authorized_delivery_path"] == AUTHORIZED_DELIVERY_PATH
    for flag in FUTURE_RECORD_MUST_KEEP_FALSE:
        assert flag in brief["future_record_must_keep_false"]
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in brief["do_not_claim_yet"]
        assert claim not in brief["safe_to_claim"]
    assert brief["still_blocked_claims"] == brief["do_not_claim_yet"]


def test_write_brief_persists_valid_artifact(tmp_path):
    seed_source_gate(tmp_path)

    path = write_aas_single_boundary_operator_review_brief(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME
    assert load_aas_single_boundary_operator_review_brief(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_gate_human_approval_promotion_fails_closed():
    gate = build_aas_single_boundary_approval_record_schema_gate()
    gate["selected_boundary"] = copy.deepcopy(gate["selected_boundary"])
    gate["selected_boundary"]["human_operator_approval_recorded_here"] = True

    with pytest.raises(CityOpsContractError, match="recorded human approval"):
        build_aas_single_boundary_operator_review_brief(source_gate=gate)


def test_source_gate_future_field_satisfaction_fails_closed():
    gate = build_aas_single_boundary_approval_record_schema_gate()
    gate["future_approval_record_required_fields"] = copy.deepcopy(
        gate["future_approval_record_required_fields"]
    )
    gate["future_approval_record_required_fields"][0]["satisfied_by_this_gate"] = True

    with pytest.raises(CityOpsContractError, match="satisfied future approval field"):
        build_aas_single_boundary_operator_review_brief(source_gate=gate)


def test_source_gate_redaction_pass_fails_closed():
    gate = build_aas_single_boundary_approval_record_schema_gate()
    gate["redaction_contract"] = copy.deepcopy(gate["redaction_contract"])
    gate["redaction_contract"][0]["passed_by_this_gate"] = True

    with pytest.raises(CityOpsContractError, match="passed redactions"):
        build_aas_single_boundary_operator_review_brief(source_gate=gate)


def test_loader_fails_closed_on_checklist_satisfied(tmp_path):
    brief = build_aas_single_boundary_operator_review_brief()
    brief["human_review_checklist"][0]["satisfied_by_this_brief"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME).write_text(
        json.dumps(brief), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="satisfied checklist item"):
        load_aas_single_boundary_operator_review_brief(artifact_dir=tmp_path)


def test_loader_fails_closed_on_current_delivery_promotion(tmp_path):
    brief = build_aas_single_boundary_operator_review_brief()
    brief["current_brief_values"]["customer_delivery_path_authorized"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME).write_text(
        json.dumps(brief), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted current value"):
        load_aas_single_boundary_operator_review_brief(artifact_dir=tmp_path)


def test_loader_fails_closed_on_redaction_passed_by_brief(tmp_path):
    brief = build_aas_single_boundary_operator_review_brief()
    brief["redaction_review_items"][0]["passed_by_this_brief"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME).write_text(
        json.dumps(brief), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="passed redactions"):
        load_aas_single_boundary_operator_review_brief(artifact_dir=tmp_path)
