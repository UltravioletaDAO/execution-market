"""Tests for the Acontext project-admin route mismatch observation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_project_admin_route_mismatch_observation import (
    ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME,
    ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM,
    ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCHEMA,
    build_acontext_project_admin_route_mismatch_observation,
    load_acontext_project_admin_route_mismatch_observation,
    write_acontext_project_admin_route_mismatch_observation,
)
from mcp_server.city_ops.acontext_sdk_api_contract_discovery_smoke import (
    ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME).exists()


def test_build_admin_route_mismatch_records_404_blocker(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)

    assert artifact["schema"] == ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCHEMA
    assert artifact["observation_verdict"] == (
        "swagger_advertises_admin_project_route_but_running_api_returns_404_project_secret_gate_still_blocked"
    )
    assert ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM in artifact["claim_boundaries"]["safe_to_claim"]
    assert artifact["readiness"]["admin_project_route_advertised_by_swagger"] is True
    assert artifact["readiness"]["admin_project_route_reachable"] is False
    assert artifact["readiness"]["project_bearer_available_to_probe"] is False
    assert artifact["readiness"]["runtime_parity_proven"] is False
    assert artifact["runtime_observation"]["runtime_truth_delta"]["new_blocker"] == (
        "project_admin_route_mismatch_404"
    )


def test_admin_route_mismatch_keeps_secret_and_identity_values_out(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)
    observation = artifact["runtime_observation"]

    assert observation["root_token_probe"]["root_token_available_to_local_probe"] is True
    assert observation["root_token_probe"]["root_token_value_recorded"] is False
    assert observation["sanitization_policy"]["include_project_secret_value"] is False
    assert observation["sanitization_policy"]["include_project_id"] is False
    assert observation["live_parity_attempt"]["recorded_project_secret"] is False
    assert observation["live_parity_attempt"]["created_session"] is False

    serialized = json.dumps(artifact).lower()
    assert "bearer sk-" not in serialized
    assert "root_api_bearer_token=" not in serialized
    assert "secret_key_hmac" not in serialized
    assert "secret_key_hash_phc" not in serialized


def test_admin_route_mismatch_gate_order_blocks_write_retrieve(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)
    gates = {gate["gate"]: gate for gate in artifact["runtime_truth_gates"]}

    assert gates["contract_discovery_source_loaded"]["passed"] is True
    assert gates["root_token_available_without_recording_value"]["passed"] is True
    assert gates["admin_project_route_reachable"]["passed"] is False
    assert gates["project_bearer_secret_obtained"]["passed"] is False
    assert gates["single_live_write_retrieve_parity_attempt"]["passed"] is False
    assert all(gate["authorizes_customer_or_dispatch_claim"] is False for gate in artifact["runtime_truth_gates"])


def test_write_and_load_admin_route_mismatch_fixture_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME
    loaded = load_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)
    assert loaded == build_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)


def test_admin_route_mismatch_fixture_drift_is_rejected(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["admin_project_route_reachable"] = True
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)


def test_admin_route_mismatch_rejects_secret_recording_or_successful_route(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    observation = build_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["admin_project_route_probes"][0]["status_code"] = 201

    with pytest.raises(CityOpsContractError, match="404"):
        build_acontext_project_admin_route_mismatch_observation(
            artifact_dir=tmp_path,
            observation=observation,
        )

    observation = build_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["live_parity_attempt"]["recorded_project_secret"] = True

    with pytest.raises(CityOpsContractError, match="recorded_project_secret"):
        build_acontext_project_admin_route_mismatch_observation(
            artifact_dir=tmp_path,
            observation=observation,
        )
