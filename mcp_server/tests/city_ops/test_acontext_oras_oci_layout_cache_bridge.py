from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_crane_export_load_timeout_observation import (
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    build_acontext_crane_export_load_timeout_observation,
)
from mcp_server.city_ops.acontext_digest_pinned_pull_timeout_observation import (
    FIRST_REQUIRED_IMAGE,
    FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
)
from mcp_server.city_ops.acontext_oras_oci_layout_cache_bridge import (
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_BLOCKED_CLAIMS,
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME,
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM,
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCHEMA,
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_VERDICT,
    build_acontext_oras_oci_layout_cache_bridge,
    load_acontext_oras_oci_layout_cache_bridge,
    write_acontext_oras_oci_layout_cache_bridge,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_bridge() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_oras_oci_layout_cache_bridge_matches_fixture_and_loader():
    bridge = build_acontext_oras_oci_layout_cache_bridge()

    assert bridge == read_fixture_bridge()
    assert load_acontext_oras_oci_layout_cache_bridge() == bridge
    assert bridge["schema"] == ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCHEMA
    assert bridge["observation_verdict"] == ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_VERDICT
    safe = bridge["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM in safe
    assert ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM in safe


def test_oras_bridge_records_different_acquisition_path_and_first_image_present():
    bridge = build_acontext_oras_oci_layout_cache_bridge()
    runtime = bridge["runtime_observation"]
    attempt = runtime["changed_cache_path_attempt"]
    inventory = runtime["image_inventory_after_attempt"]
    readiness = bridge["readiness"]

    assert runtime["trusted_tool"] == {
        "tool": "oras",
        "available": True,
        "path": "/opt/homebrew/bin/oras",
        "version": "1.3.2+Homebrew",
        "install_source": "Homebrew formula oras",
        "oci_layout_capable_for_local_image_cache": True,
    }
    assert attempt["selected_path"] == "trusted_oras_oci_layout_export_load_path"
    assert attempt["manifest_digest_matches_expected"] is True
    assert attempt["oras_copy_to_oci_layout_attempted"] is True
    assert attempt["oci_layout_created"] is True
    assert attempt["oci_layout_archive_created"] is True
    assert attempt["docker_load_attempted"] is True
    assert attempt["docker_tag_performed"] is True
    assert attempt["blind_tag_docker_pull_repeated"] is False
    assert attempt["digest_pinned_docker_pull_repeated"] is False
    assert attempt["crane_path_repeated"] is False
    assert attempt["compose_started"] is False
    assert inventory["first_required_image_present_by_tag"] is True
    assert inventory["first_required_image_local_id"] == FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST
    assert FIRST_REQUIRED_IMAGE in inventory["present_required_images"]
    assert readiness["first_required_image_present"] is True
    assert readiness["all_required_images_present"] is False
    assert readiness["one_live_parity_attempt_authorized"] is False


def test_oras_bridge_records_direct_pull_limitation_and_layout_copy_success():
    bridge = build_acontext_oras_oci_layout_cache_bridge()
    attempt = bridge["runtime_observation"]["changed_cache_path_attempt"]

    assert attempt["direct_oras_pull_attempted"] is True
    assert attempt["direct_oras_pull_returncode"] == 0
    assert attempt["direct_oras_pull_downloaded_layers"] is False
    assert attempt["direct_oras_pull_file_count"] == 0
    assert "oras copy --to-oci-layout" in attempt["direct_oras_pull_stdout_note"]
    assert attempt["oras_copy_returncode"] == 0
    assert attempt["oci_layout_file_count"] == 14
    assert attempt["oci_layout_total_size_bytes"] == 75494698
    assert attempt["docker_load_returncode"] == 0


def test_oras_bridge_preserves_remaining_runtime_gates():
    bridge = build_acontext_oras_oci_layout_cache_bridge()
    gates = bridge["runtime_truth_gates"]

    assert [gate["gate"] for gate in gates] == [
        "alternate_trusted_registry_client_installed",
        "platform_manifest_resolved",
        "oci_layout_export_created",
        "first_required_image_loaded_and_tagged",
        "all_required_images_present",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert [gate["passed"] for gate in gates] == [True, True, True, True, False, False]
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)


def test_oras_bridge_preserves_blocked_claims_after_partial_unblock():
    bridge = build_acontext_oras_oci_layout_cache_bridge()

    safe = set(bridge["claim_boundaries"]["safe_to_claim"])
    blocked = set(bridge["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_BLOCKED_CLAIMS) <= blocked
    assert "oras_oci_layout_cache_bridge_cached_all_required_images" in blocked
    assert "oras_oci_layout_cache_bridge_started_compose_services" in blocked
    assert "oras_oci_layout_cache_bridge_proved_runtime_parity" in blocked
    assert (
        "oras_oci_layout_cache_bridge_authorizes_customer_copy_delivery_or_publication"
        in blocked
    )


def test_oras_bridge_refuses_source_that_already_promotes_live_parity():
    source = copy.deepcopy(build_acontext_crane_export_load_timeout_observation())
    source["readiness"]["one_live_parity_attempt_authorized"] = True

    with pytest.raises(CityOpsContractError, match="must not authorize live parity"):
        build_acontext_oras_oci_layout_cache_bridge(crane_timeout_observation=source)


def test_oras_bridge_refuses_missing_first_image_claim():
    source = build_acontext_crane_export_load_timeout_observation()
    runtime = copy.deepcopy(read_fixture_bridge()["runtime_observation"])
    runtime["image_inventory_after_attempt"]["first_required_image_present_by_tag"] = False

    with pytest.raises(CityOpsContractError, match="must prove first image"):
        build_acontext_oras_oci_layout_cache_bridge(
            crane_timeout_observation=source,
            observation=runtime,
        )


def test_oras_bridge_refuses_compose_start_claim():
    source = build_acontext_crane_export_load_timeout_observation()
    runtime = copy.deepcopy(read_fixture_bridge()["runtime_observation"])
    runtime["changed_cache_path_attempt"]["compose_started"] = True

    with pytest.raises(CityOpsContractError, match="compose_started"):
        build_acontext_oras_oci_layout_cache_bridge(
            crane_timeout_observation=source,
            observation=runtime,
        )


def test_oras_bridge_write_and_load_temp_fixture(tmp_path):
    _copy_bridge_sources(tmp_path)
    path = write_acontext_oras_oci_layout_cache_bridge(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME
    loaded = load_acontext_oras_oci_layout_cache_bridge(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM
    )


def test_oras_bridge_loader_rejects_drift(tmp_path):
    _copy_bridge_sources(tmp_path)
    path = write_acontext_oras_oci_layout_cache_bridge(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["all_required_images_present"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_oras_oci_layout_cache_bridge(artifact_dir=tmp_path)


def _copy_bridge_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME).exists()
