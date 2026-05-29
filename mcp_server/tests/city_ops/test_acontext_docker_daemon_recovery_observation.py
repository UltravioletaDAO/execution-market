from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_next_truth_selector import (
    AAS_NEXT_TRUTH_SELECTOR_FILENAME,
    AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
    build_aas_next_truth_selector,
)
from mcp_server.city_ops.aas_system_integration_runtime_truth_queue import (
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME,
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM,
    build_aas_system_integration_runtime_truth_queue,
)
from mcp_server.city_ops.acontext_docker_daemon_recovery_observation import (
    ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME,
    ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA,
    RECOVERY_OBSERVATION_BLOCKED_CLAIMS,
    RECOVERY_OBSERVATION_VERDICT,
    build_acontext_docker_daemon_recovery_observation,
    load_acontext_docker_daemon_recovery_observation,
    write_acontext_docker_daemon_recovery_observation,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_observation() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_docker_daemon_recovery_observation_matches_fixture_and_loader():
    observation = build_acontext_docker_daemon_recovery_observation()

    assert observation == read_fixture_observation()
    assert load_acontext_docker_daemon_recovery_observation() == observation
    assert observation["schema"] == ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA
    assert observation["observation_verdict"] == RECOVERY_OBSERVATION_VERDICT
    assert AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM in observation[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM in observation["claim_boundaries"][
        "safe_to_claim"
    ]
    assert ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM in observation[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_docker_daemon_recovery_observation_records_first_gate_only():
    observation = build_acontext_docker_daemon_recovery_observation()
    readiness = observation["readiness"]

    assert readiness["docker_daemon_recovery_observation_landed"] is True
    assert readiness["docker_daemon_available"] is True
    assert readiness["buildx_builder_available"] is True
    assert readiness["required_image_inventory_checked"] is True
    assert readiness["required_images_present"] is False
    assert readiness["compose_services_started"] is False
    assert readiness["acontext_api_reachable"] is False
    assert readiness["acontext_dashboard_reachable"] is False
    assert readiness["one_live_parity_attempt_authorized"] is False
    assert readiness["live_acontext_write_performed"] is False
    assert readiness["live_acontext_retrieval_performed"] is False
    assert readiness["memory_acontext_parity_ready"] is False

    gates = observation["runtime_truth_gates"]
    assert [gate["gate"] for gate in gates] == [
        "docker_daemon_socket",
        "required_image_inventory",
        "local_acontext_services",
        "empty_readiness_gate",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert gates[0]["passed"] is True
    assert all(gate["passed"] is False for gate in gates[1:])
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)


def test_docker_daemon_recovery_observation_preserves_blocked_claims():
    observation = build_acontext_docker_daemon_recovery_observation()

    safe = set(observation["claim_boundaries"]["safe_to_claim"])
    blocked = set(observation["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(RECOVERY_OBSERVATION_BLOCKED_CLAIMS) <= blocked
    assert "docker_daemon_recovery_observation_verified_required_images_present" in blocked
    assert "docker_daemon_recovery_observation_reached_acontext_api_or_dashboard" in blocked
    assert "docker_daemon_recovery_observation_completed_live_acontext_write" in blocked
    assert "docker_daemon_recovery_observation_proved_runtime_parity" in blocked
    assert "docker_daemon_recovery_observation_authorizes_queue_launch_or_dispatch" in blocked


def test_docker_daemon_recovery_observation_refuses_runtime_queue_promotion():
    queue = copy.deepcopy(build_aas_system_integration_runtime_truth_queue())
    queue["readiness"]["memory_acontext_parity_ready"] = True

    with pytest.raises(CityOpsContractError, match="runtime truth queue promoted readiness"):
        build_acontext_docker_daemon_recovery_observation(runtime_queue=queue)


def test_docker_daemon_recovery_observation_refuses_selector_promotion():
    selector = copy.deepcopy(build_aas_next_truth_selector())
    selector["readiness"]["ready_to_attempt_live_transport"] = True

    with pytest.raises(CityOpsContractError, match="next-truth selector promoted readiness"):
        build_acontext_docker_daemon_recovery_observation(next_truth_selector=selector)


def test_docker_daemon_recovery_observation_refuses_impossible_observation():
    observed = copy.deepcopy(read_fixture_observation()["runtime_observation"])
    observed["api"]["reachable"] = True

    with pytest.raises(CityOpsContractError, match="API/dashboard"):
        build_acontext_docker_daemon_recovery_observation(observation=observed)


def test_docker_daemon_recovery_observation_refuses_live_write_observation():
    observed = copy.deepcopy(read_fixture_observation()["runtime_observation"])
    observed["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live write"):
        build_acontext_docker_daemon_recovery_observation(observation=observed)


def test_docker_daemon_recovery_observation_write_and_load_temp_fixture(tmp_path):
    _copy_observation_sources(tmp_path)
    path = write_acontext_docker_daemon_recovery_observation(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME
    loaded = load_acontext_docker_daemon_recovery_observation(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM
    )


def test_docker_daemon_recovery_observation_loader_rejects_later_gate_promotion(tmp_path):
    _copy_observation_sources(tmp_path)
    path = write_acontext_docker_daemon_recovery_observation(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["acontext_api_reachable"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_docker_daemon_recovery_observation(artifact_dir=tmp_path)


def _copy_observation_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
