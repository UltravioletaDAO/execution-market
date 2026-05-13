import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.document_handoff_customer_output_schema_gate import (
    ALLOWED_CUSTOMER_OUTPUT_FIELDS,
    DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME,
    DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA,
    FORBIDDEN_CUSTOMER_OUTPUT_FIELDS,
    GATE_ID,
    NEXT_REQUIRED_LADDER_STEPS,
    build_document_handoff_customer_output_schema_gate,
    load_document_handoff_customer_output_schema_gate,
    write_document_handoff_customer_output_schema_gate,
)
from mcp_server.city_ops.document_handoff_operator_read_surface import (
    DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME,
    DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_SAFE_CLAIM,
    build_document_handoff_operator_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_gate() -> dict:
    with (ARTIFACT_DIR / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_document_handoff_customer_output_schema_gate_matches_persisted_artifact():
    gate = build_document_handoff_customer_output_schema_gate()

    assert gate == read_gate()
    assert load_document_handoff_customer_output_schema_gate() == gate
    assert gate["schema"] == DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA
    assert gate["gate_id"] == GATE_ID
    assert gate["scope"] == "internal_admin_customer_output_schema_gate_only"
    assert gate["gate_status"] == "schema_gate_landed_not_customer_copy_not_public_not_approved"
    assert DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM in gate["safe_to_claim"]
    assert DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_SAFE_CLAIM in gate["safe_to_claim"]


def test_schema_gate_consumes_only_operator_read_surface_and_builder():
    gate = build_document_handoff_customer_output_schema_gate()
    contract = gate["source_contract"]

    assert gate["source_surface_file"] == DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME
    assert contract["consumes_only"] == [DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME]
    assert contract["source_builder"] == "build_document_handoff_operator_read_surface"
    assert contract["source_is_read_only_operator_surface"] is True
    assert contract["source_operator_cards_used_as_schema_inputs_only"] is True
    assert contract["source_payload_reinterpreted_as_customer_copy"] is False
    assert contract["reads_raw_review_fixture"] is False
    assert contract["reads_raw_transcripts"] is False
    assert contract["reads_raw_metadata"] is False
    assert contract["reads_private_operator_context"] is False


def test_schema_gate_defines_exact_allowed_and_forbidden_customer_output_fields():
    gate = build_document_handoff_customer_output_schema_gate()
    review = gate["schema_review"]

    assert review["allowed_customer_output_fields"] == ALLOWED_CUSTOMER_OUTPUT_FIELDS
    assert review["allowed_customer_output_fields"] == [
        "plain_language_status",
        "handoff_window_summary",
        "chain_of_custody_event_summary",
        "recipient_or_source_type_summary",
        "receipt_or_stamp_summary",
        "failed_handoff_reason",
        "queue_or_wait_boundary",
        "what_was_checked",
        "what_was_not_checked",
        "limitations_and_non_guarantees",
        "recommended_next_action",
        "operator_review_notice",
        "privacy_redaction_notice",
    ]
    assert review["forbidden_customer_output_fields"] == FORBIDDEN_CUSTOMER_OUTPUT_FIELDS
    for field in [
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "legal_service_claim",
        "notarial_act_claim",
        "identity_verification_claim",
        "guaranteed_acceptance_claim",
        "filing_success_claim",
        "custody_guarantee_claim",
        "dispatch_instruction_or_assignment",
        "erc8004_reputation_receipt",
        "worker_copyable_handoff_doctrine",
        "customer_public_launch_readiness_claim",
        "catalog_or_pilot_readiness_claim",
    ]:
        assert field in review["forbidden_customer_output_fields"]
    assert not set(review["allowed_customer_output_fields"]) & set(
        review["forbidden_customer_output_fields"]
    )


def test_schema_gate_keeps_all_readiness_and_approval_flags_false():
    gate = build_document_handoff_customer_output_schema_gate()

    assert all(value is False for value in gate["readiness"].values())
    assert all(value is False for value in gate["schema_gate_readiness"].values())
    for flag in [
        "customer_copy_created",
        "customer_copy_ready",
        "public_route_registered",
        "dispatch_enabled",
        "emits_reputation_receipts",
        "legal_service_ready",
        "notarial_act_ready",
        "identity_verification_ready",
        "guaranteed_acceptance_ready",
        "filing_success_ready",
        "custody_guarantee_ready",
        "customer_public_launch_ready",
        "catalog_or_pilot_readiness_ready",
    ]:
        assert gate["schema_gate_readiness"][flag] is False


def test_schema_gate_blocks_external_product_and_outcome_claims():
    gate = build_document_handoff_customer_output_schema_gate()
    blocked = set(gate["do_not_claim_yet"])

    for claim in [
        "schema_gate_customer_copy_ready",
        "schema_gate_public_route_ready",
        "schema_gate_dispatch_ready",
        "schema_gate_reputation_ready",
        "schema_gate_exact_gps_or_raw_metadata_release_ready",
        "schema_gate_legal_service_ready",
        "schema_gate_notarial_act_ready",
        "schema_gate_identity_verification_ready",
        "schema_gate_guaranteed_acceptance_ready",
        "schema_gate_filing_success_ready",
        "schema_gate_custody_guarantee_ready",
        "document_handoff_customer_public_launch_ready",
        "document_handoff_catalog_or_pilot_readiness_ready",
    ]:
        assert claim in blocked
        assert claim not in gate["safe_to_claim"]
    assert gate["safe_to_claim"][-1] == DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM


def test_schema_gate_advances_ladder_without_promotion():
    gate = build_document_handoff_customer_output_schema_gate()

    assert gate["ladder_boundary"]["covered_steps"][-1] == "customer_output_schema_gate"
    assert gate["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert gate["ladder_boundary"]["promotion_allowed"] is False
    assert gate["next_smallest_proof"].startswith("Draft one internal/admin sample")


def test_write_document_handoff_customer_output_schema_gate_persists_valid_artifact(tmp_path):
    source = build_document_handoff_operator_read_surface()
    (tmp_path / DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )

    path = write_document_handoff_customer_output_schema_gate(artifact_dir=tmp_path)

    assert path == tmp_path / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME
    assert load_document_handoff_customer_output_schema_gate(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_schema_gate_fails_closed_when_source_surface_promotes_public_access():
    surface = copy.deepcopy(build_document_handoff_operator_read_surface())
    surface["access_policy"]["public_route_registered"] = True

    with pytest.raises(CityOpsContractError, match="source access overclaims"):
        build_document_handoff_customer_output_schema_gate(operator_surface=surface)


def test_loader_fails_closed_on_customer_copy_created(tmp_path):
    source = build_document_handoff_operator_read_surface()
    gate = build_document_handoff_customer_output_schema_gate(operator_surface=source)
    gate["schema_gate_readiness"]["customer_copy_created"] = True
    (tmp_path / DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted schema readiness"):
        load_document_handoff_customer_output_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    source = build_document_handoff_operator_read_surface()
    gate = build_document_handoff_customer_output_schema_gate(operator_surface=source)
    gate["safe_to_claim"].append("schema_gate_dispatch_ready")
    (tmp_path / DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_document_handoff_customer_output_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_allowed_forbidden_field_overlap(tmp_path):
    source = build_document_handoff_operator_read_surface()
    gate = build_document_handoff_customer_output_schema_gate(operator_surface=source)
    gate["schema_review"]["forbidden_customer_output_fields"] = list(
        gate["schema_review"]["forbidden_customer_output_fields"]
    )
    gate["schema_review"]["forbidden_customer_output_fields"][0] = "plain_language_status"
    (tmp_path / DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden field drift"):
        load_document_handoff_customer_output_schema_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_exact_location_language(tmp_path):
    source = build_document_handoff_operator_read_surface()
    gate = build_document_handoff_customer_output_schema_gate(operator_surface=source)
    gate["schema_review"]["required_boundary_notes"].append(
        "latitude and longitude should be copied"
    )
    (tmp_path / DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(source), encoding="utf-8"
    )
    (tmp_path / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exact location"):
        load_document_handoff_customer_output_schema_gate(artifact_dir=tmp_path)
