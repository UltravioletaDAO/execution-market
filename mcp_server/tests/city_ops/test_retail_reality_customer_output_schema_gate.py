import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.retail_reality_customer_output_schema_gate import (
    ALLOWED_CUSTOMER_OUTPUT_FIELDS,
    RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME,
    RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM,
    RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA,
    FORBIDDEN_CUSTOMER_OUTPUT_FIELDS,
    GATE_ID,
    NEXT_REQUIRED_LADDER_STEPS,
    build_retail_reality_customer_output_schema_gate,
    load_retail_reality_customer_output_schema_gate,
    write_retail_reality_customer_output_schema_gate,
)
from mcp_server.city_ops.retail_reality_operator_read_surface import (
    RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME,
    RETAIL_REALITY_OPERATOR_READ_SURFACE_SAFE_CLAIM,
    build_retail_reality_operator_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_gate() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_retail_reality_customer_output_schema_gate_matches_persisted_artifact():
    gate = build_retail_reality_customer_output_schema_gate()

    assert gate == read_gate()
    assert load_retail_reality_customer_output_schema_gate() == gate
    assert gate["schema"] == RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA
    assert gate["gate_id"] == GATE_ID
    assert gate["scope"] == "internal_admin_customer_output_schema_gate_only"
    assert gate["gate_status"] == "schema_gate_landed_not_customer_copy_not_public_not_approved"
    assert RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM in gate["safe_to_claim"]
    assert RETAIL_REALITY_OPERATOR_READ_SURFACE_SAFE_CLAIM in gate["safe_to_claim"]


def test_schema_gate_consumes_only_operator_read_surface_and_builder():
    gate = build_retail_reality_customer_output_schema_gate()
    contract = gate["source_contract"]

    assert gate["source_surface_file"] == RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME
    assert contract["consumes_only"] == [RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME]
    assert contract["source_builder"] == "build_retail_reality_operator_read_surface"
    assert contract["source_is_read_only_operator_surface"] is True
    assert contract["source_operator_cards_used_as_schema_inputs_only"] is True
    assert contract["source_payload_reinterpreted_as_customer_copy"] is False
    assert contract["reads_raw_review_fixture"] is False
    assert contract["reads_raw_transcripts"] is False
    assert contract["reads_raw_metadata"] is False
    assert contract["reads_private_operator_context"] is False


def test_schema_gate_defines_exact_allowed_and_forbidden_customer_output_fields():
    gate = build_retail_reality_customer_output_schema_gate()
    review = gate["schema_review"]

    assert review["allowed_customer_output_fields"] == ALLOWED_CUSTOMER_OUTPUT_FIELDS
    assert review["allowed_customer_output_fields"] == [
        "plain_language_status",
        "storefront_context_summary",
        "posted_hours_summary",
        "observed_open_closed_or_unable_to_determine_state",
        "availability_or_service_state_summary",
        "source_type_summary",
        "discrepancy_summary",
        "observation_window_summary",
        "what_was_checked",
        "what_was_not_checked",
        "limitations_and_non_guarantees",
        "recommended_next_step",
        "operator_review_notice",
        "privacy_redaction_notice",
    ]
    assert review["forbidden_customer_output_fields"] == FORBIDDEN_CUSTOMER_OUTPUT_FIELDS
    for field in [
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "permanent_business_status_claim",
        "inventory_guarantee_claim",
        "brand_compliance_certification_claim",
        "employee_performance_judgment",
        "consumer_safety_certification_claim",
        "continuous_availability_monitoring_claim",
        "dispatch_instruction_or_assignment",
        "erc8004_reputation_receipt",
        "worker_copyable_retail_doctrine",
        "customer_public_launch_readiness_claim",
        "catalog_or_pilot_readiness_claim",
    ]:
        assert field in review["forbidden_customer_output_fields"]
    assert not set(review["allowed_customer_output_fields"]) & set(
        review["forbidden_customer_output_fields"]
    )


def test_schema_gate_keeps_all_readiness_and_approval_flags_false():
    gate = build_retail_reality_customer_output_schema_gate()

    assert all(value is False for value in gate["readiness"].values())
    assert all(value is False for value in gate["schema_gate_readiness"].values())
    for flag in [
        "customer_copy_created",
        "customer_copy_ready",
        "public_route_registered",
        "dispatch_enabled",
        "emits_reputation_receipts",
        "permanent_business_status_ready",
        "inventory_guarantee_ready",
        "brand_compliance_ready",
        "employee_performance_judgment_ready",
        "consumer_safety_ready",
        "continuous_availability_monitoring_ready",
        "customer_public_launch_ready",
        "catalog_or_pilot_readiness_ready",
    ]:
        assert gate["schema_gate_readiness"][flag] is False


def test_schema_gate_blocks_external_product_and_outcome_claims():
    gate = build_retail_reality_customer_output_schema_gate()
    blocked = set(gate["do_not_claim_yet"])

    for claim in [
        "schema_gate_customer_copy_ready",
        "schema_gate_public_route_ready",
        "schema_gate_dispatch_ready",
        "schema_gate_reputation_ready",
        "schema_gate_exact_gps_or_raw_metadata_release_ready",
        "schema_gate_permanent_business_status_ready",
        "schema_gate_inventory_guarantee_ready",
        "schema_gate_brand_compliance_ready",
        "schema_gate_employee_performance_ready",
        "schema_gate_consumer_safety_ready",
        "schema_gate_continuous_availability_monitoring_ready",
        "retail_reality_customer_public_launch_ready",
        "retail_reality_catalog_or_pilot_readiness_ready",
    ]:
        assert claim in blocked
        assert claim not in gate["safe_to_claim"]
    assert gate["safe_to_claim"][-1] == RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM


def test_schema_gate_advances_ladder_without_promotion():
    gate = build_retail_reality_customer_output_schema_gate()

    assert gate["ladder_boundary"]["covered_steps"][-1] == "customer_output_schema_gate"
    assert gate["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert gate["ladder_boundary"]["promotion_allowed"] is False
    assert gate["next_smallest_proof"].startswith("Draft one internal/admin sample")


def test_write_retail_reality_customer_output_schema_gate_persists_valid_artifact(tmp_path):
    source = build_retail_reality_operator_read_surface()
    (tmp_path / RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )

    path = write_retail_reality_customer_output_schema_gate(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME
    assert load_retail_reality_customer_output_schema_gate(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_schema_gate_fails_closed_when_source_surface_promotes_public_access():
    surface = copy.deepcopy(build_retail_reality_operator_read_surface())
    surface["access_policy"]["public_route_registered"] = True

    with pytest.raises(CityOpsContractError, match="source access overclaims"):
        build_retail_reality_customer_output_schema_gate(operator_surface=surface)


def test_loader_fails_closed_on_customer_copy_created(tmp_path):
    source = build_retail_reality_operator_read_surface()
    gate = build_retail_reality_customer_output_schema_gate(operator_surface=source)
    gate["schema_gate_readiness"]["customer_copy_created"] = True
    (tmp_path / RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted schema readiness"):
        load_retail_reality_customer_output_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    source = build_retail_reality_operator_read_surface()
    gate = build_retail_reality_customer_output_schema_gate(operator_surface=source)
    gate["safe_to_claim"].append("schema_gate_dispatch_ready")
    (tmp_path / RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_customer_output_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_allowed_forbidden_field_overlap(tmp_path):
    source = build_retail_reality_operator_read_surface()
    gate = build_retail_reality_customer_output_schema_gate(operator_surface=source)
    gate["schema_review"]["forbidden_customer_output_fields"] = list(
        gate["schema_review"]["forbidden_customer_output_fields"]
    )
    gate["schema_review"]["forbidden_customer_output_fields"][0] = "plain_language_status"
    (tmp_path / RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden field drift"):
        load_retail_reality_customer_output_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_exact_location_language(tmp_path):
    source = build_retail_reality_operator_read_surface()
    gate = build_retail_reality_customer_output_schema_gate(operator_surface=source)
    gate["schema_review"]["required_boundary_notes"].append(
        "latitude and longitude should be copied"
    )
    (tmp_path / RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exact location"):
        load_retail_reality_customer_output_schema_gate(artifact_dir=tmp_path)
