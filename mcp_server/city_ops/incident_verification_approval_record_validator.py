"""Validator for a future Incident Verification human approval record.

This module is the conservative rung after the Incident Verification approval-
record schema gate. It creates an internal/admin validator artifact and a
callable validator for a later real human-created approval record. It does not
create or imply human approval, does not approve customer copy or delivery, does
not publish, does not create routes/catalog/pilots, does not price or launch a
queue, does not dispatch, does not attach reputation, does not prove live
Acontext/runtime parity, does not expose exact GPS/raw metadata, does not grant
raw transcript authority, does not create emergency/safety/repair/insurance/SLA/
official-report/fault-liability authority, and does not create worker-copyable
incident doctrine.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .incident_verification_approval_record_schema_gate import (
    FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    FUTURE_RECORD_MUST_KEEP_FALSE,
    FUTURE_RECORD_SCHEMA_NAME,
    GATE_ID,
    GATE_STATUS,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
    INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA,
    RECORD_GATE_READINESS_FALSE_FLAGS,
    REQUIRED_BLOCKED_CLAIMS as SCHEMA_GATE_REQUIRED_BLOCKED_CLAIMS,
    build_incident_verification_approval_record_schema_gate,
    load_incident_verification_approval_record_schema_gate,
)
from .incident_verification_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .incident_verification_human_operator_approval_request import (
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    SELECTED_TEXT_BOUNDARY_KEY,
)

INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SCHEMA = (
    "city_ops.incident_verification_approval_record_validator.v1"
)
INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME = (
    "incident_verification_approval_record_validator.json"
)
INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM = (
    "incident_verification_approval_record_validator_landed"
)

VALIDATOR_ID = "execution_market.aas.incident_verification.approval_record_validator.001"
SCOPE = "internal_admin_validator_for_future_incident_verification_human_approval_record_only"
SOURCE_POLICY = "consume_only_incident_verification_approval_record_schema_gate_json"
VALIDATOR_STATUS = "validator_contract_only_no_human_approval_record_created"
APPROVAL_RECORD_ALLOWED_STATUS = "human_operator_approved_incident_verification_text_boundary_only"
APPROVAL_RECORD_ALLOWED_SCOPE = (
    "incident_verification_text_boundary_only_not_customer_delivery_publication_dispatch_or_incident_authority"
)
APPROVAL_RECORD_ALLOWED_DELIVERY_PATH = "still_none_unless_a_separate_delivery_approval_gate_exists"
INCIDENT_AUTHORITY_LIMITS = (
    "must_explicitly_exclude_emergency_safety_repair_insurance_sla_official_report_fault_or_liability_authority"
)

VALIDATOR_READINESS_FALSE_FLAGS = [
    *RECORD_GATE_READINESS_FALSE_FLAGS,
    "validator_created_human_approval_record",
    "validator_approves_selected_boundary",
    "validator_passes_pre_approval_checks",
    "validator_passes_redaction_or_authority_checks",
    "validator_authorizes_customer_delivery",
    "validator_authorizes_publication",
    "validator_authorizes_public_route_or_catalog",
    "validator_authorizes_public_price_or_customer_quote",
    "validator_launches_operator_queue",
    "validator_enables_dispatch",
    "validator_attaches_reputation",
    "validator_proves_live_runtime_or_acontext_parity",
    "validator_allows_exact_gps_or_raw_metadata_release",
    "validator_grants_raw_transcript_authority",
    "validator_grants_incident_authority",
    "validator_creates_worker_incident_doctrine",
]

REQUIRED_BLOCKED_CLAIMS = [
    *SCHEMA_GATE_REQUIRED_BLOCKED_CLAIMS,
    "incident_verification_approval_record_created_by_validator",
    "incident_verification_approval_record_accepted_without_human_reference",
    "incident_verification_approval_record_accepted_without_precheck_evidence",
    "incident_verification_approval_record_accepted_without_redaction_authority_evidence",
    "incident_verification_approval_record_authorizes_customer_delivery",
    "incident_verification_approval_record_authorizes_publication",
    "incident_verification_approval_record_authorizes_public_route_or_catalog",
    "incident_verification_approval_record_authorizes_public_price_or_customer_quote",
    "incident_verification_approval_record_authorizes_operator_queue_launch",
    "incident_verification_approval_record_authorizes_dispatch",
    "incident_verification_approval_record_authorizes_reputation",
    "incident_verification_approval_record_authorizes_live_runtime_or_acontext",
    "incident_verification_approval_record_authorizes_exact_gps_or_raw_metadata_release",
    "incident_verification_approval_record_authorizes_raw_transcript_authority",
    "incident_verification_approval_record_authorizes_emergency_safety_repair_insurance_sla_official_report_fault_liability",
    "incident_verification_approval_record_authorizes_worker_copyable_incident_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "approval_record_ready",
    "human_approved",
    "operator_approved",
    "selected_text_boundary_ready",
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "pilot_ready",
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

APPROVAL_RECORD_REQUIRED_FIELDS = [
    "schema",
    "record_status",
    "source_gate_id",
    "source_gate_digest_sha256",
    "source_safe_claim",
    *FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    "future_record_must_keep_false",
]

REJECT_IF_FIELDS_TRUE = [
    *FUTURE_RECORD_MUST_KEEP_FALSE,
    "customer_copy_created",
    "customer_copy_ready",
    "customer_delivery_authorized",
    "customer_delivery_path_authorized",
    "customer_delivery_approval",
    "customer_delivery_approved",
    "operator_publish_approval",
    "publication_ready",
    "publication_approved",
    "publishable",
    "public_route_ready",
    "catalog_route_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "public_price_ready",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "dispatch_enabled",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "reputation_receipt_attachable",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "exact_gps_or_raw_metadata_release_ready",
    "raw_transcript_authority_allowed",
    "raw_transcript_authority_ready",
    "emergency_response_ready",
    "safety_certification_ready",
    "repair_diagnosis_ready",
    "repair_completion_ready",
    "insurance_adjustment_ready",
    "sla_uptime_ready",
    "official_incident_report_ready",
    "fault_or_liability_assignment_ready",
    "worker_skill_dna_ready",
    "worker_copyable_incident_doctrine_ready",
    "worker_copyable_doctrine_ready",
]


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


def _load_source_gate(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_incident_verification_approval_record_schema_gate(artifact_dir=artifact_dir)


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("incident approval record validator source schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("incident approval record validator source gate id drift")
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("incident approval record validator source gate status drift")
    if gate.get("source_surface_id") == "":
        raise CityOpsContractError("incident approval record validator source surface missing")
    if INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("incident approval record validator source safe claim missing")
    forbidden_safe = set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"incident approval record validator source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SCHEMA_GATE_REQUIRED_BLOCKED_CLAIMS) - set(gate.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"incident approval record validator source missing blocked claims: {sorted(missing_blocked)}"
        )
    if gate.get("still_blocked_claims") != gate.get("do_not_claim_yet"):
        raise CityOpsContractError("incident approval record validator source blocked claims drift")
    if gate.get("future_record_schema") != FUTURE_RECORD_SCHEMA_NAME:
        raise CityOpsContractError("incident approval record validator source future schema drift")

    boundary = gate.get("selected_text_boundary", {})
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("incident approval record validator source selected boundary drift")
    if boundary.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("incident approval record validator source family drift")
    if boundary.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("incident approval record validator source offer drift")
    if boundary.get("candidate_text_boundary") != "internal_package_label_only":
        raise CityOpsContractError("incident approval record validator source boundary type drift")
    if boundary.get("candidate_text_value") != "One-location incident state snapshot":
        raise CityOpsContractError("incident approval record validator source text drift")
    for flag in [
        "selected_text_boundary_approved_here",
        "human_operator_approval_recorded_here",
        "incident_authority_claim_authorized_here",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"incident approval record validator source promoted boundary {flag}")

    fields = gate.get("future_approval_record_required_fields", [])
    if [field.get("field") for field in fields] != FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS:
        raise CityOpsContractError("incident approval record validator source field contract drift")
    for field in fields:
        if field.get("satisfied_by_this_gate") is not False:
            raise CityOpsContractError("incident approval record validator source satisfied future field")
    if [item.get("check") for item in gate.get("pre_approval_contract", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("incident approval record validator source pre-check contract drift")
    for item in gate.get("pre_approval_contract", []):
        if item.get("passed_by_this_gate") is not False:
            raise CityOpsContractError("incident approval record validator source passed pre-check")
        if item.get("authorizes_execution_market_action_here") is not False:
            raise CityOpsContractError("incident approval record validator source authorized execution action")
    if [item.get("check") for item in gate.get("redaction_and_authority_contract", [])] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("incident approval record validator source redaction contract drift")
    for item in gate.get("redaction_and_authority_contract", []):
        if item.get("passed_by_this_gate") is not False:
            raise CityOpsContractError("incident approval record validator source passed redaction")
        if item.get("authorizes_incident_authority_claim_here") is not False:
            raise CityOpsContractError("incident approval record validator source authorized incident authority")

    current = gate.get("current_gate_values", {})
    for flag in [
        "human_operator_approval_recorded",
        "selected_text_boundary_approved",
        "approved_text_boundary_recorded",
        "pre_approval_checks_passed",
        "redaction_and_authority_checks_passed",
        "incident_authority_claim_authorized",
        "customer_delivery_path_authorized",
        "operator_publish_approval_recorded",
        "publication_approved",
    ]:
        if current.get(flag) is not False:
            raise CityOpsContractError(f"incident approval record validator source promoted current value {flag}")
    if current.get("authorized_delivery_path") != "none_until_separate_human_operator_approval_record":
        raise CityOpsContractError("incident approval record validator source current delivery drift")
    if gate.get("future_record_must_keep_false") != FUTURE_RECORD_MUST_KEEP_FALSE:
        raise CityOpsContractError("incident approval record validator source false-flag contract drift")
    for flag in RECORD_GATE_READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"incident approval record validator source promoted readiness {flag}")


def _record_field_contract() -> list[dict[str, Any]]:
    return [
        {
            "field": field,
            "required_for_future_human_record": True,
            "satisfied_by_validator_artifact": False,
        }
        for field in APPROVAL_RECORD_REQUIRED_FIELDS
    ]


def _precheck_evidence_contract() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "future_record_must_mark_passed": True,
            "future_record_must_include_evidence_reference": True,
            "satisfied_by_validator_artifact": False,
        }
        for check in REQUIRED_PRE_APPROVAL_CHECKS
    ]


def _redaction_authority_evidence_contract() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "future_record_must_mark_passed": True,
            "future_record_must_include_evidence_reference": True,
            "future_record_must_authorize_delivery_or_publication": False,
            "future_record_must_authorize_incident_authority_claim": False,
            "satisfied_by_validator_artifact": False,
        }
        for check in REDACTION_AND_AUTHORITY_REQUIREMENTS
    ]


def build_incident_verification_approval_record_validator(
    *,
    artifact_dir: Path | None = None,
    source_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an internal/admin validator contract for a future approval record."""

    gate = source_gate or _load_source_gate(artifact_dir=artifact_dir)
    _assert_source_gate(gate)
    boundary = gate["selected_text_boundary"]

    safe_to_claim = _dedupe(
        [
            *gate.get("safe_to_claim", []),
            INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*REQUIRED_BLOCKED_CLAIMS, *gate.get("do_not_claim_yet", [])])

    validator = {
        "schema": INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SCHEMA,
        "validator_id": VALIDATOR_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "source_gate_file": INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
        "source_gate_schema": gate["schema"],
        "source_gate_id": gate["gate_id"],
        "source_gate_digest_sha256": _canonical_digest(gate),
        "source_safe_claim": INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "validator_status": VALIDATOR_STATUS,
        "future_record_schema": FUTURE_RECORD_SCHEMA_NAME,
        "allowed_record_status": APPROVAL_RECORD_ALLOWED_STATUS,
        "allowed_approval_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "allowed_delivery_path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
        "required_incident_authority_limits": INCIDENT_AUTHORITY_LIMITS,
        "selected_text_boundary": {
            "key": boundary["key"],
            "package_family_id": boundary["package_family_id"],
            "offer_id": boundary["offer_id"],
            "approved_text_boundary_must_equal": boundary["candidate_text_boundary"],
            "exact_approved_text_must_equal": boundary["candidate_text_value"],
        },
        "record_field_contract": _record_field_contract(),
        "precheck_evidence_contract": _precheck_evidence_contract(),
        "redaction_authority_evidence_contract": _redaction_authority_evidence_contract(),
        "future_record_must_keep_false": FUTURE_RECORD_MUST_KEEP_FALSE,
        "reject_if_fields_true": REJECT_IF_FIELDS_TRUE,
        "readiness": {flag: False for flag in VALIDATOR_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this validator before accepting any future human-created Incident Verification approval record. "
            "It may only accept the exact package-label boundary `One-location incident state snapshot`. "
            "The validator must reject customer delivery, publication, routes, catalog, pilot, pricing, queue, "
            "dispatch, reputation, live runtime, exact GPS/raw metadata, raw transcript authority, emergency/safety/"
            "repair/insurance/SLA/official-report/fault-liability authority, and worker-copyable incident doctrine. "
            "This artifact itself creates no approval record."
        ),
    }
    _assert_validator(validator)
    return validator


def _assert_validator(validator: dict[str, Any]) -> None:
    if validator.get("schema") != INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SCHEMA:
        raise CityOpsContractError("incident approval record validator schema drift")
    if validator.get("validator_id") != VALIDATOR_ID:
        raise CityOpsContractError("incident approval record validator id drift")
    if validator.get("scope") != SCOPE:
        raise CityOpsContractError("incident approval record validator scope drift")
    if validator.get("validator_status") != VALIDATOR_STATUS:
        raise CityOpsContractError("incident approval record validator status drift")
    if validator.get("source_gate_file") != INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME:
        raise CityOpsContractError("incident approval record validator source file drift")
    if validator.get("source_gate_schema") != INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("incident approval record validator source schema drift")
    if validator.get("source_gate_id") != GATE_ID:
        raise CityOpsContractError("incident approval record validator source id drift")
    if validator.get("source_safe_claim") != INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM:
        raise CityOpsContractError("incident approval record validator source safe claim drift")
    if INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM not in validator.get("safe_to_claim", []):
        raise CityOpsContractError("incident approval record validator safe claim missing")
    if INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM not in validator.get("safe_to_claim", []):
        raise CityOpsContractError("incident approval record validator source safe claim missing")
    forbidden_safe = set(validator.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"incident approval record validator forbidden safe claims: {sorted(forbidden_safe)}"
        )
    overlap = set(validator.get("safe_to_claim", [])) & set(validator.get("do_not_claim_yet", []))
    if overlap:
        raise CityOpsContractError(
            f"incident approval record validator claim overlap: {sorted(overlap)}"
        )
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(validator.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"incident approval record validator missing blocked claims: {sorted(missing_blocked)}"
        )
    if validator.get("future_record_schema") != FUTURE_RECORD_SCHEMA_NAME:
        raise CityOpsContractError("incident approval record validator future schema drift")
    if validator.get("allowed_record_status") != APPROVAL_RECORD_ALLOWED_STATUS:
        raise CityOpsContractError("incident approval record validator allowed status drift")
    if validator.get("allowed_approval_scope") != APPROVAL_RECORD_ALLOWED_SCOPE:
        raise CityOpsContractError("incident approval record validator approval scope drift")
    if validator.get("allowed_delivery_path") != APPROVAL_RECORD_ALLOWED_DELIVERY_PATH:
        raise CityOpsContractError("incident approval record validator delivery path drift")
    if validator.get("required_incident_authority_limits") != INCIDENT_AUTHORITY_LIMITS:
        raise CityOpsContractError("incident approval record validator authority limits drift")

    boundary = validator.get("selected_text_boundary", {})
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("incident approval record validator selected boundary drift")
    if boundary.get("exact_approved_text_must_equal") != "One-location incident state snapshot":
        raise CityOpsContractError("incident approval record validator exact text drift")
    if [field.get("field") for field in validator.get("record_field_contract", [])] != APPROVAL_RECORD_REQUIRED_FIELDS:
        raise CityOpsContractError("incident approval record validator field contract drift")
    for field in validator.get("record_field_contract", []):
        if field.get("satisfied_by_validator_artifact") is not False:
            raise CityOpsContractError("incident approval record validator satisfies future field")
    if [item.get("check") for item in validator.get("precheck_evidence_contract", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("incident approval record validator precheck contract drift")
    for item in validator.get("precheck_evidence_contract", []):
        if item.get("satisfied_by_validator_artifact") is not False:
            raise CityOpsContractError("incident approval record validator satisfies precheck evidence")
    if [item.get("check") for item in validator.get("redaction_authority_evidence_contract", [])] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("incident approval record validator redaction authority contract drift")
    for item in validator.get("redaction_authority_evidence_contract", []):
        if item.get("satisfied_by_validator_artifact") is not False:
            raise CityOpsContractError("incident approval record validator satisfies redaction authority evidence")
        if item.get("future_record_must_authorize_delivery_or_publication") is not False:
            raise CityOpsContractError("incident approval record validator allows delivery/publication authority")
        if item.get("future_record_must_authorize_incident_authority_claim") is not False:
            raise CityOpsContractError("incident approval record validator allows incident authority")
    if validator.get("future_record_must_keep_false") != FUTURE_RECORD_MUST_KEEP_FALSE:
        raise CityOpsContractError("incident approval record validator false-flag contract drift")
    for flag in VALIDATOR_READINESS_FALSE_FLAGS:
        if validator.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"incident approval record validator promoted readiness {flag}")
    if validator.get("still_blocked_claims") != validator.get("do_not_claim_yet"):
        raise CityOpsContractError("incident approval record validator blocked claims drift")
    _assert_no_private_coordinate_or_authority_overclaim(validator)


def _assert_timestamp_utc(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CityOpsContractError("incident approval record timestamp must be UTC Z string")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise CityOpsContractError("incident approval record timestamp invalid") from exc


def _assert_non_empty_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CityOpsContractError(f"incident approval record missing {field}")


def _assert_passed_check_list(
    values: Any,
    expected_checks: list[str],
    *,
    field: str,
    authority_fields_must_remain_false: bool = False,
) -> None:
    if not isinstance(values, list):
        raise CityOpsContractError(f"incident approval record {field} must be a list")
    if [item.get("check") for item in values] != expected_checks:
        raise CityOpsContractError(f"incident approval record {field} drift")
    for item in values:
        if item.get("passed") is not True:
            raise CityOpsContractError(f"incident approval record {field} check not passed")
        _assert_non_empty_string(item.get("evidence_reference"), f"{field} evidence reference")
        if authority_fields_must_remain_false:
            for flag in [
                "authorizes_delivery_or_publication",
                "authorizes_incident_authority_claim",
                "authorizes_execution_market_action",
            ]:
                if item.get(flag) is True:
                    raise CityOpsContractError(f"incident approval record forbidden authority {flag}")


def validate_incident_verification_human_operator_approval_record(
    record: dict[str, Any],
    *,
    artifact_dir: Path | None = None,
    source_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a future human-created Incident Verification approval record."""

    if not isinstance(record, dict):
        raise CityOpsContractError("incident approval record must be a JSON object")
    gate = source_gate or _load_source_gate(artifact_dir=artifact_dir)
    _assert_source_gate(gate)
    boundary = gate["selected_text_boundary"]
    expected_gate_digest = _canonical_digest(gate)

    missing_fields = [field for field in APPROVAL_RECORD_REQUIRED_FIELDS if field not in record]
    if missing_fields:
        raise CityOpsContractError(f"incident approval record missing required fields: {missing_fields}")
    if record.get("schema") != FUTURE_RECORD_SCHEMA_NAME:
        raise CityOpsContractError("incident approval record schema drift")
    if record.get("record_status") != APPROVAL_RECORD_ALLOWED_STATUS:
        raise CityOpsContractError("incident approval record status not allowed")
    if record.get("source_gate_id") != GATE_ID:
        raise CityOpsContractError("incident approval record source gate id drift")
    if record.get("source_gate_digest_sha256") != expected_gate_digest:
        raise CityOpsContractError("incident approval record source gate digest drift")
    if record.get("source_safe_claim") != INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM:
        raise CityOpsContractError("incident approval record source safe claim drift")
    if record.get("source_surface_id") != gate.get("source_surface_id"):
        raise CityOpsContractError("incident approval record source surface id drift")
    if record.get("source_request_id") != gate.get("source_request_id"):
        raise CityOpsContractError("incident approval record source request id drift")
    if record.get("source_surface_digest_sha256") != gate.get("source_surface_digest_sha256"):
        raise CityOpsContractError("incident approval record source surface digest drift")
    if record.get("selected_text_boundary_key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("incident approval record selected boundary drift")
    if record.get("approved_text_boundary") != boundary["candidate_text_boundary"]:
        raise CityOpsContractError("incident approval record approved boundary drift")
    if record.get("exact_approved_text") != boundary["candidate_text_value"]:
        raise CityOpsContractError("incident approval record approved text drift")
    if record.get("human_operator_approval_recorded") is not True:
        raise CityOpsContractError("incident approval record must record human approval")
    _assert_non_empty_string(
        record.get("human_operator_approval_reference"),
        "human_operator_approval_reference",
    )
    _assert_timestamp_utc(record.get("approval_timestamp_utc"))
    if record.get("authorized_delivery_path") != APPROVAL_RECORD_ALLOWED_DELIVERY_PATH:
        raise CityOpsContractError("incident approval record delivery path not allowed")
    if record.get("approval_scope") != APPROVAL_RECORD_ALLOWED_SCOPE:
        raise CityOpsContractError("incident approval record approval scope not allowed")
    if record.get("incident_authority_limits") != INCIDENT_AUTHORITY_LIMITS:
        raise CityOpsContractError("incident approval record authority limits drift")

    _assert_passed_check_list(
        record.get("pre_approval_checks_passed"),
        REQUIRED_PRE_APPROVAL_CHECKS,
        field="pre_approval_checks_passed",
    )
    _assert_passed_check_list(
        record.get("redaction_and_authority_checks_passed"),
        REDACTION_AND_AUTHORITY_REQUIREMENTS,
        field="redaction_and_authority_checks_passed",
        authority_fields_must_remain_false=True,
    )

    approvals_not_granted = record.get("approvals_not_granted")
    if not isinstance(approvals_not_granted, list):
        raise CityOpsContractError("incident approval record approvals_not_granted must be a list")
    missing_false_flags = set(FUTURE_RECORD_MUST_KEEP_FALSE) - set(approvals_not_granted)
    if missing_false_flags:
        raise CityOpsContractError(
            f"incident approval record missing approvals not granted: {sorted(missing_false_flags)}"
        )
    false_map = record.get("future_record_must_keep_false")
    if not isinstance(false_map, dict):
        raise CityOpsContractError("incident approval record false flags must be an object")
    for flag in FUTURE_RECORD_MUST_KEEP_FALSE:
        if false_map.get(flag) is not False:
            raise CityOpsContractError(f"incident approval record promoted false flag {flag}")
    for flag in REJECT_IF_FIELDS_TRUE:
        if record.get(flag) is True:
            raise CityOpsContractError(f"incident approval record forbidden promotion {flag}")
    still_blocked = record.get("still_blocked_claims")
    if not isinstance(still_blocked, list):
        raise CityOpsContractError("incident approval record still_blocked_claims must be a list")
    missing_blocked = set(gate.get("still_blocked_claims", [])) - set(still_blocked)
    if missing_blocked:
        raise CityOpsContractError(
            f"incident approval record missing still blocked claims: {sorted(missing_blocked)}"
        )
    _assert_no_private_coordinate_or_authority_overclaim(record)
    return {
        "record_valid": True,
        "validated_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "selected_text_boundary_key": SELECTED_TEXT_BOUNDARY_KEY,
        "exact_text_approved": boundary["candidate_text_value"],
        "customer_delivery_authorized": False,
        "publication_authorized": False,
        "dispatch_authorized": False,
        "reputation_authorized": False,
        "runtime_or_acontext_authorized": False,
        "incident_authority_authorized": False,
        "exact_gps_or_raw_metadata_authorized": False,
        "raw_transcript_authority_authorized": False,
    }


def _assert_no_private_coordinate_or_authority_overclaim(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True).lower()
    forbidden_substrings = [
        "latitude",
        "longitude",
        "gps:",
        "dispatch now",
        "emergency response dispatched",
        "safety certified",
        "repair diagnosed",
        "repair completed",
        "insurance adjustment approved",
        "sla guaranteed",
        "official incident report issued",
        "fault assigned",
        "liability assigned",
        "driver license",
        "passport",
    ]
    for substring in forbidden_substrings:
        if substring in serialized:
            raise CityOpsContractError(
                "incident approval record validator leaked coordinate/private authority overclaim"
            )


def write_incident_verification_approval_record_validator(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    validator = build_incident_verification_approval_record_validator(artifact_dir=target_dir)
    path = target_dir / INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME
    path.write_text(json.dumps(validator, indent=2) + "\n", encoding="utf-8")
    return path


def load_incident_verification_approval_record_validator(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_APPROVAL_RECORD_VALIDATOR_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        validator = json.load(fh)
    if not isinstance(validator, dict):
        raise CityOpsContractError("incident approval record validator must be JSON object")
    _assert_validator(validator)
    return validator
