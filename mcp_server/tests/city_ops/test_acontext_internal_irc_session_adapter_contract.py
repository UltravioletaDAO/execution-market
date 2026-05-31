"""Tests for the internal IRC-session-shaped Acontext adapter contract."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_internal_irc_session_adapter_contract import (
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCHEMA,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_STOP_LINE,
    build_acontext_internal_irc_session_adapter_contract,
    load_acontext_internal_irc_session_adapter_contract,
    write_acontext_internal_irc_session_adapter_contract,
)
from mcp_server.city_ops.acontext_root_prefixed_local_write_retrieve_parity import (
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME,
    build_acontext_root_prefixed_local_write_retrieve_parity,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME).exists()


def test_build_internal_irc_adapter_contract_records_only_safe_contract(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)

    assert artifact["schema"] == ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCHEMA
    assert artifact["observation_verdict"] == (
        "internal_adapter_contract_ready_for_local_redacted_runner_but_not_irc_runtime_mutation"
    )
    assert ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM in artifact[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert artifact["derived_from"]["requires_running_local_stack_for_next_runner"] is True
    assert artifact["derived_from"]["uses_running_local_stack"] is False
    assert artifact["derived_from"]["mutates_irc_runtime_session_manager"] is False
    assert artifact["readiness"]["adapter_contract_defined"] is True
    assert artifact["readiness"]["local_runner_fixture_ready_to_execute_next"] is True
    assert artifact["readiness"]["live_runner_executed_in_this_artifact"] is False


def test_internal_irc_adapter_contract_preserves_prior_boundaries(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    source = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)
    artifact = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)
    inherited = source["claim_boundaries"]["do_not_claim_yet"]

    assert artifact["claim_boundary_audit"]["inherited_do_not_claim_yet"] == inherited
    assert artifact["claim_boundaries"]["do_not_claim_yet"][: len(inherited)] == inherited
    assert set(inherited) <= set(artifact["claim_boundaries"]["do_not_claim_yet"])
    assert not set(artifact["claim_boundaries"]["safe_to_claim"]) & set(
        artifact["claim_boundaries"]["do_not_claim_yet"]
    )


def test_internal_irc_adapter_contract_endpoint_mapping_matches_local_parity(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)
    mapping = artifact["runtime_observation"]["adapter_contract"]["endpoint_mapping"]

    assert [step["method"] for step in mapping] == ["POST", "POST", "GET"]
    assert mapping[0]["path"] == "/api/v1/session"
    assert mapping[1]["path"] == "/api/v1/session/{redacted_session_id}/messages"
    assert mapping[2]["path"] == (
        "/api/v1/session/{redacted_session_id}/messages?limit=5&format=acontext&with_events=true"
    )
    assert mapping[0]["records_session_id_in_artifact"] is False
    assert mapping[1]["records_message_id_in_artifact"] is False
    assert mapping[2]["records_message_id_in_artifact"] is False
    assert all(gate["passed"] is True for gate in artifact["contract_gates"])
    assert all(gate["authorizes_customer_or_dispatch_claim"] is False for gate in artifact["contract_gates"])


def test_internal_irc_adapter_contract_keeps_secrets_and_ids_out(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)
    serialized = json.dumps(artifact).lower()

    assert "authorization: bearer ***${root_api_bearer_token}" in serialized
    assert re.search(r"bearer sk-ac-[a-z0-9_-]{8,}", serialized) is None
    assert "root_api_bearer_token=" not in serialized
    assert "secret_key_" + "hmac" not in serialized
    assert "secret_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None


def test_internal_irc_adapter_contract_blocks_runtime_customer_dispatch_and_reputation(
    tmp_path: Path,
) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)
    blocked = artifact["claim_boundaries"]["do_not_claim_yet"]
    safe = artifact["claim_boundaries"]["safe_to_claim"]

    for required_fragment in [
        "executed_live_runner_fixture",
        "mutates_irc_runtime_session_manager",
        "enables_cross_project_autorouting",
        "authorizes_customer_copy_delivery_or_publication",
        "authorizes_queue_launch_or_dispatch",
        "authorizes_reputation_or_worker_skill_dna",
        "reverifies_payment_or_production",
        "allows_exact_gps_or_raw_metadata",
        "releases_private_operator_context",
        "creates_worker_copyable_doctrine",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)

    assert all(flag is False for flag in artifact["access_flags"].values())


def test_internal_irc_adapter_contract_stop_line_remains_narrow(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)

    assert artifact["operator_guidance"]["stop_line"] == ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_STOP_LINE
    assert "safe local runner shape only" in artifact["operator_guidance"]["stop_line"]
    assert artifact["readiness"]["irc_runtime_session_manager_ready"] is False
    assert artifact["readiness"]["cross_project_autorouting_ready"] is False
    assert artifact["readiness"]["customer_or_public_delivery_ready"] is False


def test_write_and_load_internal_irc_adapter_contract_fixture_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME
    loaded = load_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)
    assert loaded == build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)


def test_internal_irc_adapter_contract_fixture_drift_is_rejected(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["live_runner_executed_in_this_artifact"] = True
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)


def test_internal_irc_adapter_contract_rejects_secret_or_runtime_mutation(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    observation = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["adapter_contract"]["auth_strategy"][
        "header_shape"
    ] = "Authorization: Bearer unsafe-unredacted-value"

    with pytest.raises(CityOpsContractError, match="auth header"):
        build_acontext_internal_irc_session_adapter_contract(
            artifact_dir=tmp_path,
            observation=observation,
        )

    observation = build_acontext_internal_irc_session_adapter_contract(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["runner_policy"]["allowed_to_mutate_irc_runtime_session_manager"] = True

    with pytest.raises(CityOpsContractError, match="mutate_irc_runtime"):
        build_acontext_internal_irc_session_adapter_contract(
            artifact_dir=tmp_path,
            observation=observation,
        )
