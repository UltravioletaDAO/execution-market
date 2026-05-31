"""Tests for the disabled-by-default Acontext runtime adapter seam contract."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_opt_in_runtime_adapter_seam_contract import (
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME,
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCHEMA,
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_STOP_LINE,
    RUNTIME_ADAPTER_SEAM_BLOCKED_CLAIMS,
    build_acontext_opt_in_runtime_adapter_seam_contract,
    load_acontext_opt_in_runtime_adapter_seam_contract,
    write_acontext_opt_in_runtime_adapter_seam_contract,
)
from mcp_server.city_ops.acontext_runtime_memory_promotion_gate import (
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME,
    build_acontext_runtime_memory_promotion_gate,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME).exists()


def test_opt_in_runtime_adapter_seam_contract_matches_fixture() -> None:
    contract = build_acontext_opt_in_runtime_adapter_seam_contract()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert contract == fixture
    assert contract["schema"] == ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCHEMA
    assert contract["contract_verdict"] == (
        "disabled_by_default_runtime_adapter_seam_contract_defined_without_runtime_mutation"
    )
    assert ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM in contract[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_opt_in_runtime_adapter_seam_contract_is_disabled_by_default() -> None:
    contract = build_acontext_opt_in_runtime_adapter_seam_contract()

    principles = contract["contract_principles"]
    assert principles["disabled_by_default"] is True
    assert principles["explicit_operator_activation_required"] is True
    assert principles["fail_closed_on_missing_cleanup_or_quarantine"] is True
    assert principles["fail_closed_on_single_fixture_only"] is True

    insertion = contract["seam_interfaces"]["runtime_insertion_point"]
    assert insertion["status"] == "design_only_not_registered"
    assert insertion["default_enabled"] is False
    assert insertion["accepts_private_context"] is False
    assert insertion["accepts_gps_or_raw_metadata"] is False
    assert insertion["accepts_customer_copy"] is False
    assert insertion["accepts_worker_instruction"] is False

    assert all(flag is False for flag in contract["access_flags"].values())


def test_opt_in_runtime_adapter_seam_contract_defines_next_gates_without_executing_them() -> None:
    contract = build_acontext_opt_in_runtime_adapter_seam_contract()

    readiness = contract["readiness"]
    assert readiness["seam_contract_landed"] is True
    assert readiness["disabled_by_default_contract_defined"] is True
    assert readiness["cleanup_or_quarantine_contract_defined"] is True
    assert readiness["multi_fixture_replay_contract_defined"] is True
    assert readiness["safe_for_internal_implementation_planning"] is True
    assert readiness["cleanup_or_quarantine_executed"] is False
    assert readiness["multi_fixture_replay_executed"] is False
    assert readiness["safe_for_runtime_adapter_registration"] is False
    assert readiness["safe_for_runtime_session_manager_mutation"] is False
    assert readiness["general_acontext_sink_ready"] is False
    assert readiness["runtime_parity_proven"] is False

    cleanup = contract["seam_interfaces"]["cleanup_or_quarantine_contract"]
    assert cleanup["status"] == "defined_not_executed"
    assert cleanup["required_before_activation"] is True
    assert cleanup["authorizes_runtime_mutation"] is False

    replay = contract["seam_interfaces"]["multi_fixture_replay_contract"]
    assert replay["minimum_reviewed_sanitized_fixtures"] == 2
    assert replay["status"] == "defined_not_executed"
    assert replay["authorizes_runtime_mutation"] is False


def test_opt_in_runtime_adapter_seam_contract_blocks_external_and_worker_claims() -> None:
    contract = build_acontext_opt_in_runtime_adapter_seam_contract()
    blocked = set(contract["claim_boundaries"]["do_not_claim_yet"])
    safe = set(contract["claim_boundaries"]["safe_to_claim"])

    assert set(RUNTIME_ADAPTER_SEAM_BLOCKED_CLAIMS) <= blocked
    assert not safe & blocked
    for required_fragment in [
        "runtime_registration",
        "irc_session_manager_mutation",
        "cross_project_autorouting",
        "customer_copy_delivery_or_publication",
        "operator_queue_launch_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "payment_or_production",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "worker_copyable_doctrine",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)

    assert all(
        row["authorizes_runtime_adapter_registration"] is False
        for row in contract["promotion_sequence"]
    )


def test_opt_in_runtime_adapter_seam_contract_forbids_sensitive_candidate_fields() -> None:
    contract = build_acontext_opt_in_runtime_adapter_seam_contract()
    candidate = contract["seam_interfaces"]["candidate_input_contract"]

    assert "sanitized_message_text" in candidate["required_fields"]
    assert "operator_hold_default" in candidate["required_fields"]
    for flag in [
        "contains_private_context",
        "contains_gps_or_raw_metadata",
        "customer_visible",
        "worker_visible",
        "dispatch_enabled",
        "reputation_enabled",
        "payment_or_production_claim",
    ]:
        assert flag in candidate["required_boolean_false_fields"]

    for forbidden in [
        "root_token",
        "bearer_token",
        "project_secret",
        "session_id",
        "message_id",
        "gps_coordinates",
        "raw_metadata",
        "private_operator_context",
        "customer_copy",
        "worker_instruction",
    ]:
        assert forbidden in candidate["forbidden_fields"]


def test_opt_in_runtime_adapter_seam_contract_keeps_secrets_and_runtime_ids_out() -> None:
    contract = build_acontext_opt_in_runtime_adapter_seam_contract()
    serialized = json.dumps(contract).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret_key_" + "hmac" not in serialized
    assert "secret_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None


def test_opt_in_runtime_adapter_seam_contract_stop_line_remains_fail_closed() -> None:
    contract = build_acontext_opt_in_runtime_adapter_seam_contract()

    assert (
        contract["operator_guidance"]["stop_line"]
        == ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_STOP_LINE
    )
    assert "Do not register the runtime adapter" in contract["operator_guidance"]["stop_line"]
    assert contract["operator_guidance"]["not_customer_copy"] is True
    assert contract["operator_guidance"]["not_worker_instruction"] is True


def test_opt_in_runtime_adapter_seam_contract_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_opt_in_runtime_adapter_seam_contract(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME
    loaded = load_acontext_opt_in_runtime_adapter_seam_contract(artifact_dir=tmp_path)
    assert loaded == build_acontext_opt_in_runtime_adapter_seam_contract(artifact_dir=tmp_path)


def test_opt_in_runtime_adapter_seam_contract_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_runtime_memory_promotion_gate())
    source["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        build_acontext_opt_in_runtime_adapter_seam_contract(promotion_gate=source)

    source = copy.deepcopy(build_acontext_runtime_memory_promotion_gate())
    source["access_flags"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="access flag promoted"):
        build_acontext_opt_in_runtime_adapter_seam_contract(promotion_gate=source)


def test_opt_in_runtime_adapter_seam_contract_rejects_fixture_drift(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_opt_in_runtime_adapter_seam_contract(artifact_dir=tmp_path)
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract["readiness"]["safe_for_runtime_adapter_registration"] = True
    path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_opt_in_runtime_adapter_seam_contract(artifact_dir=tmp_path)
