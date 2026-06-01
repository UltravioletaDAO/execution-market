"""Tests for the Acontext operator activation read-only review packet."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_operator_activation_answer_shape_validation_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM,
    build_acontext_operator_activation_answer_shape_validation_packet,
)
from mcp_server.city_ops.acontext_operator_activation_read_only_review_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_STOP_LINE,
    READ_ONLY_REVIEW_PACKET_BLOCKED_CLAIMS,
    build_acontext_operator_activation_read_only_review_packet,
    load_acontext_operator_activation_read_only_review_packet,
    write_acontext_operator_activation_read_only_review_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME).exists()


def test_read_only_review_packet_matches_fixture() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert packet == fixture
    assert load_acontext_operator_activation_read_only_review_packet() == packet
    assert packet["schema"] == ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCHEMA
    assert packet["status_verdict"] == "read_only_review_packet_landed_no_answer_no_approval_default_hold_preserved"
    assert ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_read_only_review_packet_is_internal_admin_only() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
    review = packet["read_only_review_packet"]

    assert review["intended_audience"] == "internal_admin_operator_only"
    assert review["not_customer_copy"] is True
    assert review["not_worker_instruction"] is True
    assert review["current_decision"] == "hold_no_runtime_mutation"
    assert review["explicit_operator_answer_present"] is False
    assert review["operator_approval_record_present"] is False
    assert review["review_is_not_approval"] is True
    assert review["effective_decision_after_review"] == "hold_no_runtime_mutation"
    assert review["runtime_mutation_authorized"] is False
    assert review["bounded_activation_test_authorized"] is False


def test_read_only_review_allows_only_digest_and_boundary_review() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
    review = packet["read_only_review_packet"]

    assert [item["mode"] for item in review["review_inputs"]] == [
        "digest_and_boundary_review_only",
        "docs_boundary_review_only",
    ]
    for item in review["review_inputs"]:
        assert item["payload_persisted"] is False
        assert item["raw_context_persisted"] is False
    assert review["review_invariants"] == [
        "source_digests_before_payloads",
        "operator_answers_before_runtime_mutation",
        "approval_records_before_activation_tests",
        "sanitized_fixtures_before_customer_surfaces",
        "blocked_claims_before_product_copy",
        "stopped_project_firewall_before_cross_project_reuse",
    ]


def test_read_only_review_records_pattern_findings_without_authorizing_action() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
    findings = packet["read_only_review_packet"]["pattern_recognition_findings"]

    assert {item["finding_id"] for item in findings} == {
        "memory_promotion_requires_explicit_answer_chain",
        "coordination_value_comes_from_claim_boundaries",
        "aas_multiplier_is_repeatable_low_authority_packaging",
    }
    assert all(item["action_authorized"] == "read_only_review_only" for item in findings)
    assert any("Durable agent memory" in item["safe_observation"] for item in findings)
    assert any("safe-to-claim" in item["safe_observation"] for item in findings)


def test_read_only_review_preserves_stopped_project_firewall() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_read_only_review_keeps_runtime_and_external_surfaces_blocked() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
    readiness = packet["readiness"]

    assert readiness["safe_for_read_only_docs_fixture_review"] is True
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


def test_read_only_review_preserves_blocked_claim_boundaries() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    safe = set(packet["claim_boundaries"]["safe_to_claim"])

    assert set(READ_ONLY_REVIEW_PACKET_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "treats_review_as_approval",
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


def test_read_only_review_persists_no_secret_ids_payload_or_pii() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()
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


def test_read_only_review_stop_line_remains_fail_closed() -> None:
    packet = build_acontext_operator_activation_read_only_review_packet()

    assert packet["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_STOP_LINE
    assert "read-only docs/fixture review only" in packet["operator_guidance"]["stop_line"]
    assert "records no answer" in packet["operator_guidance"]["stop_line"]
    assert "records no approval" in packet["operator_guidance"]["stop_line"]
    assert "does not authorize runtime adapter registration" in packet["operator_guidance"]["stop_line"]
    assert packet["operator_guidance"]["not_customer_copy"] is True
    assert packet["operator_guidance"]["not_worker_instruction"] is True


def test_read_only_review_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_read_only_review_packet(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME
    loaded = load_acontext_operator_activation_read_only_review_packet(artifact_dir=tmp_path)
    assert loaded == build_acontext_operator_activation_read_only_review_packet(artifact_dir=tmp_path)


def test_read_only_review_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_answer_shape_validation_packet())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source answer shape readiness promoted"):
        build_acontext_operator_activation_read_only_review_packet(answer_shape_validation_packet=source)

    source = copy.deepcopy(build_acontext_operator_activation_answer_shape_validation_packet())
    source["answer_shape_validation_packet"]["operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="source answer shape promoted"):
        build_acontext_operator_activation_read_only_review_packet(answer_shape_validation_packet=source)
