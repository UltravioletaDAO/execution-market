import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_exponential_value_pathfinder import (
    AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
    AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM,
    AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA,
    EXPONENTIAL_VALUE_BLOCKED_CLAIMS,
    build_aas_exponential_value_pathfinder,
    load_aas_exponential_value_pathfinder,
    write_aas_exponential_value_pathfinder,
)
from mcp_server.city_ops.aas_strength_connection_control_packet import (
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
    build_aas_strength_connection_control_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_pathfinder() -> dict:
    with (PROOF_BLOCK_DIR / AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_exponential_value_pathfinder_matches_fixture_and_loader():
    pathfinder = build_aas_exponential_value_pathfinder()

    assert pathfinder == read_fixture_pathfinder()
    assert load_aas_exponential_value_pathfinder() == pathfinder
    assert pathfinder["schema"] == AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA
    assert pathfinder["pathfinder_verdict"] == (
        "exponential_value_connections_mapped_internal_admin_only"
    )
    assert pathfinder["readiness"]["pathfinder_landed"] is True
    assert pathfinder["readiness"]["one_next_proof_selected_from_existing_queue"] is True
    assert pathfinder["readiness"]["live_acontext_memory_integration_ready"] is False
    assert AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM in pathfinder[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM in pathfinder[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_pathfinder_names_five_exponential_loops_without_authorizing_surfaces():
    pathfinder = build_aas_exponential_value_pathfinder()

    loops = {loop["loop"]: loop for loop in pathfinder["exponential_value_loops"]}
    assert set(loops) == {
        "memory_insight_to_acontext_proof_loop",
        "irc_four_id_to_swarm_handoff_loop",
        "cross_project_signal_to_aas_gate_selection_loop",
        "agent_observability_to_private_selection_loop",
        "landed_code_to_proof_ladder_loop",
    }
    assert loops["memory_insight_to_acontext_proof_loop"]["value_score"] == 5
    assert loops["landed_code_to_proof_ladder_loop"]["value_score"] == 5
    for loop in loops.values():
        assert loop["may_auto_promote"] is False
        for key, value in loop.items():
            if key.startswith("authorizes_"):
                assert value is False


def test_pathfinder_recommends_existing_one_next_proof_from_strength_packet():
    pathfinder = build_aas_exponential_value_pathfinder()

    recommended = pathfinder["recommended_next_proof"]
    assert recommended["selected_from_source_queue"] is True
    assert recommended["source_slot"] == 1
    assert recommended["proof"] == (
        "acontext_runtime_memory_prerequisites_then_single_live_parity_attempt"
    )
    assert recommended["customer_visible"] is False
    assert recommended["may_auto_promote"] is False

    pathways = pathfinder["ranked_pathways"]
    assert [pathway["rank"] for pathway in pathways] == [1, 2, 3]
    assert pathways[0]["pathway"] == (
        "prove_acontext_runtime_memory_prerequisites_then_single_live_parity_attempt"
    )
    assert all(pathway["customer_visible"] is False for pathway in pathways)
    assert all(pathway["may_auto_promote"] is False for pathway in pathways)


def test_pathfinder_preserves_four_id_header_and_sticky_blocked_claims():
    pathfinder = build_aas_exponential_value_pathfinder()

    header = pathfinder["four_id_handoff_header"]
    for key in [
        "proof_anchor_id",
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
    ]:
        assert header[key] == pathfinder[key]

    safe = set(pathfinder["claim_boundaries"]["safe_to_claim"])
    blocked = set(pathfinder["claim_boundaries"]["do_not_claim_yet"])
    assert set(EXPONENTIAL_VALUE_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "pathfinder_promotes_live_acontext_memory" in blocked
    assert "pathfinder_emits_erc8004_reputation_or_worker_skill_dna" in blocked
    assert "pathfinder_authorizes_customer_delivery_or_publication" in blocked


def test_pathfinder_quarantines_tempting_connections():
    pathfinder = build_aas_exponential_value_pathfinder()

    quarantine = {
        row["tempting_connection"]: row for row in pathfinder["quarantine_table"]
    }
    assert set(quarantine) == {
        "memory_system_data_directly_into_live_acontext",
        "irc_coordination_patterns_change_runtime_manager",
        "coordination_scores_become_erc8004_reputation_or_worker_skill_dna",
        "portfolio_packaging_goes_customer_visible",
    }
    assert quarantine["memory_system_data_directly_into_live_acontext"][
        "blocked_claim"
    ] == "pathfinder_promotes_live_acontext_memory"
    assert quarantine["portfolio_packaging_goes_customer_visible"][
        "blocked_claim"
    ] == "pathfinder_authorizes_customer_delivery_or_publication"


def test_pathfinder_refuses_source_lane_promotion():
    source = copy.deepcopy(build_aas_strength_connection_control_packet())
    source["integration_lane_cards"][0]["authorizes_live_runtime"] = True

    with pytest.raises(CityOpsContractError, match="source strength lane promoted authorization"):
        build_aas_exponential_value_pathfinder(strength_packet=source)


def test_pathfinder_refuses_source_next_proof_promotion():
    source = copy.deepcopy(build_aas_strength_connection_control_packet())
    source["one_next_proof_queue"][0]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="source next proof promoted visibility"):
        build_aas_exponential_value_pathfinder(strength_packet=source)


def test_pathfinder_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_exponential_value_pathfinder(artifact_dir=tmp_path)

    assert path.name == AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME
    loaded = load_aas_exponential_value_pathfinder(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM
    )


def test_pathfinder_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_exponential_value_pathfinder(artifact_dir=tmp_path)
    pathfinder = json.loads(path.read_text(encoding="utf-8"))
    pathfinder["readiness"]["customer_visible_packaging_ready"] = True
    path.write_text(json.dumps(pathfinder), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_exponential_value_pathfinder(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
