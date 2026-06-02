"""Tests for the Acontext operator activation answer-record dry-run validator."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_operator_activation_answer_record_dry_run_validator import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_STOP_LINE,
    ANSWER_RECORD_DRY_RUN_VALIDATOR_BLOCKED_CLAIMS,
    build_acontext_operator_activation_answer_record_dry_run_validator,
    load_acontext_operator_activation_answer_record_dry_run_validator,
    write_acontext_operator_activation_answer_record_dry_run_validator,
)
from mcp_server.city_ops.acontext_operator_activation_answer_schema_gate import (
    ALLOWED_OPERATOR_ANSWER_VALUES,
)
from mcp_server.city_ops.acontext_operator_activation_daytime_handoff_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
    build_acontext_operator_activation_daytime_handoff_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME).exists()


def test_answer_record_dry_run_validator_matches_fixture() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert packet == fixture
    assert load_acontext_operator_activation_answer_record_dry_run_validator() == packet
    assert packet["schema"] == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCHEMA
    assert packet["status_verdict"] == "answer_record_dry_run_validator_landed_no_explicit_answer_blockers_fail_closed"
    assert ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_answer_record_dry_run_validator_is_internal_admin_only_not_answer_or_approval() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    validator = packet["answer_record_dry_run_validator"]

    assert validator["intended_audience"] == "internal_admin_operator_only"
    assert validator["not_customer_copy"] is True
    assert validator["not_worker_instruction"] is True
    assert validator["dry_run_only"] is True
    assert validator["validator_landed"] is True
    assert validator["validator_is_not_answer_record"] is True
    assert validator["validator_is_not_approval"] is True
    assert validator["current_decision"] == "hold_no_runtime_mutation"
    assert validator["effective_decision_after_dry_run"] == "hold_no_runtime_mutation"
    assert validator["explicit_operator_answer_present"] is False
    assert validator["operator_approval_record_present"] is False
    assert validator["runtime_mutation_authorized"] is False
    assert validator["bounded_activation_test_authorized"] is False


def test_answer_record_dry_run_validates_only_allowed_hypothetical_values() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    validator = packet["answer_record_dry_run_validator"]

    assert validator["allowed_answer_values"] == ALLOWED_OPERATOR_ANSWER_VALUES
    assert [item["answer_value"] for item in validator["valid_hypothetical_answer_records"]] == (
        ALLOWED_OPERATOR_ANSWER_VALUES
    )
    for item in validator["valid_hypothetical_answer_records"]:
        assert item["validation_status"] == "hypothetical_record_valid_not_answer_not_approval"
        assert item["answer_is_explicit_human_statement"] is True
        assert item["dry_run_only"] is True
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


def test_answer_record_dry_run_rejects_no_answer_and_promotions_fail_closed() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    rejected = packet["answer_record_dry_run_validator"]["rejected_hypothetical_answer_records"]

    assert {item["case_id"] for item in rejected} == {
        "reject_no_explicit_answer_record_present",
        "reject_unrecognized_answer_value",
        "reject_source_digest_mismatch",
        "reject_any_runtime_or_public_promotion_flag",
    }
    assert all(item["validation_status"] == "rejected_fail_closed" for item in rejected)
    assert any(item["rejection_reason"] == "missing_explicit_operator_answer_record" for item in rejected)
    assert any(item["rejection_reason"] == "answer_value_not_in_allowed_set" for item in rejected)
    assert any("digest_mismatch" in item["rejection_reason"] for item in rejected)
    assert any("promotion_flags" in item["rejection_reason"] for item in rejected)


def test_answer_record_dry_run_emits_no_answer_blockers() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    validator = packet["answer_record_dry_run_validator"]

    assert validator["no_explicit_answer_fail_closed_blockers"] == [
        "explicit_operator_answer_record_absent",
        "operator_approval_record_absent",
        "do_not_select_design_only_wiring",
        "do_not_select_bounded_local_activation_test",
        "do_not_register_or_enable_runtime_adapter",
        "do_not_mutate_irc_session_manager",
        "do_not_expose_customer_public_worker_or_catalog_surface",
    ]
    assert validator["validator_recommendation"]["recommended_default"] == (
        "hold_no_runtime_mutation_until_real_explicit_human_answer_record_exists"
    )


def test_answer_record_dry_run_preserves_stopped_project_firewall() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_answer_record_dry_run_keeps_runtime_and_external_surfaces_blocked() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    readiness = packet["readiness"]

    assert readiness["safe_for_hypothetical_answer_record_dry_run_validation"] is True
    assert readiness["no_explicit_answer_blockers_emitted"] is True
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


def test_answer_record_dry_run_preserves_blocked_claim_boundaries() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    safe = set(packet["claim_boundaries"]["safe_to_claim"])

    assert set(ANSWER_RECORD_DRY_RUN_VALIDATOR_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "treats_dry_run_as_answer",
        "treats_validation_as_approval",
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


def test_answer_record_dry_run_persists_no_secret_ids_payload_or_pii() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()
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


def test_answer_record_dry_run_stop_line_remains_fail_closed() -> None:
    packet = build_acontext_operator_activation_answer_record_dry_run_validator()

    assert packet["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_STOP_LINE
    assert "hypothetical answer-record candidates" in packet["operator_guidance"]["stop_line"]
    assert "records no real operator answer" in packet["operator_guidance"]["stop_line"]
    assert "records no approval" in packet["operator_guidance"]["stop_line"]
    assert "treats no-answer as fail-closed" in packet["operator_guidance"]["stop_line"]
    assert packet["operator_guidance"]["not_customer_copy"] is True
    assert packet["operator_guidance"]["not_worker_instruction"] is True


def test_answer_record_dry_run_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_answer_record_dry_run_validator(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME
    loaded = load_acontext_operator_activation_answer_record_dry_run_validator(artifact_dir=tmp_path)
    assert loaded == build_acontext_operator_activation_answer_record_dry_run_validator(
        artifact_dir=tmp_path
    )


def test_answer_record_dry_run_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_daytime_handoff_packet())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source daytime handoff readiness promoted"):
        build_acontext_operator_activation_answer_record_dry_run_validator(
            daytime_handoff_packet=source
        )

    source = copy.deepcopy(build_acontext_operator_activation_daytime_handoff_packet())
    source["daytime_handoff_packet"]["operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="source daytime handoff promoted"):
        build_acontext_operator_activation_answer_record_dry_run_validator(
            daytime_handoff_packet=source
        )
