"""Incident Verification adjacent-AAS local reviewed fixture.

This module advances Incident Verification by exactly one rung: from an
internal fixture spec/review gate to one synthetic local reviewed fixture. It
remains internal/admin only. It does not create customer copy, publish a
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
)
from .contracts import CityOpsContractError
from .incident_verification_fixture_review_gate import (
    ARTIFACT_DIR,
    INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_BLOCKED_CLAIMS as GATE_BLOCKED_CLAIMS,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    load_incident_verification_fixture_review_gate,
)

INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SCHEMA = (
    "city_ops.incident_verification_local_reviewed_fixture.v1"
)
INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME = (
    "incident_verification_local_reviewed_fixture.json"
)
INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "incident_verification_local_reviewed_fixture_landed"
)

FIXTURE_ID = "execution_market.aas.incident_verification.local_reviewed_fixture.001"
SCOPE = "internal_admin_incident_verification_local_reviewed_fixture_only"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

LOCAL_FIXTURE_REVIEW_CHECKS = [
    "source_gate_safe_claims_present",
    "all_required_incident_evidence_fields_populated",
    "reviewed_output_uses_only_allowed_fields",
    "place_time_window_summary_avoids_exact_public_coordinates",
    "wide_and_close_evidence_are_permitted_visual_summaries_only",
    "severity_taxonomy_is_observational_not_safety_certification",
    "uncertainty_and_what_was_not_checked_are_explicit",
    "follow_on_trigger_is_next_step_only_not_live_dispatch",
    "privacy_redaction_completed_for_local_fixture",
    "exact_gps_raw_metadata_private_address_and_raw_transcript_absent",
    "emergency_safety_repair_insurance_sla_and_official_report_claims_absent",
    "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "incident_verification_local_fixture_customer_delivery_ready",
    "incident_verification_local_fixture_publication_ready",
    "incident_verification_local_fixture_catalog_ready",
    "incident_verification_local_fixture_dispatch_ready",
    "incident_verification_local_fixture_reputation_ready",
    "incident_verification_local_fixture_worker_doctrine_ready",
    "incident_verification_local_fixture_live_acontext_ready",
    "incident_verification_local_fixture_emergency_ready",
    "incident_verification_local_fixture_safety_certification_ready",
    "incident_verification_local_fixture_repair_ready",
    "incident_verification_local_fixture_insurance_ready",
    "incident_verification_local_fixture_official_report_ready",
    "incident_verification_local_fixture_sla_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(GATE_BLOCKED_CLAIMS) | set(ADDITIONAL_BLOCKED_CLAIMS)


def build_incident_verification_local_reviewed_fixture(
    *, gate: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one internal reviewed fixture for Incident Verification.

    The fixture is synthetic and non-jurisdiction-specific. It proves the local
    review shape for a bounded one-location incident state snapshot without
    claiming emergency response, safety certification, repair diagnosis,
    insurance adjustment, official reporting, customer readiness, dispatch,
    reputation attachment, live Acontext parity, exact location disclosure, or
    worker-copyable incident doctrine.
    """

    source_gate = gate or load_incident_verification_fixture_review_gate()
    _assert_source_gate(source_gate)

    reviewed_output = {
        "task_id_or_local_case_reference": "local_incident_verification_fixture_001",
        "offer_type": OFFER_ID,
        "plain_language_status": (
            "A bounded one-location incident state snapshot was reviewed from "
            "permitted synthetic visual evidence and a scoped time window. This "
            "is an operator-reviewed evidence snapshot, not emergency response, "
            "not a safety certification, not a repair diagnosis, not an insurance "
            "adjustment, and not an official incident report."
        ),
        "incident_question": (
            "Is the reported obstruction-like condition visibly present during "
            "the scoped observation window, and what bounded next action should "
            "an operator consider?"
        ),
        "place_time_window_summary": (
            "Synthetic public-facing location category and same-day observation "
            "window only; no precise address, exact GPS coordinate, raw metadata, "
            "or private resident/tenant identity is retained in reviewed output."
        ),
        "wide_context_evidence_summary": (
            "Wide-context permitted visual snapshot showed the general scene and "
            "approach boundary, enough to classify that an obstruction-like condition "
            "was visible in the scoped window without exposing exact coordinates."
        ),
        "close_evidence_summary": (
            "Close evidence summary captured the observable condition category and "
            "approximate relative placement. It does not include raw photo metadata, "
            "precise measurements, private identifiers, or unsafe access claims."
        ),
        "severity_taxonomy": "observed_minor_to_moderate_obstruction_unverified_safety_impact",
        "uncertainty_note": (
            "The fixture cannot determine cause, legal responsibility, safety risk, "
            "repair scope, emergency urgency, insurance value, or official status."
        ),
        "what_was_checked": [
            "incident_question_present",
            "scoped_place_time_window_without_exact_public_coordinates",
            "wide_context_visual_summary",
            "close_evidence_visual_summary_where_allowed",
            "observational_severity_taxonomy",
            "uncertainty_and_limitations",
            "follow_on_trigger_as_operator_next_step_only",
        ],
        "what_was_not_checked": [
            "emergency_response_need",
            "safety_certification",
            "repair_diagnosis_or_completion",
            "insurance_adjustment",
            "official_incident_report",
            "sla_uptime_or_resolution_time",
            "exact_location_publication",
            "live_dispatch_readiness",
            "customer_delivery_readiness",
        ],
        "limitations_and_non_guarantees": [
            "This fixture is synthetic and local; it does not represent a real incident case.",
            "The review does not certify safety, diagnose repairs, assign fault, or adjust insurance.",
            "The output summarizes permitted evidence and excludes exact GPS/raw metadata/private addresses.",
            "The follow-on trigger is only an operator next-step suggestion, not live dispatch.",
            "No customer delivery, public catalog, dispatch route, ERC-8004 reputation receipt, SLA, official report, or worker doctrine is authorized.",
        ],
        "recommended_next_action": (
            "Create an Incident Verification internal package record that consumes "
            "this local fixture and keeps customer/public/dispatch/reputation/"
            "privacy/emergency/safety/repair/insurance/SLA/official-report/"
            "worker-doctrine readiness false."
        ),
        "follow_on_task_trigger": (
            "operator_review_next_step_only: consider a separate scoped follow-up "
            "verification or specialist referral if the customer requests more than "
            "an observational state snapshot; do not auto-dispatch."
        ),
        "operator_review_notice": (
            "Reviewed for local fixture shape only. Keep all customer/public/pilot/"
            "dispatch/reputation/live-runtime/emergency/safety/repair/insurance/"
            "SLA/official-report/worker-doctrine readiness false."
        ),
    }

    fixture = {
        "schema": INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": FIXTURE_ID,
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_gate_id": source_gate["gate_id"],
        "source_gate_schema": source_gate["schema"],
        "source_safe_claims_inherited": [
            INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "safe_to_claim": [
            INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "do_not_claim_yet": _dedupe(
            [
                *GATE_BLOCKED_CLAIMS,
                *source_gate.get("do_not_claim_yet", []),
                *ADDITIONAL_BLOCKED_CLAIMS,
            ]
        ),
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "local_fixture": {
            "review_status": "reviewed_internal_fixture_only_not_promoted",
            "fixture_kind": "synthetic_non_jurisdiction_specific_incident_state_snapshot",
            "customer_copy_changed": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "worker_copyable_doctrine_allowed": False,
            "emergency_or_safety_claim_allowed": False,
            "repair_or_insurance_claim_allowed": False,
            "sla_or_official_report_claim_allowed": False,
            "evidence_contract_snapshot": {
                "incident_question": "bounded_obstruction_like_condition_state_question",
                "place_time_window_without_exact_public_coordinates": (
                    "synthetic_public_facing_place_category_and_relative_window_no_precise_address_or_gps"
                ),
                "wide_context_photo_or_permitted_visual_snapshot": (
                    "permitted_visual_summary_only_no_raw_metadata"
                ),
                "close_evidence_photo_where_allowed": (
                    "permitted_close_evidence_summary_without_private_identifiers_or_unsafe_access_claims"
                ),
                "severity_taxonomy": "observational_taxonomy_not_safety_certification",
                "uncertainty_note": "cause_fault_safety_repair_insurance_and_official_status_unverified",
                "what_was_not_checked": (
                    "emergency_response_safety_certification_repair_insurance_official_report_sla_and_dispatch"
                ),
                "recommended_next_action": (
                    "package_as_internal_record_before_any_customer_output_schema_or_approval_decision"
                ),
                "follow_on_task_trigger_if_another_visit_or_specialist_needed": (
                    "operator_review_next_step_only_no_live_dispatch"
                ),
            },
            "reviewed_output_schema": {
                "status": "local_reviewed_fixture_internal_only_not_customer_output",
                "required_fields": list(REQUIRED_OUTPUT_FIELDS),
                "forbidden_fields": list(
                    source_gate["fixture_spec"]["reviewed_output_schema_draft"][
                        "forbidden_fields"
                    ]
                ),
            },
            "reviewed_output": reviewed_output,
        },
        "local_review_checks": [
            {
                "check_id": check,
                "status": "passed_for_local_fixture_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check in LOCAL_FIXTURE_REVIEW_CHECKS
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "operator_instruction": (
            "Use this fixture only to prove the Incident Verification reviewed-output "
            "shape. The next valid step is an internal package record, not customer "
            "copy, catalog routing, dispatch, reputation, live Acontext, emergency/"
            "safety/repair/insurance/SLA/official-report claims, exact location "
            "release, or worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Create an Incident Verification internal package record that consumes "
            "this local fixture and keeps customer/public/dispatch/reputation/privacy/"
            "emergency/safety/repair/insurance/SLA/official-report/worker-doctrine "
            "readiness false."
        ),
    }
    _assert_fixture_is_conservative(fixture, source_gate=source_gate)
    return fixture


def write_incident_verification_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Incident Verification local reviewed fixture."""

    fixture = build_incident_verification_local_reviewed_fixture()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_incident_verification_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Incident Verification local reviewed fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    if not isinstance(fixture, dict):
        raise CityOpsContractError(
            "Incident Verification local reviewed fixture must be a JSON object"
        )
    _assert_fixture_is_conservative(
        fixture, source_gate=load_incident_verification_fixture_review_gate()
    )
    return fixture


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Incident Verification local fixture source gate family drift")
    if gate.get("fixture_spec", {}).get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Incident Verification local fixture source gate offer drift")
    safe_claims = set(gate.get("safe_to_claim", []))
    for claim in (
        INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
        AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    ):
        if claim not in safe_claims:
            raise CityOpsContractError("Incident Verification local fixture source safe claim missing")
    gate_ladder = gate.get("ladder_boundary", {})
    if gate_ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification local fixture source gate promoted readiness")


def _assert_fixture_is_conservative(
    fixture: dict[str, Any], *, source_gate: dict[str, Any]
) -> None:
    _assert_source_gate(source_gate)
    if fixture.get("schema") != INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SCHEMA:
        raise CityOpsContractError("Incident Verification local reviewed fixture schema drift")
    if fixture.get("scope") != SCOPE:
        raise CityOpsContractError("Incident Verification local reviewed fixture scope drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Incident Verification local reviewed fixture family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Incident Verification local reviewed fixture offer drift")
    if fixture.get("source_gate_id") != source_gate.get("gate_id"):
        raise CityOpsContractError("Incident Verification local reviewed fixture source gate drift")

    safe_claims = set(fixture.get("safe_to_claim", []))
    if INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM not in safe_claims:
        raise CityOpsContractError("Incident Verification local reviewed fixture safe claim missing")
    if safe_claims & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Incident Verification local reviewed fixture has forbidden safe claims")
    for inherited_claim in fixture.get("source_safe_claims_inherited", []):
        if inherited_claim not in safe_claims:
            raise CityOpsContractError("Incident Verification local reviewed fixture inherited claim missing")

    missing_blocked = (set(GATE_BLOCKED_CLAIMS) | set(ADDITIONAL_BLOCKED_CLAIMS)) - set(
        fixture.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            "Incident Verification local reviewed fixture missing blocked claims: "
            f"{sorted(missing_blocked)}"
        )

    ladder = fixture.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification local reviewed fixture covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification local reviewed fixture next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification local reviewed fixture promoted readiness")

    readiness = fixture.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Incident Verification local reviewed fixture promoted readiness: {flag}"
            )

    local_fixture = fixture.get("local_fixture")
    if not isinstance(local_fixture, dict):
        raise CityOpsContractError("Incident Verification local fixture payload must be an object")
    if local_fixture.get("review_status") != "reviewed_internal_fixture_only_not_promoted":
        raise CityOpsContractError("Incident Verification local fixture review status drift")
    for false_flag in (
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_copyable_doctrine_allowed",
        "emergency_or_safety_claim_allowed",
        "repair_or_insurance_claim_allowed",
        "sla_or_official_report_claim_allowed",
    ):
        if local_fixture.get(false_flag) is not False:
            raise CityOpsContractError(f"Incident Verification local fixture promoted {false_flag}")

    evidence = local_fixture.get("evidence_contract_snapshot", {})
    if set(REQUIRED_EVIDENCE_FIELDS) - set(evidence):
        raise CityOpsContractError("Incident Verification local fixture lost required evidence fields")

    schema = local_fixture.get("reviewed_output_schema", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(schema.get("required_fields", []))):
        raise CityOpsContractError("Incident Verification local fixture lost required output fields")
    forbidden_fields = set(schema.get("forbidden_fields", []))
    for field in (
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "precise_address_or_private_location",
        "raw_transcript_as_authority",
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
    ):
        if field not in forbidden_fields:
            raise CityOpsContractError("Incident Verification local fixture lost forbidden output fields")

    reviewed_output = local_fixture.get("reviewed_output", {})
    if set(REQUIRED_OUTPUT_FIELDS) - set(reviewed_output):
        raise CityOpsContractError("Incident Verification local fixture reviewed output lost required fields")
    _assert_no_private_location_or_incident_overclaims(reviewed_output)

    checks = fixture.get("local_review_checks")
    if not isinstance(checks, list) or len(checks) != len(LOCAL_FIXTURE_REVIEW_CHECKS):
        raise CityOpsContractError("Incident Verification local fixture review checks drift")
    check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
    if check_ids != LOCAL_FIXTURE_REVIEW_CHECKS:
        raise CityOpsContractError("Incident Verification local fixture review check order drift")
    for item in checks:
        if item.get("status") != "passed_for_local_fixture_only":
            raise CityOpsContractError("Incident Verification local fixture review check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Incident Verification local fixture review check stopped blocking promotion"
            )


def _assert_no_private_location_or_incident_overclaims(reviewed_output: dict[str, Any]) -> None:
    serialized = json.dumps(reviewed_output, sort_keys=True).lower()
    forbidden_substrings = [
        "latitude",
        "longitude",
        "gps:",
        "gps coordinate:",
        "home address",
        "precise address:",
        "driver license",
        "passport",
        "social security",
        "emergency response completed",
        "emergency dispatch",
        "safety certified",
        "safe for occupancy",
        "repair diagnosed",
        "repair completed",
        "insurance adjustment completed",
        "official incident report filed",
        "sla guaranteed",
        "worker doctrine ready",
    ]
    for substring in forbidden_substrings:
        if substring in serialized:
            raise CityOpsContractError(
                "Incident Verification local fixture leaked private location or incident overclaim"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
