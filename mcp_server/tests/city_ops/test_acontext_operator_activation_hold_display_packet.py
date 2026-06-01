"""Tests for the Acontext operator activation hold display packet."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_operator_activation_no_answer_work_queue import (
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM,
    build_acontext_operator_activation_no_answer_work_queue,
)
from mcp_server.city_ops.acontext_operator_activation_hold_display_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_STOP_LINE,
    HOLD_DISPLAY_PACKET_BLOCKED_CLAIMS,
    build_acontext_operator_activation_hold_display_packet,
    load_acontext_operator_activation_hold_display_packet,
    write_acontext_operator_activation_hold_display_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME).exists()


def test_hold_display_packet_matches_fixture() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert packet == fixture
    assert load_acontext_operator_activation_hold_display_packet() == packet
    assert packet["schema"] == ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCHEMA
    assert packet["status_verdict"] == "hold_display_packet_landed_no_answer_no_approval_default_hold_preserved"
    assert ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_hold_display_packet_is_internal_admin_only() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
    display = packet["hold_display_packet"]

    assert display["intended_audience"] == "internal_admin_operator_only"
    assert display["not_customer_copy"] is True
    assert display["not_worker_instruction"] is True
    assert display["current_decision"] == "hold_no_runtime_mutation"
    assert display["explicit_operator_answer_present"] is False
    assert display["operator_approval_record_present"] is False
    assert display["runtime_mutation_authorized"] is False
    assert display["bounded_activation_test_authorized"] is False


def test_hold_display_packet_shows_only_safe_status_lines() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
    status_lines = packet["hold_display_packet"]["safe_status_lines"]

    assert status_lines == [
        "Candidate: irc_session_manager_memory_sink",
        "Current decision: hold_no_runtime_mutation",
        "Operator answer present: false",
        "Approval record present: false",
        "Runtime mutation authorized: false",
        "Customer/public/worker exposure: none",
    ]
    assert packet["hold_display_packet"]["allowed_future_answer_values"] == [
        "hold_no_runtime_mutation",
        "approve_design_only_wiring_default_off",
        "approve_one_bounded_local_activation_test",
    ]


def test_hold_display_packet_preserves_allowed_no_answer_work_boundaries() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
    work_ids = {item["work_id"] for item in packet["displayed_allowed_no_answer_work"]}

    assert work_ids == {
        "display_internal_admin_hold_and_answer_schema",
        "validate_future_answer_shape_only",
        "continue_read_only_docs_or_fixture_review",
    }
    for item in packet["displayed_allowed_no_answer_work"]:
        assert item["records_approval"] is False
        assert item["runtime_mutation"] is False
        assert item["customer_or_worker_exposure"] == "none"


def test_hold_display_packet_preserves_stopped_project_firewall() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_hold_display_packet_keeps_runtime_and_external_surfaces_blocked() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
    readiness = packet["readiness"]

    assert readiness["safe_for_internal_admin_hold_display"] is True
    for key in [
        "safe_for_future_answer_validation",
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
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


def test_hold_display_packet_preserves_blocked_claim_boundaries() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    safe = set(packet["claim_boundaries"]["safe_to_claim"])

    assert set(HOLD_DISPLAY_PACKET_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "validates_future_answer",
        "runtime_adapter_registration",
        "runtime_adapter_enablement",
        "irc_session_manager_mutation",
        "bounded_activation_test",
        "cross_project_autorouting",
        "customer_copy_delivery_or_publication",
        "queue_launch_or_dispatch",
        "erc8004_reputation",
        "worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "worker_copyable_doctrine",
        "stopped_project_integration",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_hold_display_packet_persists_no_secret_ids_payload_or_pii() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()
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


def test_hold_display_packet_stop_line_remains_fail_closed() -> None:
    packet = build_acontext_operator_activation_hold_display_packet()

    assert packet["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_STOP_LINE
    assert "records no answer" in packet["operator_guidance"]["stop_line"]
    assert "does not validate a future answer" in packet["operator_guidance"]["stop_line"]
    assert "does not authorize runtime adapter registration" in packet["operator_guidance"]["stop_line"]
    assert packet["operator_guidance"]["not_customer_copy"] is True
    assert packet["operator_guidance"]["not_worker_instruction"] is True


def test_hold_display_packet_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_hold_display_packet(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME
    loaded = load_acontext_operator_activation_hold_display_packet(artifact_dir=tmp_path)
    assert loaded == build_acontext_operator_activation_hold_display_packet(artifact_dir=tmp_path)


def test_hold_display_packet_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_no_answer_work_queue())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source no-answer readiness promoted"):
        build_acontext_operator_activation_hold_display_packet(no_answer_work_queue=source)

    source = copy.deepcopy(build_acontext_operator_activation_no_answer_work_queue())
    source["no_answer_runtime_posture"]["operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="source no-answer posture promoted"):
        build_acontext_operator_activation_hold_display_packet(no_answer_work_queue=source)
