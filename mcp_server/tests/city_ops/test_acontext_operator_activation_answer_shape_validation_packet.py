"""Tests for the Acontext operator activation answer-shape validation packet."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_operator_activation_answer_schema_gate import (
    ALLOWED_OPERATOR_ANSWER_VALUES,
)
from mcp_server.city_ops.acontext_operator_activation_hold_display_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM,
    build_acontext_operator_activation_hold_display_packet,
)
from mcp_server.city_ops.acontext_operator_activation_answer_shape_validation_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_STOP_LINE,
    ANSWER_SHAPE_VALIDATION_PACKET_BLOCKED_CLAIMS,
    build_acontext_operator_activation_answer_shape_validation_packet,
    load_acontext_operator_activation_answer_shape_validation_packet,
    write_acontext_operator_activation_answer_shape_validation_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME).exists()


def test_answer_shape_validation_packet_matches_fixture() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert packet == fixture
    assert load_acontext_operator_activation_answer_shape_validation_packet() == packet
    assert packet["schema"] == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCHEMA
    assert packet["status_verdict"] == "answer_shape_validation_packet_landed_no_answer_no_approval_default_hold_preserved"
    assert ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_answer_shape_validation_packet_is_internal_admin_only() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
    validation = packet["answer_shape_validation_packet"]

    assert validation["intended_audience"] == "internal_admin_operator_only"
    assert validation["not_customer_copy"] is True
    assert validation["not_worker_instruction"] is True
    assert validation["current_decision"] == "hold_no_runtime_mutation"
    assert validation["explicit_operator_answer_present"] is False
    assert validation["operator_approval_record_present"] is False
    assert validation["shape_validity_is_not_approval"] is True
    assert validation["effective_decision_after_shape_validation"] == "hold_no_runtime_mutation"
    assert validation["runtime_mutation_authorized"] is False
    assert validation["bounded_activation_test_authorized"] is False


def test_answer_shape_validation_accepts_only_allowed_shapes_not_approval() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
    validation = packet["answer_shape_validation_packet"]

    assert validation["allowed_answer_values"] == ALLOWED_OPERATOR_ANSWER_VALUES
    assert [item["answer_value"] for item in validation["valid_shape_examples"]] == ALLOWED_OPERATOR_ANSWER_VALUES
    for item in validation["valid_shape_examples"]:
        assert item["validation_status"] == "shape_valid_not_approval"
        assert item["preserve_all_blocked_claims"] is True
        assert item["records_customer_or_public_approval"] is False
        assert item["authorizes_runtime_adapter_registration"] is False
        assert item["authorizes_runtime_adapter_enablement"] is False
        assert item["authorizes_irc_session_manager_mutation"] is False
        assert item["authorizes_cross_project_autorouting"] is False
        assert item["authorizes_queue_launch_or_dispatch"] is False
        assert item["authorizes_reputation_or_worker_skill_dna"] is False
        assert item["authorizes_payment_or_production_claim"] is False
        assert item["allows_exact_gps_or_raw_metadata"] is False
        assert item["releases_private_context"] is False
        assert item["creates_worker_copyable_doctrine"] is False
        assert item["integrates_stopped_projects"] is False


def test_answer_shape_validation_rejects_promoted_or_bad_examples() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
    invalid_examples = packet["answer_shape_validation_packet"]["invalid_shape_examples"]

    assert {item["case_id"] for item in invalid_examples} == {
        "reject_unrecognized_answer_value",
        "reject_missing_non_secret_operator_reference",
        "reject_any_runtime_promotion_flag",
    }
    assert all(item["validation_status"] == "rejected" for item in invalid_examples)
    assert any(item["rejection_reason"] == "answer_value_not_in_allowed_set" for item in invalid_examples)
    assert any("promotion_flags" in item["rejection_reason"] for item in invalid_examples)


def test_answer_shape_validation_preserves_stopped_project_firewall() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_answer_shape_validation_keeps_runtime_and_external_surfaces_blocked() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
    readiness = packet["readiness"]

    assert readiness["safe_for_future_answer_shape_validation"] is True
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


def test_answer_shape_validation_preserves_blocked_claim_boundaries() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    safe = set(packet["claim_boundaries"]["safe_to_claim"])

    assert set(ANSWER_SHAPE_VALIDATION_PACKET_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "accepts_shape_validity_as_approval",
        "changes_effective_decision",
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


def test_answer_shape_validation_persists_no_secret_ids_payload_or_pii() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()
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


def test_answer_shape_validation_stop_line_remains_fail_closed() -> None:
    packet = build_acontext_operator_activation_answer_shape_validation_packet()

    assert packet["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_STOP_LINE
    assert "validates only future operator answer shapes" in packet["operator_guidance"]["stop_line"]
    assert "records no answer" in packet["operator_guidance"]["stop_line"]
    assert "records no approval" in packet["operator_guidance"]["stop_line"]
    assert "does not authorize runtime adapter registration" in packet["operator_guidance"]["stop_line"]
    assert packet["operator_guidance"]["not_customer_copy"] is True
    assert packet["operator_guidance"]["not_worker_instruction"] is True


def test_answer_shape_validation_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_answer_shape_validation_packet(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME
    loaded = load_acontext_operator_activation_answer_shape_validation_packet(artifact_dir=tmp_path)
    assert loaded == build_acontext_operator_activation_answer_shape_validation_packet(artifact_dir=tmp_path)


def test_answer_shape_validation_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_hold_display_packet())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source hold display readiness promoted"):
        build_acontext_operator_activation_answer_shape_validation_packet(hold_display_packet=source)

    source = copy.deepcopy(build_acontext_operator_activation_hold_display_packet())
    source["hold_display_packet"]["operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="source hold display promoted"):
        build_acontext_operator_activation_answer_shape_validation_packet(hold_display_packet=source)
