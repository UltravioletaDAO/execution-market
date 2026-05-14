"""Incident Verification adjacent-AAS fixture spec and review gate.

This module instantiates the Incident Verification as a Service adjacent AAS
package from the minimum ladder. It deliberately stops at an internal fixture
spec and review-gate checklist. It does not create customer copy, publish a
catalog, authorize a pilot, prove live Acontext/runtime parity, dispatch work,
attach ERC-8004 reputation, expose exact GPS/raw metadata, create emergency or
safety certification claims, diagnose or complete repairs, adjust insurance,
claim SLA uptime, create official incident reports, or create worker-copyable
incident doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    READINESS_FALSE_FLAGS,
    REQUIRED_BLOCKED_CLAIMS as TEMPLATE_BLOCKED_CLAIMS,
    REQUIRED_LADDER_STEPS,
    load_aas_minimum_ladder_template,
)
from .contracts import CityOpsContractError

INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SCHEMA = (
    "city_ops.incident_verification_fixture_review_gate.v1"
)
INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_FILENAME = (
    "incident_verification_fixture_review_gate.json"
)
INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM = (
    "incident_verification_fixture_review_gate_landed"
)

PACKAGE_FAMILY_ID = "incident_verification_as_a_service"
OFFER_ID = "one_location_incident_state_snapshot"
SCOPE = "internal_admin_incident_verification_fixture_spec_and_review_gate_only"
ARTIFACT_DIR = Path(__file__).resolve().parent / "fixtures" / "aas_package_ladder"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

SOURCE_TEMPLATE_REQUIRED_EVIDENCE_FIELDS = [
    "incident_question",
    "place_time_window_without_exact_public_coordinates",
    "wide_context_photo_or_permitted_visual_snapshot",
    "close_evidence_photo_where_allowed",
    "severity_taxonomy",
    "uncertainty_note",
    "what_was_not_checked",
    "recommended_next_action",
]

REQUIRED_EVIDENCE_FIELDS = [
    *SOURCE_TEMPLATE_REQUIRED_EVIDENCE_FIELDS,
    "follow_on_task_trigger_if_another_visit_or_specialist_needed",
]

REQUIRED_OUTPUT_FIELDS = [
    "task_id_or_local_case_reference",
    "offer_type",
    "plain_language_status",
    "incident_question",
    "place_time_window_summary",
    "wide_context_evidence_summary",
    "close_evidence_summary",
    "severity_taxonomy",
    "uncertainty_note",
    "what_was_checked",
    "what_was_not_checked",
    "limitations_and_non_guarantees",
    "recommended_next_action",
    "follow_on_task_trigger",
    "operator_review_notice",
]

REVIEW_GATE_CHECKS = [
    "source_template_family_row_matches_incident_verification",
    "evidence_contract_requires_incident_question_and_place_time_window",
    "wide_context_and_close_evidence_photos_required_where_allowed",
    "severity_taxonomy_is_observational_not_safety_certification",
    "uncertainty_and_what_was_not_checked_sections_required",
    "follow_on_trigger_is_next_step_only_not_live_dispatch",
    "privacy_redaction_required_before_any_customer_language",
    "exact_gps_and_raw_metadata_blocked",
    "emergency_safety_repair_insurance_sla_and_official_report_claims_blocked",
    "operator_review_required_before_fixture_acceptance",
    "publication_customer_delivery_dispatch_reputation_and_worker_doctrine_blocked",
]

INCIDENT_VERIFICATION_SPECIFIC_BLOCKED_CLAIMS = [
    "emergency_response",
    "safety_certification",
    "repair_diagnosis",
    "repair_completion",
    "repair_diagnosis_or_completion",
    "insurance_adjustment",
    "sla_uptime",
    "official_incident_report",
    "live_dispatch",
    "erc8004_reputation_receipt",
    "worker_copyable_incident_doctrine",
]

REQUIRED_BLOCKED_CLAIMS = [
    *TEMPLATE_BLOCKED_CLAIMS,
    *INCIDENT_VERIFICATION_SPECIFIC_BLOCKED_CLAIMS,
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "incident_verification_customer_ready",
    "incident_verification_catalog_ready",
    "incident_verification_dispatch_ready",
    "incident_verification_reputation_ready",
    "incident_verification_worker_doctrine_ready",
    "incident_verification_official_report_ready",
    "incident_verification_safety_ready",
    "incident_verification_repair_ready",
}


def build_incident_verification_fixture_review_gate(
    *, template: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the internal fixture spec and review-gate checklist.

    The returned artifact proves only that the Incident Verification adjacent-AAS
    fixture boundary exists. It does not prove reviewed fixtures, customer
    output, approval, publication, dispatch, reputation, safety/legal/repair
    readiness, official reporting, or worker doctrine.
    """

    source_template = template or load_aas_minimum_ladder_template()
    family_row = _extract_incident_verification_family_row(source_template)

    gate = {
        "schema": INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SCHEMA,
        "gate_id": "execution_market.aas.incident_verification.fixture_review_gate.2026_05_13",
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "source_template_id": source_template["template_id"],
        "source_template_schema": source_template["schema"],
        "source_template_safe_claims_inherited": [
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM
        ],
        "safe_to_claim": [
            INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "do_not_claim_yet": _dedupe(
            [
                *REQUIRED_BLOCKED_CLAIMS,
                *source_template.get("do_not_claim_yet", []),
                *family_row.get("blocked_claims", []),
                *family_row.get("specific_blocked_claims", []),
            ]
        ),
        "ladder_boundary": {
            "required_full_ladder": list(REQUIRED_LADDER_STEPS),
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "fixture_spec": {
            "offer_id": OFFER_ID,
            "offer_label": "One-Location Incident State Snapshot",
            "family_label": family_row["label"],
            "caas_source_pattern": family_row["caas_source_pattern"],
            "source_caas_offer": "site_audit + measurement + proof_observability",
            "fixture_status": "spec_only_no_reviewed_fixture_yet",
            "operator_review_required": True,
            "customer_copy_changed": False,
            "phase_1_sellable_claim_allowed": False,
            "automation_claim_allowed": False,
            "emergency_or_safety_claim_allowed": False,
            "repair_or_insurance_claim_allowed": False,
            "sla_or_official_report_claim_allowed": False,
            "live_dispatch_allowed": False,
            "required_evidence_fields": list(REQUIRED_EVIDENCE_FIELDS),
            "reviewed_output_schema_draft": {
                "status": "draft_internal_only_not_customer_output",
                "required_fields": list(REQUIRED_OUTPUT_FIELDS),
                "forbidden_fields": [
                    "exact_gps_coordinates",
                    "raw_metadata_blob",
                    "precise_address_or_private_location",
                    "raw_transcript_as_authority",
                    "private_operator_context",
                    "emergency_response_instruction",
                    "safety_certification_claim",
                    "repair_diagnosis_claim",
                    "repair_completion_claim",
                    "insurance_adjustment_claim",
                    "sla_uptime_claim",
                    "official_incident_report_claim",
                    "dispatch_instruction_or_assignment",
                    "erc8004_reputation_receipt",
                    "worker_copyable_incident_doctrine",
                ],
            },
            "fixture_acceptance_gate": {
                "requires_local_reviewed_fixture": True,
                "requires_privacy_redaction_review": True,
                "requires_non_guarantee_language_review": True,
                "requires_operator_review_record": True,
                "requires_follow_on_trigger_review": True,
                "preserves_safe_and_blocked_claims": True,
                "allows_customer_delivery": False,
                "allows_publication": False,
                "allows_live_dispatch": False,
                "allows_reputation_receipt": False,
                "allows_exact_gps_or_raw_metadata_release": False,
            },
        },
        "review_gate_checklist": [
            {
                "check_id": check,
                "required": True,
                "status": "pending_future_review",
                "blocks_promotion_until_passed": True,
            }
            for check in REVIEW_GATE_CHECKS
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "operator_instruction": (
            "Use this only as the Incident Verification fixture boundary. The next "
            "valid step is a local reviewed fixture plus reviewed-output schema, not "
            "customer copy, catalog routing, live dispatch, reputation, live memory, "
            "exact GPS/raw metadata release, emergency/safety/repair/insurance/SLA/"
            "official-report claims, or worker-copyable incident doctrine."
        ),
        "next_smallest_proof": (
            "Create one local reviewed Incident Verification fixture for a one-location "
            "incident state snapshot that fills this evidence contract while keeping all "
            "promotion and customer/public readiness flags false."
        ),
    }
    _assert_gate_is_conservative(gate)
    return gate


def write_incident_verification_fixture_review_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Incident Verification fixture review gate."""

    gate = build_incident_verification_fixture_review_gate()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_incident_verification_fixture_review_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Incident Verification fixture review gate."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    if not isinstance(gate, dict):
        raise CityOpsContractError("Incident Verification fixture review gate must be a JSON object")
    _assert_gate_is_conservative(gate)
    return gate


def _extract_incident_verification_family_row(template: dict[str, Any]) -> dict[str, Any]:
    if template.get("schema") != "city_ops.aas_minimum_ladder_template.v1":
        raise CityOpsContractError("Incident Verification gate source template schema drift")
    if AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM not in template.get("safe_to_claim", []):
        raise CityOpsContractError("Incident Verification gate source template safe claim missing")
    rows = template.get("families")
    if not isinstance(rows, list):
        raise CityOpsContractError("Incident Verification gate source template missing family rows")
    matching = [row for row in rows if row.get("family_id") == PACKAGE_FAMILY_ID]
    if len(matching) != 1:
        raise CityOpsContractError("Incident Verification family row missing from source template")
    row = matching[0]
    expected_evidence = set(SOURCE_TEMPLATE_REQUIRED_EVIDENCE_FIELDS)
    if not expected_evidence.issubset(set(row.get("required_evidence", []))):
        raise CityOpsContractError("Incident Verification family row lost required evidence")
    if row.get("caas_source_pattern") != "site_audit + measurement + proof_observability":
        raise CityOpsContractError("Incident Verification family row source pattern drift")
    return row


def _assert_gate_is_conservative(gate: dict[str, Any]) -> None:
    if gate.get("schema") != INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("Incident Verification fixture review gate schema drift")
    if gate.get("scope") != SCOPE:
        raise CityOpsContractError("Incident Verification fixture review gate scope drift")
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Incident Verification fixture review gate family drift")
    if set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Incident Verification fixture review gate has forbidden safe claims")

    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(gate.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"Incident Verification fixture review gate missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = gate.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification fixture review gate covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification fixture review gate next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification fixture review gate promoted readiness")

    readiness = gate.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Incident Verification fixture review gate promoted readiness: {flag}"
            )

    spec = gate.get("fixture_spec")
    if not isinstance(spec, dict):
        raise CityOpsContractError("Incident Verification fixture spec must be an object")
    if spec.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Incident Verification fixture spec offer drift")
    if spec.get("operator_review_required") is not True:
        raise CityOpsContractError("Incident Verification fixture spec must require operator review")
    for flag in (
        "customer_copy_changed",
        "phase_1_sellable_claim_allowed",
        "automation_claim_allowed",
        "emergency_or_safety_claim_allowed",
        "repair_or_insurance_claim_allowed",
        "sla_or_official_report_claim_allowed",
        "live_dispatch_allowed",
    ):
        if spec.get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification fixture spec promoted {flag}")
    if not set(REQUIRED_EVIDENCE_FIELDS).issubset(set(spec.get("required_evidence_fields", []))):
        raise CityOpsContractError("Incident Verification fixture spec lost required evidence")

    schema = spec.get("reviewed_output_schema_draft", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(schema.get("required_fields", []))):
        raise CityOpsContractError("Incident Verification fixture spec lost output fields")
    forbidden_fields = set(schema.get("forbidden_fields", []))
    for forbidden in [
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "emergency_response_instruction",
        "safety_certification_claim",
        "repair_diagnosis_claim",
        "repair_completion_claim",
        "insurance_adjustment_claim",
        "sla_uptime_claim",
        "official_incident_report_claim",
        "dispatch_instruction_or_assignment",
        "erc8004_reputation_receipt",
        "worker_copyable_incident_doctrine",
    ]:
        if forbidden not in forbidden_fields:
            raise CityOpsContractError("Incident Verification fixture spec lost forbidden fields")

    acceptance = spec.get("fixture_acceptance_gate", {})
    for flag in [
        "requires_local_reviewed_fixture",
        "requires_privacy_redaction_review",
        "requires_non_guarantee_language_review",
        "requires_operator_review_record",
        "requires_follow_on_trigger_review",
        "preserves_safe_and_blocked_claims",
    ]:
        if acceptance.get(flag) is not True:
            raise CityOpsContractError(f"Incident Verification fixture acceptance lost {flag}")
    for flag in [
        "allows_customer_delivery",
        "allows_publication",
        "allows_live_dispatch",
        "allows_reputation_receipt",
        "allows_exact_gps_or_raw_metadata_release",
    ]:
        if acceptance.get(flag) is not False:
            raise CityOpsContractError(
                f"Incident Verification fixture acceptance promoted readiness: {flag}"
            )

    checklist = gate.get("review_gate_checklist")
    if not isinstance(checklist, list) or [item.get("check_id") for item in checklist] != REVIEW_GATE_CHECKS:
        raise CityOpsContractError("Incident Verification fixture review checklist drift")
    for item in checklist:
        if item.get("required") is not True or item.get("blocks_promotion_until_passed") is not True:
            raise CityOpsContractError("Incident Verification fixture checklist no longer blocks promotion")
        if item.get("status") != "pending_future_review":
            raise CityOpsContractError("Incident Verification fixture checklist status drift")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
