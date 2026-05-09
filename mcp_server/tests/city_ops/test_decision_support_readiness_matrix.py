import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight import (
    build_acontext_live_preflight_result,
    build_blocked_acontext_preflight_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.coordination_intelligence import (
    build_coordination_intelligence_snapshot,
)
from mcp_server.city_ops.decision_support_readiness_matrix import (
    DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM,
    DECISION_SUPPORT_READINESS_MATRIX_SCHEMA,
    build_decision_support_readiness_matrix,
    load_decision_support_readiness_matrix,
    write_decision_support_readiness_matrix_fixture,
)
from mcp_server.city_ops.operator_debug_surface import build_operator_debug_surface
from mcp_server.city_ops.proof_observability import build_proof_observability_snapshot

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_matrix() -> dict:
    with (PROOF_BLOCK_DIR / "decision_support_readiness_matrix.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_decision_support_readiness_matrix_matches_fixture():
    matrix = build_decision_support_readiness_matrix()

    assert matrix == read_fixture_matrix()
    assert matrix["schema"] == DECISION_SUPPORT_READINESS_MATRIX_SCHEMA
    assert matrix["matrix_verdict"] == "decision_support_matrix_landed_live_transport_blocked"
    assert DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM in matrix["claim_boundaries"][
        "safe_to_claim"
    ]
    assert "acontext_sink_ready" in matrix["claim_boundaries"]["do_not_claim_yet"]
    assert "worker-copyable municipal doctrine" in matrix["claim_boundaries"][
        "do_not_claim_yet"
    ]
    assert matrix["readiness"]["matrix_promotes_readiness"] is False
    assert matrix["readiness"]["acontext_sink_ready"] is False


def test_decision_support_readiness_matrix_names_four_system_axes():
    matrix = build_decision_support_readiness_matrix()
    axes = {axis["axis"]: axis for axis in matrix["handoff_axes"]}

    assert set(axes) == {
        "memory_system_to_acontext_bridge",
        "irc_session_management",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
    }
    assert axes["memory_system_to_acontext_bridge"]["ready_now"] is False
    assert axes["irc_session_management"]["state"] == "compact_id_handoff_active"
    assert axes["cross_project_decision_support"]["state"] == (
        "bounded_verdict_reusable_operator_only"
    )
    assert matrix["success_metrics"]["ready_axis_count"] == 3
    assert matrix["success_metrics"]["blocked_axis_count"] == 1
    assert matrix["success_metrics"]["claim_boundary_preservation"] == "pass"


def test_decision_support_readiness_matrix_can_mark_transport_attemptable_without_readiness():
    probe = build_blocked_acontext_preflight_probe()
    probe["docker"].update({"available": True, "exit_code": 0, "error": None})
    probe["python_sdk"]["available"] = True
    probe["api"].update({"reachable": True, "status_code": 200, "error": None})
    probe["dashboard"].update({"reachable": True, "status_code": 200, "error": None})
    preflight = build_acontext_live_preflight_result(probe=probe)
    surface = build_operator_debug_surface(acontext_live_preflight_result=preflight)
    observability = build_proof_observability_snapshot(operator_debug_surface=surface)
    coordination = build_coordination_intelligence_snapshot(
        proof_observability_snapshot=observability
    )

    matrix = build_decision_support_readiness_matrix(
        coordination_intelligence_snapshot=coordination
    )

    assert matrix["matrix_verdict"] == (
        "decision_support_matrix_landed_live_transport_attemptable"
    )
    axes = {axis["axis"]: axis for axis in matrix["handoff_axes"]}
    assert axes["memory_system_to_acontext_bridge"]["state"] == "attemptable_not_ready"
    assert matrix["readiness"]["ready_to_attempt_live_transport"] is True
    assert matrix["readiness"]["acontext_sink_ready"] is False
    assert matrix["recommended_next_action"] == (
        "run one live local Acontext write/retrieve parity pass"
    )


def test_decision_support_readiness_matrix_refuses_blocked_safe_claim():
    coordination = build_coordination_intelligence_snapshot()
    coordination["claim_boundaries"]["safe_to_claim"].append("acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims safe"):
        build_decision_support_readiness_matrix(
            coordination_intelligence_snapshot=coordination
        )


def test_decision_support_readiness_matrix_refuses_promoted_worker_doctrine():
    coordination = build_coordination_intelligence_snapshot()
    coordination["readiness"]["worker_copyable_doctrine_ready"] = True

    with pytest.raises(CityOpsContractError, match="worker_copyable_doctrine_ready"):
        build_decision_support_readiness_matrix(
            coordination_intelligence_snapshot=coordination
        )


def test_decision_support_readiness_matrix_refuses_raw_conversation_reopen():
    coordination = build_coordination_intelligence_snapshot()
    coordination["derived_from"]["raw_conversation_reopened"] = True

    with pytest.raises(CityOpsContractError, match="raw conversation"):
        build_decision_support_readiness_matrix(
            coordination_intelligence_snapshot=coordination
        )


def test_decision_support_readiness_matrix_write_and_load_temp_fixture(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / "coordination_intelligence_snapshot.json",
        tmp_path / "coordination_intelligence_snapshot.json",
    )
    path = write_decision_support_readiness_matrix_fixture(artifact_dir=tmp_path)

    assert path.name == "decision_support_readiness_matrix.json"
    loaded = load_decision_support_readiness_matrix(artifact_dir=tmp_path)
    assert loaded["schema"] == DECISION_SUPPORT_READINESS_MATRIX_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM
    )


def test_decision_support_readiness_matrix_loader_rejects_promoted_readiness(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / "coordination_intelligence_snapshot.json",
        tmp_path / "coordination_intelligence_snapshot.json",
    )
    path = write_decision_support_readiness_matrix_fixture(artifact_dir=tmp_path)
    matrix = json.loads(path.read_text(encoding="utf-8"))
    matrix["readiness"]["acontext_sink_ready"] = True
    path.write_text(json.dumps(matrix), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="acontext_sink_ready"):
        load_decision_support_readiness_matrix(artifact_dir=tmp_path)
