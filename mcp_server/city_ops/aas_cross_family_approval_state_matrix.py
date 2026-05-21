"""Cross-family AAS approval-state matrix.

This module implements the no-customer-exposure fork from the AAS handoffs: a
single internal/admin matrix comparing Compliance Desk, Document / Handoff, and
Incident Verification approval posture. It deliberately does not create human
approval, delivery authorization, publication, public/catalog routes, pricing,
queue launch, dispatch, reputation, live Acontext/runtime parity, exact GPS/raw
metadata exposure, domain-authority claims, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_single_boundary_delivery_publication_gate import (
    AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME,
    AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SCHEMA,
    DELIVERY_PUBLICATION_VERDICT,
    load_aas_single_boundary_delivery_publication_gate,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError
from .document_handoff_approval_request_read_surface import (
    DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
    DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SCHEMA,
    SURFACE_FALSE_FLAGS as DOCUMENT_SURFACE_FALSE_FLAGS,
    load_document_handoff_approval_request_read_surface,
)
from .incident_verification_approval_record_validator import (
    INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SCHEMA,
    VALIDATOR_READINESS_FALSE_FLAGS as INCIDENT_VALIDATOR_FALSE_FLAGS,
    load_incident_verification_approval_record_validator,
)

AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SCHEMA = (
    "city_ops.aas_cross_family_approval_state_matrix.v1"
)
AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME = (
    "aas_cross_family_approval_state_matrix.json"
)
AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM = (
    "admin_aas_cross_family_approval_state_matrix_landed"
)

MATRIX_ID = "execution_market.aas.cross_family_approval_state_matrix.2026_05_21"
SCOPE = "internal_admin_cross_family_approval_state_matrix_only_no_customer_exposure"
MATRIX_STATUS = "read_only_no_exposure_matrix_all_delivery_publication_claims_blocked"

APPROVAL_STATE_ROWS = [
    "compliance_desk_as_a_service",
    "document_handoff_logistics_as_a_service",
    "incident_verification_as_a_service",
]

MATRIX_FALSE_FLAGS = {
    "matrix_creates_human_approval": False,
    "matrix_approves_any_selected_boundary": False,
    "matrix_authorizes_customer_copy": False,
    "matrix_authorizes_customer_delivery": False,
    "matrix_authorizes_publication": False,
    "matrix_authorizes_public_route_or_catalog": False,
    "matrix_authorizes_controlled_pilot": False,
    "matrix_authorizes_public_price_or_customer_quote": False,
    "matrix_authorizes_operator_queue_launch": False,
    "matrix_authorizes_dispatch": False,
    "matrix_authorizes_reputation": False,
    "matrix_proves_live_acontext_or_runtime_parity": False,
    "matrix_reverifies_payment_or_production_health": False,
    "matrix_allows_exact_gps_or_raw_metadata_release": False,
    "matrix_grants_domain_legal_notarial_custody_or_incident_authority": False,
    "matrix_creates_worker_skill_dna_or_copyable_doctrine": False,
}

MATRIX_BLOCKED_CLAIMS = [
    "cross_family_matrix_creates_human_approval",
    "cross_family_matrix_approves_selected_boundary",
    "cross_family_matrix_authorizes_customer_copy",
    "cross_family_matrix_authorizes_customer_delivery",
    "cross_family_matrix_authorizes_publication",
    "cross_family_matrix_authorizes_public_route_or_catalog",
    "cross_family_matrix_authorizes_controlled_pilot_or_front_door_sku",
    "cross_family_matrix_authorizes_public_price_or_customer_quote",
    "cross_family_matrix_authorizes_operator_queue_launch",
    "cross_family_matrix_authorizes_dispatch",
    "cross_family_matrix_authorizes_erc8004_reputation",
    "cross_family_matrix_authorizes_worker_skill_dna",
    "cross_family_matrix_proves_live_acontext_or_runtime_parity",
    "cross_family_matrix_reverifies_payment_or_production_health",
    "cross_family_matrix_allows_exact_gps_or_raw_metadata_release",
    "cross_family_matrix_grants_domain_legal_regulator_notarial_custody_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
    "cross_family_matrix_creates_worker_copyable_aas_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(MATRIX_BLOCKED_CLAIMS) | {
    "human_operator_approval_created",
    "selected_boundary_approved",
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "public_price_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "domain_authority_ready",
    "legal_or_regulator_authority_ready",
    "worker_copyable_doctrine_ready",
}


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _load_sources(artifact_dir: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        load_aas_single_boundary_delivery_publication_gate(artifact_dir=artifact_dir),
        load_document_handoff_approval_request_read_surface(artifact_dir=artifact_dir),
        load_incident_verification_approval_record_validator(artifact_dir=artifact_dir),
    )


def build_aas_cross_family_approval_state_matrix(
    *,
    artifact_dir: Path | None = None,
    compliance_delivery_gate: dict[str, Any] | None = None,
    document_request_surface: dict[str, Any] | None = None,
    incident_validator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative read-only approval-state matrix across AAS families."""

    if compliance_delivery_gate is None or document_request_surface is None or incident_validator is None:
        loaded_compliance, loaded_document, loaded_incident = _load_sources(artifact_dir)
        compliance_delivery_gate = compliance_delivery_gate or loaded_compliance
        document_request_surface = document_request_surface or loaded_document
        incident_validator = incident_validator or loaded_incident

    _assert_compliance_gate_is_held(compliance_delivery_gate)
    _assert_document_surface_is_pending(document_request_surface)
    _assert_incident_validator_is_contract_only(incident_validator)

    safe_to_claim = _dedupe(
        [
            AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM,
            DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
            INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
            AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *MATRIX_BLOCKED_CLAIMS,
            *compliance_delivery_gate.get("do_not_claim_yet", []),
            *document_request_surface.get("do_not_claim_yet", []),
            *incident_validator.get("do_not_claim_yet", []),
        ]
    )

    matrix: dict[str, Any] = {
        "schema": AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SCHEMA,
        "matrix_id": MATRIX_ID,
        "scope": SCOPE,
        "matrix_status": MATRIX_STATUS,
        "source_artifacts": {
            "compliance_desk": {
                "file": AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME,
                "schema": compliance_delivery_gate["schema"],
                "id": compliance_delivery_gate["gate_id"],
                "digest_sha256": _canonical_digest(compliance_delivery_gate),
                "safe_claim": AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM,
            },
            "document_handoff": {
                "file": DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
                "schema": document_request_surface["schema"],
                "id": document_request_surface["surface_id"],
                "digest_sha256": _canonical_digest(document_request_surface),
                "safe_claim": DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
            },
            "incident_verification": {
                "file": INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME,
                "schema": incident_validator["schema"],
                "id": incident_validator["validator_id"],
                "digest_sha256": _canonical_digest(incident_validator),
                "safe_claim": INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
            },
        },
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "approval_state_rows": [
            {
                "family_id": "compliance_desk_as_a_service",
                "family_label": "Compliance Desk as a Service",
                "selected_boundary_label": "Visible posting / notice compliance snapshot",
                "state": "approval_record_exists_but_delivery_path_absent",
                "approval_request_exists": True,
                "approval_request_read_surface_exists": True,
                "schema_gate_exists": True,
                "validator_exists": True,
                "human_operator_approval_record_exists": True,
                "selected_boundary_approved": True,
                "delivery_publication_gate_exists": True,
                "delivery_publication_verdict": compliance_delivery_gate["delivery_publication_verdict"],
                "authorized_delivery_path": compliance_delivery_gate["authorized_delivery_path"],
                "authorized_delivery_path_authorized": False,
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "next_smallest_proof": "separate explicit human operator decision for a named delivery path, or keep held",
            },
            {
                "family_id": "document_handoff_logistics_as_a_service",
                "family_label": "Document / Handoff Logistics as a Service",
                "selected_boundary_label": "Document handoff proof run",
                "state": "pending_approval_request_read_surface_no_approval_record",
                "approval_request_exists": True,
                "approval_request_read_surface_exists": True,
                "schema_gate_exists": False,
                "validator_exists": False,
                "human_operator_approval_record_exists": False,
                "selected_boundary_approved": False,
                "delivery_publication_gate_exists": False,
                "delivery_publication_verdict": "not_applicable_no_approval_record",
                "authorized_delivery_path": "none_until_separate_human_operator_approval_record",
                "authorized_delivery_path_authorized": False,
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "next_smallest_proof": "real human approval record only if reviewed; otherwise keep held",
            },
            {
                "family_id": "incident_verification_as_a_service",
                "family_label": "Incident Verification as a Service",
                "selected_boundary_label": "One-location incident state snapshot",
                "state": "validator_exists_for_future_record_no_approval_record",
                "approval_request_exists": True,
                "approval_request_read_surface_exists": True,
                "schema_gate_exists": True,
                "validator_exists": True,
                "human_operator_approval_record_exists": False,
                "selected_boundary_approved": False,
                "delivery_publication_gate_exists": False,
                "delivery_publication_verdict": "not_applicable_no_approval_record",
                "authorized_delivery_path": "still_none_unless_a_separate_delivery_approval_gate_exists",
                "authorized_delivery_path_authorized": False,
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "next_smallest_proof": "real human approval record through validator only if reviewed; delivery still separate",
            },
        ],
        "matrix_summary": {
            "family_count": 3,
            "families_with_human_approval_record": 1,
            "families_with_delivery_authorization": 0,
            "families_publishable": 0,
            "families_with_public_or_catalog_routes": 0,
            "families_ready_for_dispatch": 0,
            "families_with_reputation_attachment_ready": 0,
            "families_with_live_acontext_runtime_parity": 0,
            "families_allowed_to_release_exact_gps_or_raw_metadata": 0,
        },
        **MATRIX_FALSE_FLAGS,
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this matrix only as an internal/admin approval-state review surface. "
            "Compliance has an approved text boundary but no delivery path; Document / "
            "Handoff and Incident Verification do not have approval records. Do not publish, "
            "route, price, launch queues, dispatch, attach reputation, claim runtime parity, "
            "release exact GPS/raw metadata, or turn this into worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Choose one family and either record a separate human operator approval artifact "
            "or an explicit named delivery-path decision. If no customer exposure is desired, "
            "keep all rows held and continue internal packaging/pricing/operator workflow review."
        ),
    }
    _assert_matrix_is_conservative(
        matrix,
        compliance_delivery_gate=compliance_delivery_gate,
        document_request_surface=document_request_surface,
        incident_validator=incident_validator,
    )
    return matrix


def write_aas_cross_family_approval_state_matrix(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    matrix = build_aas_cross_family_approval_state_matrix(artifact_dir=target_dir)
    path = target_dir / AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME
    path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_cross_family_approval_state_matrix(artifact_dir: Path | None = None) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        matrix = json.load(fh)
    if not isinstance(matrix, dict):
        raise CityOpsContractError("AAS cross-family approval-state matrix must be a JSON object")
    compliance_gate, document_surface, incident_validator = _load_sources(source_dir)
    _assert_matrix_is_conservative(
        matrix,
        compliance_delivery_gate=compliance_gate,
        document_request_surface=document_surface,
        incident_validator=incident_validator,
    )
    return matrix


def _assert_compliance_gate_is_held(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SCHEMA:
        raise CityOpsContractError("cross-family matrix compliance source schema drift")
    if AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("cross-family matrix compliance source safe claim missing")
    if gate.get("delivery_publication_verdict") != DELIVERY_PUBLICATION_VERDICT:
        raise CityOpsContractError("cross-family matrix compliance source verdict drift")
    if gate.get("authorized_delivery_path_authorized") is not False:
        raise CityOpsContractError("cross-family matrix compliance source delivery path promoted")
    for flag in [
        "customer_delivery_approval",
        "customer_delivery_approved",
        "publication_approved",
        "public_route_ready",
        "catalog_route_ready",
        "dispatch_enabled",
        "erc8004_reputation_ready",
        "live_acontext_ready",
        "runtime_parity_proven",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "worker_copyable_doctrine_ready",
    ]:
        if gate.get(flag) is not False:
            raise CityOpsContractError(f"cross-family matrix compliance source promoted {flag}")


def _assert_document_surface_is_pending(surface: dict[str, Any]) -> None:
    if surface.get("schema") != DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("cross-family matrix document source schema drift")
    if DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM not in surface.get("safe_to_claim", []):
        raise CityOpsContractError("cross-family matrix document source safe claim missing")
    forbidden_safe = set(surface.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(f"cross-family matrix document source forbidden safe claims: {sorted(forbidden_safe)}")
    for flag in DOCUMENT_SURFACE_FALSE_FLAGS:
        if surface.get(flag) is not False:
            raise CityOpsContractError(f"cross-family matrix document source promoted {flag}")


def _assert_incident_validator_is_contract_only(validator: dict[str, Any]) -> None:
    if validator.get("schema") != INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SCHEMA:
        raise CityOpsContractError("cross-family matrix incident source schema drift")
    if INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM not in validator.get("safe_to_claim", []):
        raise CityOpsContractError("cross-family matrix incident source safe claim missing")
    forbidden_safe = set(validator.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(f"cross-family matrix incident source forbidden safe claims: {sorted(forbidden_safe)}")
    readiness = validator.get("readiness", {})
    for flag in INCIDENT_VALIDATOR_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"cross-family matrix incident source promoted readiness {flag}")


def _assert_matrix_is_conservative(
    matrix: dict[str, Any],
    *,
    compliance_delivery_gate: dict[str, Any],
    document_request_surface: dict[str, Any],
    incident_validator: dict[str, Any],
) -> None:
    _assert_compliance_gate_is_held(compliance_delivery_gate)
    _assert_document_surface_is_pending(document_request_surface)
    _assert_incident_validator_is_contract_only(incident_validator)
    if matrix.get("schema") != AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SCHEMA:
        raise CityOpsContractError("cross-family matrix schema drift")
    if matrix.get("matrix_id") != MATRIX_ID:
        raise CityOpsContractError("cross-family matrix id drift")
    if matrix.get("scope") != SCOPE:
        raise CityOpsContractError("cross-family matrix scope drift")
    if matrix.get("matrix_status") != MATRIX_STATUS:
        raise CityOpsContractError("cross-family matrix status drift")
    if AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM not in matrix.get("safe_to_claim", []):
        raise CityOpsContractError("cross-family matrix safe claim missing")
    forbidden_safe = set(matrix.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(f"cross-family matrix forbidden safe claims: {sorted(forbidden_safe)}")
    if set(matrix.get("safe_to_claim", [])) & set(matrix.get("do_not_claim_yet", [])):
        raise CityOpsContractError("cross-family matrix safe/blocked overlap")
    missing_blocked = set(MATRIX_BLOCKED_CLAIMS) - set(matrix.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(f"cross-family matrix missing blocked claims: {sorted(missing_blocked)}")
    if matrix.get("still_blocked_claims") != matrix.get("do_not_claim_yet"):
        raise CityOpsContractError("cross-family matrix blocked claims drift")
    source_artifacts = matrix.get("source_artifacts", {})
    if source_artifacts.get("compliance_desk", {}).get("digest_sha256") != _canonical_digest(compliance_delivery_gate):
        raise CityOpsContractError("cross-family matrix compliance source digest drift")
    if source_artifacts.get("document_handoff", {}).get("digest_sha256") != _canonical_digest(document_request_surface):
        raise CityOpsContractError("cross-family matrix document source digest drift")
    if source_artifacts.get("incident_verification", {}).get("digest_sha256") != _canonical_digest(incident_validator):
        raise CityOpsContractError("cross-family matrix incident source digest drift")
    rows = matrix.get("approval_state_rows", [])
    if [row.get("family_id") for row in rows] != APPROVAL_STATE_ROWS:
        raise CityOpsContractError("cross-family matrix row order drift")
    summary = matrix.get("matrix_summary", {})
    if summary.get("family_count") != 3:
        raise CityOpsContractError("cross-family matrix family count drift")
    if summary.get("families_with_human_approval_record") != 1:
        raise CityOpsContractError("cross-family matrix human approval count drift")
    for count_key in [
        "families_with_delivery_authorization",
        "families_publishable",
        "families_with_public_or_catalog_routes",
        "families_ready_for_dispatch",
        "families_with_reputation_attachment_ready",
        "families_with_live_acontext_runtime_parity",
        "families_allowed_to_release_exact_gps_or_raw_metadata",
    ]:
        if summary.get(count_key) != 0:
            raise CityOpsContractError(f"cross-family matrix promoted summary {count_key}")
    for row in rows:
        if row.get("authorized_delivery_path_authorized") is not False:
            raise CityOpsContractError("cross-family matrix row authorized delivery path")
        if row.get("customer_delivery_authorized") is not False:
            raise CityOpsContractError("cross-family matrix row authorized customer delivery")
        if row.get("publication_authorized") is not False:
            raise CityOpsContractError("cross-family matrix row authorized publication")
    for flag in MATRIX_FALSE_FLAGS:
        if matrix.get(flag) is not False:
            raise CityOpsContractError(f"cross-family matrix promoted false flag {flag}")
