import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_packaging_pricing_operator_workflow_review_board import (
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME,
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM,
    build_aas_packaging_pricing_operator_workflow_review_board,
)
from mcp_server.city_ops.aas_single_boundary_human_operator_approval_request import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_REDACTION_CHECKS,
    SELECTED_BOUNDARY_KEY,
    build_aas_single_boundary_human_operator_approval_request,
    load_aas_single_boundary_human_operator_approval_request,
    write_aas_single_boundary_human_operator_approval_request,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    with (ARTIFACT_DIR / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_board(tmp_path: Path) -> None:
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    (tmp_path / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )


def test_approval_request_matches_persisted_artifact():
    packet = build_aas_single_boundary_human_operator_approval_request()

    assert packet == read_packet()
    assert load_aas_single_boundary_human_operator_approval_request() == packet
    assert packet["schema"] == AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA
    assert packet["scope"] == "internal_admin_single_boundary_human_operator_approval_request_only"
    assert packet["source_board_file"] == AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME
    assert AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]
    assert AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]


def test_request_names_exactly_one_pending_boundary_without_approval():
    packet = build_aas_single_boundary_human_operator_approval_request()
    boundary = packet["selected_boundary"]

    assert packet["approval_request_status"] == APPROVAL_REQUEST_STATUS
    assert packet["human_operator_approval_recorded"] is False
    assert packet["selected_boundary_count"] == 1
    assert boundary["key"] == SELECTED_BOUNDARY_KEY == "compliance_desk"
    assert boundary["candidate_text_boundary"] == "internal_package_label_only"
    assert boundary["candidate_text_value"] == "Visible posting / notice compliance snapshot"
    assert boundary["candidate_text_fields"] == ["package_label_under_review"]
    assert boundary["selected_boundary_approved"] is False
    assert boundary["human_operator_approval_recorded"] is False


def test_redaction_requirements_and_delivery_path_are_not_approval():
    packet = build_aas_single_boundary_human_operator_approval_request()

    assert [item["check"] for item in packet["redaction_requirements"]] == REQUIRED_REDACTION_CHECKS
    assert all(item["required_before_human_approval"] is True for item in packet["redaction_requirements"])
    assert all(item["passed_here"] is False for item in packet["redaction_requirements"])
    assert packet["authorized_delivery_path"] == {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "no_customer_delivery_no_publication_no_dispatch",
        "customer_delivery_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
    }


def test_customer_public_pricing_dispatch_reputation_runtime_and_metadata_stay_blocked():
    packet = build_aas_single_boundary_human_operator_approval_request()

    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "customer_delivery_path_authorized",
        "customer_copy_created",
        "customer_copy_ready",
        "customer_visible_catalog_ready",
        "public_service_catalog_ready",
        "publication_approved",
        "public_route_ready",
        "controlled_pilot_ready",
        "front_door_sku_ready",
        "public_price_approved",
        "customer_quote_ready",
        "operator_queue_launch_ready",
        "dispatch_enabled",
        "autonomous_dispatch_ready",
        "reputation_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "worker_copyable_doctrine_ready",
        "live_acontext_ready",
        "runtime_parity_proven",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        assert packet[flag] is False

    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in packet["do_not_claim_yet"]
        assert claim not in packet["safe_to_claim"]
    assert packet["still_blocked_claims"] == packet["do_not_claim_yet"]


def test_write_approval_request_persists_valid_artifact(tmp_path):
    seed_source_board(tmp_path)

    path = write_aas_single_boundary_human_operator_approval_request(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    assert load_aas_single_boundary_human_operator_approval_request(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_board_customer_copy_promotion_fails_closed():
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["summary"] = copy.deepcopy(board["summary"])
    board["summary"]["customer_copy_approved"] = True

    with pytest.raises(CityOpsContractError, match="summary drift"):
        build_aas_single_boundary_human_operator_approval_request(source_board=board)


def test_source_board_row_public_price_promotion_fails_closed():
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["review_rows"] = copy.deepcopy(board["review_rows"])
    board["review_rows"][0]["public_price_approved"] = True

    with pytest.raises(CityOpsContractError, match="promoted row public_price_approved"):
        build_aas_single_boundary_human_operator_approval_request(source_board=board)


def test_source_board_forbidden_safe_claim_fails_closed():
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["safe_to_claim"] = [*board["safe_to_claim"], "customer_delivery_ready"]

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_aas_single_boundary_human_operator_approval_request(source_board=board)


def test_loader_fails_closed_on_human_approval_flip(tmp_path):
    packet = build_aas_single_boundary_human_operator_approval_request()
    packet["human_operator_approval_recorded"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="recorded human approval"):
        load_aas_single_boundary_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_multiple_boundaries(tmp_path):
    packet = build_aas_single_boundary_human_operator_approval_request()
    packet["selected_boundary_count"] = 2
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exactly one boundary"):
        load_aas_single_boundary_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_delivery_path_expansion(tmp_path):
    packet = build_aas_single_boundary_human_operator_approval_request()
    packet["authorized_delivery_path"]["customer_delivery_allowed"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="delivery path promoted"):
        load_aas_single_boundary_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_redaction_passing_itself(tmp_path):
    packet = build_aas_single_boundary_human_operator_approval_request()
    packet["redaction_requirements"][0]["passed_here"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="redaction marked passed"):
        load_aas_single_boundary_human_operator_approval_request(artifact_dir=tmp_path)
