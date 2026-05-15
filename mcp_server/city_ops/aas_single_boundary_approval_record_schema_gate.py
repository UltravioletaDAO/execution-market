"""Schema gate for a future single-boundary AAS approval record.

This module consumes the pending single-boundary human-operator approval
request and defines the exact shape a later human approval record must satisfy.
It deliberately does not record human approval, does not pass redactions, does
not authorize customer delivery, does not publish, does not create a public
route, does not approve pricing, does not launch an operator queue, does not
dispatch, does not attach reputation, does not prove live Acontext/runtime
parity, and does not expose exact GPS/raw metadata or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_single_boundary_human_operator_approval_request import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    REQUIRED_BLOCKED_CLAIMS as REQUEST_REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_REDACTION_CHECKS,
    REQUEST_ID,
    REQUEST_READINESS_FALSE_FLAGS,
    SELECTED_BOUNDARY_KEY,
    build_aas_single_boundary_human_operator_approval_request,
    load_aas_single_boundary_human_operator_approval_request,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA = (
    "city_ops.aas_single_boundary_approval_record_schema_gate.v1"
)
AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME = (
    "aas_single_boundary_approval_record_schema_gate.json"
)
AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM = (
    "aas_single_boundary_approval_record_schema_gate_landed"
)

GATE_ID = "execution_market.aas.single_boundary_approval_record_schema_gate.001"
SCOPE = "internal_admin_schema_gate_for_future_human_approval_record_only"
SOURCE_POLICY = "consume_only_pending_single_boundary_human_operator_approval_request_json"
GATE_STATUS = "schema_gate_only_no_human_approval_recorded"
FUTURE_RECORD_SCHEMA_NAME = "city_ops.aas_single_boundary_human_operator_approval_record.v1"

RECORD_GATE_READINESS_FALSE_FLAGS = [
    *REQUEST_READINESS_FALSE_FLAGS,
    "future_human_operator_approval_record_created",
    "human_operator_approval_recorded",
    "selected_boundary_approved",
    "approved_text_boundary_recorded",
    "redaction_checks_passed",
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
]

REQUIRED_BLOCKED_CLAIMS = [
    *REQUEST_REQUIRED_BLOCKED_CLAIMS,
    "future_human_operator_approval_record_created",
    "human_operator_approval_recorded",
    "selected_boundary_approved",
    "approved_text_boundary_recorded",
    "redaction_checks_passed",
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
    "approval_record_publishable",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "approval_record_ready",
    "human_approved",
    "operator_approved",
    "selected_boundary_ready",
    "customer_copy_ready",
    "customer_delivery_ready",
    "publishable",
    "publication_ready",
    "public_route_ready",
    "catalog_ready",
    "pilot_ready",
    "dispatch_ready",
    "reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
}

FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS = [
    "source_request_id",
    "source_request_digest_sha256",
    "selected_boundary_key",
    "approved_text_boundary",
    "exact_approved_text",
    "approved_text_fields",
    "human_operator_approval_recorded",
    "human_operator_approval_reference",
    "approval_timestamp_utc",
    "redaction_checks_passed",
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
    "worker_copyable_doctrine_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "domain_authority_claims_allowed",
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


def _load_source_request(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_single_boundary_human_operator_approval_request(
        artifact_dir=artifact_dir
    )


def _assert_source_request(request: dict[str, Any]) -> None:
    if request.get("schema") != AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("approval record schema gate source request schema drift")
    if request.get("request_id") != REQUEST_ID:
        raise CityOpsContractError("approval record schema gate source request id drift")
    if request.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("approval record schema gate source request status drift")
    if AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in request.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval record schema gate source request safe claim missing")
    forbidden_safe = set(request.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval record schema gate source request forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(REQUEST_REQUIRED_BLOCKED_CLAIMS) - set(
        request.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"approval record schema gate source request missing blocked claims: {sorted(missing_blocked)}"
        )
    if request.get("human_operator_approval_recorded") is not False:
        raise CityOpsContractError("approval record schema gate source already records approval")
    if request.get("selected_boundary_count") != 1:
        raise CityOpsContractError("approval record schema gate source must name exactly one boundary")
    boundary = request.get("selected_boundary", {})
    if boundary.get("key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("approval record schema gate source selected boundary drift")
    if boundary.get("selected_boundary_approved") is not False:
        raise CityOpsContractError("approval record schema gate source selected boundary approved")
    if boundary.get("human_operator_approval_recorded") is not False:
        raise CityOpsContractError("approval record schema gate source boundary records approval")
    for item in request.get("redaction_requirements", []):
        if item.get("passed_here") is not False:
            raise CityOpsContractError("approval record schema gate source passed redactions")
    if [item.get("check") for item in request.get("redaction_requirements", [])] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("approval record schema gate source redaction requirements drift")
    delivery = request.get("authorized_delivery_path", {})
    if delivery.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("approval record schema gate source delivery path drift")
    for field in [
        "customer_delivery_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
    ]:
        if delivery.get(field) is not False:
            raise CityOpsContractError(f"approval record schema gate source promoted {field}")
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if request.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"approval record schema gate source promoted readiness {flag}")
        if boundary.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"approval record schema gate source boundary promoted readiness {flag}"
            )


def _future_required_field_contracts(request: dict[str, Any]) -> list[dict[str, Any]]:
    boundary = request["selected_boundary"]
    values = {
        "source_request_id": request["request_id"],
        "source_request_digest_sha256": _canonical_digest(request),
        "selected_boundary_key": boundary["key"],
        "approved_text_boundary": boundary["candidate_text_boundary"],
        "exact_approved_text": boundary["candidate_text_value"],
        "approved_text_fields": boundary["candidate_text_fields"],
        "human_operator_approval_recorded": True,
        "redaction_checks_passed": REQUIRED_REDACTION_CHECKS,
        "authorized_delivery_path": "still_none_unless_a_separate_delivery_approval_gate_exists",
        "approval_scope": "text_boundary_only_not_customer_delivery_or_publication",
        "approvals_not_granted": FUTURE_RECORD_MUST_KEEP_FALSE,
        "still_blocked_claims": REQUIRED_BLOCKED_CLAIMS,
    }
    optional_context = {
        "human_operator_approval_reference": "non_secret_operator_review_reference_required",
        "approval_timestamp_utc": "required_when_a_real_human_record_is_created",
    }
    out: list[dict[str, Any]] = []
    for field in FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS:
        out.append(
            {
                "field": field,
                "required_in_future_record": True,
                "expected_value_or_constraint": values.get(field, optional_context.get(field)),
                "satisfied_by_this_gate": False,
            }
        )
    return out


def _redaction_contract() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "required_in_future_approval_record": True,
            "passed_by_this_gate": False,
            "future_record_must_include_evidence_reference": True,
        }
        for check in REQUIRED_REDACTION_CHECKS
    ]


def build_aas_single_boundary_approval_record_schema_gate(
    *,
    artifact_dir: Path | None = None,
    source_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the schema gate for a later human-operator approval record."""

    request = source_request or _load_source_request(artifact_dir=artifact_dir)
    _assert_source_request(request)
    boundary = request["selected_boundary"]

    safe_to_claim = _dedupe(
        [
            *request.get("safe_to_claim", []),
            AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*REQUIRED_BLOCKED_CLAIMS, *request.get("do_not_claim_yet", [])])

    gate = {
        "schema": AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA,
        "gate_id": GATE_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "source_request_file": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
        "source_request_schema": request["schema"],
        "source_request_id": request["request_id"],
        "source_request_digest_sha256": _canonical_digest(request),
        "source_safe_claim": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "gate_status": GATE_STATUS,
        "future_record_schema": FUTURE_RECORD_SCHEMA_NAME,
        "future_approval_record_required_fields": _future_required_field_contracts(request),
        "selected_boundary": {
            "key": boundary["key"],
            "family_id": boundary["family_id"],
            "family_label": boundary["family_label"],
            "offer_id": boundary["offer_id"],
            "candidate_text_boundary": boundary["candidate_text_boundary"],
            "candidate_text_value": boundary["candidate_text_value"],
            "candidate_text_fields": boundary["candidate_text_fields"],
            "selected_boundary_approved_here": False,
            "human_operator_approval_recorded_here": False,
        },
        "redaction_contract": _redaction_contract(),
        "current_gate_values": {
            "human_operator_approval_recorded": False,
            "selected_boundary_approved": False,
            "approved_text_boundary_recorded": False,
            "redaction_checks_passed": False,
            "authorized_delivery_path": AUTHORIZED_DELIVERY_PATH,
            "customer_delivery_path_authorized": False,
            "operator_publish_approval_recorded": False,
            "publication_approved": False,
        },
        "future_record_must_keep_false": FUTURE_RECORD_MUST_KEEP_FALSE,
        "readiness": {flag: False for flag in RECORD_GATE_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this as the schema gate for a later real human approval record only. "
            "Do not treat this gate as approval; a future record must cite this request, name "
            "the exact approved text, carry redaction evidence references, and keep customer "
            "delivery/publication/routes/pricing/dispatch/reputation/runtime/GPS/worker-doctrine "
            "blocked unless separate gates prove them."
        ),
        "next_smallest_proof": (
            "A human operator may later create one approval record for this exact Compliance Desk "
            "package-label boundary, but that record still must not authorize delivery, publication, "
            "pricing, routes, queues, dispatch, reputation, live runtime, GPS/raw metadata release, "
            "domain authority, or worker-copyable doctrine."
        ),
    }
    _assert_gate(gate)
    return gate


def _assert_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("approval record schema gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("approval record schema gate id drift")
    if gate.get("scope") != SCOPE:
        raise CityOpsContractError("approval record schema gate scope drift")
    if gate.get("source_request_file") != AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME:
        raise CityOpsContractError("approval record schema gate source file drift")
    if gate.get("source_request_schema") != AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("approval record schema gate source schema drift")
    if gate.get("source_request_id") != REQUEST_ID:
        raise CityOpsContractError("approval record schema gate source id drift")
    if gate.get("source_safe_claim") != AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM:
        raise CityOpsContractError("approval record schema gate source safe claim drift")
    if AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM not in gate.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval record schema gate safe claim missing")
    forbidden_safe = set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval record schema gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(gate.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"approval record schema gate missing blocked claims: {sorted(missing_blocked)}"
        )
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("approval record schema gate status drift")
    if gate.get("future_record_schema") != FUTURE_RECORD_SCHEMA_NAME:
        raise CityOpsContractError("approval record schema gate future schema drift")
    fields = gate.get("future_approval_record_required_fields", [])
    if [field.get("field") for field in fields] != FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS:
        raise CityOpsContractError("approval record schema gate required fields drift")
    for field in fields:
        if field.get("required_in_future_record") is not True:
            raise CityOpsContractError("approval record schema gate field not required")
        if field.get("satisfied_by_this_gate") is not False:
            raise CityOpsContractError("approval record schema gate satisfied a future field")
    boundary = gate.get("selected_boundary", {})
    if boundary.get("key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("approval record schema gate selected boundary drift")
    if boundary.get("selected_boundary_approved_here") is not False:
        raise CityOpsContractError("approval record schema gate approved selected boundary")
    if boundary.get("human_operator_approval_recorded_here") is not False:
        raise CityOpsContractError("approval record schema gate recorded human approval")
    if [item.get("check") for item in gate.get("redaction_contract", [])] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("approval record schema gate redaction contract drift")
    for item in gate.get("redaction_contract", []):
        if item.get("required_in_future_approval_record") is not True:
            raise CityOpsContractError("approval record schema gate redaction not required")
        if item.get("passed_by_this_gate") is not False:
            raise CityOpsContractError("approval record schema gate passed redactions")
    current = gate.get("current_gate_values", {})
    for flag in [
        "human_operator_approval_recorded",
        "selected_boundary_approved",
        "approved_text_boundary_recorded",
        "redaction_checks_passed",
        "customer_delivery_path_authorized",
        "operator_publish_approval_recorded",
        "publication_approved",
    ]:
        if current.get(flag) is not False:
            raise CityOpsContractError(f"approval record schema gate promoted current value {flag}")
    if current.get("authorized_delivery_path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("approval record schema gate delivery path drift")
    if gate.get("future_record_must_keep_false") != FUTURE_RECORD_MUST_KEEP_FALSE:
        raise CityOpsContractError("approval record schema gate false-flag contract drift")
    for flag in RECORD_GATE_READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"approval record schema gate promoted readiness {flag}")
    if gate.get("still_blocked_claims") != gate.get("do_not_claim_yet"):
        raise CityOpsContractError("approval record schema gate blocked claims drift")


def write_aas_single_boundary_approval_record_schema_gate(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_aas_single_boundary_approval_record_schema_gate(artifact_dir=target_dir)
    path = target_dir / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_single_boundary_approval_record_schema_gate(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    _assert_gate(gate)
    return gate
