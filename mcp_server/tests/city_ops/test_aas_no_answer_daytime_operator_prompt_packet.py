"""Tests for the internal/admin AAS no-answer daytime prompt packet."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    build_aas_concept_gap_implementation_roadmap,
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_no_answer_daytime_operator_prompt_packet import (
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM,
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SCHEMA,
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_STATUS,
    FALSE_FLAGS,
    PROMPT_ALLOWED_ANSWER_VALUES,
    PROMPT_BLOCKED_CLAIMS,
    REQUIRED_PROMPT_FIELDS,
    build_aas_no_answer_daytime_operator_prompt_packet,
    load_aas_no_answer_daytime_operator_prompt_packet,
    write_aas_no_answer_daytime_operator_prompt_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_packet() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_prompt_packet_matches_persisted_artifact_and_loader() -> None:
    packet = build_aas_no_answer_daytime_operator_prompt_packet()

    assert packet == read_fixture_packet()
    assert load_aas_no_answer_daytime_operator_prompt_packet() == packet
    assert packet["schema"] == AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SCHEMA
    assert packet["packet_status"] == AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_STATUS
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in packet["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_prompt_packet_consumes_all_roadmap_rows_by_digest() -> None:
    packet = build_aas_no_answer_daytime_operator_prompt_packet()
    source = packet["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_rows"] == 9
    assert len(source["digest_sha256"]) == 64


def test_prompt_packet_is_inert_until_separate_answer_receipt() -> None:
    packet = build_aas_no_answer_daytime_operator_prompt_packet()

    for key, expected in FALSE_FLAGS.items():
        assert packet["readiness"][key] is expected
    assert packet["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "ask_for_one_explicit_operator_answer_or_hold_all_lanes",
    }

    prompt = packet["daytime_prompt_packet"]
    assert prompt["allowed_use"] == "internal_admin_daytime_prompt_packet_only"
    assert prompt["prompt_goal"] == "obtain_one_explicit_operator_answer_or_hold_without_creating_permission"
    assert prompt["next_gate_after_any_human_answer"] == "write_separate_answer_receipt_then_run_specific_gate"
    assert prompt["still_blocked"] is True


def test_prompt_packet_answer_choices_are_exact_and_blocked_before_receipt() -> None:
    packet = build_aas_no_answer_daytime_operator_prompt_packet()
    prompt = packet["daytime_prompt_packet"]

    assert set(REQUIRED_PROMPT_FIELDS) <= set(prompt["required_prompt_fields"])
    assert prompt["allowed_answer_values"] == PROMPT_ALLOWED_ANSWER_VALUES
    assert [choice["answer_value"] for choice in prompt["answer_choices"]] == (
        PROMPT_ALLOWED_ANSWER_VALUES
    )
    assert len(prompt["answer_choices"]) == 12

    family_choices = [
        choice for choice in prompt["answer_choices"] if choice["answer_value"].startswith("answer_")
    ]
    assert len(family_choices) == 10
    for choice in family_choices:
        assert choice["allowed_follow_on_before_answer_receipt"] == "none"
        assert choice["required_next_gate"] == "separate_explicit_operator_answer_receipt_then_specific_gate"
        assert choice["still_blocked_until_answer_receipt"] is True

    assert "one named family boundary answer" in prompt["recommended_prompt_text"]
    assert "separate answer receipt" in prompt["recommended_prompt_text"]
    assert "stopped-project movement" in prompt["recommended_prompt_text"]


def test_prompt_packet_preserves_claim_boundaries_and_firewall() -> None:
    packet = build_aas_no_answer_daytime_operator_prompt_packet()
    safe = set(packet["claim_boundaries"]["safe_to_claim"])
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])

    assert set(PROMPT_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "treats_prompt_as_permission",
        "approves_catalog_pricing_quote_route_queue_or_dispatch",
        "attaches_reputation_worker_skill_dna_or_portable_credential",
        "mutates_runtime_acontext_irc_or_session_manager",
        "releases_exact_gps_raw_metadata_private_context_or_pii",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert packet["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_prompt_packet_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_no_answer_daytime_operator_prompt_packet(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME
    assert load_aas_no_answer_daytime_operator_prompt_packet(artifact_dir=tmp_path)[
        "packet_id"
    ] == "execution_market.aas.no_answer_daytime_operator_prompt_packet.2026_06_07_0200"


def test_prompt_packet_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["answer_receipt_created"] = True

    with pytest.raises(CityOpsContractError, match="answer_receipt_created"):
        build_aas_no_answer_daytime_operator_prompt_packet(source_roadmap=roadmap)


def test_prompt_packet_rejects_runtime_no_answer_posture_drift() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "system_integration_runtime_memory":
            row["next_allowed_without_human_answer"] = "runtime_inventory_allowed"

    with pytest.raises(CityOpsContractError, match="runtime no-answer posture drift"):
        build_aas_no_answer_daytime_operator_prompt_packet(source_roadmap=roadmap)


def test_prompt_packet_rejects_runtime_or_dispatch_promotion() -> None:
    packet = build_aas_no_answer_daytime_operator_prompt_packet()
    packet["readiness"]["packet_mutates_runtime_acontext_irc_or_session_manager"] = True

    with pytest.raises(CityOpsContractError, match="mutates_runtime_acontext_irc_or_session_manager"):
        load_aas_no_answer_daytime_operator_prompt_packet(
            artifact_dir=_write_fixture_triple(packet)
        )

    packet = build_aas_no_answer_daytime_operator_prompt_packet()
    packet["readiness"]["packet_launches_dispatch_or_worker_instruction"] = True

    with pytest.raises(CityOpsContractError, match="launches_dispatch_or_worker_instruction"):
        load_aas_no_answer_daytime_operator_prompt_packet(
            artifact_dir=_write_fixture_triple(packet)
        )


def test_prompt_packet_rejects_early_follow_on_or_missing_field() -> None:
    packet = build_aas_no_answer_daytime_operator_prompt_packet()
    packet["daytime_prompt_packet"]["answer_choices"][1][
        "allowed_follow_on_before_answer_receipt"
    ] = "dispatch_allowed"

    with pytest.raises(CityOpsContractError, match="allowed follow-on too early"):
        load_aas_no_answer_daytime_operator_prompt_packet(
            artifact_dir=_write_fixture_triple(packet)
        )

    packet = build_aas_no_answer_daytime_operator_prompt_packet()
    packet["daytime_prompt_packet"]["required_prompt_fields"] = [
        field
        for field in packet["daytime_prompt_packet"]["required_prompt_fields"]
        if field != "answer_receipt_required_before_any_follow_on_gate"
    ]

    with pytest.raises(CityOpsContractError, match="missing prompt fields"):
        load_aas_no_answer_daytime_operator_prompt_packet(
            artifact_dir=_write_fixture_triple(packet)
        )


def _write_fixture_triple(packet: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME).write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return tmp
