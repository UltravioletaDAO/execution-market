"""Tests for the internal/admin AAS stale-cron firewall work queue."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_no_answer_daytime_operator_prompt_packet import (
    write_aas_no_answer_daytime_operator_prompt_packet,
)
from mcp_server.city_ops.aas_stale_cron_firewall_work_queue import (
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME,
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM,
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SCHEMA,
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_STATUS,
    ALLOWED_NEXT_ACTIONS,
    FIREWALL_BLOCKED_CLAIMS,
    FIREWALL_READINESS,
    STOPPED_LANE_DECISIONS,
    build_aas_stale_cron_firewall_work_queue,
    load_aas_stale_cron_firewall_work_queue,
    write_aas_stale_cron_firewall_work_queue,
)
from mcp_server.city_ops.aas_system_integration_strength_bridge_packet import (
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME,
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM,
    BRIDGE_LANES,
    build_aas_system_integration_strength_bridge_packet,
    write_aas_system_integration_strength_bridge_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_queue() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def write_prerequisites(artifact_dir: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=artifact_dir)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=artifact_dir)
    write_aas_no_answer_daytime_operator_prompt_packet(artifact_dir=artifact_dir)
    write_aas_system_integration_strength_bridge_packet(artifact_dir=artifact_dir)


def test_stale_cron_firewall_matches_persisted_artifact_and_loader() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()

    assert queue == read_fixture_queue()
    assert load_aas_stale_cron_firewall_work_queue() == queue
    assert queue["schema"] == AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SCHEMA
    assert queue["queue_status"] == AAS_STALE_CRON_FIREWALL_WORK_QUEUE_STATUS
    assert AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM in queue[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM in queue["claim_boundaries"][
        "safe_to_claim"
    ]


def test_stale_cron_firewall_consumes_strength_bridge_by_digest() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()
    source = queue["source_strength_bridge"]

    assert source["file"] == AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME
    assert source["safe_claim"] == AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM
    assert len(source["digest_sha256"]) == 64


def test_stale_cron_firewall_skips_stopped_projects_and_keeps_aas_only() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()

    assert queue["governing_priority"]["source_precedence"] == (
        "dream_priorities_wins_over_stale_cron_payload"
    )
    assert queue["governing_priority"]["allowed_lane"] == (
        "Execution Market AAS / City-as-a-Service internal/admin planning"
    )
    assert queue["stale_payload_reconciliation"]["stopped_lane_decisions"] == (
        STOPPED_LANE_DECISIONS
    )
    assert {row["lane"] for row in STOPPED_LANE_DECISIONS} == {
        "autojob_pull_analysis_or_em_integration",
        "frontier_academy_guide_or_pdf_expansion",
        "kk_v2_swarm_reputation_lifecycle_or_orchestrator",
        "karmacadabra_v2",
    }
    assert all(row["decision"] == "skip" for row in STOPPED_LANE_DECISIONS)


def test_stale_cron_firewall_connects_system_strengths_without_permission() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()
    connections = queue["system_integration_connections"]

    assert [connection["aas_connection"] for connection in connections] == [
        "memory_to_acontext_digest_carry_forward",
        "irc_session_management_handoff_capsules",
        "decision_menu_without_autorouting",
        "firewall_compliance_metric",
        "future_launch_prerequisite_context_only",
    ]
    for connection in connections:
        assert connection["safe_action"]
        assert connection["blocked_promotion"]
    assert "payment_production_or_chain_reverification" in connections[-1]["blocked_promotion"]


def test_stale_cron_firewall_next_actions_hold_until_real_answer_or_runtime_truth() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()

    assert queue["allowed_next_actions"] == ALLOWED_NEXT_ACTIONS
    by_condition = {action["condition"]: action for action in ALLOWED_NEXT_ACTIONS}
    assert by_condition["no_real_operator_answer_exists"]["allowed_now"] is True
    assert by_condition["future_cron_mentions_stopped_projects"]["allowed_now"] is True
    assert by_condition["real_operator_answer_arrives"]["allowed_now"] is False
    assert by_condition["runtime_truth_becomes_available_later"]["allowed_now"] is False
    assert queue["selected_posture_now"] == "pause_aas_proof_layering"


def test_stale_cron_firewall_preserves_false_readiness_and_claim_boundaries() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()

    for key, expected in FIREWALL_READINESS.items():
        assert queue["readiness"][key] is expected
    assert queue["readiness"]["stopped_project_pull_performed"] is False
    assert queue["readiness"]["runtime_acontext_irc_or_session_manager_mutated"] is False
    assert queue["readiness"]["payment_or_production_reverified"] is False

    safe = set(queue["claim_boundaries"]["safe_to_claim"])
    blocked = set(queue["claim_boundaries"]["do_not_claim_yet"])
    assert set(FIREWALL_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "performed_autojob_pull_or_analysis",
        "expanded_frontier_academy",
        "continued_kk_v2",
        "mutated_runtime_acontext_irc_or_session_manager",
        "reverified_payment_production_or_chain_state",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_stale_cron_firewall_write_roundtrip(tmp_path: Path) -> None:
    write_prerequisites(tmp_path)
    path = write_aas_stale_cron_firewall_work_queue(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME
    loaded = load_aas_stale_cron_firewall_work_queue(artifact_dir=tmp_path)
    assert loaded["queue_id"] == (
        "execution_market.aas.stale_cron_firewall_work_queue.2026_06_12_0300"
    )


def test_stale_cron_firewall_rejects_promoted_source_bridge() -> None:
    bridge = build_aas_system_integration_strength_bridge_packet()
    bridge["governing_priority"]["stopped_project_firewall"]["autojob_work_allowed"] = True

    with pytest.raises(CityOpsContractError, match="stopped-project drift"):
        build_aas_stale_cron_firewall_work_queue(strength_bridge_packet=bridge)


def test_stale_cron_firewall_rejects_lane_drift_or_future_action_promotion() -> None:
    bridge = build_aas_system_integration_strength_bridge_packet()
    bridge["system_integration_strength_bridge"]["lanes"][0]["lane"] = "autojob_runtime_lane"

    with pytest.raises(CityOpsContractError, match="lane drift"):
        build_aas_stale_cron_firewall_work_queue(strength_bridge_packet=bridge)

    queue = build_aas_stale_cron_firewall_work_queue()
    queue["allowed_next_actions"][0]["allowed_now"] = True

    with pytest.raises(CityOpsContractError, match="next action drift"):
        load_aas_stale_cron_firewall_work_queue(artifact_dir=_write_fixture_set(queue))


def test_stale_cron_firewall_rejects_runtime_or_payment_promotion() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()
    queue["readiness"]["runtime_acontext_irc_or_session_manager_mutated"] = True

    with pytest.raises(CityOpsContractError, match="runtime_acontext_irc_or_session_manager_mutated"):
        load_aas_stale_cron_firewall_work_queue(artifact_dir=_write_fixture_set(queue))

    queue = build_aas_stale_cron_firewall_work_queue()
    queue["readiness"]["payment_or_production_reverified"] = True

    with pytest.raises(CityOpsContractError, match="payment_or_production_reverified"):
        load_aas_stale_cron_firewall_work_queue(artifact_dir=_write_fixture_set(queue))


def test_source_bridge_still_has_expected_lanes() -> None:
    bridge = build_aas_system_integration_strength_bridge_packet()
    assert [
        lane["lane"] for lane in bridge["system_integration_strength_bridge"]["lanes"]
    ] == BRIDGE_LANES


def _write_fixture_set(queue: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_prerequisites(tmp)
    (tmp / AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME).write_text(
        json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return tmp
