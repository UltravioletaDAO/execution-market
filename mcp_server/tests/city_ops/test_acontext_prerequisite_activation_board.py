import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_parity_attempt_readiness_gate import (
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME,
    build_acontext_live_parity_attempt_readiness_gate,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta_read_surface import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
)
from mcp_server.city_ops.acontext_prerequisite_activation_board import (
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM,
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA,
    ACTIVATION_BOARD_BLOCKED_CLAIMS,
    build_acontext_prerequisite_activation_board,
    load_acontext_prerequisite_activation_board,
    write_acontext_prerequisite_activation_board,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_board() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_prerequisite_activation_board_matches_fixture():
    board = build_acontext_prerequisite_activation_board()

    assert board == read_fixture_board()
    assert board["schema"] == ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA
    assert board["board_verdict"] == "activation_started_not_live_ready"
    assert ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM in board[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert board["readiness"]["activation_board_landed"] is True
    assert board["readiness"]["docker_available"] is True
    assert board["readiness"]["acontext_cli_installed"] is True
    assert board["readiness"]["dedicated_sdk_venv_found"] is True
    assert board["readiness"]["active_runner_sdk_available"] is False
    assert board["readiness"]["local_acontext_api_reachable"] is False
    assert board["readiness"]["ready_to_attempt_live_transport"] is False


def test_acontext_prerequisite_activation_board_keeps_setup_separate_from_live_authorization():
    board = build_acontext_prerequisite_activation_board()

    setup_card = board["activation_cards"][0]
    assert setup_card["status"] == "partial_assets_present"
    assert setup_card["dedicated_sdk_venv_found"] is True
    assert setup_card["active_runner_sdk_available"] is False

    claim_card = board["activation_cards"][-1]
    assert claim_card["authorizes_live_write"] is False
    assert claim_card["authorizes_live_retrieve"] is False
    assert claim_card["authorizes_runtime_parity_claim"] is False
    assert claim_card["authorizes_customer_or_worker_surface"] is False


def test_acontext_prerequisite_activation_board_preserves_sticky_blocked_claims():
    board = build_acontext_prerequisite_activation_board()

    blocked = set(board["claim_boundaries"]["do_not_claim_yet"])
    assert set(ACTIVATION_BOARD_BLOCKED_CLAIMS) <= blocked
    assert not (set(board["claim_boundaries"]["safe_to_claim"]) & blocked)
    assert "runtime_parity_proven_by_activation_board" in blocked
    assert "worker_copyable_municipal_doctrine_ready_by_gate" in blocked


def test_acontext_prerequisite_activation_board_refuses_allowed_source_gate():
    gate = copy.deepcopy(build_acontext_live_parity_attempt_readiness_gate())
    gate["readiness"]["attempt_allowed"] = True

    with pytest.raises(CityOpsContractError, match="allowed gate"):
        build_acontext_prerequisite_activation_board(gate=gate)


def test_acontext_prerequisite_activation_board_refuses_live_write_observation():
    observation = read_fixture_board()["activation_observation"]
    observation["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live write"):
        build_acontext_prerequisite_activation_board(observation=observation)


def test_acontext_prerequisite_activation_board_refuses_readiness_promotion_on_load(tmp_path):
    _copy_board_sources(tmp_path)
    path = write_acontext_prerequisite_activation_board(artifact_dir=tmp_path)
    board = json.loads(path.read_text(encoding="utf-8"))
    board["readiness"]["ready_to_attempt_live_transport"] = True
    path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_prerequisite_activation_board(artifact_dir=tmp_path)


def test_acontext_prerequisite_activation_board_write_and_load_temp_fixture(tmp_path):
    _copy_board_sources(tmp_path)
    path = write_acontext_prerequisite_activation_board(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME
    loaded = load_acontext_prerequisite_activation_board(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM
    )


def _copy_board_sources(tmp_path: Path) -> None:
    for filename in [
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
        ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME,
    ]:
        shutil.copy(PROOF_BLOCK_DIR / filename, tmp_path / filename)
