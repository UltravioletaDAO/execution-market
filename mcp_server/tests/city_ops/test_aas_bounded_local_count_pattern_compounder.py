"""Tests for the internal/admin Bounded Local Count pattern compounder."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_bounded_local_count_fixture_gate import (
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
    build_aas_bounded_local_count_fixture_gate,
)
from mcp_server.city_ops.aas_bounded_local_count_pattern_compounder import (
    AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_FILENAME,
    AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SAFE_CLAIM,
    AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SCHEMA,
    AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_STATUS,
    COMPOUNDER_BLOCKED_CLAIMS,
    COMPOUNDER_FALSE_FLAGS,
    PATTERN_QUESTIONS,
    build_aas_bounded_local_count_pattern_compounder,
    load_aas_bounded_local_count_pattern_compounder,
    write_aas_bounded_local_count_pattern_compounder,
)
from mcp_server.city_ops.aas_source_of_truth_index import (
    AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
    AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM,
    build_aas_source_of_truth_index,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_compounder() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        if source.name == AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)


def test_bounded_count_pattern_compounder_matches_persisted_artifact_and_loader() -> None:
    packet = build_aas_bounded_local_count_pattern_compounder()

    assert packet == read_compounder()
    assert load_aas_bounded_local_count_pattern_compounder() == packet
    assert packet["schema"] == AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SCHEMA
    assert packet["compounder_status"] == AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_STATUS
    assert AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM in packet["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM in packet["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_bounded_count_pattern_compounder_consumes_source_index_and_fixture_gate_by_digest() -> None:
    packet = build_aas_bounded_local_count_pattern_compounder()

    assert packet["source_index"]["file"] == AAS_SOURCE_OF_TRUTH_INDEX_FILENAME
    assert packet["source_index"]["safe_claim"] == AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM
    assert len(packet["source_index"]["digest_sha256"]) == 64
    assert packet["source_fixture_gate"]["file"] == AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME
    assert packet["source_fixture_gate"]["safe_claim"] == AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM
    assert len(packet["source_fixture_gate"]["digest_sha256"]) == 64


def test_bounded_count_pattern_compounder_answers_4am_questions_inside_aas_only() -> None:
    packet = build_aas_bounded_local_count_pattern_compounder()

    assert packet["pattern_questions"] == PATTERN_QUESTIONS
    assert [row["question"] for row in packet["pattern_compounder_rows"]] == PATTERN_QUESTIONS
    assert [row["pattern"] for row in packet["pattern_compounder_rows"]] == [
        "memory_compounds_when_it_stores_reviewed_count_fields_not_raw_context",
        "irc_coordination_scales_through_invariant_handoff_capsules",
        "cross_project_intelligence_is_a_stop_filter_before_it_is_a_router",
        "one_verified_next_gate_scales_better_than_more_agents_or_more_wrappers",
    ]
    assert packet["governing_priority"]["allowed_lane"] == (
        "Execution Market AAS / City-as-a-Service internal/admin planning"
    )


def test_bounded_count_pattern_compounder_defines_one_safe_compounding_sequence() -> None:
    packet = build_aas_bounded_local_count_pattern_compounder()

    assert [row["step"] for row in packet["compounding_sequence"]] == [
        "priority_firewall",
        "answer_menu",
        "fixture_gate",
        "integration_map",
        "pattern_compounder",
    ]
    for row in packet["compounding_sequence"]:
        assert row["input"]
        assert row["output"]


def test_bounded_count_pattern_compounder_keeps_future_steps_answer_gated() -> None:
    packet = build_aas_bounded_local_count_pattern_compounder()
    future = packet["future_after_one_real_answer_only"]

    assert future["first_gate"] == "create_one_separate_digest_backed_bounded_local_count_answer_receipt"
    assert future["second_gate"] == "validate_exactly_one_packet_against_aas_bounded_local_count_fixture_gate"
    assert "runtime_acontext_irc_session_manager_mutation" in future["still_not_authorized"]
    assert "erc8004_reputation_or_worker_skill_dna" in future["still_not_authorized"]
    assert "stopped_project_integration" in future["still_not_authorized"]


def test_bounded_count_pattern_compounder_preserves_false_readiness_and_claim_boundaries() -> None:
    packet = build_aas_bounded_local_count_pattern_compounder()

    for key, expected in COMPOUNDER_FALSE_FLAGS.items():
        assert packet["readiness"][key] is expected
    safe = set(packet["claim_boundaries"]["safe_to_claim"])
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])
    assert set(COMPOUNDER_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "selects_answer_value",
        "creates_answer_receipt",
        "collection_site_access",
        "customer_public_or_worker_surface",
        "runtime_acontext_irc",
        "erc8004_reputation_or_worker_skill_dna",
        "payment_or_production",
        "exact_location_raw_metadata_private_context_or_pii",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_bounded_count_pattern_compounder_preserves_stopped_project_firewall_and_guidance() -> None:
    packet = build_aas_bounded_local_count_pattern_compounder()
    firewall = packet["stopped_project_firewall"]
    guidance = packet["operator_guidance"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert guidance["if_no_real_answer"] == "hold_pause_aas_proof_layering_do_not_add_more_no_answer_wrappers"
    assert guidance["if_real_answer_exists"] == "create_one_separate_digest_backed_bounded_local_count_answer_receipt_first"
    assert guidance["not_customer_copy"] is True
    assert guidance["not_worker_instruction"] is True


def test_bounded_count_pattern_compounder_write_and_load_round_trip(tmp_path: Path) -> None:
    seed_sources(tmp_path)

    path = write_aas_bounded_local_count_pattern_compounder(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_FILENAME
    assert load_aas_bounded_local_count_pattern_compounder(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_bounded_count_pattern_compounder_rejects_source_answer_or_fixture_promotion() -> None:
    source = copy.deepcopy(build_aas_source_of_truth_index())
    source["current_no_answer_posture"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="records answer"):
        build_aas_bounded_local_count_pattern_compounder(source_index=source)

    gate = copy.deepcopy(build_aas_bounded_local_count_fixture_gate())
    gate["current_operator_state"]["collection_authorized"] = True

    with pytest.raises(CityOpsContractError, match="collection_authorized"):
        build_aas_bounded_local_count_pattern_compounder(fixture_gate=gate)


def test_bounded_count_pattern_compounder_loader_fails_closed_on_promoted_fixture(tmp_path: Path) -> None:
    seed_sources(tmp_path)
    path = write_aas_bounded_local_count_pattern_compounder(artifact_dir=tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["readiness"]["compounder_creates_customer_public_or_worker_surface"] = True
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="compounder_creates_customer_public_or_worker_surface"):
        load_aas_bounded_local_count_pattern_compounder(artifact_dir=tmp_path)
