from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_product_exposure_boundary_candidate_review_gate import (
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME,
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA,
    DEFAULT_POSTURE,
    GATE_BLOCKED_CLAIMS,
    GATE_FALSE_FLAGS,
    GATE_ID,
    GATE_STATUS,
    HUMAN_REVIEW_QUESTION,
    SELECTED_CANDIDATE_KEY,
    SELECTED_FAMILY_ID,
    build_aas_product_exposure_boundary_candidate_review_gate,
    load_aas_product_exposure_boundary_candidate_review_gate,
    write_aas_product_exposure_boundary_candidate_review_gate,
)
from mcp_server.city_ops.aas_product_fork_no_answer_pause_board import (
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME,
    DEFAULT_DECISION,
    RUNTIME_DECISION,
    build_aas_product_fork_no_answer_pause_board,
)
from mcp_server.city_ops.aas_portfolio_next_gate_board import (
    AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
    build_aas_portfolio_next_gate_board,
)
from mcp_server.city_ops.aas_portfolio_promotion_ledger import (
    AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME,
    build_aas_portfolio_promotion_ledger,
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
    build_retail_reality_product_exposure_hold_regression_guard,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"



def read_gate() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME).read_text(
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

    for filename, payload in [
        (AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME, ledger),
        (AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME, next_gate_board),
        (RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME, request),
        (RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME, status_card),
        (RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME, boundary_packet),
        (RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME, hold_guard),
        (AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME, pause_board),
    ]:
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")



def test_candidate_review_gate_matches_persisted_artifact_and_loader() -> None:
    gate = build_aas_product_exposure_boundary_candidate_review_gate()

    assert gate == read_gate()
    assert load_aas_product_exposure_boundary_candidate_review_gate() == gate
    assert gate["schema"] == AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA
    assert gate["gate_id"] == GATE_ID
    assert gate["gate_status"] == GATE_STATUS
    assert AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM in gate[
        "claim_boundaries"
    ]["safe_to_claim"]



def test_candidate_review_gate_selects_exactly_one_boundary_for_human_review_only() -> None:
    gate = build_aas_product_exposure_boundary_candidate_review_gate()
    candidate = gate["selected_candidates"][0]

    assert gate["candidate_count"] == 1
    assert len(gate["selected_candidates"]) == 1
    assert candidate["selection_key"] == SELECTED_CANDIDATE_KEY
    assert candidate["candidate_key"] == SELECTED_FAMILY_ID
    assert candidate["package_family_id"] == SELECTED_FAMILY_ID
    assert candidate["selected_for_human_review"] is True
    assert candidate["selection_purpose"] == "human_review_candidate_only"
    assert candidate["default_posture"] == DEFAULT_POSTURE
    assert candidate["selected_for_approval"] is False
    assert candidate["approval_recorded_here"] is False
    assert candidate["customer_or_public_exposure_allowed"] is False
    assert candidate["worker_surface_allowed"] is False
    assert candidate["pricing_queue_dispatch_allowed"] is False
    assert candidate["runtime_mutation_allowed"] is False
    assert candidate["human_review_question"] == HUMAN_REVIEW_QUESTION



def test_candidate_review_gate_preserves_no_answer_default_and_runtime_hold() -> None:
    gate = build_aas_product_exposure_boundary_candidate_review_gate()

    assert gate["no_answer_state"] == {
        "explicit_human_operator_answer_present": False,
        "human_operator_approval_record_present": False,
        "approval_can_be_inferred_from_candidate_selection": False,
        "default_if_no_human_answer": DEFAULT_DECISION,
        "runtime_decision_preserved": RUNTIME_DECISION,
    }
    assert gate["selection_contract"] == {
        "exactly_one_candidate_selected_for_human_review": True,
        "selected_family_id": SELECTED_FAMILY_ID,
        "selected_offer_id": "storefront_hours_availability_check",
        "selection_is_approval": False,
        "selection_is_customer_copy": False,
        "selection_is_public_catalog_or_pricing_surface": False,
        "selection_is_worker_surface": False,
        "selection_is_runtime_mutation": False,
        "selection_is_payment_or_production_reverification": False,
        "selection_uses_stopped_project_inputs": False,
    }



def test_candidate_review_gate_blocks_external_runtime_payment_reputation_and_stopped_claims() -> None:
    gate = build_aas_product_exposure_boundary_candidate_review_gate()
    safe = set(gate["claim_boundaries"]["safe_to_claim"])
    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])

    for claim in GATE_BLOCKED_CLAIMS:
        assert claim in blocked
        assert claim not in safe
    for flag, expected in GATE_FALSE_FLAGS.items():
        assert gate["readiness"][flag] is expected
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
        assert gate["access_policy"][flag] is False
    assert gate["access_policy"]["default_off"] is True
    assert gate["access_policy"]["non_authorizing"] is True
    assert gate["still_blocked_claims"] == gate["claim_boundaries"]["do_not_claim_yet"]



def test_candidate_review_gate_preserves_stopped_project_firewall() -> None:
    gate = build_aas_product_exposure_boundary_candidate_review_gate()
    firewall = gate["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"



def test_write_candidate_review_gate_persists_valid_fixture_from_sources(tmp_path: Path) -> None:
    seed_sources(tmp_path)

    path = write_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME
    assert load_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )



def test_candidate_review_gate_fails_closed_when_pause_board_records_answer() -> None:
    pause_board = copy.deepcopy(build_aas_product_fork_no_answer_pause_board())
    boundary_packet = build_retail_reality_product_exposure_boundary_packet()
    pause_board["no_answer_state"]["explicit_human_operator_answer_present"] = True

    with pytest.raises(CityOpsContractError, match="records answer"):
        build_aas_product_exposure_boundary_candidate_review_gate(
            pause_board=pause_board,
            boundary_packet=boundary_packet,
        )



def test_candidate_review_gate_fails_closed_when_boundary_candidate_count_changes() -> None:
    pause_board = build_aas_product_fork_no_answer_pause_board()
    boundary_packet = copy.deepcopy(build_retail_reality_product_exposure_boundary_packet())
    boundary_packet["candidate_count"] = 2
    boundary_packet["aas_candidates"].append(copy.deepcopy(boundary_packet["aas_candidates"][0]))

    with pytest.raises(CityOpsContractError, match="candidate count drift"):
        build_aas_product_exposure_boundary_candidate_review_gate(
            pause_board=pause_board,
            boundary_packet=boundary_packet,
        )



def test_loader_fails_closed_on_customer_visibility_promotion(tmp_path: Path) -> None:
    seed_sources(tmp_path)
    gate = build_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)
    gate["access_policy"]["customer_visible"] = True
    (tmp_path / AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="access promoted customer_visible"):
        load_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)



def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path: Path) -> None:
    seed_sources(tmp_path)
    gate = build_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)
    gate["claim_boundaries"]["safe_to_claim"].append("dispatch_ready")
    (tmp_path / AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)



def test_loader_fails_closed_on_selected_candidate_approval_promotion(tmp_path: Path) -> None:
    seed_sources(tmp_path)
    gate = build_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)
    gate["selected_candidates"][0]["selected_for_approval"] = True
    (tmp_path / AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="selected candidate drift"):
        load_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)
