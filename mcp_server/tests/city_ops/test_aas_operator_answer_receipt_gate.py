"""Tests for the AAS operator answer receipt gate."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_four_am_pattern_synthesis_handoff import (
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME,
    write_aas_four_am_pattern_synthesis_handoff,
)
from mcp_server.city_ops.aas_no_answer_observability_rubric_fixture import (
    write_aas_no_answer_observability_rubric_fixture,
)
from mcp_server.city_ops.aas_operator_answer_receipt_gate import (
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS,
    FUTURE_RECEIPT_SCHEMA,
    NEXT_REQUIRED_GATE_BY_VALUE,
    RECEIPT_GATE_BLOCKED_CLAIMS,
    RECEIPT_GATE_FALSE_FLAGS,
    RECEIPT_REQUIRED_FIELDS,
    SOURCE_COCKPIT_REF,
    build_aas_operator_answer_receipt_gate,
    load_aas_operator_answer_receipt_gate,
    validate_aas_operator_answer_receipt,
    write_aas_operator_answer_receipt_gate,
)
from mcp_server.city_ops.aas_operator_cockpit_read_surface import (
    AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME,
    AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM,
    build_aas_operator_cockpit_read_surface,
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


def read_gate() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME).read_text(
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
            AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
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
    write_aas_operator_cockpit_read_surface(artifact_dir=tmp_path)


def valid_receipt(gate: dict, value: str = "create_retail_reality_answer_or_hold_record") -> dict:
    return {
        "answer_receipt_id": "execution_market.aas.operator_answer.2026_06_05.fixture",
        "receipt_schema": FUTURE_RECEIPT_SCHEMA,
        "source_cockpit_ref": SOURCE_COCKPIT_REF,
        "source_cockpit_digest_sha256": gate["source_cockpit"]["digest_sha256"],
        "operator_answer_value": value,
        "operator_answer_recorded": True,
        "operator_approval_recorded": False,
        "explicit_operator_reference": "fixture_explicit_operator_answer_ref",
        "approval_evidence_ref": "",
        "approved_sections": [],
        "held_sections": ["public_delivery", "runtime_path", "dispatch"],
        "redactions_passed": False,
        "delivery_path_authorized": False,
        "runtime_path_authorized": False,
        "blocked_claims_preserved": True,
        "next_required_gate": NEXT_REQUIRED_GATE_BY_VALUE[value],
    }


def test_answer_receipt_gate_matches_persisted_artifact_and_loader() -> None:
    gate = build_aas_operator_answer_receipt_gate()

    assert gate == read_gate()
    assert load_aas_operator_answer_receipt_gate() == gate
    assert gate["schema"] == AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA
    assert gate["gate_status"] == AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS
    assert gate["future_receipt_schema"] == FUTURE_RECEIPT_SCHEMA
    assert AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM in gate["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM in gate["claim_boundaries"][
        "safe_to_claim"
    ]


def test_answer_receipt_gate_consumes_only_operator_cockpit() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    source = gate["source_cockpit"]

    assert source["file"] == AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME
    assert source["ref"] == SOURCE_COCKPIT_REF
    assert source["safe_claim"] == AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM
    assert source["default_if_no_human_answer"] == DEFAULT_EFFECTIVE_DECISION
    assert len(source["digest_sha256"]) == 64


def test_answer_receipt_gate_constrains_four_future_answer_values_without_selection() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    values = gate["allowed_operator_answer_values"]

    assert [item["value"] for item in values] == ALLOWED_FUTURE_DECISIONS
    for item in values:
        assert item["accepted_by_future_receipt"] is True
        assert item["selected_by_this_gate"] is False
        assert item["approval_granted_by_this_gate"] is False
        assert item["delivery_path_authorized_by_this_gate"] is False
        assert item["runtime_path_authorized_by_this_gate"] is False
        assert item["next_required_gate_if_explicitly_chosen"] == NEXT_REQUIRED_GATE_BY_VALUE[
            item["value"]
        ]


def test_answer_receipt_gate_requires_future_receipt_fields_without_satisfying_them() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    fields = gate["future_receipt_required_fields"]

    assert [item["field"] for item in fields] == RECEIPT_REQUIRED_FIELDS
    for item in fields:
        assert item["required_in_future_receipt"] is True
        assert item["satisfied_by_this_gate"] is False


def test_answer_receipt_gate_records_no_answer_approval_or_external_promotion() -> None:
    gate = build_aas_operator_answer_receipt_gate()

    assert gate["current_values"] == {
        "operator_answer_recorded": False,
        "operator_approval_recorded": False,
        "selected_operator_answer_value": None,
        "future_answer_receipt_created": False,
        "effective_decision": DEFAULT_EFFECTIVE_DECISION,
        "cockpit_display_is_answer": False,
        "gate_is_answer_receipt": False,
    }
    assert gate["readiness"]["internal_admin_answer_receipt_gate_landed"] is True
    for flag, expected in RECEIPT_GATE_FALSE_FLAGS.items():
        assert gate["readiness"][flag] is expected


def test_answer_receipt_gate_preserves_blocked_claim_boundaries() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    safe = set(gate["claim_boundaries"]["safe_to_claim"])
    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])

    assert set(RECEIPT_GATE_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_future_answer_receipt",
        "display_as_answer",
        "approves_product_exposure",
        "runtime_memory_wiring",
        "runtime_adapter",
        "irc_session_manager",
        "live_acontext",
        "customer_public_worker_surface",
        "catalog_pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_context",
        "stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_answer_receipt_gate_preserves_stopped_project_firewall() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    firewall = gate["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_answer_receipt_gate_write_and_load_round_trip(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)

    path = write_aas_operator_answer_receipt_gate(artifact_dir=product_tmp_path)

    assert path == product_tmp_path / AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME
    assert load_aas_operator_answer_receipt_gate(artifact_dir=product_tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_answer_receipt_gate_rejects_source_cockpit_that_records_answer() -> None:
    source = copy.deepcopy(build_aas_operator_cockpit_read_surface())
    source["current_no_answer_decision"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="recorded answer"):
        build_aas_operator_answer_receipt_gate(source_cockpit=source)


def test_answer_receipt_gate_loader_rejects_tampered_promotion(tmp_path: Path) -> None:
    proof_tmp_path = tmp_path / "proof"
    product_tmp_path = tmp_path / "product"
    proof_tmp_path.mkdir()
    product_tmp_path.mkdir()
    seed_sources(product_tmp_path, proof_tmp_path)
    path = write_aas_operator_answer_receipt_gate(artifact_dir=product_tmp_path)
    gate = json.loads(path.read_text(encoding="utf-8"))
    gate["readiness"]["dispatch_enabled"] = True
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="dispatch_enabled"):
        load_aas_operator_answer_receipt_gate(artifact_dir=product_tmp_path)


def test_answer_receipt_validator_accepts_explicit_receipt_without_authorizing_paths() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    receipt = valid_receipt(gate)

    verdict = validate_aas_operator_answer_receipt(receipt, gate=gate)

    assert verdict == {
        "receipt_valid": True,
        "accepted_operator_answer_value": "create_retail_reality_answer_or_hold_record",
        "next_required_gate": NEXT_REQUIRED_GATE_BY_VALUE[
            "create_retail_reality_answer_or_hold_record"
        ],
        "delivery_path_authorized": False,
        "runtime_path_authorized": False,
        "blocked_claims_preserved": True,
    }


def test_answer_receipt_validator_accepts_each_allowed_value_with_matching_next_gate() -> None:
    gate = build_aas_operator_answer_receipt_gate()

    for value in ALLOWED_FUTURE_DECISIONS:
        receipt = valid_receipt(gate, value=value)
        verdict = validate_aas_operator_answer_receipt(receipt, gate=gate)
        assert verdict["accepted_operator_answer_value"] == value
        assert verdict["next_required_gate"] == NEXT_REQUIRED_GATE_BY_VALUE[value]


def test_answer_receipt_validator_rejects_missing_explicit_reference() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    receipt = valid_receipt(gate)
    receipt["explicit_operator_reference"] = ""

    with pytest.raises(CityOpsContractError, match="lacks explicit reference"):
        validate_aas_operator_answer_receipt(receipt, gate=gate)


def test_answer_receipt_validator_rejects_delivery_or_runtime_authorization() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    delivery_receipt = valid_receipt(gate)
    delivery_receipt["delivery_path_authorized"] = True
    runtime_receipt = valid_receipt(gate)
    runtime_receipt["runtime_path_authorized"] = True

    with pytest.raises(CityOpsContractError, match="authorized delivery too early"):
        validate_aas_operator_answer_receipt(delivery_receipt, gate=gate)
    with pytest.raises(CityOpsContractError, match="authorized runtime too early"):
        validate_aas_operator_answer_receipt(runtime_receipt, gate=gate)


def test_answer_receipt_validator_rejects_next_gate_mismatch() -> None:
    gate = build_aas_operator_answer_receipt_gate()
    receipt = valid_receipt(gate, value="create_runtime_memory_operator_answer_record")
    receipt["next_required_gate"] = NEXT_REQUIRED_GATE_BY_VALUE[
        "create_retail_reality_answer_or_hold_record"
    ]

    with pytest.raises(CityOpsContractError, match="next gate mismatch"):
        validate_aas_operator_answer_receipt(receipt, gate=gate)
