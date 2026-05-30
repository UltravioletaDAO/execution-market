from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_7am_trusted_cache_path_probe import (
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME,
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM,
    build_acontext_7am_trusted_cache_path_probe,
)
from mcp_server.city_ops.acontext_crane_export_load_timeout_observation import (
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_BLOCKED_CLAIMS,
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCHEMA,
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_VERDICT,
    build_acontext_crane_export_load_timeout_observation,
    load_acontext_crane_export_load_timeout_observation,
    write_acontext_crane_export_load_timeout_observation,
)
from mcp_server.city_ops.acontext_digest_pinned_pull_timeout_observation import (
    FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_observation() -> dict:
    return json.loads(
        (
            PROOF_BLOCK_DIR / ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME
        ).read_text(encoding="utf-8")
    )


def test_crane_export_load_timeout_observation_matches_fixture_and_loader():
    observation = build_acontext_crane_export_load_timeout_observation()

    assert observation == read_fixture_observation()
    assert load_acontext_crane_export_load_timeout_observation() == observation
    assert observation["schema"] == ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCHEMA
    assert observation["observation_verdict"] == (
        ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_VERDICT
    )
    safe = observation["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM in safe
    assert ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM in safe


def test_crane_export_load_attempt_records_tool_install_and_timeout_without_promotion():
    observation = build_acontext_crane_export_load_timeout_observation()
    runtime = observation["runtime_observation"]
    attempt = runtime["changed_cache_path_attempt"]
    inventory = runtime["image_inventory_after_attempt"]
    readiness = observation["readiness"]

    assert runtime["trusted_tool"] == {
        "tool": "crane",
        "available": True,
        "path": "/opt/homebrew/bin/crane",
        "version": "0.21.6",
        "install_source": "Homebrew formula crane",
        "export_load_capable_for_local_image_cache": True,
    }
    assert attempt["attempted"] is True
    assert attempt["registry_tool_install_performed"] is True
    assert attempt["digest_lookup_timed_out"] is True
    assert attempt["digest_pinned_crane_pull_timed_out"] is True
    assert attempt["image_tar_created"] is False
    assert attempt["image_load_performed"] is False
    assert attempt["blind_tag_docker_pull_repeated"] is False
    assert attempt["digest_pinned_docker_pull_repeated"] is False
    assert attempt["compose_started"] is False
    assert inventory["first_required_image_present_by_tag"] is False
    assert inventory["first_required_image_present_by_digest"] is False
    assert inventory["all_required_images_present"] is False
    assert readiness["trusted_registry_client_installed"] is True
    assert readiness["trusted_export_load_cache_path_attempted"] is True
    assert readiness["first_required_image_present"] is False
    assert readiness["one_live_parity_attempt_authorized"] is False


def test_crane_export_load_timeout_preserves_digest_and_runtime_gates():
    observation = build_acontext_crane_export_load_timeout_observation()
    runtime = observation["runtime_observation"]
    gates = observation["runtime_truth_gates"]

    assert runtime["pinned_image"]["manifest_digest"] == FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST
    assert [gate["gate"] for gate in gates] == [
        "trusted_registry_client_installed",
        "changed_cache_path_attempt_completed",
        "first_required_image_cached",
        "all_required_images_present",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert gates[0]["passed"] is True
    assert all(gate["passed"] is False for gate in gates[1:])
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)


def test_crane_export_load_timeout_preserves_blocked_claims():
    observation = build_acontext_crane_export_load_timeout_observation()

    safe = set(observation["claim_boundaries"]["safe_to_claim"])
    blocked = set(observation["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_BLOCKED_CLAIMS) <= blocked
    assert "crane_export_load_attempt_cached_first_required_image" in blocked
    assert "crane_export_load_attempt_started_compose_services" in blocked
    assert "crane_export_load_attempt_proved_runtime_parity" in blocked
    assert (
        "crane_export_load_attempt_authorizes_customer_copy_delivery_or_publication"
        in blocked
    )


def test_crane_export_load_timeout_refuses_source_that_promotes_live_parity():
    source = copy.deepcopy(build_acontext_7am_trusted_cache_path_probe())
    source["readiness"]["one_live_parity_attempt_authorized"] = True

    with pytest.raises(CityOpsContractError, match="must not authorize live parity"):
        build_acontext_crane_export_load_timeout_observation(
            trusted_cache_path_probe=source
        )


def test_crane_export_load_timeout_refuses_tar_creation_claim():
    source = build_acontext_7am_trusted_cache_path_probe()
    runtime = copy.deepcopy(read_fixture_observation()["runtime_observation"])
    runtime["changed_cache_path_attempt"]["image_tar_created"] = True

    with pytest.raises(CityOpsContractError, match="must not claim tar creation"):
        build_acontext_crane_export_load_timeout_observation(
            trusted_cache_path_probe=source,
            observation=runtime,
        )


def test_crane_export_load_timeout_write_and_load_temp_fixture(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_crane_export_load_timeout_observation(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME
    loaded = load_acontext_crane_export_load_timeout_observation(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM
    )


def test_crane_export_load_timeout_loader_rejects_drift(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_crane_export_load_timeout_observation(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["first_required_image_present"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_crane_export_load_timeout_observation(artifact_dir=tmp_path)


def _copy_probe_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME).exists()
