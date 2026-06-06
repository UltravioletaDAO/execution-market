"""Tests for the internal/admin AAS strength-to-roadmap connection board."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_strength_connection_control_packet import (
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
    build_aas_strength_connection_control_packet,
    write_aas_strength_connection_control_packet,
)
from mcp_server.city_ops.aas_strength_roadmap_connection_board import (
    AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_FILENAME,
    AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SAFE_CLAIM,
    AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SCHEMA,
    AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_STATUS,
    BOARD_BLOCKED_CLAIMS,
    FALSE_FLAGS,
    build_aas_strength_roadmap_connection_board,
    load_aas_strength_roadmap_connection_board,
    write_aas_strength_roadmap_connection_board,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_ARTIFACT_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"
PACKAGE_ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_board() -> dict:
    return json.loads(
        (PROOF_ARTIFACT_DIR / AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_strength_roadmap_board_matches_persisted_artifact_and_loader() -> None:
    board = build_aas_strength_roadmap_connection_board()

    assert board == read_board()
    assert load_aas_strength_roadmap_connection_board() == board
    assert board["schema"] == AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SCHEMA
    assert board["board_status"] == AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_STATUS
    assert AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM in board["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in board["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SAFE_CLAIM in board["claim_boundaries"][
        "safe_to_claim"
    ]


def test_strength_roadmap_board_consumes_sources_by_digest() -> None:
    board = build_aas_strength_roadmap_connection_board()

    assert board["source_strength_packet"]["file"] == "aas_strength_connection_control_packet.json"
    assert board["source_roadmap"]["file"] == "aas_concept_gap_implementation_roadmap.json"
    assert len(board["source_strength_packet"]["digest_sha256"]) == 64
    assert len(board["source_roadmap"]["digest_sha256"]) == 64


def test_strength_roadmap_board_connects_five_strengths_to_held_roadmap_lanes() -> None:
    board = build_aas_strength_roadmap_connection_board()
    cards = board["strength_to_roadmap_cards"]

    assert [card["strength"] for card in cards] == [
        "latest_city_ops_code_and_fixture_graph",
        "eight_chain_payment_integration_confidence",
        "reviewed_memory_and_insight_structure",
        "production_infrastructure_operational_confidence",
        "agent_coordination_observability_and_success_metrics",
    ]
    assert cards[2]["primary_roadmap_lanes"] == ["system_integration_runtime_memory"]
    assert "not_live_write_retrieve_parity" in cards[2]["blocked_promotion"]
    assert all(card["blocked_promotion"] for card in cards)

    snapshot = board["roadmap_lane_order_snapshot"]
    assert [row["planning_sequence_rank"] for row in snapshot] == list(range(1, 10))
    assert snapshot[0]["aas_family"] == "retail_reality"
    assert snapshot[-1]["aas_family"] == "system_integration_runtime_memory"
    assert all(row["still_blocked"] is True for row in snapshot)


def test_strength_roadmap_board_records_no_answer_runtime_product_or_reputation_movement() -> None:
    board = build_aas_strength_roadmap_connection_board()

    for key, expected in FALSE_FLAGS.items():
        assert board["readiness"][key] is expected
    assert board["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_product_lane": None,
        "recommended_no_human_posture": "pause_aas_proof_layering_or_keep_both_lanes_held",
    }
    assert board["one_next_proof_rule"]["runtime_memory_lane_condition"] == (
        "only_read_only_prerequisite_inventory_after_explicit_runtime_memory_answer"
    )


def test_strength_roadmap_board_preserves_claim_boundaries_and_stopped_project_firewall() -> None:
    board = build_aas_strength_roadmap_connection_board()
    safe = set(board["claim_boundaries"]["safe_to_claim"])
    blocked = set(board["claim_boundaries"]["do_not_claim_yet"])

    assert set(BOARD_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "operator_answer",
        "customer_public_or_worker_surface",
        "quote_route_queue_or_dispatch",
        "worker_skill_dna",
        "live_acontext",
        "irc_session_manager_runtime",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert board["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_strength_roadmap_board_write_roundtrip(tmp_path: Path) -> None:
    proof_dir = tmp_path / "proof"
    package_dir = tmp_path / "package"
    _copy_default_proof_sources(proof_dir)
    write_aas_strength_connection_control_packet(artifact_dir=proof_dir)
    write_aas_concept_gap_matrix(artifact_dir=package_dir)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=package_dir)

    path = write_aas_strength_roadmap_connection_board(
        proof_artifact_dir=proof_dir,
        package_artifact_dir=package_dir,
    )

    assert path == proof_dir / AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_FILENAME
    assert load_aas_strength_roadmap_connection_board(
        proof_artifact_dir=proof_dir,
        package_artifact_dir=package_dir,
    )["board_id"] == "execution_market.aas.strength_roadmap_connection_board.2026_06_06_0300"


def test_strength_roadmap_board_rejects_promoted_strength_packet() -> None:
    packet = copy.deepcopy(build_aas_strength_connection_control_packet())
    packet["readiness"]["live_acontext_memory_integration_ready"] = True

    with pytest.raises(CityOpsContractError, match="live_acontext_memory_integration_ready"):
        build_aas_strength_roadmap_connection_board(strength_packet=packet)


def test_strength_roadmap_board_rejects_selected_product_lane() -> None:
    board = build_aas_strength_roadmap_connection_board()
    board["current_operator_state"]["selected_product_lane"] = "retail_reality"

    with pytest.raises(CityOpsContractError, match="selected a product lane"):
        load_aas_strength_roadmap_connection_board(
            proof_artifact_dir=_write_source_pair_and_board(board),
            package_artifact_dir=PACKAGE_ARTIFACT_DIR,
        )


def _write_source_pair_and_board(board: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    _copy_default_proof_sources(tmp)
    write_aas_strength_connection_control_packet(artifact_dir=tmp)
    (tmp / AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_FILENAME).write_text(
        json.dumps(board, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp


def _copy_default_proof_sources(target: Path) -> None:
    shutil.copytree(PROOF_ARTIFACT_DIR, target, dirs_exist_ok=True)
