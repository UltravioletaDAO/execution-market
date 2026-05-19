import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.document_handoff_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    REQUEST_BLOCKED_CLAIMS,
    REQUEST_FALSE_TOP_LEVEL_FLAGS,
    SELECTED_TEXT_BOUNDARY_KEY,
    build_document_handoff_human_operator_approval_request,
    load_document_handoff_human_operator_approval_request,
    write_document_handoff_human_operator_approval_request,
)
from mcp_server.city_ops.document_handoff_package_review_decision import (
    DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME,
    DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
    NEXT_REQUIRED_GATE,
    SELECTED_INTERNAL_LABEL,
    build_document_handoff_package_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    with (ARTIFACT_DIR / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_package_review(tmp_path: Path) -> None:
    decision = build_document_handoff_package_review_decision()
    (tmp_path / DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )


def test_approval_request_matches_persisted_artifact_and_loader():
    packet = build_document_handoff_human_operator_approval_request()

    assert packet == read_packet()
    assert load_document_handoff_human_operator_approval_request() == packet
    assert packet["schema"] == DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA
    assert packet["scope"] == "internal_admin_document_handoff_human_operator_approval_request_only"
    assert packet["source_package_review_file"] == DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME
    assert DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM in packet["safe_to_claim"]
    assert DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]


def test_request_names_exactly_one_document_handoff_boundary_without_approval():
    packet = build_document_handoff_human_operator_approval_request()
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


def test_pre_approval_checks_and_redaction_requirements_are_not_approval():
    packet = build_document_handoff_human_operator_approval_request()

    assert [item["check"] for item in packet["pre_approval_checks"]] == REQUIRED_PRE_APPROVAL_CHECKS
    assert NEXT_REQUIRED_GATE == "separate_human_operator_approval_artifact_for_one_exact_document_handoff_text_boundary"
    for item in packet["pre_approval_checks"]:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["approval_granted"] is False
        assert item["customer_delivery_allowed"] is False
        assert item["publication_allowed"] is False

    assert [item["check"] for item in packet["redaction_and_authority_requirements"]] == (
        REDACTION_AND_AUTHORITY_REQUIREMENTS
    )
    for item in packet["redaction_and_authority_requirements"]:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["authorizes_delivery_or_publication"] is False


def test_delivery_path_and_all_customer_public_runtime_flags_stay_blocked():
    packet = build_document_handoff_human_operator_approval_request()

    assert packet["authorized_delivery_path"] == {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "no_customer_delivery_no_publication_no_dispatch",
        "path_recorded": False,
        "customer_delivery_allowed": False,
        "publication_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "controlled_pilot_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed": False,
    }
    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        assert packet[flag] is expected


def test_claim_boundaries_preserve_all_blocked_claims():
    packet = build_document_handoff_human_operator_approval_request()

    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert packet["still_blocked_claims"] == packet["do_not_claim_yet"]
    for claim in REQUEST_BLOCKED_CLAIMS:
        assert claim in packet["do_not_claim_yet"]
        assert claim not in packet["safe_to_claim"]
    assert "document_handoff_customer_delivery_approved" not in packet["safe_to_claim"]
    assert "document_handoff_publication_approved" not in packet["safe_to_claim"]
    assert "document_handoff_legal_notarial_identity_acceptance_filing_custody_claim_ready" not in packet[
        "safe_to_claim"
    ]


def test_write_approval_request_persists_valid_artifact(tmp_path):
    seed_source_package_review(tmp_path)

    path = write_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)

    assert path == tmp_path / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    assert load_document_handoff_human_operator_approval_request(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_package_review_promotion_fails_closed():
    source = build_document_handoff_package_review_decision()
    source = copy.deepcopy(source)
    source["next_gate_satisfied"] = True

    with pytest.raises(CityOpsContractError, match="source next gate promoted"):
        build_document_handoff_human_operator_approval_request(
            source_package_review=source
        )


def test_source_forbidden_safe_claim_fails_closed():
    source = build_document_handoff_package_review_decision()
    source = copy.deepcopy(source)
    source["safe_to_claim"].append("customer_delivery_ready")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_document_handoff_human_operator_approval_request(
            source_package_review=source
        )


def test_loader_fails_closed_on_human_approval_flip(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)
    packet["human_operator_approval_recorded"] = True
    (tmp_path / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted human_operator_approval_recorded"):
        load_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_multiple_boundaries(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)
    packet["selected_text_boundary_count"] = 2
    (tmp_path / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exactly one boundary"):
        load_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_redaction_passing_itself(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)
    packet["redaction_and_authority_requirements"][0]["passed_here"] = True
    (tmp_path / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="redaction promoted passed_here"):
        load_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_delivery_path_expansion(tmp_path):
    seed_source_package_review(tmp_path)
    packet = build_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)
    packet["authorized_delivery_path"]["customer_delivery_allowed"] = True
    (tmp_path / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="delivery path promoted customer_delivery_allowed"):
        load_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)
