"""Tests for the AAS memory-to-Acontext readiness carry-forward card."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_memory_acontext_readiness_carry_forward_card import (
    AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME,
    AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM,
    AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SCHEMA,
    AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_VERDICT,
    CARRY_FORWARD_BLOCKED_CLAIMS,
    CARRY_FORWARD_STOP_LINE,
    build_aas_memory_acontext_readiness_carry_forward_card,
    load_aas_memory_acontext_readiness_carry_forward_card,
    write_aas_memory_acontext_readiness_carry_forward_card,
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
        if source.name == AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME).exists()


def test_memory_acontext_readiness_carry_forward_card_matches_fixture() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    fixture = json.loads(
        (PROOF_BLOCK_DIR / AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )

    assert card == fixture
    assert load_aas_memory_acontext_readiness_carry_forward_card() == card
    assert card["schema"] == AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SCHEMA
    assert card["status_verdict"] == AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_VERDICT
    assert ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM in card[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM in card[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_carry_forward_card_preserves_hold_and_records_no_approval() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    carry = card["readiness_carry_forward"]

    assert carry["current_decision"] == "hold_no_runtime_mutation"
    assert carry["effective_decision_after_card"] == "hold_no_runtime_mutation"
    assert carry["explicit_operator_answer_present"] is False
    assert carry["operator_approval_record_present"] is False
    assert carry["future_design_only_wiring_authorized_now"] is False
    assert carry["future_bounded_activation_test_authorized_now"] is False
    assert carry["adapter_registration_authorized_now"] is False
    assert carry["adapter_enablement_authorized_now"] is False
    assert carry["runtime_mutation_authorized_now"] is False


def test_carry_forward_card_names_disabled_adapter_field_contract_only() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    fields = {
        item["field"]: item for item in card["disabled_adapter_required_field_contract"]
    }

    assert set(fields) == {
        "proof_anchor_id",
        "coordination_session_id_alias",
        "review_packet_id",
        "compact_decision_id",
        "source_artifact_digests",
        "safe_to_claim",
        "do_not_claim_yet",
        "next_required_gate",
        "kill_switch_default",
    }
    assert all(item["required"] is True for item in fields.values())
    assert all(item["may_contain_private_context"] is False for item in fields.values())
    assert fields["kill_switch_default"]["source_class_allowed"] == "literal_false_or_disabled"


def test_carry_forward_card_preserves_field_survival_rules() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    rules = {item["rule_id"]: item for item in card["field_survival_rules"]}

    assert rules["safe_and_blocked_claims_survive_together"]["must_preserve"] == [
        "safe_to_claim",
        "do_not_claim_yet",
    ]
    assert "proof_anchor_id" in rules["invariant_ids_survive_without_raw_identifiers"][
        "must_preserve"
    ]
    assert rules["approval_absence_survives_retrieval"]["failure_mode"] == (
        "fail_closed_if_retrieved_memory_changes_hold_no_runtime_mutation"
    )


def test_carry_forward_card_future_gates_are_all_unpassed() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()

    assert [gate["step"] for gate in card["future_gate_order"]] == [
        "explicit_operator_answer_record",
        "separate_design_only_wiring_approval_record",
        "default_off_adapter_contract_tests",
        "bounded_local_activation_test_approval_record",
    ]
    assert all(gate["passed_now"] is False for gate in card["future_gate_order"])


def test_carry_forward_card_keeps_runtime_and_external_surfaces_blocked() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    readiness = card["readiness"]

    assert readiness["safe_for_internal_admin_field_contract_reference"] is True
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
    assert all(flag is False for flag in card["access_flags"].values())


def test_carry_forward_card_preserves_blocked_claim_boundaries() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    safe = set(card["claim_boundaries"]["safe_to_claim"])
    blocked = set(card["claim_boundaries"]["do_not_claim_yet"])

    assert set(CARRY_FORWARD_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "runtime_parity",
        "mutates_irc_session_manager",
        "cross_project_autorouting",
        "customer_copy_or_public_route",
        "worker_instruction_or_doctrine",
        "pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "stopped_projects",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_carry_forward_card_preserves_stopped_project_firewall() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    firewall = card["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_carry_forward_card_persists_no_secret_ids_payload_or_pii() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()
    serialized = json.dumps(card).lower()

    assert "bearer " + "sk" + "-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret" + "_key_" + "hmac" not in serialized
    assert "secret" + "_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None
    assert "@" not in serialized
    assert "redacted_session_id" not in serialized
    assert "redacted_message_id" not in serialized


def test_carry_forward_card_stop_line_remains_fail_closed() -> None:
    card = build_aas_memory_acontext_readiness_carry_forward_card()

    assert card["operator_guidance"]["stop_line"] == CARRY_FORWARD_STOP_LINE
    assert "readiness carry-forward only" in card["operator_guidance"]["stop_line"]
    assert "records no answer or approval" in card["operator_guidance"]["stop_line"]
    assert "does not authorize Acontext writes" in card["operator_guidance"]["stop_line"]
    assert card["operator_guidance"]["not_customer_copy"] is True
    assert card["operator_guidance"]["not_worker_instruction"] is True


def test_carry_forward_card_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_aas_memory_acontext_readiness_carry_forward_card(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME
    loaded = load_aas_memory_acontext_readiness_carry_forward_card(artifact_dir=tmp_path)
    assert loaded == build_aas_memory_acontext_readiness_carry_forward_card(
        artifact_dir=tmp_path
    )


def test_carry_forward_card_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_daytime_handoff_packet())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source daytime handoff readiness promoted"):
        build_aas_memory_acontext_readiness_carry_forward_card(
            daytime_handoff_packet=source
        )

    source = copy.deepcopy(build_acontext_operator_activation_daytime_handoff_packet())
    source["daytime_handoff_packet"]["operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="source daytime handoff promoted"):
        build_aas_memory_acontext_readiness_carry_forward_card(
            daytime_handoff_packet=source
        )


def test_carry_forward_card_loader_rejects_drift(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_aas_memory_acontext_readiness_carry_forward_card(artifact_dir=tmp_path)
    card = json.loads(path.read_text(encoding="utf-8"))
    card["readiness"]["runtime_parity_proven"] = True
    path.write_text(json.dumps(card), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_aas_memory_acontext_readiness_carry_forward_card(artifact_dir=tmp_path)
