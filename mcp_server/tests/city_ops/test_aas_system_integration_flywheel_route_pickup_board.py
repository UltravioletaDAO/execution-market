from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_system_integration_flywheel_route_handoff_packet import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
    build_aas_system_integration_flywheel_route_handoff_packet,
)
from mcp_server.city_ops.aas_system_integration_flywheel_route_pickup_board import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SCHEMA,
    DEFAULT_NEXT_ACTION,
    build_aas_system_integration_flywheel_route_pickup_board,
    load_aas_system_integration_flywheel_route_pickup_board,
    write_aas_system_integration_flywheel_route_pickup_board,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def test_system_integration_flywheel_route_pickup_board_matches_fixture():
    board = build_aas_system_integration_flywheel_route_pickup_board()
    fixture = json.loads(
        (
            PROOF_BLOCK_DIR
            / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME
        ).read_text(encoding="utf-8")
    )

    assert board == fixture
    assert board["schema"] == AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SCHEMA
    assert board["source_handoff"]["file"] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
    )
    assert board["default_next_action"] == DEFAULT_NEXT_ACTION
    assert board["readiness"]["pickup_board_landed"] is True
    assert board["readiness"]["source_handoff_verified"] is True
    assert board["readiness"]["route_expansion_paused"] is True
    assert board["readiness"]["customer_delivery_ready"] is False
    assert board["readiness"]["publication_ready"] is False
    assert board["readiness"]["dispatch_ready"] is False
    assert board["readiness"]["erc8004_reputation_ready"] is False
    assert board["readiness"]["live_acontext_runtime_parity_ready"] is False
    assert board["safe_fork_cards"][0]["fork"] == "default_stop"
    assert board["safe_fork_cards"][0]["allowed_now"] is True
    assert board["safe_fork_cards"][1]["fork"] == "runtime_truth"
    assert board["safe_fork_cards"][1]["allowed_now"] is False
    assert board["safe_fork_cards"][2]["fork"] == "operator_truth"
    assert board["safe_fork_cards"][2]["allowed_now"] is False
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM in board[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM in board[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "system_integration_flywheel_route_pickup_board_authorizes_customer_delivery" in board[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert "system_integration_flywheel_route_pickup_board_proves_live_acontext_or_runtime_parity" in board[
        "claim_boundaries"
    ]["do_not_claim_yet"]


def test_write_system_integration_flywheel_route_pickup_board_persists_fixture(tmp_path):
    for source_path in PROOF_BLOCK_DIR.glob("*.json"):
        if source_path.name == AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME:
            continue
        shutil.copy(source_path, tmp_path / source_path.name)

    path = write_aas_system_integration_flywheel_route_pickup_board(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME
    assert persisted == build_aas_system_integration_flywheel_route_pickup_board(
        artifact_dir=tmp_path
    )


def test_load_system_integration_flywheel_route_pickup_board_validates_fixture():
    board = load_aas_system_integration_flywheel_route_pickup_board()

    assert board["board_verdict"] == (
        "route_handoff_pickup_ready_default_stop_until_operator_or_runtime_truth"
    )
    assert board["source_handoff"]["safe_claim"] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM
    )


def test_system_integration_flywheel_route_pickup_refuses_source_readiness_promotion():
    handoff = copy.deepcopy(build_aas_system_integration_flywheel_route_handoff_packet())
    handoff["readiness"]["live_acontext_runtime_parity_ready"] = True

    with pytest.raises(CityOpsContractError, match="live_acontext_runtime_parity_ready"):
        build_aas_system_integration_flywheel_route_pickup_board(
            handoff_packet=handoff
        )


def test_system_integration_flywheel_route_pickup_refuses_customer_visibility():
    handoff = copy.deepcopy(build_aas_system_integration_flywheel_route_handoff_packet())
    handoff["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        build_aas_system_integration_flywheel_route_pickup_board(
            handoff_packet=handoff
        )


def test_system_integration_flywheel_route_pickup_refuses_claim_overlap():
    handoff = copy.deepcopy(build_aas_system_integration_flywheel_route_handoff_packet())
    handoff["claim_boundaries"]["do_not_claim_yet"].append(
        handoff["claim_boundaries"]["safe_to_claim"][0]
    )

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_system_integration_flywheel_route_pickup_board(
            handoff_packet=handoff
        )
