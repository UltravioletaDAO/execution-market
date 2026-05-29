from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_image_cache_path_probe import (
    ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME,
    ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM,
    ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA,
    IMAGE_CACHE_PATH_PROBE_BLOCKED_CLAIMS,
    IMAGE_CACHE_PATH_PROBE_VERDICT,
    build_acontext_image_cache_path_probe,
    load_acontext_image_cache_path_probe,
    write_acontext_image_cache_path_probe,
)
from mcp_server.city_ops.acontext_required_image_extended_pull_timeout_observation import (
    ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    build_acontext_required_image_extended_pull_timeout_observation,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_probe() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_image_cache_path_probe_matches_fixture_and_loader():
    probe = build_acontext_image_cache_path_probe()

    assert probe == read_fixture_probe()
    assert load_acontext_image_cache_path_probe() == probe
    assert probe["schema"] == ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA
    assert probe["observation_verdict"] == IMAGE_CACHE_PATH_PROBE_VERDICT
    safe = probe["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM in safe
    assert ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM in safe


def test_image_cache_path_probe_records_changed_path_without_pull_or_install():
    probe = build_acontext_image_cache_path_probe()
    runtime = probe["runtime_observation"]
    derived = probe["derived_from"]
    readiness = probe["readiness"]

    assert derived["repeats_blind_docker_pull"] is False
    assert derived["checks_alternate_cache_tooling"] is True
    assert derived["checks_buildx_metadata_path"] is True
    assert derived["installs_registry_tooling"] is False
    assert derived["pulls_container_image"] is False
    assert [tool["tool"] for tool in runtime["alternate_cache_tools"]] == [
        "oras",
        "crane",
        "skopeo",
        "regctl",
        "nerdctl",
    ]
    assert all(tool["available"] is False for tool in runtime["alternate_cache_tools"])
    assert runtime["alternate_cache_tools_available"] is False
    assert runtime["docker_buildx_imagetools_inspect"]["timeout_seconds"] == 60
    assert runtime["docker_buildx_imagetools_inspect"]["timed_out"] is True
    assert runtime["docker_buildx_imagetools_inspect"]["produced_metadata"] is False
    assert readiness["alternate_cache_tools_available"] is False
    assert readiness["buildx_imagetools_metadata_available"] is False
    assert readiness["registry_tool_install_performed"] is False


def test_image_cache_path_probe_preserves_runtime_blockers():
    probe = build_acontext_image_cache_path_probe()
    runtime = probe["runtime_observation"]
    readiness = probe["readiness"]

    assert runtime["image_inventory_after_probe"]["present_required_images"] == [
        "pgvector/pgvector:pg16"
    ]
    assert "ghcr.io/memodb-io/acontext-ui:latest" in runtime[
        "image_inventory_after_probe"
    ]["missing_required_images"]
    assert readiness["docker_daemon_available"] is True
    assert readiness["first_required_image_present"] is False
    assert readiness["all_required_images_present"] is False
    assert readiness["compose_services_started"] is False
    assert readiness["acontext_api_reachable"] is False
    assert readiness["acontext_dashboard_reachable"] is False
    assert readiness["one_live_parity_attempt_authorized"] is False
    assert readiness["live_acontext_write_performed"] is False
    assert readiness["memory_acontext_parity_ready"] is False


def test_image_cache_path_probe_preserves_gate_order_and_blocks_live_attempt():
    probe = build_acontext_image_cache_path_probe()
    gates = probe["runtime_truth_gates"]

    assert [gate["gate"] for gate in gates] == [
        "docker_daemon_socket",
        "alternate_registry_cache_tooling",
        "docker_buildx_metadata_path",
        "first_required_image_cached",
        "all_required_images_present",
        "local_acontext_services",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert gates[0]["passed"] is True
    assert all(gate["passed"] is False for gate in gates[1:])
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)


def test_image_cache_path_probe_preserves_blocked_claims():
    probe = build_acontext_image_cache_path_probe()

    safe = set(probe["claim_boundaries"]["safe_to_claim"])
    blocked = set(probe["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(IMAGE_CACHE_PATH_PROBE_BLOCKED_CLAIMS) <= blocked
    assert "image_cache_path_probe_installed_registry_tooling" in blocked
    assert "image_cache_path_probe_cached_first_required_image" in blocked
    assert "image_cache_path_probe_started_compose_services" in blocked
    assert "image_cache_path_probe_completed_live_acontext_write" in blocked
    assert "image_cache_path_probe_proved_runtime_parity" in blocked
    assert "image_cache_path_probe_authorizes_queue_launch_or_dispatch" in blocked


def test_image_cache_path_probe_refuses_source_with_promoted_image():
    source = copy.deepcopy(build_acontext_required_image_extended_pull_timeout_observation())
    source["readiness"]["first_required_image_present"] = True

    with pytest.raises(CityOpsContractError, match="source promoted later readiness"):
        build_acontext_image_cache_path_probe(extended_pull_observation=source)


def test_image_cache_path_probe_refuses_tool_availability_claim():
    observed = copy.deepcopy(read_fixture_probe()["runtime_observation"])
    observed["alternate_cache_tools"][0]["available"] = True

    with pytest.raises(CityOpsContractError, match="must not claim registry tooling"):
        build_acontext_image_cache_path_probe(observation=observed)


def test_image_cache_path_probe_refuses_metadata_success_claim():
    observed = copy.deepcopy(read_fixture_probe()["runtime_observation"])
    observed["docker_buildx_imagetools_inspect"]["timed_out"] = False
    observed["docker_buildx_imagetools_inspect"]["produced_metadata"] = True

    with pytest.raises(CityOpsContractError, match="must record timeout"):
        build_acontext_image_cache_path_probe(observation=observed)


def test_image_cache_path_probe_refuses_api_promotion():
    observed = copy.deepcopy(read_fixture_probe()["runtime_observation"])
    observed["api"]["reachable"] = True

    with pytest.raises(CityOpsContractError, match="must not reach Acontext API"):
        build_acontext_image_cache_path_probe(observation=observed)


def test_image_cache_path_probe_write_and_load_temp_fixture(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_image_cache_path_probe(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME
    loaded = load_acontext_image_cache_path_probe(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM
    )


def test_image_cache_path_probe_loader_rejects_drift(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_image_cache_path_probe(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["first_required_image_present"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_image_cache_path_probe(artifact_dir=tmp_path)


def _copy_probe_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
