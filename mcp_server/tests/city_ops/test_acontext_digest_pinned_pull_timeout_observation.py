from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_cache_path_resolution_plan import (
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME,
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM,
    build_acontext_cache_path_resolution_plan,
)
from mcp_server.city_ops.acontext_digest_pinned_pull_timeout_observation import (
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA,
    DIGEST_PINNED_PULL_TIMEOUT_BLOCKED_CLAIMS,
    DIGEST_PINNED_PULL_TIMEOUT_VERDICT,
    FIRST_REQUIRED_IMAGE,
    FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
    FIRST_REQUIRED_IMAGE_INDEX_DIGEST,
    build_acontext_digest_pinned_pull_timeout_observation,
    load_acontext_digest_pinned_pull_timeout_observation,
    write_acontext_digest_pinned_pull_timeout_observation,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_observation() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_digest_pinned_pull_timeout_matches_fixture_and_loader():
    observation = build_acontext_digest_pinned_pull_timeout_observation()

    assert observation == read_fixture_observation()
    assert load_acontext_digest_pinned_pull_timeout_observation() == observation
    assert observation["schema"] == ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA
    assert observation["observation_verdict"] == DIGEST_PINNED_PULL_TIMEOUT_VERDICT
    safe = observation["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM in safe
    assert ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM in safe


def test_digest_pinned_pull_timeout_locks_manifest_but_keeps_image_missing():
    observation = build_acontext_digest_pinned_pull_timeout_observation()
    runtime = observation["runtime_observation"]
    manifest = runtime["registry_manifest_lock"]
    pull = runtime["digest_pinned_pull"]
    readiness = observation["readiness"]

    assert manifest["image"] == FIRST_REQUIRED_IMAGE
    assert manifest["index_digest"] == FIRST_REQUIRED_IMAGE_INDEX_DIGEST
    assert manifest["manifest_digest"] == FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST
    assert manifest["linux_arm64_manifest_advertised"] is True
    assert manifest["layer_count"] == 10
    assert manifest["layer_total_size_bytes"] == 75482880
    assert manifest["blob_download_performed"] is False
    assert manifest["image_load_performed"] is False
    assert pull["digest"] == FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST
    assert pull["timeout_seconds"] == 240
    assert pull["timed_out"] is True
    assert pull["present_after_attempt"] is False
    assert readiness["registry_manifest_digest_locked"] is True
    assert readiness["digest_pinned_pull_attempted"] is True
    assert readiness["digest_pinned_pull_completed"] is False
    assert readiness["first_required_image_present"] is False


def test_digest_pinned_pull_timeout_gate_order_blocks_runtime():
    observation = build_acontext_digest_pinned_pull_timeout_observation()
    gates = observation["runtime_truth_gates"]

    assert [gate["gate"] for gate in gates] == [
        "docker_daemon_socket",
        "registry_manifest_digest_lock",
        "digest_pinned_docker_pull",
        "all_required_images_present",
        "local_acontext_services",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert gates[0]["passed"] is True
    assert gates[1]["passed"] is True
    assert all(gate["passed"] is False for gate in gates[2:])
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)
    assert observation["readiness"]["all_required_images_present"] is False
    assert observation["readiness"]["acontext_api_reachable"] is False
    assert observation["readiness"]["memory_acontext_parity_ready"] is False


def test_digest_pinned_pull_timeout_preserves_blocked_claims():
    observation = build_acontext_digest_pinned_pull_timeout_observation()

    safe = set(observation["claim_boundaries"]["safe_to_claim"])
    blocked = set(observation["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(DIGEST_PINNED_PULL_TIMEOUT_BLOCKED_CLAIMS) <= blocked
    assert "digest_pinned_pull_timeout_cached_first_required_image" in blocked
    assert "digest_pinned_pull_timeout_started_compose_services" in blocked
    assert "digest_pinned_pull_timeout_completed_live_acontext_write" in blocked
    assert "digest_pinned_pull_timeout_proved_runtime_parity" in blocked
    assert "digest_pinned_pull_timeout_authorizes_customer_copy_delivery_or_publication" in blocked


def test_digest_pinned_pull_timeout_refuses_source_with_unexpected_selected_path():
    source = copy.deepcopy(build_acontext_cache_path_resolution_plan())
    source["selected_next_changed_cache_path"] = "blind_tag_pull_retry"

    with pytest.raises(CityOpsContractError, match="selected unexpected path"):
        build_acontext_digest_pinned_pull_timeout_observation(
            cache_path_resolution_plan=source
        )


def test_digest_pinned_pull_timeout_refuses_observation_with_promoted_image_presence():
    observation = copy.deepcopy(read_fixture_observation())
    source = build_acontext_cache_path_resolution_plan()
    runtime = observation["runtime_observation"]
    runtime["digest_pinned_pull"]["present_after_attempt"] = True

    with pytest.raises(CityOpsContractError, match="must not claim image presence"):
        build_acontext_digest_pinned_pull_timeout_observation(
            cache_path_resolution_plan=source,
            observation=runtime,
        )


def test_digest_pinned_pull_timeout_write_and_load_temp_fixture(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_digest_pinned_pull_timeout_observation(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME
    loaded = load_acontext_digest_pinned_pull_timeout_observation(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM
    )


def test_digest_pinned_pull_timeout_loader_rejects_drift(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_digest_pinned_pull_timeout_observation(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["first_required_image_present"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_digest_pinned_pull_timeout_observation(artifact_dir=tmp_path)


def _copy_probe_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
