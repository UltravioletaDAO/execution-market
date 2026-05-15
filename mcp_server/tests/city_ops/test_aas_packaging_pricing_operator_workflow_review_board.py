import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_packaging_pricing_operator_workflow_review_board import (
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME,
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM,
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA,
    BOARD_ID,
    BOARD_READINESS_FALSE_FLAGS,
    REQUIRED_BLOCKED_CLAIMS,
    build_aas_packaging_pricing_operator_workflow_review_board,
    load_aas_packaging_pricing_operator_workflow_review_board,
    write_aas_packaging_pricing_operator_workflow_review_board,
)
from mcp_server.city_ops.aas_three_family_packaging_review_packet import (
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME,
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM,
    build_aas_three_family_packaging_review_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_board() -> dict:
    with (
        ARTIFACT_DIR / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_source_packet(tmp_path: Path) -> None:
    (tmp_path / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME).write_text(
        json.dumps(build_aas_three_family_packaging_review_packet()),
        encoding="utf-8",
    )


def test_review_board_matches_persisted_artifact():
    board = build_aas_packaging_pricing_operator_workflow_review_board()

    assert board == read_board()
    assert load_aas_packaging_pricing_operator_workflow_review_board() == board
    assert board["schema"] == AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA
    assert board["board_id"] == BOARD_ID
    assert board["scope"] == "internal_admin_review_board_only_no_customer_exposure"
    assert board["source_packet_file"] == AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME
    assert board["source_safe_claim"] == AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM
    assert AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM in board[
        "safe_to_claim"
    ]
    assert AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM in board["safe_to_claim"]


def test_board_consumes_only_packaging_packet_and_keeps_three_rows_held():
    board = build_aas_packaging_pricing_operator_workflow_review_board()

    assert board["source_policy"] == (
        "consume_only_persisted_aas_three_family_packaging_review_packet_json"
    )
    assert board["summary"]["families_on_board"] == 3
    assert board["summary"]["source_consumed"] == (
        "aas_three_family_packaging_review_packet.json_only"
    )
    assert board["summary"]["all_rows_remain_held"] is True
    assert board["summary"]["customer_copy_approved"] is False
    assert board["summary"]["customer_delivery_approved"] is False
    assert board["summary"]["publication_approved"] is False
    assert board["summary"]["public_prices_or_customer_quotes_approved"] is False
    assert board["summary"][
        "routes_pilots_dispatch_reputation_live_runtime_gps_worker_doctrine_approved"
    ] is False
    assert len(board["review_rows"]) == 3
    for row in board["review_rows"]:
        assert row["still_held"] is True
        assert row["package_label_customer_copy_approved"] is False
        assert row["public_price_approved"] is False
        assert row["customer_quote_ready"] is False
        assert row["operator_queue_launch_ready"] is False


def test_board_makes_labels_pricing_inputs_and_workflow_questions_reviewable_only():
    board = build_aas_packaging_pricing_operator_workflow_review_board()

    assert board["pricing_input_questions"]["status"] == (
        "internal_inputs_reviewable_only_no_public_price_or_customer_quote"
    )
    assert board["pricing_input_questions"]["approved_outputs"] == []
    assert "public_price" in board["pricing_input_questions"]["blocked_outputs"]
    assert "customer_quote" in board["pricing_input_questions"]["blocked_outputs"]
    assert "domain_authority_premium" in board["pricing_input_questions"]["blocked_outputs"]
    assert board["operator_workflow_questions"]["status"] == (
        "queue_and_workflow_questions_only_not_launch_ready"
    )
    assert board["operator_workflow_questions"]["launch_not_authorized"] is True
    assert board["operator_workflow_questions"]["customer_delivery_path_authorized"] is False
    assert board["operator_workflow_questions"]["worker_dispatch_path_authorized"] is False
    assert len(board["operator_workflow_questions"]["queues_under_review"]) == 3


def test_board_keeps_external_readiness_false_and_blocked():
    board = build_aas_packaging_pricing_operator_workflow_review_board()

    for flag in BOARD_READINESS_FALSE_FLAGS:
        assert board["readiness"][flag] is False
        for row in board["review_rows"]:
            assert row["readiness"][flag] is False
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in board["do_not_claim_yet"]
        assert claim not in board["safe_to_claim"]
    forbidden = board["review_boundaries"]["forbidden"]
    assert "approve customer copy or customer delivery" in forbidden
    assert "publish public prices or customer quotes" in forbidden
    assert "register public routes or catalog entries" in forbidden
    assert "authorize controlled pilots or front-door SKUs" in forbidden
    assert "dispatch workers or create dispatch instructions" in forbidden
    assert "attach reputation receipts" in forbidden
    assert "claim live Acontext/runtime parity" in forbidden
    assert "release exact GPS/raw metadata" in forbidden
    assert (
        "approve domain authority or legal/notarial/emergency/safety/repair/insurance/SLA/official-report claims"
        in forbidden
    )
    assert "create worker-copyable doctrine" in forbidden


def test_write_review_board_persists_valid_artifact(tmp_path):
    seed_source_packet(tmp_path)

    path = write_aas_packaging_pricing_operator_workflow_review_board(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME
    assert load_aas_packaging_pricing_operator_workflow_review_board(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_packet_customer_delivery_promotion_fails_closed():
    packet = build_aas_three_family_packaging_review_packet()
    packet["source_decisions"][0]["customer_delivery_approval"] = True

    with pytest.raises(CityOpsContractError, match="customer delivery promoted"):
        build_aas_packaging_pricing_operator_workflow_review_board(source_packet=packet)


def test_source_packet_forbidden_safe_claim_fails_closed():
    packet = build_aas_three_family_packaging_review_packet()
    packet["safe_to_claim"].append("public_route_ready")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_aas_packaging_pricing_operator_workflow_review_board(source_packet=packet)


def test_source_packet_price_and_customer_quote_block_drift_fails_closed():
    packet = build_aas_three_family_packaging_review_packet()
    packet["pricing_review_inputs"] = copy.deepcopy(packet["pricing_review_inputs"])
    packet["pricing_review_inputs"]["outputs_not_approved"] = ["front_door_sku"]

    with pytest.raises(CityOpsContractError, match="price/customer quote block drift"):
        build_aas_packaging_pricing_operator_workflow_review_board(source_packet=packet)


def test_source_packet_public_route_pilot_dispatch_reputation_runtime_gps_worker_blocks_fail_closed():
    packet = build_aas_three_family_packaging_review_packet()
    packet["packaging_review_boundaries"] = copy.deepcopy(packet["packaging_review_boundaries"])
    packet["packaging_review_boundaries"]["forbidden"] = [
        item
        for item in packet["packaging_review_boundaries"]["forbidden"]
        if item
        not in {
            "mount catalog or public routes",
            "authorize controlled pilot exposure",
            "dispatch workers from this packet",
            "attach ERC-8004 reputation receipts",
            "claim live Acontext/runtime parity",
            "release exact GPS/raw metadata",
            "create worker-copyable doctrine",
        }
    ]

    with pytest.raises(CityOpsContractError, match="forbidden boundary drift"):
        build_aas_packaging_pricing_operator_workflow_review_board(source_packet=packet)


def test_source_packet_domain_authority_block_drift_fails_closed():
    packet = build_aas_three_family_packaging_review_packet()
    packet["do_not_claim_yet"] = [
        claim for claim in packet["do_not_claim_yet"] if claim != "legal_or_regulator_authority_ready"
    ]

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        build_aas_packaging_pricing_operator_workflow_review_board(source_packet=packet)


def test_source_packet_operator_workflow_launch_drift_fails_closed():
    packet = build_aas_three_family_packaging_review_packet()
    packet["operator_workflow_review"] = copy.deepcopy(packet["operator_workflow_review"])
    packet["operator_workflow_review"]["worker_dispatch_path_authorized"] = True

    with pytest.raises(CityOpsContractError, match="operator workflow drift"):
        build_aas_packaging_pricing_operator_workflow_review_board(source_packet=packet)


def test_loader_fails_closed_on_board_public_price_promotion(tmp_path):
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["review_rows"][0]["public_price_approved"] = True
    (tmp_path / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="public price promoted"):
        load_aas_packaging_pricing_operator_workflow_review_board(artifact_dir=tmp_path)


def test_loader_fails_closed_on_board_customer_quote_promotion(tmp_path):
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["review_rows"][0]["customer_quote_ready"] = True
    (tmp_path / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="customer quote promoted"):
        load_aas_packaging_pricing_operator_workflow_review_board(artifact_dir=tmp_path)


def test_loader_fails_closed_on_board_operator_queue_launch_promotion(tmp_path):
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["review_rows"][0]["operator_queue_launch_ready"] = True
    (tmp_path / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="operator queue launch promoted"):
        load_aas_packaging_pricing_operator_workflow_review_board(artifact_dir=tmp_path)


def test_loader_fails_closed_on_board_readiness_flip(tmp_path):
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["readiness"]["live_acontext_ready"] = True
    (tmp_path / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_aas_packaging_pricing_operator_workflow_review_board(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    board = build_aas_packaging_pricing_operator_workflow_review_board()
    board["safe_to_claim"].append("worker_copyable_doctrine_ready")
    (tmp_path / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_aas_packaging_pricing_operator_workflow_review_board(artifact_dir=tmp_path)
