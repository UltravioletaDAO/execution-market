"""Tests for the 5 AM AAS pre-dawn synthesis handoff."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_five_am_pre_dawn_synthesis_handoff import (
    AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME,
    AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
    AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA,
    AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_STATUS,
    FIVE_AM_SYNTHESIS_BLOCKED_CLAIMS,
    SYNTHESIS_FALSE_FLAGS,
    build_aas_five_am_pre_dawn_synthesis_handoff,
    load_aas_five_am_pre_dawn_synthesis_handoff,
    write_aas_five_am_pre_dawn_synthesis_handoff,
)
from mcp_server.city_ops.aas_four_am_pattern_recognition_multiplier_ladder import (
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME,
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_handoff() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)


def test_five_am_handoff_matches_persisted_artifact_and_loader() -> None:
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff()

    assert handoff == read_handoff()
    assert load_aas_five_am_pre_dawn_synthesis_handoff() == handoff
    assert handoff["schema"] == AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA
    assert handoff["handoff_status"] == AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_STATUS
    assert AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM in handoff[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM in handoff[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_five_am_handoff_consumes_only_four_am_ladder() -> None:
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff()

    assert handoff["source_pattern_ladder"]["file"] == AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME
    assert len(handoff["source_pattern_ladder"]["digest_sha256"]) == 64
    assert handoff["derived_from"]["read_only"] is True
    assert handoff["derived_from"]["source_artifacts"] == [
        AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME
    ]
    assert handoff["derived_from"]["consumes_only"] == [
        AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME
    ]
    assert "stopped_project_codebases_as_active_sources" in handoff["derived_from"][
        "forbidden_inputs"
    ]


def test_five_am_handoff_records_no_answer_or_external_promotion() -> None:
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff()

    for key, expected in SYNTHESIS_FALSE_FLAGS.items():
        assert handoff["readiness"][key] is expected
    for key, value in handoff["access_policy"].items():
        if key in {"audience", "requires_admin_context"}:
            continue
        assert value is False


def test_five_am_handoff_synthesizes_daytime_recommendations() -> None:
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff()
    recs = {rec["recommendation"]: rec for rec in handoff["daytime_recommendations"]}

    assert recs["pause_aas_proof_layering"]["priority"] == "P0"
    assert "explicit operator answer" in recs["pause_aas_proof_layering"]["why"]
    assert "Docker" in recs[
        "if_runtime_memory_lane_selected_restore_docker_then_rerun_read_only_inventory"
    ]["why"]
    assert "stopped projects" in recs["keep_stopped_project_firewall_visible"]["why"]


def test_five_am_handoff_connects_requested_systems_without_authority() -> None:
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff()
    systems = {card["system"]: card for card in handoff["integration_synthesis"]}

    assert set(systems) == {
        "memory_to_acontext",
        "irc_and_session_coordination",
        "cross_project_intelligence",
        "agent_coordination",
    }
    assert "do not write live memory" in systems["memory_to_acontext"]["daytime_use"]
    assert "source ref" in systems["irc_and_session_coordination"]["daytime_use"]
    assert "routing/firewall" in systems["cross_project_intelligence"]["daytime_use"]
    assert "boundary survival" in systems["agent_coordination"]["daytime_use"]


def test_five_am_handoff_consumes_handoff_packet_contract() -> None:
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff()
    contract = handoff["handoff_packet_contract_synthesis"]

    assert contract["source_contract_status"] == "required_for_future_agent_or_runtime_consumers"
    assert contract["fail_closed_posture"] == "pause_aas_proof_layering"
    assert set(contract["required_fields"]) == {
        "source_file",
        "source_digest_sha256",
        "safe_claim",
        "blocked_claims",
        "next_gate",
        "recommended_posture",
    }
    assert "missing_field_means_hold" in contract["consumer_rules_to_preserve"]
    assert "blocked_claims_travel_with_the_packet" in contract["consumer_rules_to_preserve"]
    assert contract["blocked_behavior_count"] >= 5

    cards = {card["card"]: card for card in handoff["handoff_cards"]}
    assert cards["handoff_packet_contract"]["source_contract_status"] == contract[
        "source_contract_status"
    ]


def test_five_am_handoff_preserves_blocked_claims() -> None:
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff()
    safe = set(handoff["claim_boundaries"]["safe_to_claim"])
    blocked = set(handoff["claim_boundaries"]["do_not_claim_yet"])

    assert set(FIVE_AM_SYNTHESIS_BLOCKED_CLAIMS) <= blocked
    assert not safe & blocked
    assert "five_am_synthesis_integrates_stopped_projects" in blocked
    assert "five_am_synthesis_writes_or_retrieves_live_acontext" in blocked
    assert "five_am_synthesis_emits_erc8004_reputation_or_worker_skill_dna" in blocked


def test_five_am_handoff_write_roundtrip_with_tmp_sources(tmp_path: Path) -> None:
    seed_sources(tmp_path)

    path = write_aas_five_am_pre_dawn_synthesis_handoff(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME
    assert load_aas_five_am_pre_dawn_synthesis_handoff(artifact_dir=tmp_path)[
        "handoff_verdict"
    ] == "five_am_pre_dawn_synthesis_landed_internal_only"


def test_five_am_handoff_rejects_source_ladder_promotion() -> None:
    ladder = json.loads(
        (ARTIFACT_DIR / AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME).read_text()
    )
    promoted = copy.deepcopy(ladder)
    promoted["readiness"]["pattern_ladder_records_operator_answer"] = True

    with pytest.raises(CityOpsContractError, match="pattern_ladder_records_operator_answer"):
        build_aas_five_am_pre_dawn_synthesis_handoff(ladder=promoted)


def test_five_am_handoff_rejects_forbidden_safe_claim() -> None:
    ladder = json.loads(
        (ARTIFACT_DIR / AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME).read_text()
    )
    promoted = copy.deepcopy(ladder)
    promoted["claim_boundaries"]["safe_to_claim"].append("dispatch_ready")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_aas_five_am_pre_dawn_synthesis_handoff(ladder=promoted)


def test_five_am_handoff_rejects_source_ladder_missing_packet_fields() -> None:
    ladder = json.loads(
        (ARTIFACT_DIR / AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME).read_text()
    )
    promoted = copy.deepcopy(ladder)
    promoted["handoff_packet_contract"]["required_fields"].remove("blocked_claims")

    with pytest.raises(CityOpsContractError, match="missing handoff packet fields"):
        build_aas_five_am_pre_dawn_synthesis_handoff(ladder=promoted)
