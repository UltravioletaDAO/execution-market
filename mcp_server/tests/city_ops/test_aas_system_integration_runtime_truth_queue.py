from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_system_integration_flywheel_route_regret_panel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
    build_aas_system_integration_flywheel_route_regret_panel,
)
from mcp_server.city_ops.aas_system_integration_runtime_truth_queue import (
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME,
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SCHEMA,
    RUNTIME_TRUTH_QUEUE_VERDICT,
    build_aas_system_integration_runtime_truth_queue,
    load_aas_system_integration_runtime_truth_queue,
    write_aas_system_integration_runtime_truth_queue,
)
from mcp_server.city_ops.acontext_runtime_memory_daemon_recheck import (
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM,
    build_acontext_runtime_memory_daemon_recheck,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def test_system_integration_runtime_truth_queue_matches_fixture():
    queue = build_aas_system_integration_runtime_truth_queue()
    fixture = json.loads(
        (
            PROOF_BLOCK_DIR / AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME
        ).read_text(encoding="utf-8")
    )

    assert queue == fixture
    assert queue["schema"] == AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SCHEMA
    assert queue["queue_verdict"] == RUNTIME_TRUTH_QUEUE_VERDICT
    assert queue["source_artifacts"]["route_regret_panel"]["file"] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME
    )
    assert queue["source_artifacts"]["acontext_daemon_recheck"]["file"] == (
        ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME
    )
    assert queue["readiness"]["runtime_truth_queue_landed"] is True
    assert queue["readiness"]["route_layering_stopped"] is True
    assert queue["readiness"]["docker_daemon_available"] is False
    assert queue["readiness"]["one_live_parity_attempt_authorized"] is False
    assert queue["readiness"]["live_acontext_write_performed"] is False
    assert queue["readiness"]["memory_acontext_parity_ready"] is False
    assert queue["readiness"]["irc_runtime_session_manager_enhanced"] is False
    assert queue["readiness"]["customer_delivery_ready"] is False
    assert queue["readiness"]["dispatch_ready"] is False
    assert queue["readiness"]["erc8004_reputation_ready"] is False
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM in queue[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM in queue[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM in queue[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "runtime_truth_queue_authorized_live_write_retrieve_attempt" in queue[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert "runtime_truth_queue_proved_memory_acontext_parity" in queue[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert "runtime_truth_queue_changes_irc_runtime_session_manager" in queue[
        "claim_boundaries"
    ]["do_not_claim_yet"]


def test_system_integration_runtime_truth_queue_preserves_gate_order():
    queue = build_aas_system_integration_runtime_truth_queue()

    assert [gate["gate"] for gate in queue["runtime_truth_gates"]] == [
        "docker_daemon_socket",
        "required_image_inventory",
        "local_acontext_services",
        "empty_readiness_gate",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert all(gate["passed"] is False for gate in queue["runtime_truth_gates"])
    assert all(
        gate["authorizes_live_attempt"] is False
        for gate in queue["runtime_truth_gates"]
    )


def test_system_integration_runtime_truth_queue_connection_cards_are_planning_only():
    queue = build_aas_system_integration_runtime_truth_queue()
    cards = {card["connection"]: card for card in queue["coordination_connection_cards"]}

    assert cards["memory_system_to_acontext"]["safe_now"] == "plan_the_order_only"
    assert cards["irc_session_management"]["creates_runtime_change"] is False
    assert cards["cross_project_decision_support"]["creates_runtime_change"] is False
    assert cards["agent_observability_success_metrics"]["creates_runtime_change"] is False
    assert queue["success_metric_cards"][0]["metric"] == "route_layer_regret_respected"


def test_write_system_integration_runtime_truth_queue_persists_fixture(tmp_path):
    for source_path in PROOF_BLOCK_DIR.glob("*.json"):
        if source_path.name == AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME:
            continue
        shutil.copy(source_path, tmp_path / source_path.name)

    path = write_aas_system_integration_runtime_truth_queue(artifact_dir=tmp_path)
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME
    assert persisted == build_aas_system_integration_runtime_truth_queue(
        artifact_dir=tmp_path
    )


def test_load_system_integration_runtime_truth_queue_validates_fixture():
    queue = load_aas_system_integration_runtime_truth_queue()

    assert queue["queue_verdict"] == RUNTIME_TRUTH_QUEUE_VERDICT
    assert queue["source_artifacts"]["acontext_daemon_recheck"]["safe_claim"] == (
        ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM
    )


def test_system_integration_runtime_truth_queue_refuses_regret_panel_promotion():
    panel = copy.deepcopy(build_aas_system_integration_flywheel_route_regret_panel())
    panel["readiness"]["runtime_truth_present"] = True

    with pytest.raises(CityOpsContractError, match="runtime_truth_present"):
        build_aas_system_integration_runtime_truth_queue(regret_panel=panel)


def test_system_integration_runtime_truth_queue_refuses_daemon_recheck_promotion():
    recheck = copy.deepcopy(build_acontext_runtime_memory_daemon_recheck())
    recheck["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="runtime_parity_proven"):
        build_aas_system_integration_runtime_truth_queue(daemon_recheck=recheck)


def test_system_integration_runtime_truth_queue_refuses_claim_overlap():
    panel = copy.deepcopy(build_aas_system_integration_flywheel_route_regret_panel())
    panel["claim_boundaries"]["do_not_claim_yet"].append(
        panel["claim_boundaries"]["safe_to_claim"][0]
    )

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_system_integration_runtime_truth_queue(regret_panel=panel)
