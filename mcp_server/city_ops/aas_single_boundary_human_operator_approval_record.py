"""Human-operator approval record for one AAS text boundary.

This module creates the smallest internal/admin approval record after the
single-boundary operator review brief and validator. It approves only the exact
Compliance Desk package-label text boundary. It is deliberately not customer
delivery, not publication, not a public route/catalog/pilot, not pricing or
operator queue launch, not dispatch, not reputation, not live Acontext/runtime
parity, not exact GPS/raw metadata exposure, and not worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_single_boundary_approval_record_schema_gate import (
    FUTURE_RECORD_MUST_KEEP_FALSE,
    FUTURE_RECORD_SCHEMA_NAME,
    REQUIRED_REDACTION_CHECKS,
)
from .aas_single_boundary_approval_record_validator import (
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SCHEMA,
    APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
    APPROVAL_RECORD_ALLOWED_SCOPE,
    APPROVAL_RECORD_ALLOWED_STATUS,
    REJECT_IF_FIELDS_TRUE,
    REQUIRED_BLOCKED_CLAIMS as VALIDATOR_REQUIRED_BLOCKED_CLAIMS,
    VALIDATOR_ID,
    build_aas_single_boundary_approval_record_validator,
    load_aas_single_boundary_approval_record_validator,
    validate_aas_single_boundary_human_operator_approval_record,
)
from .aas_single_boundary_operator_review_brief import (
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA,
    BRIEF_ID,
    build_aas_single_boundary_operator_review_brief,
    load_aas_single_boundary_operator_review_brief,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA = FUTURE_RECORD_SCHEMA_NAME
AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME = (
    "aas_single_boundary_human_operator_approval_record.json"
)
AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM = (
    "aas_single_boundary_human_operator_approval_record_landed"
)

APPROVAL_RECORD_ID = (
    "execution_market.aas.single_boundary_human_operator_approval_record."
    "compliance_desk.visible_posting_notice_compliance_snapshot.2026_05_17"
)
APPROVAL_REFERENCE = (
    "dream_task_2026_05_17_0702_operator_authorized_single_boundary_internal_label"
)
APPROVAL_TIMESTAMP_UTC = "2026-05-17T11:02:00Z"
APPROVED_BOUNDARY_KEY = "compliance_desk"
APPROVED_TEXT_BOUNDARY = "internal_package_label_only"
EXACT_APPROVED_TEXT = "Visible posting / notice compliance snapshot"
APPROVED_TEXT_FIELDS = ["package_label_under_review"]

RECORD_SCOPE = "internal_admin_single_boundary_human_operator_approval_record_only"

RECORD_STILL_BLOCKED_CLAIMS = [
    *VALIDATOR_REQUIRED_BLOCKED_CLAIMS,
    "approval_record_authorizes_customer_delivery",
    "approval_record_authorizes_publication",
    "approval_record_authorizes_public_route_or_catalog",
    "approval_record_authorizes_controlled_pilot_or_front_door_sku",
    "approval_record_authorizes_public_price_or_customer_quote",
    "approval_record_authorizes_operator_queue_launch",
    "approval_record_authorizes_dispatch",
    "approval_record_authorizes_erc8004_reputation_receipts",
    "approval_record_authorizes_live_acontext_or_runtime_parity",
    "approval_record_authorizes_exact_gps_or_raw_metadata_exposure",
    "approval_record_authorizes_domain_authority_or_legal_regulator_claims",
    "approval_record_authorizes_worker_skill_dna_or_copyable_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(RECORD_STILL_BLOCKED_CLAIMS) | {
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
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "domain_authority_ready",
    "legal_or_regulator_authority_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
}

DELIVERY_FLAGS_FALSE = {
    "customer_delivery_authorized": False,
    "customer_delivery_path_authorized": False,
    "customer_delivery_approval": False,
    "customer_delivery_approved": False,
    "operator_publish_approval": False,
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
    "domain_authority_claims_allowed": False,
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


def _load_source_brief(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_single_boundary_operator_review_brief(artifact_dir=artifact_dir)


def _load_source_validator(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_single_boundary_approval_record_validator(artifact_dir=artifact_dir)


def _assert_sources(brief: dict[str, Any], validator: dict[str, Any]) -> None:
    if brief.get("schema") != AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA:
        raise CityOpsContractError("approval record source brief schema drift")
    if brief.get("brief_id") != BRIEF_ID:
        raise CityOpsContractError("approval record source brief id drift")
    if AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM not in brief.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval record source brief safe claim missing")
    if validator.get("schema") != AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SCHEMA:
        raise CityOpsContractError("approval record source validator schema drift")
    if validator.get("validator_id") != VALIDATOR_ID:
        raise CityOpsContractError("approval record source validator id drift")
    if validator.get("source_brief_id") != brief.get("brief_id"):
        raise CityOpsContractError("approval record validator source brief id drift")
    if validator.get("source_brief_digest_sha256") != _canonical_digest(brief):
        raise CityOpsContractError("approval record validator source brief digest drift")
    if AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM not in validator.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval record source validator safe claim missing")
    forbidden_safe = (
        set(brief.get("safe_to_claim", [])) | set(validator.get("safe_to_claim", []))
    ) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval record source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    boundary = brief.get("selected_boundary", {})
    if boundary.get("key") != APPROVED_BOUNDARY_KEY:
        raise CityOpsContractError("approval record source selected boundary drift")
    if boundary.get("text_boundary_under_review") != APPROVED_TEXT_BOUNDARY:
        raise CityOpsContractError("approval record source text boundary drift")
    if boundary.get("exact_text_under_review") != EXACT_APPROVED_TEXT:
        raise CityOpsContractError("approval record source exact text drift")
    if boundary.get("candidate_text_fields") != APPROVED_TEXT_FIELDS:
        raise CityOpsContractError("approval record source approved text fields drift")
    if boundary.get("selected_boundary_approved_by_this_brief") is not False:
        raise CityOpsContractError("approval record source brief self-approved boundary")
    if boundary.get("human_operator_approval_recorded_by_this_brief") is not False:
        raise CityOpsContractError("approval record source brief recorded approval")


def _redaction_checks_passed() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "passed": True,
            "evidence_reference": f"operator_redaction_review:{APPROVAL_REFERENCE}:{check}",
        }
        for check in REQUIRED_REDACTION_CHECKS
    ]


def build_aas_single_boundary_human_operator_approval_record(
    *,
    artifact_dir: Path | None = None,
    source_brief: dict[str, Any] | None = None,
    source_validator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the narrow internal/admin approval record for one label boundary."""

    brief = source_brief or _load_source_brief(artifact_dir=artifact_dir)
    validator = source_validator or _load_source_validator(artifact_dir=artifact_dir)
    _assert_sources(brief, validator)
    boundary = brief["selected_boundary"]

    safe_to_claim = _dedupe(
        [
            *validator.get("safe_to_claim", []),
            AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *RECORD_STILL_BLOCKED_CLAIMS,
            *brief.get("still_blocked_claims", []),
            *validator.get("still_blocked_claims", []),
            *validator.get("do_not_claim_yet", []),
        ]
    )

    record: dict[str, Any] = {
        "schema": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA,
        "record_id": APPROVAL_RECORD_ID,
        "record_status": APPROVAL_RECORD_ALLOWED_STATUS,
        "scope": RECORD_SCOPE,
        "source_brief_file": AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
        "source_brief_id": brief["brief_id"],
        "source_brief_digest_sha256": _canonical_digest(brief),
        "source_safe_claim": AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
        "source_request_id": brief["source_gate_id"],
        "source_request_digest_sha256": brief["source_gate_digest_sha256"],
        "source_validator_file": AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME,
        "source_validator_id": validator["validator_id"],
        "source_validator_digest_sha256": _canonical_digest(validator),
        "source_validator_safe_claim": AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "selected_boundary_key": boundary["key"],
        "family_id": boundary["family_id"],
        "family_label": boundary["family_label"],
        "offer_id": boundary["offer_id"],
        "approved_text_boundary": boundary["text_boundary_under_review"],
        "exact_approved_text": boundary["exact_text_under_review"],
        "approved_text_fields": boundary["candidate_text_fields"],
        "approved_text_sections": [
            {
                "section": boundary["text_boundary_under_review"],
                "approved_text": boundary["exact_text_under_review"],
                "approved_fields": boundary["candidate_text_fields"],
            }
        ],
        "human_operator_approval_recorded": True,
        "selected_boundary_approved": True,
        "approved_text_boundary_recorded": True,
        "human_operator_approval_reference": APPROVAL_REFERENCE,
        "approval_timestamp_utc": APPROVAL_TIMESTAMP_UTC,
        "redaction_checks_passed": _redaction_checks_passed(),
        "authorized_delivery_path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
        "authorized_delivery_path_detail": {
            "path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
            "authorized_for": "no_customer_delivery_no_publication_no_dispatch",
            "customer_delivery_allowed": False,
            "public_route_allowed": False,
            "catalog_route_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "exact_gps_or_raw_metadata_allowed": False,
        },
        "approval_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "approvals_not_granted": list(FUTURE_RECORD_MUST_KEEP_FALSE),
        "future_record_must_keep_false": {
            flag: False for flag in FUTURE_RECORD_MUST_KEEP_FALSE
        },
        "still_blocked_claims": do_not_claim_yet,
        **DELIVERY_FLAGS_FALSE,
        "operator_instruction": (
            "This record approves only the exact internal package label text boundary. "
            "It does not publish, deliver to a customer, register a route or catalog, "
            "launch a pilot/SKU/queue, dispatch work, attach ERC-8004 reputation, prove "
            "live Acontext/runtime parity, expose exact GPS/raw metadata, make legal or "
            "domain-authority claims, or create worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Keep this as an internal/admin approval record. A separate delivery/publication "
            "gate is required before any customer, public, catalog, pilot, route, dispatch, "
            "or reputation action."
        ),
    }
    _assert_record_is_conservative(record, source_brief=brief)
    return record


def _assert_record_is_conservative(
    record: dict[str, Any], *, source_brief: dict[str, Any] | None = None
) -> None:
    result = validate_aas_single_boundary_human_operator_approval_record(
        record,
        source_brief=source_brief,
    )
    if result.get("record_valid") is not True:
        raise CityOpsContractError("approval record validator did not accept record")
    if record.get("record_id") != APPROVAL_RECORD_ID:
        raise CityOpsContractError("approval record id drift")
    if record.get("scope") != RECORD_SCOPE:
        raise CityOpsContractError("approval record scope drift")
    if record.get("selected_boundary_key") != APPROVED_BOUNDARY_KEY:
        raise CityOpsContractError("approval record selected boundary drift")
    if record.get("approved_text_boundary") != APPROVED_TEXT_BOUNDARY:
        raise CityOpsContractError("approval record approved text boundary drift")
    if record.get("exact_approved_text") != EXACT_APPROVED_TEXT:
        raise CityOpsContractError("approval record exact approved text drift")
    if record.get("approved_text_fields") != APPROVED_TEXT_FIELDS:
        raise CityOpsContractError("approval record approved text fields drift")
    if record.get("approved_text_sections") != [
        {
            "section": APPROVED_TEXT_BOUNDARY,
            "approved_text": EXACT_APPROVED_TEXT,
            "approved_fields": APPROVED_TEXT_FIELDS,
        }
    ]:
        raise CityOpsContractError("approval record approved text sections drift")
    if AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM not in record.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval record safe claim missing")
    forbidden_safe = set(record.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval record forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(RECORD_STILL_BLOCKED_CLAIMS) - set(
        record.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"approval record missing blocked claims: {sorted(missing_blocked)}"
        )
    if record.get("still_blocked_claims") != record.get("do_not_claim_yet"):
        raise CityOpsContractError("approval record blocked claims drift")
    if record.get("human_operator_approval_recorded") is not True:
        raise CityOpsContractError("approval record missing human approval")
    if record.get("selected_boundary_approved") is not True:
        raise CityOpsContractError("approval record missing selected-boundary approval")
    if record.get("authorized_delivery_path") != APPROVAL_RECORD_ALLOWED_DELIVERY_PATH:
        raise CityOpsContractError("approval record delivery path drift")
    detail = record.get("authorized_delivery_path_detail", {})
    for field in [
        "customer_delivery_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
    ]:
        if detail.get(field) is not False:
            raise CityOpsContractError(f"approval record promoted delivery detail {field}")
    if [item.get("check") for item in record.get("redaction_checks_passed", [])] != (
        REQUIRED_REDACTION_CHECKS
    ):
        raise CityOpsContractError("approval record redaction checks drift")
    for item in record.get("redaction_checks_passed", []):
        if item.get("passed") is not True:
            raise CityOpsContractError("approval record redaction check not passed")
        if not item.get("evidence_reference"):
            raise CityOpsContractError("approval record missing redaction evidence")
    for flag in FUTURE_RECORD_MUST_KEEP_FALSE:
        if record.get("future_record_must_keep_false", {}).get(flag) is not False:
            raise CityOpsContractError(f"approval record promoted false flag {flag}")
    for flag in set(REJECT_IF_FIELDS_TRUE) | set(DELIVERY_FLAGS_FALSE):
        if record.get(flag) is True:
            raise CityOpsContractError(f"approval record forbidden promotion {flag}")


def write_aas_single_boundary_human_operator_approval_record(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    record = build_aas_single_boundary_human_operator_approval_record(
        artifact_dir=target_dir
    )
    path = target_dir / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_single_boundary_human_operator_approval_record(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError("approval record must be a JSON object")
    source_brief = _load_source_brief(artifact_dir=source_dir)
    _assert_record_is_conservative(record, source_brief=source_brief)
    return record
