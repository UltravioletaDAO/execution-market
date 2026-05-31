"""Tests for the internal/admin Acontext multi-fixture replay gate."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_cleanup_quarantine_harness_gate import (
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME,
    build_acontext_cleanup_quarantine_harness_gate,
)
from mcp_server.city_ops.acontext_multi_fixture_replay_gate import (
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME,
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM,
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCHEMA,
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_STOP_LINE,
    MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS,
    build_acontext_multi_fixture_replay_gate,
    build_reviewed_sanitized_multi_fixture_replay_observation,
    load_acontext_multi_fixture_replay_gate,
    write_acontext_multi_fixture_replay_gate,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME).exists()


def test_multi_fixture_replay_gate_matches_fixture() -> None:
    gate = build_acontext_multi_fixture_replay_gate()
    with (PROOF_BLOCK_DIR / ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert gate == fixture
    assert gate["schema"] == ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCHEMA
    assert gate["gate_verdict"] == (
        "multi_fixture_replay_gate_passed_runtime_activation_remains_blocked"
    )
    assert ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM in gate["claim_boundaries"][
        "safe_to_claim"
    ]


def test_multi_fixture_replay_covers_success_hold_and_quarantine() -> None:
    gate = build_acontext_multi_fixture_replay_gate()
    results = gate["replay_results"]

    assert results["local_multi_fixture_replay_executed"] is True
    assert results["reviewed_sanitized_fixture_count"] >= 2
    assert results["success_case_count"] >= 1
    assert results["hold_case_count"] >= 1
    assert results["quarantine_case_count"] >= 1
    assert results["all_expected_outcomes_matched"] is True
    assert results["runtime_handles_kept_in_process_memory_only"] is True
    assert results["runtime_handles_persisted"] is False
    assert results["fixture_payloads_persisted"] is False

    outcomes = {
        row["fixture_label"]: row["observed_outcome"]
        for row in gate["multi_fixture_replay_observation"]["replay_cases"]
    }
    assert outcomes["reviewed_sanitized_success_retrieve_case"] == "success_cleanup"
    assert outcomes["reviewed_sanitized_failed_write_quarantine_case"] == "quarantine"
    assert outcomes["reviewed_sanitized_schema_mismatch_hold_case"] == "hold"


def test_multi_fixture_replay_keeps_runtime_activation_blocked() -> None:
    gate = build_acontext_multi_fixture_replay_gate()
    readiness = gate["readiness"]

    assert readiness["multi_fixture_replay_gate_landed"] is True
    assert readiness["safe_for_operator_activation_review_design"] is True
    assert readiness["safe_for_runtime_adapter_registration"] is False
    assert readiness["safe_for_runtime_session_manager_mutation"] is False
    assert readiness["safe_for_cross_project_autorouting"] is False
    assert readiness["safe_for_customer_or_public_delivery"] is False
    assert readiness["safe_for_queue_launch_or_dispatch"] is False
    assert readiness["safe_for_reputation_or_worker_skill_dna"] is False
    assert readiness["safe_for_payment_or_production_claim"] is False
    assert readiness["safe_for_gps_or_raw_metadata_release"] is False
    assert readiness["safe_for_private_context_release"] is False
    assert readiness["safe_for_worker_copyable_doctrine"] is False
    assert readiness["general_acontext_sink_ready"] is False
    assert readiness["runtime_parity_proven"] is False
    assert readiness["operator_activation_approved"] is False
    assert all(flag is False for flag in gate["access_flags"].values())


def test_multi_fixture_replay_preserves_blocked_claim_boundaries() -> None:
    gate = build_acontext_multi_fixture_replay_gate()
    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])
    safe = set(gate["claim_boundaries"]["safe_to_claim"])

    assert set(MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "runtime_adapter_registration",
        "irc_session_manager_mutation",
        "cross_project_autorouting",
        "customer_copy_delivery_or_publication",
        "operator_queue_launch_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "payment_or_production",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "worker_copyable_doctrine",
        "operator_activation_approved",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_multi_fixture_replay_persists_no_secret_ids_or_fixture_payload_text() -> None:
    gate = build_acontext_multi_fixture_replay_gate()
    serialized = json.dumps(gate).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret_key_" + "hmac" not in serialized
    assert "secret_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None

    observation = gate["multi_fixture_replay_observation"]
    assert observation["fixture_set"]["persists_fixture_payload_text"] is False
    assert "sanitized message" not in serialized
    assert "redacted_session_id" not in serialized
    assert "redacted_message_id" not in serialized


def test_multi_fixture_replay_stop_line_remains_fail_closed() -> None:
    gate = build_acontext_multi_fixture_replay_gate()

    assert gate["operator_guidance"]["stop_line"] == ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_STOP_LINE
    assert "does not authorize runtime adapter registration" in gate["operator_guidance"]["stop_line"]
    assert gate["operator_guidance"]["not_customer_copy"] is True
    assert gate["operator_guidance"]["not_worker_instruction"] is True
    assert gate["operator_guidance"]["next_required_gate"] == (
        "explicit_operator_activation_decision_before_runtime_mutation"
    )


def test_multi_fixture_replay_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_multi_fixture_replay_gate(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME
    loaded = load_acontext_multi_fixture_replay_gate(artifact_dir=tmp_path)
    assert loaded == build_acontext_multi_fixture_replay_gate(artifact_dir=tmp_path)


def test_multi_fixture_replay_rejects_promoted_cleanup_source() -> None:
    source = copy.deepcopy(build_acontext_cleanup_quarantine_harness_gate())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source cleanup readiness promoted"):
        build_acontext_multi_fixture_replay_gate(cleanup_gate=source)

    source = copy.deepcopy(build_acontext_cleanup_quarantine_harness_gate())
    source["access_flags"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="source cleanup access flag promoted"):
        build_acontext_multi_fixture_replay_gate(cleanup_gate=source)


def test_multi_fixture_replay_rejects_unsafe_observation() -> None:
    observation = copy.deepcopy(build_reviewed_sanitized_multi_fixture_replay_observation())
    observation["fixture_set"]["reviewed_sanitized_fixture_count"] = 1

    with pytest.raises(CityOpsContractError, match="at least two reviewed sanitized fixtures"):
        build_acontext_multi_fixture_replay_gate(observation=observation)

    observation = copy.deepcopy(build_reviewed_sanitized_multi_fixture_replay_observation())
    observation["replay_cases"][1]["hold_record_created"] = False
    observation["replay_cases"][1]["quarantine_envelope_created"] = False

    with pytest.raises(CityOpsContractError, match="hold/quarantine replay missing"):
        build_acontext_multi_fixture_replay_gate(observation=observation)

    observation = copy.deepcopy(build_reviewed_sanitized_multi_fixture_replay_observation())
    observation["replay_cases"][0]["fixture_payload_persisted"] = True

    with pytest.raises(CityOpsContractError, match="persisted fixture payload"):
        build_acontext_multi_fixture_replay_gate(observation=observation)


def test_multi_fixture_replay_rejects_fixture_drift(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_multi_fixture_replay_gate(artifact_dir=tmp_path)
    gate = json.loads(path.read_text(encoding="utf-8"))
    gate["readiness"]["safe_for_runtime_adapter_registration"] = True
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_multi_fixture_replay_gate(artifact_dir=tmp_path)
