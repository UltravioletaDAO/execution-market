from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
    build_aas_coordination_observability_success_metrics_board,
)
from mcp_server.city_ops.aas_next_truth_selector import (
    AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
    SELECTED_NEXT_PROOF,
    SELECTED_NEXT_TRACK,
    build_aas_next_truth_selector,
)
from mcp_server.city_ops.aas_session_handoff_capsule import (
    AAS_SESSION_HANDOFF_CAPSULE_FILENAME,
    AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM,
    AAS_SESSION_HANDOFF_CAPSULE_SCHEMA,
    AAS_SESSION_HANDOFF_CAPSULE_VERDICT,
    build_aas_session_handoff_capsule,
    load_aas_session_handoff_capsule,
    write_aas_session_handoff_capsule,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_capsule() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / AAS_SESSION_HANDOFF_CAPSULE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_aas_session_handoff_capsule_matches_fixture():
    capsule = build_aas_session_handoff_capsule()

    assert capsule == read_fixture_capsule()
    assert capsule["schema"] == AAS_SESSION_HANDOFF_CAPSULE_SCHEMA
    assert capsule["capsule_verdict"] == AAS_SESSION_HANDOFF_CAPSULE_VERDICT
    assert capsule["readiness"]["session_handoff_capsule_landed"] is True
    assert capsule["readiness"]["four_id_header_preserved"] is True
    assert capsule["readiness"]["runtime_session_manager_mutated"] is False
    assert capsule["readiness"]["raw_transcript_replay_required"] is False
    assert capsule["readiness"]["live_acontext_memory_integration_ready"] is False
    assert capsule["readiness"]["runtime_parity_proven"] is False
    assert capsule["readiness"]["customer_delivery_ready"] is False
    assert capsule["readiness"]["dispatch_ready"] is False


def test_aas_session_handoff_capsule_preserves_four_id_header_and_next_proof():
    capsule = build_aas_session_handoff_capsule()

    assert capsule["four_id_header"] == {
        "proof_anchor_id": "redirect_outdated_packet_001",
        "coordination_session_id": "city_session_redirect_outdated_packet_001",
        "compact_decision_id": "cdo_c51f4b767729",
        "review_packet_id": "review_packet_redirect_outdated_packet_001",
    }
    assert capsule["session_handoff_capsule"]["selected_next_track"] == (
        SELECTED_NEXT_TRACK
    )
    assert capsule["session_handoff_capsule"]["selected_next_proof"] == (
        SELECTED_NEXT_PROOF
    )
    assert capsule["session_handoff_capsule"]["one_next_proof_slot"] == {
        "track": SELECTED_NEXT_TRACK,
        "proof": SELECTED_NEXT_PROOF,
        "authorizes_live_attempt_now": False,
        "requires_empty_readiness_gate_first": True,
    }
    assert all(
        line.startswith(
            (
                "proof_anchor_id:",
                "coordination_session_id:",
                "compact_decision_id:",
                "review_packet_id:",
            )
        )
        for line in capsule["session_handoff_capsule"]["header_lines"]
    )


def test_aas_session_handoff_capsule_is_read_only_internal_admin_only():
    capsule = build_aas_session_handoff_capsule()

    assert capsule["derived_from"]["read_only"] is True
    assert capsule["derived_from"]["mutates_irc_runtime_session_manager"] is False
    assert capsule["derived_from"]["reads_raw_transcripts"] is False
    assert capsule["derived_from"]["writes_live_acontext"] is False
    assert capsule["derived_from"]["retrieves_live_acontext"] is False
    assert capsule["derived_from"]["emits_reputation_receipts"] is False
    assert capsule["access_policy"]["customer_visible"] is False
    assert capsule["access_policy"]["public_route_registered"] is False
    assert capsule["access_policy"]["dispatch_enabled"] is False
    assert capsule["access_policy"]["gps_or_raw_metadata_release_allowed"] is False


def test_aas_session_handoff_capsule_carries_claim_boundaries():
    capsule = build_aas_session_handoff_capsule()
    safe = set(capsule["claim_boundaries"]["safe_to_claim"])
    blocked = set(capsule["claim_boundaries"]["do_not_claim_yet"])

    assert AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM in safe
    assert AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM in safe
    assert AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM in safe
    assert safe.isdisjoint(blocked)
    assert "session_handoff_capsule_mutates_irc_runtime_session_manager" in blocked
    assert "session_handoff_capsule_proves_memory_acontext_parity" in blocked
    assert "session_handoff_capsule_authorizes_public_or_catalog_route" in blocked
    assert "session_handoff_capsule_authorizes_erc8004_reputation_or_worker_skill_dna" in blocked
    assert "session_handoff_capsule_allows_exact_gps_or_raw_metadata" in blocked
    assert "session_handoff_capsule_creates_worker_copyable_doctrine" in blocked


def test_aas_session_handoff_capsule_success_metrics_are_not_customer_visible():
    capsule = build_aas_session_handoff_capsule()
    metrics = {card["metric"]: card for card in capsule["success_metric_assertions"]}

    assert metrics["aas_handoff_four_id_completeness_rate"]["observed"] is True
    assert metrics["aas_claim_boundary_survival_rate"]["observed"] is True
    assert metrics["aas_one_next_proof_slot_survival_rate"]["observed"] is True
    assert metrics["aas_memory_candidate_retrieval_parity_rate"]["observed"] is False
    assert all(card["customer_visible"] is False for card in metrics.values())


def test_aas_session_handoff_capsule_refuses_promoted_selector():
    selector = copy.deepcopy(build_aas_next_truth_selector())
    selector["readiness"]["more_route_layers_allowed"] = True

    with pytest.raises(CityOpsContractError, match="more_route_layers_allowed"):
        build_aas_session_handoff_capsule(selector=selector)


def test_aas_session_handoff_capsule_refuses_promoted_metrics_board():
    board = copy.deepcopy(build_aas_coordination_observability_success_metrics_board())
    board["readiness"]["agent_observability_live_dashboard_ready"] = True

    with pytest.raises(
        CityOpsContractError, match="agent_observability_live_dashboard_ready"
    ):
        build_aas_session_handoff_capsule(metrics_board=board)


def test_aas_session_handoff_capsule_refuses_claim_overlap():
    selector = copy.deepcopy(build_aas_next_truth_selector())
    selector["claim_boundaries"]["do_not_claim_yet"].append(
        selector["claim_boundaries"]["safe_to_claim"][0]
    )

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_session_handoff_capsule(selector=selector)


def test_aas_session_handoff_capsule_write_and_load_temp_fixture(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_session_handoff_capsule(artifact_dir=tmp_path)

    assert path.name == AAS_SESSION_HANDOFF_CAPSULE_FILENAME
    loaded = load_aas_session_handoff_capsule(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_SESSION_HANDOFF_CAPSULE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM
    )


def test_aas_session_handoff_capsule_loader_rejects_drift(tmp_path):
    _copy_all_proof_block_sources(tmp_path)
    path = write_aas_session_handoff_capsule(artifact_dir=tmp_path)
    capsule = json.loads(path.read_text(encoding="utf-8"))
    capsule["readiness"]["dispatch_ready"] = True
    path.write_text(json.dumps(capsule), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="dispatch_ready"):
        load_aas_session_handoff_capsule(artifact_dir=tmp_path)


def _copy_all_proof_block_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
