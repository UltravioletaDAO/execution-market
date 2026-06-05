"""Tests for the 4 AM AAS pattern-recognition multiplier ladder."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_four_am_pattern_recognition_multiplier_ladder import (
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME,
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM,
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SCHEMA,
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_STATUS,
    LADDER_FALSE_FLAGS,
    PATTERN_RECOGNITION_BLOCKED_CLAIMS,
    build_aas_four_am_pattern_recognition_multiplier_ladder,
    load_aas_four_am_pattern_recognition_multiplier_ladder,
    write_aas_four_am_pattern_recognition_multiplier_ladder,
)
from mcp_server.city_ops.aas_intelligence_flow_compounder import (
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
)
from mcp_server.city_ops.aas_operator_answer_receipt_gate import (
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_ladder() -> dict:
    return json.loads(
        (
            ARTIFACT_DIR
            / AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME
        ).read_text(encoding="utf-8")
    )


def seed_sources(tmp_path: Path, proof_tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        shutil.copy(source, proof_tmp_path / source.name)


def test_pattern_recognition_ladder_matches_persisted_artifact_and_loader() -> None:
    ladder = build_aas_four_am_pattern_recognition_multiplier_ladder()

    assert ladder == read_ladder()
    assert load_aas_four_am_pattern_recognition_multiplier_ladder() == ladder
    assert ladder["schema"] == AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SCHEMA
    assert ladder["ladder_status"] == AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_STATUS
    assert AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM in ladder["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM in ladder["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM in ladder[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_pattern_recognition_ladder_consumes_only_reviewed_sources() -> None:
    ladder = build_aas_four_am_pattern_recognition_multiplier_ladder()

    assert ladder["source_operator_answer_gate"]["file"] == AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME
    assert ladder["source_intelligence_flow_compounder"]["file"] == AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME
    assert len(ladder["source_operator_answer_gate"]["digest_sha256"]) == 64
    assert len(ladder["source_intelligence_flow_compounder"]["digest_sha256"]) == 64
    assert ladder["derived_from"]["read_only"] is True
    assert ladder["derived_from"]["source_artifacts"] == [
        AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
        AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
    ]
    assert "stopped_project_codebases_as_active_sources" in ladder["derived_from"][
        "forbidden_inputs"
    ]


def test_pattern_recognition_ladder_records_no_answer_or_external_promotion() -> None:
    ladder = build_aas_four_am_pattern_recognition_multiplier_ladder()

    for key, expected in LADDER_FALSE_FLAGS.items():
        assert ladder["readiness"][key] is expected
    for key, value in ladder["access_policy"].items():
        if key in {"audience", "requires_admin_context"}:
            continue
        assert value is False


def test_pattern_recognition_cards_answer_the_4am_questions_without_authority() -> None:
    ladder = build_aas_four_am_pattern_recognition_multiplier_ladder()
    cards = {card["pattern"]: card for card in ladder["pattern_recognition_cards"]}

    assert set(cards) == {
        "memory_system_data",
        "irc_coordination",
        "cross_project_intelligence_flows",
        "agent_coordination_scaling",
    }
    assert cards["memory_system_data"]["safe_use"] == "planning and boundary preservation only"
    assert "handoff format" in cards["irc_coordination"]["safe_use"]
    assert "stopped projects" in cards["cross_project_intelligence_flows"]["insight"]
    assert "one-next-proof" in cards["agent_coordination_scaling"]["insight"]


def test_pattern_recognition_ladder_keeps_required_gates_closed() -> None:
    ladder = build_aas_four_am_pattern_recognition_multiplier_ladder()
    gates = ladder["next_required_gates"]

    assert gates == [
        {
            "if_saúl_gives_no_answer": "pause_aas_proof_layering",
            "gate": "stop_no_movement_pause_proof_layering",
        },
        {
            "if_saúl_wants_product_lane": "create_retail_reality_answer_or_hold_record",
            "gate": "create_retail_reality_answer_or_hold_record_before_any_public_or_dispatch_step",
        },
        {
            "if_saúl_wants_runtime_memory_lane": "create_runtime_memory_operator_answer_record",
            "gate": "create_runtime_memory_operator_answer_record_then_restore_docker_and_rerun_read_only_inventory",
        },
        {
            "if_saúl_wants_hold": "keep_both_lanes_held",
            "gate": "stop_no_movement_keep_both_lanes_held",
        },
    ]


def test_pattern_recognition_ladder_preserves_blocked_claims() -> None:
    ladder = build_aas_four_am_pattern_recognition_multiplier_ladder()
    safe = set(ladder["claim_boundaries"]["safe_to_claim"])
    blocked = set(ladder["claim_boundaries"]["do_not_claim_yet"])

    assert set(PATTERN_RECOGNITION_BLOCKED_CLAIMS) <= blocked
    assert not safe & blocked
    assert "pattern_recognition_ladder_integrates_stopped_projects" in blocked
    assert "pattern_recognition_ladder_mutates_irc_session_manager" in blocked
    assert "pattern_recognition_ladder_writes_or_retrieves_live_acontext" in blocked


def test_pattern_recognition_ladder_write_roundtrip_with_tmp_sources(
    tmp_path: Path,
) -> None:
    package_tmp = tmp_path / "package"
    proof_tmp = tmp_path / "proof"
    package_tmp.mkdir()
    proof_tmp.mkdir()
    seed_sources(package_tmp, proof_tmp)

    path = write_aas_four_am_pattern_recognition_multiplier_ladder(
        artifact_dir=package_tmp,
        proof_artifact_dir=proof_tmp,
    )

    assert path == package_tmp / AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME
    assert load_aas_four_am_pattern_recognition_multiplier_ladder(
        artifact_dir=package_tmp,
        proof_artifact_dir=proof_tmp,
    )["ladder_verdict"] == "pattern_recognition_multiplier_ladder_landed_internal_only"


def test_pattern_recognition_ladder_rejects_operator_gate_promotion() -> None:
    gate = json.loads((ARTIFACT_DIR / AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME).read_text())
    compounder = json.loads((PROOF_BLOCK_DIR / AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME).read_text())
    promoted = copy.deepcopy(gate)
    promoted["readiness"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_answer_recorded"):
        build_aas_four_am_pattern_recognition_multiplier_ladder(
            answer_gate=promoted,
            compounder=compounder,
        )


def test_pattern_recognition_ladder_rejects_compounder_runtime_promotion() -> None:
    gate = json.loads((ARTIFACT_DIR / AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME).read_text())
    compounder = json.loads((PROOF_BLOCK_DIR / AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME).read_text())
    promoted = copy.deepcopy(compounder)
    promoted["access_policy"]["writes_live_acontext"] = True

    with pytest.raises(CityOpsContractError, match="writes_live_acontext"):
        build_aas_four_am_pattern_recognition_multiplier_ladder(
            answer_gate=gate,
            compounder=promoted,
        )


def test_pattern_recognition_ladder_rejects_forbidden_safe_claim() -> None:
    gate = json.loads((ARTIFACT_DIR / AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME).read_text())
    compounder = json.loads((PROOF_BLOCK_DIR / AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME).read_text())
    promoted = copy.deepcopy(compounder)
    promoted["claim_boundaries"]["safe_to_claim"].append("dispatch_ready")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_aas_four_am_pattern_recognition_multiplier_ladder(
            answer_gate=gate,
            compounder=promoted,
        )
