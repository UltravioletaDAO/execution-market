"""Validation harness for a future single-boundary AAS approval record.

This module is the next conservative step after the operator review brief. It
creates an internal/admin validator contract and a callable validator for a
future human-created approval record. It does not create a human approval
record, does not approve customer copy or delivery, does not publish, does not
create public routes/catalog/pilots, does not approve pricing or queue launch,
does not dispatch, does not attach reputation, does not prove live
Acontext/runtime parity, and does not expose exact GPS/raw metadata or
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .aas_single_boundary_approval_record_schema_gate import (
    FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    FUTURE_RECORD_MUST_KEEP_FALSE,
    FUTURE_RECORD_SCHEMA_NAME,
    REQUIRED_REDACTION_CHECKS,
)
from .aas_single_boundary_operator_review_brief import (
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA,
    BRIEF_ID,
    BRIEF_STATUS,
    CURRENT_BRIEF_VALUES,
    HUMAN_REVIEW_CHECKLIST,
    REQUIRED_BLOCKED_CLAIMS as BRIEF_REQUIRED_BLOCKED_CLAIMS,
    build_aas_single_boundary_operator_review_brief,
    load_aas_single_boundary_operator_review_brief,
)
from .aas_single_boundary_human_operator_approval_request import SELECTED_BOUNDARY_KEY
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SCHEMA = (
    "city_ops.aas_single_boundary_approval_record_validator.v1"
)
AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME = (
    "aas_single_boundary_approval_record_validator.json"
)
AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM = (
    "aas_single_boundary_approval_record_validator_landed"
)

VALIDATOR_ID = "execution_market.aas.single_boundary_approval_record_validator.001"
SCOPE = "internal_admin_validator_for_future_human_approval_record_only"
SOURCE_POLICY = "consume_only_single_boundary_operator_review_brief_json"
VALIDATOR_STATUS = "validator_contract_only_no_human_approval_record_created"
APPROVAL_RECORD_ALLOWED_STATUS = "human_operator_approved_selected_boundary_only"
APPROVAL_RECORD_ALLOWED_SCOPE = "selected_internal_package_label_only"
APPROVAL_RECORD_ALLOWED_DELIVERY_PATH = "none_no_customer_delivery_authorized"

VALIDATOR_READINESS_FALSE_FLAGS = [
    "validator_created_human_approval_record",
    "validator_approves_customer_copy",
    "validator_authorizes_customer_delivery",
    "validator_authorizes_publication",
    "validator_authorizes_public_price_or_customer_quote",
    "validator_launches_operator_queue",
    "validator_enables_dispatch",
    "validator_attaches_reputation",
    "validator_proves_live_runtime_or_acontext_parity",
    "validator_allows_gps_or_raw_metadata_release",
    "validator_creates_worker_doctrine",
]

REQUIRED_BLOCKED_CLAIMS = [
    *BRIEF_REQUIRED_BLOCKED_CLAIMS,
    "approval_record_created_by_validator",
    "approval_record_accepted_without_human_reference",
    "approval_record_accepted_without_redaction_evidence",
    "approval_record_authorizes_customer_delivery",
    "approval_record_authorizes_publication",
    "approval_record_authorizes_public_price_or_customer_quote",
    "approval_record_authorizes_operator_queue_launch",
    "approval_record_authorizes_dispatch",
    "approval_record_authorizes_reputation",
    "approval_record_authorizes_live_runtime_or_acontext",
    "approval_record_authorizes_gps_or_raw_metadata_release",
    "approval_record_authorizes_domain_authority",
    "approval_record_authorizes_worker_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
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
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
}

APPROVAL_RECORD_REQUIRED_FIELDS = [
    "schema",
    "record_status",
    "source_brief_id",
    "source_brief_digest_sha256",
    "source_safe_claim",
    *FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    "future_record_must_keep_false",
]

REJECT_IF_FIELDS_TRUE = [
    *FUTURE_RECORD_MUST_KEEP_FALSE,
    "customer_copy_created",
    "customer_copy_ready",
    "customer_delivery_path_authorized",
    "customer_delivery_approved",
    "publication_ready",
    "publishable",
    "public_price_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_receipt_attachable",
    "exact_gps_or_raw_metadata_release_ready",
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


def _load_source_brief(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_single_boundary_operator_review_brief(artifact_dir=artifact_dir)


def _assert_source_brief(brief: dict[str, Any]) -> None:
    if brief.get("schema") != AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA:
        raise CityOpsContractError("approval record validator source brief schema drift")
    if brief.get("brief_id") != BRIEF_ID:
        raise CityOpsContractError("approval record validator source brief id drift")
    if brief.get("brief_status") != BRIEF_STATUS:
        raise CityOpsContractError("approval record validator source brief status drift")
    if AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM not in brief.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval record validator source brief safe claim missing")
    forbidden_safe = set(brief.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval record validator source brief forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(BRIEF_REQUIRED_BLOCKED_CLAIMS) - set(brief.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"approval record validator source brief missing blocked claims: {sorted(missing_blocked)}"
        )
    boundary = brief.get("selected_boundary", {})
    if boundary.get("key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("approval record validator source selected boundary drift")
    if boundary.get("exact_text_under_review") != "Visible posting / notice compliance snapshot":
        raise CityOpsContractError("approval record validator source exact text drift")
    if boundary.get("selected_boundary_approved_by_this_brief") is not False:
        raise CityOpsContractError("approval record validator source approved selected boundary")
    if boundary.get("human_operator_approval_recorded_by_this_brief") is not False:
        raise CityOpsContractError("approval record validator source recorded human approval")
    if [item.get("check") for item in brief.get("human_review_checklist", [])] != HUMAN_REVIEW_CHECKLIST:
        raise CityOpsContractError("approval record validator source checklist drift")
    for item in brief.get("human_review_checklist", []):
        if item.get("satisfied_by_this_brief") is not False:
            raise CityOpsContractError("approval record validator source satisfied checklist")
    if [item.get("check") for item in brief.get("redaction_review_items", [])] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("approval record validator source redaction items drift")
    for item in brief.get("redaction_review_items", []):
        if item.get("passed_by_this_brief") is not False:
            raise CityOpsContractError("approval record validator source passed redactions")
    current = brief.get("current_brief_values", {})
    for flag, expected in CURRENT_BRIEF_VALUES.items():
        if current.get(flag) != expected:
            raise CityOpsContractError(f"approval record validator source promoted current value {flag}")
    for flag in FUTURE_RECORD_MUST_KEEP_FALSE:
        if flag not in brief.get("future_record_must_keep_false", []):
            raise CityOpsContractError(f"approval record validator source missing false flag {flag}")


def _record_field_contract() -> list[dict[str, Any]]:
    return [
        {
            "field": field,
            "required_for_future_human_record": True,
            "satisfied_by_validator_artifact": False,
        }
        for field in APPROVAL_RECORD_REQUIRED_FIELDS
    ]


def _redaction_evidence_contract() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "future_record_must_mark_passed": True,
            "future_record_must_include_evidence_reference": True,
            "satisfied_by_validator_artifact": False,
        }
        for check in REQUIRED_REDACTION_CHECKS
    ]


def build_aas_single_boundary_approval_record_validator(
    *,
    artifact_dir: Path | None = None,
    source_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an internal/admin validator contract for a future approval record."""

    brief = source_brief or _load_source_brief(artifact_dir=artifact_dir)
    _assert_source_brief(brief)
    boundary = brief["selected_boundary"]

    safe_to_claim = _dedupe(
        [
            *brief.get("safe_to_claim", []),
            AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*REQUIRED_BLOCKED_CLAIMS, *brief.get("do_not_claim_yet", [])])

    validator = {
        "schema": AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SCHEMA,
        "validator_id": VALIDATOR_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "source_brief_file": AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
        "source_brief_schema": brief["schema"],
        "source_brief_id": brief["brief_id"],
        "source_brief_digest_sha256": _canonical_digest(brief),
        "source_safe_claim": AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "validator_status": VALIDATOR_STATUS,
        "future_record_schema": FUTURE_RECORD_SCHEMA_NAME,
        "allowed_record_status": APPROVAL_RECORD_ALLOWED_STATUS,
        "allowed_approval_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "allowed_delivery_path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
        "selected_boundary": {
            "key": boundary["key"],
            "family_id": boundary["family_id"],
            "family_label": boundary["family_label"],
            "offer_id": boundary["offer_id"],
            "approved_text_boundary_must_equal": boundary["text_boundary_under_review"],
            "exact_approved_text_must_equal": boundary["exact_text_under_review"],
            "approved_text_fields_must_equal": boundary["candidate_text_fields"],
        },
        "record_field_contract": _record_field_contract(),
        "redaction_evidence_contract": _redaction_evidence_contract(),
        "future_record_must_keep_false": FUTURE_RECORD_MUST_KEEP_FALSE,
        "reject_if_fields_true": REJECT_IF_FIELDS_TRUE,
        "readiness": {flag: False for flag in VALIDATOR_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this validator before accepting any future human-created approval record. "
            "The validator may only accept an approval for the exact Compliance Desk package "
            "label boundary, and it must reject delivery, publication, pricing, queue, dispatch, "
            "reputation, live runtime, GPS/raw metadata, domain-authority, and worker-doctrine claims. "
            "This artifact itself creates no approval record."
        ),
    }
    _assert_validator(validator)
    return validator


def _assert_validator(validator: dict[str, Any]) -> None:
    if validator.get("schema") != AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SCHEMA:
        raise CityOpsContractError("approval record validator schema drift")
    if validator.get("validator_id") != VALIDATOR_ID:
        raise CityOpsContractError("approval record validator id drift")
    if validator.get("scope") != SCOPE:
        raise CityOpsContractError("approval record validator scope drift")
    if validator.get("validator_status") != VALIDATOR_STATUS:
        raise CityOpsContractError("approval record validator status drift")
    if validator.get("source_brief_file") != AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME:
        raise CityOpsContractError("approval record validator source file drift")
    if validator.get("source_brief_schema") != AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA:
        raise CityOpsContractError("approval record validator source schema drift")
    if validator.get("source_brief_id") != BRIEF_ID:
        raise CityOpsContractError("approval record validator source id drift")
    if validator.get("source_safe_claim") != AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM:
        raise CityOpsContractError("approval record validator source safe claim drift")
    if AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM not in validator.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval record validator safe claim missing")
    forbidden_safe = set(validator.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval record validator forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(validator.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"approval record validator missing blocked claims: {sorted(missing_blocked)}"
        )
    if validator.get("future_record_schema") != FUTURE_RECORD_SCHEMA_NAME:
        raise CityOpsContractError("approval record validator future schema drift")
    if validator.get("allowed_record_status") != APPROVAL_RECORD_ALLOWED_STATUS:
        raise CityOpsContractError("approval record validator allowed status drift")
    if validator.get("allowed_approval_scope") != APPROVAL_RECORD_ALLOWED_SCOPE:
        raise CityOpsContractError("approval record validator approval scope drift")
    if validator.get("allowed_delivery_path") != APPROVAL_RECORD_ALLOWED_DELIVERY_PATH:
        raise CityOpsContractError("approval record validator delivery path drift")
    boundary = validator.get("selected_boundary", {})
    if boundary.get("key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("approval record validator selected boundary drift")
    if boundary.get("exact_approved_text_must_equal") != "Visible posting / notice compliance snapshot":
        raise CityOpsContractError("approval record validator exact text drift")
    if [field.get("field") for field in validator.get("record_field_contract", [])] != APPROVAL_RECORD_REQUIRED_FIELDS:
        raise CityOpsContractError("approval record validator field contract drift")
    for field in validator.get("record_field_contract", []):
        if field.get("satisfied_by_validator_artifact") is not False:
            raise CityOpsContractError("approval record validator satisfies future field")
    if [item.get("check") for item in validator.get("redaction_evidence_contract", [])] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("approval record validator redaction contract drift")
    for item in validator.get("redaction_evidence_contract", []):
        if item.get("satisfied_by_validator_artifact") is not False:
            raise CityOpsContractError("approval record validator satisfies redaction evidence")
    if validator.get("future_record_must_keep_false") != FUTURE_RECORD_MUST_KEEP_FALSE:
        raise CityOpsContractError("approval record validator false-flag contract drift")
    for flag in VALIDATOR_READINESS_FALSE_FLAGS:
        if validator.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"approval record validator promoted readiness {flag}")
    if validator.get("still_blocked_claims") != validator.get("do_not_claim_yet"):
        raise CityOpsContractError("approval record validator blocked claims drift")


def _assert_timestamp_utc(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CityOpsContractError("approval record timestamp must be UTC Z string")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise CityOpsContractError("approval record timestamp invalid") from exc


def _assert_non_empty_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CityOpsContractError(f"approval record missing {field}")


def validate_aas_single_boundary_human_operator_approval_record(
    record: dict[str, Any],
    *,
    artifact_dir: Path | None = None,
    source_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a future human-created approval record without creating one."""

    if not isinstance(record, dict):
        raise CityOpsContractError("approval record must be a JSON object")
    brief = source_brief or _load_source_brief(artifact_dir=artifact_dir)
    _assert_source_brief(brief)
    boundary = brief["selected_boundary"]
    expected_digest = _canonical_digest(brief)

    missing_fields = [field for field in APPROVAL_RECORD_REQUIRED_FIELDS if field not in record]
    if missing_fields:
        raise CityOpsContractError(f"approval record missing required fields: {missing_fields}")
    if record.get("schema") != FUTURE_RECORD_SCHEMA_NAME:
        raise CityOpsContractError("approval record schema drift")
    if record.get("record_status") != APPROVAL_RECORD_ALLOWED_STATUS:
        raise CityOpsContractError("approval record status not allowed")
    if record.get("source_brief_id") != BRIEF_ID:
        raise CityOpsContractError("approval record source brief id drift")
    if record.get("source_brief_digest_sha256") != expected_digest:
        raise CityOpsContractError("approval record source digest drift")
    if record.get("source_safe_claim") != AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM:
        raise CityOpsContractError("approval record source safe claim drift")
    if record.get("source_request_id") != brief.get("source_gate_id"):
        raise CityOpsContractError("approval record source request id drift")
    if record.get("source_request_digest_sha256") != brief.get("source_gate_digest_sha256"):
        raise CityOpsContractError("approval record source request digest drift")
    if record.get("selected_boundary_key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("approval record selected boundary drift")
    if record.get("approved_text_boundary") != boundary["text_boundary_under_review"]:
        raise CityOpsContractError("approval record approved boundary drift")
    if record.get("exact_approved_text") != boundary["exact_text_under_review"]:
        raise CityOpsContractError("approval record approved text drift")
    if record.get("approved_text_fields") != boundary["candidate_text_fields"]:
        raise CityOpsContractError("approval record approved text fields drift")
    if record.get("human_operator_approval_recorded") is not True:
        raise CityOpsContractError("approval record must record human approval")
    _assert_non_empty_string(
        record.get("human_operator_approval_reference"),
        "human_operator_approval_reference",
    )
    _assert_timestamp_utc(record.get("approval_timestamp_utc"))
    if record.get("authorized_delivery_path") != APPROVAL_RECORD_ALLOWED_DELIVERY_PATH:
        raise CityOpsContractError("approval record delivery path not allowed")
    if record.get("approval_scope") != APPROVAL_RECORD_ALLOWED_SCOPE:
        raise CityOpsContractError("approval record approval scope not allowed")

    redactions = record.get("redaction_checks_passed")
    if not isinstance(redactions, list):
        raise CityOpsContractError("approval record redaction checks must be a list")
    if [item.get("check") for item in redactions] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("approval record redaction checks drift")
    for item in redactions:
        if item.get("passed") is not True:
            raise CityOpsContractError("approval record redaction check not passed")
        _assert_non_empty_string(item.get("evidence_reference"), "redaction evidence reference")

    approvals_not_granted = record.get("approvals_not_granted")
    if not isinstance(approvals_not_granted, list):
        raise CityOpsContractError("approval record approvals_not_granted must be a list")
    missing_false_flags = set(FUTURE_RECORD_MUST_KEEP_FALSE) - set(approvals_not_granted)
    if missing_false_flags:
        raise CityOpsContractError(
            f"approval record missing approvals not granted: {sorted(missing_false_flags)}"
        )
    false_map = record.get("future_record_must_keep_false")
    if not isinstance(false_map, dict):
        raise CityOpsContractError("approval record false flags must be an object")
    for flag in FUTURE_RECORD_MUST_KEEP_FALSE:
        if false_map.get(flag) is not False:
            raise CityOpsContractError(f"approval record promoted false flag {flag}")
    for flag in REJECT_IF_FIELDS_TRUE:
        if record.get(flag) is True:
            raise CityOpsContractError(f"approval record forbidden promotion {flag}")
    still_blocked = record.get("still_blocked_claims")
    if not isinstance(still_blocked, list):
        raise CityOpsContractError("approval record still_blocked_claims must be a list")
    missing_blocked = set(brief.get("still_blocked_claims", [])) - set(still_blocked)
    if missing_blocked:
        raise CityOpsContractError(
            f"approval record missing still blocked claims: {sorted(missing_blocked)}"
        )
    return {
        "record_valid": True,
        "validated_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "selected_boundary_key": SELECTED_BOUNDARY_KEY,
        "exact_text_approved": boundary["exact_text_under_review"],
        "customer_delivery_authorized": False,
        "publication_authorized": False,
        "dispatch_authorized": False,
        "reputation_authorized": False,
        "runtime_or_acontext_authorized": False,
    }


def write_aas_single_boundary_approval_record_validator(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    validator = build_aas_single_boundary_approval_record_validator(artifact_dir=target_dir)
    path = target_dir / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME
    path.write_text(json.dumps(validator, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_single_boundary_approval_record_validator(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        validator = json.load(fh)
    _assert_validator(validator)
    return validator
