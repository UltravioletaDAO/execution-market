import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_compose_image_pull_attempt_log import (
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME,
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM,
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SCHEMA,
    COMPOSE_IMAGE_PULL_ATTEMPT_BLOCKED_CLAIMS,
    REQUIRED_ACONTEXT_IMAGES,
    build_acontext_compose_image_pull_attempt_log,
    build_may16_2304_compose_pull_attempt_observation,
    load_acontext_compose_image_pull_attempt_log,
)
from mcp_server.city_ops.acontext_runtime_memory_prerequisite_probe import (
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME,
    build_acontext_runtime_memory_prerequisite_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_attempt_log() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_compose_image_pull_attempt_log_matches_fixture():
    attempt_log = build_acontext_compose_image_pull_attempt_log()

    assert attempt_log == read_fixture_attempt_log()
    assert attempt_log["schema"] == ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SCHEMA
    assert attempt_log["attempt_verdict"] == "compose_image_pull_attempt_still_blocks_acontext_startup"
    assert ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM in attempt_log[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_compose_image_pull_attempt_log_preserves_image_inventory_blocker():
    attempt_log = build_acontext_compose_image_pull_attempt_log()
    inventory = attempt_log["image_inventory"]

    assert inventory["required_image_count"] == len(REQUIRED_ACONTEXT_IMAGES)
    assert inventory["present_required_images"] == ["pgvector/pgvector:pg16"]
    assert "redis:7.4" in inventory["missing_required_images"]
    assert "ghcr.io/memodb-io/acontext-api:latest" in inventory["missing_required_images"]
    assert inventory["all_required_images_present"] is False
    assert inventory["image_pull_blocker_remains"] is True


def test_compose_image_pull_attempt_log_readiness_never_authorizes_live_attempt():
    attempt_log = build_acontext_compose_image_pull_attempt_log()
    readiness = attempt_log["readiness"]

    assert readiness["pull_attempt_recorded"] is True
    assert readiness["compose_pull_completed"] is False
    assert readiness["all_required_images_present"] is False
    assert readiness["compose_services_started"] is False
    assert readiness["api_reachable_after_attempt"] is False
    assert readiness["dashboard_reachable_after_attempt"] is False
    assert readiness["readiness_gate_rebuilt_with_empty_blockers"] is False
    assert readiness["live_acontext_write_performed"] is False
    assert readiness["live_acontext_retrieval_performed"] is False


def test_compose_image_pull_attempt_log_sticky_blocked_claims():
    attempt_log = build_acontext_compose_image_pull_attempt_log()

    blocked = set(attempt_log["claim_boundaries"]["do_not_claim_yet"])
    assert set(COMPOSE_IMAGE_PULL_ATTEMPT_BLOCKED_CLAIMS) <= blocked
    assert not (set(attempt_log["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "runtime_parity_proven_by_attempt_log" in blocked
    assert "compose_image_pull_completed_by_attempt_log" in blocked


def test_compose_image_pull_attempt_log_refuses_completed_pull_observation():
    observation = build_may16_2304_compose_pull_attempt_observation()
    observation["pull_completed"] = True

    with pytest.raises(CityOpsContractError, match="completed compose pull"):
        build_acontext_compose_image_pull_attempt_log(observation=observation)


def test_compose_image_pull_attempt_log_refuses_new_image_promotion():
    observation = build_may16_2304_compose_pull_attempt_observation()
    observation["new_required_images_observed_after_attempt"] = ["redis:7.4"]

    with pytest.raises(CityOpsContractError, match="no new required images"):
        build_acontext_compose_image_pull_attempt_log(observation=observation)


def test_compose_image_pull_attempt_log_refuses_live_write_observation():
    observation = build_may16_2304_compose_pull_attempt_observation()
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live Acontext write"):
        build_acontext_compose_image_pull_attempt_log(observation=observation)


def test_compose_image_pull_attempt_log_refuses_readiness_promotion_on_load(tmp_path):
    source = build_acontext_runtime_memory_prerequisite_probe()
    (tmp_path / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    attempt_log = build_acontext_compose_image_pull_attempt_log(prerequisite_probe=source)
    path = tmp_path / ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME
    path.write_text(json.dumps(attempt_log), encoding="utf-8")
    attempt_log["readiness"]["all_required_images_present"] = True
    path.write_text(json.dumps(attempt_log), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_compose_image_pull_attempt_log(artifact_dir=tmp_path)


def test_compose_image_pull_attempt_log_loads_persisted_fixture():
    loaded = load_acontext_compose_image_pull_attempt_log()

    assert loaded["schema"] == ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM
    )
