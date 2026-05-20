import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
    build_aas_coordination_observability_success_metrics_board,
)
from mcp_server.city_ops.aas_coordination_observability_success_metrics_read_surface import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SAFE_CLAIM,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA,
    READ_SURFACE_BLOCKED_CLAIMS,
    build_aas_coordination_observability_success_metrics_read_surface,
    load_aas_coordination_observability_success_metrics_read_surface,
    write_aas_coordination_observability_success_metrics_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_surface() -> dict:
    with (
        PROOF_BLOCK_DIR / AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_coordination_metrics_read_surface_matches_fixture_and_loader():
    surface = build_aas_coordination_observability_success_metrics_read_surface()

    assert surface == read_fixture_surface()
    assert load_aas_coordination_observability_success_metrics_read_surface() == surface
    assert surface["schema"] == AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA
    assert surface["surface_verdict"] == "coordination_metrics_read_surface_landed_internal_admin_only"
    assert AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM in surface[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SAFE_CLAIM in surface[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert surface["readiness"]["coordination_metrics_read_surface_landed"] is True
    assert surface["readiness"]["agent_observability_live_dashboard_ready"] is False


def test_coordination_metrics_read_surface_preserves_four_id_handoff():
    surface = build_aas_coordination_observability_success_metrics_read_surface()
    header = surface["four_id_session_header"]

    for key in [
        "proof_anchor_id",
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
        "source_board_id",
    ]:
        assert header[key]
    assert header["normal_handoff_rule"] == (
        "handoff by IDs and reviewed board fields; do not reopen raw transcripts"
    )


def test_coordination_metrics_read_surface_track_cards_are_pass_through_and_read_only():
    surface = build_aas_coordination_observability_success_metrics_read_surface()
    cards = {card["track"]: card for card in surface["integration_track_cards"]}

    assert set(cards) == {
        "memory_system_to_acontext_integration",
        "irc_session_management_enhancement",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
        "payment_infrastructure_context",
    }
    for card in cards.values():
        assert card["render_policy"] == "operator_read_only_pass_through"
        assert card["customer_visible"] is False
        assert all(value is False for value in card["authorization_flags"].values())


def test_coordination_metrics_read_surface_success_rubric_stays_internal():
    surface = build_aas_coordination_observability_success_metrics_read_surface()

    metrics = {card["metric"]: card for card in surface["success_metric_cards"]}
    rubric = {card["rubric"]: card for card in surface["agent_success_rubric_cards"]}

    assert metrics["claim_boundary_integrity"]["observed"] is True
    assert metrics["four_id_handoff_completeness"]["observed"] is True
    assert metrics["acontext_prerequisite_honesty"]["observed"] is True
    assert metrics["one_next_proof_discipline"]["observed"] is True
    assert set(rubric) == set(metrics)
    assert all(card["customer_visible"] is False for card in metrics.values())
    assert all(card["score_can_be_customer_visible"] is False for card in rubric.values())


def test_coordination_metrics_read_surface_claim_footer_preserves_blocked_claims():
    surface = build_aas_coordination_observability_success_metrics_read_surface()

    safe = set(surface["claim_boundaries"]["safe_to_claim"])
    blocked = set(surface["claim_boundaries"]["do_not_claim_yet"])
    footer = surface["claim_boundary_footer"]

    assert safe.isdisjoint(blocked)
    assert set(READ_SURFACE_BLOCKED_CLAIMS) <= blocked
    assert footer["blocked_claims_may_be_hidden"] is False
    assert footer["safe_to_claim"] == surface["claim_boundaries"]["safe_to_claim"]
    assert footer["do_not_claim_yet"] == surface["claim_boundaries"]["do_not_claim_yet"]
    assert "coordination_metrics_read_surface_is_live_dashboard" in blocked
    assert "coordination_metrics_read_surface_public_or_customer_visible" in blocked


def test_coordination_metrics_read_surface_access_and_render_policy_register_no_route():
    surface = build_aas_coordination_observability_success_metrics_read_surface()

    assert surface["access_policy"]["audience"] == "internal_admin_only"
    assert surface["access_policy"]["network_route_registered"] is False
    assert surface["access_policy"]["public_route_registered"] is False
    assert surface["access_policy"]["customer_visible"] is False
    assert surface["render_contract"]["network_route_registered"] is False
    assert surface["render_contract"]["allowed_interpretation"] == (
        "pass_through_metrics_board_fields_only"
    )


def test_coordination_metrics_read_surface_refuses_source_runtime_promotion():
    board = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    board["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        build_aas_coordination_observability_success_metrics_read_surface(
            metrics_board=board
        )


def test_coordination_metrics_read_surface_refuses_source_public_route_promotion():
    board = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    board["access_policy"]["public_route_registered"] = True

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        build_aas_coordination_observability_success_metrics_read_surface(
            metrics_board=board
        )


def test_coordination_metrics_read_surface_refuses_blocked_safe_claim():
    board = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    board["claim_boundaries"]["safe_to_claim"].append(
        "coordination_metrics_read_surface_writes_live_acontext"
    )

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_coordination_observability_success_metrics_read_surface(
            metrics_board=board
        )


def test_coordination_metrics_read_surface_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_coordination_observability_success_metrics_read_surface(
        artifact_dir=tmp_path
    )

    assert path.name == AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME
    loaded = load_aas_coordination_observability_success_metrics_read_surface(
        artifact_dir=tmp_path
    )
    assert loaded["schema"] == AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SAFE_CLAIM
    )


def test_coordination_metrics_read_surface_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_coordination_observability_success_metrics_read_surface(
        artifact_dir=tmp_path
    )
    surface = json.loads(path.read_text(encoding="utf-8"))
    surface["access_policy"]["customer_visible"] = True
    path.write_text(json.dumps(surface), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_coordination_observability_success_metrics_read_surface(
            artifact_dir=tmp_path
        )


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
