"""Tests for the internal/admin AAS system-integration strength bridge packet."""

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
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM,
    build_aas_no_answer_daytime_operator_prompt_packet,
    write_aas_no_answer_daytime_operator_prompt_packet,
)
from mcp_server.city_ops.aas_system_integration_strength_bridge_packet import (
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME,
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SCHEMA,
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_STATUS,
    BRIDGE_LANES,
    FALSE_FLAGS,
    REQUIRED_PACKET_FIELDS,
    STRENGTH_BRIDGE_BLOCKED_CLAIMS,
    build_aas_system_integration_strength_bridge_packet,
    load_aas_system_integration_strength_bridge_packet,
    write_aas_system_integration_strength_bridge_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_packet() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_strength_bridge_packet_matches_persisted_artifact_and_loader() -> None:
    packet = build_aas_system_integration_strength_bridge_packet()

    assert packet == read_fixture_packet()
    assert load_aas_system_integration_strength_bridge_packet() == packet
    assert packet["schema"] == AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SCHEMA
    assert packet["packet_status"] == AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_STATUS
    assert AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_strength_bridge_consumes_no_answer_prompt_packet_by_digest() -> None:
    packet = build_aas_system_integration_strength_bridge_packet()
    source = packet["source_prompt_packet"]

    assert source["file"] == AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME
    assert source["safe_claim"] == AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM
    assert len(source["digest_sha256"]) == 64
    assert "hold_all_aas_lanes" in source["allowed_answer_values"]
    assert "answer_runtime_memory_read_only_prerequisite_inventory_only" in source[
        "allowed_answer_values"
    ]


def test_strength_bridge_is_read_only_and_creates_no_runtime_payment_or_dispatch() -> None:
    packet = build_aas_system_integration_strength_bridge_packet()

    for key, expected in FALSE_FLAGS.items():
        assert packet["readiness"][key] is expected
    assert packet["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "use_strength_bridge_as_read_only_handoff_then_wait_for_one_explicit_answer_or_hold",
    }

    bridge = packet["system_integration_strength_bridge"]
    assert bridge["allowed_use"] == "internal_admin_strength_connection_packet_only"
    assert bridge["bridge_goal"] == (
        "connect_current_system_strengths_to_the_no_answer_aas_packet_without_creating_permission"
    )
    assert bridge["still_blocked"] is True


def test_strength_bridge_lanes_have_required_fields_and_safe_postures() -> None:
    packet = build_aas_system_integration_strength_bridge_packet()
    bridge = packet["system_integration_strength_bridge"]

    assert set(REQUIRED_PACKET_FIELDS) <= set(bridge["required_packet_fields"])
    assert [lane["lane"] for lane in bridge["lanes"]] == BRIDGE_LANES
    for lane in bridge["lanes"]:
        assert set(REQUIRED_PACKET_FIELDS) <= set(lane["required_packet_fields"])
        assert lane["source_file"] == AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME
        assert len(lane["source_digest_sha256"]) == 64
        assert lane["safe_claim"] == AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM
        assert lane["blocked_claims"]
        assert lane["next_gate"] == "separate_explicit_operator_answer_receipt_then_specific_gate"
        assert lane["recommended_posture"]

    postures = {lane["lane"]: lane["recommended_posture"] for lane in bridge["lanes"]}
    assert postures["memory_acontext_planning"] == (
        "digest_only_no_live_runtime_memory_write_or_retrieve"
    )
    assert postures["irc_session_management"] == (
        "read_only_handoff_no_irc_or_session_manager_mutation"
    )
    assert postures["payment_integration_strength_reference"] == (
        "no_payment_or_chain_reverification_from_this_bridge"
    )


def test_strength_bridge_preserves_claim_boundaries_and_stopped_project_firewall() -> None:
    packet = build_aas_system_integration_strength_bridge_packet()
    safe = set(packet["claim_boundaries"]["safe_to_claim"])
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])

    assert set(STRENGTH_BRIDGE_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "creates_answer_receipt",
        "treats_system_integration_as_permission",
        "authorizes_catalog_pricing_quote_route_queue_or_dispatch",
        "mutates_runtime_acontext_irc_or_session_manager",
        "reverifies_payment_production_or_chain_integrations",
        "attaches_reputation_worker_skill_dna_or_portable_credential",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert packet["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_strength_bridge_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    write_aas_no_answer_daytime_operator_prompt_packet(artifact_dir=tmp_path)
    path = write_aas_system_integration_strength_bridge_packet(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME
    assert load_aas_system_integration_strength_bridge_packet(artifact_dir=tmp_path)[
        "packet_id"
    ] == "execution_market.aas.system_integration_strength_bridge_packet.2026_06_07_0300"


def test_strength_bridge_rejects_promoted_source_prompt_packet() -> None:
    source = copy.deepcopy(build_aas_no_answer_daytime_operator_prompt_packet())
    source["current_operator_state"]["answer_receipt_created"] = True

    with pytest.raises(CityOpsContractError, match="answer_receipt_created"):
        build_aas_system_integration_strength_bridge_packet(source_prompt_packet=source)


def test_strength_bridge_rejects_runtime_or_payment_promotion() -> None:
    packet = build_aas_system_integration_strength_bridge_packet()
    packet["readiness"]["bridge_mutates_runtime_acontext_irc_or_session_manager"] = True

    with pytest.raises(CityOpsContractError, match="mutates_runtime_acontext_irc_or_session_manager"):
        load_aas_system_integration_strength_bridge_packet(
            artifact_dir=_write_fixture_triple(packet)
        )

    packet = build_aas_system_integration_strength_bridge_packet()
    packet["readiness"]["bridge_reverifies_payment_or_production"] = True

    with pytest.raises(CityOpsContractError, match="reverifies_payment_or_production"):
        load_aas_system_integration_strength_bridge_packet(
            artifact_dir=_write_fixture_triple(packet)
        )


def test_strength_bridge_rejects_lane_drift_or_missing_required_field() -> None:
    packet = build_aas_system_integration_strength_bridge_packet()
    packet["system_integration_strength_bridge"]["lanes"][0]["lane"] = "runtime_mutation_lane"

    with pytest.raises(CityOpsContractError, match="lane drift"):
        load_aas_system_integration_strength_bridge_packet(
            artifact_dir=_write_fixture_triple(packet)
        )

    packet = build_aas_system_integration_strength_bridge_packet()
    packet["system_integration_strength_bridge"]["lanes"][0]["required_packet_fields"] = [
        field
        for field in packet["system_integration_strength_bridge"]["lanes"][0][
            "required_packet_fields"
        ]
        if field != "blocked_claims"
    ]

    with pytest.raises(CityOpsContractError, match="lane missing required fields"):
        load_aas_system_integration_strength_bridge_packet(
            artifact_dir=_write_fixture_triple(packet)
        )


def _write_fixture_triple(packet: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    write_aas_no_answer_daytime_operator_prompt_packet(artifact_dir=tmp)
    (tmp / AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME).write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return tmp
