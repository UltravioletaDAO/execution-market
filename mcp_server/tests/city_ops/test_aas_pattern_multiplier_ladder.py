"""Tests for the internal/admin AAS pattern multiplier ladder."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_bounded_local_count_fixture_gate import (
    write_aas_bounded_local_count_fixture_gate,
)
from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_event_readiness_observation_outline import (
    write_aas_event_readiness_observation_outline,
)
from mcp_server.city_ops.aas_field_asset_visible_state_fixture_outline import (
    write_aas_field_asset_visible_state_fixture_outline,
)
from mcp_server.city_ops.aas_package_family_hold_selector import (
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME,
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM,
    RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE,
    build_aas_package_family_hold_selector,
    write_aas_package_family_hold_selector,
)
from mcp_server.city_ops.aas_pattern_multiplier_ladder import (
    AAS_PATTERN_MULTIPLIER_LADDER_FILENAME,
    AAS_PATTERN_MULTIPLIER_LADDER_SAFE_CLAIM,
    AAS_PATTERN_MULTIPLIER_LADDER_SCHEMA,
    AAS_PATTERN_MULTIPLIER_LADDER_STATUS,
    FALSE_FLAGS,
    MULTIPLIER_LADDER_BLOCKED_CLAIMS,
    PATTERN_ROWS,
    build_aas_pattern_multiplier_ladder,
    load_aas_pattern_multiplier_ladder,
    write_aas_pattern_multiplier_ladder,
)
from mcp_server.city_ops.aas_pre_event_blocker_internal_checklist import (
    write_aas_pre_event_blocker_internal_checklist,
)
from mcp_server.city_ops.aas_visible_asset_state_internal_state_menu import (
    write_aas_visible_asset_state_internal_state_menu,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_ladder() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_PATTERN_MULTIPLIER_LADDER_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def write_prerequisites(artifact_dir: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=artifact_dir)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=artifact_dir)
    write_aas_bounded_local_count_fixture_gate(artifact_dir=artifact_dir)
    write_aas_field_asset_visible_state_fixture_outline(artifact_dir=artifact_dir)
    write_aas_visible_asset_state_internal_state_menu(artifact_dir=artifact_dir)
    write_aas_event_readiness_observation_outline(artifact_dir=artifact_dir)
    write_aas_pre_event_blocker_internal_checklist(artifact_dir=artifact_dir)
    write_aas_package_family_hold_selector(artifact_dir=artifact_dir)


def test_pattern_multiplier_ladder_matches_persisted_artifact_and_loader() -> None:
    ladder = build_aas_pattern_multiplier_ladder()

    assert ladder == read_fixture_ladder()
    assert load_aas_pattern_multiplier_ladder() == ladder
    assert ladder["schema"] == AAS_PATTERN_MULTIPLIER_LADDER_SCHEMA
    assert ladder["ladder_status"] == AAS_PATTERN_MULTIPLIER_LADDER_STATUS
    safe = ladder["claim_boundaries"]["safe_to_claim"]
    assert AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM in safe
    assert AAS_PATTERN_MULTIPLIER_LADDER_SAFE_CLAIM in safe


def test_pattern_multiplier_ladder_consumes_hold_selector_by_digest() -> None:
    ladder = build_aas_pattern_multiplier_ladder()
    source = ladder["source_selector"]

    assert source["file"] == AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME
    assert source["safe_claim"] == AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM
    assert source["recommended_value_if_human_moves"] == (
        RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE
    )
    assert len(source["digest_sha256"]) == 64


def test_pattern_multiplier_ladder_rows_answer_late_night_pattern_questions_read_only() -> None:
    ladder = build_aas_pattern_multiplier_ladder()
    rows = ladder["pattern_multiplier_rows"]

    assert rows == PATTERN_ROWS
    assert [row["pattern_code"] for row in rows] == [
        "memory_digest_preservation",
        "irc_handoff_without_route_mutation",
        "stale_cron_firewall",
        "single_answer_receipt_gate",
        "concept_menu_as_option_space",
        "observability_of_restraint",
    ]
    for row in rows:
        assert row["observed_pattern"]
        assert row["multiplier_effect_if_proven_later"]
        assert row["safe_now"]
        assert row["blocked_until_gate"].startswith("no ")
        assert row["scales_best_when"]


def test_pattern_multiplier_ladder_preserves_single_gate_synthesis_and_operator_hold() -> None:
    ladder = build_aas_pattern_multiplier_ladder()

    assert ladder["late_night_synthesis"] == {
        "best_scaling_pattern": "digest_backed_read_only_handoffs_with_one_explicit_next_gate",
        "highest_value_connection": "memory_digest_preservation_plus_stale_cron_firewall_plus_answer_receipt_gate",
        "why_it_compounds": "agents preserve context and boundaries across sessions without turning planning depth into authorization",
        "next_safe_action_if_no_operator_answer": "hold_pause_aas_proof_layering_and_do_not_add_more_package_menus",
        "next_safe_action_if_operator_answer_arrives": "create_one_separate_digest_backed_bounded_local_count_answer_receipt",
    }
    assert ladder["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_value": None,
        "selected_posture_now": "pause_aas_proof_layering",
    }


def test_pattern_multiplier_ladder_preserves_false_readiness_and_firewall() -> None:
    ladder = build_aas_pattern_multiplier_ladder()

    for key, expected in FALSE_FLAGS.items():
        assert ladder["readiness"][key] is expected
    assert ladder["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_pattern_multiplier_ladder_preserves_claim_boundaries() -> None:
    ladder = build_aas_pattern_multiplier_ladder()
    safe = set(ladder["claim_boundaries"]["safe_to_claim"])
    blocked = set(ladder["claim_boundaries"]["do_not_claim_yet"])

    assert set(MULTIPLIER_LADDER_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "creates_answer_receipt",
        "mutates_memory_acontext_irc_runtime_or_session_manager",
        "emits_erc8004_reputation_or_worker_skill_dna",
        "reverifies_payment_production_or_chain_state",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_pattern_multiplier_ladder_write_roundtrip(tmp_path: Path) -> None:
    write_prerequisites(tmp_path)
    path = write_aas_pattern_multiplier_ladder(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PATTERN_MULTIPLIER_LADDER_FILENAME
    loaded = load_aas_pattern_multiplier_ladder(artifact_dir=tmp_path)
    assert loaded["ladder_id"] == (
        "execution_market.aas.pattern_multiplier_ladder.2026_06_14_0400"
    )


def test_pattern_multiplier_ladder_rejects_source_selector_promotion() -> None:
    selector = copy.deepcopy(build_aas_package_family_hold_selector())
    selector["current_operator_state"]["selected_value"] = RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE

    with pytest.raises(CityOpsContractError, match="source selected a value"):
        build_aas_pattern_multiplier_ladder(hold_selector=selector)

    selector = copy.deepcopy(build_aas_package_family_hold_selector())
    selector["governing_priority"]["stopped_project_firewall"]["autojob_work_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source allowed autojob_work_allowed"):
        build_aas_pattern_multiplier_ladder(hold_selector=selector)


def test_pattern_multiplier_ladder_rejects_runtime_payment_or_stopped_project_promotion() -> None:
    ladder = build_aas_pattern_multiplier_ladder()
    ladder["readiness"]["ladder_mutates_memory_acontext_irc_runtime_or_session_manager"] = True

    with pytest.raises(CityOpsContractError, match="memory_acontext_irc_runtime_or_session_manager"):
        load_aas_pattern_multiplier_ladder(artifact_dir=_write_fixture_set(ladder))

    ladder = build_aas_pattern_multiplier_ladder()
    ladder["readiness"]["ladder_reverifies_payment_production_or_chain_state"] = True

    with pytest.raises(CityOpsContractError, match="payment_production_or_chain_state"):
        load_aas_pattern_multiplier_ladder(artifact_dir=_write_fixture_set(ladder))

    ladder = build_aas_pattern_multiplier_ladder()
    ladder["governing_priority"]["stopped_project_firewall"]["kk_v2_work_allowed"] = True

    with pytest.raises(CityOpsContractError, match="kk_v2_work_allowed"):
        load_aas_pattern_multiplier_ladder(artifact_dir=_write_fixture_set(ladder))


def test_pattern_multiplier_ladder_rejects_pattern_row_or_digest_drift() -> None:
    ladder = build_aas_pattern_multiplier_ladder()
    ladder["pattern_multiplier_rows"] = ladder["pattern_multiplier_rows"][:-1]

    with pytest.raises(CityOpsContractError, match="row drift"):
        load_aas_pattern_multiplier_ladder(artifact_dir=_write_fixture_set(ladder))

    ladder = build_aas_pattern_multiplier_ladder()
    ladder["source_selector"]["digest_sha256"] = "0" * 64

    with pytest.raises(CityOpsContractError, match="source digest drift"):
        load_aas_pattern_multiplier_ladder(artifact_dir=_write_fixture_set(ladder))


def _write_fixture_set(ladder: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_prerequisites(tmp)
    (tmp / AAS_PATTERN_MULTIPLIER_LADDER_FILENAME).write_text(
        json.dumps(ladder, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
