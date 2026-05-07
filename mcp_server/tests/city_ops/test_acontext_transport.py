import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_transport import (
    ACONTEXT_TRANSPORT_PACKET_SCHEMA,
    ACONTEXT_TRANSPORT_PARITY_RESULT_SCHEMA,
    ACONTEXT_TRANSPORT_SAFE_CLAIM,
    assert_acontext_transport_parity,
    build_acontext_transport_packet,
    build_acontext_transport_parity_result,
    retrieve_acontext_transport_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.session_rebuild_consumer import build_session_rebuild_report

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_result() -> dict:
    with (PROOF_BLOCK_DIR / "acontext_transport_parity_result.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_transport_parity_result_matches_fixture():
    result = build_acontext_transport_parity_result()

    assert result == read_fixture_result()
    assert result["schema"] == ACONTEXT_TRANSPORT_PARITY_RESULT_SCHEMA
    assert result["result_verdict"] == "acontext_transport_parity_fixture_landed"
    assert ACONTEXT_TRANSPORT_SAFE_CLAIM in result["claim_boundaries"]["safe_to_claim"]
    assert result["transport_contract"]["transport_mode"] == "local_parity_fixture"
    assert result["transport_contract"]["live_acontext_write_performed"] is False
    assert result["transport_contract"]["ready_to_replace_local_sink"] is False


def test_acontext_transport_packet_round_trip_preserves_boundaries():
    packet = build_acontext_transport_packet()
    retrieval = retrieve_acontext_transport_packet(packet)

    assert packet["schema"] == ACONTEXT_TRANSPORT_PACKET_SCHEMA
    assert retrieval["retrieved_payload"] == packet["stored_payload"]
    assert_acontext_transport_parity(packet, retrieval)

    payload = retrieval["retrieved_payload"]
    assert payload["identity"] == {
        "proof_anchor_id": "redirect_outdated_packet_001",
        "coordination_session_id": "city_session_redirect_outdated_packet_001",
        "compact_decision_id": "cdo_c51f4b767729",
        "review_packet_id": "review_packet_redirect_outdated_packet_001",
    }
    assert payload["promotion_boundaries"]["promotion_class"] == (
        "conservative_memory_delta"
    )
    assert payload["promotion_boundaries"]["guidance_tone"] == (
        "cautionary_or_corrective"
    )
    assert payload["promotion_boundaries"]["guidance_placement"] == (
        "operator_visible_before_worker_copy"
    )
    assert payload["promotion_boundaries"]["copyable_worker_instruction"]["allowed"] is False
    assert payload["readiness"]["telemetry_acontext_sink_ready"] is False


def test_acontext_transport_refuses_safe_sink_readiness_claim():
    report = build_session_rebuild_report()
    report["claim_boundaries"]["safe_to_claim"].append("acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims safe"):
        build_acontext_transport_packet(report=report)


def test_acontext_transport_refuses_worker_copyability_strengthening():
    packet = build_acontext_transport_packet()
    packet["stored_payload"]["promotion_boundaries"]["copyable_worker_instruction"][
        "allowed"
    ] = True

    with pytest.raises(CityOpsContractError, match="copyable_worker_instruction"):
        retrieve_acontext_transport_packet(packet)


def test_acontext_transport_refuses_retrieval_readiness_promotion():
    packet = build_acontext_transport_packet()
    retrieval = retrieve_acontext_transport_packet(packet)
    retrieval["retrieved_payload"]["readiness"]["decision"][
        "session_rebuild_ready"
    ] = True

    with pytest.raises(CityOpsContractError, match="session_rebuild_ready"):
        assert_acontext_transport_parity(packet, retrieval)
