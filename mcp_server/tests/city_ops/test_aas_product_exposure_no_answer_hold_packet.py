from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_portfolio_next_gate_board import (
    AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
    build_aas_portfolio_next_gate_board,
)
from mcp_server.city_ops.aas_portfolio_promotion_ledger import (
    AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME,
    build_aas_portfolio_promotion_ledger,
)
from mcp_server.city_ops.aas_product_exposure_boundary_candidate_review_gate import (
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME,
    build_aas_product_exposure_boundary_candidate_review_gate,
)
from mcp_server.city_ops.aas_product_exposure_no_answer_hold_packet import (
    AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_FILENAME,
    AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SAFE_CLAIM,
    AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SCHEMA,
    PACKET_BLOCKED_CLAIMS,
    PACKET_FALSE_FLAGS,
    PACKET_ID,
    PACKET_STATUS,
    PACKET_VERDICT,
    build_aas_product_exposure_no_answer_hold_packet,
    load_aas_product_exposure_no_answer_hold_packet,
    write_aas_product_exposure_no_answer_hold_packet,
)
from mcp_server.city_ops.aas_product_fork_no_answer_pause_board import (
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME,
    DEFAULT_DECISION,
    RUNTIME_DECISION,
    build_aas_product_fork_no_answer_pause_board,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.retail_reality_human_operator_approval_request import (
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    build_retail_reality_human_operator_approval_request,
)
from mcp_server.city_ops.retail_reality_pending_approval_status_card import (
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME,
    build_retail_reality_pending_approval_status_card,
)
from mcp_server.city_ops.retail_reality_product_exposure_boundary_packet import (
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME,
    build_retail_reality_product_exposure_boundary_packet,
)
from mcp_server.city_ops.retail_reality_product_exposure_hold_regression_guard import (
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
    build_retail_reality_product_exposure_hold_regression_guard,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path) -> None:
    ledger = build_aas_portfolio_promotion_ledger()
    next_gate_board = build_aas_portfolio_next_gate_board(source_ledger=ledger)
    request = build_retail_reality_human_operator_approval_request()
    status_card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    boundary_packet = build_retail_reality_product_exposure_boundary_packet(status_card=status_card)
    hold_guard = build_retail_reality_product_exposure_hold_regression_guard(
        source_packet=boundary_packet
    )
    pause_board = build_aas_product_fork_no_answer_pause_board(
        source_next_gate_board=next_gate_board,
        source_retail_hold_guard=hold_guard,
    )
    candidate_gate = build_aas_product_exposure_boundary_candidate_review_gate(
        pause_board=pause_board,
        boundary_packet=boundary_packet,
    )

    for filename, payload in [
        (AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME, ledger),
        (AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME, next_gate_board),
        (RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME, request),
        (RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME, status_card),
        (RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME, boundary_packet),
        (RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME, hold_guard),
        (AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME, pause_board),
        (AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME, candidate_gate),
    ]:
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_no_answer_hold_packet_matches_persisted_artifact_and_loader() -> None:
    packet = build_aas_product_exposure_no_answer_hold_packet()

    assert packet == read_packet()
    assert load_aas_product_exposure_no_answer_hold_packet() == packet
    assert packet["schema"] == AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SCHEMA
    assert packet["packet_id"] == PACKET_ID
    assert packet["packet_status"] == PACKET_STATUS
    assert packet["packet_verdict"] == PACKET_VERDICT
    assert AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_no_answer_hold_packet_cross_checks_digest_only_candidate_without_approval() -> None:
    packet = build_aas_product_exposure_no_answer_hold_packet()
    card = packet["selected_candidate_digest_card"]
    alignment = packet["source_alignment"]
    no_answer = packet["no_answer_contract"]

    assert packet["candidate_count"] == 1
    assert card["candidate_key"] == "retail_reality_as_a_service"
    assert card["offer_id"] == "storefront_hours_availability_check"
    assert card["selected_for_human_review"] is True
    assert card["selected_for_approval"] is False
    assert card["approval_recorded_here"] is False
    assert card["candidate_text_values_visible"] is False
    assert card["selected_text_boundary_digest_sha256"]
    assert alignment == {
        "candidate_gate_and_hold_guard_reference_same_candidate": True,
        "candidate_gate_and_hold_guard_reference_same_selected_boundary_digest": True,
        "digest_match_is_not_approval": True,
        "digest_match_creates_no_hold_record": True,
        "candidate_text_values_visible": False,
    }
    assert no_answer["explicit_human_operator_answer_present"] is False
    assert no_answer["human_operator_approval_record_present"] is False
    assert no_answer["approval_can_be_inferred_from_candidate_selection"] is False
    assert no_answer["approval_can_be_inferred_from_digest_match"] is False
    assert no_answer["packet_is_operator_answer"] is False
    assert no_answer["default_if_no_human_answer"] == DEFAULT_DECISION
    assert no_answer["runtime_decision_preserved"] == RUNTIME_DECISION


def test_no_answer_hold_packet_blocks_external_runtime_payment_reputation_and_stopped_claims() -> None:
    packet = build_aas_product_exposure_no_answer_hold_packet()
    safe = set(packet["claim_boundaries"]["safe_to_claim"])
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])

    for claim in PACKET_BLOCKED_CLAIMS:
        assert claim in blocked
        assert claim not in safe
    for flag, expected in PACKET_FALSE_FLAGS.items():
        assert packet["readiness"][flag] is expected
        assert packet["regression_assertions"][flag] is expected
    for flag in [
        "customer_visible",
        "public_visible",
        "worker_visible",
        "catalog_visible",
        "pricing_enabled",
        "dispatch_enabled",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "mutates_runtime_adapter_or_session_manager",
        "emits_reputation_receipts",
        "publishes_worker_doctrine",
        "exposes_exact_gps_or_raw_metadata",
        "exposes_private_context",
    ]:
        assert packet["access_policy"][flag] is False
    assert packet["access_policy"]["default_off"] is True
    assert packet["access_policy"]["non_authorizing"] is True
    assert packet["still_blocked_claims"] == packet["claim_boundaries"]["do_not_claim_yet"]


def test_no_answer_hold_packet_preserves_stopped_project_firewall() -> None:
    packet = build_aas_product_exposure_no_answer_hold_packet()
    firewall = packet["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_write_no_answer_hold_packet_persists_valid_fixture_from_sources(tmp_path: Path) -> None:
    seed_sources(tmp_path)

    path = write_aas_product_exposure_no_answer_hold_packet(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_FILENAME
    assert load_aas_product_exposure_no_answer_hold_packet(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_no_answer_hold_packet_fails_closed_on_boundary_digest_mismatch() -> None:
    candidate_gate = copy.deepcopy(build_aas_product_exposure_boundary_candidate_review_gate())
    hold_guard = build_retail_reality_product_exposure_hold_regression_guard()
    candidate_gate["selected_candidates"][0]["selected_text_boundary_digest_sha256"] = "bad-digest"

    with pytest.raises(CityOpsContractError, match="selected boundary digest mismatch|selected candidate drift"):
        build_aas_product_exposure_no_answer_hold_packet(
            candidate_gate=candidate_gate,
            hold_guard=hold_guard,
        )


def test_no_answer_hold_packet_fails_closed_when_source_gate_records_approval() -> None:
    candidate_gate = copy.deepcopy(build_aas_product_exposure_boundary_candidate_review_gate())
    hold_guard = build_retail_reality_product_exposure_hold_regression_guard()
    candidate_gate["no_answer_state"]["human_operator_approval_record_present"] = True

    with pytest.raises(CityOpsContractError, match="records approval|promoted human_operator_approval_record_present"):
        build_aas_product_exposure_no_answer_hold_packet(
            candidate_gate=candidate_gate,
            hold_guard=hold_guard,
        )


def test_loader_fails_closed_when_packet_readiness_promotes_dispatch(tmp_path: Path) -> None:
    seed_sources(tmp_path)
    packet = build_aas_product_exposure_no_answer_hold_packet(artifact_dir=tmp_path)
    packet["readiness"]["dispatch_enabled"] = True
    (tmp_path / AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="readiness promoted dispatch_enabled"):
        load_aas_product_exposure_no_answer_hold_packet(artifact_dir=tmp_path)
