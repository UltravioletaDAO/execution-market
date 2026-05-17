import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_runtime_memory_prerequisite_probe import (
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM,
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SCHEMA,
    RUNTIME_MEMORY_PREREQUISITE_PROBE_BLOCKED_CLAIMS,
    build_acontext_runtime_memory_prerequisite_probe,
    build_may16_2201_runtime_memory_prerequisite_observation,
    load_acontext_runtime_memory_prerequisite_probe,
    write_acontext_runtime_memory_prerequisite_probe,
)
from mcp_server.city_ops.acontext_runtime_memory_preflight_rerun import (
    build_acontext_runtime_memory_preflight_rerun,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_probe() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_runtime_memory_prerequisite_probe_matches_fixture():
    probe = build_acontext_runtime_memory_prerequisite_probe()

    assert probe == read_fixture_probe()
    assert probe["schema"] == ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SCHEMA
    assert probe["probe_verdict"] == "runtime_memory_prerequisites_still_block_live_parity"
    assert ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM in probe[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert probe["readiness"]["ready_to_attempt_live_transport"] is False


def test_runtime_memory_prerequisite_probe_records_precise_remaining_blockers():
    probe = build_acontext_runtime_memory_prerequisite_probe()

    assert probe["readiness"]["remaining_blockers"] == [
        "acontext_cli_not_on_path",
        "default_active_runner_acontext_import_missing",
        "compose_image_pull_not_completed",
        "acontext_compose_services_not_started",
        "local_acontext_api_unreachable",
        "local_acontext_dashboard_unreachable",
        "readiness_gate_not_rebuilt_empty",
    ]
    assert probe["readiness"]["dedicated_venv_imports_acontext"] is True
    assert probe["readiness"]["default_active_runner_sdk_import_ready"] is False
    assert probe["readiness"]["compose_pull_completed"] is False
    assert probe["readiness"]["api_reachable_after_probe"] is False
    assert probe["readiness"]["dashboard_reachable_after_probe"] is False


def test_runtime_memory_prerequisite_probe_cards_do_not_authorize_live_attempt():
    probe = build_acontext_runtime_memory_prerequisite_probe()

    cards = {card["card_id"]: card for card in probe["prerequisite_cards"]}
    assert cards["docker_and_compose"]["status"] == "available_but_pull_not_completed"
    assert cards["cli_and_sdk"]["status"] == (
        "explicit_sdk_available_default_runner_and_cli_blocked"
    )
    assert cards["localhost_reachability"]["status"] == "api_and_dashboard_unreachable"
    assert cards["live_parity_gate"]["status"] == "not_rebuilt_empty_not_authorized"
    assert all(card["authorizes_live_attempt"] is False for card in cards.values())


def test_runtime_memory_prerequisite_probe_preserves_sticky_blocked_claims():
    probe = build_acontext_runtime_memory_prerequisite_probe()

    blocked = set(probe["claim_boundaries"]["do_not_claim_yet"])
    assert set(RUNTIME_MEMORY_PREREQUISITE_PROBE_BLOCKED_CLAIMS) <= blocked
    assert not (set(probe["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "runtime_parity_proven_by_runtime_memory_prerequisite_probe" in blocked
    assert "live_acontext_write_completed_by_runtime_memory_prerequisite_probe" in blocked


def test_runtime_memory_prerequisite_probe_refuses_live_write_observation():
    observation = build_may16_2201_runtime_memory_prerequisite_observation()
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="cannot record live write"):
        build_acontext_runtime_memory_prerequisite_probe(observation=observation)


def test_runtime_memory_prerequisite_probe_refuses_service_reachability_without_startup():
    observation = build_may16_2201_runtime_memory_prerequisite_observation()
    observation["api"]["reachable"] = True

    with pytest.raises(CityOpsContractError, match="API reachability requires"):
        build_acontext_runtime_memory_prerequisite_probe(observation=observation)


def test_runtime_memory_prerequisite_probe_refuses_readiness_promotion_on_load(tmp_path):
    source = build_acontext_runtime_memory_preflight_rerun()
    probe = build_acontext_runtime_memory_prerequisite_probe(runtime_rerun=source)
    path = tmp_path / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME
    path.write_text(json.dumps(probe), encoding="utf-8")
    probe["readiness"]["ready_to_attempt_live_transport"] = True
    path.write_text(json.dumps(probe), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_runtime_memory_prerequisite_probe(artifact_dir=tmp_path)


def test_runtime_memory_prerequisite_probe_write_and_load_temp_fixture(tmp_path):
    source = build_acontext_runtime_memory_preflight_rerun()
    probe = build_acontext_runtime_memory_prerequisite_probe(runtime_rerun=source)
    path = tmp_path / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME
    path.write_text(json.dumps(probe), encoding="utf-8")

    assert path.name == ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME
    loaded = load_acontext_runtime_memory_prerequisite_probe(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM
    )
