import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_coordination_multiplier_pattern_map import (
    build_aas_coordination_multiplier_pattern_map,
)
from mcp_server.city_ops.aas_intelligence_flow_compounder import (
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA,
    INTELLIGENCE_FLOW_BLOCKED_CLAIMS,
    build_aas_intelligence_flow_compounder,
    load_aas_intelligence_flow_compounder,
    write_aas_intelligence_flow_compounder,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_compounder() -> dict:
    with (PROOF_BLOCK_DIR / AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_intelligence_flow_compounder_matches_fixture():
    compounder = build_aas_intelligence_flow_compounder()

    assert compounder == read_fixture_compounder()
    assert compounder["schema"] == AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA
    assert compounder["compounder_verdict"] == (
        "cross_project_intelligence_flows_mapped_internal_only"
    )
    assert compounder["readiness"]["compounder_landed"] is True
    assert compounder["readiness"]["live_acontext_memory_integration_ready"] is False
    assert compounder["readiness"]["public_route_ready"] is False
    assert AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM in compounder[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_intelligence_flows_capture_multiplier_connections_without_authority():
    compounder = build_aas_intelligence_flow_compounder()

    flows = {flow["flow"]: flow for flow in compounder["intelligence_flows"]}
    assert set(flows) == {
        "memory_prerequisites_to_next_proof",
        "irc_handoff_ids_to_coordination_compression",
        "cross_project_patterns_to_claim_quarantine",
        "agent_selection_to_boundary_preservation",
    }
    assert flows["memory_prerequisites_to_next_proof"]["authorizes_live_runtime"] is False
    assert flows["irc_handoff_ids_to_coordination_compression"][
        "authorizes_runtime_session_manager_change"
    ] is False
    assert flows["cross_project_patterns_to_claim_quarantine"][
        "authorizes_autonomous_routing"
    ] is False
    assert flows["agent_selection_to_boundary_preservation"][
        "authorizes_reputation_or_public_score"
    ] is False


def test_compounder_rules_do_not_promote_visibility_or_readiness():
    compounder = build_aas_intelligence_flow_compounder()

    rules = {rule["rule"]: rule for rule in compounder["compounder_rules"]}
    assert set(rules) == {
        "treat_cross_project_intelligence_as_a_filter_not_autopilot",
        "convert_every_insight_to_one_verifiable_next_proof",
        "never_separate_safe_claims_from_blocked_claims",
        "keep_agent_quality_private_until_a_separate_scoring_gate_exists",
    }
    assert all(rule["promotes_readiness_now"] is False for rule in rules.values())
    assert all(rule["customer_visible"] is False for rule in rules.values())


def test_compounder_quarantine_rules_keep_auto_promotion_false():
    compounder = build_aas_intelligence_flow_compounder()

    quarantine = {rule["claim_class"]: rule for rule in compounder["quarantine_rules"]}
    assert set(quarantine) == {
        "live_runtime_memory",
        "customer_or_public_packaging",
        "dispatch_or_operator_queue",
        "reputation_or_worker_skill_dna",
        "payment_or_production_health",
    }
    assert all(rule["may_auto_promote"] is False for rule in quarantine.values())


def test_compounder_decision_table_names_next_proofs_without_promoting():
    compounder = build_aas_intelligence_flow_compounder()

    decisions = {item["decision"]: item for item in compounder["decision_table"]}
    assert decisions["next_runtime_memory_step"]["internal_recommendation"] == (
        "fix_or_bypass_docker_pull_stall_then_inventory_all_required_images"
    )
    assert all(item["may_auto_promote"] is False for item in decisions.values())
    assert all(item["customer_visible"] is False for item in decisions.values())


def test_compounder_preserves_sticky_blocked_claims():
    compounder = build_aas_intelligence_flow_compounder()

    safe = set(compounder["claim_boundaries"]["safe_to_claim"])
    blocked = set(compounder["claim_boundaries"]["do_not_claim_yet"])
    assert set(INTELLIGENCE_FLOW_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "memory_system_live_write_retrieve_ready_by_compounder" in blocked
    assert "customer_delivery_approval_ready_by_compounder" in blocked
    assert "worker_copyable_doctrine_ready_by_compounder" in blocked


def test_compounder_refuses_promoted_source_readiness():
    source = copy.deepcopy(build_aas_coordination_multiplier_pattern_map())
    source["readiness"]["cross_project_autorouting_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        build_aas_intelligence_flow_compounder(pattern_map=source)


def test_compounder_refuses_source_authorization():
    source = copy.deepcopy(build_aas_coordination_multiplier_pattern_map())
    source["pattern_edges"][0]["authorizes_live_runtime"] = True

    with pytest.raises(CityOpsContractError, match="source pattern map promoted authorization"):
        build_aas_intelligence_flow_compounder(pattern_map=source)


def test_compounder_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_intelligence_flow_compounder(artifact_dir=tmp_path)

    assert path.name == AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME
    loaded = load_aas_intelligence_flow_compounder(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM
    )


def test_compounder_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_intelligence_flow_compounder(artifact_dir=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["readiness"]["public_route_ready"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_intelligence_flow_compounder(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
