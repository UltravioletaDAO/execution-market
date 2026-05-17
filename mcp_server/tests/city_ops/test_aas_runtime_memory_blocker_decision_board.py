import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
    build_aas_coordination_observability_success_metrics_board,
)
from mcp_server.city_ops.aas_runtime_memory_blocker_decision_board import (
    AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_FILENAME,
    AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SAFE_CLAIM,
    AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SCHEMA,
    RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_BLOCKED_CLAIMS,
    build_aas_runtime_memory_blocker_decision_board,
    load_aas_runtime_memory_blocker_decision_board,
    write_aas_runtime_memory_blocker_decision_board,
)
from mcp_server.city_ops.acontext_docker_pull_path_diagnostic import (
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME,
    build_acontext_docker_pull_path_diagnostic,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_board() -> dict:
    with (PROOF_BLOCK_DIR / AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_runtime_memory_blocker_decision_board_matches_fixture():
    board = build_aas_runtime_memory_blocker_decision_board()

    assert board == read_fixture_board()
    assert board["schema"] == AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SCHEMA
    assert board["board_verdict"] == (
        "runtime_memory_blocker_board_landed_docker_pull_still_blocks_live_acontext"
    )
    assert AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SAFE_CLAIM in board[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert board["readiness"]["runtime_memory_blocker_board_landed"] is True
    assert board["readiness"]["docker_pull_path_blocker_confirmed"] is True
    assert board["readiness"]["acontext_sink_ready"] is False


def test_runtime_memory_blocker_decision_board_ranks_resolution_paths():
    board = build_aas_runtime_memory_blocker_decision_board()
    options = board["resolution_decision_tree"]

    assert [option["rank"] for option in options] == [1, 2, 3, 4]
    assert options[0]["option"] == "repair_docker_desktop_containerd_or_network_layer_fetch"
    assert options[1]["option"] == "use_trusted_prepopulated_image_cache_or_mirror"
    assert all(option["authorizes_live_runtime"] is False for option in options)
    assert board["blocker_summary"]["primary_blocker"] == (
        "docker_layer_fetch_stalls_before_first_acontext_image"
    )


def test_runtime_memory_blocker_decision_board_links_system_integration_axes():
    board = build_aas_runtime_memory_blocker_decision_board()

    session_cards = {card["card"]: card for card in board["session_management_enhancement_cards"]}
    decision_cards = {card["card"]: card for card in board["cross_project_decision_support_cards"]}
    metric_cards = {card["metric"]: card for card in board["agent_success_metric_cards"]}

    assert set(session_cards) == {
        "four_id_pickup_ticket",
        "blocker_state_event",
        "no_raw_context_reopen_rule",
    }
    assert session_cards["four_id_pickup_ticket"]["runtime_session_manager_changed"] is False
    assert decision_cards["next_action_selector"]["decision"] == (
        "fix_or_bypass_docker_layer_fetch_before_any_compose_start"
    )
    assert metric_cards["docker_inventory_gate"]["observed"] is False
    assert metric_cards["live_runtime_parity_gate"]["observed"] is False
    assert metric_cards["coordination_metrics_board_continuity"]["observed"] is True


def test_runtime_memory_blocker_decision_board_preserves_blocked_claims():
    board = build_aas_runtime_memory_blocker_decision_board()

    safe = set(board["claim_boundaries"]["safe_to_claim"])
    blocked = set(board["claim_boundaries"]["do_not_claim_yet"])
    assert set(RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "runtime_parity_proven_by_runtime_memory_board" in blocked
    assert "payment_or_production_reverified_by_runtime_memory_board" in blocked
    assert "worker_copyable_doctrine_ready_by_runtime_memory_board" in blocked


def test_runtime_memory_blocker_decision_board_refuses_promoted_diagnostic():
    diagnostic = copy.deepcopy(build_acontext_docker_pull_path_diagnostic())
    diagnostic["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="Docker diagnostic promoted readiness"):
        build_aas_runtime_memory_blocker_decision_board(docker_diagnostic=diagnostic)


def test_runtime_memory_blocker_decision_board_refuses_resolved_pull_blocker():
    diagnostic = copy.deepcopy(build_acontext_docker_pull_path_diagnostic())
    diagnostic["explicit_platform_retry_summary"][
        "explicit_platform_retry_blocker_remains"
    ] = False

    with pytest.raises(CityOpsContractError, match="no longer records pull blocker"):
        build_aas_runtime_memory_blocker_decision_board(docker_diagnostic=diagnostic)


def test_runtime_memory_blocker_decision_board_refuses_metrics_readiness_promotion():
    metrics = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    metrics["readiness"]["agent_observability_live_dashboard_ready"] = True

    with pytest.raises(CityOpsContractError, match="metrics board promoted readiness"):
        build_aas_runtime_memory_blocker_decision_board(metrics_board=metrics)


def test_runtime_memory_blocker_decision_board_refuses_source_id_mismatch():
    metrics = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    metrics["coordination_session_id"] = "different_session"

    with pytest.raises(CityOpsContractError, match="source invariant id mismatch"):
        build_aas_runtime_memory_blocker_decision_board(metrics_board=metrics)


def test_runtime_memory_blocker_decision_board_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_runtime_memory_blocker_decision_board(artifact_dir=tmp_path)

    assert path.name == AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_FILENAME
    loaded = load_aas_runtime_memory_blocker_decision_board(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SAFE_CLAIM
    )


def test_runtime_memory_blocker_decision_board_loader_rejects_route_promotion(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_runtime_memory_blocker_decision_board(artifact_dir=tmp_path)
    board = json.loads(path.read_text(encoding="utf-8"))
    board["access_policy"]["public_route_registered"] = True
    path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_runtime_memory_blocker_decision_board(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
