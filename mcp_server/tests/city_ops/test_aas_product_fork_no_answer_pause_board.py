from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_portfolio_next_gate_board import (
    AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
    build_aas_portfolio_next_gate_board,
)
from mcp_server.city_ops.aas_product_fork_no_answer_pause_board import (
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME,
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM,
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SCHEMA,
    DEFAULT_DECISION,
    NEXT_ALLOWED_MOVE,
    PAUSE_BLOCKED_CLAIMS,
    PAUSE_BOARD_ID,
    PAUSE_BOARD_STATUS,
    PAUSE_FALSE_FLAGS,
    RUNTIME_DECISION,
    build_aas_product_fork_no_answer_pause_board,
    load_aas_product_fork_no_answer_pause_board,
    write_aas_product_fork_no_answer_pause_board,
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


def read_pause_board() -> dict:
    with (ARTIFACT_DIR / AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    ledger = build_aas_portfolio_promotion_ledger()
    next_gate_board = build_aas_portfolio_next_gate_board(source_ledger=ledger)
    request = build_retail_reality_human_operator_approval_request()
    status_card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    boundary_packet = build_retail_reality_product_exposure_boundary_packet(status_card=status_card)
    hold_guard = build_retail_reality_product_exposure_hold_regression_guard(
        source_packet=boundary_packet
    )

    (tmp_path / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME).write_text(
        json.dumps(ledger), encoding="utf-8"
    )
    (tmp_path / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME).write_text(
        json.dumps(next_gate_board), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME).write_text(
        json.dumps(status_card), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME).write_text(
        json.dumps(boundary_packet), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME).write_text(
        json.dumps(hold_guard), encoding="utf-8"
    )


def test_product_fork_pause_board_matches_persisted_artifact_and_loader():
    pause_board = build_aas_product_fork_no_answer_pause_board()

    assert pause_board == read_pause_board()
    assert load_aas_product_fork_no_answer_pause_board() == pause_board
    assert pause_board["schema"] == AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SCHEMA
    assert pause_board["pause_board_id"] == PAUSE_BOARD_ID
    assert pause_board["pause_board_status"] == PAUSE_BOARD_STATUS
    assert AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM in pause_board["safe_to_claim"]


def test_product_fork_pause_board_preserves_no_answer_defaults_and_runtime_hold():
    pause_board = build_aas_product_fork_no_answer_pause_board()

    assert pause_board["default_decision"] == DEFAULT_DECISION
    assert pause_board["runtime_decision"] == RUNTIME_DECISION
    assert pause_board["next_allowed_move"] == NEXT_ALLOWED_MOVE
    assert pause_board["no_answer_state"] == {
        "explicit_human_operator_answer_present": False,
        "human_operator_approval_record_present": False,
        "product_family_approval_selected": False,
        "retail_reality_is_closest_review_candidate": True,
        "retail_reality_guard_confirms_hold": True,
        "no_human_default_applied": DEFAULT_DECISION,
        "runtime_decision_preserved": RUNTIME_DECISION,
    }


def test_product_fork_pause_board_keeps_ranked_family_rows_but_approves_none():
    pause_board = build_aas_product_fork_no_answer_pause_board()
    rows = pause_board["product_family_pause_rows"]

    assert [row["rank"] for row in rows] == [1, 2, 3, 4, 5]
    assert rows[0]["family_id"] == "retail_reality_as_a_service"
    assert rows[0]["pause_action"] == "wait_for_real_operator_answer_or_keep_retail_boundary_held"
    assert rows[0]["source_retail_hold_guard_file"] == (
        RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME
    )
    for row in rows:
        assert row["explicit_human_answer_present"] is False
        assert row["approval_record_present"] is False
        assert row["customer_or_public_surface_allowed"] is False
        assert row["this_pause_board_approves_family"] is False
        assert row["customer_delivery_authorized"] is False
        assert row["queue_or_dispatch_ready"] is False
        assert row["live_acontext_runtime_parity"] is False
        assert row["worker_copyable_doctrine_ready"] is False


def test_product_fork_pause_board_regresses_all_customer_runtime_reputation_and_stopped_claims():
    pause_board = build_aas_product_fork_no_answer_pause_board()
    safe = set(pause_board["safe_to_claim"])
    blocked = set(pause_board["do_not_claim_yet"])

    for claim in PAUSE_BLOCKED_CLAIMS:
        assert claim in blocked
        assert claim not in safe
    for flag, expected in PAUSE_FALSE_FLAGS.items():
        assert pause_board["readiness"][flag] is expected
        assert pause_board["regression_assertions"][flag] is expected
    assert pause_board["still_blocked_claims"] == pause_board["do_not_claim_yet"]


def test_write_product_fork_pause_board_persists_valid_fixture_from_sources(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_product_fork_no_answer_pause_board(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME
    assert load_aas_product_fork_no_answer_pause_board(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_pause_board_fails_closed_when_next_gate_board_gets_no_auth_gate():
    next_gate_board = copy.deepcopy(build_aas_portfolio_next_gate_board())
    retail_guard = build_retail_reality_product_exposure_hold_regression_guard()
    next_gate_board["summary"]["gates_ready_without_separate_authorization"] = 1

    with pytest.raises(CityOpsContractError, match="gained no-auth gates"):
        build_aas_product_fork_no_answer_pause_board(
            source_next_gate_board=next_gate_board,
            source_retail_hold_guard=retail_guard,
        )


def test_pause_board_fails_closed_when_next_gate_board_promotes_customer_delivery_safe_claim():
    next_gate_board = copy.deepcopy(build_aas_portfolio_next_gate_board())
    retail_guard = build_retail_reality_product_exposure_hold_regression_guard()
    next_gate_board["safe_to_claim"].append("customer_delivery_approved")

    with pytest.raises(CityOpsContractError, match="source board forbidden safe claims"):
        build_aas_product_fork_no_answer_pause_board(
            source_next_gate_board=next_gate_board,
            source_retail_hold_guard=retail_guard,
        )


def test_pause_board_fails_closed_when_retail_guard_records_human_answer():
    next_gate_board = build_aas_portfolio_next_gate_board()
    retail_guard = copy.deepcopy(build_retail_reality_product_exposure_hold_regression_guard())
    retail_guard["readiness"]["human_operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="retail guard readiness promoted"):
        build_aas_product_fork_no_answer_pause_board(
            source_next_gate_board=next_gate_board,
            source_retail_hold_guard=retail_guard,
        )


def test_loader_fails_closed_on_pause_board_dispatch_promotion(tmp_path):
    seed_sources(tmp_path)
    pause_board = build_aas_product_fork_no_answer_pause_board(artifact_dir=tmp_path)
    pause_board["readiness"]["dispatch_ready"] = True
    (tmp_path / AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME).write_text(
        json.dumps(pause_board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="readiness promoted dispatch_ready"):
        load_aas_product_fork_no_answer_pause_board(artifact_dir=tmp_path)


def test_loader_fails_closed_on_pause_board_forbidden_safe_claim(tmp_path):
    seed_sources(tmp_path)
    pause_board = build_aas_product_fork_no_answer_pause_board(artifact_dir=tmp_path)
    pause_board["safe_to_claim"].append("kk_v2_swarm_ready")
    (tmp_path / AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME).write_text(
        json.dumps(pause_board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_aas_product_fork_no_answer_pause_board(artifact_dir=tmp_path)
