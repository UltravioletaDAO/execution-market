from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_required_image_extended_pull_timeout_observation import (
    ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA,
    EXTENDED_PULL_TIMEOUT_BLOCKED_CLAIMS,
    EXTENDED_PULL_TIMEOUT_VERDICT,
    build_acontext_required_image_extended_pull_timeout_observation,
    load_acontext_required_image_extended_pull_timeout_observation,
    write_acontext_required_image_extended_pull_timeout_observation,
)
from mcp_server.city_ops.acontext_required_image_pull_retry_observation import (
    ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM,
    build_acontext_required_image_pull_retry_observation,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_observation() -> dict:
    return json.loads(
        (
            PROOF_BLOCK_DIR
            / ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME
        ).read_text(encoding="utf-8")
    )


def test_extended_pull_timeout_observation_matches_fixture_and_loader():
    observation = build_acontext_required_image_extended_pull_timeout_observation()

    assert observation == read_fixture_observation()
    assert load_acontext_required_image_extended_pull_timeout_observation() == observation
    assert observation["schema"] == ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA
    assert observation["observation_verdict"] == EXTENDED_PULL_TIMEOUT_VERDICT
    safe = observation["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM in safe
    assert ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM in safe


def test_extended_pull_timeout_records_manifest_reachability_but_missing_image():
    observation = build_acontext_required_image_extended_pull_timeout_observation()
    runtime = observation["runtime_observation"]
    readiness = observation["readiness"]

    assert len(runtime["ghcr_manifest_checks"]) == 3
    assert all(check["manifest_fetch_succeeded"] for check in runtime["ghcr_manifest_checks"])
    assert all(check["linux_arm64_manifest_advertised"] for check in runtime["ghcr_manifest_checks"])
    assert runtime["extended_pull"]["image"] == "ghcr.io/memodb-io/acontext-ui:latest"
    assert runtime["extended_pull"]["timeout_seconds"] == 600
    assert runtime["extended_pull"]["timed_out"] is True
    assert runtime["extended_pull"]["present_after_attempt"] is False
    assert runtime["image_inventory_after_extended_pull"]["present_required_images"] == [
        "pgvector/pgvector:pg16"
    ]
    assert "ghcr.io/memodb-io/acontext-ui:latest" in runtime[
        "image_inventory_after_extended_pull"
    ]["missing_required_images"]
    assert readiness["docker_daemon_available"] is True
    assert readiness["ghcr_manifests_reachable"] is True
    assert readiness["linux_arm64_manifests_advertised"] is True
    assert readiness["first_required_image_extended_pull_attempted"] is True
    assert readiness["first_required_image_present"] is False
    assert readiness["all_required_images_present"] is False
    assert readiness["compose_services_started"] is False
    assert readiness["acontext_api_reachable"] is False
    assert readiness["one_live_parity_attempt_authorized"] is False
    assert readiness["live_acontext_write_performed"] is False


def test_extended_pull_timeout_preserves_gate_order_and_blocks_live_attempt():
    observation = build_acontext_required_image_extended_pull_timeout_observation()
    gates = observation["runtime_truth_gates"]

    assert [gate["gate"] for gate in gates] == [
        "docker_daemon_socket",
        "ghcr_manifest_reachability",
        "first_required_image_extended_pull",
        "all_required_images_present",
        "local_acontext_services",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert gates[0]["passed"] is True
    assert gates[1]["passed"] is True
    assert all(gate["passed"] is False for gate in gates[2:])
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)


def test_extended_pull_timeout_preserves_blocked_claims():
    observation = build_acontext_required_image_extended_pull_timeout_observation()

    safe = set(observation["claim_boundaries"]["safe_to_claim"])
    blocked = set(observation["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(EXTENDED_PULL_TIMEOUT_BLOCKED_CLAIMS) <= blocked
    assert "extended_pull_timeout_manifest_success_implies_image_cached" in blocked
    assert "extended_pull_timeout_started_compose_services" in blocked
    assert "extended_pull_timeout_completed_live_acontext_write" in blocked
    assert "extended_pull_timeout_proved_runtime_parity" in blocked
    assert "extended_pull_timeout_authorizes_queue_launch_or_dispatch" in blocked


def test_extended_pull_timeout_refuses_source_with_promoted_image():
    source = copy.deepcopy(build_acontext_required_image_pull_retry_observation())
    source["readiness"]["first_required_image_present"] = True

    with pytest.raises(CityOpsContractError, match="source promoted later readiness"):
        build_acontext_required_image_extended_pull_timeout_observation(
            pull_retry_observation=source
        )


def test_extended_pull_timeout_refuses_successful_pull_claim():
    observed = copy.deepcopy(read_fixture_observation()["runtime_observation"])
    observed["extended_pull"]["timed_out"] = False
    observed["extended_pull"]["present_after_attempt"] = True

    with pytest.raises(CityOpsContractError, match="must record timeout"):
        build_acontext_required_image_extended_pull_timeout_observation(observation=observed)


def test_extended_pull_timeout_refuses_api_promotion():
    observed = copy.deepcopy(read_fixture_observation()["runtime_observation"])
    observed["api"]["reachable"] = True

    with pytest.raises(CityOpsContractError, match="must not reach Acontext API"):
        build_acontext_required_image_extended_pull_timeout_observation(observation=observed)


def test_extended_pull_timeout_write_and_load_temp_fixture(tmp_path):
    _copy_observation_sources(tmp_path)
    path = write_acontext_required_image_extended_pull_timeout_observation(
        artifact_dir=tmp_path
    )

    assert path.name == ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME
    loaded = load_acontext_required_image_extended_pull_timeout_observation(
        artifact_dir=tmp_path
    )
    assert loaded["schema"] == ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM
    )


def test_extended_pull_timeout_loader_rejects_drift(tmp_path):
    _copy_observation_sources(tmp_path)
    path = write_acontext_required_image_extended_pull_timeout_observation(
        artifact_dir=tmp_path
    )
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["first_required_image_present"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_required_image_extended_pull_timeout_observation(artifact_dir=tmp_path)


def _copy_observation_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
