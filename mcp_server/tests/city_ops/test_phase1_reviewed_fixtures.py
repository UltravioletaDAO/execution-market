import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_reviewed_fixtures import (
    COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
    PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM,
    PHASE1_REVIEWED_FIXTURE_SCHEMA,
    build_counter_reality_check_reviewed_fixture,
    load_counter_reality_check_reviewed_fixture,
)
from mcp_server.city_ops.phase1_review_output_schemas import validate_phase1_review_output

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_counter_fixture() -> dict:
    with (REVIEWED_FIXTURE_DIR / COUNTER_REALITY_CHECK_FIXTURE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_counter_reality_check_reviewed_fixture_matches_persisted_fixture():
    fixture = build_counter_reality_check_reviewed_fixture()

    assert fixture == read_counter_fixture()
    assert fixture["schema"] == PHASE1_REVIEWED_FIXTURE_SCHEMA
    assert fixture["offer_id"] == "counter_reality_check"
    assert PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]


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


def test_counter_reality_check_fixture_does_not_promote_blocked_claims():
    fixture = build_counter_reality_check_reviewed_fixture()
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


def test_load_counter_reality_check_reviewed_fixture_validates_contract():
    fixture = load_counter_reality_check_reviewed_fixture()

    assert fixture["fixture_id"] == "caas_phase1_counter_reality_check_redirect_outdated_packet_001"


def test_loader_rejects_promotion_overclaim(tmp_path):
    fixture_dir = tmp_path / "reviewed_outputs"
    fixture_dir.mkdir()
    fixture = build_counter_reality_check_reviewed_fixture()
    fixture["promotion_gate"]["acontext_write_performed"] = True
    (fixture_dir / COUNTER_REALITY_CHECK_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="overclaims promotion flags"):
        load_counter_reality_check_reviewed_fixture(fixture_dir=fixture_dir)
