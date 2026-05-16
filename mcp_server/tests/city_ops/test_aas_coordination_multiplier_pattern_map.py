import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_coordination_multiplier_pattern_map import (
    AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME,
    AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SAFE_CLAIM,
    AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA,
    MULTIPLIER_PATTERN_BLOCKED_CLAIMS,
    build_aas_coordination_multiplier_pattern_map,
    load_aas_coordination_multiplier_pattern_map,
    write_aas_coordination_multiplier_pattern_map,
)
from mcp_server.city_ops.aas_coordination_observability_success_metrics_board import (
    build_aas_coordination_observability_success_metrics_board,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_map() -> dict:
    with (PROOF_BLOCK_DIR / AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_coordination_multiplier_pattern_map_matches_fixture():
    pattern_map = build_aas_coordination_multiplier_pattern_map()

    assert pattern_map == read_fixture_map()
    assert pattern_map["schema"] == AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA
    assert pattern_map["map_verdict"] == "coordination_multiplier_patterns_mapped_internal_only"
    assert pattern_map["readiness"]["pattern_map_landed"] is True
    assert pattern_map["readiness"]["live_acontext_memory_integration_ready"] is False
    assert pattern_map["readiness"]["public_route_ready"] is False
    assert AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SAFE_CLAIM in pattern_map[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_coordination_multiplier_pattern_edges_capture_scaling_patterns():
    pattern_map = build_aas_coordination_multiplier_pattern_map()

    edges = {edge["edge"]: edge for edge in pattern_map["pattern_edges"]}
    assert set(edges) == {
        "memory_to_runtime_truth",
        "irc_to_handoff_continuity",
        "cross_project_to_claim_discipline",
        "observability_to_agent_selection",
    }
    assert all(edge["observed"] is True for edge in edges.values())
    assert edges["memory_to_runtime_truth"]["authorizes_live_runtime"] is False
    assert edges["irc_to_handoff_continuity"][
        "authorizes_runtime_session_manager_change"
    ] is False
    assert edges["cross_project_to_claim_discipline"][
        "authorizes_customer_copy_or_public_route"
    ] is False
    assert edges["observability_to_agent_selection"][
        "authorizes_reputation_or_public_score"
    ] is False


def test_coordination_multiplier_hypotheses_do_not_promote_readiness():
    pattern_map = build_aas_coordination_multiplier_pattern_map()

    hypotheses = {item["hypothesis"]: item for item in pattern_map["multiplier_hypotheses"]}
    assert set(hypotheses) == {
        "memory_bridge_becomes_compounding_after_live_parity",
        "irc_coordination_scales_through_id_headers_not_context_bulk",
        "cross_project_intelligence_is_a_filter_not_an_autopilot",
        "agent_success_metrics_should_reward_not_launching_too_early",
    }
    assert all(item["promotes_readiness_now"] is False for item in hypotheses.values())


def test_coordination_multiplier_scaling_rules_preserve_four_id_handoff():
    pattern_map = build_aas_coordination_multiplier_pattern_map()

    rules = {rule["rule"]: rule for rule in pattern_map["scaling_rules"]}
    assert rules["start_every_future_aas_handoff_with_four_ids"][
        "source_values_present"
    ] is True
    assert rules["carry_sticky_blocked_claims_across_all_reuse"][
        "source_boundary_integrity"
    ] is True
    assert all(rule["customer_visible"] is False for rule in rules.values())


def test_coordination_multiplier_pattern_map_preserves_sticky_blocked_claims():
    pattern_map = build_aas_coordination_multiplier_pattern_map()

    safe = set(pattern_map["claim_boundaries"]["safe_to_claim"])
    blocked = set(pattern_map["claim_boundaries"]["do_not_claim_yet"])
    assert set(MULTIPLIER_PATTERN_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "memory_system_live_acontext_bridge_ready_by_pattern_map" in blocked
    assert "agent_success_score_public_or_reputation_ready_by_pattern_map" in blocked
    assert "worker_copyable_doctrine_ready_by_pattern_map" in blocked


def test_coordination_multiplier_pattern_map_refuses_promoted_source_readiness():
    board = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    board["readiness"]["live_acontext_memory_integration_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        build_aas_coordination_multiplier_pattern_map(metrics_board=board)


def test_coordination_multiplier_pattern_map_refuses_source_authorization():
    board = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    board["integration_tracks"][0]["authorizes_live_runtime"] = True

    with pytest.raises(CityOpsContractError, match="source metrics board promoted authorization"):
        build_aas_coordination_multiplier_pattern_map(metrics_board=board)


def test_coordination_multiplier_pattern_map_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_coordination_multiplier_pattern_map(artifact_dir=tmp_path)

    assert path.name == AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME
    loaded = load_aas_coordination_multiplier_pattern_map(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SAFE_CLAIM
    )


def test_coordination_multiplier_pattern_map_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_coordination_multiplier_pattern_map(artifact_dir=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["readiness"]["public_route_ready"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_coordination_multiplier_pattern_map(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
