"""Tests for the AAS operator cockpit read surface."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_four_am_pattern_synthesis_handoff import (
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME,
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
    build_aas_four_am_pattern_synthesis_handoff,
    write_aas_four_am_pattern_synthesis_handoff,
)
from mcp_server.city_ops.aas_no_answer_observability_rubric_fixture import (
    write_aas_no_answer_observability_rubric_fixture,
)
from mcp_server.city_ops.aas_operator_cockpit_read_surface import (
    AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME,
    AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM,
    AAS_OPERATOR_COCKPIT_READ_SURFACE_SCHEMA,
    AAS_OPERATOR_COCKPIT_READ_SURFACE_STATUS,
    COCKPIT_BLOCKED_CLAIMS,
    COCKPIT_FALSE_FLAGS,
    COCKPIT_PANES,
    build_aas_operator_cockpit_read_surface,
    load_aas_operator_cockpit_read_surface,
    write_aas_operator_cockpit_read_surface,
)
from mcp_server.city_ops.aas_product_exposure_boundary_candidate_review_gate import (
    write_aas_product_exposure_boundary_candidate_review_gate,
)
from mcp_server.city_ops.aas_source_of_truth_index import (
    AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
    write_aas_source_of_truth_index,
)
from mcp_server.city_ops.aas_system_integration_decision_support_map import (
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME,
    write_aas_system_integration_decision_support_map,
)
from mcp_server.city_ops.aas_two_lane_no_cross_promotion_guard import (
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
    write_aas_two_lane_no_cross_promotion_guard,
)
from mcp_server.city_ops.aas_two_lane_operator_answer_schema import (
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
    ALLOWED_FUTURE_DECISIONS,
    DEFAULT_EFFECTIVE_DECISION,
    write_aas_two_lane_operator_answer_schema,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_cockpit() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path, proof_tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        if source.name in {
            AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
            AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
            AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
            AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME,
            AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME,
            AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME,
        }:
            continue
        shutil.copy(source, tmp_path / source.name)
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, proof_tmp_path / source.name)

    write_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=tmp_path)
    write_aas_no_answer_observability_rubric_fixture(artifact_dir=proof_tmp_path)
    write_aas_two_lane_no_cross_promotion_guard(
        artifact_dir=tmp_path,
        no_answer_artifact_dir=proof_tmp_path,
    )
    write_aas_two_lane_operator_answer_schema(artifact_dir=tmp_path)
    write_aas_source_of_truth_index(artifact_dir=tmp_path)
    write_aas_system_integration_decision_support_map(artifact_dir=tmp_path)
    write_aas_four_am_pattern_synthesis_handoff(artifact_dir=tmp_path)


def test_operator_cockpit_matches_persisted_artifact_and_loader() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()

    assert cockpit == read_cockpit()
    assert load_aas_operator_cockpit_read_surface() == cockpit
    assert cockpit["schema"] == AAS_OPERATOR_COCKPIT_READ_SURFACE_SCHEMA
    assert cockpit["cockpit_status"] == AAS_OPERATOR_COCKPIT_READ_SURFACE_STATUS
    assert AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM in cockpit["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM in cockpit["claim_boundaries"][
        "safe_to_claim"
    ]


def test_operator_cockpit_consumes_only_four_am_handoff() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()
    source = cockpit["source_handoff"]

    assert source["file"] == AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME
    assert source["safe_claim"] == AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM
    assert source["effective_decision"] == DEFAULT_EFFECTIVE_DECISION
    assert len(source["digest_sha256"]) == 64


def test_operator_cockpit_renders_five_read_only_panes_without_promoting_them() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()
    panes = cockpit["cockpit_panes"]

    assert [pane["pane"] for pane in panes] == [pane["pane"] for pane in COCKPIT_PANES]
    assert {pane["pane"] for pane in panes} == {
        "source_truth",
        "allowed_answer_values",
        "runtime_blocker",
        "product_exposure_blocker",
        "recommended_no_answer_posture",
    }
    for pane in panes:
        assert pane["internal_admin_read_only"] is True
        assert pane["selected_by_this_cockpit"] is False
        assert pane["approval_granted_by_this_cockpit"] is False
        assert pane["runtime_or_external_promotion_allowed"] is False


def test_operator_cockpit_answer_panel_displays_allowed_values_without_selection() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()
    answer_panel = cockpit["answer_panel"]

    assert [item["decision"] for item in answer_panel["allowed_future_decisions"]] == (
        ALLOWED_FUTURE_DECISIONS
    )
    assert answer_panel["recommended_no_answer_values"] == [
        "pause_aas_proof_layering",
        "keep_both_lanes_held",
    ]
    assert answer_panel["default_if_no_human_answer"] == DEFAULT_EFFECTIVE_DECISION
    assert answer_panel["display_text_is_not_answer"] is True
    for item in answer_panel["allowed_future_decisions"]:
        assert item["displayed_by_this_cockpit"] is True
        assert item["selected_by_this_cockpit"] is False
        assert item["requires_separate_answer_record"] is True
        assert item["approval_granted_by_this_cockpit"] is False


def test_operator_cockpit_records_no_answer_approval_or_future_selection() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()

    assert cockpit["current_no_answer_decision"] == {
        "operator_answer_recorded": False,
        "operator_approval_recorded": False,
        "selected_future_answer": None,
        "effective_decision": DEFAULT_EFFECTIVE_DECISION,
        "cockpit_display_is_approval": False,
        "cockpit_is_answer_record": False,
    }
    assert cockpit["readiness"]["internal_admin_operator_cockpit_read_surface_landed"] is True
    for flag, expected in COCKPIT_FALSE_FLAGS.items():
        assert cockpit["readiness"][flag] is expected


def test_operator_cockpit_runtime_snapshot_remains_blocked_and_non_repairing() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()
    blocker = cockpit["runtime_blocker_snapshot"]

    assert blocker["docker_context_observed"] == "desktop-linux"
    assert blocker["docker_daemon_reachable"] is False
    assert blocker["local_acontext_3000_reachable"] is False
    assert blocker["local_acontext_8080_reachable"] is False
    assert blocker["local_acontext_5173_reachable"] is False
    assert blocker["snapshot_is_runtime_repair"] is False
    assert blocker["snapshot_claims_runtime_parity"] is False


def test_operator_cockpit_preserves_blocked_claim_boundaries() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()
    safe = set(cockpit["claim_boundaries"]["safe_to_claim"])
    blocked = set(cockpit["claim_boundaries"]["do_not_claim_yet"])

    assert set(COCKPIT_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "selects_future_answer",
        "display_as_approval",
        "approves_product_exposure",
        "runtime_memory_wiring",
        "runtime_adapter",
        "irc_session_manager",
        "live_acontext",
        "cross_project_autorouting",
        "customer_public_worker_surface",
        "public_dashboard_or_metric",
        "catalog_pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "payment_or_production",
        "exact_gps_or_raw_metadata",
        "private_context",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_operator_cockpit_preserves_stopped_project_firewall() -> None:
    cockpit = build_aas_operator_cockpit_read_surface()
    firewall = cockpit["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_operator_cockpit_write_and_load_round_trip(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)

    path = write_aas_operator_cockpit_read_surface(artifact_dir=product_tmp_path)

    assert path == product_tmp_path / AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME
    assert load_aas_operator_cockpit_read_surface(
        artifact_dir=product_tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_operator_cockpit_rejects_source_handoff_that_records_answer() -> None:
    source = copy.deepcopy(build_aas_four_am_pattern_synthesis_handoff())
    source["current_no_answer_decision"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="recorded operator answer"):
        build_aas_operator_cockpit_read_surface(source_handoff=source)


def test_operator_cockpit_loader_rejects_tampered_promotion(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)
    path = write_aas_operator_cockpit_read_surface(artifact_dir=product_tmp_path)
    cockpit = json.loads(path.read_text(encoding="utf-8"))
    cockpit["readiness"]["cockpit_creates_public_dashboard"] = True
    path.write_text(json.dumps(cockpit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_aas_operator_cockpit_read_surface(artifact_dir=product_tmp_path)
