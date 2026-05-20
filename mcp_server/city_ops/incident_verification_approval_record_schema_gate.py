"""Incident Verification approval-record schema gate.

This module consumes the read-only Incident Verification approval-request surface
and defines the exact contract a later real human-operator approval record must
satisfy. It deliberately does not record human approval, does not pass
pre-approval checks, does not pass redaction/authority review, does not authorize
customer delivery, does not publish, does not create a public route/catalog/pilot,
does not price or launch a queue, does not dispatch, does not attach reputation,
does not prove live Acontext/runtime parity, does not expose exact GPS/raw
metadata, does not grant raw transcript authority, does not create emergency/
safety/repair/insurance/SLA/official-report/fault-liability authority, and does
not create worker-copyable incident doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .incident_verification_approval_request_read_surface import (
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
    INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SCHEMA,
    SURFACE_BLOCKED_CLAIMS as SOURCE_SURFACE_BLOCKED_CLAIMS,
    SURFACE_FALSE_FLAGS,
    load_incident_verification_approval_request_read_surface,
)
from .incident_verification_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .incident_verification_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUEST_READINESS_FALSE_FLAGS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    SELECTED_TEXT_BOUNDARY_KEY,
)

INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA = (
    "city_ops.incident_verification_approval_record_schema_gate.v1"
)
INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME = (
    "incident_verification_approval_record_schema_gate.json"
)
INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM = (
    "incident_verification_approval_record_schema_gate_landed"
)

GATE_ID = "execution_market.aas.incident_verification.approval_record_schema_gate.001"
SCOPE = "internal_admin_schema_gate_for_future_incident_verification_human_approval_record_only"
SOURCE_POLICY = "consume_only_read_only_pending_incident_verification_approval_request_surface_json"
GATE_STATUS = "schema_gate_only_no_human_approval_recorded"
FUTURE_RECORD_SCHEMA_NAME = "city_ops.incident_verification_human_operator_approval_record.v1"

FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS = [
    "source_surface_id",
    "source_request_id",
    "source_surface_digest_sha256",
    "selected_text_boundary_key",
    "approved_text_boundary",
    "exact_approved_text",
    "human_operator_approval_recorded",
    "human_operator_approval_reference",
    "approval_timestamp_utc",
    "pre_approval_checks_passed",
    "redaction_and_authority_checks_passed",
    "incident_authority_limits",
    "authorized_delivery_path",
    "approval_scope",
    "approvals_not_granted",
    "still_blocked_claims",
]

FUTURE_RECORD_MUST_KEEP_FALSE = [
    "customer_delivery_approval",
    "operator_publish_approval",
    "publication_approved",
    "public_route_ready",
    "catalog_route_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_enabled",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_incident_doctrine_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "raw_transcript_authority_allowed",
    "emergency_response_ready",
    "safety_certification_ready",
    "repair_diagnosis_ready",
    "repair_completion_ready",
    "insurance_adjustment_ready",
    "sla_uptime_ready",
    "official_incident_report_ready",
    "fault_or_liability_assignment_ready",
]

RECORD_GATE_READINESS_FALSE_FLAGS = [
    *REQUEST_READINESS_FALSE_FLAGS,
    "future_human_operator_approval_record_created",
    "human_operator_approval_recorded",
    "selected_text_boundary_approved",
    "approved_text_boundary_recorded",
    "pre_approval_checks_passed",
    "redaction_and_authority_checks_passed",
    "incident_authority_limits_recorded",
    "customer_delivery_path_authorized",
    "customer_delivery_approval_recorded",
    "operator_publish_approval_recorded",
    "publication_approved",
    "public_route_ready",
    "catalog_route_ready",
    "controlled_pilot_ready",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_enabled",
    "reputation_ready",
    "live_runtime_ready",
    "exact_gps_or_raw_metadata_release_ready",
    "raw_transcript_authority_ready",
    "incident_authority_ready",
]

REQUIRED_BLOCKED_CLAIMS = [
    *SOURCE_SURFACE_BLOCKED_CLAIMS,
    "incident_verification_future_human_operator_approval_record_created",
    "incident_verification_human_operator_approval_recorded",
    "incident_verification_selected_text_boundary_approved",
    "incident_verification_approved_text_boundary_recorded",
    "incident_verification_pre_approval_checks_passed",
    "incident_verification_redaction_and_authority_checks_passed",
    "incident_verification_incident_authority_limits_recorded",
    "incident_verification_customer_delivery_path_authorized",
    "incident_verification_customer_delivery_approval_recorded",
    "incident_verification_operator_publish_approval_recorded",
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
    "incident_verification_approval_record_publishable",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "approval_record_ready",
    "human_approved",
    "operator_approved",
    "selected_text_boundary_ready",
    "customer_copy_ready",
    "customer_delivery_ready",
    "publishable",
    "publication_ready",
    "public_route_ready",
    "catalog_ready",
    "pilot_ready",
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


def _load_source_surface(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_incident_verification_approval_request_read_surface(artifact_dir=artifact_dir)


def _cards_by_name(surface: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card.get("card"): card for card in surface.get("operator_cards", []) if isinstance(card, dict)}


def _assert_source_surface(surface: dict[str, Any]) -> None:
    if surface.get("schema") != INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("incident approval record schema gate source surface schema drift")
    if surface.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("incident approval record schema gate source family drift")
    if surface.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("incident approval record schema gate source offer drift")
    if surface.get("surface_status") != "read_only_pending_request_surface_no_human_approval_recorded":
        raise CityOpsContractError("incident approval record schema gate source status drift")
    if INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM not in surface.get("safe_to_claim", []):
        raise CityOpsContractError("incident approval record schema gate source safe claim missing")
    forbidden_safe = set(surface.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"incident approval record schema gate source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SOURCE_SURFACE_BLOCKED_CLAIMS) - set(surface.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"incident approval record schema gate source missing blocked claims: {sorted(missing_blocked)}"
        )
    if surface.get("still_blocked_claims") != surface.get("do_not_claim_yet"):
        raise CityOpsContractError("incident approval record schema gate source blocked claims drift")

    snapshot = surface.get("approval_request_snapshot", {})
    if snapshot.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("incident approval record schema gate source request status drift")
    if snapshot.get("selected_text_boundary_count") != 1:
        raise CityOpsContractError("incident approval record schema gate source must name exactly one boundary")
    if snapshot.get("selected_text_boundary_key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("incident approval record schema gate source boundary drift")
    if snapshot.get("candidate_text_boundary") != "internal_package_label_only":
        raise CityOpsContractError("incident approval record schema gate source boundary type drift")
    for flag in [
        "human_operator_approval_recorded",
        "selected_text_boundary_approved",
        "customer_delivery_authorized",
        "publication_authorized",
        "incident_authority_claim_authorized",
    ]:
        if snapshot.get(flag) is not False:
            raise CityOpsContractError(f"incident approval record schema gate source snapshot promoted {flag}")

    for flag, expected in SURFACE_FALSE_FLAGS.items():
        if surface.get(flag) is not expected:
            raise CityOpsContractError(f"incident approval record schema gate source promoted {flag}")
        if surface.get("surface_flags", {}).get(flag) is not expected:
            raise CityOpsContractError(f"incident approval record schema gate source flag summary promoted {flag}")
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"incident approval record schema gate source promoted readiness {flag}")

    access = surface.get("access_policy", {})
    if access.get("audience") != "internal_admin_only":
        raise CityOpsContractError("incident approval record schema gate source access drift")
    for flag in ["network_route_registered", "public_route_registered", "customer_visible", "worker_visible", "dispatch_enabled"]:
        if access.get(flag) is not False:
            raise CityOpsContractError(f"incident approval record schema gate source access promoted {flag}")
    if surface.get("mount_contract", {}).get("network_route_registered") is not False:
        raise CityOpsContractError("incident approval record schema gate source registered network route")

    cards = _cards_by_name(surface)
    if [item.get("check") for item in cards.get("pre_approval_checks", {}).get("values", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("incident approval record schema gate source pre-check drift")
    for item in cards.get("pre_approval_checks", {}).get("values", []):
        for flag in ["passed_here", "approval_granted", "customer_delivery_allowed", "publication_allowed", "execution_market_action_authorized"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(f"incident approval record schema gate source pre-check promoted {flag}")
    if [item.get("check") for item in cards.get("redaction_and_authority_requirements", {}).get("values", [])] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("incident approval record schema gate source redaction drift")
    for item in cards.get("redaction_and_authority_requirements", {}).get("values", []):
        for flag in ["passed_here", "authorizes_delivery_or_publication", "authorizes_incident_authority_claim"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(f"incident approval record schema gate source redaction promoted {flag}")
    delivery = cards.get("authorized_delivery_path", {}).get("values", {})
    if delivery.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("incident approval record schema gate source delivery path drift")
    for flag, value in delivery.items():
        if flag not in {"path", "authorized_for"} and value is not False:
            raise CityOpsContractError(f"incident approval record schema gate source delivery promoted {flag}")


def _future_required_field_contracts(surface: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = surface["approval_request_snapshot"]
    values = {
        "source_surface_id": surface["surface_id"],
        "source_request_id": surface["source_request_id"],
        "source_surface_digest_sha256": _canonical_digest(surface),
        "selected_text_boundary_key": snapshot["selected_text_boundary_key"],
        "approved_text_boundary": snapshot["candidate_text_boundary"],
        "exact_approved_text": snapshot["candidate_text_value"],
        "human_operator_approval_recorded": True,
        "pre_approval_checks_passed": REQUIRED_PRE_APPROVAL_CHECKS,
        "redaction_and_authority_checks_passed": REDACTION_AND_AUTHORITY_REQUIREMENTS,
        "incident_authority_limits": "must_explicitly_exclude_emergency_safety_repair_insurance_sla_official_report_fault_or_liability_authority",
        "authorized_delivery_path": "still_none_unless_a_separate_delivery_approval_gate_exists",
        "approval_scope": "incident_verification_text_boundary_only_not_customer_delivery_publication_dispatch_or_incident_authority",
        "approvals_not_granted": FUTURE_RECORD_MUST_KEEP_FALSE,
        "still_blocked_claims": REQUIRED_BLOCKED_CLAIMS,
    }
    optional_context = {
        "human_operator_approval_reference": "non_secret_operator_review_reference_required",
        "approval_timestamp_utc": "required_when_a_real_human_record_is_created",
    }
    return [
        {
            "field": field,
            "required_in_future_record": True,
            "expected_value_or_constraint": values.get(field, optional_context.get(field)),
            "satisfied_by_this_gate": False,
        }
        for field in FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS
    ]


def _pre_approval_contract() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "required_in_future_approval_record": True,
            "passed_by_this_gate": False,
            "future_record_must_include_evidence_reference": True,
            "authorizes_execution_market_action_here": False,
        }
        for check in REQUIRED_PRE_APPROVAL_CHECKS
    ]


def _redaction_and_authority_contract() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "required_in_future_approval_record": True,
            "passed_by_this_gate": False,
            "future_record_must_include_evidence_reference": True,
            "authorizes_delivery_or_publication_here": False,
            "authorizes_incident_authority_claim_here": False,
        }
        for check in REDACTION_AND_AUTHORITY_REQUIREMENTS
    ]


def build_incident_verification_approval_record_schema_gate(
    *,
    artifact_dir: Path | None = None,
    source_surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the schema gate for a later Incident Verification approval record."""

    surface = source_surface or _load_source_surface(artifact_dir=artifact_dir)
    _assert_source_surface(surface)
    snapshot = surface["approval_request_snapshot"]

    safe_to_claim = _dedupe(
        [
            *surface.get("safe_to_claim", []),
            INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*REQUIRED_BLOCKED_CLAIMS, *surface.get("do_not_claim_yet", [])])

    gate: dict[str, Any] = {
        "schema": INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA,
        "gate_id": GATE_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "source_surface_file": INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME,
        "source_surface_schema": surface["schema"],
        "source_surface_id": surface["surface_id"],
        "source_surface_digest_sha256": _canonical_digest(surface),
        "source_request_id": surface["source_request_id"],
        "source_safe_claim": INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "gate_status": GATE_STATUS,
        "future_record_schema": FUTURE_RECORD_SCHEMA_NAME,
        "future_approval_record_required_fields": _future_required_field_contracts(surface),
        "selected_text_boundary": {
            "key": snapshot["selected_text_boundary_key"],
            "package_family_id": PACKAGE_FAMILY_ID,
            "offer_id": OFFER_ID,
            "candidate_text_boundary": snapshot["candidate_text_boundary"],
            "candidate_text_value": snapshot["candidate_text_value"],
            "selected_text_boundary_approved_here": False,
            "human_operator_approval_recorded_here": False,
            "incident_authority_claim_authorized_here": False,
        },
        "pre_approval_contract": _pre_approval_contract(),
        "redaction_and_authority_contract": _redaction_and_authority_contract(),
        "current_gate_values": {
            "human_operator_approval_recorded": False,
            "selected_text_boundary_approved": False,
            "approved_text_boundary_recorded": False,
            "pre_approval_checks_passed": False,
            "redaction_and_authority_checks_passed": False,
            "incident_authority_claim_authorized": False,
            "authorized_delivery_path": AUTHORIZED_DELIVERY_PATH,
            "customer_delivery_path_authorized": False,
            "operator_publish_approval_recorded": False,
            "publication_approved": False,
        },
        "future_record_must_keep_false": FUTURE_RECORD_MUST_KEEP_FALSE,
        "readiness": {flag: False for flag in RECORD_GATE_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this as the schema gate for a later real Incident Verification human approval record only. "
            "Do not treat this gate as approval. A future record must cite the pending request surface, name "
            "the exact approved text, include evidence references for every pre-approval and redaction/authority "
            "check, explicitly exclude incident authority claims, and keep delivery/publication/routes/pricing/"
            "queues/dispatch/reputation/runtime/GPS/raw metadata/raw transcript authority/worker doctrine blocked "
            "unless separate gates prove them."
        ),
        "next_smallest_proof": (
            "A real human operator may later create one approval record for this exact Incident Verification "
            "package-label boundary. That record still must not authorize customer delivery, publication, pricing, "
            "routes, queues, dispatch, reputation, live runtime, GPS/raw metadata release, raw transcript authority, "
            "emergency/safety/repair/insurance/SLA/official-report/fault-liability claims, or worker-copyable doctrine."
        ),
    }
    _assert_gate(gate, source_surface=surface)
    return gate


def _assert_gate(gate: dict[str, Any], *, source_surface: dict[str, Any]) -> None:
    _assert_source_surface(source_surface)
    if gate.get("schema") != INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("incident approval record schema gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("incident approval record schema gate id drift")
    if gate.get("scope") != SCOPE:
        raise CityOpsContractError("incident approval record schema gate scope drift")
    if gate.get("source_surface_file") != INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_FILENAME:
        raise CityOpsContractError("incident approval record schema gate source file drift")
    if gate.get("source_surface_schema") != INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("incident approval record schema gate source schema drift")
    if gate.get("source_surface_id") != source_surface.get("surface_id"):
        raise CityOpsContractError("incident approval record schema gate source id mismatch")
    if gate.get("source_surface_digest_sha256") != _canonical_digest(source_surface):
        raise CityOpsContractError("incident approval record schema gate source digest drift")
    if gate.get("source_safe_claim") != INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM:
        raise CityOpsContractError("incident approval record schema gate source safe claim drift")
    if INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("incident approval record schema gate safe claim missing")
    if INCIDENT_VERIFICATION_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("incident approval record schema gate source safe claim missing")
    forbidden_safe = set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"incident approval record schema gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    overlap = set(gate.get("safe_to_claim", [])) & set(gate.get("do_not_claim_yet", []))
    if overlap:
        raise CityOpsContractError(f"incident approval record schema gate claim overlap: {sorted(overlap)}")
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(gate.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"incident approval record schema gate missing blocked claims: {sorted(missing_blocked)}"
        )
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("incident approval record schema gate status drift")
    if gate.get("future_record_schema") != FUTURE_RECORD_SCHEMA_NAME:
        raise CityOpsContractError("incident approval record schema gate future schema drift")

    fields = gate.get("future_approval_record_required_fields", [])
    if [field.get("field") for field in fields] != FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS:
        raise CityOpsContractError("incident approval record schema gate required fields drift")
    for field in fields:
        if field.get("required_in_future_record") is not True:
            raise CityOpsContractError("incident approval record schema gate field not required")
        if field.get("satisfied_by_this_gate") is not False:
            raise CityOpsContractError("incident approval record schema gate satisfied a future field")

    boundary = gate.get("selected_text_boundary", {})
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("incident approval record schema gate selected boundary drift")
    for flag in [
        "selected_text_boundary_approved_here",
        "human_operator_approval_recorded_here",
        "incident_authority_claim_authorized_here",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"incident approval record schema gate promoted boundary {flag}")

    if [item.get("check") for item in gate.get("pre_approval_contract", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("incident approval record schema gate pre-approval contract drift")
    for item in gate.get("pre_approval_contract", []):
        if item.get("required_in_future_approval_record") is not True:
            raise CityOpsContractError("incident approval record schema gate pre-check not required")
        for flag in ["passed_by_this_gate", "authorizes_execution_market_action_here"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(f"incident approval record schema gate promoted pre-check {flag}")
    if [item.get("check") for item in gate.get("redaction_and_authority_contract", [])] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("incident approval record schema gate redaction contract drift")
    for item in gate.get("redaction_and_authority_contract", []):
        if item.get("required_in_future_approval_record") is not True:
            raise CityOpsContractError("incident approval record schema gate redaction not required")
        for flag in ["passed_by_this_gate", "authorizes_delivery_or_publication_here", "authorizes_incident_authority_claim_here"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(f"incident approval record schema gate promoted redaction {flag}")

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
            raise CityOpsContractError(f"incident approval record schema gate promoted current value {flag}")
    if current.get("authorized_delivery_path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("incident approval record schema gate delivery path drift")
    if gate.get("future_record_must_keep_false") != FUTURE_RECORD_MUST_KEEP_FALSE:
        raise CityOpsContractError("incident approval record schema gate false-flag contract drift")
    for flag in RECORD_GATE_READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"incident approval record schema gate promoted readiness {flag}")
    if gate.get("still_blocked_claims") != gate.get("do_not_claim_yet"):
        raise CityOpsContractError("incident approval record schema gate blocked claims drift")
    _assert_no_private_coordinate_or_authority_overclaim(gate)


def _assert_no_private_coordinate_or_authority_overclaim(gate: dict[str, Any]) -> None:
    serialized = json.dumps(gate, sort_keys=True).lower()
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
                "incident approval record schema gate leaked coordinate/private authority overclaim"
            )


def write_incident_verification_approval_record_schema_gate(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_incident_verification_approval_record_schema_gate(artifact_dir=target_dir)
    path = target_dir / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    return path


def load_incident_verification_approval_record_schema_gate(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_APPROVAL_RECORD_SCHEMA_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    if not isinstance(gate, dict):
        raise CityOpsContractError("incident approval record schema gate must be JSON object")
    _assert_gate(gate, source_surface=_load_source_surface(artifact_dir=source_dir))
    return gate
