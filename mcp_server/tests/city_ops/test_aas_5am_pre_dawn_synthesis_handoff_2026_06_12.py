"""Tests for the June 12 5 AM AAS pre-dawn synthesis handoff."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_5am_pre_dawn_synthesis_handoff_2026_06_12 import (
    AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_FILENAME,
    AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SAFE_CLAIM,
    AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SCHEMA,
    AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_STATUS,
    FIVE_AM_2026_06_12_BLOCKED_CLAIMS,
    FIVE_AM_2026_06_12_READINESS,
    build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12,
    load_aas_5am_pre_dawn_synthesis_handoff_2026_06_12,
    write_aas_5am_pre_dawn_synthesis_handoff_2026_06_12,
)
from mcp_server.city_ops.aas_exponential_value_connection_board import (
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME,
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_handoff() -> dict:
    return json.loads(
        (
            ARTIFACT_DIR / AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_FILENAME
        ).read_text(encoding="utf-8")
    )


def seed_sources(tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)


def test_handoff_matches_persisted_artifact_and_loader() -> None:
    handoff = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12()

    assert handoff == read_handoff()
    assert load_aas_5am_pre_dawn_synthesis_handoff_2026_06_12() == handoff
    assert handoff["schema"] == AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SCHEMA
    assert handoff["handoff_status"] == AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_STATUS
    assert AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM in handoff[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SAFE_CLAIM in handoff[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_handoff_consumes_only_the_4am_connection_board() -> None:
    handoff = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12()

    assert handoff["source_connection_board"]["file"] == AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME
    assert len(handoff["source_connection_board"]["digest_sha256"]) == 64
    assert handoff["governing_priority"]["source_precedence"] == (
        "dream_priorities_wins_over_stale_cron_payload"
    )
    assert handoff["governing_priority"]["selected_posture_now"] == "pause_aas_proof_layering"


def test_handoff_records_no_answer_or_external_promotion() -> None:
    handoff = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12()

    for key, expected in FIVE_AM_2026_06_12_READINESS.items():
        assert handoff["readiness"][key] is expected


def test_handoff_synthesizes_requested_system_connections() -> None:
    handoff = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12()
    systems = {row["system"]: row for row in handoff["night_synthesis"]}

    assert set(systems) == {
        "memory_system",
        "acontext_and_runtime_memory",
        "irc_session_coordination",
        "execution_market_aas_strategy",
    }
    assert "digest-backed safe claims" in systems["memory_system"]["daytime_use"]
    assert "prerequisite gates" in systems["acontext_and_runtime_memory"]["daytime_use"]
    assert "compact source refs" in systems["irc_session_coordination"]["daytime_use"]
    assert "stale-context detection" in systems["execution_market_aas_strategy"]["daytime_use"]


def test_handoff_prepares_actionable_daytime_queue_and_memory_packet() -> None:
    handoff = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12()
    actions = {row["action"]: row for row in handoff["daytime_priority_queue"]}

    assert actions["keep_pause_aas_proof_layering"]["priority"] == "P0"
    assert "real allowed answer" in actions[
        "if_saúl_answers_create_one_digest_backed_answer_receipt"
    ]["why"]
    assert handoff["memory_update_packet"]["write_to_daily_memory"] is True
    assert handoff["memory_update_packet"]["write_to_long_term_memory"] is False
    assert len(handoff["memory_update_packet"]["source_board_digest_sha256"]) == 64


def test_handoff_preserves_blocked_claims() -> None:
    handoff = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12()
    safe = set(handoff["claim_boundaries"]["safe_to_claim"])
    blocked = set(handoff["claim_boundaries"]["do_not_claim_yet"])

    assert set(FIVE_AM_2026_06_12_BLOCKED_CLAIMS) <= blocked
    assert not safe & blocked
    assert "five_am_2026_06_12_works_on_autojob_frontier_academy_kk_v2_or_karmacadabra" in blocked
    assert "five_am_2026_06_12_performs_live_acontext_write_or_retrieve" in blocked
    assert "five_am_2026_06_12_emits_erc8004_reputation_or_worker_skill_dna" in blocked


def test_handoff_write_roundtrip_with_tmp_sources(tmp_path: Path) -> None:
    seed_sources(tmp_path)

    path = write_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_FILENAME
    assert load_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(artifact_dir=tmp_path)[
        "handoff_status"
    ] == AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_STATUS


def test_handoff_rejects_promoted_source_board() -> None:
    board = json.loads(
        (ARTIFACT_DIR / AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    promoted = copy.deepcopy(board)
    promoted["readiness"]["future_answer_selected"] = True

    with pytest.raises(CityOpsContractError, match="future_answer_selected"):
        build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(
            connection_board=promoted
        )


def test_handoff_rejects_forbidden_safe_claim() -> None:
    board = json.loads(
        (ARTIFACT_DIR / AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    promoted = copy.deepcopy(board)
    promoted["claim_boundaries"]["safe_to_claim"].append("dispatch_ready")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(
            connection_board=promoted
        )


def test_handoff_rejects_digest_drift_in_persisted_packet(tmp_path: Path) -> None:
    seed_sources(tmp_path)
    path = write_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(artifact_dir=tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["handoff_digest_sha256"] = "0" * 64
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="digest mismatch"):
        load_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(artifact_dir=tmp_path)
