import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_individual_image_pull_timeout_probe import (
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME,
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM,
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SCHEMA,
    INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_BLOCKED_CLAIMS,
    build_acontext_individual_image_pull_timeout_probe,
    build_may17_0002_individual_pull_probe_observation,
    load_acontext_individual_image_pull_timeout_probe,
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


def read_fixture_probe() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_individual_image_pull_timeout_probe_matches_fixture():
    probe = build_acontext_individual_image_pull_timeout_probe()

    assert probe == read_fixture_probe()
    assert probe["schema"] == ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SCHEMA
    assert probe["probe_verdict"] == "individual_image_pull_probe_still_blocks_acontext_startup"
    assert ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM in probe[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_individual_image_pull_timeout_probe_records_first_image_timeout():
    probe = build_acontext_individual_image_pull_timeout_probe()
    progress = probe["pull_progress_summary"]

    assert progress["attempted_image_count"] == 2
    assert progress["successful_pull_count"] == 0
    assert progress["timed_out_images"] == ["ghcr.io/memodb-io/acontext-ui:latest"]
    assert progress["operator_aborted_images"] == ["chrislusf/seaweedfs:4.02"]
    assert progress["all_required_images_attempted"] is False
    assert progress["per_image_pull_blocker_remains"] is True


def test_individual_image_pull_timeout_probe_registry_reachability_does_not_promote_readiness():
    probe = build_acontext_individual_image_pull_timeout_probe()
    registry = probe["registry_reachability_summary"]
    readiness = probe["readiness"]

    assert registry["all_registry_endpoints_reachable_by_http"] is True
    assert registry["reachability_is_not_pull_success"] is True
    assert registry["image_availability_proven"] is False
    assert registry["pull_success_proven"] is False
    assert readiness["first_required_image_pulled"] is False
    assert readiness["all_required_images_present"] is False
    assert readiness["compose_services_started"] is False
    assert readiness["readiness_gate_rebuilt_with_empty_blockers"] is False


def test_individual_image_pull_timeout_probe_preserves_inventory_blocker():
    probe = build_acontext_individual_image_pull_timeout_probe()
    inventory = probe["image_inventory"]

    assert inventory["present_required_images"] == ["pgvector/pgvector:pg16"]
    assert "ghcr.io/memodb-io/acontext-ui:latest" in inventory["missing_required_images"]
    assert "redis:7.4" in inventory["missing_required_images"]
    assert inventory["missing_required_image_count"] == 8
    assert inventory["all_required_images_present"] is False


def test_individual_image_pull_timeout_probe_sticky_blocked_claims():
    probe = build_acontext_individual_image_pull_timeout_probe()

    blocked = set(probe["claim_boundaries"]["do_not_claim_yet"])
    assert set(INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_BLOCKED_CLAIMS) <= blocked
    assert not (set(probe["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "all_required_images_present_by_individual_probe" in blocked
    assert "runtime_parity_proven_by_individual_probe" in blocked


def test_individual_image_pull_timeout_probe_refuses_successful_first_pull():
    observation = build_may17_0002_individual_pull_probe_observation()
    observation["pull_results"][0]["timed_out"] = False
    observation["pull_results"][0]["pulled_or_present"] = True

    with pytest.raises(CityOpsContractError, match="first individual pull"):
        build_acontext_individual_image_pull_timeout_probe(observation=observation)


def test_individual_image_pull_timeout_probe_refuses_new_image_promotion():
    observation = build_may17_0002_individual_pull_probe_observation()
    observation["new_required_images_observed_after_probe"] = ["redis:7.4"]

    with pytest.raises(CityOpsContractError, match="no new required images"):
        build_acontext_individual_image_pull_timeout_probe(observation=observation)


def test_individual_image_pull_timeout_probe_refuses_live_write_observation():
    observation = build_may17_0002_individual_pull_probe_observation()
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live Acontext write"):
        build_acontext_individual_image_pull_timeout_probe(observation=observation)


def test_individual_image_pull_timeout_probe_loads_persisted_fixture():
    loaded = load_acontext_individual_image_pull_timeout_probe()

    assert loaded["schema"] == ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM
    )


def test_individual_image_pull_timeout_probe_refuses_readiness_promotion_on_load(tmp_path):
    prerequisite = build_acontext_runtime_memory_prerequisite_probe()
    (tmp_path / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME).write_text(
        json.dumps(prerequisite), encoding="utf-8"
    )
    source = build_acontext_compose_image_pull_attempt_log(prerequisite_probe=prerequisite)
    (tmp_path / ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    probe = build_acontext_individual_image_pull_timeout_probe(compose_attempt_log=source)
    path = tmp_path / ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME
    path.write_text(json.dumps(probe), encoding="utf-8")
    probe["readiness"]["all_required_images_present"] = True
    path.write_text(json.dumps(probe), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_individual_image_pull_timeout_probe(artifact_dir=tmp_path)
