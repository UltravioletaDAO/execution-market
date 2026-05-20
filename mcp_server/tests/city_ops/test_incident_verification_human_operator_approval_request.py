import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    REQUEST_BLOCKED_CLAIMS,
    REQUEST_FALSE_TOP_LEVEL_FLAGS,
    SELECTED_TEXT_BOUNDARY_KEY,
    build_incident_verification_human_operator_approval_request,
    load_incident_verification_human_operator_approval_request,
    write_incident_verification_human_operator_approval_request,
)
from mcp_server.city_ops.incident_verification_package_review_decision import (
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME,
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
    NEXT_REQUIRED_GATE,
    SELECTED_INTERNAL_LABEL,
    build_incident_verification_package_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_package_review(tmp_path: Path) -> None:
    decision = build_incident_verification_package_review_decision()
    (tmp_path / INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )


def test_approval_request_matches_persisted_artifact_and_loader():
    packet = build_incident_verification_human_operator_approval_request()

    assert packet == read_packet()
    assert load_incident_verification_human_operator_approval_request() == packet
    assert packet["schema"] == INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA
    assert packet["scope"] == "internal_admin_incident_verification_human_operator_approval_request_only"
    assert packet["source_package_review_file"] == INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME
    assert INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM in packet["safe_to_claim"]
    assert INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]


def test_request_names_exactly_one_incident_boundary_without_approval():
    packet = build_incident_verification_human_operator_approval_request()
    boundary = packet["selected_text_boundary"]

    assert packet["approval_request_status"] == APPROVAL_REQUEST_STATUS
    assert packet["selected_text_boundary_count"] == 1
    assert packet["human_operator_approval_recorded"] is False
    assert packet["selected_text_boundary_approved"] is False
    assert boundary["key"] == SELECTED_TEXT_BOUNDARY_KEY
    assert boundary["candidate_text_boundary"] == "internal_package_label_only"
    assert boundary["candidate_text_value"] == SELECTED_INTERNAL_LABEL
    assert boundary["candidate_text_fields"] == ["selected_internal_label"]
    assert boundary["source_customer_copy_approved"] is False
    assert boundary["source_next_gate_satisfied"] is False
    assert boundary["selected_text_boundary_approved"] is False
    assert boundary["human_operator_approval_recorded"] is False
    assert (
        boundary[
            "emergency_safety_repair_insurance_sla_official_report_fault_or_liability_authorized_by_boundary"
        ]
        is False
    )


def test_pre_approval_checks_redaction_and_follow_on_requirements_are_not_approval():
    packet = build_incident_verification_human_operator_approval_request()

    assert [item["check"] for item in packet["pre_approval_checks"]] == REQUIRED_PRE_APPROVAL_CHECKS
    assert NEXT_REQUIRED_GATE == "separate_human_operator_approval_artifact_for_one_exact_incident_verification_text_boundary"
    assert "follow_on_escalation_boundaries_still_non_authorizing" in REQUIRED_PRE_APPROVAL_CHECKS
    assert "raw_transcript_authority_absent_before_any_approval" in REQUIRED_PRE_APPROVAL_CHECKS
    for item in packet["pre_approval_checks"]:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["approval_granted"] is False
        assert item["customer_delivery_allowed"] is False
        assert item["publication_allowed"] is False
        assert item["execution_market_action_authorized"] is False

    assert [item["check"] for item in packet["redaction_and_authority_requirements"]] == (
        REDACTION_AND_AUTHORITY_REQUIREMENTS
    )
    assert "official_incident_report_language_absent" in REDACTION_AND_AUTHORITY_REQUIREMENTS
    assert "fault_or_liability_assignment_language_absent" in REDACTION_AND_AUTHORITY_REQUIREMENTS
    for item in packet["redaction_and_authority_requirements"]:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["authorizes_delivery_or_publication"] is False
        assert item["authorizes_incident_authority_claim"] is False


def test_delivery_path_and_all_customer_public_runtime_incident_flags_stay_blocked():
    packet = build_incident_verification_human_operator_approval_request()

    assert packet["authorized_delivery_path"] == {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "no_customer_delivery_no_publication_no_dispatch_no_incident_authority",
        "path_recorded": False,
        "customer_delivery_allowed": False,
        "publication_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "controlled_pilot_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
        "raw_transcript_authority_allowed": False,
        "emergency_response_allowed": False,
        "safety_certification_allowed": False,
        "repair_diagnosis_allowed": False,
        "repair_completion_allowed": False,
        "insurance_adjustment_allowed": False,
        "sla_uptime_allowed": False,
        "official_incident_report_allowed": False,
        "fault_or_liability_assignment_allowed": False,
    }
    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        assert packet[flag] is expected


def test_claim_boundaries_preserve_all_blocked_incident_claims():
    packet = build_incident_verification_human_operator_approval_request()

    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert packet["still_blocked_claims"] == packet["do_not_claim_yet"]
    for claim in REQUEST_BLOCKED_CLAIMS:
        assert claim in packet["do_not_claim_yet"]
        assert claim not in packet["safe_to_claim"]
    assert "incident_verification_customer_delivery_approved" not in packet["safe_to_claim"]
    assert "incident_verification_emergency_response_ready" not in packet["safe_to_claim"]
    assert "incident_verification_official_incident_report_ready" not in packet["safe_to_claim"]
    assert "incident_verification_fault_or_liability_assignment_ready" not in packet[
        "safe_to_claim"
    ]


def test_write_approval_request_persists_valid_artifact(tmp_path):
    seed_source_package_review(tmp_path)

    path = write_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    assert load_incident_verification_human_operator_approval_request(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_package_review_promotion_fails_closed():
    source = build_incident_verification_package_review_decision()
    source = copy.deepcopy(source)
    source["next_gate_satisfied"] = True

    with pytest.raises(CityOpsContractError, match="source next gate promoted"):
        build_incident_verification_human_operator_approval_request(
            source_package_review=source
        )


def test_source_follow_on_authorization_fails_closed():
    source = build_incident_verification_package_review_decision()
    source = copy.deepcopy(source)
    source["follow_on_escalation_boundaries"][0]["execution_market_action_authorized"] = True

    with pytest.raises(CityOpsContractError, match="source follow-on boundary drift"):
        build_incident_verification_human_operator_approval_request(
            source_package_review=source
        )


def test_source_forbidden_safe_claim_fails_closed():
    source = build_incident_verification_package_review_decision()
    source = copy.deepcopy(source)
    source["safe_to_claim"].append("emergency_response_ready")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_incident_verification_human_operator_approval_request(
            source_package_review=source
        )


def test_loader_fails_closed_on_human_approval_flip(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)
    packet["human_operator_approval_recorded"] = True
    (tmp_path / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted human_operator_approval_recorded"):
        load_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_multiple_boundaries(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)
    packet["selected_text_boundary_count"] = 2
    (tmp_path / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exactly one boundary"):
        load_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_incident_authority_passing_itself(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)
    packet["redaction_and_authority_requirements"][-2]["authorizes_incident_authority_claim"] = True
    (tmp_path / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="redaction promoted authorizes_incident_authority_claim"):
        load_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_delivery_path_expansion(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)
    packet["authorized_delivery_path"]["official_incident_report_allowed"] = True
    (tmp_path / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="delivery path promoted official_incident_report_allowed"):
        load_incident_verification_human_operator_approval_request(artifact_dir=tmp_path)
