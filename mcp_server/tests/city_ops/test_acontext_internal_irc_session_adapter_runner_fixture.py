"""Tests for the redacted local IRC-shaped Acontext adapter runner fixture."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_internal_irc_session_adapter_contract import (
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME,
)
from mcp_server.city_ops.acontext_internal_irc_session_adapter_runner_fixture import (
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCHEMA,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_STOP_LINE,
    build_acontext_internal_irc_session_adapter_runner_fixture,
    load_acontext_internal_irc_session_adapter_runner_fixture,
    write_acontext_internal_irc_session_adapter_runner_fixture,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME).exists()


def test_build_runner_fixture_records_live_local_success_without_ids(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)

    assert artifact["schema"] == ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCHEMA
    assert artifact["observation_verdict"] == (
        "local_redacted_irc_session_adapter_runner_succeeded_without_runtime_mutation"
    )
    assert artifact["readiness"]["local_runner_fixture_executed"] is True
    assert artifact["readiness"]["sanitized_session_create_status_201"] is True
    assert artifact["readiness"]["sanitized_message_store_status_201"] is True
    assert artifact["readiness"]["sanitized_message_retrieve_status_200"] is True
    assert artifact["readiness"]["retrieved_message_text_matched"] is True
    assert artifact["readiness"]["retrieved_message_meta_matched"] is True
    assert artifact["readiness"]["root_token_or_bearer_recorded"] is False
    assert artifact["readiness"]["session_or_message_id_recorded"] is False


def test_runner_fixture_lifts_only_the_executed_fixture_blocker(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)

    assert artifact["claim_boundary_audit"]["lifted_by_this_redacted_local_runner"] == [
        "internal_irc_adapter_executed_live_runner_fixture"
    ]
    assert "internal_irc_adapter_executed_live_runner_fixture" not in artifact[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM in artifact[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert not set(artifact["claim_boundaries"]["safe_to_claim"]) & set(
        artifact["claim_boundaries"]["do_not_claim_yet"]
    )


def test_runner_fixture_blocks_runtime_customer_dispatch_and_reputation(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)
    blocked = artifact["claim_boundaries"]["do_not_claim_yet"]
    safe = artifact["claim_boundaries"]["safe_to_claim"]

    for required_fragment in [
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
    assert artifact["readiness"]["irc_runtime_session_manager_ready"] is False
    assert artifact["readiness"]["cross_project_autorouting_ready"] is False
    assert artifact["readiness"]["customer_or_public_delivery_ready"] is False


def test_runner_fixture_keeps_secrets_and_runtime_ids_out(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)
    serialized = json.dumps(artifact).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret_key_" + "hmac" not in serialized
    assert "secret_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None


def test_runner_fixture_stop_line_remains_narrow(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)

    assert artifact["operator_guidance"]["stop_line"] == ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_STOP_LINE
    assert "one sanitized fixture only" in artifact["operator_guidance"]["stop_line"]
    assert artifact["operator_guidance"]["not_customer_copy"] is True
    assert artifact["operator_guidance"]["not_worker_instruction"] is True


def test_write_and_load_runner_fixture_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME
    loaded = load_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)
    assert loaded == build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)


def test_runner_fixture_drift_is_rejected(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["customer_or_public_delivery_ready"] = True
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)


def test_runner_fixture_rejects_failed_store_or_private_metadata(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    observation = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["local_runner_probe"]["store_message"]["status_code"] = 400

    with pytest.raises(CityOpsContractError, match="store message"):
        build_acontext_internal_irc_session_adapter_runner_fixture(
            artifact_dir=tmp_path,
            observation=observation,
        )

    observation = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["runner_input"]["metadata"]["contains_private_context"] = True

    with pytest.raises(CityOpsContractError, match="metadata unsafe"):
        build_acontext_internal_irc_session_adapter_runner_fixture(
            artifact_dir=tmp_path,
            observation=observation,
        )
