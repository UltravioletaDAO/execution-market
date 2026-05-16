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
)
from mcp_server.city_ops.acontext_prerequisite_recovery_attempt_log import (
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME,
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM,
    build_acontext_prerequisite_recovery_attempt_log,
)
from mcp_server.city_ops.acontext_explicit_venv_preflight_rerun import (
    ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_FILENAME,
    ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SAFE_CLAIM,
    ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SCHEMA,
    EXPLICIT_VENV_PREFLIGHT_RERUN_BLOCKED_CLAIMS,
    build_acontext_explicit_venv_preflight_rerun,
    load_acontext_explicit_venv_preflight_rerun,
    write_acontext_explicit_venv_preflight_rerun,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_rerun() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_explicit_venv_preflight_rerun_matches_fixture():
    rerun = build_acontext_explicit_venv_preflight_rerun()

    assert rerun == read_fixture_rerun()
    assert rerun["schema"] == ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SCHEMA
    assert rerun["rerun_verdict"] == (
        "explicit_venv_preflight_rerun_logged_still_not_live_ready"
    )
    assert ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM in rerun[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SAFE_CLAIM in rerun[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert rerun["readiness"]["explicit_venv_preflight_rerun_landed"] is True
    assert rerun["readiness"]["explicit_runner_sdk_available"] is True
    assert rerun["readiness"]["active_runner_sdk_available"] is False
    assert rerun["readiness"]["ready_to_attempt_live_transport"] is False


def test_acontext_explicit_venv_preflight_rerun_separates_runner_progress_from_authorization():
    rerun = build_acontext_explicit_venv_preflight_rerun()

    decision = rerun["runner_path_decision"]
    assert decision["explicit_venv_status"] == "available_for_read_only_preflight_only"
    assert decision["explicit_runner_authorizes_live_write"] is False
    assert decision["explicit_runner_authorizes_live_retrieve"] is False

    runner_card = rerun["preflight_cards"][0]
    assert runner_card["status"] == "explicit_venv_available_active_runner_blocked"
    assert runner_card["explicit_runner_sdk_available"] is True
    assert runner_card["active_runner_sdk_available"] is False
    assert runner_card["authorizes_live_attempt"] is False


def test_acontext_explicit_venv_preflight_rerun_preserves_compose_and_reachability_blockers():
    rerun = build_acontext_explicit_venv_preflight_rerun()

    blockers = set(rerun["readiness"]["blockers"])
    assert "compose_pull_not_settled" in blockers
    assert "acontext_compose_services_not_started" in blockers
    assert "local_acontext_api_unreachable" in blockers
    assert "local_acontext_dashboard_unreachable" in blockers
    assert "active_runner_acontext_sdk_missing_or_explicit_venv_required" in blockers

    compose_card = rerun["preflight_cards"][1]
    assert compose_card["compose_pull_command_started"] is True
    assert compose_card["compose_pull_settled"] is False
    assert compose_card["compose_services_started"] is False

    reachability_card = rerun["preflight_cards"][2]
    assert reachability_card["local_acontext_api_reachable"] is False
    assert reachability_card["local_acontext_dashboard_reachable"] is False


def test_acontext_explicit_venv_preflight_rerun_preserves_sticky_blocked_claims():
    rerun = build_acontext_explicit_venv_preflight_rerun()

    blocked = set(rerun["claim_boundaries"]["do_not_claim_yet"])
    assert set(EXPLICIT_VENV_PREFLIGHT_RERUN_BLOCKED_CLAIMS) <= blocked
    assert not (set(rerun["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "acontext_live_parity_attempt_authorized_by_explicit_venv_rerun" in blocked
    assert "runtime_parity_proven_by_explicit_venv_rerun" in blocked
    assert "worker_copyable_municipal_doctrine_ready_by_gate" in blocked


def test_acontext_explicit_venv_preflight_rerun_refuses_ready_source_log():
    log = copy.deepcopy(build_acontext_prerequisite_recovery_attempt_log())
    log["readiness"]["ready_to_attempt_live_transport"] = True

    with pytest.raises(CityOpsContractError, match="consume ready log"):
        build_acontext_explicit_venv_preflight_rerun(recovery_log=log)


def test_acontext_explicit_venv_preflight_rerun_refuses_missing_explicit_sdk():
    observation = read_fixture_rerun()["explicit_venv_observation"]
    observation["explicit_runner_sdk_available"] = False

    with pytest.raises(CityOpsContractError, match="available explicit SDK"):
        build_acontext_explicit_venv_preflight_rerun(observation=observation)


def test_acontext_explicit_venv_preflight_rerun_refuses_impossible_service_state():
    observation = read_fixture_rerun()["explicit_venv_observation"]
    observation["compose_services_started"] = True
    observation["compose_pull_completed"] = False

    with pytest.raises(CityOpsContractError, match="services cannot start"):
        build_acontext_explicit_venv_preflight_rerun(observation=observation)


def test_acontext_explicit_venv_preflight_rerun_refuses_readiness_promotion_on_load(
    tmp_path,
):
    _copy_rerun_sources(tmp_path)
    path = write_acontext_explicit_venv_preflight_rerun(artifact_dir=tmp_path)
    rerun = json.loads(path.read_text(encoding="utf-8"))
    rerun["readiness"]["attempt_allowed"] = True
    path.write_text(json.dumps(rerun), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_explicit_venv_preflight_rerun(artifact_dir=tmp_path)


def test_acontext_explicit_venv_preflight_rerun_write_and_load_temp_fixture(tmp_path):
    _copy_rerun_sources(tmp_path)
    path = write_acontext_explicit_venv_preflight_rerun(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_FILENAME
    loaded = load_acontext_explicit_venv_preflight_rerun(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SAFE_CLAIM
    )


def _copy_rerun_sources(tmp_path: Path) -> None:
    for filename in [
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
        ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME,
        ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
        ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME,
    ]:
        shutil.copy(PROOF_BLOCK_DIR / filename, tmp_path / filename)
