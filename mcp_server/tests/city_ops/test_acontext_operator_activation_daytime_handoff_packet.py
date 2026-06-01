"""Tests for the Acontext operator activation daytime handoff packet."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_operator_activation_daytime_handoff_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_STOP_LINE,
    DAYTIME_HANDOFF_BLOCKED_CLAIMS,
    build_acontext_operator_activation_daytime_handoff_packet,
    load_acontext_operator_activation_daytime_handoff_packet,
    write_acontext_operator_activation_daytime_handoff_packet,
)
from mcp_server.city_ops.acontext_operator_activation_read_only_review_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM,
    build_acontext_operator_activation_read_only_review_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME).exists()


def test_daytime_handoff_packet_matches_fixture() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert packet == fixture
    assert load_acontext_operator_activation_daytime_handoff_packet() == packet
    assert packet["schema"] == ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA
    assert packet["status_verdict"] == "daytime_handoff_packet_landed_current_hold_preserved_operator_answer_still_required"
    assert ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_daytime_handoff_is_internal_admin_only_and_not_approval() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    handoff = packet["daytime_handoff_packet"]

    assert handoff["intended_audience"] == "internal_admin_operator_only"
    assert handoff["not_customer_copy"] is True
    assert handoff["not_worker_instruction"] is True
    assert handoff["handoff_only_landed"] is True
    assert handoff["handoff_is_not_approval"] is True
    assert handoff["current_decision"] == "hold_no_runtime_mutation"
    assert handoff["effective_decision_after_handoff"] == "hold_no_runtime_mutation"
    assert handoff["explicit_operator_answer_present"] is False
    assert handoff["operator_approval_record_present"] is False
    assert handoff["runtime_mutation_authorized"] is False
    assert handoff["bounded_activation_test_authorized"] is False


def test_daytime_handoff_displays_only_three_non_authorizing_choices() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    choices = packet["daytime_handoff_packet"]["allowed_operator_choices_to_request"]

    assert [item["choice_id"] for item in choices] == [
        "hold_no_runtime_mutation",
        "approve_design_only_wiring_default_off",
        "approve_one_bounded_local_activation_test",
    ]
    assert all(item["runtime_mutation_authorized_by_choice_display"] is False for item in choices)
    assert all("separate" in item["separate_artifact_required"] for item in choices)


def test_daytime_handoff_records_synthesis_without_authorizing_action() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    handoff = packet["daytime_handoff_packet"]

    assert handoff["handoff_recommendation"]["recommended_default"] == (
        "hold_no_runtime_mutation_until_explicit_human_answer"
    )
    assert {item["connection_id"] for item in handoff["synthesis_connections"]} == {
        "memory_system_to_acontext",
        "irc_coordination_to_claim_boundaries",
        "aas_portfolio_to_runtime_truth",
    }
    assert all(item["action_authorized"] == "daytime_handoff_only" for item in handoff["synthesis_connections"])


def test_daytime_handoff_preserves_stopped_project_firewall() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_daytime_handoff_keeps_runtime_and_external_surfaces_blocked() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    readiness = packet["readiness"]

    assert readiness["safe_for_daytime_operator_handoff"] is True
    for key in [
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
        "safe_for_design_only_wiring_selection",
        "safe_for_bounded_local_activation_test_selection",
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_adapter_enablement",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_bounded_activation_test_execution",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority",
        "safe_for_worker_copyable_doctrine",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        assert readiness[key] is False
    assert all(flag is False for flag in packet["access_flags"].values())


def test_daytime_handoff_preserves_blocked_claim_boundaries() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    safe = set(packet["claim_boundaries"]["safe_to_claim"])

    assert set(DAYTIME_HANDOFF_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "treats_handoff_as_approval",
        "runtime_adapter_registration",
        "runtime_adapter_enablement",
        "irc_session_manager_mutation",
        "cross_project_autorouting",
        "customer_copy_delivery_or_publication",
        "queue_launch_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "worker_copyable_doctrine",
        "stopped_project_integration",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_daytime_handoff_persists_no_secret_ids_payload_or_pii() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()
    serialized = json.dumps(packet).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret" + "_key_" + "hmac" not in serialized
    assert "secret" + "_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None
    assert "@" not in serialized
    assert "sanitized message" not in serialized
    assert "redacted_session_id" not in serialized
    assert "redacted_message_id" not in serialized


def test_daytime_handoff_stop_line_remains_fail_closed() -> None:
    packet = build_acontext_operator_activation_daytime_handoff_packet()

    assert packet["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_STOP_LINE
    assert "daytime handoff only" in packet["operator_guidance"]["stop_line"]
    assert "records no answer" in packet["operator_guidance"]["stop_line"]
    assert "records no approval" in packet["operator_guidance"]["stop_line"]
    assert "does not authorize design-only wiring" in packet["operator_guidance"]["stop_line"]
    assert packet["operator_guidance"]["not_customer_copy"] is True
    assert packet["operator_guidance"]["not_worker_instruction"] is True


def test_daytime_handoff_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_daytime_handoff_packet(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME
    loaded = load_acontext_operator_activation_daytime_handoff_packet(artifact_dir=tmp_path)
    assert loaded == build_acontext_operator_activation_daytime_handoff_packet(artifact_dir=tmp_path)


def test_daytime_handoff_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_read_only_review_packet())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source read-only review readiness promoted"):
        build_acontext_operator_activation_daytime_handoff_packet(read_only_review_packet=source)

    source = copy.deepcopy(build_acontext_operator_activation_read_only_review_packet())
    source["read_only_review_packet"]["operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="source read-only review promoted"):
        build_acontext_operator_activation_daytime_handoff_packet(read_only_review_packet=source)
