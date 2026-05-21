import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_claim_quarantine_board import (
    AAS_CLAIM_QUARANTINE_BOARD_FILENAME,
    AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_BOARD_SCHEMA,
    BOARD_FALSE_FLAGS,
    QUARANTINE_BUCKETS,
    build_aas_claim_quarantine_board,
    load_aas_claim_quarantine_board,
    write_aas_claim_quarantine_board,
)
from mcp_server.city_ops.aas_cross_family_approval_state_matrix import (
    AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM,
    build_aas_cross_family_approval_state_matrix,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_board() -> dict:
    with (ARTIFACT_DIR / AAS_CLAIM_QUARANTINE_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )


def test_board_matches_persisted_artifact_and_loader():
    board = build_aas_claim_quarantine_board()

    assert board == read_board()
    assert load_aas_claim_quarantine_board() == board
    assert board["schema"] == AAS_CLAIM_QUARANTINE_BOARD_SCHEMA
    assert board["scope"] == "internal_admin_claim_quarantine_board_only_no_customer_exposure"
    assert board["board_status"] == "all_launch_customer_runtime_and_authority_claims_quarantined"
    assert AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM in board["safe_to_claim"]


def test_board_quarantines_customer_public_runtime_reputation_and_authority_claims():
    board = build_aas_claim_quarantine_board()
    claims = set(board["quarantined_claims"])

    for bucket in QUARANTINE_BUCKETS:
        assert set(bucket["claims"]).issubset(claims)
    for claim in [
        "customer_delivery_approved",
        "publication_approved",
        "public_price_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "live_acontext_runtime_parity",
        "payment_production_reverified",
        "exact_gps_or_raw_metadata_release_allowed",
        "domain_authority_ready",
    ]:
        assert claim in board["do_not_claim_yet"]
        assert claim not in board["safe_to_claim"]


def test_bucket_cards_are_internal_admin_only_and_launch_blocked():
    board = build_aas_claim_quarantine_board()

    assert [bucket["bucket_id"] for bucket in board["quarantine_buckets"]] == [
        bucket["bucket_id"] for bucket in QUARANTINE_BUCKETS
    ]
    for bucket in board["quarantine_buckets"]:
        assert bucket["status"] == "quarantined_not_safe_to_claim"
        assert bucket["safe_to_use_now"] == "internal_admin_review_and_planning_only"
        assert bucket["may_publish_or_launch"] is False
        assert bucket["next_smallest_proof"]
        assert set(bucket["source_matrix_zero_counts"].values()) == {0}


def test_family_hold_cards_preserve_matrix_hold_state_without_delivery_authorization():
    board = build_aas_claim_quarantine_board()
    cards = {card["family_id"]: card for card in board["family_hold_cards"]}

    assert list(cards) == [
        "compliance_desk_as_a_service",
        "document_handoff_logistics_as_a_service",
        "incident_verification_as_a_service",
    ]
    assert cards["compliance_desk_as_a_service"]["human_operator_approval_record_exists"] is True
    assert cards["compliance_desk_as_a_service"]["selected_boundary_approved"] is True
    for card in cards.values():
        assert card["claim_quarantine_status"] == "held_until_named_next_smallest_proof"
        assert card["authorized_delivery_path_authorized"] is False
        assert card["customer_delivery_authorized"] is False
        assert card["publication_authorized"] is False


def test_safe_and_blocked_boundaries_stay_adjacent_and_non_overlapping():
    board = build_aas_claim_quarantine_board()
    key_order = list(board.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM in board["safe_to_claim"]
    assert AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM in board["safe_to_claim"]
    assert not set(board["safe_to_claim"]) & set(board["do_not_claim_yet"])
    assert board["still_blocked_claims"] == board["do_not_claim_yet"]


def test_false_flags_and_summary_keep_all_launch_counts_at_zero():
    board = build_aas_claim_quarantine_board()

    for flag in BOARD_FALSE_FLAGS:
        assert board[flag] is False
    summary = board["matrix_summary_snapshot"]
    assert summary["family_count"] == 3
    assert summary["families_with_human_approval_record"] == 1
    for key in [
        "families_with_delivery_authorization",
        "families_publishable",
        "families_with_public_or_catalog_routes",
        "families_ready_for_dispatch",
        "families_with_reputation_attachment_ready",
        "families_with_live_acontext_runtime_parity",
        "families_allowed_to_release_exact_gps_or_raw_metadata",
    ]:
        assert summary[key] == 0


def test_write_board_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_claim_quarantine_board(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_CLAIM_QUARANTINE_BOARD_FILENAME
    assert load_aas_claim_quarantine_board(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_matrix_delivery_promotion_fails_closed():
    matrix = build_aas_cross_family_approval_state_matrix()
    matrix = copy.deepcopy(matrix)
    matrix["matrix_summary"]["families_with_delivery_authorization"] = 1

    with pytest.raises(CityOpsContractError, match="source matrix promoted families_with_delivery_authorization"):
        build_aas_claim_quarantine_board(matrix=matrix)


def test_source_matrix_forbidden_safe_claim_fails_closed():
    matrix = build_aas_cross_family_approval_state_matrix()
    matrix = copy.deepcopy(matrix)
    matrix["safe_to_claim"].append("customer_delivery_approved")

    with pytest.raises(CityOpsContractError, match="source matrix forbidden safe claims"):
        build_aas_claim_quarantine_board(matrix=matrix)


def test_loader_fails_closed_on_bucket_launch_flip(tmp_path):
    seed_sources(tmp_path)
    board = build_aas_claim_quarantine_board(artifact_dir=tmp_path)
    board["quarantine_buckets"][0]["may_publish_or_launch"] = True
    (tmp_path / AAS_CLAIM_QUARANTINE_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="bucket launch promoted"):
        load_aas_claim_quarantine_board(artifact_dir=tmp_path)
