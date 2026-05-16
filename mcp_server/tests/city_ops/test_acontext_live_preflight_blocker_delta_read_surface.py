import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight_blocker_delta import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM,
    BLOCKER_DELTA_BLOCKED_CLAIMS,
    build_acontext_live_preflight_blocker_delta,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta_read_surface import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA,
    SURFACE_BLOCKED_CLAIMS,
    build_acontext_live_preflight_blocker_delta_read_surface,
    load_acontext_live_preflight_blocker_delta_read_surface,
    write_acontext_live_preflight_blocker_delta_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_surface() -> dict:
    with (
        PROOF_BLOCK_DIR / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_acontext_blocker_delta_read_surface_matches_fixture():
    surface = build_acontext_live_preflight_blocker_delta_read_surface()

    assert surface == read_fixture_surface()
    assert surface["schema"] == ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA
    assert surface["surface_verdict"] == (
        "admin_acontext_blocker_delta_surface_landed_live_transport_blocked"
    )
    assert ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM in surface[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM in surface[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert surface["readiness"]["surface_landed"] is True
    assert surface["readiness"]["surface_promotes_live_readiness"] is False
    assert surface["readiness"]["acontext_sink_ready"] is False


def test_acontext_blocker_delta_read_surface_renders_prerequisite_cards():
    delta = build_acontext_live_preflight_blocker_delta()
    surface = build_acontext_live_preflight_blocker_delta_read_surface(delta=delta)

    cards = {card["prerequisite"]: card for card in surface["prerequisite_status_cards"]}
    assert cards["docker_daemon"]["status"] == "cleared"
    assert cards["docker_daemon"]["badge"] == "prerequisite_cleared_not_authority"
    assert cards["acontext_python_sdk"]["status"] == "blocked"
    assert cards["local_acontext_api"]["status"] == "blocked"
    assert cards["local_acontext_dashboard"]["status"] == "blocked"
    assert all(card["authorizes_live_write"] is False for card in cards.values())


def test_acontext_blocker_delta_read_surface_preserves_blocker_summary_and_footer():
    delta = build_acontext_live_preflight_blocker_delta()
    surface = build_acontext_live_preflight_blocker_delta_read_surface(delta=delta)

    summary = surface["blocker_delta_summary"]
    assert summary["cleared_blockers"] == ["docker_daemon_unavailable"]
    assert summary["remaining_blockers"] == [
        "acontext_python_sdk_missing",
        "local_acontext_api_unreachable",
        "local_acontext_dashboard_unreachable",
    ]
    assert summary["may_attempt_live_parity"] is False
    assert summary["may_claim_runtime_parity"] is False

    footer = surface["claim_boundary_footer"]
    assert footer["placement"] == "sticky_after_every_blocker_recommendation"
    assert set(BLOCKER_DELTA_BLOCKED_CLAIMS) <= set(footer["do_not_claim_yet"])
    assert set(SURFACE_BLOCKED_CLAIMS) <= set(footer["do_not_claim_yet"])
    assert not (set(footer["safe_to_claim"]) & set(footer["do_not_claim_yet"]))


def test_acontext_blocker_delta_read_surface_refuses_ready_source():
    delta = copy.deepcopy(build_acontext_live_preflight_blocker_delta())
    delta["readiness"]["ready_to_attempt_live_transport"] = True

    with pytest.raises(CityOpsContractError, match="ready source"):
        build_acontext_live_preflight_blocker_delta_read_surface(delta=delta)


def test_acontext_blocker_delta_read_surface_refuses_runtime_promotion():
    delta = copy.deepcopy(build_acontext_live_preflight_blocker_delta())
    delta["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="runtime_parity_proven"):
        build_acontext_live_preflight_blocker_delta_read_surface(delta=delta)


def test_acontext_blocker_delta_read_surface_refuses_blocked_safe_claim():
    delta = copy.deepcopy(build_acontext_live_preflight_blocker_delta())
    delta["claim_boundaries"]["safe_to_claim"].append("public_route_ready")

    with pytest.raises(CityOpsContractError, match="blocked safe claims"):
        build_acontext_live_preflight_blocker_delta_read_surface(delta=delta)


def test_acontext_blocker_delta_read_surface_loader_rejects_route_drift(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
        tmp_path / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
    )
    path = write_acontext_live_preflight_blocker_delta_read_surface(artifact_dir=tmp_path)
    surface = json.loads(path.read_text(encoding="utf-8"))
    surface["render_contract"]["network_route_registered"] = True
    path.write_text(json.dumps(surface), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="network_route_registered"):
        load_acontext_live_preflight_blocker_delta_read_surface(artifact_dir=tmp_path)


def test_acontext_blocker_delta_read_surface_write_and_load_temp_fixture(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
        tmp_path / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
    )
    path = write_acontext_live_preflight_blocker_delta_read_surface(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME
    loaded = load_acontext_live_preflight_blocker_delta_read_surface(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM
    )
