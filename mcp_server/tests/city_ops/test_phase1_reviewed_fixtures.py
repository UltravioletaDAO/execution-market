import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_reviewed_fixtures import (
    COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
    COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
    PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM,
    PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM,
    PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME,
    PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM,
    PHASE1_REVIEWED_FIXTURE_REGISTRY_SCHEMA,
    PHASE1_REVIEWED_FIXTURE_SCHEMA,
    POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
    POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    build_counter_reality_check_reviewed_fixture,
    build_packet_submission_attempt_reviewed_fixture,
    build_phase1_reviewed_fixture_registry_summary,
    build_posting_compliance_check_reviewed_fixture,
    load_counter_reality_check_reviewed_fixture,
    load_packet_submission_attempt_reviewed_fixture,
    load_phase1_reviewed_fixture_registry_summary,
    load_posting_compliance_check_reviewed_fixture,
)
from mcp_server.city_ops.phase1_review_output_schemas import validate_phase1_review_output

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_reviewed_fixture(filename: str) -> dict:
    with (REVIEWED_FIXTURE_DIR / filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_counter_reality_check_reviewed_fixture_matches_persisted_fixture():
    fixture = build_counter_reality_check_reviewed_fixture()

    assert fixture == read_reviewed_fixture(COUNTER_REALITY_CHECK_FIXTURE_FILENAME)
    assert fixture["schema"] == PHASE1_REVIEWED_FIXTURE_SCHEMA
    assert fixture["offer_id"] == "counter_reality_check"
    assert COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM == COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM


def test_counter_reality_check_reviewed_output_validates_against_schema():
    fixture = build_counter_reality_check_reviewed_fixture()
    reviewed_output = fixture["reviewed_output"]

    assert reviewed_output["offer"] == "counter_reality_check"
    assert reviewed_output["outcome_status"] == "redirected"
    assert reviewed_output["source_type"] == "mixed"
    assert reviewed_output["operator_review_status"] == "reviewed"
    assert reviewed_output["proof_status_label"] == "planning_supported_needs_first_fixture"
    assert reviewed_output["forbidden_claims_preserved"] is True
    assert validate_phase1_review_output("counter_reality_check", reviewed_output)["status"] == "passed"


def test_counter_reality_check_fixture_keeps_source_boundaries_and_no_raw_authority():
    fixture = build_counter_reality_check_reviewed_fixture()
    scenario = fixture["scenario"]
    evidence = " ".join(fixture["reviewed_output"]["evidence_summary"])

    assert scenario["raw_transcript_used_as_authority"] is False
    assert scenario["unreviewed_memory_used"] is False
    assert "Documented source" in evidence
    assert "Observed source" in evidence
    assert "Staff-heard source" in evidence
    assert "legal conclusion" in evidence


def test_posting_compliance_check_reviewed_fixture_matches_persisted_fixture():
    fixture = build_posting_compliance_check_reviewed_fixture()

    assert fixture == read_reviewed_fixture(POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME)
    assert fixture["schema"] == PHASE1_REVIEWED_FIXTURE_SCHEMA
    assert fixture["offer_id"] == "posting_compliance_check"
    assert POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]


def test_posting_compliance_check_reviewed_output_validates_against_schema():
    fixture = build_posting_compliance_check_reviewed_fixture()
    reviewed_output = fixture["reviewed_output"]

    assert reviewed_output["offer"] == "posting_compliance_check"
    assert reviewed_output["outcome_status"] == "verified_partial"
    assert reviewed_output["source_type"] == "observed"
    assert reviewed_output["checklist_result"] == "partial_visibility_legibility_not_confirmed"
    assert reviewed_output["follow_on_task_trigger"] == "posting_recheck"
    assert reviewed_output["operator_review_status"] == "reviewed"
    assert reviewed_output["proof_status_label"] == "planning_supported_needs_first_fixture"
    assert reviewed_output["forbidden_claims_preserved"] is True
    assert validate_phase1_review_output("posting_compliance_check", reviewed_output)["status"] == "passed"


def test_posting_compliance_check_fixture_preserves_access_and_privacy_boundaries():
    fixture = build_posting_compliance_check_reviewed_fixture()
    scenario = fixture["scenario"]
    reviewed_output = fixture["reviewed_output"]
    evidence = " ".join(reviewed_output["evidence_summary"])

    assert scenario["raw_transcript_used_as_authority"] is False
    assert scenario["unreviewed_memory_used"] is False
    assert scenario["exact_gps_or_metadata_exposed"] is False
    assert "wide/context evidence" in evidence
    assert "close/legibility evidence" in evidence
    assert "access angle was constrained" in evidence
    assert "not regulator acceptance or legal sufficiency" in evidence
    assert "exact GPS or metadata" in reviewed_output["failure_reason"]


def test_packet_submission_attempt_reviewed_fixture_matches_persisted_fixture():
    fixture = build_packet_submission_attempt_reviewed_fixture()

    assert fixture == read_reviewed_fixture(PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME)
    assert fixture["schema"] == PHASE1_REVIEWED_FIXTURE_SCHEMA
    assert fixture["offer_id"] == "packet_submission_attempt"
    assert PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]


def test_packet_submission_attempt_reviewed_output_validates_against_schema():
    fixture = build_packet_submission_attempt_reviewed_fixture()
    reviewed_output = fixture["reviewed_output"]

    assert reviewed_output["offer"] == "packet_submission_attempt"
    assert reviewed_output["outcome_status"] == "rejected"
    assert reviewed_output["source_type"] == "mixed"
    assert reviewed_output["redirect_target"] == "not_applicable_non_redirect_attempt"
    assert reviewed_output["follow_on_task_trigger"] == "rejection_diagnosis_resubmission_prep"
    assert reviewed_output["operator_review_status"] == "reviewed"
    assert reviewed_output["proof_status_label"] == "local_anchor_supported_redirect_outdated_packet_only"
    assert reviewed_output["forbidden_claims_preserved"] is True
    assert validate_phase1_review_output("packet_submission_attempt", reviewed_output)["status"] == "passed"


def test_packet_submission_fixture_preserves_source_privacy_and_no_overclaim_boundaries():
    fixture = build_packet_submission_attempt_reviewed_fixture()
    scenario = fixture["scenario"]
    reviewed_output = fixture["reviewed_output"]
    evidence = " ".join(reviewed_output["evidence_summary"])
    next_step = reviewed_output["structured_next_step"]

    assert scenario["raw_transcript_used_as_authority"] is False
    assert scenario["unreviewed_memory_used"] is False
    assert scenario["exact_gps_or_metadata_exposed"] is False
    assert scenario["non_redirect_attempt"] is True
    assert scenario["retry_or_resubmission_included"] is False
    assert "Customer-supplied source" in evidence
    assert "Observed source" in evidence
    assert "Staff-heard source" in evidence
    assert "not approval, legal sufficiency" in evidence
    assert "No acceptance receipt" in reviewed_output["acceptance_evidence"]
    assert "do not bundle or guarantee a retry" in next_step


def test_reviewed_fixtures_do_not_promote_blocked_claims():
    for fixture in [
        build_counter_reality_check_reviewed_fixture(),
        build_packet_submission_attempt_reviewed_fixture(),
        build_posting_compliance_check_reviewed_fixture(),
    ]:
        promotion_gate = fixture["promotion_gate"]

        assert promotion_gate["ready_for_local_replay_gate"] is True
        assert promotion_gate["requires_operator_review"] is True
        assert promotion_gate["requires_existing_replay_promotion_gates"] is True
        assert promotion_gate["customer_copy_changed"] is False
        assert promotion_gate["durable_municipal_memory_write_performed"] is False
        assert promotion_gate["acontext_write_performed"] is False
        assert promotion_gate["autonomous_dispatch_enabled"] is False
        assert "durable_municipal_memory_write" in fixture["do_not_claim_yet"]
        assert "live_acontext_readiness" in fixture["do_not_claim_yet"]
        assert "autonomous_dispatch_readiness" in fixture["do_not_claim_yet"]
        assert not (set(fixture["safe_to_claim"]) & set(fixture["do_not_claim_yet"]))


def test_load_reviewed_fixtures_validate_contract():
    counter_fixture = load_counter_reality_check_reviewed_fixture()
    packet_fixture = load_packet_submission_attempt_reviewed_fixture()
    posting_fixture = load_posting_compliance_check_reviewed_fixture()

    assert counter_fixture["fixture_id"] == "caas_phase1_counter_reality_check_redirect_outdated_packet_001"
    assert packet_fixture["fixture_id"] == "caas_phase1_packet_submission_attempt_rejected_fixable_non_redirect_001"
    assert posting_fixture["fixture_id"] == "caas_phase1_posting_compliance_check_partial_legibility_001"


def test_phase1_reviewed_fixture_registry_summary_matches_persisted_fixture():
    registry = build_phase1_reviewed_fixture_registry_summary()

    assert registry == read_reviewed_fixture(PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME)
    assert registry["schema"] == PHASE1_REVIEWED_FIXTURE_REGISTRY_SCHEMA
    assert registry["total_reviewed_fixtures"] == 3
    assert PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM in registry["safe_to_claim"]
    assert set(registry["offer_ids"]) == {
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    }


def test_phase1_reviewed_fixture_registry_keeps_safe_and_blocked_claims_adjacent():
    registry = build_phase1_reviewed_fixture_registry_summary()
    coverage = registry["coverage_by_offer"]

    assert registry["operator_observability"]["safe_and_blocked_claims_travel_together"] is True
    assert registry["operator_observability"]["exact_gps_or_metadata_exposed"] is False
    assert registry["commercial_scope"]["customer_copy_changed"] is False
    assert registry["commercial_scope"]["acontext_write_performed"] is False
    assert registry["commercial_scope"]["autonomous_dispatch_enabled"] is False
    assert not (set(registry["safe_to_claim"]) & set(registry["do_not_claim_yet"]))

    for offer_id, row in coverage.items():
        assert row["safe_to_claim"]
        assert row["do_not_claim_yet"]
        assert row["customer_copy_changed"] is False
        assert row["durable_municipal_memory_write_performed"] is False
        assert row["acontext_write_performed"] is False
        assert row["autonomous_dispatch_enabled"] is False


def test_counter_loader_rejects_promotion_overclaim(tmp_path):
    fixture_dir = tmp_path / "reviewed_outputs"
    fixture_dir.mkdir()
    fixture = build_counter_reality_check_reviewed_fixture()
    fixture["promotion_gate"]["acontext_write_performed"] = True
    (fixture_dir / COUNTER_REALITY_CHECK_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="overclaims promotion flags"):
        load_counter_reality_check_reviewed_fixture(fixture_dir=fixture_dir)


def test_posting_loader_rejects_exact_gps_or_metadata_exposure(tmp_path):
    fixture_dir = tmp_path / "reviewed_outputs"
    fixture_dir.mkdir()
    fixture = build_posting_compliance_check_reviewed_fixture()
    fixture["scenario"]["exact_gps_or_metadata_exposed"] = True
    (fixture_dir / POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="cannot expose exact GPS or metadata"):
        load_posting_compliance_check_reviewed_fixture(fixture_dir=fixture_dir)


def test_packet_loader_rejects_redirect_or_retry_overclaim(tmp_path):
    fixture_dir = tmp_path / "reviewed_outputs"
    fixture_dir.mkdir()
    fixture = build_packet_submission_attempt_reviewed_fixture()
    fixture["scenario"]["retry_or_resubmission_included"] = True
    (fixture_dir / PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="cannot bundle retries"):
        load_packet_submission_attempt_reviewed_fixture(fixture_dir=fixture_dir)


def test_registry_loader_rejects_scope_overclaim(tmp_path):
    fixture_dir = tmp_path / "reviewed_outputs"
    fixture_dir.mkdir()
    registry = build_phase1_reviewed_fixture_registry_summary()
    registry["commercial_scope"]["autonomous_dispatch_enabled"] = True
    (fixture_dir / PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME).write_text(
        json.dumps(registry), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="overclaims commercial scope"):
        load_phase1_reviewed_fixture_registry_summary(fixture_dir=fixture_dir)
