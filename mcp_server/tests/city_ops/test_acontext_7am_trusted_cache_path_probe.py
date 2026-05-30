from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_7am_trusted_cache_path_probe import (
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_BLOCKED_CLAIMS,
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME,
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM,
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA,
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_VERDICT,
    EXPORT_LOAD_TOOLS,
    build_acontext_7am_trusted_cache_path_probe,
    load_acontext_7am_trusted_cache_path_probe,
    write_acontext_7am_trusted_cache_path_probe,
)
from mcp_server.city_ops.acontext_digest_pinned_pull_timeout_observation import (
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
    build_acontext_digest_pinned_pull_timeout_observation,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_probe() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_7am_trusted_cache_path_probe_matches_fixture_and_loader():
    probe = build_acontext_7am_trusted_cache_path_probe()

    assert probe == read_fixture_probe()
    assert load_acontext_7am_trusted_cache_path_probe() == probe
    assert probe["schema"] == ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA
    assert probe["observation_verdict"] == ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_VERDICT
    safe = probe["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM in safe
    assert ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM in safe


def test_7am_trusted_cache_path_probe_stops_without_export_load_tool():
    probe = build_acontext_7am_trusted_cache_path_probe()
    runtime = probe["runtime_observation"]
    tool_inventory = runtime["trusted_tool_inventory"]
    attempt = runtime["changed_cache_path_attempt"]
    inventory = runtime["image_inventory_after_probe"]

    assert [tool["tool"] for tool in tool_inventory["export_load_tools"]] == EXPORT_LOAD_TOOLS
    assert all(tool["available"] is False for tool in tool_inventory["export_load_tools"])
    assert tool_inventory["trusted_export_load_tool_available"] is False
    assert tool_inventory["metadata_only_tools"][0]["tool"] == "docker_buildx_imagetools"
    assert tool_inventory["metadata_only_tools"][0]["available"] is True
    assert tool_inventory["metadata_only_tools"][0]["export_load_capable_for_local_image_cache"] is False
    assert attempt["selected_path"] == "trusted_registry_client_export_load_path"
    assert attempt["attempted"] is False
    assert attempt["stop_reason"] == "no_installed_export_load_capable_trusted_registry_client"
    assert attempt["blind_tag_pull_repeated"] is False
    assert attempt["digest_pinned_docker_pull_repeated"] is False
    assert attempt["image_load_performed"] is False
    assert inventory["first_required_image_present_by_tag"] is False
    assert inventory["first_required_image_present_by_digest"] is False
    assert inventory["present_required_images"] == ["pgvector/pgvector:pg16"]


def test_7am_trusted_cache_path_probe_preserves_pinned_digest_and_blocks_runtime():
    probe = build_acontext_7am_trusted_cache_path_probe()
    runtime = probe["runtime_observation"]
    readiness = probe["readiness"]
    gates = probe["runtime_truth_gates"]

    assert runtime["pinned_image"]["manifest_digest"] == FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST
    assert [gate["gate"] for gate in gates] == [
        "digest_pinned_source_artifact",
        "trusted_export_load_tool_inventory",
        "changed_cache_path_attempt",
        "first_required_image_cached",
        "all_required_images_present",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert gates[0]["passed"] is True
    assert all(gate["passed"] is False for gate in gates[1:])
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)
    assert readiness["trusted_tool_inventory_checked"] is True
    assert readiness["trusted_export_load_tool_available"] is False
    assert readiness["trusted_export_load_cache_path_attempted"] is False
    assert readiness["first_required_image_present"] is False
    assert readiness["all_required_images_present"] is False
    assert readiness["compose_services_started"] is False
    assert readiness["acontext_api_reachable"] is False
    assert readiness["acontext_dashboard_reachable"] is False
    assert readiness["one_live_parity_attempt_authorized"] is False


def test_7am_trusted_cache_path_probe_preserves_blocked_claims():
    probe = build_acontext_7am_trusted_cache_path_probe()

    safe = set(probe["claim_boundaries"]["safe_to_claim"])
    blocked = set(probe["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_BLOCKED_CLAIMS) <= blocked
    assert "trusted_cache_path_probe_used_crane_oras_skopeo_or_regctl" in blocked
    assert "trusted_cache_path_probe_cached_first_required_image" in blocked
    assert "trusted_cache_path_probe_started_compose_services" in blocked
    assert "trusted_cache_path_probe_proved_runtime_parity" in blocked
    assert "trusted_cache_path_probe_authorizes_customer_copy_delivery_or_publication" in blocked


def test_7am_trusted_cache_path_probe_refuses_source_without_digest_lock():
    source = copy.deepcopy(build_acontext_digest_pinned_pull_timeout_observation())
    source["readiness"]["registry_manifest_digest_locked"] = False

    with pytest.raises(CityOpsContractError, match="source missing digest lock"):
        build_acontext_7am_trusted_cache_path_probe(digest_pinned_observation=source)


def test_7am_trusted_cache_path_probe_refuses_promoted_tool_availability():
    probe = copy.deepcopy(read_fixture_probe())
    source = build_acontext_digest_pinned_pull_timeout_observation()
    runtime = probe["runtime_observation"]
    runtime["trusted_tool_inventory"]["trusted_export_load_tool_available"] = True

    with pytest.raises(CityOpsContractError, match="must not claim export/load tool availability"):
        build_acontext_7am_trusted_cache_path_probe(
            digest_pinned_observation=source,
            observation=runtime,
        )


def test_7am_trusted_cache_path_probe_write_and_load_temp_fixture(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_7am_trusted_cache_path_probe(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME
    loaded = load_acontext_7am_trusted_cache_path_probe(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM
    )


def test_7am_trusted_cache_path_probe_loader_rejects_drift(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_7am_trusted_cache_path_probe(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["first_required_image_present"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_7am_trusted_cache_path_probe(artifact_dir=tmp_path)


def _copy_probe_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME).exists()
