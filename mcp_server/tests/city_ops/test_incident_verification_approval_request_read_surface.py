import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.incident_verification_approval_request_read_surface import (
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SCHEMA,
    SURFACE_BLOCKED_CLAIMS,
    SURFACE_FALSE_FLAGS,
    build_incident_verification_approval_request_read_surface,
    load_incident_verification_approval_request_read_surface,
    write_incident_verification_approval_request_read_surface,
)
from mcp_server.city_ops.incident_verification_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    build_incident_verification_human_operator_approval_request,
)
from mcp_server.city_ops.incident_verification_package_review_decision import (
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME,
    build_incident_verification_package_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_surface() -> dict:
    with (ARTIFACT_DIR / INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME).open(
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


def test_read_surface_matches_persisted_artifact_and_loader():
    surface = build_incident_verification_approval_request_read_surface()

    assert surface == read_surface()
    assert load_incident_verification_approval_request_read_surface() == surface
    assert surface["schema"] == INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SCHEMA
    assert surface["source_request_file"] == INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    assert INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in surface["safe_to_claim"]
    assert INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM in surface["safe_to_claim"]


def test_surface_preserves_pending_one_boundary_request_without_approval_or_incident_authority():
    surface = build_incident_verification_approval_request_read_surface()
    snapshot = surface["approval_request_snapshot"]

    assert snapshot["approval_request_status"] == APPROVAL_REQUEST_STATUS
    assert snapshot["selected_text_boundary_count"] == 1
    assert snapshot["candidate_text_boundary"] == "internal_package_label_only"
    assert snapshot["human_operator_approval_recorded"] is False
    assert snapshot["selected_text_boundary_approved"] is False
    assert snapshot["customer_delivery_authorized"] is False
    assert snapshot["publication_authorized"] is False
    assert snapshot["incident_authority_claim_authorized"] is False

    cards = {card["card"]: card for card in surface["operator_cards"]}
    assert cards["pending_boundary"]["values"]["selected_text_boundary_approved"] is False
    assert cards["pending_boundary"]["values"]["human_operator_approval_recorded"] is False
    assert cards["pending_boundary"]["values"]["incident_authority_claim_authorized"] is False


def test_pre_approval_redaction_and_incident_authority_cards_are_visible_but_unmet():
    surface = build_incident_verification_approval_request_read_surface()
    cards = {card["card"]: card for card in surface["operator_cards"]}

    pre_checks = cards["pre_approval_checks"]["values"]
    assert [item["check"] for item in pre_checks] == REQUIRED_PRE_APPROVAL_CHECKS
    for item in pre_checks:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["approval_granted"] is False
        assert item["customer_delivery_allowed"] is False
        assert item["publication_allowed"] is False
        assert item["execution_market_action_authorized"] is False

    redactions = cards["redaction_and_authority_requirements"]["values"]
    assert [item["check"] for item in redactions] == REDACTION_AND_AUTHORITY_REQUIREMENTS
    assert "official_incident_report_language_absent" in REDACTION_AND_AUTHORITY_REQUIREMENTS
    assert "fault_or_liability_assignment_language_absent" in REDACTION_AND_AUTHORITY_REQUIREMENTS
    for item in redactions:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["authorizes_delivery_or_publication"] is False
        assert item["authorizes_incident_authority_claim"] is False


def test_access_mount_delivery_and_surface_flags_stay_blocked():
    surface = build_incident_verification_approval_request_read_surface()
    cards = {card["card"]: card for card in surface["operator_cards"]}

    assert surface["access_policy"]["audience"] == "internal_admin_only"
    assert surface["access_policy"]["network_route_registered"] is False
    assert surface["access_policy"]["customer_visible"] is False
    assert surface["mount_contract"]["network_route_registered"] is False

    delivery = cards["authorized_delivery_path"]["values"]
    assert delivery["path"] == "none_until_separate_human_operator_approval_record"
    for flag in [
        "path_recorded",
        "customer_delivery_allowed",
        "publication_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "controlled_pilot_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
        "raw_transcript_authority_allowed",
        "emergency_response_allowed",
        "safety_certification_allowed",
        "repair_diagnosis_allowed",
        "repair_completion_allowed",
        "insurance_adjustment_allowed",
        "sla_uptime_allowed",
        "official_incident_report_allowed",
        "fault_or_liability_assignment_allowed",
    ]:
        assert delivery[flag] is False

    for flag, expected in SURFACE_FALSE_FLAGS.items():
        assert surface[flag] is expected
        assert surface["surface_flags"][flag] is expected


def test_claim_boundaries_preserve_all_blocked_incident_claims():
    surface = build_incident_verification_approval_request_read_surface()

    assert not set(surface["safe_to_claim"]) & set(surface["do_not_claim_yet"])
    assert surface["still_blocked_claims"] == surface["do_not_claim_yet"]
    for claim in SURFACE_BLOCKED_CLAIMS:
        assert claim in surface["do_not_claim_yet"]
        assert claim not in surface["safe_to_claim"]
    assert "incident_verification_approval_request_read_surface_authorizes_customer_delivery" not in surface[
        "safe_to_claim"
    ]
    assert "incident_verification_approval_request_read_surface_authorizes_exact_gps_or_raw_metadata" not in surface[
        "safe_to_claim"
    ]
    assert (
        "incident_verification_approval_request_read_surface_authorizes_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_claims"
        not in surface["safe_to_claim"]
    )


def test_write_read_surface_persists_valid_artifact(tmp_path):
    seed_source_chain(tmp_path)

    path = write_incident_verification_approval_request_read_surface(artifact_dir=tmp_path)

    assert path == tmp_path / INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME
    assert load_incident_verification_approval_request_read_surface(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_human_approval_promotion_fails_closed():
    request = copy.deepcopy(build_incident_verification_human_operator_approval_request())
    request["human_operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="source promoted human_operator_approval_recorded"):
        build_incident_verification_approval_request_read_surface(source_request=request)


def test_source_incident_authority_promotion_fails_closed():
    request = copy.deepcopy(build_incident_verification_human_operator_approval_request())
    request["redaction_and_authority_requirements"][-2]["authorizes_incident_authority_claim"] = True

    with pytest.raises(CityOpsContractError, match="source redaction promoted authorizes_incident_authority_claim"):
        build_incident_verification_approval_request_read_surface(source_request=request)


def test_source_forbidden_safe_claim_fails_closed():
    request = copy.deepcopy(build_incident_verification_human_operator_approval_request())
    request["safe_to_claim"].append("emergency_response_ready")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_incident_verification_approval_request_read_surface(source_request=request)


def test_loader_fails_closed_on_surface_approval_flag(tmp_path):
    seed_source_chain(tmp_path)
    surface = build_incident_verification_approval_request_read_surface(artifact_dir=tmp_path)
    surface["surface_is_human_approval_record"] = True
    (tmp_path / INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted surface_is_human_approval_record"):
        load_incident_verification_approval_request_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_network_route_registration(tmp_path):
    seed_source_chain(tmp_path)
    surface = build_incident_verification_approval_request_read_surface(artifact_dir=tmp_path)
    surface["mount_contract"]["network_route_registered"] = True
    (tmp_path / INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="registered network route"):
        load_incident_verification_approval_request_read_surface(artifact_dir=tmp_path)
