import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_parity_attempt_readiness_gate import (
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta_read_surface import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
)
from mcp_server.city_ops.acontext_prerequisite_activation_board import (
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
    build_acontext_prerequisite_activation_board,
)
from mcp_server.city_ops.acontext_prerequisite_recovery_attempt_log import (
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME,
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM,
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA,
    RECOVERY_ATTEMPT_BLOCKED_CLAIMS,
    build_acontext_prerequisite_recovery_attempt_log,
    load_acontext_prerequisite_recovery_attempt_log,
    write_acontext_prerequisite_recovery_attempt_log,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_log() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_prerequisite_recovery_attempt_log_matches_fixture():
    log = build_acontext_prerequisite_recovery_attempt_log()

    assert log == read_fixture_log()
    assert log["schema"] == ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA
    assert log["recovery_verdict"] == "recovery_attempt_logged_still_not_live_ready"
    assert ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM in log[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert log["readiness"]["recovery_attempt_log_landed"] is True
    assert log["readiness"]["docker_available"] is True
    assert log["readiness"]["dedicated_sdk_venv_imports_acontext"] is True
    assert log["readiness"]["active_runner_sdk_available"] is False
    assert log["readiness"]["compose_pull_started"] is True
    assert log["readiness"]["compose_pull_completed"] is False
    assert log["readiness"]["compose_services_started"] is False
    assert log["readiness"]["api_reachable_after_attempt"] is False
    assert log["readiness"]["dashboard_reachable_after_attempt"] is False
    assert log["readiness"]["ready_to_attempt_live_transport"] is False


def test_acontext_prerequisite_recovery_attempt_log_separates_assets_from_authorization():
    log = build_acontext_prerequisite_recovery_attempt_log()

    assets = log["recovery_cards"][0]
    assert assets["status"] == "partial_assets_present"
    assert assets["dedicated_sdk_venv_imports_acontext"] is True
    assert assets["active_runner_sdk_available"] is False
    assert assets["authorizes_live_attempt"] is False

    compose = log["recovery_cards"][1]
    assert compose["status"] == "attempted_not_completed"
    assert compose["compose_pull_started"] is True
    assert compose["compose_pull_completed"] is False
    assert compose["compose_services_started"] is False
    assert compose["authorizes_api_dashboard_claim"] is False

    reachability = log["recovery_cards"][2]
    assert reachability["status"] == "still_unreachable"
    assert reachability["authorizes_runtime_parity_claim"] is False


def test_acontext_prerequisite_recovery_attempt_log_preserves_sticky_blocked_claims():
    log = build_acontext_prerequisite_recovery_attempt_log()

    blocked = set(log["claim_boundaries"]["do_not_claim_yet"])
    assert set(RECOVERY_ATTEMPT_BLOCKED_CLAIMS) <= blocked
    assert not (set(log["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "acontext_services_started_by_recovery_attempt" in blocked
    assert "runtime_parity_proven_by_recovery_attempt" in blocked
    assert "worker_copyable_municipal_doctrine_ready_by_gate" in blocked


def test_acontext_prerequisite_recovery_attempt_log_refuses_ready_source_board():
    board = copy.deepcopy(build_acontext_prerequisite_activation_board())
    board["readiness"]["ready_to_attempt_live_transport"] = True

    with pytest.raises(CityOpsContractError, match="already-ready board"):
        build_acontext_prerequisite_recovery_attempt_log(activation_board=board)


def test_acontext_prerequisite_recovery_attempt_log_refuses_impossible_observation():
    observation = read_fixture_log()["recovery_observation"]
    observation["compose_services_started"] = True
    observation["compose_pull_completed"] = False

    with pytest.raises(CityOpsContractError, match="pull completion"):
        build_acontext_prerequisite_recovery_attempt_log(observation=observation)


def test_acontext_prerequisite_recovery_attempt_log_refuses_live_write_observation():
    observation = read_fixture_log()["recovery_observation"]
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live write"):
        build_acontext_prerequisite_recovery_attempt_log(observation=observation)


def test_acontext_prerequisite_recovery_attempt_log_refuses_readiness_promotion_on_load(
    tmp_path,
):
    _copy_log_sources(tmp_path)
    path = write_acontext_prerequisite_recovery_attempt_log(artifact_dir=tmp_path)
    log = json.loads(path.read_text(encoding="utf-8"))
    log["readiness"]["compose_services_started"] = True
    path.write_text(json.dumps(log), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_prerequisite_recovery_attempt_log(artifact_dir=tmp_path)


def test_acontext_prerequisite_recovery_attempt_log_write_and_load_temp_fixture(tmp_path):
    _copy_log_sources(tmp_path)
    path = write_acontext_prerequisite_recovery_attempt_log(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME
    loaded = load_acontext_prerequisite_recovery_attempt_log(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM
    )


def _copy_log_sources(tmp_path: Path) -> None:
    for filename in [
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
        ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME,
        ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
    ]:
        shutil.copy(PROOF_BLOCK_DIR / filename, tmp_path / filename)
