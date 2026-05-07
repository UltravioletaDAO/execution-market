import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight import build_blocked_acontext_preflight_probe, build_acontext_live_preflight_result
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.operator_debug_surface import (
    OPERATOR_DEBUG_SURFACE_SAFE_CLAIM,
    OPERATOR_DEBUG_SURFACE_SCHEMA,
    build_operator_debug_surface,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_surface() -> dict:
    with (PROOF_BLOCK_DIR / "operator_debug_surface.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_operator_debug_surface_matches_fixture():
    surface = build_operator_debug_surface()

    assert surface == read_fixture_surface()
    assert surface["schema"] == OPERATOR_DEBUG_SURFACE_SCHEMA
    assert surface["surface_verdict"] == "thin_operator_debug_surface_landed_live_transport_blocked"
    assert OPERATOR_DEBUG_SURFACE_SAFE_CLAIM in surface["claim_boundaries"]["safe_to_claim"]
    assert "acontext_sink_ready" in surface["claim_boundaries"]["do_not_claim_yet"]
    assert "worker-copyable municipal doctrine" in surface["claim_boundaries"]["do_not_claim_yet"]
    assert surface["operator_visibility"]["worker_copyable_surface_enabled"] is False
    assert surface["operator_visibility"]["copyable_worker_instruction"]["allowed"] is False
    assert surface["readiness"]["surface_promotes_readiness"] is False
    assert surface["readiness"]["acontext_sink_ready"] is False


def test_operator_debug_surface_preserves_claim_cards_without_softening():
    surface = build_operator_debug_surface()
    cards = {card["card"]: card for card in surface["debug_cards"]}

    assert cards["safe_to_claim"]["status"] == "visible_without_softening"
    assert OPERATOR_DEBUG_SURFACE_SAFE_CLAIM in cards["safe_to_claim"]["values"]
    assert cards["do_not_claim_yet"]["status"] == "visible_without_softening"
    assert set(cards["do_not_claim_yet"]["values"]).issubset(
        set(surface["claim_boundaries"]["do_not_claim_yet"])
    )
    assert cards["operator_guidance"]["status"] == "operator_visible_not_worker_copyable"
    assert cards["transport"]["status"] == "blocked_before_live_sink_write"


def test_operator_debug_surface_can_show_attemptable_transport_without_promoting_readiness():
    probe = build_blocked_acontext_preflight_probe()
    probe["docker"].update({"available": True, "exit_code": 0, "error": None})
    probe["python_sdk"]["available"] = True
    probe["api"].update({"reachable": True, "status_code": 200, "error": None})
    probe["dashboard"].update({"reachable": True, "status_code": 200, "error": None})
    preflight = build_acontext_live_preflight_result(probe=probe)

    surface = build_operator_debug_surface(acontext_live_preflight_result=preflight)

    assert surface["surface_verdict"] == "thin_operator_debug_surface_landed_live_transport_attemptable"
    assert surface["readiness"]["ready_to_attempt_live_transport"] is True
    assert surface["readiness"]["acontext_sink_ready"] is False
    assert surface["readiness"]["runtime_parity_proven"] is False
    assert "acontext_live_transport_parity_landed" in surface["claim_boundaries"]["do_not_claim_yet"]


def test_operator_debug_surface_refuses_identity_drift():
    preflight = build_acontext_live_preflight_result(probe=build_blocked_acontext_preflight_probe())
    preflight["compact_decision_id"] = "drifted_decision"

    with pytest.raises(CityOpsContractError, match="identity drift"):
        build_operator_debug_surface(acontext_live_preflight_result=preflight)


def test_operator_debug_surface_refuses_worker_copyable_upgrade():
    with (PROOF_BLOCK_DIR / "session_rebuild_report.json").open("r", encoding="utf-8") as fh:
        report = json.load(fh)
    report["promotion_boundaries"]["copyable_worker_instruction"]["allowed"] = True

    with pytest.raises(CityOpsContractError, match="worker-copyable"):
        build_operator_debug_surface(session_rebuild_report=report)


def test_operator_debug_surface_refuses_blocked_safe_claim():
    preflight = build_acontext_live_preflight_result(probe=build_blocked_acontext_preflight_probe())
    preflight["claim_boundaries"]["safe_to_claim"].append("acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims safe"):
        build_operator_debug_surface(acontext_live_preflight_result=preflight)
