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
)
from mcp_server.city_ops.retail_reality_internal_package_record import (
    COVERED_LADDER_STEPS,
    NEXT_REQUIRED_LADDER_STEPS,
    PACKAGE_ID,
    PACKAGE_REVIEW_CHECKS,
    RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME,
    RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SCHEMA,
    build_retail_reality_internal_package_record,
    load_retail_reality_internal_package_record,
    write_retail_reality_internal_package_record,
)
from mcp_server.city_ops.retail_reality_local_reviewed_fixture import (
    RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    build_retail_reality_local_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_package_record() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_retail_reality_internal_package_record_matches_persisted_artifact():
    record = build_retail_reality_internal_package_record()

    assert record == read_package_record()
    assert load_retail_reality_internal_package_record() == record
    assert record["schema"] == RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SCHEMA
    assert record["package_id"] == PACKAGE_ID
    assert record["scope"] == "internal_admin_retail_reality_package_record_only"
    assert record["offer_id"] == "storefront_hours_availability_check"
    assert RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in record["safe_to_claim"]
    assert RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM in record["safe_to_claim"]
    assert RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM in record["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in record["safe_to_claim"]


def test_package_record_advances_exactly_one_ladder_rung_without_promotion():
    record = build_retail_reality_internal_package_record()

    assert record["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert record["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert record["ladder_boundary"]["promotion_allowed"] is False
    assert record["internal_package_record"]["review_status"] == (
        "packaged_internal_only_not_promoted"
    )


def test_package_record_preserves_retail_evidence_and_reviewed_output_fields():
    record = build_retail_reality_internal_package_record()
    package = record["internal_package_record"]
    evidence = package["packaged_evidence_contract"]
    reviewed_output = package["packaged_reviewed_output"]

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

    for field in package["reviewed_output_schema"]["required_fields"]:
        assert field in reviewed_output
    assert "not a permanent business-status claim" in reviewed_output[
        "plain_language_observation_status"
    ]
    assert "not an inventory guarantee" in reviewed_output[
        "plain_language_observation_status"
    ]
    assert "staff_answer_source_type" in reviewed_output["source_type_summary"]
    assert "future state remains unchecked" in reviewed_output["discrepancy_summary"]


def test_package_record_blocks_customer_public_pricing_dispatch_reputation_and_retail_overclaims():
    record = build_retail_reality_internal_package_record()
    package = record["internal_package_record"]

    assert package["customer_copy_changed"] is False
    assert package["customer_delivery_allowed"] is False
    assert package["publication_allowed"] is False
    assert package["catalog_allowed"] is False
    assert package["pricing_quote_allowed"] is False
    assert package["dispatch_allowed"] is False
    assert package["reputation_attachment_allowed"] is False
    assert package["worker_skill_dna_allowed"] is False
    assert package["worker_copyable_doctrine_allowed"] is False
    assert package["live_acontext_or_runtime_parity_claimed"] is False
    assert package["exact_gps_or_raw_metadata_exposure_allowed"] is False
    assert package["permanent_business_status_claim_allowed"] is False
    assert package["inventory_guarantee_allowed"] is False
    assert package["brand_compliance_claim_allowed"] is False
    assert package["employee_performance_judgment_allowed"] is False
    assert package["consumer_safety_claim_allowed"] is False

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_retail_doctrine",
        "retail_reality_internal_package_customer_delivery_ready",
        "retail_reality_internal_package_catalog_ready",
        "retail_reality_internal_package_pricing_ready",
        "retail_reality_internal_package_permanent_status_ready",
        "retail_reality_internal_package_inventory_guarantee_ready",
        "retail_reality_internal_package_consumer_safety_ready",
    ]:
        assert claim in record["do_not_claim_yet"]
        assert claim not in record["safe_to_claim"]


def test_readiness_flags_remain_false():
    record = build_retail_reality_internal_package_record()

    assert record["readiness"]["customer_copy_ready"] is False
    assert record["readiness"]["public_service_catalog_ready"] is False
    assert record["readiness"]["live_acontext_ready"] is False
    assert record["readiness"]["runtime_parity_proven"] is False
    assert record["readiness"]["autonomous_dispatch_ready"] is False
    assert record["readiness"]["reputation_ready"] is False
    assert record["readiness"]["worker_skill_dna_ready"] is False
    assert record["readiness"]["worker_copyable_doctrine_ready"] is False
    assert record["readiness"]["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_package_review_checks_pass_only_for_internal_package_and_still_block_promotion():
    record = build_retail_reality_internal_package_record()

    assert [item["check_id"] for item in record["package_review_checks"]] == (
        PACKAGE_REVIEW_CHECKS
    )
    for item in record["package_review_checks"]:
        assert item["status"] == "passed_for_internal_package_record_only"
        assert item["blocks_promotion_until_later_gate"] is True


def test_write_retail_reality_internal_package_record_persists_valid_artifact(tmp_path):
    path = write_retail_reality_internal_package_record(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME
    assert load_retail_reality_internal_package_record(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_package_record_fails_closed_when_source_fixture_promotes_readiness():
    fixture = build_retail_reality_local_reviewed_fixture()
    fixture = copy.deepcopy(fixture)
    fixture["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_retail_reality_internal_package_record(local_fixture=fixture)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    record = build_retail_reality_internal_package_record()
    record["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_retail_reality_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    record = build_retail_reality_internal_package_record()
    record["safe_to_claim"].append("retail_reality_internal_package_publication_ready")
    (tmp_path / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_on_private_identity_language(tmp_path):
    record = build_retail_reality_internal_package_record()
    record["internal_package_record"]["packaged_reviewed_output"][
        "source_type_summary"
    ] = "private staff name was copied for authority"
    (tmp_path / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private metadata or overclaimed"):
        load_retail_reality_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_on_retail_overclaim_language(tmp_path):
    record = build_retail_reality_internal_package_record()
    record["internal_package_record"]["packaged_reviewed_output"][
        "limitations_and_non_guarantees"
    ].append("inventory guarantee provided and consumer-safety claim provided")
    (tmp_path / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private metadata or overclaimed"):
        load_retail_reality_internal_package_record(artifact_dir=tmp_path)


def test_loader_fails_closed_when_review_check_stops_blocking(tmp_path):
    record = build_retail_reality_internal_package_record()
    record["package_review_checks"][0]["blocks_promotion_until_later_gate"] = False
    (tmp_path / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="stopped blocking promotion"):
        load_retail_reality_internal_package_record(artifact_dir=tmp_path)
