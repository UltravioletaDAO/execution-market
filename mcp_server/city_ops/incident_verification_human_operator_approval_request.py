"""Incident Verification human-operator approval request.

This module is the cautious next rung after the internal Incident Verification
package-review decision. It creates a pending request for a human operator to
review exactly one Incident Verification label/text boundary. It is intentionally
not a human approval record, not customer copy, not delivery, not publication,
not a public route/catalog/pilot, not pricing, not queue launch, not dispatch,
not reputation, not live Acontext/runtime parity, not exact GPS/raw metadata
exposure, not raw transcript authority, not emergency/safety/repair/insurance/
SLA/official-report/fault-liability authority, and not worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .incident_verification_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .incident_verification_package_review_decision import (
    ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS,
    FOLLOW_ON_ESCALATION_BOUNDARIES,
    FORBIDDEN_FIELD_CLASSES,
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME,
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
    INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SCHEMA,
    NEXT_REQUIRED_GATE,
    PACKAGE_REVIEW_BLOCKED_CLAIMS as SOURCE_PACKAGE_REQUIRED_BLOCKED_CLAIMS,
    PACKAGE_REVIEW_DECISION,
    PACKAGE_REVIEW_FALSE_FLAGS,
    SELECTED_INTERNAL_LABEL,
    load_incident_verification_package_review_decision,
)

INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA = (
    "city_ops.incident_verification_human_operator_approval_request.v1"
)
INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME = (
    "incident_verification_human_operator_approval_request.json"
)
INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM = (
    "incident_verification_human_operator_approval_request_landed"
)

REQUEST_ID = "execution_market.aas.incident_verification.human_operator_approval_request.001"
SCOPE = "internal_admin_incident_verification_human_operator_approval_request_only"
SELECTED_TEXT_BOUNDARY_KEY = "incident_verification_internal_package_label"
APPROVAL_REQUEST_STATUS = "pending_human_operator_review_not_approved"
AUTHORIZED_DELIVERY_PATH = "none_until_separate_human_operator_approval_record"

REQUIRED_PRE_APPROVAL_CHECKS = [
    "source_package_review_decision_still_held",
    "selected_text_boundary_exact_value_preserved",
    "allowed_future_fields_still_allowlisted_only",
    "forbidden_authority_classes_still_blocked",
    "follow_on_escalation_boundaries_still_non_authorizing",
    "privacy_redaction_required_before_any_approval",
    "exact_gps_and_raw_metadata_reverification_required_before_any_approval",
    "raw_transcript_authority_absent_before_any_approval",
    "emergency_safety_repair_insurance_sla_official_report_fault_liability_language_absent_before_any_approval",
    "authorized_delivery_path_required_but_absent",
    "operator_publish_approval_required_but_absent",
    "customer_delivery_approval_required_but_absent",
]

REDACTION_AND_AUTHORITY_REQUIREMENTS = [
    "exact_gps_removed",
    "raw_metadata_removed",
    "raw_transcript_not_used_as_authority",
    "private_operator_context_removed",
    "precise_private_location_removed",
    "emergency_response_instruction_absent",
    "safety_certification_language_absent",
    "repair_diagnosis_language_absent",
    "repair_completion_language_absent",
    "insurance_adjustment_language_absent",
    "sla_uptime_or_availability_guarantee_absent",
    "official_incident_report_language_absent",
    "fault_or_liability_assignment_language_absent",
    "dispatch_instruction_language_absent",
    "reputation_receipt_language_absent",
    "worker_copyable_incident_doctrine_absent",
]

REQUEST_READINESS_FALSE_FLAGS = [
    *PACKAGE_REVIEW_FALSE_FLAGS,
    "human_operator_approval_recorded",
    "selected_text_boundary_approved",
    "pre_approval_checks_passed",
    "redaction_requirements_passed",
    "authority_requirements_passed",
    "follow_on_escalation_authorized",
    "authorized_delivery_path_recorded",
    "operator_publish_approval",
    "customer_delivery_approval",
]

REQUEST_BLOCKED_CLAIMS = [
    *SOURCE_PACKAGE_REQUIRED_BLOCKED_CLAIMS,
    "incident_verification_human_operator_approval_recorded",
    "incident_verification_selected_text_boundary_approved",
    "incident_verification_pre_approval_checks_passed",
    "incident_verification_customer_copy_created",
    "incident_verification_customer_copy_ready",
    "incident_verification_authorized_delivery_path_recorded",
    "incident_verification_customer_delivery_approved",
    "incident_verification_publication_approved",
    "incident_verification_public_route_ready",
    "incident_verification_catalog_route_ready",
    "incident_verification_controlled_pilot_ready",
    "incident_verification_public_price_approved",
    "incident_verification_customer_quote_ready",
    "incident_verification_operator_queue_launch_ready",
    "incident_verification_dispatch_enabled",
    "incident_verification_reputation_ready",
    "incident_verification_live_runtime_ready",
    "incident_verification_exact_gps_or_raw_metadata_release_ready",
    "incident_verification_raw_transcript_authority_ready",
    "incident_verification_emergency_response_ready",
    "incident_verification_safety_certification_ready",
    "incident_verification_repair_diagnosis_ready",
    "incident_verification_repair_completion_ready",
    "incident_verification_insurance_adjustment_ready",
    "incident_verification_sla_uptime_ready",
    "incident_verification_official_incident_report_ready",
    "incident_verification_fault_or_liability_assignment_ready",
    "incident_verification_worker_copyable_incident_doctrine_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUEST_BLOCKED_CLAIMS) | {
    "human_operator_approval_recorded",
    "selected_text_boundary_approved",
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
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
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "raw_transcript_authority_ready",
    "emergency_response_ready",
    "safety_certification_ready",
    "repair_diagnosis_ready",
    "repair_completion_ready",
    "insurance_adjustment_ready",
    "sla_uptime_ready",
    "official_incident_report_ready",
    "fault_or_liability_assignment_ready",
    "worker_copyable_doctrine_ready",
}

REQUEST_FALSE_TOP_LEVEL_FLAGS = {
    "human_operator_approval_recorded": False,
    "selected_text_boundary_approved": False,
    "pre_approval_checks_passed": False,
    "redaction_requirements_passed": False,
    "authority_requirements_passed": False,
    "follow_on_escalation_authorized": False,
    "authorized_delivery_path_recorded": False,
    "operator_publish_approval": False,
    "customer_delivery_approval": False,
    "customer_delivery_path_authorized": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "publication_approved": False,
    "public_route_ready": False,
    "catalog_route_ready": False,
    "controlled_pilot_ready": False,
    "front_door_sku_ready": False,
    "public_price_approved": False,
    "customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_enabled": False,
    "autonomous_dispatch_ready": False,
    "reputation_ready": False,
    "erc8004_reputation_ready": False,
    "live_acontext_ready": False,
    "runtime_parity_proven": False,
    "exact_gps_or_raw_metadata_exposure_allowed": False,
    "raw_transcript_authority_allowed": False,
    "emergency_response_ready": False,
    "safety_certification_ready": False,
    "repair_diagnosis_ready": False,
    "repair_completion_ready": False,
    "insurance_adjustment_ready": False,
    "sla_uptime_ready": False,
    "official_incident_report_ready": False,
    "fault_or_liability_assignment_ready": False,
    "worker_skill_dna_ready": False,
    "worker_copyable_doctrine_ready": False,
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


def _load_source_package_review(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_incident_verification_package_review_decision(artifact_dir=artifact_dir)


def _assert_source_package_review(decision: dict[str, Any]) -> None:
    if decision.get("schema") != INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("incident approval request source schema drift")
    if decision.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("incident approval request source family drift")
    if decision.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("incident approval request source offer drift")
    if decision.get("package_review_decision") != PACKAGE_REVIEW_DECISION:
        raise CityOpsContractError("incident approval request source promoted decision")
    if decision.get("selected_internal_label") != SELECTED_INTERNAL_LABEL:
        raise CityOpsContractError("incident approval request source label drift")
    if decision.get("selected_internal_label_customer_copy_approved") is not False:
        raise CityOpsContractError("incident approval request source label promoted")
    if decision.get("next_required_gate_before_any_delivery_path") != NEXT_REQUIRED_GATE:
        raise CityOpsContractError("incident approval request source next gate drift")
    if decision.get("next_gate_satisfied") is not False:
        raise CityOpsContractError("incident approval request source next gate promoted")
    if INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM not in decision.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("incident approval request source safe claim missing")
    forbidden_safe = set(decision.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"incident approval request source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SOURCE_PACKAGE_REQUIRED_BLOCKED_CLAIMS) - set(
        decision.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"incident approval request source missing blocked claims: {sorted(missing_blocked)}"
        )
    if decision.get("allowed_future_customer_output_fields") != ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("incident approval request source allowed field drift")
    if set(FORBIDDEN_FIELD_CLASSES) - set(decision.get("forbidden_field_classes", [])):
        raise CityOpsContractError("incident approval request source forbidden classes drift")
    if decision.get("follow_on_escalation_boundaries") != FOLLOW_ON_ESCALATION_BOUNDARIES:
        raise CityOpsContractError("incident approval request source follow-on boundary drift")
    for row in decision.get("follow_on_escalation_boundaries", []):
        if row.get("execution_market_action_authorized") is not False:
            raise CityOpsContractError("incident approval request source follow-on action authorized")
    for flag in PACKAGE_REVIEW_FALSE_FLAGS:
        if decision.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"incident approval request source promoted readiness {flag}"
            )
    summary = decision.get("package_review_summary", {})
    for flag in [
        "customer_copy_approved",
        "customer_delivery_approved",
        "publication_approved",
        "public_price_or_customer_quote_approved",
        "queue_dispatch_reputation_runtime_gps_incident_authority_worker_doctrine_approved",
    ]:
        if summary.get(flag) is not False:
            raise CityOpsContractError(
                f"incident approval request source summary promoted {flag}"
            )
    for row in decision.get("review_questions", []):
        if row.get("approval_granted") is not False:
            raise CityOpsContractError("incident approval request source question approved")


def _selected_text_boundary(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": SELECTED_TEXT_BOUNDARY_KEY,
        "package_family_id": source["package_family_id"],
        "offer_id": source["offer_id"],
        "candidate_text_boundary": "internal_package_label_only",
        "candidate_text_value": source["selected_internal_label"],
        "candidate_text_fields": ["selected_internal_label"],
        "approval_request_boundary": (
            "human_operator_may_review_this_exact_incident_verification_label_later_"
            "but_no_approval_is_recorded_here"
        ),
        "source_customer_copy_approved": source["selected_internal_label_customer_copy_approved"],
        "source_next_gate_satisfied": source["next_gate_satisfied"],
        "selected_text_boundary_approved": False,
        "human_operator_approval_recorded": False,
        "customer_delivery_authorized_by_boundary": False,
        "publication_authorized_by_boundary": False,
        "emergency_safety_repair_insurance_sla_official_report_fault_or_liability_authorized_by_boundary": False,
        "readiness": {flag: False for flag in REQUEST_READINESS_FALSE_FLAGS},
    }


def _pre_approval_checks() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "required_before_human_approval": True,
            "passed_here": False,
            "approval_granted": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "execution_market_action_authorized": False,
        }
        for check in REQUIRED_PRE_APPROVAL_CHECKS
    ]


def _redaction_and_authority_requirements() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "required_before_human_approval": True,
            "passed_here": False,
            "authorizes_delivery_or_publication": False,
            "authorizes_incident_authority_claim": False,
        }
        for check in REDACTION_AND_AUTHORITY_REQUIREMENTS
    ]


def _delivery_path() -> dict[str, Any]:
    return {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "no_customer_delivery_no_publication_no_dispatch_no_incident_authority",
        "path_recorded": False,
        "customer_delivery_allowed": False,
        "publication_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "controlled_pilot_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
        "raw_transcript_authority_allowed": False,
        "emergency_response_allowed": False,
        "safety_certification_allowed": False,
        "repair_diagnosis_allowed": False,
        "repair_completion_allowed": False,
        "insurance_adjustment_allowed": False,
        "sla_uptime_allowed": False,
        "official_incident_report_allowed": False,
        "fault_or_liability_assignment_allowed": False,
    }


def build_incident_verification_human_operator_approval_request(
    *,
    artifact_dir: Path | None = None,
    source_package_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a pending, no-approval Incident Verification human-operator request."""

    source = source_package_review or _load_source_package_review(artifact_dir=artifact_dir)
    _assert_source_package_review(source)

    safe_to_claim = _dedupe(
        [
            *source.get("safe_to_claim", []),
            INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUEST_BLOCKED_CLAIMS,
            *source.get("do_not_claim_yet", []),
        ]
    )

    packet: dict[str, Any] = {
        "schema": INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
        "request_id": REQUEST_ID,
        "scope": SCOPE,
        "source_package_review_file": INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME,
        "source_package_review_schema": source["schema"],
        "source_package_review_decision_id": source["decision_id"],
        "source_package_review_digest_sha256": _canonical_digest(source),
        "source_safe_claim": INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "approval_request_status": APPROVAL_REQUEST_STATUS,
        "selected_text_boundary_count": 1,
        "selected_text_boundary": _selected_text_boundary(source),
        "pre_approval_checks": _pre_approval_checks(),
        "redaction_and_authority_requirements": _redaction_and_authority_requirements(),
        "authorized_delivery_path": _delivery_path(),
        **REQUEST_FALSE_TOP_LEVEL_FLAGS,
        "readiness": {flag: False for flag in REQUEST_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "This packet only asks a human operator to review one exact Incident "
            "Verification label boundary later. It does not record approval, create "
            "customer copy, authorize delivery, publish, launch a route/catalog/pilot/"
            "queue, dispatch workers, attach reputation, expose exact GPS/raw metadata, "
            "use raw transcripts as authority, or make emergency/safety/repair/insurance/"
            "SLA/official-report/fault-liability claims."
        ),
        "next_smallest_proof": (
            "If a human operator approves this exact boundary later, create a separate "
            "approval record that names the exact approved text, passed checks, authorized "
            "delivery path, incident-authority limitations, and still-blocked claims."
        ),
    }
    _assert_approval_request(packet)
    return packet


def _assert_approval_request(packet: dict[str, Any]) -> None:
    if packet.get("schema") != INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("incident approval request schema drift")
    if packet.get("request_id") != REQUEST_ID:
        raise CityOpsContractError("incident approval request id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("incident approval request scope drift")
    if packet.get("source_package_review_file") != INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_FILENAME:
        raise CityOpsContractError("incident approval request source file drift")
    if packet.get("source_package_review_schema") != INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("incident approval request source schema drift")
    if packet.get("source_safe_claim") != INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM:
        raise CityOpsContractError("incident approval request source safe claim drift")
    if packet.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("incident approval request family drift")
    if packet.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("incident approval request offer drift")
    if INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("incident approval request safe claim missing")
    if INCIDENT_VERIFICATION_PACKAGE_REVIEW_DECISION_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("incident approval request source safe claim missing")
    forbidden_safe = set(packet.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"incident approval request has forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(REQUEST_BLOCKED_CLAIMS) - set(packet.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"incident approval request missing blocked claims: {sorted(missing_blocked)}"
        )
    if packet.get("still_blocked_claims") != packet.get("do_not_claim_yet"):
        raise CityOpsContractError("incident approval request blocked claims drift")
    if packet.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("incident approval request status drift")
    if packet.get("selected_text_boundary_count") != 1:
        raise CityOpsContractError("incident approval request must name exactly one boundary")
    boundary = packet.get("selected_text_boundary", {})
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("incident approval request boundary key drift")
    if boundary.get("candidate_text_boundary") != "internal_package_label_only":
        raise CityOpsContractError("incident approval request boundary type drift")
    if boundary.get("candidate_text_value") != SELECTED_INTERNAL_LABEL:
        raise CityOpsContractError("incident approval request boundary value drift")
    for flag in [
        "selected_text_boundary_approved",
        "human_operator_approval_recorded",
        "customer_delivery_authorized_by_boundary",
        "publication_authorized_by_boundary",
        "emergency_safety_repair_insurance_sla_official_report_fault_or_liability_authorized_by_boundary",
        "source_customer_copy_approved",
        "source_next_gate_satisfied",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"incident approval request boundary promoted {flag}")
    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        if packet.get(flag) is not expected:
            raise CityOpsContractError(f"incident approval request promoted {flag}")
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"incident approval request promoted readiness {flag}")
        if boundary.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"incident approval request boundary promoted readiness {flag}"
            )
    if [item.get("check") for item in packet.get("pre_approval_checks", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("incident approval request pre-approval checks drift")
    for item in packet.get("pre_approval_checks", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("incident approval request pre-check not required")
        for flag in [
            "passed_here",
            "approval_granted",
            "customer_delivery_allowed",
            "publication_allowed",
            "execution_market_action_authorized",
        ]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"incident approval request pre-check promoted {flag}"
                )
    if [
        item.get("check")
        for item in packet.get("redaction_and_authority_requirements", [])
    ] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("incident approval request redaction requirements drift")
    for item in packet.get("redaction_and_authority_requirements", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("incident approval request redaction not required")
        for flag in ["passed_here", "authorizes_delivery_or_publication", "authorizes_incident_authority_claim"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"incident approval request redaction promoted {flag}"
                )
    path = packet.get("authorized_delivery_path", {})
    if path.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("incident approval request delivery path drift")
    for flag in [
        "path_recorded",
        "customer_delivery_allowed",
        "publication_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "controlled_pilot_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
        "raw_transcript_authority_allowed",
        "emergency_response_allowed",
        "safety_certification_allowed",
        "repair_diagnosis_allowed",
        "repair_completion_allowed",
        "insurance_adjustment_allowed",
        "sla_uptime_allowed",
        "official_incident_report_allowed",
        "fault_or_liability_assignment_allowed",
    ]:
        if path.get(flag) is not False:
            raise CityOpsContractError(f"incident approval request delivery path promoted {flag}")


def write_incident_verification_human_operator_approval_request(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_incident_verification_human_operator_approval_request(artifact_dir=target_dir)
    path = target_dir / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def load_incident_verification_human_operator_approval_request(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("incident approval request must be JSON object")
    _assert_approval_request(packet)
    return packet
