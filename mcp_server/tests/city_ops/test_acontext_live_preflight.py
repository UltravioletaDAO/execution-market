import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight import (
    ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM,
    ACONTEXT_LIVE_PREFLIGHT_SCHEMA,
    build_acontext_live_preflight_result,
    build_blocked_acontext_preflight_probe,
)
from mcp_server.city_ops.acontext_transport import build_acontext_transport_packet
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_result() -> dict:
    with (PROOF_BLOCK_DIR / "acontext_live_preflight_result.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def ready_probe() -> dict:
    probe = build_blocked_acontext_preflight_probe()
    probe["docker"].update({"available": True, "exit_code": 0, "error": None})
    probe["python_sdk"]["available"] = True
    probe["api"].update({"reachable": True, "status_code": 200, "error": None})
    probe["dashboard"].update(
        {"reachable": True, "status_code": 200, "error": None}
    )
    return probe


def test_acontext_live_preflight_result_matches_fixture():
    result = build_acontext_live_preflight_result(
        probe=build_blocked_acontext_preflight_probe()
    )

    assert result == read_fixture_result()
    assert result["schema"] == ACONTEXT_LIVE_PREFLIGHT_SCHEMA
    assert result["preflight_verdict"] == "live_transport_blocked_before_sink_write"
    assert ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM in result["claim_boundaries"][
        "safe_to_claim"
    ]
    assert result["readiness"]["ready_to_attempt_live_transport"] is False
    assert result["readiness"]["acontext_sink_ready"] is False
    assert result["readiness"]["live_acontext_write_performed"] is False
    assert result["probe"]["live_acontext_write_performed"] is False


def test_acontext_live_preflight_can_be_ready_without_promoting_sink_readiness():
    result = build_acontext_live_preflight_result(probe=ready_probe())

    assert result["preflight_verdict"] == (
        "live_transport_can_be_attempted_without_readiness_claim"
    )
    assert result["readiness"]["ready_to_attempt_live_transport"] is True
    assert result["readiness"]["acontext_sink_ready"] is False
    assert result["readiness"]["session_rebuild_ready"] is False
    assert result["readiness"]["runtime_parity_proven"] is False
    assert "acontext_sink_ready" in result["claim_boundaries"]["do_not_claim_yet"]
    assert "acontext_live_transport_parity_landed" in result["claim_boundaries"][
        "do_not_claim_yet"
    ]
    assert "assert_acontext_transport_parity" in result[
        "planned_live_transport_contract"
    ]["must_reuse_assertion"]


def test_acontext_live_preflight_refuses_probe_that_writes_live_sink():
    probe = build_blocked_acontext_preflight_probe()
    probe["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="must not perform live Acontext writes"):
        build_acontext_live_preflight_result(probe=probe)


def test_acontext_live_preflight_refuses_safe_live_readiness_claim():
    packet = build_acontext_transport_packet()
    packet["stored_payload"]["claim_boundaries"]["safe_to_claim"].append(
        "acontext_sink_ready"
    )

    with pytest.raises(CityOpsContractError, match="blocked claims safe"):
        build_acontext_live_preflight_result(
            packet=packet,
            probe=build_blocked_acontext_preflight_probe(),
        )
