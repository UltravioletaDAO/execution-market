import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_portfolio_next_gate_board import (
    AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
    AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM,
    AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA,
    BOARD_BLOCKED_CLAIMS,
    BOARD_FALSE_FLAGS,
    BOARD_ID,
    build_aas_portfolio_next_gate_board,
    load_aas_portfolio_next_gate_board,
    write_aas_portfolio_next_gate_board,
)
from mcp_server.city_ops.aas_portfolio_promotion_ledger import (
    AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME,
    AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM,
    build_aas_portfolio_promotion_ledger,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_board() -> dict:
    with (ARTIFACT_DIR / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_ledger(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME).write_text(
        json.dumps(build_aas_portfolio_promotion_ledger(artifact_dir=tmp_path)),
        encoding="utf-8",
    )


def test_next_gate_board_matches_persisted_artifact_and_loader():
    board = build_aas_portfolio_next_gate_board()

    assert board == read_board()
    assert load_aas_portfolio_next_gate_board() == board
    assert board["schema"] == AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA
    assert board["board_id"] == BOARD_ID
    assert board["scope"] == "internal_admin_next_gate_board_only_no_customer_exposure"
    assert board["source_ledger_file"] == AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME
    assert AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM in board["safe_to_claim"]
    assert AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM in board["safe_to_claim"]


def test_board_ranks_exactly_one_next_gate_menu_without_approval():
    board = build_aas_portfolio_next_gate_board()

    assert board["source_policy"] == "consume_only_persisted_aas_portfolio_promotion_ledger_json"
    assert board["summary"]["families_on_board"] == 5
    assert board["summary"]["candidate_human_review_gates"] == 2
    assert board["summary"]["internal_prerequisite_gates"] == 3
    assert board["summary"]["gates_ready_without_separate_authorization"] == 0
    assert [row["family_id"] for row in board["next_gate_rows"]] == [
        "retail_reality_as_a_service",
        "compliance_desk_as_a_service",
        "document_handoff_logistics_as_a_service",
        "incident_verification_as_a_service",
        "local_data_collection_as_a_service",
    ]
    assert [row["rank"] for row in board["next_gate_rows"]] == [1, 2, 3, 4, 5]
    assert board["next_gate_rows"][0]["human_authorization_required"] is True
    assert board["next_gate_rows"][0]["next_gate_action"] == (
        "create_separate_human_operator_approval_record_only_if_explicitly_authorized"
    )
    assert board["operator_review_menu"]["ranked_first_choice"] == "retail_reality_as_a_service"
    assert board["default_decision"]["this_board_is_not_the_approval_record"] is True


def test_board_keeps_customer_public_dispatch_runtime_and_worker_doctrine_blocked():
    board = build_aas_portfolio_next_gate_board()

    for key in [
        "customer_copy_approved",
        "customer_delivery_approved",
        "publication_approved",
        "public_or_catalog_routes_approved",
        "public_prices_or_customer_quotes_approved",
        "queue_dispatch_reputation_runtime_gps_worker_doctrine_approved",
    ]:
        assert board["summary"][key] is False
    for flag in BOARD_FALSE_FLAGS:
        assert board[flag] is False
    for row in board["next_gate_rows"]:
        for flag in [
            "this_board_approves_gate",
            "customer_delivery_authorized",
            "publication_authorized",
            "public_or_catalog_route_ready",
            "pricing_or_customer_quote_ready",
            "queue_or_dispatch_ready",
            "reputation_attachment_ready",
            "live_acontext_runtime_parity",
            "exact_gps_or_raw_metadata_release_allowed",
            "worker_copyable_doctrine_ready",
        ]:
            assert row[flag] is False
    for claim in BOARD_BLOCKED_CLAIMS:
        assert claim in board["do_not_claim_yet"]
        assert claim not in board["safe_to_claim"]


def test_operator_menu_names_allowed_and_forbidden_paths():
    board = build_aas_portfolio_next_gate_board()
    menu = board["operator_review_menu"]

    assert "keep_all_families_internal_admin_only" in menu["allowed_actions"]
    assert (
        "create_one_separate_human_operator_approval_record_for_rank_1_or_rank_2_only_if_explicitly_authorized"
        in menu["allowed_actions"]
    )
    assert "approve_customer_copy_delivery_or_publication_from_this_board" in menu[
        "forbidden_actions"
    ]
    assert "mount_public_or_catalog_routes_from_this_board" in menu["forbidden_actions"]
    assert "publish_prices_or_customer_quotes_from_this_board" in menu["forbidden_actions"]
    assert "launch_operator_queue_or_dispatch_from_this_board" in menu["forbidden_actions"]
    assert "attach_ERC_8004_reputation_from_this_board" in menu["forbidden_actions"]
    assert "claim_live_Acontext_runtime_parity_from_this_board" in menu["forbidden_actions"]
    assert (
        "release_exact_GPS_raw_metadata_or_private_operator_context_from_this_board"
        in menu["forbidden_actions"]
    )
    assert "publish_worker_copyable_AAS_doctrine_from_this_board" in menu[
        "forbidden_actions"
    ]


def test_write_next_gate_board_persists_valid_artifact(tmp_path):
    seed_ledger(tmp_path)

    path = write_aas_portfolio_next_gate_board(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME
    assert load_aas_portfolio_next_gate_board(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_ledger_summary_promotion_fails_closed():
    ledger = build_aas_portfolio_promotion_ledger()
    ledger = copy.deepcopy(ledger)
    ledger["ledger_summary"]["families_ready_for_queue_or_dispatch"] = 1

    with pytest.raises(CityOpsContractError, match="source promoted summary"):
        build_aas_portfolio_next_gate_board(source_ledger=ledger)


def test_source_ledger_row_promotion_fails_closed():
    ledger = build_aas_portfolio_promotion_ledger()
    ledger = copy.deepcopy(ledger)
    ledger["family_rows"][0]["public_or_catalog_route_ready"] = True

    with pytest.raises(CityOpsContractError, match="source row promoted"):
        build_aas_portfolio_next_gate_board(source_ledger=ledger)


def test_source_ledger_forbidden_safe_claim_fails_closed():
    ledger = build_aas_portfolio_promotion_ledger()
    ledger = copy.deepcopy(ledger)
    ledger["safe_to_claim"].append("customer_delivery_approved")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_aas_portfolio_next_gate_board(source_ledger=ledger)


def test_loader_fails_closed_on_board_customer_delivery_promotion(tmp_path):
    seed_ledger(tmp_path)
    board = build_aas_portfolio_next_gate_board(artifact_dir=tmp_path)
    board["summary"]["customer_delivery_approved"] = True
    (tmp_path / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="summary drift customer_delivery_approved"):
        load_aas_portfolio_next_gate_board(artifact_dir=tmp_path)


def test_loader_fails_closed_on_board_row_gate_promotion(tmp_path):
    seed_ledger(tmp_path)
    board = build_aas_portfolio_next_gate_board(artifact_dir=tmp_path)
    board["next_gate_rows"][0]["this_board_approves_gate"] = True
    (tmp_path / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="row promoted"):
        load_aas_portfolio_next_gate_board(artifact_dir=tmp_path)
