"""Tests for the AAS session-manager no-mutation adapter field map."""

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
    build_aas_memory_acontext_readiness_carry_forward_card,
)
from mcp_server.city_ops.aas_session_manager_no_mutation_adapter_field_map import (
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME,
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM,
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SCHEMA,
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_VERDICT,
    SESSION_MANAGER_FIELD_MAP_BLOCKED_CLAIMS,
    SESSION_MANAGER_FIELD_MAP_STOP_LINE,
    build_aas_session_manager_no_mutation_adapter_field_map,
    load_aas_session_manager_no_mutation_adapter_field_map,
    write_aas_session_manager_no_mutation_adapter_field_map,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME).exists()


def test_session_manager_field_map_matches_fixture() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    fixture = json.loads(
        (PROOF_BLOCK_DIR / AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME).read_text(
            encoding="utf-8"
        )
    )

    assert field_map == fixture
    assert load_aas_session_manager_no_mutation_adapter_field_map() == field_map
    assert field_map["schema"] == AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SCHEMA
    assert field_map["status_verdict"] == AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_VERDICT
    assert AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM in field_map[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM in field_map[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_session_manager_field_map_preserves_hold_and_records_no_approval() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    mapped = field_map["no_mutation_adapter_field_map"]

    assert mapped["current_decision"] == "hold_no_runtime_mutation"
    assert mapped["effective_decision_after_field_map"] == "hold_no_runtime_mutation"
    assert mapped["explicit_operator_answer_present"] is False
    assert mapped["operator_approval_record_present"] is False
    assert mapped["design_only_wiring_authorized_now"] is False
    assert mapped["bounded_activation_test_authorized_now"] is False
    assert mapped["adapter_registration_authorized_now"] is False
    assert mapped["adapter_enablement_authorized_now"] is False
    assert mapped["session_manager_mutation_authorized_now"] is False


def test_session_manager_field_map_names_only_sanitized_allowed_fields() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    fields = {item["adapter_field"]: item for item in field_map["allowed_adapter_fields"]}

    assert set(fields) == {
        "proof_anchor_ref",
        "session_alias",
        "review_packet_ref",
        "compact_decision_ref",
        "source_artifact_digests",
        "safe_to_claim",
        "do_not_claim_yet",
        "next_required_gate",
        "kill_switch_default",
    }
    assert all(item["required"] is True for item in fields.values())
    assert all(item["may_contain_private_context"] is False for item in fields.values())
    assert all(item["raw_identifier_allowed"] is False for item in fields.values())
    assert all(item["customer_or_worker_visible"] is False for item in fields.values())
    assert fields["session_alias"]["source_field"] == "coordination_session_id_alias"


def test_session_manager_field_map_excludes_dangerous_field_classes_forever() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    excluded = {item["field_class"]: item for item in field_map["excluded_fields_forever"]}

    assert set(excluded) == {
        "raw_session_or_message_identifiers",
        "raw_transcripts_or_unreviewed_memory",
        "private_operator_context_or_secrets",
        "exact_gps_or_raw_metadata",
        "customer_public_worker_surfaces",
        "launch_or_settlement_controls",
        "stopped_project_inputs",
    }
    assert "raw_session_id" in excluded["raw_session_or_message_identifiers"]["examples"]
    assert "latitude" in excluded["exact_gps_or_raw_metadata"]["examples"]
    assert "autojob_history" in excluded["stopped_project_inputs"]["examples"]


def test_session_manager_field_map_runtime_defaults_are_all_disabled() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    defaults = field_map["adapter_runtime_defaults"]

    assert defaults["default_decision"] == "hold_no_runtime_mutation"
    assert defaults["kill_switch_default"] == "disabled"
    for key, value in defaults.items():
        if key not in {"default_decision", "kill_switch_default"}:
            assert value is False

    assert field_map["access_flags"]["adapter_shape_documented"] is True
    for key, value in field_map["access_flags"].items():
        if key != "adapter_shape_documented":
            assert value is False


def test_session_manager_field_map_keeps_runtime_and_external_surfaces_blocked() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    readiness = field_map["readiness"]

    assert readiness["safe_for_internal_admin_adapter_shape_reference"] is True
    for key in [
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
        "safe_for_design_only_wiring_selection",
        "safe_for_bounded_local_activation_test_selection",
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_adapter_enablement",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_session_manager_config_write",
        "safe_for_live_acontext_write_or_retrieval",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_worker_instruction_or_doctrine",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        assert readiness[key] is False


def test_session_manager_field_map_preserves_blocked_claim_boundaries() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    safe = set(field_map["claim_boundaries"]["safe_to_claim"])
    blocked = set(field_map["claim_boundaries"]["do_not_claim_yet"])

    assert set(SESSION_MANAGER_FIELD_MAP_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "mutates_session_manager",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "runtime_parity",
        "raw_session_or_message_ids",
        "raw_transcripts",
        "private_operator_context",
        "cross_project_autorouting",
        "customer_public_or_worker_surface",
        "pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "stopped_projects",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_session_manager_field_map_preserves_stopped_project_firewall() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    firewall = field_map["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_session_manager_field_map_persists_no_secret_ids_payload_or_pii() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()
    serialized = json.dumps(field_map).lower()

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


def test_session_manager_field_map_stop_line_remains_fail_closed() -> None:
    field_map = build_aas_session_manager_no_mutation_adapter_field_map()

    assert field_map["operator_guidance"]["stop_line"] == SESSION_MANAGER_FIELD_MAP_STOP_LINE
    assert "no-mutation adapter shape only" in field_map["operator_guidance"]["stop_line"]
    assert "records no answer or approval" in field_map["operator_guidance"]["stop_line"]
    assert "does not authorize IRC/session-manager mutation" in field_map["operator_guidance"]["stop_line"]
    assert field_map["operator_guidance"]["not_customer_copy"] is True
    assert field_map["operator_guidance"]["not_worker_instruction"] is True


def test_session_manager_field_map_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_aas_session_manager_no_mutation_adapter_field_map(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME
    loaded = load_aas_session_manager_no_mutation_adapter_field_map(artifact_dir=tmp_path)
    assert loaded == build_aas_session_manager_no_mutation_adapter_field_map(
        artifact_dir=tmp_path
    )


def test_session_manager_field_map_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_aas_memory_acontext_readiness_carry_forward_card())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source carry-forward readiness promoted"):
        build_aas_session_manager_no_mutation_adapter_field_map(carry_forward_card=source)

    source = copy.deepcopy(build_aas_memory_acontext_readiness_carry_forward_card())
    source["readiness_carry_forward"]["operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="source carry-forward promoted"):
        build_aas_session_manager_no_mutation_adapter_field_map(carry_forward_card=source)


def test_session_manager_field_map_loader_rejects_drift(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_aas_session_manager_no_mutation_adapter_field_map(artifact_dir=tmp_path)
    field_map = json.loads(path.read_text(encoding="utf-8"))
    field_map["readiness"]["runtime_parity_proven"] = True
    path.write_text(json.dumps(field_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="session-manager field map readiness promoted"):
        load_aas_session_manager_no_mutation_adapter_field_map(artifact_dir=tmp_path)
