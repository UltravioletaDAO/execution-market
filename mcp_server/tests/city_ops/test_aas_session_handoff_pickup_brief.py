from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_next_truth_selector import SELECTED_NEXT_PROOF, SELECTED_NEXT_TRACK
from mcp_server.city_ops.aas_session_handoff_capsule import (
    AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM,
    build_aas_session_handoff_capsule,
)
from mcp_server.city_ops.aas_session_handoff_pickup_brief import (
    AAS_SESSION_HANDOFF_PICKUP_BRIEF_FILENAME,
    AAS_SESSION_HANDOFF_PICKUP_BRIEF_SAFE_CLAIM,
    AAS_SESSION_HANDOFF_PICKUP_BRIEF_SCHEMA,
    AAS_SESSION_HANDOFF_PICKUP_BRIEF_VERDICT,
    build_aas_session_handoff_pickup_brief,
    load_aas_session_handoff_pickup_brief,
    write_aas_session_handoff_pickup_brief,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_brief() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / AAS_SESSION_HANDOFF_PICKUP_BRIEF_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_aas_session_handoff_pickup_brief_matches_fixture():
    brief = build_aas_session_handoff_pickup_brief()

    assert brief == read_fixture_brief()
    assert brief["schema"] == AAS_SESSION_HANDOFF_PICKUP_BRIEF_SCHEMA
    assert brief["brief_verdict"] == AAS_SESSION_HANDOFF_PICKUP_BRIEF_VERDICT
    assert brief["readiness"]["pickup_brief_landed"] is True
    assert brief["readiness"]["capsule_consumed"] is True
    assert brief["readiness"]["four_id_header_preserved"] is True
    assert brief["readiness"]["source_capsule_authorizes_live_attempt_now"] is False
    assert brief["readiness"]["runtime_parity_proven"] is False
    assert brief["readiness"]["customer_delivery_ready"] is False
    assert brief["readiness"]["dispatch_ready"] is False


def test_aas_session_handoff_pickup_brief_preserves_header_and_selected_proof():
    brief = build_aas_session_handoff_pickup_brief()

    assert brief["four_id_header"] == {
        "proof_anchor_id": "redirect_outdated_packet_001",
        "coordination_session_id": "city_session_redirect_outdated_packet_001",
        "compact_decision_id": "cdo_c51f4b767729",
        "review_packet_id": "review_packet_redirect_outdated_packet_001",
    }
    rendered = "\n".join(brief["first_message_template"]["lines"])
    assert "proof_anchor_id: redirect_outdated_packet_001" in rendered
    assert f"selected_next_track: {SELECTED_NEXT_TRACK}" in rendered
    assert f"selected_next_proof: {SELECTED_NEXT_PROOF}" in rendered
    assert brief["next_pickup_order"][1]["track"] == SELECTED_NEXT_TRACK
    assert brief["next_pickup_order"][1]["proof"] == SELECTED_NEXT_PROOF
    assert brief["next_pickup_order"][-1]["authorized_now"] is False


def test_aas_session_handoff_pickup_brief_maps_4am_patterns_without_promotion():
    brief = build_aas_session_handoff_pickup_brief()
    patterns = {item["pattern"]: item for item in brief["pattern_recognition"]}

    assert "memory_system_data_compounds_only_after_review" in patterns
    assert "irc_coordination_scales_with_four_ids" in patterns
    assert "cross_project_intelligence_is_a_filter_not_an_autopilot" in patterns
    assert "agent_coordination_quality_is_boundary_survival" in patterns
    assert patterns["memory_system_data_compounds_only_after_review"]["next_safe_use"] == (
        SELECTED_NEXT_PROOF
    )
    assert "explicit_human_priority_change" in patterns[
        "cross_project_intelligence_is_a_filter_not_an_autopilot"
    ]["blocked_until"]


def test_aas_session_handoff_pickup_brief_is_internal_admin_only():
    brief = build_aas_session_handoff_pickup_brief()

    assert brief["derived_from"]["read_only"] is True
    assert brief["derived_from"]["capsule_consumer_only"] is True
    assert brief["derived_from"]["mutates_irc_runtime_session_manager"] is False
    assert brief["derived_from"]["reads_raw_transcripts"] is False
    assert brief["derived_from"]["writes_live_acontext"] is False
    assert brief["derived_from"]["emits_reputation_receipts"] is False
    assert brief["access_policy"]["customer_visible"] is False
    assert brief["access_policy"]["public_route_registered"] is False
    assert brief["access_policy"]["dispatch_enabled"] is False
    assert brief["access_policy"]["worker_copyable_doctrine_allowed"] is False


def test_aas_session_handoff_pickup_brief_carries_claim_boundaries():
    brief = build_aas_session_handoff_pickup_brief()
    safe = set(brief["claim_boundaries"]["safe_to_claim"])
    blocked = set(brief["claim_boundaries"]["do_not_claim_yet"])

    assert AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM in safe
    assert AAS_SESSION_HANDOFF_PICKUP_BRIEF_SAFE_CLAIM in safe
    assert safe.isdisjoint(blocked)
    assert "pickup_brief_authorizes_live_parity_attempt" in blocked
    assert "pickup_brief_authorizes_customer_copy_delivery_or_publication" in blocked
    assert "pickup_brief_authorizes_erc8004_reputation_or_worker_skill_dna" in blocked
    assert "pickup_brief_allows_exact_gps_or_raw_metadata" in blocked
    assert "pickup_brief_creates_worker_copyable_doctrine" in blocked


def test_aas_session_handoff_pickup_brief_refuses_promoted_capsule_readiness():
    capsule = copy.deepcopy(build_aas_session_handoff_capsule())
    capsule["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="runtime_parity_proven"):
        build_aas_session_handoff_pickup_brief(capsule=capsule)


def test_aas_session_handoff_pickup_brief_refuses_live_attempt_authorization():
    capsule = copy.deepcopy(build_aas_session_handoff_capsule())
    capsule["session_handoff_capsule"]["one_next_proof_slot"][
        "authorizes_live_attempt_now"
    ] = True

    with pytest.raises(CityOpsContractError, match="authorizes live attempt"):
        build_aas_session_handoff_pickup_brief(capsule=capsule)


def test_aas_session_handoff_pickup_brief_refuses_claim_overlap():
    capsule = copy.deepcopy(build_aas_session_handoff_capsule())
    capsule["claim_boundaries"]["do_not_claim_yet"].append(
        capsule["claim_boundaries"]["safe_to_claim"][0]
    )

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_session_handoff_pickup_brief(capsule=capsule)


def test_aas_session_handoff_pickup_brief_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_session_handoff_pickup_brief(artifact_dir=tmp_path)

    assert path.name == AAS_SESSION_HANDOFF_PICKUP_BRIEF_FILENAME
    loaded = load_aas_session_handoff_pickup_brief(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_SESSION_HANDOFF_PICKUP_BRIEF_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_SESSION_HANDOFF_PICKUP_BRIEF_SAFE_CLAIM
    )


def test_aas_session_handoff_pickup_brief_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_session_handoff_pickup_brief(artifact_dir=tmp_path)
    brief = json.loads(path.read_text(encoding="utf-8"))
    brief["readiness"]["dispatch_ready"] = True
    path.write_text(json.dumps(brief), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="dispatch_ready"):
        load_aas_session_handoff_pickup_brief(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
