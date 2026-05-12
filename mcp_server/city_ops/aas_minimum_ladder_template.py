"""Minimum proof ladder template for adjacent Execution Market AAS packages.

This module turns the City-as-a-Service proof discipline into a reusable,
conservative template for adjacent AAS package families. It is deliberately an
internal planning artifact only: not customer copy, not a public catalog, not a
pilot launch, not dispatch, not live Acontext/runtime parity, not ERC-8004
reputation, not exact GPS/raw metadata exposure, and not worker-copyable doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError

AAS_MINIMUM_LADDER_TEMPLATE_SCHEMA = "city_ops.aas_minimum_ladder_template.v1"
AAS_MINIMUM_LADDER_TEMPLATE_FILENAME = "aas_minimum_ladder_template.json"
AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM = "aas_minimum_ladder_template_landed"

TEMPLATE_ID = "execution_market.aas.minimum_ladder_template.2026_05_12"
TEMPLATE_SCOPE = "internal_planning_adjacent_aas_package_template_only"

ARTIFACT_DIR = Path(__file__).resolve().parent / "fixtures" / "aas_package_ladder"

REQUIRED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

REQUIRED_FAMILY_ORDER = [
    "compliance_desk_as_a_service",
    "property_permit_desk_as_a_service",
    "incident_verification_as_a_service",
    "document_handoff_logistics_as_a_service",
    "procurement_admin_ops_as_a_service",
]

REQUIRED_BLOCKED_CLAIMS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "front_door_sku_ready",
    "pilot_authorized",
    "catalog_customer_ready",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "filing_success_ready",
    "broad_office_reuse_ready",
    "city_relationship_or_influence",
    "guaranteed_approval",
    "legal_sufficiency",
    "regulator_acceptance",
    "live_acontext_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "autonomous_dispatch_readiness",
    "dispatch_routing_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_municipal_doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "exact_gps_or_metadata_exposure",
    "raw_metadata_exposure_allowed",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "adjacent_aas_customer_ready",
    "aas_catalog_ready",
    "aas_public_route_ready",
    "aas_dispatch_ready",
    "aas_reputation_ready",
    "worker_doctrine_ready",
}

READINESS_FALSE_FLAGS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_allowed",
    "front_door_sku_ready",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
]

FAMILY_DEFINITIONS = {
    "compliance_desk_as_a_service": {
        "label": "Compliance Desk as a Service",
        "first_concierge_offer": "Visible Posting / Notice Compliance Snapshot",
        "caas_source_pattern": "posting_compliance_check",
        "required_evidence": [
            "wide_context_photo_or_permitted_visual_snapshot",
            "close_notice_or_required_element_photo_where_allowed",
            "timestamp_window",
            "visible_element_checklist",
            "source_type_observed_documented_or_heard",
            "obstruction_or_legibility_notes",
            "reviewed_limitations",
        ],
        "specific_blocked_claims": [
            "legal_compliance",
            "official_inspection",
            "continuous_monitoring",
        ],
    },
    "property_permit_desk_as_a_service": {
        "label": "Property / Permit Desk as a Service",
        "first_concierge_offer": "Single-Site Permit / Office Reality Check",
        "caas_source_pattern": "counter_reality_check + packet_submission_attempt",
        "required_evidence": [
            "target_or_site_identifier_without_private_location_leakage",
            "allowed_access_boundary",
            "office_window_or_portal_state",
            "form_version_or_routing_evidence",
            "accepted_rejected_redirected_blocked_or_inconclusive_status",
            "next_step_recommendation",
        ],
        "specific_blocked_claims": [
            "permit_approval",
            "appraisal_or_tenant_determination",
            "trespass_or_access_guarantee",
        ],
    },
    "incident_verification_as_a_service": {
        "label": "Incident Verification as a Service",
        "first_concierge_offer": "One-Location Incident State Snapshot",
        "caas_source_pattern": "site_audit + measurement + proof_observability",
        "required_evidence": [
            "incident_question",
            "place_time_window_without_exact_public_coordinates",
            "wide_context_photo_or_permitted_visual_snapshot",
            "close_evidence_photo_where_allowed",
            "severity_taxonomy",
            "uncertainty_note",
            "what_was_not_checked",
            "recommended_next_action",
        ],
        "specific_blocked_claims": [
            "emergency_response",
            "safety_certification",
            "repair_diagnosis_or_completion",
            "insurance_adjustment",
        ],
    },
    "document_handoff_logistics_as_a_service": {
        "label": "Document / Handoff Logistics as a Service",
        "first_concierge_offer": "Document Handoff Proof Run",
        "caas_source_pattern": "packet_submission_attempt",
        "required_evidence": [
            "chain_of_custody_events_inside_scoped_windows",
            "pickup_or_dropoff_timestamp",
            "recipient_or_source_type",
            "receipt_stamp_or_photo_where_available",
            "failed_handoff_reason",
            "queue_or_wait_boundary",
            "recommended_next_action",
        ],
        "specific_blocked_claims": [
            "legal_service",
            "notarial_act_without_separate_credential_scope",
            "guaranteed_acceptance",
            "identity_verification_beyond_scoped_evidence",
            "custody_guarantee_outside_documented_windows",
        ],
    },
    "procurement_admin_ops_as_a_service": {
        "label": "Procurement / Admin Ops as a Service",
        "first_concierge_offer": "Admin Counter / Vendor Reality Check",
        "caas_source_pattern": "counter_reality_check",
        "required_evidence": [
            "buyer_question",
            "target_office_or_vendor",
            "observed_open_or_closed_state",
            "posted_hours_or_counter_status_proof",
            "quote_receipt_or_photo_where_allowed",
            "source_type_split",
            "discrepancy_summary",
            "limitations",
            "next_step_recommendation",
        ],
        "specific_blocked_claims": [
            "procurement_authority",
            "vendor_contract_enforcement",
            "guaranteed_pricing_or_inventory_beyond_observation_window",
            "employee_performance_judgment",
        ],
    },
}


def build_aas_minimum_ladder_template(
    *, family_definitions: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Build the internal adjacent-AAS minimum ladder template."""

    families_source = family_definitions or FAMILY_DEFINITIONS
    _assert_family_definitions(families_source)

    family_rows = [_build_family_row(family_id, families_source[family_id]) for family_id in REQUIRED_FAMILY_ORDER]
    safe_to_claim = [AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM]
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *[
                claim
                for row in family_rows
                for claim in row["specific_blocked_claims"]
            ],
        ]
    )

    template = {
        "schema": AAS_MINIMUM_LADDER_TEMPLATE_SCHEMA,
        "template_id": TEMPLATE_ID,
        "scope": TEMPLATE_SCOPE,
        "source_concept_doc": "docs/planning/EXECUTION_MARKET_AAS_GAP_MAP_2026_05_12.md",
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "promotion_rule": list(REQUIRED_LADDER_STEPS),
        "family_order": list(REQUIRED_FAMILY_ORDER),
        "families": family_rows,
        "global_readiness": {
            "template_exists": True,
            "adjacent_family_count": len(family_rows),
            "customer_copy_ready": False,
            "customer_visible_catalog_ready": False,
            "public_service_catalog_ready": False,
            "controlled_concierge_pilot_ready": False,
            "customer_pilot_exposure_allowed": False,
            "front_door_sku_ready": False,
            "operator_publish_approval": False,
            "customer_delivery_approval": False,
            "publication_approved": False,
            "live_acontext_ready": False,
            "runtime_parity_proven": False,
            "autonomous_dispatch_ready": False,
            "reputation_ready": False,
            "worker_skill_dna_ready": False,
            "worker_copyable_doctrine_ready": False,
            "exact_gps_or_raw_metadata_exposure_allowed": False,
        },
        "operator_instruction": (
            "Use this as the required starting checklist for adjacent AAS packages. "
            "Do not turn any family into customer copy, catalog routes, dispatch, "
            "reputation, live memory, or worker doctrine until that family has its "
            "own reviewed artifacts and an explicit approval or hold decision."
        ),
        "next_smallest_proof": (
            "Pick one adjacent family, preferably Compliance Desk or Document/Handoff "
            "Logistics, and create only its fixture spec plus review-gate checklist with "
            "all customer/public/dispatch/reputation/privacy/worker-doctrine readiness false."
        ),
    }
    _assert_template_is_conservative(template)
    return template


def write_aas_minimum_ladder_template(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the adjacent-AAS minimum ladder template."""

    template = build_aas_minimum_ladder_template()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME
    path.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_minimum_ladder_template(*, artifact_dir: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the persisted adjacent-AAS minimum ladder template."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        template = json.load(fh)
    if not isinstance(template, dict):
        raise CityOpsContractError("AAS minimum ladder template must be a JSON object")
    _assert_template_is_conservative(template)
    return template


def _build_family_row(family_id: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_id": family_id,
        "label": definition["label"],
        "first_concierge_offer": definition["first_concierge_offer"],
        "caas_source_pattern": definition["caas_source_pattern"],
        "required_evidence": list(definition["required_evidence"]),
        "required_ladder_steps": list(REQUIRED_LADDER_STEPS),
        "minimum_artifacts_required_before_promotion": [
            "offer_card_fixture_spec",
            "reviewed_output_schema",
            "local_reviewed_fixture",
            "internal_package_record",
            "coverage_summary_or_read_only_operator_surface",
            "customer_output_schema_gate",
            "internal_sample_output",
            "approval_or_hold_decision",
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "safe_to_claim": ["adjacent_aas_family_template_row_created"],
        "specific_blocked_claims": list(definition["specific_blocked_claims"]),
        "blocked_claims": _dedupe([*REQUIRED_BLOCKED_CLAIMS, *definition["specific_blocked_claims"]]),
        "next_smallest_step": (
            "Create a fixture spec and review-gate checklist only; keep customer, public, "
            "dispatch, reputation, live-memory, GPS/raw-metadata, legal/regulator, and "
            "worker-doctrine readiness false."
        ),
    }


def _assert_family_definitions(families: dict[str, dict[str, Any]]) -> None:
    if set(families) != set(REQUIRED_FAMILY_ORDER):
        missing = sorted(set(REQUIRED_FAMILY_ORDER) - set(families))
        extra = sorted(set(families) - set(REQUIRED_FAMILY_ORDER))
        raise CityOpsContractError(
            f"AAS family definitions drifted; missing={missing}; extra={extra}"
        )
    for family_id, definition in families.items():
        for key in (
            "label",
            "first_concierge_offer",
            "caas_source_pattern",
            "required_evidence",
            "specific_blocked_claims",
        ):
            if key not in definition:
                raise CityOpsContractError(f"AAS family {family_id} missing {key}")
        if not definition["required_evidence"]:
            raise CityOpsContractError(f"AAS family {family_id} must require evidence")
        if not definition["specific_blocked_claims"]:
            raise CityOpsContractError(f"AAS family {family_id} must block claims")


def _assert_template_is_conservative(template: dict[str, Any]) -> None:
    if template.get("schema") != AAS_MINIMUM_LADDER_TEMPLATE_SCHEMA:
        raise CityOpsContractError("AAS minimum ladder template schema drift")
    if template.get("scope") != TEMPLATE_SCOPE:
        raise CityOpsContractError("AAS minimum ladder template scope drift")
    if template.get("promotion_rule") != REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("AAS minimum ladder promotion rule drift")
    if template.get("family_order") != REQUIRED_FAMILY_ORDER:
        raise CityOpsContractError("AAS minimum ladder family order drift")
    if set(template.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("AAS minimum ladder has forbidden safe claims")
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(template.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(f"AAS minimum ladder missing blocked claims: {sorted(missing_blocked)}")
    readiness = template.get("global_readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"AAS minimum ladder promoted readiness: {flag}")
    families = template.get("families")
    if not isinstance(families, list) or len(families) != len(REQUIRED_FAMILY_ORDER):
        raise CityOpsContractError("AAS minimum ladder must include all family rows")
    family_ids = [row.get("family_id") for row in families]
    if family_ids != REQUIRED_FAMILY_ORDER:
        raise CityOpsContractError("AAS minimum ladder family row order drift")
    for row in families:
        _assert_family_row_is_conservative(row)


def _assert_family_row_is_conservative(row: dict[str, Any]) -> None:
    family_id = row.get("family_id", "<unknown>")
    if row.get("required_ladder_steps") != REQUIRED_LADDER_STEPS:
        raise CityOpsContractError(f"AAS family {family_id} ladder steps drift")
    if set(row.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError(f"AAS family {family_id} has forbidden safe claims")
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(row.get("blocked_claims", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS family {family_id} missing blocked claims: {sorted(missing_blocked)}"
        )
    readiness = row.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"AAS family {family_id} promoted readiness: {flag}")
    if not row.get("required_evidence"):
        raise CityOpsContractError(f"AAS family {family_id} lost required evidence")
    if not row.get("specific_blocked_claims"):
        raise CityOpsContractError(f"AAS family {family_id} lost specific blocked claims")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
