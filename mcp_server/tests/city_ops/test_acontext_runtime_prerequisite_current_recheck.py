"""Tests for the current Acontext runtime prerequisite recheck."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from mcp_server.city_ops.acontext_operator_activation_no_answer_pause_ledger import (
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM,
    build_acontext_operator_activation_no_answer_pause_ledger,
)
from mcp_server.city_ops.acontext_runtime_prerequisite_current_recheck import (
    ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_FILENAME,
    ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SAFE_CLAIM,
    ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SCHEMA,
    ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_VERDICT,
    RUNTIME_PREREQUISITE_CURRENT_RECHECK_BLOCKED_CLAIMS,
    build_acontext_runtime_prerequisite_current_recheck,
    build_june04_0005_runtime_prerequisite_observation,
    load_acontext_runtime_prerequisite_current_recheck,
    write_acontext_runtime_prerequisite_current_recheck,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME).exists()


def _read_fixture() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_current_recheck_matches_fixture_and_loader() -> None:
    packet = build_acontext_runtime_prerequisite_current_recheck()

    assert packet == _read_fixture()
    assert load_acontext_runtime_prerequisite_current_recheck() == packet
    assert packet["schema"] == ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SCHEMA
    assert packet["status_verdict"] == ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_VERDICT
    assert ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_current_recheck_records_daemon_unreachable_without_runtime_promotion() -> None:
    packet = build_acontext_runtime_prerequisite_current_recheck()
    summary = packet["runtime_prerequisite_recheck"]
    observation = packet["runtime_observation"]

    assert summary["read_only"] is True
    assert summary["current_fact"] == "docker_daemon_unreachable_current_runtime_reverification_blocked"
    assert summary["docker_context_active"] == "desktop-linux"
    assert summary["docker_daemon_available"] is False
    assert summary["current_required_image_inventory_verified"] is False
    assert summary["current_container_inventory_verified"] is False
    assert summary["current_local_api_reachable"] is False
    assert summary["current_local_core_reachable"] is False
    assert summary["current_local_ui_reachable"] is False
    assert summary["runtime_parity_proven"] is False
    assert observation["required_image_inventory"]["required_images_known_from_code"] == REQUIRED_ACONTEXT_IMAGES


def test_current_recheck_preserves_no_answer_hold_state() -> None:
    packet = build_acontext_runtime_prerequisite_current_recheck()
    summary = packet["runtime_prerequisite_recheck"]
    readiness = packet["readiness"]

    assert summary["source_no_answer_state_preserved"] is True
    assert summary["explicit_operator_answer_present"] is False
    assert summary["operator_approval_record_present"] is False
    assert summary["effective_decision"] == "hold_no_runtime_mutation"
    assert readiness["operator_answer_recorded"] is False
    assert readiness["operator_approval_recorded"] is False
    assert readiness["runtime_memory_answer_record_authorized"] is False
    assert readiness["compose_startup_authorized"] is False
    assert readiness["live_acontext_write_authorized"] is False
    assert readiness["runtime_adapter_registration_authorized"] is False


def test_current_recheck_keeps_runtime_and_external_surfaces_blocked() -> None:
    packet = build_acontext_runtime_prerequisite_current_recheck()

    assert packet["operator_guidance"]["records_no_answer"] is True
    assert packet["operator_guidance"]["records_no_approval"] is True
    assert packet["operator_guidance"]["not_customer_copy"] is True
    assert packet["operator_guidance"]["not_worker_instruction"] is True
    assert packet["operator_guidance"]["not_dashboard_spec"] is True
    assert all(value is False for value in packet["access_flags"].values())
    assert "runtime parity" in packet["operator_guidance"]["stop_line"]
    assert "not an approval" in packet["operator_guidance"]["stop_line"]


def test_current_recheck_preserves_stopped_project_firewall() -> None:
    packet = build_acontext_runtime_prerequisite_current_recheck()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_current_recheck_preserves_blocked_claim_boundaries() -> None:
    packet = build_acontext_runtime_prerequisite_current_recheck()
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    safe = set(packet["claim_boundaries"]["safe_to_claim"])

    assert set(RUNTIME_PREREQUISITE_CURRENT_RECHECK_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "started_docker_desktop",
        "verified_current_required_image_inventory",
        "started_compose_services",
        "reached_current_acontext_api",
        "completed_live_acontext_write",
        "completed_live_acontext_retrieval",
        "proved_runtime_parity",
        "runtime_adapter_registration",
        "irc_session_manager_mutation",
        "customer_public_worker_surface",
        "catalog_pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_context",
        "worker_copyable_doctrine",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_current_recheck_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_runtime_prerequisite_current_recheck(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_FILENAME
    loaded = load_acontext_runtime_prerequisite_current_recheck(artifact_dir=tmp_path)
    assert loaded == json.loads(path.read_text(encoding="utf-8"))


def test_current_recheck_refuses_unsanitized_observation() -> None:
    observation = build_june04_0005_runtime_prerequisite_observation()
    observation["sanitization_policy"]["include_tokens"] = True

    with pytest.raises(CityOpsContractError, match="include_tokens"):
        build_acontext_runtime_prerequisite_current_recheck(observation=observation)


def test_current_recheck_refuses_daemon_available_observation() -> None:
    observation = build_june04_0005_runtime_prerequisite_observation()
    observation["docker_daemon"]["available"] = True

    with pytest.raises(CityOpsContractError, match="Docker daemon unavailable"):
        build_acontext_runtime_prerequisite_current_recheck(observation=observation)


def test_current_recheck_refuses_live_service_reachability() -> None:
    observation = build_june04_0005_runtime_prerequisite_observation()
    observation["local_http_checks"]["api_health"]["reachable"] = True

    with pytest.raises(CityOpsContractError, match="unexpectedly reached api_health"):
        build_acontext_runtime_prerequisite_current_recheck(observation=observation)


def test_current_recheck_refuses_source_with_operator_answer() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_no_answer_pause_ledger())
    source["no_answer_pause_ledger"]["explicit_operator_answer_present"] = True

    with pytest.raises(CityOpsContractError, match="operator answer"):
        build_acontext_runtime_prerequisite_current_recheck(pause_ledger=source)


def test_current_recheck_loader_rejects_runtime_promotion(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_runtime_prerequisite_current_recheck(artifact_dir=tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["readiness"]["runtime_parity_proven"] = True
    path.write_text(json.dumps(packet), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="runtime_parity_proven"):
        load_acontext_runtime_prerequisite_current_recheck(artifact_dir=tmp_path)
