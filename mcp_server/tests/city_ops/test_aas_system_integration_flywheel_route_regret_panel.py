from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_system_integration_flywheel_route_pickup_board import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM,
    build_aas_system_integration_flywheel_route_pickup_board,
)
from mcp_server.city_ops.aas_system_integration_flywheel_route_regret_panel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA,
    REGRET_PANEL_DEFAULT_OUTCOME,
    build_aas_system_integration_flywheel_route_regret_panel,
    load_aas_system_integration_flywheel_route_regret_panel,
    write_aas_system_integration_flywheel_route_regret_panel,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def test_system_integration_flywheel_route_regret_panel_matches_fixture():
    panel = build_aas_system_integration_flywheel_route_regret_panel()
    fixture = json.loads(
        (
            PROOF_BLOCK_DIR
            / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME
        ).read_text(encoding="utf-8")
    )

    assert panel == fixture
    assert panel["schema"] == AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA
    assert panel["source_pickup_board"]["file"] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME
    )
    assert panel["default_outcome"] == REGRET_PANEL_DEFAULT_OUTCOME
    assert panel["readiness"]["regret_panel_landed"] is True
    assert panel["readiness"]["source_pickup_board_verified"] is True
    assert panel["readiness"]["default_stop_reaffirmed"] is True
    assert panel["readiness"]["extra_route_layering_stopped"] is True
    assert panel["readiness"]["new_route_requested"] is False
    assert panel["readiness"]["runtime_truth_present"] is False
    assert panel["readiness"]["operator_truth_present"] is False
    assert panel["readiness"]["customer_delivery_ready"] is False
    assert panel["readiness"]["dispatch_ready"] is False
    assert panel["readiness"]["erc8004_reputation_ready"] is False
    assert panel["readiness"]["live_acontext_runtime_parity_ready"] is False
    assert panel["regret_checks"][1]["check"] == "another_route_layer_would_not_add_truth"
    assert panel["regret_checks"][1]["regret"] is True
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM in panel[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM in panel[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "system_integration_flywheel_route_regret_panel_authorizes_more_route_layers_without_new_truth" in panel[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert "system_integration_flywheel_route_regret_panel_authorizes_customer_delivery" in panel[
        "claim_boundaries"
    ]["do_not_claim_yet"]


def test_write_system_integration_flywheel_route_regret_panel_persists_fixture(tmp_path):
    for source_path in PROOF_BLOCK_DIR.glob("*.json"):
        if source_path.name == AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME:
            continue
        shutil.copy(source_path, tmp_path / source_path.name)

    path = write_aas_system_integration_flywheel_route_regret_panel(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME
    assert persisted == build_aas_system_integration_flywheel_route_regret_panel(
        artifact_dir=tmp_path
    )


def test_load_system_integration_flywheel_route_regret_panel_validates_fixture():
    panel = load_aas_system_integration_flywheel_route_regret_panel()

    assert panel["panel_verdict"] == (
        "stop_internal_route_layering_until_runtime_or_operator_truth_exists"
    )
    assert panel["source_pickup_board"]["safe_claim"] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM
    )


def test_system_integration_flywheel_route_regret_refuses_future_fork_promotion():
    board = copy.deepcopy(build_aas_system_integration_flywheel_route_pickup_board())
    board["safe_fork_cards"][1]["allowed_now"] = True

    with pytest.raises(CityOpsContractError, match="future forks"):
        build_aas_system_integration_flywheel_route_regret_panel(
            pickup_board=board
        )


def test_system_integration_flywheel_route_regret_refuses_source_readiness_promotion():
    board = copy.deepcopy(build_aas_system_integration_flywheel_route_pickup_board())
    board["readiness"]["customer_delivery_ready"] = True

    with pytest.raises(CityOpsContractError, match="customer_delivery_ready"):
        build_aas_system_integration_flywheel_route_regret_panel(
            pickup_board=board
        )


def test_system_integration_flywheel_route_regret_refuses_claim_overlap():
    board = copy.deepcopy(build_aas_system_integration_flywheel_route_pickup_board())
    board["claim_boundaries"]["do_not_claim_yet"].append(
        board["claim_boundaries"]["safe_to_claim"][0]
    )

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_system_integration_flywheel_route_regret_panel(
            pickup_board=board
        )
