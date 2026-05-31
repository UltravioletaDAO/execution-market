"""Tests for the Acontext runtime-memory promotion gate."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_internal_irc_session_adapter_runner_fixture import (
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME,
    build_acontext_internal_irc_session_adapter_runner_fixture,
)
from mcp_server.city_ops.acontext_runtime_memory_promotion_gate import (
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM,
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCHEMA,
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_STOP_LINE,
    PROMOTION_GATE_BLOCKED_CLAIMS,
    build_acontext_runtime_memory_promotion_gate,
    load_acontext_runtime_memory_promotion_gate,
    write_acontext_runtime_memory_promotion_gate,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME).exists()


def test_runtime_memory_promotion_gate_matches_fixture() -> None:
    gate = build_acontext_runtime_memory_promotion_gate()
    with (PROOF_BLOCK_DIR / ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert gate == fixture
    assert gate["schema"] == ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCHEMA
    assert gate["gate_verdict"] == (
        "single_redacted_runner_succeeded_runtime_promotion_remains_blocked"
    )
    assert ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM in gate[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_runtime_memory_promotion_gate_keeps_success_narrow() -> None:
    gate = build_acontext_runtime_memory_promotion_gate()

    facts = gate["promotable_facts"]
    assert facts["single_local_runner_fixture_executed"] is True
    assert facts["sanitized_session_create_status_201"] is True
    assert facts["sanitized_message_store_status_201"] is True
    assert facts["sanitized_message_retrieve_status_200"] is True
    assert facts["retrieved_message_text_matched"] is True
    assert facts["retrieved_message_meta_matched"] is True
    assert facts["root_token_or_bearer_recorded"] is False
    assert facts["session_or_message_id_recorded"] is False

    readiness = gate["readiness"]
    assert readiness["safe_for_internal_adapter_design"] is True
    assert readiness["safe_for_runtime_session_manager_mutation"] is False
    assert readiness["general_acontext_sink_ready"] is False
    assert readiness["runtime_parity_proven"] is False
    assert readiness["cleanup_or_quarantine_ready"] is False
    assert readiness["multi_fixture_replay_ready"] is False


def test_runtime_memory_promotion_gate_blocks_external_and_worker_claims() -> None:
    gate = build_acontext_runtime_memory_promotion_gate()
    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])
    safe = set(gate["claim_boundaries"]["safe_to_claim"])

    assert set(PROMOTION_GATE_BLOCKED_CLAIMS) <= blocked
    assert not safe & blocked
    for required_fragment in [
        "customer_copy_delivery_or_publication",
        "operator_queue_launch_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "payment_or_production",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "worker_copyable_doctrine",
        "runtime_parity_proven",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)

    assert all(flag is False for flag in gate["access_flags"].values())
    assert all(row["authorizes_runtime_promotion"] is False for row in gate["promotion_gates"])


def test_runtime_memory_promotion_gate_keeps_secret_and_runtime_ids_out() -> None:
    gate = build_acontext_runtime_memory_promotion_gate()
    serialized = json.dumps(gate).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret_key_" + "hmac" not in serialized
    assert "secret_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None


def test_runtime_memory_promotion_gate_stop_line_remains_fail_closed() -> None:
    gate = build_acontext_runtime_memory_promotion_gate()

    assert gate["operator_guidance"]["stop_line"] == ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_STOP_LINE
    assert "do not mutate IRC runtime session management" in gate["operator_guidance"]["stop_line"]
    assert gate["operator_guidance"]["not_customer_copy"] is True
    assert gate["operator_guidance"]["not_worker_instruction"] is True


def test_runtime_memory_promotion_gate_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_runtime_memory_promotion_gate(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME
    loaded = load_acontext_runtime_memory_promotion_gate(artifact_dir=tmp_path)
    assert loaded == build_acontext_runtime_memory_promotion_gate(artifact_dir=tmp_path)


def test_runtime_memory_promotion_gate_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_internal_irc_session_adapter_runner_fixture())
    source["readiness"]["customer_or_public_delivery_ready"] = True

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        build_acontext_runtime_memory_promotion_gate(runner_fixture=source)

    source = copy.deepcopy(build_acontext_internal_irc_session_adapter_runner_fixture())
    source["access_flags"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="access flag promoted"):
        build_acontext_runtime_memory_promotion_gate(runner_fixture=source)


def test_runtime_memory_promotion_gate_rejects_fixture_drift(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_runtime_memory_promotion_gate(artifact_dir=tmp_path)
    gate = json.loads(path.read_text(encoding="utf-8"))
    gate["readiness"]["runtime_parity_proven"] = True
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_runtime_memory_promotion_gate(artifact_dir=tmp_path)
