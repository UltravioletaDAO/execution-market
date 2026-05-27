import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_portfolio_next_gate_board import (
    AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
    AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM,
    build_aas_portfolio_next_gate_board,
)
from mcp_server.city_ops.aas_portfolio_operator_authorization_packet import (
    AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME,
    AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SAFE_CLAIM,
    AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SCHEMA,
    PACKET_BLOCKED_CLAIMS,
    PACKET_FALSE_FLAGS,
    PACKET_ID,
    build_aas_portfolio_operator_authorization_packet,
    load_aas_portfolio_operator_authorization_packet,
    write_aas_portfolio_operator_authorization_packet,
)
from mcp_server.city_ops.aas_portfolio_promotion_ledger import (
    AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME,
    build_aas_portfolio_promotion_ledger,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    with (ARTIFACT_DIR / AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_board(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME).write_text(
        json.dumps(build_aas_portfolio_promotion_ledger(artifact_dir=tmp_path)),
        encoding="utf-8",
    )
    (tmp_path / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME).write_text(
        json.dumps(build_aas_portfolio_next_gate_board(artifact_dir=tmp_path)),
        encoding="utf-8",
    )


def test_operator_authorization_packet_matches_persisted_artifact_and_loader():
    packet = build_aas_portfolio_operator_authorization_packet()

    assert packet == read_packet()
    assert load_aas_portfolio_operator_authorization_packet() == packet
    assert packet["schema"] == AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SCHEMA
    assert packet["packet_id"] == PACKET_ID
    assert packet["scope"] == "internal_admin_operator_authorization_packet_only_no_customer_exposure"
    assert packet["source_board_file"] == AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME
    assert AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM in packet["safe_to_claim"]
    assert AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SAFE_CLAIM in packet["safe_to_claim"]


def test_packet_prepares_two_questions_without_recording_answers_or_approval():
    packet = build_aas_portfolio_operator_authorization_packet()

    assert packet["source_policy"] == "consume_only_persisted_aas_portfolio_next_gate_board_json"
    assert packet["summary"] == {
        "candidate_questions_prepared": 2,
        "operator_answers_recorded": 0,
        "candidates_selected_for_approval": 0,
        "human_approval_records_created": 0,
        "delivery_paths_authorized": 0,
        "families_kept_internal_admin_only_by_default": 5,
        "customer_copy_delivery_publication_route_pricing_dispatch_reputation_runtime_gps_worker_doctrine_approved": False,
    }
    assert packet["default_if_unanswered"] == "keep_all_families_internal_admin_only_no_promotion"
    assert [row["family_id"] for row in packet["candidate_rows"]] == [
        "retail_reality_as_a_service",
        "compliance_desk_as_a_service",
    ]
    assert [row["candidate_rank"] for row in packet["candidate_rows"]] == [1, 2]
    assert packet["operator_decision_form"]["chosen_answer"] is None
    assert packet["operator_decision_form"]["operator_answer_recorded"] is False
    assert packet["operator_decision_form"]["this_form_is_not_an_approval_record"] is True


def test_packet_keeps_customer_public_dispatch_runtime_and_doctrine_blocked():
    packet = build_aas_portfolio_operator_authorization_packet()

    for flag in PACKET_FALSE_FLAGS:
        assert packet[flag] is False
    for row in packet["candidate_rows"]:
        assert row["candidate_text_values_included"] is False
        assert row["authorized_delivery_path"] == "none_until_separate_operator_answer_artifact"
        for flag in [
            "operator_answer_recorded",
            "selected_for_approval",
            "human_operator_approval_recorded",
            "customer_copy_authorized",
            "customer_delivery_authorized",
            "publication_authorized",
            "public_or_catalog_route_ready",
            "pricing_or_customer_quote_ready",
            "queue_or_dispatch_ready",
            "reputation_attachment_ready",
            "live_acontext_runtime_parity",
            "exact_gps_or_raw_metadata_release_allowed",
            "private_operator_context_release_allowed",
            "domain_legal_regulator_emergency_safety_repair_insurance_or_dataset_claims_allowed",
            "worker_copyable_doctrine_ready",
        ]:
            assert row[flag] is False
    for claim in PACKET_BLOCKED_CLAIMS:
        assert claim in packet["do_not_claim_yet"]
        assert claim not in packet["safe_to_claim"]
    assert packet["still_blocked_claims"] == packet["do_not_claim_yet"]


def test_candidate_rows_name_required_future_inputs_but_no_candidate_text_values():
    packet = build_aas_portfolio_operator_authorization_packet()
    retail, compliance = packet["candidate_rows"]

    assert "already selected Retail Reality boundary" in retail["authorization_question"]
    assert "exact_selected_boundary_digest_from_retail_reality_request" in retail[
        "required_explicit_inputs"
    ]
    assert retail["answer_artifact_if_authorized"] == (
        "retail_reality_human_operator_approval_record_or_hold_record"
    )
    assert retail["default_without_answer"] == "keep_pending_status_card_not_approved"
    assert retail["candidate_text_values_included"] is False

    assert "what exact delivery path is authorized" in compliance["authorization_question"]
    assert "exact_delivery_path_or_none" in compliance["required_explicit_inputs"]
    assert compliance["answer_artifact_if_authorized"] == (
        "aas_single_boundary_delivery_publication_gate_or_hold_record"
    )
    assert compliance["default_without_answer"] == (
        "keep_internal_label_approval_only_no_delivery_path"
    )
    assert compliance["candidate_text_values_included"] is False


def test_write_operator_authorization_packet_persists_valid_artifact(tmp_path):
    seed_board(tmp_path)

    path = write_aas_portfolio_operator_authorization_packet(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME
    assert load_aas_portfolio_operator_authorization_packet(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_board_summary_promotion_fails_closed():
    board = build_aas_portfolio_next_gate_board()
    board = copy.deepcopy(board)
    board["summary"]["delivery_paths_authorized"] = 1
    board["summary"]["customer_delivery_approved"] = True

    with pytest.raises(CityOpsContractError, match="source promoted summary customer_delivery_approved"):
        build_aas_portfolio_operator_authorization_packet(source_board=board)


def test_source_board_row_promotion_fails_closed():
    board = build_aas_portfolio_next_gate_board()
    board = copy.deepcopy(board)
    board["next_gate_rows"][0]["this_board_approves_gate"] = True

    with pytest.raises(CityOpsContractError, match="source row promoted"):
        build_aas_portfolio_operator_authorization_packet(source_board=board)


def test_source_board_forbidden_safe_claim_fails_closed():
    board = build_aas_portfolio_next_gate_board()
    board = copy.deepcopy(board)
    board["safe_to_claim"].append("customer_delivery_approved")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_aas_portfolio_operator_authorization_packet(source_board=board)


def test_loader_fails_closed_on_packet_recorded_answer(tmp_path):
    seed_board(tmp_path)
    packet = build_aas_portfolio_operator_authorization_packet(artifact_dir=tmp_path)
    packet["operator_decision_form"]["operator_answer_recorded"] = True
    (tmp_path / AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="recorded answer"):
        load_aas_portfolio_operator_authorization_packet(artifact_dir=tmp_path)


def test_loader_fails_closed_on_candidate_delivery_path_promotion(tmp_path):
    seed_board(tmp_path)
    packet = build_aas_portfolio_operator_authorization_packet(artifact_dir=tmp_path)
    packet["candidate_rows"][1]["authorized_delivery_path"] = "email_customer_now"
    (tmp_path / AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="delivery path drift"):
        load_aas_portfolio_operator_authorization_packet(artifact_dir=tmp_path)
