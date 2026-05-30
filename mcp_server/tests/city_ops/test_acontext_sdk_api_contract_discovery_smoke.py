"""Tests for the Acontext SDK/API contract-discovery smoke artifact."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_remaining_images_oras_compose_health_observation import (
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME,
)
from mcp_server.city_ops.acontext_sdk_api_contract_discovery_smoke import (
    ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME,
    ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM,
    ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCHEMA,
    build_acontext_sdk_api_contract_discovery_smoke,
    load_acontext_sdk_api_contract_discovery_smoke,
    write_acontext_sdk_api_contract_discovery_smoke,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME).exists()


def test_build_contract_discovery_smoke_preserves_contract_and_blocks_parity(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)

    assert artifact["schema"] == ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCHEMA
    assert artifact["observation_verdict"] == (
        "local_acontext_contract_surface_discovered_project_bearer_gate_blocks_write_retrieve_parity"
    )
    assert ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM in artifact["claim_boundaries"]["safe_to_claim"]
    assert artifact["runtime_observation"]["contract_surface"]["session_write_contract_seen"] is True
    assert artifact["runtime_observation"]["contract_surface"]["message_write_contract_seen"] is True
    assert artifact["runtime_observation"]["contract_surface"]["message_retrieval_contract_seen"] is True
    assert artifact["runtime_observation"]["auth_gate"]["project_bearer_required"] is True
    assert artifact["runtime_observation"]["auth_gate"]["project_secret_value_available_to_this_smoke"] is False
    assert artifact["readiness"]["contract_surface_discovered"] is True
    assert artifact["readiness"]["project_bearer_available_to_smoke"] is False
    assert artifact["readiness"]["mutating_write_retrieve_smoke_attempted"] is False
    assert artifact["readiness"]["runtime_parity_proven"] is False


def test_contract_discovery_auth_probes_are_401_and_no_secret_values(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)
    auth = artifact["runtime_observation"]["auth_gate"]

    assert auth["root_api_bearer_token_value_recorded"] is False
    assert auth["root_token_accepted_for_project_endpoints"] is False
    assert auth["unauthorized_body_shape"] == {"code": 401, "msg": "Unauthorized"}
    for probe in auth["auth_probes"]:
        assert probe["no_auth_status"] == 401
        assert probe["root_token_status"] == 401

    serialized = json.dumps(artifact)
    assert "Bearer sk-" not in serialized
    assert "ROOT_API_BEARER_TOKEN" not in serialized
    assert "secret_key" not in serialized.lower()


def test_contract_discovery_gate_order_is_truthful(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)
    gates = {gate["gate"]: gate for gate in artifact["runtime_truth_gates"]}

    assert gates["local_stack_health_recheck"]["passed"] is True
    assert gates["sdk_import_available"]["passed"] is False
    assert gates["raw_http_contract_surface_discovered"]["passed"] is True
    assert gates["project_bearer_auth_ready"]["passed"] is False
    assert gates["single_live_write_retrieve_parity_attempt"]["passed"] is False
    assert all(gate["authorizes_customer_or_dispatch_claim"] is False for gate in artifact["runtime_truth_gates"])


def test_write_and_load_contract_discovery_fixture_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME
    loaded = load_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)
    assert loaded == build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)


def test_contract_discovery_fixture_drift_is_rejected(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["runtime_parity_proven"] = True
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)


def test_contract_discovery_rejects_mutating_observation(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    observation = build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path)["runtime_observation"]
    observation["mutating_smoke"] = dict(observation["mutating_smoke"], attempted=True)

    with pytest.raises(CityOpsContractError, match="mutating smoke"):
        build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=tmp_path, observation=observation)
