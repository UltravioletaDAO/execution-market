"""Tests for the Acontext operator activation answer schema gate."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_activation_hold_status_card import (
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME,
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM,
    build_acontext_activation_hold_status_card,
)
from mcp_server.city_ops.acontext_operator_activation_answer_schema_gate import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_STOP_LINE,
    ALLOWED_OPERATOR_ANSWER_VALUES,
    ANSWER_SCHEMA_BLOCKED_CLAIMS,
    build_acontext_operator_activation_answer_schema_gate,
    load_acontext_operator_activation_answer_schema_gate,
    validate_acontext_operator_activation_answer_shape,
    write_acontext_operator_activation_answer_schema_gate,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME).exists()


def _source_digest() -> str:
    gate = build_acontext_operator_activation_answer_schema_gate()
    return gate["source_artifacts"]["activation_hold_status_card"]["file_digest_sha256"]


def _base_answer(value: str) -> dict[str, object]:
    return {
        "answer_value": value,
        "non_secret_operator_reference": "operator.answer.alpha",
        "source_hold_status_card_file_digest_sha256": _source_digest(),
        "preserve_all_blocked_claims": True,
        "records_customer_or_public_approval": False,
        "authorizes_customer_or_public_delivery": False,
        "authorizes_runtime_adapter_registration": False,
        "authorizes_runtime_adapter_enablement": False,
        "authorizes_irc_session_manager_mutation": False,
        "authorizes_cross_project_autorouting": False,
        "authorizes_queue_launch_or_dispatch": False,
        "authorizes_reputation_or_worker_skill_dna": False,
        "authorizes_payment_or_production_claim": False,
        "allows_exact_gps_or_raw_metadata": False,
        "releases_private_context": False,
        "grants_domain_or_emergency_authority": False,
        "creates_worker_copyable_doctrine": False,
        "integrates_stopped_projects": False,
        "default_off_confirmed": False,
        "kill_switch_required": False,
        "rollback_plan_required": False,
        "cleanup_quarantine_required": False,
        "local_only_one_attempt_limit": False,
        "sanitized_candidate_fixture_digest_sha256": None,
    }


def test_answer_schema_gate_matches_fixture() -> None:
    gate = build_acontext_operator_activation_answer_schema_gate()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert gate == fixture
    assert load_acontext_operator_activation_answer_schema_gate() == gate
    assert gate["schema"] == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCHEMA
    assert gate["status_verdict"] == (
        "answer_schema_gate_landed_no_operator_answer_recorded_default_hold_preserved"
    )
    assert ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM in gate["claim_boundaries"][
        "safe_to_claim"
    ]
    assert ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM in gate[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_answer_schema_gate_records_no_answer_and_preserves_default_hold() -> None:
    gate = build_acontext_operator_activation_answer_schema_gate()
    state = gate["current_answer_state"]

    assert gate["activation_candidate"]["candidate_id"] == "irc_session_manager_memory_sink"
    assert state["explicit_operator_answer_present"] is False
    assert state["operator_answer_value"] is None
    assert state["operator_approval_record_present"] is False
    assert state["answer_schema_validated"] is False
    assert state["effective_decision"] == "hold_no_runtime_mutation"
    assert state["this_gate_is_not_an_approval_record"] is True


def test_answer_schema_gate_defines_only_three_future_answers() -> None:
    gate = build_acontext_operator_activation_answer_schema_gate()
    contract = gate["answer_intake_contract"]

    assert contract["allowed_answer_values"] == ALLOWED_OPERATOR_ANSWER_VALUES
    assert contract["hold_no_runtime_mutation"]["allows_runtime_mutation"] is False
    assert contract["approve_design_only_wiring_default_off"][
        "requires_separate_approval_record"
    ] is True
    assert contract["approve_design_only_wiring_default_off"][
        "allows_live_session_manager_mutation_from_this_gate"
    ] is False
    assert contract["approve_one_bounded_local_activation_test"][
        "requires_sanitized_candidate_fixture_digest"
    ] is True
    assert contract["approve_one_bounded_local_activation_test"][
        "allows_customer_public_dispatch_reputation_payment_or_production_from_this_gate"
    ] is False


def test_answer_schema_gate_keeps_runtime_and_external_surfaces_blocked() -> None:
    gate = build_acontext_operator_activation_answer_schema_gate()
    readiness = gate["readiness"]

    assert readiness["safe_for_internal_admin_answer_intake_schema_display"] is True
    for key in [
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
    assert all(flag is False for flag in gate["access_flags"].values())


def test_answer_schema_gate_preserves_blocked_claim_boundaries() -> None:
    gate = build_acontext_operator_activation_answer_schema_gate()
    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])
    safe = set(gate["claim_boundaries"]["safe_to_claim"])

    assert set(ANSWER_SCHEMA_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "runtime_adapter_registration",
        "runtime_adapter_enablement",
        "irc_session_manager_mutation",
        "bounded_activation_test_execution",
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


def test_answer_schema_gate_persists_no_secret_ids_payload_or_pii() -> None:
    gate = build_acontext_operator_activation_answer_schema_gate()
    serialized = json.dumps(gate).lower()

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


def test_answer_schema_gate_stop_line_remains_fail_closed() -> None:
    gate = build_acontext_operator_activation_answer_schema_gate()

    assert gate["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_STOP_LINE
    assert "records no answer" in gate["operator_guidance"]["stop_line"]
    assert "does not authorize runtime adapter registration" in gate["operator_guidance"]["stop_line"]
    assert gate["operator_guidance"]["not_customer_copy"] is True
    assert gate["operator_guidance"]["not_worker_instruction"] is True
    assert gate["operator_guidance"]["next_required_gate"] == (
        "separate_explicit_operator_answer_record_before_any_runtime_mutation_or_activation_test"
    )


def test_answer_schema_gate_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_answer_schema_gate(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME
    loaded = load_acontext_operator_activation_answer_schema_gate(artifact_dir=tmp_path)
    assert loaded == build_acontext_operator_activation_answer_schema_gate(artifact_dir=tmp_path)


def test_answer_schema_gate_rejects_promoted_hold_source() -> None:
    source = copy.deepcopy(build_acontext_activation_hold_status_card())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source hold readiness promoted"):
        build_acontext_operator_activation_answer_schema_gate(hold_status_card=source)

    source = copy.deepcopy(build_acontext_activation_hold_status_card())
    source["operator_answer_state"]["explicit_operator_answer_present"] = True

    with pytest.raises(CityOpsContractError, match="hold source records answer"):
        build_acontext_operator_activation_answer_schema_gate(hold_status_card=source)


def test_answer_shape_validator_accepts_fail_closed_hold_answer() -> None:
    result = validate_acontext_operator_activation_answer_shape(
        _base_answer("hold_no_runtime_mutation"),
        expected_source_file_digest_sha256=_source_digest(),
    )

    assert result == {
        "valid_shape": True,
        "answer_value": "hold_no_runtime_mutation",
        "records_approval": False,
        "authorizes_runtime_mutation": False,
        "requires_separate_approval_artifact": False,
        "effective_decision_until_separate_artifact": "hold_no_runtime_mutation",
    }


def test_answer_shape_validator_accepts_design_only_shape_without_authorizing_runtime() -> None:
    answer = _base_answer("approve_design_only_wiring_default_off")
    answer.update(
        {
            "default_off_confirmed": True,
            "kill_switch_required": True,
            "rollback_plan_required": True,
            "cleanup_quarantine_required": True,
        }
    )

    result = validate_acontext_operator_activation_answer_shape(
        answer,
        expected_source_file_digest_sha256=_source_digest(),
    )

    assert result["answer_value"] == "approve_design_only_wiring_default_off"
    assert result["records_approval"] is False
    assert result["authorizes_runtime_mutation"] is False
    assert result["requires_separate_approval_artifact"] is True


def test_answer_shape_validator_accepts_bounded_local_activation_shape_without_authorizing_runtime() -> None:
    answer = _base_answer("approve_one_bounded_local_activation_test")
    answer.update(
        {
            "default_off_confirmed": True,
            "kill_switch_required": True,
            "rollback_plan_required": True,
            "cleanup_quarantine_required": True,
            "local_only_one_attempt_limit": True,
            "sanitized_candidate_fixture_digest_sha256": "a" * 64,
        }
    )

    result = validate_acontext_operator_activation_answer_shape(
        answer,
        expected_source_file_digest_sha256=_source_digest(),
    )

    assert result["answer_value"] == "approve_one_bounded_local_activation_test"
    assert result["records_approval"] is False
    assert result["authorizes_runtime_mutation"] is False
    assert result["requires_separate_approval_artifact"] is True


def test_answer_shape_validator_rejects_ambiguous_promoted_or_sensitive_answers() -> None:
    with pytest.raises(CityOpsContractError, match="value not allowed"):
        validate_acontext_operator_activation_answer_shape(
            {**_base_answer("approve_everything"), "answer_value": "approve_everything"},
            expected_source_file_digest_sha256=_source_digest(),
        )

    promoted = _base_answer("hold_no_runtime_mutation")
    promoted["authorizes_queue_launch_or_dispatch"] = True
    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        validate_acontext_operator_activation_answer_shape(
            promoted,
            expected_source_file_digest_sha256=_source_digest(),
        )

    wrong_digest = _base_answer("hold_no_runtime_mutation")
    wrong_digest["source_hold_status_card_file_digest_sha256"] = "b" * 64
    with pytest.raises(CityOpsContractError, match="source digest mismatch"):
        validate_acontext_operator_activation_answer_shape(
            wrong_digest,
            expected_source_file_digest_sha256=_source_digest(),
        )

    pii = _base_answer("hold_no_runtime_mutation")
    pii["non_secret_operator_reference"] = "operator@example.com"
    with pytest.raises(CityOpsContractError, match="secret, identifier, or PII"):
        validate_acontext_operator_activation_answer_shape(
            pii,
            expected_source_file_digest_sha256=_source_digest(),
        )

    missing_fixture = _base_answer("approve_one_bounded_local_activation_test")
    missing_fixture.update(
        {
            "default_off_confirmed": True,
            "kill_switch_required": True,
            "rollback_plan_required": True,
            "cleanup_quarantine_required": True,
            "local_only_one_attempt_limit": True,
        }
    )
    with pytest.raises(CityOpsContractError, match="missing sanitized fixture digest"):
        validate_acontext_operator_activation_answer_shape(
            missing_fixture,
            expected_source_file_digest_sha256=_source_digest(),
        )
