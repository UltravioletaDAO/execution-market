"""Tests for the Acontext operator activation no-answer pause ledger."""

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
    build_acontext_operator_activation_answer_record_dry_run_validator,
)
from mcp_server.city_ops.acontext_operator_activation_no_answer_pause_ledger import (
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_STOP_LINE,
    NO_ANSWER_PAUSE_LEDGER_BLOCKED_CLAIMS,
    build_acontext_operator_activation_no_answer_pause_ledger,
    load_acontext_operator_activation_no_answer_pause_ledger,
    write_acontext_operator_activation_no_answer_pause_ledger,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME).exists()


def test_no_answer_pause_ledger_matches_fixture() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert packet == fixture
    assert load_acontext_operator_activation_no_answer_pause_ledger() == packet
    assert packet["schema"] == ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCHEMA
    assert packet["status_verdict"] == "no_answer_pause_ledger_landed_hold_no_runtime_mutation_fail_closed"
    assert ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_no_answer_pause_ledger_is_internal_admin_only_not_answer_or_approval() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()
    ledger = packet["no_answer_pause_ledger"]

    assert ledger["intended_audience"] == "internal_admin_operator_only"
    assert ledger["not_customer_copy"] is True
    assert ledger["not_worker_instruction"] is True
    assert ledger["ledger_landed"] is True
    assert ledger["ledger_is_not_answer_record"] is True
    assert ledger["ledger_is_not_approval"] is True
    assert ledger["source_dry_run_validator_validated"] is True
    assert ledger["current_decision"] == "hold_no_runtime_mutation"
    assert ledger["effective_decision_after_pause"] == "hold_no_runtime_mutation"
    assert ledger["explicit_operator_answer_present"] is False
    assert ledger["operator_approval_record_present"] is False
    assert ledger["runtime_mutation_authorized"] is False
    assert ledger["bounded_activation_test_authorized"] is False


def test_no_answer_pause_ledger_entries_are_non_promoting() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()
    ledger = packet["no_answer_pause_ledger"]

    assert [entry["entry_id"] for entry in ledger["pause_entries"]] == [
        "source_dry_run_validator_confirmed",
        "no_explicit_human_answer_present",
        "fail_closed_next_action",
    ]
    assert ledger["pause_reason"] == "no_real_explicit_operator_answer_record_exists"
    for entry in ledger["pause_entries"]:
        assert entry["records_operator_answer"] is False
        assert entry["records_operator_approval"] is False
        assert entry["changes_effective_decision"] is False


def test_no_answer_pause_ledger_carries_fail_closed_blockers_forward() -> None:
    source = build_acontext_operator_activation_answer_record_dry_run_validator()
    packet = build_acontext_operator_activation_no_answer_pause_ledger(dry_run_validator=source)
    ledger = packet["no_answer_pause_ledger"]

    assert ledger["fail_closed_blockers_carried_forward"] == source[
        "answer_record_dry_run_validator"
    ]["no_explicit_answer_fail_closed_blockers"]
    assert ledger["eligible_future_actions_without_new_human_answer"] == [
        "keep_hold_no_runtime_mutation",
        "display_internal_admin_pause_state",
        "continue_read_only_docs_or_fixture_review_only",
    ]
    assert ledger["only_unlocking_input"] == (
        "separate_real_explicit_operator_answer_record_with_non_secret_reference"
    )
    assert "do_not_treat_pause_ledger_as_answer" in ledger["forbidden_shortcuts"]


def test_no_answer_pause_ledger_preserves_stopped_project_firewall() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_no_answer_pause_ledger_keeps_runtime_and_external_surfaces_blocked() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()
    readiness = packet["readiness"]

    assert readiness["no_answer_pause_ledger_landed"] is True
    assert readiness["safe_for_internal_admin_pause_display"] is True
    assert readiness["safe_for_read_only_docs_or_fixture_review"] is True
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


def test_no_answer_pause_ledger_preserves_blocked_claim_boundaries() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    safe = set(packet["claim_boundaries"]["safe_to_claim"])

    assert set(NO_ANSWER_PAUSE_LEDGER_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "treats_pause_as_answer",
        "treats_pause_as_approval",
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


def test_no_answer_pause_ledger_persists_no_secret_ids_payload_or_pii() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()
    serialized = json.dumps(packet).lower()

    assert "bear" + "er " + "sk" + "-ac-" not in serialized
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


def test_no_answer_pause_ledger_stop_line_remains_fail_closed() -> None:
    packet = build_acontext_operator_activation_no_answer_pause_ledger()

    assert packet["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_STOP_LINE
    assert "records no operator answer" in packet["operator_guidance"]["stop_line"]
    assert "records no approval" in packet["operator_guidance"]["stop_line"]
    assert "hold_no_runtime_mutation" in packet["operator_guidance"]["stop_line"]
    assert packet["operator_guidance"]["not_customer_copy"] is True
    assert packet["operator_guidance"]["not_worker_instruction"] is True


def test_no_answer_pause_ledger_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_no_answer_pause_ledger(artifact_dir=tmp_path)
    assert path.name == ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME
    assert json.loads(path.read_text(encoding="utf-8")) == load_acontext_operator_activation_no_answer_pause_ledger(
        artifact_dir=tmp_path
    )


def test_no_answer_pause_ledger_rejects_promoted_source_dry_run_validator() -> None:
    source = build_acontext_operator_activation_answer_record_dry_run_validator()
    promoted = copy.deepcopy(source)
    promoted["answer_record_dry_run_validator"]["explicit_operator_answer_present"] = True

    with pytest.raises(CityOpsContractError, match="source dry-run validator promoted"):
        build_acontext_operator_activation_no_answer_pause_ledger(dry_run_validator=promoted)


def test_no_answer_pause_ledger_load_rejects_promoted_fixture_readiness(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_operator_activation_no_answer_pause_ledger(artifact_dir=tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["readiness"]["operator_activation_approved"] = True
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_operator_activation_no_answer_pause_ledger(artifact_dir=tmp_path)
