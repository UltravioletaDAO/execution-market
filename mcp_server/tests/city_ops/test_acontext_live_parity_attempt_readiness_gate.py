import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_parity_attempt_readiness_gate import (
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME,
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM,
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA,
    GATE_BLOCKED_CLAIMS,
    build_acontext_live_parity_attempt_readiness_gate,
    load_acontext_live_parity_attempt_readiness_gate,
    write_acontext_live_parity_attempt_readiness_gate,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta_read_surface import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM,
    build_acontext_live_preflight_blocker_delta_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_gate() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_live_parity_attempt_gate_matches_fixture():
    gate = build_acontext_live_parity_attempt_readiness_gate()

    assert gate == read_fixture_gate()
    assert gate["schema"] == ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA
    assert gate["gate_verdict"] == "live_parity_attempt_blocked_prerequisites_missing"
    assert ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM in gate[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM in gate[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert gate["readiness"]["gate_landed"] is True
    assert gate["readiness"]["attempt_allowed"] is False
    assert gate["readiness"]["runtime_parity_proven"] is False


def test_acontext_live_parity_attempt_gate_denies_write_retrieve_but_allows_preflight_only():
    surface = build_acontext_live_preflight_blocker_delta_read_surface()
    gate = build_acontext_live_parity_attempt_readiness_gate(blocker_surface=surface)

    policy = gate["attempt_policy"]
    assert policy["attempt_allowed"] is False
    assert policy["may_run_preflight_only"] is True
    assert policy["may_run_live_write"] is False
    assert policy["may_run_live_retrieve"] is False
    assert policy["may_claim_runtime_parity"] is False
    assert policy["blocked_by"] == [
        "acontext_python_sdk_missing",
        "local_acontext_api_unreachable",
        "local_acontext_dashboard_unreachable",
    ]
    assert "rerun_preflight_without_live_write_or_retrieve" in policy[
        "allowed_next_action_classes"
    ]
    assert "live_acontext_write" in policy["forbidden_next_action_classes"]


def test_acontext_live_parity_attempt_gate_preserves_sticky_blocked_claims():
    gate = build_acontext_live_parity_attempt_readiness_gate()

    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])
    assert set(GATE_BLOCKED_CLAIMS) <= blocked
    assert not (set(gate["claim_boundaries"]["safe_to_claim"]) & blocked)

    sticky = gate["operator_decision_cards"][2]["sticky_claims"]
    assert "runtime_parity_proven" in sticky
    assert "worker_copyable_municipal_doctrine_ready" in sticky


def test_acontext_live_parity_attempt_gate_refuses_ready_source():
    surface = copy.deepcopy(build_acontext_live_preflight_blocker_delta_read_surface())
    surface["readiness"]["ready_to_attempt_live_transport"] = True

    with pytest.raises(CityOpsContractError, match="ready source"):
        build_acontext_live_parity_attempt_readiness_gate(blocker_surface=surface)


def test_acontext_live_parity_attempt_gate_refuses_missing_blockers():
    surface = copy.deepcopy(build_acontext_live_preflight_blocker_delta_read_surface())
    surface["blocker_delta_summary"]["remaining_blockers"] = []

    with pytest.raises(CityOpsContractError, match="remaining blockers"):
        build_acontext_live_parity_attempt_readiness_gate(blocker_surface=surface)


def test_acontext_live_parity_attempt_gate_refuses_blocked_safe_claim():
    surface = copy.deepcopy(build_acontext_live_preflight_blocker_delta_read_surface())
    surface["claim_boundaries"]["safe_to_claim"].append("runtime_parity_proven")

    with pytest.raises(CityOpsContractError, match="blocked safe claims"):
        build_acontext_live_parity_attempt_readiness_gate(blocker_surface=surface)


def _copy_gate_sources(tmp_path: Path) -> None:
    for filename in [
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
    ]:
        shutil.copy(PROOF_BLOCK_DIR / filename, tmp_path / filename)


def test_acontext_live_parity_attempt_gate_loader_rejects_attempt_promotion(tmp_path):
    _copy_gate_sources(tmp_path)
    path = write_acontext_live_parity_attempt_readiness_gate(artifact_dir=tmp_path)
    gate = json.loads(path.read_text(encoding="utf-8"))
    gate["attempt_policy"]["attempt_allowed"] = True
    path.write_text(json.dumps(gate), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="allowed live attempt"):
        load_acontext_live_parity_attempt_readiness_gate(artifact_dir=tmp_path)


def test_acontext_live_parity_attempt_gate_write_and_load_temp_fixture(tmp_path):
    _copy_gate_sources(tmp_path)
    path = write_acontext_live_parity_attempt_readiness_gate(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME
    loaded = load_acontext_live_parity_attempt_readiness_gate(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM
    )
