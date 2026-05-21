import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_coordination_observability_success_metrics_read_surface import (
    build_aas_coordination_observability_success_metrics_read_surface,
)
from mcp_server.city_ops.aas_intelligence_flow_compounder import (
    build_aas_intelligence_flow_compounder,
)
from mcp_server.city_ops.aas_strength_connection_control_packet import (
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME,
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA,
    STRENGTH_CONNECTION_BLOCKED_CLAIMS,
    build_aas_strength_connection_control_packet,
    load_aas_strength_connection_control_packet,
    write_aas_strength_connection_control_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_packet() -> dict:
    with (PROOF_BLOCK_DIR / AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_strength_connection_packet_matches_fixture():
    packet = build_aas_strength_connection_control_packet()

    assert packet == read_fixture_packet()
    assert packet["schema"] == AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA
    assert packet["packet_verdict"] == "strength_connections_mapped_internal_admin_only"
    assert packet["readiness"]["packet_landed"] is True
    assert packet["readiness"]["one_next_proof_queue_preserved"] is True
    assert packet["readiness"]["live_acontext_memory_integration_ready"] is False
    assert AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_strength_connection_cards_amplify_current_strengths_without_revalidation():
    packet = build_aas_strength_connection_control_packet()

    cards = {card["strength"]: card for card in packet["strength_connection_cards"]}
    assert set(cards) == {
        "latest_city_ops_code_changes",
        "eight_chain_payment_integration_perfection",
        "intelligent_memory_with_26_plus_insights",
        "production_infrastructure_operational",
        "legendary_agent_coordination",
    }
    assert cards["latest_city_ops_code_changes"]["verification_badge"] == (
        "consumed_from_local_artifact_graph"
    )
    assert cards["eight_chain_payment_integration_perfection"][
        "verification_badge"
    ] == "declared_context_only_not_reverified_here"
    assert cards["production_infrastructure_operational"]["reverified_by_this_packet"] is False
    assert all(card["authorizes_live_or_customer_readiness"] is False for card in cards.values())


def test_strength_connection_lanes_do_not_authorize_runtime_or_customer_surfaces():
    packet = build_aas_strength_connection_control_packet()

    lanes = {lane["lane"]: lane for lane in packet["integration_lane_cards"]}
    assert set(lanes) == {
        "memory_system_to_acontext",
        "irc_session_management",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
    }
    assert lanes["memory_system_to_acontext"]["authorizes_live_runtime"] is False
    assert lanes["irc_session_management"][
        "authorizes_runtime_session_manager_change"
    ] is False
    assert lanes["cross_project_decision_support"]["authorizes_autonomous_routing"] is False
    assert lanes["agent_observability_success_metrics"][
        "authorizes_live_dashboard_or_reputation"
    ] is False


def test_strength_connection_packet_preserves_one_next_proof_queue():
    packet = build_aas_strength_connection_control_packet()

    queue = packet["one_next_proof_queue"]
    assert len(queue) == 1
    assert queue[0]["slot"] == 1
    assert queue[0]["proof"] == (
        "acontext_runtime_memory_prerequisites_then_single_live_parity_attempt"
    )
    assert queue[0]["customer_visible"] is False
    assert queue[0]["may_auto_promote"] is False


def test_strength_connection_packet_preserves_sticky_blocked_claims():
    packet = build_aas_strength_connection_control_packet()

    safe = set(packet["claim_boundaries"]["safe_to_claim"])
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    assert set(STRENGTH_CONNECTION_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "strength_packet_revalidates_eight_chain_payments" in blocked
    assert "strength_packet_revalidates_production_infrastructure" in blocked
    assert "strength_packet_publishes_worker_copyable_doctrine" in blocked


def test_strength_connection_packet_refuses_source_id_mismatch():
    compounder = copy.deepcopy(build_aas_intelligence_flow_compounder())
    compounder["review_packet_id"] = "different_review_packet"

    with pytest.raises(CityOpsContractError, match="source invariant id mismatch"):
        build_aas_strength_connection_control_packet(
            intelligence_compounder=compounder
        )


def test_strength_connection_packet_refuses_promoted_metrics_surface_readiness():
    surface = copy.deepcopy(build_aas_coordination_observability_success_metrics_read_surface())
    surface["readiness"]["agent_observability_live_dashboard_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        build_aas_strength_connection_control_packet(metrics_surface=surface)


def test_strength_connection_packet_refuses_promoted_compounder_authorization():
    compounder = copy.deepcopy(build_aas_intelligence_flow_compounder())
    compounder["intelligence_flows"][0]["authorizes_live_runtime"] = True

    with pytest.raises(CityOpsContractError, match="source compounder promoted authorization"):
        build_aas_strength_connection_control_packet(
            intelligence_compounder=compounder
        )


def test_strength_connection_packet_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_strength_connection_control_packet(artifact_dir=tmp_path)

    assert path.name == AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME
    loaded = load_aas_strength_connection_control_packet(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM
    )


def test_strength_connection_packet_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_strength_connection_control_packet(artifact_dir=tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["readiness"]["payment_coverage_reverified_by_this_packet"] = True
    path.write_text(json.dumps(packet), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_strength_connection_control_packet(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
