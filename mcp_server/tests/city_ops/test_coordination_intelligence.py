import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight import (
    build_acontext_live_preflight_result,
    build_blocked_acontext_preflight_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.coordination_intelligence import (
    COORDINATION_INTELLIGENCE_SAFE_CLAIM,
    COORDINATION_INTELLIGENCE_SCHEMA,
    build_coordination_intelligence_snapshot,
)
from mcp_server.city_ops.operator_debug_surface import build_operator_debug_surface
from mcp_server.city_ops.proof_observability import build_proof_observability_snapshot

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_snapshot() -> dict:
    with (PROOF_BLOCK_DIR / "coordination_intelligence_snapshot.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_coordination_intelligence_snapshot_matches_fixture():
    snapshot = build_coordination_intelligence_snapshot()

    assert snapshot == read_fixture_snapshot()
    assert snapshot["schema"] == COORDINATION_INTELLIGENCE_SCHEMA
    assert (
        snapshot["coordination_verdict"]
        == "coordination_intelligence_landed_live_transport_blocked"
    )
    assert COORDINATION_INTELLIGENCE_SAFE_CLAIM in snapshot["claim_boundaries"][
        "safe_to_claim"
    ]
    assert "acontext_sink_ready" in snapshot["claim_boundaries"]["do_not_claim_yet"]
    assert "autonomous_city_dispatch_ready" in snapshot["claim_boundaries"][
        "do_not_claim_yet"
    ]
    assert snapshot["readiness"]["patterns_promote_readiness"] is False
    assert snapshot["readiness"]["acontext_sink_ready"] is False


def test_coordination_intelligence_names_scaling_patterns():
    snapshot = build_coordination_intelligence_snapshot()
    patterns = {pattern["pattern"]: pattern for pattern in snapshot["coordination_patterns"]}
    rules = {rule["rule"]: rule for rule in snapshot["scaling_rules"]}
    effects = {effect["effect"]: effect for effect in snapshot["multiplier_effects"]}

    assert patterns["compact_artifact_spine"]["status"] == "active"
    assert patterns["operator_only_learning_reuse"]["status"] == "active_but_conservative"
    assert patterns["transport_is_not_truth"]["status"] == "blocked_until_live_sink"
    assert "coordinate_by_invariant_ids" in rules
    assert "memory_system_data_becomes_dispatch_capital" in effects
    assert "irc_coordination_lessons_become_product_rules" in effects


def test_coordination_intelligence_can_mark_transport_attemptable_without_readiness():
    probe = build_blocked_acontext_preflight_probe()
    probe["docker"].update({"available": True, "exit_code": 0, "error": None})
    probe["python_sdk"]["available"] = True
    probe["api"].update({"reachable": True, "status_code": 200, "error": None})
    probe["dashboard"].update({"reachable": True, "status_code": 200, "error": None})
    preflight = build_acontext_live_preflight_result(probe=probe)
    surface = build_operator_debug_surface(acontext_live_preflight_result=preflight)
    observability = build_proof_observability_snapshot(operator_debug_surface=surface)

    snapshot = build_coordination_intelligence_snapshot(
        proof_observability_snapshot=observability
    )

    assert (
        snapshot["coordination_verdict"]
        == "coordination_intelligence_landed_live_transport_attemptable"
    )
    assert snapshot["readiness"]["ready_to_attempt_live_transport"] is True
    assert snapshot["readiness"]["acontext_sink_ready"] is False
    assert snapshot["readiness"]["runtime_parity_proven"] is False
    assert snapshot["decision_support"]["recommended_next_action"] == (
        "run one live local Acontext write/retrieve parity pass"
    )


def test_coordination_intelligence_refuses_blocked_safe_claim():
    observability = build_proof_observability_snapshot()
    observability["claim_boundaries"]["safe_to_claim"].append("acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims safe"):
        build_coordination_intelligence_snapshot(
            proof_observability_snapshot=observability
        )


def test_coordination_intelligence_refuses_promoted_worker_doctrine():
    observability = build_proof_observability_snapshot()
    observability["readiness"]["worker_copyable_doctrine_ready"] = True

    with pytest.raises(CityOpsContractError, match="worker_copyable_doctrine_ready"):
        build_coordination_intelligence_snapshot(
            proof_observability_snapshot=observability
        )


def test_coordination_intelligence_refuses_non_read_only_source():
    observability = build_proof_observability_snapshot()
    observability["derived_from"]["read_only"] = False

    with pytest.raises(CityOpsContractError, match="read-only source"):
        build_coordination_intelligence_snapshot(
            proof_observability_snapshot=observability
        )
