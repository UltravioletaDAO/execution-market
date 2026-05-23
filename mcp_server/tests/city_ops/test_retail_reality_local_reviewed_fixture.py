import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.retail_reality_fixture_review_gate import (
    RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    build_retail_reality_fixture_review_gate,
)
from mcp_server.city_ops.retail_reality_local_reviewed_fixture import (
    COVERED_LADDER_STEPS,
    FIXTURE_ID,
    LOCAL_FIXTURE_REVIEW_CHECKS,
    NEXT_REQUIRED_LADDER_STEPS,
    RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME,
    RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SCHEMA,
    build_retail_reality_local_reviewed_fixture,
    load_retail_reality_local_reviewed_fixture,
    write_retail_reality_local_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_retail_reality_local_reviewed_fixture_matches_persisted_artifact():
    fixture = build_retail_reality_local_reviewed_fixture()

    assert fixture == read_fixture()
    assert load_retail_reality_local_reviewed_fixture() == fixture
    assert fixture["schema"] == RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SCHEMA
    assert fixture["fixture_id"] == FIXTURE_ID
    assert fixture["scope"] == "internal_admin_retail_reality_local_reviewed_fixture_only"
    assert fixture["offer_id"] == "storefront_hours_availability_check"
    assert RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in fixture["safe_to_claim"]


def test_fixture_advances_exactly_one_ladder_rung_without_promotion():
    fixture = build_retail_reality_local_reviewed_fixture()

    assert fixture["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert fixture["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert fixture["ladder_boundary"]["promotion_allowed"] is False
    assert fixture["local_fixture"]["review_status"] == (
        "reviewed_internal_fixture_only_not_promoted"
    )


def test_fixture_populates_required_retail_evidence_and_reviewed_output_fields():
    fixture = build_retail_reality_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]
    evidence = local_fixture["evidence_contract_snapshot"]
    reviewed_output = local_fixture["reviewed_output"]

    for field in [
        "storefront_context_photo_or_permitted_visual_snapshot",
        "posted_hours_or_open_closed_state_proof",
        "observation_window",
        "staff_answer_source_type_where_available",
        "availability_or_service_observed_state",
        "discrepancy_summary_between_posted_and_observed_state",
        "uncertainty_note",
        "what_was_not_checked",
    ]:
        assert field in evidence

    for field in local_fixture["reviewed_output_schema"]["required_fields"]:
        assert field in reviewed_output
    assert "not a permanent business-status claim" in reviewed_output[
        "plain_language_observation_status"
    ]
    assert "not an inventory guarantee" in reviewed_output[
        "plain_language_observation_status"
    ]
    assert "staff_answer_source_type" in reviewed_output["source_type_summary"]
    assert "future state remains unchecked" in reviewed_output["discrepancy_summary"]


def test_fixture_blocks_customer_public_pricing_dispatch_reputation_and_worker_doctrine():
    fixture = build_retail_reality_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]

    assert local_fixture["customer_copy_changed"] is False
    assert local_fixture["customer_delivery_allowed"] is False
    assert local_fixture["publication_allowed"] is False
    assert local_fixture["catalog_allowed"] is False
    assert local_fixture["pricing_quote_allowed"] is False
    assert local_fixture["dispatch_allowed"] is False
    assert local_fixture["reputation_attachment_allowed"] is False
    assert local_fixture["worker_skill_dna_allowed"] is False
    assert local_fixture["worker_copyable_doctrine_allowed"] is False
    assert local_fixture["permanent_business_status_claim_allowed"] is False
    assert local_fixture["inventory_guarantee_allowed"] is False
    assert local_fixture["brand_compliance_claim_allowed"] is False
    assert local_fixture["employee_performance_judgment_allowed"] is False
    assert local_fixture["consumer_safety_claim_allowed"] is False

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_retail_doctrine",
        "permanent_business_status_claim",
        "inventory_guarantee",
        "brand_compliance_certification",
        "employee_performance_judgment",
        "consumer_safety_claim",
        "retail_reality_local_fixture_customer_delivery_ready",
        "retail_reality_local_fixture_pricing_ready",
        "retail_reality_local_fixture_dispatch_ready",
        "retail_reality_local_fixture_worker_doctrine_ready",
    ]:
        assert claim in fixture["do_not_claim_yet"]
        assert claim not in fixture["safe_to_claim"]


def test_readiness_flags_remain_false():
    fixture = build_retail_reality_local_reviewed_fixture()

    assert fixture["readiness"]["customer_copy_ready"] is False
    assert fixture["readiness"]["public_service_catalog_ready"] is False
    assert fixture["readiness"]["live_acontext_ready"] is False
    assert fixture["readiness"]["runtime_parity_proven"] is False
    assert fixture["readiness"]["autonomous_dispatch_ready"] is False
    assert fixture["readiness"]["reputation_ready"] is False
    assert fixture["readiness"]["worker_skill_dna_ready"] is False
    assert fixture["readiness"]["worker_copyable_doctrine_ready"] is False
    assert fixture["readiness"]["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_local_review_checks_pass_only_for_local_fixture_and_still_block_promotion():
    fixture = build_retail_reality_local_reviewed_fixture()

    assert [item["check_id"] for item in fixture["local_review_checks"]] == (
        LOCAL_FIXTURE_REVIEW_CHECKS
    )
    for item in fixture["local_review_checks"]:
        assert item["status"] == "passed_for_local_fixture_only"
        assert item["blocks_promotion_until_later_gate"] is True


def test_write_retail_reality_local_reviewed_fixture_persists_valid_artifact(tmp_path):
    path = write_retail_reality_local_reviewed_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME
    assert load_retail_reality_local_reviewed_fixture(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_fixture_fails_closed_when_source_gate_promotes_readiness():
    gate = copy.deepcopy(build_retail_reality_fixture_review_gate())
    gate["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source gate promoted readiness"):
        build_retail_reality_local_reviewed_fixture(gate=gate)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    fixture = build_retail_reality_local_reviewed_fixture()
    fixture["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_retail_reality_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    fixture = build_retail_reality_local_reviewed_fixture()
    fixture["safe_to_claim"].append("retail_reality_local_fixture_publication_ready")
    (tmp_path / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_private_staff_identity_language(tmp_path):
    fixture = build_retail_reality_local_reviewed_fixture()
    fixture["local_fixture"]["reviewed_output"]["source_type_summary"] = (
        "private staff name was copied into the output"
    )
    (tmp_path / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private metadata or overclaimed"):
        load_retail_reality_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_inventory_overclaim(tmp_path):
    fixture = build_retail_reality_local_reviewed_fixture()
    fixture["local_fixture"]["reviewed_output"]["limitations_and_non_guarantees"].append(
        "inventory guarantee provided for future customers"
    )
    (tmp_path / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private metadata or overclaimed"):
        load_retail_reality_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_when_review_check_stops_blocking(tmp_path):
    fixture = build_retail_reality_local_reviewed_fixture()
    fixture["local_review_checks"][0]["blocks_promotion_until_later_gate"] = False
    (tmp_path / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="stopped blocking promotion"):
        load_retail_reality_local_reviewed_fixture(artifact_dir=tmp_path)
