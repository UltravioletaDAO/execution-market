import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_exponential_value_pathfinder import (
    AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM,
    build_aas_exponential_value_pathfinder,
)
from mcp_server.city_ops.aas_pre_dawn_synthesis_handoff import (
    AAS_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME,
    AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
    AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA,
    PRE_DAWN_SYNTHESIS_BLOCKED_CLAIMS,
    build_aas_pre_dawn_synthesis_handoff,
    load_aas_pre_dawn_synthesis_handoff,
    write_aas_pre_dawn_synthesis_handoff,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_handoff() -> dict:
    with (PROOF_BLOCK_DIR / AAS_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_pre_dawn_synthesis_handoff_matches_fixture_and_loader():
    handoff = build_aas_pre_dawn_synthesis_handoff()

    assert handoff == read_fixture_handoff()
    assert load_aas_pre_dawn_synthesis_handoff() == handoff
    assert handoff["schema"] == AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA
    assert handoff["handoff_verdict"] == (
        "pre_dawn_synthesis_ready_for_daytime_internal_admin_coordination_only"
    )
    assert handoff["readiness"]["handoff_landed"] is True
    assert handoff["readiness"]["source_pathfinder_consumed"] is True
    assert handoff["readiness"]["live_acontext_memory_integration_ready"] is False
    assert handoff["readiness"]["autojob_integration_ready"] is False
    assert AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM in handoff["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM in handoff["claim_boundaries"][
        "safe_to_claim"
    ]


def test_handoff_preserves_dream_priority_stop_list():
    handoff = build_aas_pre_dawn_synthesis_handoff()

    scope = handoff["scope_guard"]
    assert scope["governing_file"] == "~/clawd/DREAM-PRIORITIES.md"
    assert scope["active_focus"] == "Execution Market AAS / City-as-a-Service only"
    assert scope["stale_cron_tracks_skipped"] == [
        "AutoJob",
        "Frontier Academy",
        "KK v2",
        "KarmaCadabra v2",
    ]
    assert scope["autojob_pull_skipped_because_stop_list_wins"] is True
    assert handoff["derived_from"]["pulls_autojob_repo"] is False
    assert handoff["derived_from"]["analyzes_autojob_codebase"] is False
    assert handoff["derived_from"]["expands_frontier_academy_guides"] is False
    assert handoff["derived_from"]["works_on_kk_v2"] is False


def test_handoff_daytime_priority_queue_is_internal_and_ordered():
    handoff = build_aas_pre_dawn_synthesis_handoff()

    queue = handoff["daytime_priority_queue"]
    assert [row["rank"] for row in queue] == [1, 2, 3]
    assert queue[0]["priority"] == (
        "acontext_runtime_memory_prerequisites_then_single_live_parity_attempt"
    )
    assert queue[0]["requires_separate_human_approval"] is False
    assert queue[1]["requires_separate_human_approval"] is True
    assert "AutoJob" in queue[2]["action"]
    assert all(row["customer_visible"] is False for row in queue)
    assert all(row["may_auto_promote"] is False for row in queue)


def test_handoff_cards_preserve_four_ids_and_claim_boundary():
    handoff = build_aas_pre_dawn_synthesis_handoff()

    cards = {card["card"]: card for card in handoff["handoff_cards"]}
    assert set(cards) == {"start_here", "do_not_start_here", "claim_boundary"}
    for key in [
        "proof_anchor_id",
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
    ]:
        assert cards["start_here"][key] == handoff[key]
    assert cards["do_not_start_here"]["blocked_tracks"] == [
        "AutoJob",
        "Frontier Academy",
        "KK v2",
        "KarmaCadabra v2",
    ]
    assert cards["claim_boundary"]["safe_claim"] == (
        AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM
    )


def test_handoff_preserves_blocked_claims_and_false_access():
    handoff = build_aas_pre_dawn_synthesis_handoff()

    safe = set(handoff["claim_boundaries"]["safe_to_claim"])
    blocked = set(handoff["claim_boundaries"]["do_not_claim_yet"])
    assert set(PRE_DAWN_SYNTHESIS_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    assert "synthesis_pulled_or_analyzed_autojob" in blocked
    assert "synthesis_authorizes_live_acontext_write_or_retrieval" in blocked
    assert "synthesis_authorizes_queue_launch_or_dispatch" in blocked
    assert handoff["access_policy"]["customer_visible"] is False
    assert handoff["access_policy"]["dispatch_enabled"] is False


def test_handoff_refuses_pathfinder_visibility_promotion():
    source = copy.deepcopy(build_aas_exponential_value_pathfinder())
    source["recommended_next_proof"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="source recommended proof promoted visibility"):
        build_aas_pre_dawn_synthesis_handoff(pathfinder=source)


def test_handoff_refuses_pathfinder_authorization_promotion():
    source = copy.deepcopy(build_aas_exponential_value_pathfinder())
    source["exponential_value_loops"][0]["authorizes_live_runtime"] = True

    with pytest.raises(CityOpsContractError, match="source pathfinder promoted authorization"):
        build_aas_pre_dawn_synthesis_handoff(pathfinder=source)


def test_handoff_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_pre_dawn_synthesis_handoff(artifact_dir=tmp_path)

    assert path.name == AAS_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME
    loaded = load_aas_pre_dawn_synthesis_handoff(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM
    )


def test_handoff_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_pre_dawn_synthesis_handoff(artifact_dir=tmp_path)
    handoff = json.loads(path.read_text(encoding="utf-8"))
    handoff["readiness"]["dispatch_ready"] = True
    path.write_text(json.dumps(handoff), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted forbidden flag"):
        load_aas_pre_dawn_synthesis_handoff(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
