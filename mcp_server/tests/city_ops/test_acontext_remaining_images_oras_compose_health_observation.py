from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from mcp_server.city_ops.acontext_oras_oci_layout_cache_bridge import (
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME,
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM,
    build_acontext_oras_oci_layout_cache_bridge,
)
from mcp_server.city_ops.acontext_remaining_images_oras_compose_health_observation import (
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_BLOCKED_CLAIMS,
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME,
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM,
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCHEMA,
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_VERDICT,
    build_acontext_remaining_images_oras_compose_health,
    build_may30_0103_remaining_images_oras_compose_health_observation,
    load_acontext_remaining_images_oras_compose_health,
    write_acontext_remaining_images_oras_compose_health,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_remaining_images_oras_compose_health_matches_fixture_and_loader():
    artifact = build_acontext_remaining_images_oras_compose_health()

    assert artifact == read_fixture()
    assert load_acontext_remaining_images_oras_compose_health() == artifact
    assert artifact["schema"] == ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCHEMA
    assert artifact["observation_verdict"] == ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_VERDICT
    safe = artifact["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM in safe
    assert ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM in safe


def test_remaining_images_records_complete_required_image_inventory():
    artifact = build_acontext_remaining_images_oras_compose_health()
    runtime = artifact["runtime_observation"]
    inventory = runtime["image_inventory_after_attempt"]

    assert runtime["trusted_tool"]["tool"] == "oras"
    assert runtime["remaining_image_cache_attempt"]["attempted"] is True
    assert runtime["remaining_image_cache_attempt"]["platform"] == "linux/arm64"
    assert runtime["remaining_image_cache_attempt"]["oras_copy_failures"] == []
    assert runtime["remaining_image_cache_attempt"]["docker_load_failures"] == []
    assert runtime["remaining_image_cache_attempt"]["required_tag_failures"] == []
    assert inventory["present_required_image_names"] == REQUIRED_ACONTEXT_IMAGES
    assert inventory["missing_required_images"] == []
    assert inventory["all_required_images_present"] is True
    assert len(inventory["present_required_images"]) == len(REQUIRED_ACONTEXT_IMAGES)


def test_remaining_images_records_compose_and_local_health_without_live_parity():
    artifact = build_acontext_remaining_images_oras_compose_health()
    runtime = artifact["runtime_observation"]
    readiness = artifact["readiness"]

    assert runtime["compose_start"]["attempted"] is True
    assert runtime["compose_start"]["returncode"] == 0
    assert runtime["compose_start"]["services_started"] is True
    assert runtime["compose_service_health"]["unhealthy_services"] == []
    assert "acontext-server-api" in runtime["compose_service_health"]["healthy_services"]
    assert runtime["http_health_checks"]["api_health"]["status_code"] == 200
    assert runtime["http_health_checks"]["core_health"]["status_code"] == 200
    assert runtime["http_health_checks"]["ui_root"]["status_code"] == 307
    assert readiness["all_required_images_present"] is True
    assert readiness["compose_services_started"] is True
    assert readiness["acontext_api_health_reachable"] is True
    assert readiness["write_retrieve_contract_discovered"] is False
    assert readiness["live_acontext_write_performed"] is False
    assert readiness["live_acontext_retrieval_performed"] is False
    assert readiness["runtime_parity_proven"] is False


def test_remaining_images_runtime_truth_gates_stop_before_parity():
    artifact = build_acontext_remaining_images_oras_compose_health()
    gates = artifact["runtime_truth_gates"]

    assert [gate["gate"] for gate in gates] == [
        "all_required_images_present",
        "compose_services_started",
        "local_api_and_core_health",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert [gate["passed"] for gate in gates] == [True, True, True, False]
    assert all(gate["authorizes_customer_or_dispatch_claim"] is False for gate in gates)


def test_remaining_images_unblocks_superseded_source_claims_only():
    artifact = build_acontext_remaining_images_oras_compose_health()
    safe = set(artifact["claim_boundaries"]["safe_to_claim"])
    blocked = set(artifact["claim_boundaries"]["do_not_claim_yet"])

    assert safe.isdisjoint(blocked)
    assert set(ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_BLOCKED_CLAIMS) <= blocked
    assert "oras_oci_layout_cache_bridge_cached_all_required_images" not in blocked
    assert "oras_oci_layout_cache_bridge_started_compose_services" not in blocked
    assert "oras_oci_layout_cache_bridge_reached_acontext_api" not in blocked
    assert "remaining_images_oras_compose_health_completed_live_acontext_write" in blocked
    assert "remaining_images_oras_compose_health_proved_runtime_parity" in blocked
    assert "remaining_images_oras_compose_health_authorizes_queue_launch_or_dispatch" in blocked


def test_remaining_images_access_flags_remain_false():
    artifact = build_acontext_remaining_images_oras_compose_health()

    assert artifact["operator_guidance"]["not_customer_copy"] is True
    assert artifact["operator_guidance"]["not_worker_instruction"] is True
    assert all(value is False for value in artifact["access_flags"].values())


def test_remaining_images_refuses_source_without_partial_inventory_boundary():
    source = copy.deepcopy(build_acontext_oras_oci_layout_cache_bridge())
    source["readiness"]["all_required_images_present"] = True

    with pytest.raises(CityOpsContractError, match="partial image inventory"):
        build_acontext_remaining_images_oras_compose_health(oras_bridge=source)


def test_remaining_images_refuses_missing_required_image_observation():
    source = build_acontext_oras_oci_layout_cache_bridge()
    observation = copy.deepcopy(build_may30_0103_remaining_images_oras_compose_health_observation())
    observation["image_inventory_after_attempt"]["missing_required_images"] = ["redis:7.4"]
    observation["image_inventory_after_attempt"]["all_required_images_present"] = False

    with pytest.raises(CityOpsContractError, match="all required images"):
        build_acontext_remaining_images_oras_compose_health(
            oras_bridge=source,
            observation=observation,
        )


def test_remaining_images_refuses_live_parity_claim():
    source = build_acontext_oras_oci_layout_cache_bridge()
    observation = copy.deepcopy(build_may30_0103_remaining_images_oras_compose_health_observation())
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live write"):
        build_acontext_remaining_images_oras_compose_health(
            oras_bridge=source,
            observation=observation,
        )


def test_remaining_images_write_and_loader_rejects_drift(tmp_path):
    _copy_proof_block_sources(tmp_path)
    path = write_acontext_remaining_images_oras_compose_health(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME
    loaded = load_acontext_remaining_images_oras_compose_health(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM
    )

    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["runtime_parity_proven"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_remaining_images_oras_compose_health(artifact_dir=tmp_path)


def _copy_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME).exists()
