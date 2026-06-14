"""Tests for the internal/admin AAS package-family hold selector."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_bounded_local_count_fixture_gate import (
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
    build_aas_bounded_local_count_fixture_gate,
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
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SCHEMA,
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_STATUS,
    FALSE_FLAGS,
    PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS,
    PACKAGE_FAMILY_ROWS,
    RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE,
    SYSTEM_INTEGRATION_HOLD_CONNECTIONS,
    build_aas_package_family_hold_selector,
    load_aas_package_family_hold_selector,
    write_aas_package_family_hold_selector,
)
from mcp_server.city_ops.aas_pre_event_blocker_internal_checklist import (
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM,
    write_aas_pre_event_blocker_internal_checklist,
)
from mcp_server.city_ops.aas_visible_asset_state_internal_state_menu import (
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM,
    build_aas_visible_asset_state_internal_state_menu,
    write_aas_visible_asset_state_internal_state_menu,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_selector() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME).read_text(
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


def test_package_family_hold_selector_matches_persisted_artifact_and_loader() -> None:
    selector = build_aas_package_family_hold_selector()

    assert selector == read_fixture_selector()
    assert load_aas_package_family_hold_selector() == selector
    assert selector["schema"] == AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SCHEMA
    assert selector["selector_status"] == AAS_PACKAGE_FAMILY_HOLD_SELECTOR_STATUS
    safe = selector["claim_boundaries"]["safe_to_claim"]
    assert AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM in safe
    assert AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM in safe
    assert AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM in safe
    assert AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM in safe


def test_package_family_hold_selector_consumes_three_latest_family_artifacts() -> None:
    selector = build_aas_package_family_hold_selector()
    sources = selector["source_artifacts"]

    assert sorted(sources) == [
        "bounded_local_count_fixture_gate",
        "pre_event_blocker_internal_checklist",
        "visible_asset_state_internal_state_menu",
    ]
    for source in sources.values():
        assert len(source["digest_sha256"]) == 64
        assert source["safe_claim"].startswith("internal_admin_aas_")
    assert sources["bounded_local_count_fixture_gate"]["file"] == (
        "aas_bounded_local_count_fixture_gate.json"
    )
    assert sources["visible_asset_state_internal_state_menu"]["required_state_codes"]
    assert sources["pre_event_blocker_internal_checklist"]["required_check_codes"]


def test_package_family_hold_selector_names_single_next_gate_without_selecting_it() -> None:
    selector = build_aas_package_family_hold_selector()
    rows = selector["package_family_rows"]

    assert rows == PACKAGE_FAMILY_ROWS
    bounded_row = rows[0]
    assert bounded_row["canonical_family"] == "Bounded Local Count"
    assert bounded_row["recommended_value_if_human_chooses_to_move"] == (
        RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE
    )
    assert bounded_row["allowed_next_gate"] == (
        "separate_operator_value_then_digest_backed_answer_receipt"
    )
    assert rows[1]["recommended_value_if_human_chooses_to_move"] is None
    assert rows[2]["recommended_value_if_human_chooses_to_move"] is None

    operator = selector["current_operator_state"]
    assert operator["explicit_operator_answer_available"] is False
    assert operator["operator_approval_recorded"] is False
    assert operator["answer_receipt_created"] is False
    assert operator["selected_package_family"] is None
    assert operator["selected_value"] is None
    assert operator["selected_posture_now"] == "pause_aas_proof_layering"


def test_package_family_hold_selector_connects_system_integration_read_only() -> None:
    selector = build_aas_package_family_hold_selector()
    connections = selector["system_integration_hold_connections"]

    assert connections == SYSTEM_INTEGRATION_HOLD_CONNECTIONS
    assert [connection["connection"] for connection in connections] == [
        "memory_system_to_acontext",
        "irc_session_management",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
        "payment_and_production_maturity",
    ]
    for connection in connections:
        assert connection["safe_now"]
        assert connection["blocked_until_gate"].startswith("no ")
        assert connection["success_metric"]


def test_package_family_hold_selector_preserves_firewall_and_next_actions() -> None:
    selector = build_aas_package_family_hold_selector()

    firewall = selector["governing_priority"]["stopped_project_firewall"]
    assert firewall == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }
    by_condition = {
        action["condition"]: action for action in selector["allowed_next_actions"]
    }
    assert by_condition["no_real_operator_answer_exists"]["allowed_now"] is True
    assert by_condition["future_cron_mentions_stopped_projects"]["allowed_now"] is True
    assert by_condition["bounded_local_count_operator_value_arrives"]["allowed_now"] is False
    assert by_condition["visible_asset_or_pre_event_family_requested_later"]["allowed_now"] is False


def test_package_family_hold_selector_preserves_false_readiness_and_claim_boundaries() -> None:
    selector = build_aas_package_family_hold_selector()

    for key, expected in FALSE_FLAGS.items():
        assert selector["readiness"][key] is expected
    safe = set(selector["claim_boundaries"]["safe_to_claim"])
    blocked = set(selector["claim_boundaries"]["do_not_claim_yet"])
    assert set(PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "creates_answer_receipt",
        "selects_future_answer",
        "mutates_runtime_acontext_irc_or_session_manager",
        "reverifies_payment_production_or_chain_state",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_package_family_hold_selector_write_roundtrip(tmp_path: Path) -> None:
    write_prerequisites(tmp_path)
    path = write_aas_package_family_hold_selector(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME
    loaded = load_aas_package_family_hold_selector(artifact_dir=tmp_path)
    assert loaded["selector_id"] == (
        "execution_market.aas.package_family_hold_selector.2026_06_14_0300"
    )


def test_package_family_hold_selector_rejects_source_promotion() -> None:
    bounded = build_aas_bounded_local_count_fixture_gate()
    bounded["readiness"]["gate_records_operator_answer"] = True

    with pytest.raises(CityOpsContractError, match="bounded gate promoted"):
        build_aas_package_family_hold_selector(bounded_gate=bounded)

    visible = build_aas_visible_asset_state_internal_state_menu()
    visible["visible_asset_state_internal_state_menu"]["state_menu_rows"] = []

    with pytest.raises(CityOpsContractError, match="visible menu state code drift"):
        build_aas_package_family_hold_selector(visible_menu=visible)


def test_package_family_hold_selector_rejects_answer_runtime_payment_or_stopped_project_promotion() -> None:
    selector = build_aas_package_family_hold_selector()
    selector["current_operator_state"]["selected_value"] = RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE

    with pytest.raises(CityOpsContractError, match="selected a value"):
        load_aas_package_family_hold_selector(artifact_dir=_write_fixture_set(selector))

    selector = build_aas_package_family_hold_selector()
    selector["readiness"]["selector_mutates_runtime_acontext_irc_or_session_manager"] = True

    with pytest.raises(CityOpsContractError, match="runtime_acontext_irc_or_session_manager"):
        load_aas_package_family_hold_selector(artifact_dir=_write_fixture_set(selector))

    selector = build_aas_package_family_hold_selector()
    selector["readiness"]["selector_reverifies_payment_production_or_chain_state"] = True

    with pytest.raises(CityOpsContractError, match="payment_production_or_chain_state"):
        load_aas_package_family_hold_selector(artifact_dir=_write_fixture_set(selector))

    selector = build_aas_package_family_hold_selector()
    selector["governing_priority"]["stopped_project_firewall"]["autojob_work_allowed"] = True

    with pytest.raises(CityOpsContractError, match="autojob_work_allowed"):
        load_aas_package_family_hold_selector(artifact_dir=_write_fixture_set(selector))


def test_package_family_hold_selector_rejects_next_action_promotion_or_digest_drift() -> None:
    selector = build_aas_package_family_hold_selector()
    selector["allowed_next_actions"][1]["allowed_now"] = True

    with pytest.raises(CityOpsContractError, match="next action promoted"):
        load_aas_package_family_hold_selector(artifact_dir=_write_fixture_set(selector))

    selector = copy.deepcopy(build_aas_package_family_hold_selector())
    selector["selector_digest_sha256"] = "0" * 64

    with pytest.raises(CityOpsContractError, match="digest drift"):
        load_aas_package_family_hold_selector(artifact_dir=_write_fixture_set(selector))


def _write_fixture_set(selector: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_prerequisites(tmp)
    (tmp / AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME).write_text(
        json.dumps(selector, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return tmp
