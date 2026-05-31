"""Tests for the local Acontext cleanup/quarantine harness gate."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_cleanup_quarantine_harness_gate import (
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME,
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM,
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCHEMA,
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_STOP_LINE,
    CLEANUP_QUARANTINE_HARNESS_BLOCKED_CLAIMS,
    build_acontext_cleanup_quarantine_harness_gate,
    build_local_cleanup_quarantine_harness_observation,
    load_acontext_cleanup_quarantine_harness_gate,
    write_acontext_cleanup_quarantine_harness_gate,
)
from mcp_server.city_ops.acontext_opt_in_runtime_adapter_seam_contract import (
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME,
    build_acontext_opt_in_runtime_adapter_seam_contract,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME).exists()


def test_cleanup_quarantine_harness_gate_matches_fixture() -> None:
    gate = build_acontext_cleanup_quarantine_harness_gate()
    with (PROOF_BLOCK_DIR / ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert gate == fixture
    assert gate["schema"] == ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCHEMA
    assert gate["gate_verdict"] == (
        "local_cleanup_quarantine_harness_passed_runtime_activation_remains_blocked"
    )
    assert ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM in gate[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_cleanup_quarantine_harness_executes_success_and_failure_paths_safely() -> None:
    gate = build_acontext_cleanup_quarantine_harness_gate()
    results = gate["cleanup_quarantine_results"]

    assert results["local_harness_executed"] is True
    assert results["success_cleanup_path_observed"] is True
    assert results["failed_write_quarantine_path_observed"] is True
    assert results["runtime_handles_kept_in_process_memory_only"] is True
    assert results["runtime_handles_persisted"] is False
    assert results["status_booleans_and_status_classes_only"] is True
    assert results["candidate_text_persisted"] is False
    assert results["raw_metadata_persisted"] is False
    assert results["private_context_persisted"] is False
    assert results["gps_or_raw_metadata_persisted"] is False

    paths = {row["path_kind"]: row for row in gate["harness_observation"]["local_harness_paths"]}
    assert paths["success_cleanup"]["cleanup_observed"] is True
    assert paths["success_cleanup"]["quarantine_envelope_created"] is False
    assert paths["failed_write_quarantine"]["quarantine_observed"] is True
    assert paths["failed_write_quarantine"]["quarantine_envelope_created"] is True
    assert all(row["runtime_handle_persisted"] is False for row in paths.values())
    assert all(row["status_boolean_recorded_only"] is True for row in paths.values())


def test_cleanup_quarantine_harness_keeps_runtime_activation_blocked() -> None:
    gate = build_acontext_cleanup_quarantine_harness_gate()
    readiness = gate["readiness"]

    assert readiness["cleanup_quarantine_harness_gate_landed"] is True
    assert readiness["safe_for_internal_multi_fixture_replay_design"] is True
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
    assert readiness["multi_fixture_replay_executed"] is False
    assert readiness["operator_activation_approved"] is False
    assert all(flag is False for flag in gate["access_flags"].values())


def test_cleanup_quarantine_harness_blocks_external_and_worker_claims() -> None:
    gate = build_acontext_cleanup_quarantine_harness_gate()
    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])
    safe = set(gate["claim_boundaries"]["safe_to_claim"])

    assert set(CLEANUP_QUARANTINE_HARNESS_BLOCKED_CLAIMS) <= blocked
    assert not safe & blocked
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
        "multi_fixture_replay_executed",
        "operator_activation_approved",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)

    assert all(
        row["authorizes_runtime_adapter_registration"] is False
        for row in gate["promotion_sequence"]
    )


def test_cleanup_quarantine_harness_persists_no_secret_ids_or_candidate_text() -> None:
    gate = build_acontext_cleanup_quarantine_harness_gate()
    serialized = json.dumps(gate).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret_key_" + "hmac" not in serialized
    assert "secret_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None

    observation = gate["harness_observation"]
    assert observation["harness_inputs"]["persists_candidate_text"] is False
    assert "sanitized message" not in serialized
    assert "redacted_session_id" not in serialized
    assert "redacted_message_id" not in serialized


def test_cleanup_quarantine_harness_stop_line_remains_fail_closed() -> None:
    gate = build_acontext_cleanup_quarantine_harness_gate()

    assert gate["operator_guidance"]["stop_line"] == ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_STOP_LINE
    assert "does not authorize runtime adapter registration" in gate["operator_guidance"]["stop_line"]
    assert gate["operator_guidance"]["not_customer_copy"] is True
    assert gate["operator_guidance"]["not_worker_instruction"] is True


def test_cleanup_quarantine_harness_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_cleanup_quarantine_harness_gate(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME
    loaded = load_acontext_cleanup_quarantine_harness_gate(artifact_dir=tmp_path)
    assert loaded == build_acontext_cleanup_quarantine_harness_gate(artifact_dir=tmp_path)


def test_cleanup_quarantine_harness_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_opt_in_runtime_adapter_seam_contract())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        build_acontext_cleanup_quarantine_harness_gate(seam_contract=source)

    source = copy.deepcopy(build_acontext_opt_in_runtime_adapter_seam_contract())
    source["access_flags"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="access flag promoted"):
        build_acontext_cleanup_quarantine_harness_gate(seam_contract=source)


def test_cleanup_quarantine_harness_rejects_unsafe_observation() -> None:
    observation = copy.deepcopy(build_local_cleanup_quarantine_harness_observation())
    observation["harness_inputs"]["persists_runtime_session_id"] = True

    with pytest.raises(CityOpsContractError, match="unsafe harness input persistence"):
        build_acontext_cleanup_quarantine_harness_gate(observation=observation)

    observation = copy.deepcopy(build_local_cleanup_quarantine_harness_observation())
    observation["local_harness_paths"][1]["quarantine_envelope_created"] = False

    with pytest.raises(CityOpsContractError, match="failed write path missing quarantine envelope"):
        build_acontext_cleanup_quarantine_harness_gate(observation=observation)


def test_cleanup_quarantine_harness_rejects_fixture_drift(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_cleanup_quarantine_harness_gate(artifact_dir=tmp_path)
    gate = json.loads(path.read_text(encoding="utf-8"))
    gate["readiness"]["safe_for_runtime_adapter_registration"] = True
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_cleanup_quarantine_harness_gate(artifact_dir=tmp_path)
