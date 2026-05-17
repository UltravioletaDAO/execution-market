import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_docker_pull_path_diagnostic import (
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME,
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM,
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SCHEMA,
    DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS,
    build_acontext_docker_pull_path_diagnostic,
    build_may17_0200_docker_pull_path_observation,
    load_acontext_docker_pull_path_diagnostic,
)
from mcp_server.city_ops.acontext_registry_manifest_pull_stall_diagnostic import (
    ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME,
    build_acontext_registry_manifest_pull_stall_diagnostic,
)
from mcp_server.city_ops.acontext_individual_image_pull_timeout_probe import (
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME,
    build_acontext_individual_image_pull_timeout_probe,
)
from mcp_server.city_ops.acontext_compose_image_pull_attempt_log import (
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME,
    build_acontext_compose_image_pull_attempt_log,
)
from mcp_server.city_ops.acontext_runtime_memory_prerequisite_probe import (
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME,
    build_acontext_runtime_memory_prerequisite_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_diagnostic() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_docker_pull_path_diagnostic_matches_fixture():
    diagnostic = build_acontext_docker_pull_path_diagnostic()

    assert diagnostic == read_fixture_diagnostic()
    assert diagnostic["schema"] == ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SCHEMA
    assert diagnostic["diagnostic_verdict"] == (
        "docker_context_available_but_explicit_platform_pull_still_stalls"
    )
    assert ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM in diagnostic[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_docker_pull_path_diagnostic_records_sanitized_context_without_promotion():
    diagnostic = build_acontext_docker_pull_path_diagnostic()
    summary = diagnostic["docker_context_summary"]

    assert summary["docker_context_available"] is True
    assert summary["server_arch"] == "aarch64"
    assert summary["buildx_running"] is True
    assert summary["buildx_linux_arm64_advertised"] is True
    assert summary["context_availability_is_not_pull_success"] is True
    assert diagnostic["docker_pull_path_observation"]["sanitization_policy"] == {
        "include_tokens": False,
        "include_registry_credentials": False,
        "include_raw_docker_logs": False,
        "include_home_paths": False,
        "include_private_operator_context": False,
    }


def test_docker_pull_path_diagnostic_preserves_explicit_platform_pull_blocker():
    diagnostic = build_acontext_docker_pull_path_diagnostic()
    retry = diagnostic["explicit_platform_retry_summary"]

    assert retry["image"] == "ghcr.io/memodb-io/acontext-ui:latest"
    assert retry["platform"] == "linux/arm64"
    assert retry["timed_out_without_output"] is True
    assert retry["exit_code"] is None
    assert retry["pulled_or_present_after_retry"] is False
    assert retry["explicit_platform_retry_blocker_remains"] is True


def test_docker_pull_path_diagnostic_preserves_image_inventory_blocker():
    diagnostic = build_acontext_docker_pull_path_diagnostic()
    inventory = diagnostic["image_inventory"]

    assert inventory["present_required_images"] == ["pgvector/pgvector:pg16"]
    assert "ghcr.io/memodb-io/acontext-ui:latest" in inventory["missing_required_images"]
    assert "ghcr.io/memodb-io/acontext-api:latest" in inventory["missing_required_images"]
    assert inventory["missing_required_image_count"] == 8
    assert inventory["all_required_images_present"] is False


def test_docker_pull_path_diagnostic_sticky_blocked_claims():
    diagnostic = build_acontext_docker_pull_path_diagnostic()

    blocked = set(diagnostic["claim_boundaries"]["do_not_claim_yet"])
    assert set(DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS) <= blocked
    assert not (set(diagnostic["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "explicit_platform_retry_resolved_pull_stall" in blocked
    assert "runtime_parity_proven_by_docker_pull_path_diagnostic" in blocked


def test_docker_pull_path_diagnostic_refuses_unsanitized_observation():
    observation = build_may17_0200_docker_pull_path_observation()
    observation["sanitization_policy"]["include_tokens"] = True

    with pytest.raises(CityOpsContractError, match="include_tokens"):
        build_acontext_docker_pull_path_diagnostic(observation=observation)


def test_docker_pull_path_diagnostic_refuses_pull_success_promotion():
    observation = build_may17_0200_docker_pull_path_observation()
    observation["explicit_platform_pull_retry"]["timed_out"] = False
    observation["explicit_platform_pull_retry"]["exit_code"] = 0
    observation["explicit_platform_pull_retry"]["pulled_or_present_after_retry"] = True

    with pytest.raises(CityOpsContractError, match="explicit platform retry"):
        build_acontext_docker_pull_path_diagnostic(observation=observation)


def test_docker_pull_path_diagnostic_refuses_live_write_observation():
    observation = build_may17_0200_docker_pull_path_observation()
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live Acontext write"):
        build_acontext_docker_pull_path_diagnostic(observation=observation)


def test_docker_pull_path_diagnostic_loads_persisted_fixture():
    loaded = load_acontext_docker_pull_path_diagnostic()

    assert loaded["schema"] == ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM
    )


def test_docker_pull_path_diagnostic_refuses_readiness_promotion_on_load(tmp_path):
    prerequisite = build_acontext_runtime_memory_prerequisite_probe()
    (tmp_path / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME).write_text(
        json.dumps(prerequisite), encoding="utf-8"
    )
    compose_log = build_acontext_compose_image_pull_attempt_log(
        prerequisite_probe=prerequisite
    )
    (tmp_path / ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME).write_text(
        json.dumps(compose_log), encoding="utf-8"
    )
    individual_probe = build_acontext_individual_image_pull_timeout_probe(
        compose_attempt_log=compose_log
    )
    (tmp_path / ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME).write_text(
        json.dumps(individual_probe), encoding="utf-8"
    )
    registry = build_acontext_registry_manifest_pull_stall_diagnostic(
        individual_probe=individual_probe
    )
    (tmp_path / ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME).write_text(
        json.dumps(registry), encoding="utf-8"
    )
    diagnostic = build_acontext_docker_pull_path_diagnostic(registry_diagnostic=registry)
    path = tmp_path / ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME
    path.write_text(json.dumps(diagnostic), encoding="utf-8")
    diagnostic["readiness"]["all_required_images_present"] = True
    path.write_text(json.dumps(diagnostic), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_docker_pull_path_diagnostic(artifact_dir=tmp_path)
