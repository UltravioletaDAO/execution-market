import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_exponential_value_pathfinder import (
    AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
    build_aas_exponential_value_pathfinder,
)
from mcp_server.city_ops.aas_next_truth_selector import (
    AAS_NEXT_TRUTH_SELECTOR_FILENAME,
    AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
    AAS_NEXT_TRUTH_SELECTOR_SCHEMA,
    SELECTED_NEXT_PROOF,
    SELECTED_NEXT_TRACK,
    SELECTOR_BLOCKED_CLAIMS,
    build_aas_next_truth_selector,
    load_aas_next_truth_selector,
    write_aas_next_truth_selector,
)
from mcp_server.city_ops.aas_system_integration_flywheel_route_regret_panel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
    build_aas_system_integration_flywheel_route_regret_panel,
)
from mcp_server.city_ops.acontext_prerequisite_activation_board import (
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
    build_acontext_prerequisite_activation_board,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_selector() -> dict:
    with (PROOF_BLOCK_DIR / AAS_NEXT_TRUTH_SELECTOR_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_aas_next_truth_selector_matches_fixture_and_loader():
    selector = build_aas_next_truth_selector()

    assert selector == read_fixture_selector()
    assert load_aas_next_truth_selector() == selector
    assert selector["schema"] == AAS_NEXT_TRUTH_SELECTOR_SCHEMA
    assert selector["selector_verdict"] == (
        "select_runtime_prerequisite_truth_not_more_route_layers"
    )
    assert selector["selected_next_track"] == SELECTED_NEXT_TRACK
    assert selector["selected_next_proof"] == SELECTED_NEXT_PROOF
    assert AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM in selector["claim_boundaries"][
        "safe_to_claim"
    ]


def test_aas_next_truth_selector_turns_patterns_into_one_runtime_truth_action():
    selector = build_aas_next_truth_selector()

    readiness = selector["readiness"]
    assert readiness["selector_landed"] is True
    assert readiness["selected_track_is_runtime_truth_prerequisite_work"] is True
    assert readiness["selected_track_is_more_route_layering"] is False
    assert readiness["ready_to_attempt_live_transport"] is False
    assert readiness["runtime_parity_proven"] is False

    rankings = {row["track"]: row for row in selector["truth_track_ranking"]}
    assert rankings[SELECTED_NEXT_TRACK]["rank"] == 1
    assert rankings[SELECTED_NEXT_TRACK]["selected"] is True
    assert rankings["more_internal_route_layering"]["rank"] == 4
    assert rankings["more_internal_route_layering"]["selected"] is False
    assert rankings["more_internal_route_layering"]["authorizes_new_route"] is False


def test_aas_next_truth_selector_preserves_blocked_auto_promotions():
    selector = build_aas_next_truth_selector()

    blocked = set(selector["claim_boundaries"]["do_not_claim_yet"])
    safe = set(selector["claim_boundaries"]["safe_to_claim"])
    assert set(SELECTOR_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "next_truth_selector_authorizes_more_route_layers" in blocked
    assert "next_truth_selector_authorizes_live_acontext_write_or_retrieve" in blocked
    assert "next_truth_selector_authorizes_erc8004_reputation_or_worker_skill_dna" in blocked

    promotions = {row["temptation"]: row for row in selector["blocked_auto_promotions"]}
    assert promotions["breakthrough_pattern_means_live_runtime_ready"]["blocked_by"] == (
        "next_truth_selector_authorizes_live_acontext_write_or_retrieve"
    )
    assert promotions["portfolio_pattern_map_means_customer_packaging_ready"][
        "blocked_by"
    ] == "next_truth_selector_authorizes_customer_copy_or_delivery"


def test_aas_next_truth_selector_operator_packet_allows_setup_not_live_write():
    selector = build_aas_next_truth_selector()

    packet = selector["operator_next_work_packet"]
    assert packet["packet_type"] == "internal_admin_runtime_truth_prerequisite_packet"
    assert packet["live_write_or_retrieve_allowed_now"] is False
    assert packet["customer_or_worker_surface_allowed_now"] is False
    assert packet["must_rebuild_before_live_attempt"] == [
        "acontext_live_preflight_blocker_delta",
        "acontext_live_preflight_blocker_delta_read_surface",
        "acontext_live_parity_attempt_readiness_gate",
    ]
    assert "complete_local_acontext_service_startup" in packet["allowed_now"]
    assert "wire_active_runner_to_acontext_sdk" in packet["allowed_now"]


def test_aas_next_truth_selector_refuses_promoted_pathfinder_recommendation():
    pathfinder = copy.deepcopy(build_aas_exponential_value_pathfinder())
    pathfinder["recommended_next_proof"]["may_auto_promote"] = True

    with pytest.raises(CityOpsContractError, match="promoted pathfinder proof"):
        build_aas_next_truth_selector(pathfinder=pathfinder)


def test_aas_next_truth_selector_refuses_live_ready_activation_board():
    activation = copy.deepcopy(build_acontext_prerequisite_activation_board())
    activation["readiness"]["ready_to_attempt_live_transport"] = True

    with pytest.raises(CityOpsContractError, match="promoted activation board"):
        build_aas_next_truth_selector(activation_board=activation)


def test_aas_next_truth_selector_refuses_route_regret_promotion():
    regret = copy.deepcopy(build_aas_system_integration_flywheel_route_regret_panel())
    regret["readiness"]["new_route_requested"] = True

    with pytest.raises(CityOpsContractError, match="promoted regret panel"):
        build_aas_next_truth_selector(regret_panel=regret)


def test_aas_next_truth_selector_write_and_load_temp_fixture(tmp_path):
    _copy_selector_sources(tmp_path)
    path = write_aas_next_truth_selector(artifact_dir=tmp_path)

    assert path.name == AAS_NEXT_TRUTH_SELECTOR_FILENAME
    loaded = load_aas_next_truth_selector(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_NEXT_TRUTH_SELECTOR_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM
    )


def test_aas_next_truth_selector_loader_rejects_live_write_promotion(tmp_path):
    _copy_selector_sources(tmp_path)
    path = write_aas_next_truth_selector(artifact_dir=tmp_path)
    selector = json.loads(path.read_text(encoding="utf-8"))
    selector["operator_next_work_packet"]["live_write_or_retrieve_allowed_now"] = True
    path.write_text(json.dumps(selector), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="allowed live Acontext"):
        load_aas_next_truth_selector(artifact_dir=tmp_path)


def _copy_selector_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
