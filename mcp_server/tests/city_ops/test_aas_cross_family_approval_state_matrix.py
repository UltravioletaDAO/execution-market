import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_cross_family_approval_state_matrix import (
    AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME,
    AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM,
    AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SCHEMA,
    MATRIX_BLOCKED_CLAIMS,
    MATRIX_FALSE_FLAGS,
    build_aas_cross_family_approval_state_matrix,
    load_aas_cross_family_approval_state_matrix,
    write_aas_cross_family_approval_state_matrix,
)
from mcp_server.city_ops.aas_single_boundary_delivery_publication_gate import (
    AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM,
    DELIVERY_PUBLICATION_VERDICT,
    build_aas_single_boundary_delivery_publication_gate,
)
from mcp_server.city_ops.document_handoff_approval_request_read_surface import (
    DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
    build_document_handoff_approval_request_read_surface,
)
from mcp_server.city_ops.incident_verification_approval_record_validator import (
    INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
    build_incident_verification_approval_record_validator,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_matrix() -> dict:
    with (ARTIFACT_DIR / AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )


def test_matrix_matches_persisted_artifact_and_loader():
    matrix = build_aas_cross_family_approval_state_matrix()

    assert matrix == read_matrix()
    assert load_aas_cross_family_approval_state_matrix() == matrix
    assert matrix["schema"] == AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SCHEMA
    assert matrix["scope"] == "internal_admin_cross_family_approval_state_matrix_only_no_customer_exposure"
    assert matrix["matrix_status"] == "read_only_no_exposure_matrix_all_delivery_publication_claims_blocked"
    assert AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM in matrix["safe_to_claim"]


def test_matrix_compares_three_family_approval_states_without_delivery_authorization():
    matrix = build_aas_cross_family_approval_state_matrix()
    rows = {row["family_id"]: row for row in matrix["approval_state_rows"]}

    assert list(rows) == [
        "compliance_desk_as_a_service",
        "document_handoff_logistics_as_a_service",
        "incident_verification_as_a_service",
    ]
    assert rows["compliance_desk_as_a_service"]["state"] == "approval_record_exists_but_delivery_path_absent"
    assert rows["compliance_desk_as_a_service"]["human_operator_approval_record_exists"] is True
    assert rows["compliance_desk_as_a_service"]["selected_boundary_approved"] is True
    assert rows["compliance_desk_as_a_service"]["delivery_publication_verdict"] == DELIVERY_PUBLICATION_VERDICT
    assert rows["document_handoff_logistics_as_a_service"]["state"] == "pending_approval_request_read_surface_no_approval_record"
    assert rows["document_handoff_logistics_as_a_service"]["human_operator_approval_record_exists"] is False
    assert rows["incident_verification_as_a_service"]["state"] == "validator_exists_for_future_record_no_approval_record"
    assert rows["incident_verification_as_a_service"]["validator_exists"] is True
    assert rows["incident_verification_as_a_service"]["human_operator_approval_record_exists"] is False
    for row in rows.values():
        assert row["authorized_delivery_path_authorized"] is False
        assert row["customer_delivery_authorized"] is False
        assert row["publication_authorized"] is False


def test_matrix_summary_counts_hold_customer_public_runtime_and_dispatch_claims():
    matrix = build_aas_cross_family_approval_state_matrix()
    summary = matrix["matrix_summary"]

    assert summary["family_count"] == 3
    assert summary["families_with_human_approval_record"] == 1
    for key in [
        "families_with_delivery_authorization",
        "families_publishable",
        "families_with_public_or_catalog_routes",
        "families_ready_for_dispatch",
        "families_with_reputation_attachment_ready",
        "families_with_live_acontext_runtime_parity",
        "families_allowed_to_release_exact_gps_or_raw_metadata",
    ]:
        assert summary[key] == 0
    for flag in MATRIX_FALSE_FLAGS:
        assert matrix[flag] is False


def test_claim_boundaries_keep_safe_and_blocked_adjacent():
    matrix = build_aas_cross_family_approval_state_matrix()
    key_order = list(matrix.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM in matrix["safe_to_claim"]
    assert DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM in matrix["safe_to_claim"]
    assert INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM in matrix["safe_to_claim"]
    assert not set(matrix["safe_to_claim"]) & set(matrix["do_not_claim_yet"])
    assert matrix["still_blocked_claims"] == matrix["do_not_claim_yet"]
    for claim in MATRIX_BLOCKED_CLAIMS:
        assert claim in matrix["do_not_claim_yet"]
        assert claim not in matrix["safe_to_claim"]
    assert "customer_delivery_approved" not in matrix["safe_to_claim"]
    assert "publication_approved" not in matrix["safe_to_claim"]
    assert "dispatch_ready" not in matrix["safe_to_claim"]


def test_source_digests_are_recorded_for_parity_review():
    matrix = build_aas_cross_family_approval_state_matrix()
    sources = matrix["source_artifacts"]

    assert sources["compliance_desk"]["file"] == "aas_single_boundary_delivery_publication_gate.json"
    assert sources["document_handoff"]["file"] == "document_handoff_approval_request_read_surface.json"
    assert sources["incident_verification"]["file"] == "incident_verification_approval_record_validator.json"
    for source in sources.values():
        assert len(source["digest_sha256"]) == 64
        assert source["safe_claim"] in matrix["safe_to_claim"]


def test_write_matrix_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_cross_family_approval_state_matrix(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME
    assert load_aas_cross_family_approval_state_matrix(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_compliance_delivery_promotion_fails_closed():
    compliance = build_aas_single_boundary_delivery_publication_gate()
    compliance = copy.deepcopy(compliance)
    compliance["authorized_delivery_path_authorized"] = True

    with pytest.raises(CityOpsContractError, match="compliance source delivery path promoted"):
        build_aas_cross_family_approval_state_matrix(compliance_delivery_gate=compliance)


def test_document_forbidden_safe_claim_fails_closed():
    document = build_document_handoff_approval_request_read_surface()
    document = copy.deepcopy(document)
    document["safe_to_claim"].append("customer_delivery_ready")

    with pytest.raises(CityOpsContractError, match="document source forbidden safe claims"):
        build_aas_cross_family_approval_state_matrix(document_request_surface=document)


def test_incident_validator_readiness_promotion_fails_closed():
    incident = build_incident_verification_approval_record_validator()
    incident = copy.deepcopy(incident)
    incident["readiness"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="incident source promoted readiness"):
        build_aas_cross_family_approval_state_matrix(incident_validator=incident)


def test_loader_fails_closed_on_row_publication_flip(tmp_path):
    seed_sources(tmp_path)
    matrix = build_aas_cross_family_approval_state_matrix(artifact_dir=tmp_path)
    matrix["approval_state_rows"][0]["publication_authorized"] = True
    (tmp_path / AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME).write_text(
        json.dumps(matrix), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="row authorized publication"):
        load_aas_cross_family_approval_state_matrix(artifact_dir=tmp_path)
