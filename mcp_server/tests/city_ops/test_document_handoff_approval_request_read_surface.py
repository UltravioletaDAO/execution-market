import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.document_handoff_approval_request_read_surface import (
    DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
    DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SCHEMA,
    SURFACE_BLOCKED_CLAIMS,
    SURFACE_FALSE_FLAGS,
    build_document_handoff_approval_request_read_surface,
    load_document_handoff_approval_request_read_surface,
    write_document_handoff_approval_request_read_surface,
)
from mcp_server.city_ops.document_handoff_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    REQUIRED_PRE_APPROVAL_CHECKS,
    build_document_handoff_human_operator_approval_request,
)
from mcp_server.city_ops.document_handoff_package_review_decision import (
    DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME,
    build_document_handoff_package_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_surface() -> dict:
    with (ARTIFACT_DIR / DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_chain(tmp_path: Path) -> None:
    decision = build_document_handoff_package_review_decision()
    (tmp_path / DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )
    request = build_document_handoff_human_operator_approval_request(artifact_dir=tmp_path)
    (tmp_path / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )


def test_read_surface_matches_persisted_artifact_and_loader():
    surface = build_document_handoff_approval_request_read_surface()

    assert surface == read_surface()
    assert load_document_handoff_approval_request_read_surface() == surface
    assert surface["schema"] == DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SCHEMA
    assert surface["source_request_file"] == DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    assert DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in surface["safe_to_claim"]
    assert DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM in surface["safe_to_claim"]


def test_surface_preserves_pending_one_boundary_request_without_approval():
    surface = build_document_handoff_approval_request_read_surface()
    snapshot = surface["approval_request_snapshot"]

    assert snapshot["approval_request_status"] == APPROVAL_REQUEST_STATUS
    assert snapshot["selected_text_boundary_count"] == 1
    assert snapshot["candidate_text_boundary"] == "internal_package_label_only"
    assert snapshot["human_operator_approval_recorded"] is False
    assert snapshot["selected_text_boundary_approved"] is False
    assert snapshot["customer_delivery_authorized"] is False
    assert snapshot["publication_authorized"] is False

    cards = {card["card"]: card for card in surface["operator_cards"]}
    assert cards["pending_boundary"]["values"]["selected_text_boundary_approved"] is False
    assert cards["pending_boundary"]["values"]["human_operator_approval_recorded"] is False


def test_pre_approval_and_redaction_cards_are_visible_but_unmet():
    surface = build_document_handoff_approval_request_read_surface()
    cards = {card["card"]: card for card in surface["operator_cards"]}

    pre_checks = cards["pre_approval_checks"]["values"]
    assert [item["check"] for item in pre_checks] == REQUIRED_PRE_APPROVAL_CHECKS
    for item in pre_checks:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["approval_granted"] is False
        assert item["customer_delivery_allowed"] is False
        assert item["publication_allowed"] is False

    for item in cards["redaction_and_authority_requirements"]["values"]:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["authorizes_delivery_or_publication"] is False


def test_access_mount_delivery_and_surface_flags_stay_blocked():
    surface = build_document_handoff_approval_request_read_surface()
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
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed",
    ]:
        assert delivery[flag] is False

    for flag, expected in SURFACE_FALSE_FLAGS.items():
        assert surface[flag] is expected
        assert surface["surface_flags"][flag] is expected


def test_claim_boundaries_preserve_all_blocked_claims():
    surface = build_document_handoff_approval_request_read_surface()

    assert not set(surface["safe_to_claim"]) & set(surface["do_not_claim_yet"])
    assert surface["still_blocked_claims"] == surface["do_not_claim_yet"]
    for claim in SURFACE_BLOCKED_CLAIMS:
        assert claim in surface["do_not_claim_yet"]
        assert claim not in surface["safe_to_claim"]
    assert "document_handoff_approval_request_read_surface_authorizes_customer_delivery" not in surface[
        "safe_to_claim"
    ]
    assert "document_handoff_approval_request_read_surface_authorizes_exact_gps_or_raw_metadata" not in surface[
        "safe_to_claim"
    ]


def test_write_read_surface_persists_valid_artifact(tmp_path):
    seed_source_chain(tmp_path)

    path = write_document_handoff_approval_request_read_surface(artifact_dir=tmp_path)

    assert path == tmp_path / DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME
    assert load_document_handoff_approval_request_read_surface(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_human_approval_promotion_fails_closed():
    request = copy.deepcopy(build_document_handoff_human_operator_approval_request())
    request["human_operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="source promoted human_operator_approval_recorded"):
        build_document_handoff_approval_request_read_surface(source_request=request)


def test_source_pre_check_promotion_fails_closed():
    request = copy.deepcopy(build_document_handoff_human_operator_approval_request())
    request["pre_approval_checks"][0]["passed_here"] = True

    with pytest.raises(CityOpsContractError, match="source pre-check promoted passed_here"):
        build_document_handoff_approval_request_read_surface(source_request=request)


def test_source_forbidden_safe_claim_fails_closed():
    request = copy.deepcopy(build_document_handoff_human_operator_approval_request())
    request["safe_to_claim"].append("customer_delivery_ready")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_document_handoff_approval_request_read_surface(source_request=request)


def test_loader_fails_closed_on_surface_approval_flag(tmp_path):
    seed_source_chain(tmp_path)
    surface = build_document_handoff_approval_request_read_surface(artifact_dir=tmp_path)
    surface["surface_is_human_approval_record"] = True
    (tmp_path / DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted surface_is_human_approval_record"):
        load_document_handoff_approval_request_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_network_route_registration(tmp_path):
    seed_source_chain(tmp_path)
    surface = build_document_handoff_approval_request_read_surface(artifact_dir=tmp_path)
    surface["mount_contract"]["network_route_registered"] = True
    (tmp_path / DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="registered network route"):
        load_document_handoff_approval_request_read_surface(artifact_dir=tmp_path)
