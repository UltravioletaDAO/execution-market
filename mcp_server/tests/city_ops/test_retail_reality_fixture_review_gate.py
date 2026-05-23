import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.retail_reality_fixture_review_gate import (
    COVERED_LADDER_STEPS,
    NEXT_REQUIRED_LADDER_STEPS,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME,
    RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    RETAIL_REALITY_FIXTURE_REVIEW_GATE_SCHEMA,
    REVIEW_GATE_CHECKS,
    SOURCE_CONCEPT_DOC,
    build_retail_reality_fixture_review_gate,
    load_retail_reality_fixture_review_gate,
    write_retail_reality_fixture_review_gate,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"



def read_gate() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)



def test_retail_reality_fixture_review_gate_matches_persisted_artifact():
    gate = build_retail_reality_fixture_review_gate()

    assert gate == read_gate()
    assert load_retail_reality_fixture_review_gate() == gate
    assert gate["schema"] == RETAIL_REALITY_FIXTURE_REVIEW_GATE_SCHEMA
    assert gate["scope"] == "internal_admin_retail_reality_fixture_spec_and_review_gate_only"
    assert gate["package_family_id"] == PACKAGE_FAMILY_ID
    assert gate["source_concept_doc"] == SOURCE_CONCEPT_DOC
    assert gate["fixture_spec"]["offer_id"] == OFFER_ID
    assert RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM in gate["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in gate["safe_to_claim"]



def test_gate_stages_retail_reality_boundary_without_promotion():
    gate = build_retail_reality_fixture_review_gate()
    spec = gate["fixture_spec"]

    assert spec["family_label"] == "Retail Reality as a Service"
    assert spec["caas_source_pattern"] == "verify_place + counter_question + site_audit"
    assert gate["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert gate["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert gate["ladder_boundary"]["promotion_allowed"] is False
    assert spec["customer_copy_changed"] is False
    assert spec["phase_1_sellable_claim_allowed"] is False
    assert spec["automation_claim_allowed"] is False



def test_fixture_spec_names_retail_evidence_output_fields_and_acceptance_gate():
    gate = build_retail_reality_fixture_review_gate()
    spec = gate["fixture_spec"]

    for field in REQUIRED_EVIDENCE_FIELDS:
        assert field in spec["required_evidence_fields"]
    for field in REQUIRED_OUTPUT_FIELDS:
        assert field in spec["reviewed_output_schema_draft"]["required_fields"]
    for forbidden_field in [
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "private_staff_identity",
        "employee_performance_judgment",
        "permanent_business_status_claim",
        "inventory_guarantee_language",
        "brand_compliance_certification_claim",
        "consumer_safety_claim",
        "worker_copyable_retail_doctrine",
    ]:
        assert forbidden_field in spec["reviewed_output_schema_draft"]["forbidden_fields"]
    assert spec["fixture_acceptance_gate"]["requires_local_reviewed_fixture"] is True
    assert spec["fixture_acceptance_gate"]["allows_customer_delivery"] is False
    assert spec["fixture_acceptance_gate"]["allows_publication"] is False



def test_review_checklist_blocks_promotion_and_customer_surfaces():
    gate = build_retail_reality_fixture_review_gate()

    assert [item["check_id"] for item in gate["review_gate_checklist"]] == REVIEW_GATE_CHECKS
    for item in gate["review_gate_checklist"]:
        assert item["required"] is True
        assert item["status"] == "pending_future_review"
        assert item["blocks_promotion_until_passed"] is True

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_retail_doctrine",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "permanent_business_status_claim",
        "inventory_guarantee",
    ]:
        assert claim in gate["do_not_claim_yet"]
        assert claim not in gate["safe_to_claim"]



def test_readiness_flags_remain_false():
    gate = build_retail_reality_fixture_review_gate()

    assert gate["readiness"]["customer_copy_ready"] is False
    assert gate["readiness"]["public_service_catalog_ready"] is False
    assert gate["readiness"]["live_acontext_ready"] is False
    assert gate["readiness"]["runtime_parity_proven"] is False
    assert gate["readiness"]["autonomous_dispatch_ready"] is False
    assert gate["readiness"]["reputation_ready"] is False
    assert gate["readiness"]["worker_skill_dna_ready"] is False
    assert gate["readiness"]["worker_copyable_doctrine_ready"] is False
    assert gate["readiness"]["exact_gps_or_raw_metadata_exposure_allowed"] is False



def test_write_retail_reality_fixture_review_gate_persists_valid_artifact(tmp_path):
    path = write_retail_reality_fixture_review_gate(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME
    assert load_retail_reality_fixture_review_gate(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )



def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    gate = build_retail_reality_fixture_review_gate()
    gate["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_retail_reality_fixture_review_gate(artifact_dir=tmp_path)



def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    gate = build_retail_reality_fixture_review_gate()
    gate["safe_to_claim"].append("retail_reality_catalog_ready")
    (tmp_path / RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_fixture_review_gate(artifact_dir=tmp_path)



def test_loader_fails_closed_on_dropped_blocked_claim(tmp_path):
    gate = build_retail_reality_fixture_review_gate()
    gate["do_not_claim_yet"] = [
        claim
        for claim in gate["do_not_claim_yet"]
        if claim != "worker_copyable_retail_doctrine"
    ]
    (tmp_path / RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        load_retail_reality_fixture_review_gate(artifact_dir=tmp_path)



def test_loader_fails_closed_on_review_checklist_promotion(tmp_path):
    gate = build_retail_reality_fixture_review_gate()
    gate["review_gate_checklist"][0]["status"] = "passed"
    (tmp_path / RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="checklist status drift"):
        load_retail_reality_fixture_review_gate(artifact_dir=tmp_path)



def test_loader_fails_closed_on_fixture_acceptance_customer_delivery(tmp_path):
    gate = build_retail_reality_fixture_review_gate()
    gate["fixture_spec"]["fixture_acceptance_gate"]["allows_customer_delivery"] = True
    (tmp_path / RETAIL_REALITY_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_retail_reality_fixture_review_gate(artifact_dir=tmp_path)
