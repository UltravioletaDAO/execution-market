import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight import (
    build_acontext_live_preflight_result,
    build_blocked_acontext_preflight_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.operator_debug_surface import build_operator_debug_surface
from mcp_server.city_ops.proof_observability import (
    PROOF_OBSERVABILITY_SAFE_CLAIM,
    PROOF_OBSERVABILITY_SCHEMA,
    build_proof_observability_snapshot,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_snapshot() -> dict:
    with (PROOF_BLOCK_DIR / "proof_observability_snapshot.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_proof_observability_snapshot_matches_fixture():
    snapshot = build_proof_observability_snapshot()

    assert snapshot == read_fixture_snapshot()
    assert snapshot["schema"] == PROOF_OBSERVABILITY_SCHEMA
    assert (
        snapshot["observability_verdict"]
        == "proof_observability_metrics_landed_live_transport_blocked"
    )
    assert PROOF_OBSERVABILITY_SAFE_CLAIM in snapshot["claim_boundaries"]["safe_to_claim"]
    assert "acontext_sink_ready" in snapshot["claim_boundaries"]["do_not_claim_yet"]
    assert "worker-copyable municipal doctrine" in snapshot["claim_boundaries"]["do_not_claim_yet"]
    assert snapshot["readiness"]["metrics_promote_readiness"] is False
    assert snapshot["readiness"]["acontext_sink_ready"] is False
    assert snapshot["readiness"]["runtime_parity_proven"] is False


def test_proof_observability_metrics_preserve_honest_state():
    snapshot = build_proof_observability_snapshot()
    metrics = snapshot["metrics"]
    signals = {signal["signal"]: signal for signal in snapshot["signals"]}

    assert metrics["safe_claim_count"] == len(snapshot["claim_boundaries"]["safe_to_claim"])
    assert metrics["blocked_claim_count"] == len(
        snapshot["claim_boundaries"]["do_not_claim_yet"]
    )
    assert metrics["all_critical_readiness_flags_false"] is True
    assert metrics["local_transport_parity_fixture_passed"] is True
    assert metrics["worker_copyable_surface_enabled"] is False
    assert metrics["copyable_worker_instruction_allowed"] is False
    assert signals["claim_boundary_visibility"]["status"] == "passed"
    assert signals["live_acontext_prerequisites"]["status"] == "blocked"
    assert signals["readiness_honesty"]["status"] == "passed"


def test_proof_observability_can_mark_transport_attemptable_without_readiness():
    probe = build_blocked_acontext_preflight_probe()
    probe["docker"].update({"available": True, "exit_code": 0, "error": None})
    probe["python_sdk"]["available"] = True
    probe["api"].update({"reachable": True, "status_code": 200, "error": None})
    probe["dashboard"].update({"reachable": True, "status_code": 200, "error": None})
    preflight = build_acontext_live_preflight_result(probe=probe)
    surface = build_operator_debug_surface(acontext_live_preflight_result=preflight)

    snapshot = build_proof_observability_snapshot(operator_debug_surface=surface)

    assert (
        snapshot["observability_verdict"]
        == "proof_observability_metrics_landed_live_transport_attemptable"
    )
    assert snapshot["readiness"]["ready_to_attempt_live_transport"] is True
    assert snapshot["readiness"]["acontext_sink_ready"] is False
    assert snapshot["readiness"]["runtime_parity_proven"] is False
    assert snapshot["decision_support"]["recommended_next_action"] == (
        "run one live local Acontext write/retrieve parity pass"
    )


def test_proof_observability_refuses_blocked_safe_claim():
    surface = build_operator_debug_surface()
    surface["claim_boundaries"]["safe_to_claim"].append("acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims safe"):
        build_proof_observability_snapshot(operator_debug_surface=surface)


def test_proof_observability_refuses_worker_copyable_upgrade():
    surface = build_operator_debug_surface()
    surface["operator_visibility"]["copyable_worker_instruction"]["allowed"] = True

    with pytest.raises(CityOpsContractError, match="worker-copyable upgrade"):
        build_proof_observability_snapshot(operator_debug_surface=surface)


def test_proof_observability_refuses_promoted_runtime_readiness():
    surface = build_operator_debug_surface()
    surface["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="runtime_parity_proven"):
        build_proof_observability_snapshot(operator_debug_surface=surface)


def test_proof_observability_refuses_non_read_only_surface():
    surface = build_operator_debug_surface()
    surface["derived_from"]["writes_live_sink"] = True

    with pytest.raises(CityOpsContractError, match="live sink"):
        build_proof_observability_snapshot(operator_debug_surface=surface)
