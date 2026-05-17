import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_compose_image_pull_attempt_log import (
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME,
    build_acontext_compose_image_pull_attempt_log,
)
from mcp_server.city_ops.acontext_individual_image_pull_timeout_probe import (
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME,
    build_acontext_individual_image_pull_timeout_probe,
)
from mcp_server.city_ops.acontext_runtime_memory_prerequisite_probe import (
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME,
    build_acontext_runtime_memory_prerequisite_probe,
)
from mcp_server.city_ops.acontext_registry_manifest_pull_stall_diagnostic import (
    ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME,
    ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM,
    ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SCHEMA,
    REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_BLOCKED_CLAIMS,
    build_acontext_registry_manifest_pull_stall_diagnostic,
    build_may17_0102_registry_manifest_pull_stall_observation,
    load_acontext_registry_manifest_pull_stall_diagnostic,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_diagnostic() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_registry_manifest_pull_stall_diagnostic_matches_fixture():
    diagnostic = build_acontext_registry_manifest_pull_stall_diagnostic()

    assert diagnostic == read_fixture_diagnostic()
    assert diagnostic["schema"] == ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SCHEMA
    assert diagnostic["diagnostic_verdict"] == (
        "registry_manifests_available_but_docker_pull_still_stalls"
    )
    assert ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM in diagnostic[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_registry_manifest_pull_stall_diagnostic_narrows_registry_blocker_only():
    diagnostic = build_acontext_registry_manifest_pull_stall_diagnostic()
    summary = diagnostic["registry_manifest_summary"]
    pull = diagnostic["docker_pull_stall_summary"]

    assert summary["ghcr_image_count"] == 3
    assert summary["manifest_fetch_success_count"] == 3
    assert summary["all_ghcr_manifests_fetchable_anonymously"] is True
    assert summary["all_ghcr_images_advertise_linux_arm64"] is True
    assert summary["manifest_availability_is_not_pull_success"] is True
    assert summary["docker_pull_success_proven"] is False
    assert pull["timed_out_without_output"] is True
    assert pull["pulled_or_present_after_check"] is False
    assert pull["docker_pull_blocker_remains"] is True


def test_registry_manifest_pull_stall_diagnostic_preserves_image_inventory_blocker():
    diagnostic = build_acontext_registry_manifest_pull_stall_diagnostic()
    inventory = diagnostic["image_inventory"]

    assert inventory["present_required_images"] == ["pgvector/pgvector:pg16"]
    assert "ghcr.io/memodb-io/acontext-ui:latest" in inventory["missing_required_images"]
    assert "ghcr.io/memodb-io/acontext-api:latest" in inventory["missing_required_images"]
    assert inventory["missing_required_image_count"] == 8
    assert inventory["all_required_images_present"] is False


def test_registry_manifest_pull_stall_diagnostic_sticky_blocked_claims():
    diagnostic = build_acontext_registry_manifest_pull_stall_diagnostic()

    blocked = set(diagnostic["claim_boundaries"]["do_not_claim_yet"])
    assert set(REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_BLOCKED_CLAIMS) <= blocked
    assert not (set(diagnostic["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "registry_manifest_success_implies_docker_pull_success" in blocked
    assert "runtime_parity_proven_by_manifest_diagnostic" in blocked


def test_registry_manifest_pull_stall_diagnostic_refuses_missing_arm64_manifest():
    observation = build_may17_0102_registry_manifest_pull_stall_observation()
    observation["ghcr_manifest_checks"][0]["linux_arm64_manifest_advertised"] = False
    observation["ghcr_manifest_checks"][0]["platforms"] = ["linux/amd64"]

    with pytest.raises(CityOpsContractError, match="linux/arm64"):
        build_acontext_registry_manifest_pull_stall_diagnostic(observation=observation)


def test_registry_manifest_pull_stall_diagnostic_refuses_pull_success_promotion():
    observation = build_may17_0102_registry_manifest_pull_stall_observation()
    observation["docker_pull_stall_check"]["timed_out"] = False
    observation["docker_pull_stall_check"]["exit_code"] = 0
    observation["docker_pull_stall_check"]["pulled_or_present_after_check"] = True

    with pytest.raises(CityOpsContractError, match="timed out and not pulled"):
        build_acontext_registry_manifest_pull_stall_diagnostic(observation=observation)


def test_registry_manifest_pull_stall_diagnostic_refuses_live_write_observation():
    observation = build_may17_0102_registry_manifest_pull_stall_observation()
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live Acontext write"):
        build_acontext_registry_manifest_pull_stall_diagnostic(observation=observation)


def test_registry_manifest_pull_stall_diagnostic_loads_persisted_fixture():
    loaded = load_acontext_registry_manifest_pull_stall_diagnostic()

    assert loaded["schema"] == ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM
    )


def test_registry_manifest_pull_stall_diagnostic_refuses_readiness_promotion_on_load(tmp_path):
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
    source = build_acontext_individual_image_pull_timeout_probe(
        compose_attempt_log=compose_log
    )
    (tmp_path / ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    diagnostic = build_acontext_registry_manifest_pull_stall_diagnostic(individual_probe=source)
    path = tmp_path / ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME
    path.write_text(json.dumps(diagnostic), encoding="utf-8")
    diagnostic["readiness"]["all_required_images_present"] = True
    path.write_text(json.dumps(diagnostic), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_registry_manifest_pull_stall_diagnostic(artifact_dir=tmp_path)
