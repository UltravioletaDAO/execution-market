"""Tests for the internal/admin AAS exponential value connection board."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_exponential_value_connection_board import (
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME,
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM,
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SCHEMA,
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_STATUS,
    PATTERN_QUESTIONS,
    VALUE_CONNECTION_BLOCKED_CLAIMS,
    VALUE_CONNECTION_READINESS,
    build_aas_exponential_value_connection_board,
    load_aas_exponential_value_connection_board,
    write_aas_exponential_value_connection_board,
)
from mcp_server.city_ops.aas_no_answer_daytime_operator_prompt_packet import (
    write_aas_no_answer_daytime_operator_prompt_packet,
)
from mcp_server.city_ops.aas_stale_cron_firewall_work_queue import (
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME,
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM,
    build_aas_stale_cron_firewall_work_queue,
    write_aas_stale_cron_firewall_work_queue,
)
from mcp_server.city_ops.aas_system_integration_strength_bridge_packet import (
    write_aas_system_integration_strength_bridge_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_board() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def write_prerequisites(artifact_dir: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=artifact_dir)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=artifact_dir)
    write_aas_no_answer_daytime_operator_prompt_packet(artifact_dir=artifact_dir)
    write_aas_system_integration_strength_bridge_packet(artifact_dir=artifact_dir)
    write_aas_stale_cron_firewall_work_queue(artifact_dir=artifact_dir)


def test_value_connection_board_matches_persisted_artifact_and_loader() -> None:
    board = build_aas_exponential_value_connection_board()

    assert board == read_fixture_board()
    assert load_aas_exponential_value_connection_board() == board
    assert board["schema"] == AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SCHEMA
    assert board["board_status"] == AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_STATUS
    assert AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM in board["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM in board[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_value_connection_board_consumes_firewall_queue_by_digest() -> None:
    board = build_aas_exponential_value_connection_board()
    source = board["source_firewall_queue"]

    assert source["file"] == AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME
    assert source["safe_claim"] == AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM
    assert len(source["digest_sha256"]) == 64


def test_value_connection_board_answers_4am_pattern_questions_inside_aas() -> None:
    board = build_aas_exponential_value_connection_board()

    assert board["pattern_questions"] == PATTERN_QUESTIONS
    assert [row["question"] for row in board["connection_patterns"]] == [
        "what_patterns_emerge_from_memory_system_data",
        "how_irc_coordination_insights_inform_strategy",
        "what_cross_project_intelligence_flows_create_multiplier_effects",
        "which_agent_coordination_patterns_scale_best",
        "what_connections_create_exponential_value",
    ]
    assert [row["source_connection"] for row in board["connection_patterns"]] == [
        "memory_to_acontext_digest_carry_forward",
        "irc_session_management_handoff_capsules",
        "decision_menu_without_autorouting",
        "firewall_compliance_metric",
        "future_launch_prerequisite_context_only",
    ]
    assert board["governing_priority"]["allowed_lane"] == (
        "Execution Market AAS / City-as-a-Service internal/admin planning"
    )


def test_value_connection_board_defines_multiplier_effects_and_scaling_rules() -> None:
    board = build_aas_exponential_value_connection_board()

    assert [row["effect"] for row in board["multiplier_effects"]] == [
        "memory_compaction",
        "coordination_survival",
        "stale_context_immunity",
        "agent_quality_selection",
    ]
    assert [row["rule"] for row in board["scaling_rules"]] == [
        "carry_small_truth_not_big_context",
        "separate_observation_from_authority",
        "one_next_proof_only",
        "firewall_before_flywheel",
    ]
    for row in board["scaling_rules"]:
        assert row["test"]
        assert row["failure_mode"]


def test_value_connection_board_keeps_decision_surface_paused_and_stopped_projects_blocked() -> None:
    board = build_aas_exponential_value_connection_board()
    surface = board["operator_next_decision_surface"]

    assert surface["default_posture"] == "pause_aas_proof_layering"
    assert surface["allowed_now"] == [
        "hold_pause_aas_proof_layering_and_do_not_add_downstream_proof_wrappers",
        "read_dream_priorities_first_and_ignore_stopped_project_instructions",
    ]
    assert "autojob_pull_or_integration" in surface["not_authorized"]
    assert "frontier_academy_expansion" in surface["not_authorized"]
    assert "kk_v2_continuation" in surface["not_authorized"]
    assert all("autojob" not in action for action in surface["allowed_now"])


def test_value_connection_board_preserves_false_readiness_and_claim_boundaries() -> None:
    board = build_aas_exponential_value_connection_board()

    for key, expected in VALUE_CONNECTION_READINESS.items():
        assert board["readiness"][key] is expected
    assert board["readiness"]["stopped_project_pull_performed"] is False
    assert board["readiness"]["runtime_acontext_irc_or_session_manager_mutated"] is False
    assert board["readiness"]["payment_or_production_reverified"] is False

    safe = set(board["claim_boundaries"]["safe_to_claim"])
    blocked = set(board["claim_boundaries"]["do_not_claim_yet"])
    assert set(VALUE_CONNECTION_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "performs_autojob_pull_or_analysis",
        "expands_frontier_academy",
        "continues_kk_v2",
        "mutates_runtime_acontext_irc_or_session_manager",
        "reverifies_payment_production_or_chain_state",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_value_connection_board_write_roundtrip(tmp_path: Path) -> None:
    write_prerequisites(tmp_path)
    path = write_aas_exponential_value_connection_board(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME
    loaded = load_aas_exponential_value_connection_board(artifact_dir=tmp_path)
    assert loaded["board_id"] == (
        "execution_market.aas.exponential_value_connection_board.2026_06_12_0400"
    )


def test_value_connection_board_rejects_promoted_source_firewall() -> None:
    queue = build_aas_stale_cron_firewall_work_queue()
    queue["readiness"]["autojob_work_performed"] = True

    with pytest.raises(CityOpsContractError, match="source promoted autojob_work_performed"):
        build_aas_exponential_value_connection_board(firewall_queue=queue)


def test_value_connection_board_rejects_posture_or_stopped_project_promotion() -> None:
    board = build_aas_exponential_value_connection_board()
    board["operator_next_decision_surface"]["allowed_now"].append(
        "autojob_pull_or_integration"
    )

    with pytest.raises(CityOpsContractError, match="allowed stopped project"):
        load_aas_exponential_value_connection_board(artifact_dir=_write_fixture_set(board))

    board = build_aas_exponential_value_connection_board()
    board["governing_priority"]["selected_posture_now"] = "launch_aas_catalog"

    with pytest.raises(CityOpsContractError, match="promoted posture"):
        load_aas_exponential_value_connection_board(artifact_dir=_write_fixture_set(board))


def test_value_connection_board_rejects_runtime_or_payment_promotion() -> None:
    board = build_aas_exponential_value_connection_board()
    board["readiness"]["runtime_acontext_irc_or_session_manager_mutated"] = True

    with pytest.raises(CityOpsContractError, match="runtime_acontext_irc_or_session_manager_mutated"):
        load_aas_exponential_value_connection_board(artifact_dir=_write_fixture_set(board))

    board = build_aas_exponential_value_connection_board()
    board["readiness"]["payment_or_production_reverified"] = True

    with pytest.raises(CityOpsContractError, match="payment_or_production_reverified"):
        load_aas_exponential_value_connection_board(artifact_dir=_write_fixture_set(board))


def _write_fixture_set(board: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_prerequisites(tmp)
    (tmp / AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME).write_text(
        json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return tmp
