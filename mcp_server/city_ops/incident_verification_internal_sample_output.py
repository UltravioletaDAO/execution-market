"""Incident Verification adjacent-AAS internal/admin sample output.

This module advances Incident Verification by exactly one conservative rung: from
customer-output schema gate to one internal/admin sample output for the incident
verification proof run. The sample consumes only the persisted schema-gate
artifact, populates only allowed schema fields, and remains synthetic,
non-emergency, and non-authoritative. It is not customer copy, not publication
approval, not a catalog or pilot, not dispatch, not live Acontext/runtime parity,
not ERC-8004 reputation, not exact GPS/raw metadata exposure, not emergency
response, not safety certification, not repair/insurance/SLA proof, not an
official incident report, and not worker-copyable incident doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import READINESS_FALSE_FLAGS
from .contracts import CityOpsContractError
from .incident_verification_customer_output_schema_gate import (
    ALLOWED_CUSTOMER_OUTPUT_FIELDS,
    FORBIDDEN_CUSTOMER_OUTPUT_FIELDS,
    GATE_ID,
    INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME,
    INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM,
    INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA,
    load_incident_verification_customer_output_schema_gate,
)
from .incident_verification_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID

INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SCHEMA = (
    "city_ops.incident_verification_internal_sample_output.v1"
)
INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME = (
    "incident_verification_internal_sample_output.json"
)
INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM = (
    "incident_verification_internal_sample_output_landed"
)

SAMPLE_OUTPUT_ID = "execution_market.aas.incident_verification.internal_sample_output.001"
SCOPE = "internal_admin_incident_verification_sample_output_only"
SAMPLE_STATUS = "internal_sample_output_landed_not_customer_copy_not_public_not_approved"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
]
NEXT_REQUIRED_LADDER_STEPS = ["explicit_approval_or_hold_decision"]

SAMPLE_OUTPUT_BLOCKED_CLAIMS = [
    "internal_sample_customer_copy_ready",
    "internal_sample_customer_delivery_ready",
    "internal_sample_publication_ready",
    "internal_sample_catalog_ready",
    "internal_sample_controlled_pilot_ready",
    "internal_sample_public_route_ready",
    "internal_sample_dispatch_ready",
    "internal_sample_reputation_ready",
    "internal_sample_worker_doctrine_ready",
    "internal_sample_live_acontext_ready",
    "internal_sample_exact_gps_or_raw_metadata_release_ready",
    "internal_sample_emergency_response_ready",
    "internal_sample_safety_certification_ready",
    "internal_sample_repair_diagnosis_ready",
    "internal_sample_repair_completion_ready",
    "internal_sample_insurance_adjustment_ready",
    "internal_sample_sla_uptime_ready",
    "internal_sample_official_incident_report_ready",
    "internal_sample_fault_or_liability_assignment_ready",
    "internal_sample_operator_approval_ready",
    "internal_sample_hold_decision_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(SAMPLE_OUTPUT_BLOCKED_CLAIMS) | {
    "customer_copy_ready",
    "customer_output_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "emergency_response",
    "safety_certification",
    "repair_diagnosis",
    "repair_completion",
    "repair_diagnosis_or_completion",
    "insurance_adjustment",
    "sla_uptime",
    "official_incident_report",
    "fault_or_liability_assignment",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "dispatch_routing_ready",
    "live_dispatch",
    "erc8004_reputation_ready",
    "erc8004_reputation_receipt",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_incident_doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "customer_sample_publication_ready",
    "sample_output_publication_ready",
}

_SAMPLE_READINESS_FALSE_FLAGS = [
    "customer_copy_created",
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_allowed",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "network_route_registered",
    "public_route_registered",
    "dispatch_enabled",
    "dispatch_instruction_ready",
    "emits_reputation_receipts",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "raw_metadata_release_ready",
    "emergency_response_ready",
    "safety_certification_ready",
    "repair_diagnosis_ready",
    "repair_completion_ready",
    "insurance_adjustment_ready",
    "sla_uptime_ready",
    "official_incident_report_ready",
    "fault_or_liability_assignment_ready",
    "customer_public_launch_ready",
    "catalog_or_pilot_readiness_ready",
    "explicit_hold_or_approval_decision_recorded",
]

REQUIRED_SAMPLE_REVIEW_FLAGS = [
    "privacy_redaction_review_passed",
    "limitations_preserved_review_passed",
    "non_authoritative_language_review_passed",
    "emergency_safety_repair_insurance_sla_and_official_report_exclusion_review_passed",
]

FORBIDDEN_SAMPLE_KEYS = set(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS) | {
    "task_id_or_local_case_reference",
    "offer_type",
    "customer_private_name",
    "customer_contact_details",
    "precise_private_location",
    "dispatch_assignment",
    "worker_instruction",
    "repair_instruction",
    "insurance_adjustment_instruction",
    "official_report_reference_number",
}

FORBIDDEN_TEXT_FRAGMENTS = [
    "emergency response dispatched",
    "call 911",
    "certified safe",
    "safety certified",
    "repair completed",
    "repair diagnosed",
    "insurance adjusted",
    "official incident report filed",
    "sla guaranteed",
    "fault assigned",
    "liability assigned",
    "guaranteed uptime",
    "latitude",
    "longitude",
    "gps:",
    "raw metadata attached",
    "erc-8004 reputation receipt",
    "erc8004 reputation receipt",
    "dispatch instruction",
]

SAMPLE_FIELD_VALUES = {
    "plain_language_status": (
        "Internal review sample: the synthetic source supports a cautious note that "
        "a reported condition was observed within a bounded place/time window. This "
        "is not emergency response, safety certification, repair diagnosis, insurance "
        "adjustment, SLA proof, official reporting, fault assignment, or liability assignment."
    ),
    "incident_question_summary": (
        "The reviewed synthetic task question asks whether a visible condition appears "
        "consistent with the incident scenario under review; the answer is limited to "
        "observed evidence shape, not authority or causation."
    ),
    "place_time_window_summary": (
        "The reviewed fixture keeps the location coarse and the time window bounded for "
        "operator review while excluding precise addresses, exact-location details, and "
        "source metadata blobs."
    ),
    "wide_context_evidence_summary": (
        "Wide-context evidence is summarized as a scene-level observation that helps orient "
        "the condition under review without identifying private people, private property "
        "details, or raw capture metadata."
    ),
    "close_evidence_summary": (
        "Close evidence is summarized as a narrow visual observation of the reported "
        "condition only; it does not diagnose cause, completeness of repair, safety status, "
        "or insurance outcome."
    ),
    "observational_severity_taxonomy": (
        "Severity is described as an internal observational bucket for triage language only; "
        "it is not a safety rating, code determination, public warning, or authoritative report."
    ),
    "uncertainty_note": (
        "Uncertainty remains because the sample uses a synthetic reviewed fixture, not live "
        "sensor feeds, official databases, professional inspection, emergency dispatch, or "
        "repair verification."
    ),
    "what_was_checked": [
        "Whether the synthetic reviewed fixture supported the incident question at a plain-language observation level.",
        "Whether the wording stayed inside the Incident Verification schema-gate allowed fields.",
        "Whether privacy, uncertainty, limitations, non-authoritative language, and operator-review notices remained present.",
    ],
    "what_was_not_checked": [
        "No emergency response, safety certification, repair diagnosis, repair completion, insurance adjustment, SLA uptime, official incident report, fault, or liability conclusion was checked or produced.",
        "No exact location, raw metadata, raw transcript, private operator context, private contact, or private identity detail was checked for release.",
        "No dispatch path, worker instruction, public route, catalog entry, pilot, or reputation receipt was created.",
    ],
    "limitations_and_non_guarantees": [
        "Internal/admin sample only; not customer-ready copy and not a public incident report.",
        "Based on a synthetic fixture, not live emergency, municipal, insurance, repair, sensor, or official-report data.",
        "Does not promise safety, cause, repair status, insurance outcome, uptime, official filing, fault, liability, dispatch, or response timing.",
        "A separate explicit hold/approval decision is required before any customer-visible use.",
    ],
    "recommended_next_action": (
        "Keep this sample held for internal review. The next safe step is a separate "
        "explicit hold/approval decision over this exact sample, not publication."
    ),
    "follow_on_task_trigger": (
        "If an operator wants additional confidence, create a separate follow-on task for "
        "more evidence gathering; do not convert this sample into live dispatch or a safety instruction."
    ),
    "operator_review_notice": (
        "Internal/admin sample only. Operator review has checked wording boundaries, but "
        "no customer delivery, public posting, catalog, pilot, dispatch, reputation, emergency, "
        "safety, repair, insurance, SLA, official-report, fault, or liability readiness is approved."
    ),
    "privacy_redaction_notice": (
        "Privacy-sensitive details, precise private locations, source metadata blobs, raw "
        "transcripts, private contacts, and private operator context are excluded from this sample."
    ),
}


def build_incident_verification_internal_sample_output(
    *, schema_gate: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one conservative Incident Verification internal/admin sample output."""

    gate = schema_gate or load_incident_verification_customer_output_schema_gate()
    _assert_source_gate(gate)

    safe_to_claim = _dedupe(
        [
            *gate.get("safe_to_claim", []),
            INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *gate.get("do_not_claim_yet", []),
            *SAMPLE_OUTPUT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    sample = {
        "schema": INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SCHEMA,
        "sample_output_id": SAMPLE_OUTPUT_ID,
        "scope": SCOPE,
        "sample_status": SAMPLE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_schema_gate_id": gate["gate_id"],
        "source_schema_gate_schema": gate["schema"],
        "source_schema_gate_file": INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "source_contract": {
            "consumes_only": [INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME],
            "source_loader": "load_incident_verification_customer_output_schema_gate",
            "source_is_schema_gate_only": True,
            "reads_operator_surface_directly": False,
            "reads_raw_review_fixture": False,
            "reads_raw_transcripts": False,
            "reads_raw_metadata": False,
            "reads_private_operator_context": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "emits_reputation_receipts": False,
            "enables_dispatch_automation": False,
            "publishes_worker_doctrine": False,
            "exposes_exact_gps_or_raw_metadata": False,
            "creates_emergency_response_claim": False,
            "creates_safety_certification_claim": False,
            "creates_repair_or_insurance_claim": False,
            "creates_sla_or_official_report_claim": False,
            "assigns_fault_or_liability": False,
        },
        "sample_output": {
            "sample_review_status": "internal_admin_sample_against_schema_gate_not_customer_copy",
            "sample_offer": OFFER_ID,
            "jurisdiction_specific": False,
            "synthetic_fixture_only": True,
            "allowed_customer_output_fields": list(ALLOWED_CUSTOMER_OUTPUT_FIELDS),
            "field_values": dict(SAMPLE_FIELD_VALUES),
            "forbidden_customer_output_fields_absent": list(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS),
            "separate_reviews": {
                "privacy_redaction_review_passed": True,
                "limitations_preserved_review_passed": True,
                "non_authoritative_language_review_passed": True,
                "emergency_safety_repair_insurance_sla_and_official_report_exclusion_review_passed": True,
                "operator_publish_approval": False,
                "customer_delivery_approval": False,
                "explicit_hold_or_approval_decision_recorded": False,
            },
        },
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "sample_output_readiness": {flag: False for flag in _SAMPLE_READINESS_FALSE_FLAGS},
        "sample_output_checks": [
            {
                "check_id": check_id,
                "status": "passed_for_internal_sample_only",
                "blocks_promotion_until_explicit_decision": True,
            }
            for check_id in [
                "source_schema_gate_safe_claim_present",
                "sample_consumes_only_customer_output_schema_gate",
                "sample_populates_only_allowed_schema_fields",
                "privacy_redaction_notice_preserved",
                "limitations_uncertainty_and_non_authoritative_language_preserved",
                "customer_public_catalog_pilot_dispatch_reputation_live_acontext_still_blocked",
                "emergency_safety_repair_insurance_sla_official_report_fault_liability_gps_raw_metadata_and_worker_doctrine_claims_still_blocked",
                "next_step_is_explicit_hold_or_approval_decision_not_publication",
            ]
        ],
        "operator_instruction": (
            "Use this only as an internal/admin wording-shape sample for Incident Verification. "
            "Do not publish it, route it, dispatch from it, attach reputation receipts, expose "
            "exact GPS/raw metadata, or treat it as emergency, safety, repair, insurance, SLA, "
            "official-report, fault, liability, catalog, pilot, customer-delivery, or worker-doctrine readiness."
        ),
        "next_smallest_proof": (
            "Record a separate explicit hold/approval decision over this sample. Default to hold; "
            "this is not publication. Do not publish, route, dispatch, attach reputation receipts, "
            "expose exact GPS/raw metadata, or claim customer/catalog/pilot/emergency/safety/repair/"
            "insurance/SLA/official-report/fault/liability readiness."
        ),
    }
    _assert_sample_packet_is_conservative(sample, source_gate=gate)
    return sample


def write_incident_verification_internal_sample_output(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Incident Verification internal/admin sample output."""

    sample = build_incident_verification_internal_sample_output()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME
    path.write_text(json.dumps(sample, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_incident_verification_internal_sample_output(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Incident Verification sample output."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        sample = json.load(fh)
    if not isinstance(sample, dict):
        raise CityOpsContractError("Incident Verification internal sample output must be a JSON object")
    _assert_sample_packet_is_conservative(
        sample,
        source_gate=_load_source_schema_gate_for_dir(source_dir),
    )
    return sample


def _load_source_schema_gate_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).exists():
        return load_incident_verification_customer_output_schema_gate(artifact_dir=source_dir)
    return load_incident_verification_customer_output_schema_gate()


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("Incident Verification internal sample source gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("Incident Verification internal sample source gate id drift")
    if gate.get("scope") != "internal_admin_customer_output_schema_gate_only":
        raise CityOpsContractError("Incident Verification internal sample source gate scope drift")
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Incident Verification internal sample source family drift")
    if gate.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Incident Verification internal sample source offer drift")
    if INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("Incident Verification internal sample source safe claim missing")
    ladder = gate.get("ladder_boundary", {})
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification internal sample source promoted readiness")
    if ladder.get("next_required_steps_before_promotion") != [
        "internal_sample_output",
        "explicit_approval_or_hold_decision",
    ]:
        raise CityOpsContractError("Incident Verification internal sample source next step drift")
    schema_review = gate.get("schema_review", {})
    if schema_review.get("allowed_customer_output_fields") != ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Incident Verification internal sample source allowed field drift")
    if schema_review.get("forbidden_customer_output_fields") != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Incident Verification internal sample source forbidden field drift")
    for flag in READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification internal sample source promoted readiness: {flag}")
    for flag, value in gate.get("schema_gate_readiness", {}).items():
        if value is not False:
            raise CityOpsContractError(f"Incident Verification internal sample source promoted schema readiness: {flag}")
    for claim in [
        "incident_verification_customer_sample_output_ready",
        "incident_verification_customer_public_launch_ready",
        "incident_verification_catalog_or_pilot_readiness_ready",
        "schema_gate_dispatch_ready",
        "schema_gate_reputation_ready",
        "schema_gate_exact_gps_or_raw_metadata_release_ready",
        "schema_gate_emergency_response_ready",
        "schema_gate_safety_certification_ready",
        "schema_gate_repair_ready",
        "schema_gate_insurance_ready",
        "schema_gate_sla_ready",
        "schema_gate_official_report_ready",
        "schema_gate_worker_doctrine_ready",
    ]:
        if claim not in gate.get("do_not_claim_yet", []):
            raise CityOpsContractError(f"Incident Verification internal sample source missing blocked claim: {claim}")


def _assert_sample_packet_is_conservative(
    sample: dict[str, Any], *, source_gate: dict[str, Any]
) -> None:
    _assert_source_gate(source_gate)
    if sample.get("schema") != INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SCHEMA:
        raise CityOpsContractError("Incident Verification internal sample schema drift")
    if sample.get("sample_output_id") != SAMPLE_OUTPUT_ID:
        raise CityOpsContractError("Incident Verification internal sample id drift")
    if sample.get("scope") != SCOPE:
        raise CityOpsContractError("Incident Verification internal sample scope drift")
    if sample.get("sample_status") != SAMPLE_STATUS:
        raise CityOpsContractError("Incident Verification internal sample status drift")
    if sample.get("source_schema_gate_id") != source_gate.get("gate_id"):
        raise CityOpsContractError("Incident Verification internal sample source gate drift")
    if sample.get("source_schema_gate_file") != INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME:
        raise CityOpsContractError("Incident Verification internal sample source file drift")

    safe_to_claim = list(sample.get("safe_to_claim", []))
    do_not_claim_yet = list(sample.get("do_not_claim_yet", []))
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    if INCIDENT_VERIFICATION_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("Incident Verification internal sample safe claim missing")
    if INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("Incident Verification internal sample inherited schema gate claim missing")
    missing_blocked = (set(source_gate.get("do_not_claim_yet", [])) | set(SAMPLE_OUTPUT_BLOCKED_CLAIMS)) - set(
        do_not_claim_yet
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Incident Verification internal sample missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = sample.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification internal sample covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification internal sample next step drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification internal sample promoted readiness")

    source_contract = sample.get("source_contract", {})
    if source_contract.get("consumes_only") != [INCIDENT_VERIFICATION_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME]:
        raise CityOpsContractError("Incident Verification internal sample input drift")
    for flag in (
        "reads_operator_surface_directly",
        "reads_raw_review_fixture",
        "reads_raw_transcripts",
        "reads_raw_metadata",
        "reads_private_operator_context",
        "writes_customer_copy",
        "writes_live_acontext",
        "emits_reputation_receipts",
        "enables_dispatch_automation",
        "publishes_worker_doctrine",
        "exposes_exact_gps_or_raw_metadata",
        "creates_emergency_response_claim",
        "creates_safety_certification_claim",
        "creates_repair_or_insurance_claim",
        "creates_sla_or_official_report_claim",
        "assigns_fault_or_liability",
    ):
        if source_contract.get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification internal sample source contract overclaims: {flag}")

    _assert_sample_output_is_conservative(sample.get("sample_output", {}))

    for flag in READINESS_FALSE_FLAGS:
        if sample.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification internal sample promoted readiness: {flag}")
    for flag in _SAMPLE_READINESS_FALSE_FLAGS:
        if sample.get("sample_output_readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification internal sample promoted sample readiness: {flag}")

    checks = sample.get("sample_output_checks")
    if not isinstance(checks, list) or len(checks) != 8:
        raise CityOpsContractError("Incident Verification internal sample checks drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_sample_only":
            raise CityOpsContractError("Incident Verification internal sample check status drift")
        if item.get("blocks_promotion_until_explicit_decision") is not True:
            raise CityOpsContractError("Incident Verification internal sample stopped blocking promotion")

    _assert_no_forbidden_text(sample)


def _assert_sample_output_is_conservative(sample_output: dict[str, Any]) -> None:
    if sample_output.get("sample_review_status") != "internal_admin_sample_against_schema_gate_not_customer_copy":
        raise CityOpsContractError("Incident Verification internal sample review status drift")
    if sample_output.get("sample_offer") != OFFER_ID:
        raise CityOpsContractError("Incident Verification internal sample offer drift")
    if sample_output.get("jurisdiction_specific") is not False:
        raise CityOpsContractError("Incident Verification internal sample became jurisdiction-specific")
    if sample_output.get("synthetic_fixture_only") is not True:
        raise CityOpsContractError("Incident Verification internal sample stopped being synthetic-only")
    if sample_output.get("allowed_customer_output_fields") != ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Incident Verification internal sample allowed fields drift")
    if sample_output.get("forbidden_customer_output_fields_absent") != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Incident Verification internal sample forbidden absent fields drift")
    values = sample_output.get("field_values")
    if not isinstance(values, dict):
        raise CityOpsContractError("Incident Verification internal sample missing field values")
    if set(values.keys()) != set(ALLOWED_CUSTOMER_OUTPUT_FIELDS):
        raise CityOpsContractError("Incident Verification internal sample populated disallowed field")
    forbidden_keys = sorted(FORBIDDEN_SAMPLE_KEYS & set(values.keys()))
    if forbidden_keys:
        raise CityOpsContractError(f"Incident Verification internal sample included forbidden keys: {forbidden_keys}")
    _assert_review_flags(sample_output.get("separate_reviews", {}))


def _assert_review_flags(review: dict[str, Any]) -> None:
    if not isinstance(review, dict):
        raise CityOpsContractError("Incident Verification internal sample missing separate reviews")
    missing = [flag for flag in REQUIRED_SAMPLE_REVIEW_FLAGS if review.get(flag) is not True]
    if missing:
        raise CityOpsContractError(f"Incident Verification internal sample missing review gates: {missing}")
    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "explicit_hold_or_approval_decision_recorded",
    ]:
        if review.get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification internal sample promoted review flag: {flag}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(f"Incident Verification internal sample has forbidden safe claims: {forbidden}")
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(f"Incident Verification internal sample claim overlap: {overlap}")


def _assert_no_forbidden_text(sample: dict[str, Any]) -> None:
    serialized = json.dumps(sample, sort_keys=True).lower()
    for fragment in FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(f"Incident Verification internal sample forbidden text fragment: {fragment}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
