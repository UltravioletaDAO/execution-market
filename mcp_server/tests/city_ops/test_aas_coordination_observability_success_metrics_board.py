import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA,
    COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    build_aas_coordination_observability_success_metrics_board,
    load_aas_coordination_observability_success_metrics_board,
    write_aas_coordination_observability_success_metrics_board,
)
from mcp_server.city_ops.aas_system_integration_flywheel_read_surface import (
    build_aas_system_integration_flywheel_read_surface,
)
from mcp_server.city_ops.acontext_prerequisite_recovery_attempt_log import (
    build_acontext_prerequisite_recovery_attempt_log,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_board() -> dict:
    with (PROOF_BLOCK_DIR / AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_coordination_observability_success_metrics_board_matches_fixture():
    board = build_aas_coordination_observability_success_metrics_board()

    assert board == read_fixture_board()
    assert board["schema"] == AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA
    assert board["board_verdict"] == (
        "coordination_metrics_board_landed_still_blocked_on_live_runtime"
    )
    assert AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM in board[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert board["readiness"]["coordination_metrics_board_landed"] is True
    assert board["readiness"]["live_acontext_memory_integration_ready"] is False
    assert board["readiness"]["agent_observability_live_dashboard_ready"] is False


def test_coordination_observability_success_metrics_tracks_are_read_only():
    board = build_aas_coordination_observability_success_metrics_board()

    tracks = {track["track"]: track for track in board["integration_tracks"]}
    assert set(tracks) == {
        "memory_system_to_acontext_integration",
        "irc_session_management_enhancement",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
        "payment_infrastructure_context",
    }
    assert tracks["memory_system_to_acontext_integration"]["authorizes_live_runtime"] is False
    assert tracks["irc_session_management_enhancement"][
        "authorizes_runtime_session_manager_change"
    ] is False
    assert tracks["cross_project_decision_support"][
        "authorizes_customer_copy_or_public_route"
    ] is False
    assert tracks["agent_observability_success_metrics"]["authorizes_live_dashboard"] is False
    assert tracks["payment_infrastructure_context"][
        "authorizes_payment_or_production_claim"
    ] is False


def test_coordination_observability_success_metrics_preserves_sticky_blocked_claims():
    board = build_aas_coordination_observability_success_metrics_board()

    safe = set(board["claim_boundaries"]["safe_to_claim"])
    blocked = set(board["claim_boundaries"]["do_not_claim_yet"])
    assert set(COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "live_acontext_memory_integration_ready_by_metrics_board" in blocked
    assert "payment_coverage_reverified_by_metrics_board" in blocked
    assert "worker_copyable_doctrine_ready_by_metrics_board" in blocked


def test_coordination_observability_success_metrics_cards_define_agent_success():
    board = build_aas_coordination_observability_success_metrics_board()

    metrics = {card["metric"]: card for card in board["success_metric_cards"]}
    assert metrics["claim_boundary_integrity"]["observed"] is True
    assert metrics["four_id_handoff_completeness"]["observed"] is True
    assert metrics["acontext_prerequisite_honesty"]["observed"] is True
    assert metrics["one_next_proof_discipline"]["observed"] is True
    assert all(card["customer_visible"] is False for card in metrics.values())


def test_coordination_observability_success_metrics_refuses_promoted_surface_readiness():
    surface = copy.deepcopy(build_aas_system_integration_flywheel_read_surface())
    surface["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        build_aas_coordination_observability_success_metrics_board(
            flywheel_surface=surface
        )


def test_coordination_observability_success_metrics_refuses_promoted_recovery_readiness():
    recovery = copy.deepcopy(build_acontext_prerequisite_recovery_attempt_log())
    recovery["readiness"]["compose_services_started"] = True

    with pytest.raises(CityOpsContractError, match="recovery log promoted readiness"):
        build_aas_coordination_observability_success_metrics_board(
            recovery_log=recovery
        )


def test_coordination_observability_success_metrics_refuses_source_id_mismatch():
    recovery = copy.deepcopy(build_acontext_prerequisite_recovery_attempt_log())
    recovery["coordination_session_id"] = "different_session"

    with pytest.raises(CityOpsContractError, match="source invariant id mismatch"):
        build_aas_coordination_observability_success_metrics_board(
            recovery_log=recovery
        )


def test_coordination_observability_success_metrics_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_coordination_observability_success_metrics_board(
        artifact_dir=tmp_path
    )

    assert path.name == AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME
    loaded = load_aas_coordination_observability_success_metrics_board(
        artifact_dir=tmp_path
    )
    assert loaded["schema"] == AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM
    )


def test_coordination_observability_success_metrics_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_coordination_observability_success_metrics_board(
        artifact_dir=tmp_path
    )
    board = json.loads(path.read_text(encoding="utf-8"))
    board["readiness"]["public_route_ready"] = True
    path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_coordination_observability_success_metrics_board(
            artifact_dir=tmp_path
        )


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
