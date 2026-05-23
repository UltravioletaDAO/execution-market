import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_compose_image_pull_attempt_log import (
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME,
    build_acontext_compose_image_pull_attempt_log,
)
from mcp_server.city_ops.acontext_docker_pull_path_diagnostic import (
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME,
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM,
    build_acontext_docker_pull_path_diagnostic,
)
from mcp_server.city_ops.acontext_individual_image_pull_timeout_probe import (
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME,
    build_acontext_individual_image_pull_timeout_probe,
)
from mcp_server.city_ops.acontext_registry_manifest_pull_stall_diagnostic import (
    ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME,
    build_acontext_registry_manifest_pull_stall_diagnostic,
)
from mcp_server.city_ops.acontext_runtime_memory_daemon_recheck import (
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM,
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA,
    DAEMON_RECHECK_BLOCKED_CLAIMS,
    build_acontext_runtime_memory_daemon_recheck,
    build_may23_0200_daemon_recheck_observation,
    load_acontext_runtime_memory_daemon_recheck,
    write_acontext_runtime_memory_daemon_recheck,
)
from mcp_server.city_ops.acontext_runtime_memory_prerequisite_probe import (
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME,
    build_acontext_runtime_memory_prerequisite_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_recheck() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_runtime_memory_daemon_recheck_matches_fixture():
    recheck = build_acontext_runtime_memory_daemon_recheck()

    assert recheck == read_fixture_recheck()
    assert recheck["schema"] == ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA
    assert recheck["recheck_verdict"] == (
        "docker_daemon_unavailable_runtime_memory_still_blocked"
    )
    assert ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM in recheck[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM in recheck[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_daemon_recheck_records_current_daemon_down_state_without_promotion():
    recheck = build_acontext_runtime_memory_daemon_recheck()
    summary = recheck["daemon_status_summary"]

    assert summary["docker_context"] == "desktop-linux"
    assert summary["docker_daemon_available"] is False
    assert summary["buildx_builder_available"] is False
    assert summary["daemon_unavailable_blocks_image_inventory"] is True
    assert summary["daemon_unavailable_blocks_compose_startup"] is True
    assert summary["daemon_unavailable_blocks_live_parity_attempt"] is True
    assert recheck["readiness"]["docker_daemon_available"] is False
    assert recheck["readiness"]["required_images_present"] is False
    assert recheck["readiness"]["runtime_parity_proven"] is False


def test_daemon_recheck_preserves_service_and_gate_blockers():
    recheck = build_acontext_runtime_memory_daemon_recheck()

    blockers = set(recheck["readiness"]["remaining_blockers"])
    assert "docker_daemon_socket_unavailable" in blockers
    assert "required_image_inventory_not_checkable" in blockers
    assert "local_acontext_api_unreachable" in blockers
    assert "local_acontext_dashboard_unreachable" in blockers
    assert "readiness_gate_not_rebuilt_empty" in blockers

    cards = {card["card"]: card for card in recheck["runtime_blocker_cards"]}
    assert cards["docker_daemon"]["status"] == "blocked_socket_unavailable"
    assert cards["buildx_and_inventory"]["status"] == "blocked_by_daemon_unavailable"
    assert cards["local_services"]["api_reachable"] is False
    assert cards["live_parity_gate"]["authorizes_live_attempt"] is False


def test_daemon_recheck_sticky_blocked_claims():
    recheck = build_acontext_runtime_memory_daemon_recheck()

    blocked = set(recheck["claim_boundaries"]["do_not_claim_yet"])
    assert set(DAEMON_RECHECK_BLOCKED_CLAIMS) <= blocked
    assert not (set(recheck["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "daemon_recheck_repaired_docker_socket" in blocked
    assert "daemon_recheck_authorized_live_parity_attempt" in blocked
    assert "daemon_recheck_proved_runtime_parity" in blocked


def test_daemon_recheck_refuses_unsanitized_observation():
    observation = build_may23_0200_daemon_recheck_observation()
    observation["sanitization_policy"]["include_tokens"] = True

    with pytest.raises(CityOpsContractError, match="include_tokens"):
        build_acontext_runtime_memory_daemon_recheck(observation=observation)


def test_daemon_recheck_refuses_daemon_available_observation():
    observation = build_may23_0200_daemon_recheck_observation()
    observation["docker"]["daemon_available"] = True

    with pytest.raises(CityOpsContractError, match="Docker daemon is unavailable"):
        build_acontext_runtime_memory_daemon_recheck(observation=observation)


def test_daemon_recheck_refuses_live_service_reachability():
    observation = build_may23_0200_daemon_recheck_observation()
    observation["api"]["reachable"] = True

    with pytest.raises(CityOpsContractError, match="reachable API"):
        build_acontext_runtime_memory_daemon_recheck(observation=observation)


def test_daemon_recheck_refuses_ready_source_diagnostic():
    source = copy.deepcopy(build_acontext_docker_pull_path_diagnostic())
    source["readiness"]["all_required_images_present"] = True

    with pytest.raises(CityOpsContractError, match="all_required_images_present"):
        build_acontext_runtime_memory_daemon_recheck(pull_path_diagnostic=source)


def test_daemon_recheck_write_and_load_temp_fixture(tmp_path):
    _copy_recheck_sources(tmp_path)
    path = write_acontext_runtime_memory_daemon_recheck(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME
    loaded = load_acontext_runtime_memory_daemon_recheck(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM
    )


def test_daemon_recheck_refuses_readiness_promotion_on_load(tmp_path):
    _copy_recheck_sources(tmp_path)
    path = write_acontext_runtime_memory_daemon_recheck(artifact_dir=tmp_path)
    recheck = json.loads(path.read_text(encoding="utf-8"))
    recheck["readiness"]["runtime_parity_proven"] = True
    path.write_text(json.dumps(recheck), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_runtime_memory_daemon_recheck(artifact_dir=tmp_path)


def _copy_recheck_sources(tmp_path: Path) -> None:
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
    docker_diagnostic = build_acontext_docker_pull_path_diagnostic(
        registry_diagnostic=registry
    )
    (tmp_path / ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME).write_text(
        json.dumps(docker_diagnostic), encoding="utf-8"
    )
