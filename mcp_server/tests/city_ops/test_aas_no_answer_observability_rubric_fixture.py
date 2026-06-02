"""Tests for the AAS no-answer observability rubric fixture."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_no_answer_observability_rubric_fixture import (
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME,
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM,
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SCHEMA,
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_VERDICT,
    NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS,
    NO_ANSWER_OBSERVABILITY_STOP_LINE,
    build_aas_no_answer_observability_rubric_fixture,
    load_aas_no_answer_observability_rubric_fixture,
    write_aas_no_answer_observability_rubric_fixture,
)
from mcp_server.city_ops.aas_session_manager_no_mutation_adapter_field_map import (
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME,
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM,
    build_aas_session_manager_no_mutation_adapter_field_map,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME).exists()


def test_no_answer_observability_rubric_matches_fixture() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    fixture = json.loads(
        (PROOF_BLOCK_DIR / AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME).read_text(
            encoding="utf-8"
        )
    )

    assert rubric == fixture
    assert load_aas_no_answer_observability_rubric_fixture() == rubric
    assert rubric["schema"] == AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SCHEMA
    assert rubric["status_verdict"] == AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_VERDICT
    assert AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM in rubric[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM in rubric[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_no_answer_observability_preserves_hold_and_records_no_approval() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    observed = rubric["no_answer_observability_rubric"]

    assert observed["current_decision"] == "hold_no_runtime_mutation"
    assert observed["effective_decision_after_rubric"] == "hold_no_runtime_mutation"
    assert observed["explicit_operator_answer_present"] is False
    assert observed["operator_approval_record_present"] is False
    assert observed["score_treated_as_approval"] is False
    assert observed["dashboard_or_public_metric_authorized_now"] is False
    assert observed["runtime_mutation_authorized_now"] is False


def test_no_answer_observability_scores_only_boundary_preservation() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    scoring = rubric["scoring_model"]
    dimensions = rubric["rubric_dimensions"]

    assert scoring["model"] == "binary_boundary_preservation_v1"
    assert scoring["score_is_internal_admin_only"] is True
    assert scoring["score_is_not_reputation"] is True
    assert scoring["score_is_not_worker_skill_dna"] is True
    assert scoring["score_is_not_customer_metric"] is True
    assert scoring["passed"] is True
    assert scoring["total_score"] == scoring["max_score"] == len(dimensions)
    assert {item["dimension"] for item in dimensions} == {
        "safe_and_blocked_claims_carried_together",
        "no_answer_no_approval_preserved",
        "runtime_mutation_blocked",
        "acontext_live_access_blocked",
        "external_surfaces_blocked",
        "settlement_and_reputation_blocked",
        "privacy_and_authority_blocked",
        "stopped_project_firewall_preserved",
        "future_gates_not_passed_by_observation",
    }
    assert all(item["passed"] is True for item in dimensions)
    assert all(item["promotion_allowed"] is False for item in dimensions)


def test_no_answer_observability_blocks_dashboard_public_metrics_and_runtime() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    derived = rubric["derived_from"]
    access = rubric["access_flags"]

    assert derived["scores_only_boundary_preservation"] is True
    for key in [
        "records_operator_answer",
        "records_operator_approval",
        "treats_score_as_approval",
        "creates_dashboard",
        "creates_public_metric",
        "calls_acontext",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "changes_irc_runtime_session_manager",
        "registers_adapter",
        "enables_adapter",
        "enables_cross_project_autorouting",
        "writes_customer_copy",
        "writes_worker_instruction",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_or_production",
        "exposes_gps_or_metadata",
    ]:
        assert derived[key] is False

    assert access["rubric_fixture_documented"] is True
    for key, value in access.items():
        if key != "rubric_fixture_documented":
            assert value is False


def test_no_answer_observability_keeps_all_external_readiness_blocked() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    readiness = rubric["readiness"]

    assert readiness["safe_for_internal_admin_handoff_quality_review"] is True
    for key in [
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
        "safe_for_score_as_approval",
        "safe_for_observability_dashboard_or_public_metric",
        "safe_for_design_only_wiring_selection",
        "safe_for_bounded_local_activation_test_selection",
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_adapter_enablement",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_live_acontext_write_or_retrieval",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_worker_instruction_or_doctrine",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        assert readiness[key] is False


def test_no_answer_observability_preserves_blocked_claim_boundaries() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    safe = set(rubric["claim_boundaries"]["safe_to_claim"])
    blocked = set(rubric["claim_boundaries"]["do_not_claim_yet"])

    assert set(NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "score_as_approval",
        "dashboard_or_public_metric",
        "mutates_session_manager",
        "writes_or_retrieves_live_acontext",
        "runtime_parity",
        "customer_public_or_worker_surface",
        "pricing_queue_or_dispatch",
        "erc8004_reputation_or_worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_context_or_raw_transcripts",
        "stopped_projects",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_no_answer_observability_preserves_stopped_project_firewall() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    firewall = rubric["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_no_answer_observability_future_gates_are_not_passed() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()

    assert {gate["step"] for gate in rubric["future_gate_order"]} == {
        "separate_explicit_operator_answer_record",
        "separate_observability_surface_approval",
        "separate_design_only_wiring_approval_record",
        "bounded_local_activation_test_approval_record",
    }
    assert all(gate["passed_now"] is False for gate in rubric["future_gate_order"])
    assert all(action["customer_or_worker_action_allowed"] is False for action in rubric["failure_actions"])


def test_no_answer_observability_stop_line_remains_fail_closed() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()

    assert rubric["operator_guidance"]["stop_line"] == NO_ANSWER_OBSERVABILITY_STOP_LINE
    assert "coordination-quality fixture only" in rubric["operator_guidance"]["stop_line"]
    assert "records no answer or approval" in rubric["operator_guidance"]["stop_line"]
    assert "does not authorize dashboards" in rubric["operator_guidance"]["stop_line"]
    assert rubric["operator_guidance"]["not_customer_copy"] is True
    assert rubric["operator_guidance"]["not_worker_instruction"] is True
    assert rubric["operator_guidance"]["not_dashboard_spec"] is True


def test_no_answer_observability_persists_no_secret_ids_payload_or_pii() -> None:
    rubric = build_aas_no_answer_observability_rubric_fixture()
    serialized = json.dumps(rubric).lower()

    assert "bearer " + "sk" + "-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret" + "_key_" + "hmac" not in serialized
    assert "secret" + "_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None
    assert "@" not in serialized
    assert "raw_session_id" not in serialized
    assert "raw_message_id" not in serialized


def test_no_answer_observability_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_aas_no_answer_observability_rubric_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME
    loaded = load_aas_no_answer_observability_rubric_fixture(artifact_dir=tmp_path)
    assert loaded == build_aas_no_answer_observability_rubric_fixture(artifact_dir=tmp_path)


def test_no_answer_observability_rejects_promoted_source() -> None:
    source = build_aas_session_manager_no_mutation_adapter_field_map()
    promoted = copy.deepcopy(source)
    promoted["readiness"]["safe_for_runtime_session_manager_mutation"] = True

    with pytest.raises(CityOpsContractError, match="source field map readiness promoted"):
        build_aas_no_answer_observability_rubric_fixture(field_map=promoted)


def test_no_answer_observability_rejects_fixture_promotion(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_aas_no_answer_observability_rubric_fixture(artifact_dir=tmp_path)
    fixture = json.loads(path.read_text(encoding="utf-8"))
    fixture["access_flags"]["dashboard_created"] = True
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="access flag drift"):
        load_aas_no_answer_observability_rubric_fixture(artifact_dir=tmp_path)
