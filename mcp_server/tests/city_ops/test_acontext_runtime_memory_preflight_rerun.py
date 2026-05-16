import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_runtime_memory_preflight_rerun import (
    ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM,
    ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA,
    RUNTIME_MEMORY_PREFLIGHT_RERUN_BLOCKED_CLAIMS,
    build_acontext_runtime_memory_preflight_rerun,
    build_may16_7am_compose_startup_observation,
    build_may16_7am_runtime_memory_preflight_probe,
    load_acontext_runtime_memory_preflight_rerun,
    write_acontext_runtime_memory_preflight_rerun,
)
from mcp_server.city_ops.acontext_live_preflight import build_acontext_live_preflight_result
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_rerun() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_runtime_memory_preflight_rerun_matches_fixture():
    rerun = build_acontext_runtime_memory_preflight_rerun()

    assert rerun == read_fixture_rerun()
    assert rerun["schema"] == ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA
    assert rerun["rerun_verdict"] == (
        "runtime_memory_preflight_reran_still_blocked_by_local_services"
    )
    assert ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM in rerun[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert rerun["readiness"]["active_runner_can_import_acontext_via_explicit_venv"] is True
    assert rerun["readiness"]["acontext_python_sdk_available"] is True
    assert rerun["readiness"]["ready_to_attempt_live_transport"] is False


def test_acontext_runtime_memory_preflight_rerun_preserves_service_blockers():
    rerun = build_acontext_runtime_memory_preflight_rerun()

    assert rerun["current_blockers"] == [
        "local_acontext_api_unreachable",
        "local_acontext_dashboard_unreachable",
    ]
    assert rerun["readiness"]["remaining_blockers"] == rerun["current_blockers"]
    assert rerun["readiness"]["preflight_rebuilt_with_empty_blockers"] is False
    assert rerun["readiness"]["live_acontext_write_performed"] is False
    assert rerun["readiness"]["live_acontext_retrieval_performed"] is False


def test_acontext_runtime_memory_preflight_rerun_runner_bridge_does_not_authorize_live_parity():
    rerun = build_acontext_runtime_memory_preflight_rerun()
    bridge = rerun["runner_bridge"]

    assert bridge["active_runner_importable_without_bridge"] is False
    assert bridge["explicit_venv_consulted"] is True
    assert bridge["active_runner_can_import_acontext_via_explicit_venv"] is True
    assert bridge["authorizes_live_write"] is False
    assert bridge["authorizes_live_retrieve"] is False
    assert bridge["authorizes_runtime_parity_claim"] is False


def test_acontext_runtime_memory_preflight_rerun_preserves_sticky_blocked_claims():
    rerun = build_acontext_runtime_memory_preflight_rerun()

    blocked = set(rerun["claim_boundaries"]["do_not_claim_yet"])
    assert set(RUNTIME_MEMORY_PREFLIGHT_RERUN_BLOCKED_CLAIMS) <= blocked
    assert not (set(rerun["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "runtime_parity_proven_by_runtime_memory_rerun" in blocked
    assert "exact_gps_or_metadata_exposure_allowed_by_runtime_memory_rerun" in blocked
    assert "worker_copyable_municipal_doctrine_ready_by_runtime_memory_rerun" in blocked


def test_acontext_runtime_memory_preflight_rerun_refuses_ready_preflight():
    probe = build_may16_7am_runtime_memory_preflight_probe()
    probe["api"].update({"reachable": True, "status_code": 200, "error": None})
    probe["dashboard"].update({"reachable": True, "status_code": 200, "error": None})
    preflight = build_acontext_live_preflight_result(probe=probe)

    with pytest.raises(CityOpsContractError, match="cannot replace live parity pass"):
        build_acontext_runtime_memory_preflight_rerun(preflight=preflight)


def test_acontext_runtime_memory_preflight_rerun_refuses_missing_sdk_bridge():
    probe = build_may16_7am_runtime_memory_preflight_probe()
    probe["python_sdk"].update({"available": False, "import_mode": "missing"})
    preflight = build_acontext_live_preflight_result(probe=probe)

    with pytest.raises(CityOpsContractError, match="requires explicit SDK bridge progress"):
        build_acontext_runtime_memory_preflight_rerun(preflight=preflight)


def test_acontext_runtime_memory_preflight_rerun_refuses_settled_compose_claim():
    observation = build_may16_7am_compose_startup_observation()
    observation["compose_up_command_settled"] = True

    with pytest.raises(CityOpsContractError, match="compose_up_command_settled"):
        build_acontext_runtime_memory_preflight_rerun(compose_observation=observation)


def test_acontext_runtime_memory_preflight_rerun_refuses_readiness_promotion_on_load(
    tmp_path,
):
    preflight = build_acontext_live_preflight_result(
        probe=build_may16_7am_runtime_memory_preflight_probe()
    )
    path = write_acontext_runtime_memory_preflight_rerun(
        artifact_dir=tmp_path,
        preflight=preflight,
    )
    rerun = json.loads(path.read_text(encoding="utf-8"))
    rerun["readiness"]["ready_to_attempt_live_transport"] = True
    path.write_text(json.dumps(rerun), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_runtime_memory_preflight_rerun(artifact_dir=tmp_path)


def test_acontext_runtime_memory_preflight_rerun_write_and_load_temp_fixture(tmp_path):
    preflight = build_acontext_live_preflight_result(
        probe=build_may16_7am_runtime_memory_preflight_probe()
    )
    path = write_acontext_runtime_memory_preflight_rerun(
        artifact_dir=tmp_path,
        preflight=preflight,
    )

    assert path.name == ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME
    loaded = load_acontext_runtime_memory_preflight_rerun(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM
    )
