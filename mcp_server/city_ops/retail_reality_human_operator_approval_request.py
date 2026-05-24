"""Retail Reality human-operator approval request.

This module advances the Retail Reality AAS ladder by one conservative rung after
an explicit sample-output hold decision. It creates a pending internal/admin
request for a human operator to review the exact sample text boundary later. It
is intentionally not approval, customer copy, delivery, publication, public
route/catalog/pilot, pricing, queue launch, dispatch, reputation, live
Acontext/runtime parity, exact GPS/raw metadata exposure, permanent
business-status, inventory, brand-compliance, employee-performance,
consumer-safety, continuous-monitoring, private retail context release, or
worker-copyable retail doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .retail_reality_customer_output_schema_gate import ALLOWED_CUSTOMER_OUTPUT_FIELDS
from .retail_reality_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .retail_reality_internal_sample_output import (
    RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_FILENAME,
    RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
    RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SCHEMA,
    SAMPLE_OUTPUT_ID,
    load_retail_reality_internal_sample_output,
)
from .retail_reality_sample_output_review_decision import (
    DECISION_READINESS_FALSE_FLAGS,
    RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
    REVIEW_DECISION,
    load_retail_reality_sample_output_review_decision,
)

RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA = (
    "city_ops.retail_reality_human_operator_approval_request.v1"
)
RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME = (
    "retail_reality_human_operator_approval_request.json"
)
RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM = (
    "retail_reality_human_operator_approval_request_landed"
)

REQUEST_ID = "execution_market.aas.retail_reality.human_operator_approval_request.001"
SCOPE = "internal_admin_retail_reality_human_operator_approval_request_only"
APPROVAL_REQUEST_STATUS = "pending_human_operator_review_not_approved"
SELECTED_TEXT_BOUNDARY_KEY = "retail_reality_internal_sample_exact_field_values"
AUTHORIZED_DELIVERY_PATH = "none_until_separate_human_operator_approval_record"

NEXT_REQUIRED_LADDER_STEPS = [
    "separate_human_operator_approval_record_if_authorized",
]

REQUIRED_PRE_APPROVAL_CHECKS = [
    "source_review_decision_still_explicit_hold",
    "source_sample_still_synthetic_internal_admin_only",
    "selected_sample_text_boundary_digest_preserved",
    "selected_sample_fields_match_schema_gate_allowlist",
    "privacy_redaction_notice_required_before_any_approval",
    "limitations_and_non_guarantees_required_before_any_approval",
    "retail_authority_exclusions_required_before_any_approval",
    "exact_gps_raw_metadata_private_context_release_still_blocked",
    "permanent_status_inventory_brand_employee_consumer_monitoring_claims_still_blocked",
    "authorized_delivery_path_required_but_absent",
    "operator_publish_approval_required_but_absent",
    "customer_delivery_approval_required_but_absent",
]

REDACTION_AND_AUTHORITY_REQUIREMENTS = [
    "exact_gps_removed",
    "raw_metadata_removed",
    "precise_address_or_private_location_removed",
    "staff_identity_or_private_statement_removed",
    "private_operator_context_removed",
    "raw_transcript_not_used_as_authority",
    "permanent_business_status_language_absent",
    "inventory_guarantee_language_absent",
    "brand_compliance_certification_language_absent",
    "employee_performance_judgment_language_absent",
    "consumer_safety_certification_language_absent",
    "continuous_monitoring_language_absent",
    "dispatch_assignment_language_absent",
    "reputation_receipt_language_absent",
    "worker_copyable_retail_doctrine_absent",
]

REQUEST_FALSE_TOP_LEVEL_FLAGS = {
    "human_operator_approval_recorded": False,
    "selected_text_boundary_approved": False,
    "selected_sample_text_approved_for_customer": False,
    "pre_approval_checks_passed": False,
    "redaction_requirements_passed": False,
    "authority_requirements_passed": False,
    "authorized_delivery_path_recorded": False,
    "operator_publish_approval": False,
    "customer_delivery_approval": False,
    "customer_delivery_path_authorized": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "sample_output_publishable": False,
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
    "private_retail_context_release_allowed": False,
    "permanent_business_status_ready": False,
    "inventory_guarantee_ready": False,
    "brand_compliance_ready": False,
    "employee_performance_judgment_ready": False,
    "consumer_safety_ready": False,
    "continuous_availability_monitoring_ready": False,
    "worker_skill_dna_ready": False,
    "worker_copyable_doctrine_ready": False,
}

REQUEST_READINESS_FALSE_FLAGS = sorted(
    set(DECISION_READINESS_FALSE_FLAGS) | set(REQUEST_FALSE_TOP_LEVEL_FLAGS)
)

REQUEST_BLOCKED_CLAIMS = [
    "retail_reality_human_operator_approval_recorded",
    "retail_reality_selected_sample_text_boundary_approved",
    "retail_reality_pre_approval_checks_passed",
    "retail_reality_redaction_requirements_passed",
    "retail_reality_customer_copy_created",
    "retail_reality_customer_copy_ready",
    "retail_reality_customer_delivery_approved",
    "retail_reality_authorized_delivery_path_recorded",
    "retail_reality_publication_approved",
    "retail_reality_public_route_ready",
    "retail_reality_catalog_route_ready",
    "retail_reality_controlled_pilot_ready",
    "retail_reality_pricing_or_quote_ready",
    "retail_reality_operator_queue_launch_ready",
    "retail_reality_dispatch_enabled",
    "retail_reality_reputation_ready",
    "retail_reality_live_runtime_ready",
    "retail_reality_exact_gps_or_raw_metadata_release_ready",
    "retail_reality_private_context_release_ready",
    "retail_reality_permanent_business_status_ready",
    "retail_reality_inventory_guarantee_ready",
    "retail_reality_brand_compliance_ready",
    "retail_reality_employee_performance_ready",
    "retail_reality_consumer_safety_ready",
    "retail_reality_continuous_availability_monitoring_ready",
    "retail_reality_worker_copyable_retail_doctrine_ready",
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
    "pricing_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "permanent_business_status_claim",
    "inventory_guarantee",
    "brand_compliance_certification",
    "employee_performance_judgment",
    "consumer_safety_claim",
    "continuous_monitoring",
    "worker_copyable_doctrine_ready",
    "worker_copyable_retail_doctrine",
}

FORBIDDEN_APPROVAL_FRAGMENTS = [
    "approved for customer",
    "publishable sample",
    "customer delivery authorized",
    "publication authorized",
    "route ready",
    "dispatch ready",
    "reputation ready",
    "exact gps allowed",
    "raw metadata allowed",
]


def _canonical_digest(payload: Any) -> str:
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


def _load_source_decision(artifact_dir: str | Path | None = None) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else None
    if source_dir is not None and (
        source_dir / RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME
    ).exists():
        return load_retail_reality_sample_output_review_decision(artifact_dir=source_dir)
    return load_retail_reality_sample_output_review_decision()


def _load_source_sample(artifact_dir: str | Path | None = None) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else None
    if source_dir is not None and (
        source_dir / RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_FILENAME
    ).exists():
        return load_retail_reality_internal_sample_output(artifact_dir=source_dir)
    return load_retail_reality_internal_sample_output()


def _assert_source_decision(decision: dict[str, Any], sample: dict[str, Any]) -> None:
    if decision.get("schema") != RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("Retail Reality approval request source decision schema drift")
    if decision.get("review_decision") != REVIEW_DECISION:
        raise CityOpsContractError("Retail Reality approval request source decision promoted verdict")
    if decision.get("explicit_hold_decision_recorded") is not True:
        raise CityOpsContractError("Retail Reality approval request source hold decision missing")
    if decision.get("operator_review_recorded") is not True:
        raise CityOpsContractError("Retail Reality approval request source operator review missing")
    if decision.get("source_sample_output_id") != sample.get("sample_output_id"):
        raise CityOpsContractError("Retail Reality approval request source sample id drift")
    if decision.get("source_sample_output_schema") != RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SCHEMA:
        raise CityOpsContractError("Retail Reality approval request source sample schema drift")
    if decision.get("source_sample_output_file") != RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_FILENAME:
        raise CityOpsContractError("Retail Reality approval request source sample file drift")
    if RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM not in decision.get("safe_to_claim", []):
        raise CityOpsContractError("Retail Reality approval request source safe claim missing")
    forbidden_safe = set(decision.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality approval request source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    decision_readiness = decision.get("decision_readiness", {})
    for flag in REQUEST_FALSE_TOP_LEVEL_FLAGS:
        if decision.get(flag) is not None and decision.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality approval request source promoted {flag}")
        if decision_readiness.get(flag) is not None and decision_readiness.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality approval request source promoted {flag}")
    for flag in DECISION_READINESS_FALSE_FLAGS:
        if decision.get("decision_readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality approval request source promoted decision readiness {flag}"
            )
    boundary = decision.get("sample_output_boundary", {})
    for flag in [
        "sample_text_approved_for_customer",
        "sample_text_publishable",
        "customer_delivery_allowed",
        "public_route_allowed",
        "controlled_pilot_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
        "permanent_business_status_claim_allowed",
        "inventory_guarantee_allowed",
        "brand_compliance_claim_allowed",
        "employee_performance_claim_allowed",
        "consumer_safety_claim_allowed",
        "continuous_availability_monitoring_claim_allowed",
        "private_retail_context_release_allowed",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality approval request source boundary promoted {flag}")


def _assert_source_sample(sample: dict[str, Any]) -> None:
    if sample.get("schema") != RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SCHEMA:
        raise CityOpsContractError("Retail Reality approval request source sample schema drift")
    if sample.get("sample_output_id") != SAMPLE_OUTPUT_ID:
        raise CityOpsContractError("Retail Reality approval request source sample id drift")
    if sample.get("scope") != "internal_admin_retail_reality_sample_output_only":
        raise CityOpsContractError("Retail Reality approval request source sample scope drift")
    if sample.get("offer_id") != OFFER_ID or sample.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Retail Reality approval request source sample package drift")
    if RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM not in sample.get("safe_to_claim", []):
        raise CityOpsContractError("Retail Reality approval request source sample safe claim missing")
    sample_output = sample.get("sample_output", {})
    if sample_output.get("sample_review_status") != "internal_admin_sample_against_schema_gate_not_customer_copy":
        raise CityOpsContractError("Retail Reality approval request source sample status drift")
    if sample_output.get("synthetic_fixture_only") is not True:
        raise CityOpsContractError("Retail Reality approval request source sample stopped being synthetic")
    if sample_output.get("jurisdiction_specific") is not False:
        raise CityOpsContractError("Retail Reality approval request source sample became jurisdiction-specific")
    if sample_output.get("allowed_customer_output_fields") != ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Retail Reality approval request source sample field allowlist drift")
    field_values = sample_output.get("field_values", {})
    if sorted(field_values) != sorted(ALLOWED_CUSTOMER_OUTPUT_FIELDS):
        raise CityOpsContractError("Retail Reality approval request source sample field set drift")
    reviews = sample_output.get("separate_reviews", {})
    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "explicit_hold_or_approval_decision_recorded",
    ]:
        if reviews.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality approval request source sample promoted review {flag}")


def _selected_text_boundary(sample: dict[str, Any]) -> dict[str, Any]:
    field_values = sample["sample_output"]["field_values"]
    return {
        "key": SELECTED_TEXT_BOUNDARY_KEY,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_sample_output_id": sample["sample_output_id"],
        "candidate_text_boundary": "all_internal_sample_field_values_only",
        "candidate_text_fields": list(ALLOWED_CUSTOMER_OUTPUT_FIELDS),
        "candidate_text_values": {field: field_values[field] for field in ALLOWED_CUSTOMER_OUTPUT_FIELDS},
        "candidate_text_digest_sha256": _canonical_digest(field_values),
        "approval_request_boundary": (
            "human_operator_may_review_this_exact_retail_reality_sample_text_later_"
            "but_no_approval_is_recorded_here"
        ),
        "selected_text_boundary_approved": False,
        "human_operator_approval_recorded": False,
        "customer_delivery_authorized_by_boundary": False,
        "publication_authorized_by_boundary": False,
        "dispatch_authorized_by_boundary": False,
        "reputation_authorized_by_boundary": False,
        "exact_gps_or_raw_metadata_authorized_by_boundary": False,
        "private_context_release_authorized_by_boundary": False,
        "retail_authority_claims_authorized_by_boundary": False,
        "worker_doctrine_authorized_by_boundary": False,
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
        }
        for check in REDACTION_AND_AUTHORITY_REQUIREMENTS
    ]


def _delivery_path() -> dict[str, Any]:
    return {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "no_customer_delivery_no_publication_no_dispatch",
        "path_recorded": False,
        "customer_delivery_allowed": False,
        "publication_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "controlled_pilot_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
        "private_retail_context_release_allowed": False,
        "retail_authority_claims_allowed": False,
        "worker_doctrine_allowed": False,
    }


def build_retail_reality_human_operator_approval_request(
    *,
    artifact_dir: str | Path | None = None,
    source_review_decision: dict[str, Any] | None = None,
    source_sample_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a pending, no-approval Retail Reality human-operator request."""

    sample = source_sample_output or _load_source_sample(artifact_dir=artifact_dir)
    decision = source_review_decision or _load_source_decision(artifact_dir=artifact_dir)
    _assert_source_sample(sample)
    _assert_source_decision(decision, sample)

    safe_to_claim = _dedupe(
        [
            *decision.get("safe_to_claim", []),
            RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *decision.get("do_not_claim_yet", []),
            *REQUEST_BLOCKED_CLAIMS,
        ]
    )

    packet: dict[str, Any] = {
        "schema": RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
        "request_id": REQUEST_ID,
        "scope": SCOPE,
        "source_review_decision_file": RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
        "source_review_decision_schema": decision["schema"],
        "source_review_decision_id": decision["decision_id"],
        "source_review_decision_digest_sha256": _canonical_digest(decision),
        "source_sample_output_file": RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_FILENAME,
        "source_sample_output_schema": sample["schema"],
        "source_sample_output_id": sample["sample_output_id"],
        "source_sample_output_digest_sha256": _canonical_digest(sample),
        "source_safe_claims": [
            RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
            RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        ],
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "approval_request_status": APPROVAL_REQUEST_STATUS,
        "ladder_boundary": {
            "covered_steps": [
                *decision["ladder_boundary"]["covered_steps"],
                "human_operator_approval_request",
            ],
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "selected_text_boundary_count": 1,
        "selected_text_boundary": _selected_text_boundary(sample),
        "pre_approval_checks": _pre_approval_checks(),
        "redaction_and_authority_requirements": _redaction_and_authority_requirements(),
        "authorized_delivery_path": _delivery_path(),
        **REQUEST_FALSE_TOP_LEVEL_FLAGS,
        "readiness": {flag: False for flag in REQUEST_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "This packet only asks a human operator to review one exact Retail Reality "
            "sample-text boundary later. It does not record approval, create customer "
            "copy, authorize delivery, publish, launch a route/catalog/pilot/queue, "
            "dispatch workers, attach reputation, expose exact GPS/raw metadata, release "
            "private retail context, or make permanent-status, inventory, brand-compliance, "
            "employee-performance, consumer-safety, continuous-monitoring, or worker-"
            "doctrine claims."
        ),
        "next_smallest_proof": (
            "If a human operator approves this exact boundary later, create a separate "
            "approval record that names the exact approved text, passed redactions, "
            "authorized delivery path, and still-blocked claims. Default remains hold."
        ),
    }
    _assert_approval_request(packet, source_sample=sample, source_decision=decision)
    return packet


def _assert_approval_request(
    packet: dict[str, Any], *, source_sample: dict[str, Any], source_decision: dict[str, Any]
) -> None:
    _assert_source_sample(source_sample)
    _assert_source_decision(source_decision, source_sample)
    if packet.get("schema") != RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("Retail Reality approval request schema drift")
    if packet.get("request_id") != REQUEST_ID:
        raise CityOpsContractError("Retail Reality approval request id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("Retail Reality approval request scope drift")
    if packet.get("source_review_decision_file") != RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME:
        raise CityOpsContractError("Retail Reality approval request source decision file drift")
    if packet.get("source_review_decision_schema") != RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("Retail Reality approval request source decision schema drift")
    if packet.get("source_review_decision_id") != source_decision.get("decision_id"):
        raise CityOpsContractError("Retail Reality approval request source decision id drift")
    if packet.get("source_sample_output_file") != RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_FILENAME:
        raise CityOpsContractError("Retail Reality approval request source sample file drift")
    if packet.get("source_sample_output_schema") != RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SCHEMA:
        raise CityOpsContractError("Retail Reality approval request source sample schema drift")
    if packet.get("source_sample_output_id") != SAMPLE_OUTPUT_ID:
        raise CityOpsContractError("Retail Reality approval request source sample id drift")
    if packet.get("source_review_decision_digest_sha256") != _canonical_digest(source_decision):
        raise CityOpsContractError("Retail Reality approval request source decision digest drift")
    if packet.get("source_sample_output_digest_sha256") != _canonical_digest(source_sample):
        raise CityOpsContractError("Retail Reality approval request source sample digest drift")
    if RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality approval request safe claim missing")
    for claim in [
        RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
        RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    ]:
        if claim not in packet.get("safe_to_claim", []):
            raise CityOpsContractError("Retail Reality approval request source safe claim missing")
    forbidden_safe = set(packet.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality approval request has forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = (set(source_decision.get("do_not_claim_yet", [])) | set(REQUEST_BLOCKED_CLAIMS)) - set(
        packet.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality approval request missing blocked claims: {sorted(missing_blocked)}"
        )
    if packet.get("still_blocked_claims") != packet.get("do_not_claim_yet"):
        raise CityOpsContractError("Retail Reality approval request blocked claims drift")
    if packet.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("Retail Reality approval request status drift")

    ladder = packet.get("ladder_boundary", {})
    if ladder.get("covered_steps", [])[-1:] != ["human_operator_approval_request"]:
        raise CityOpsContractError("Retail Reality approval request ladder step drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality approval request next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality approval request promoted ladder")

    if packet.get("selected_text_boundary_count") != 1:
        raise CityOpsContractError("Retail Reality approval request must name exactly one boundary")
    boundary = packet.get("selected_text_boundary", {})
    field_values = source_sample["sample_output"]["field_values"]
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("Retail Reality approval request boundary key drift")
    if boundary.get("candidate_text_boundary") != "all_internal_sample_field_values_only":
        raise CityOpsContractError("Retail Reality approval request boundary type drift")
    if boundary.get("candidate_text_fields") != ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Retail Reality approval request boundary fields drift")
    if boundary.get("candidate_text_values") != {
        field: field_values[field] for field in ALLOWED_CUSTOMER_OUTPUT_FIELDS
    }:
        raise CityOpsContractError("Retail Reality approval request boundary values drift")
    if boundary.get("candidate_text_digest_sha256") != _canonical_digest(field_values):
        raise CityOpsContractError("Retail Reality approval request boundary digest drift")
    for flag in [
        "selected_text_boundary_approved",
        "human_operator_approval_recorded",
        "customer_delivery_authorized_by_boundary",
        "publication_authorized_by_boundary",
        "dispatch_authorized_by_boundary",
        "reputation_authorized_by_boundary",
        "exact_gps_or_raw_metadata_authorized_by_boundary",
        "private_context_release_authorized_by_boundary",
        "retail_authority_claims_authorized_by_boundary",
        "worker_doctrine_authorized_by_boundary",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality approval request boundary promoted {flag}")

    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        if packet.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality approval request promoted {flag}")
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality approval request promoted readiness {flag}")
        if boundary.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality approval request boundary promoted readiness {flag}"
            )

    if [item.get("check") for item in packet.get("pre_approval_checks", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("Retail Reality approval request pre-approval checks drift")
    for item in packet.get("pre_approval_checks", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("Retail Reality approval request pre-check not required")
        for flag in ["passed_here", "approval_granted", "customer_delivery_allowed", "publication_allowed"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(f"Retail Reality approval request pre-check promoted {flag}")

    if [
        item.get("check") for item in packet.get("redaction_and_authority_requirements", [])
    ] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("Retail Reality approval request redaction requirements drift")
    for item in packet.get("redaction_and_authority_requirements", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("Retail Reality approval request redaction not required")
        for flag in ["passed_here", "authorizes_delivery_or_publication"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(f"Retail Reality approval request redaction promoted {flag}")

    path = packet.get("authorized_delivery_path", {})
    if path.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("Retail Reality approval request delivery path drift")
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
        "private_retail_context_release_allowed",
        "retail_authority_claims_allowed",
        "worker_doctrine_allowed",
    ]:
        if path.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality approval request delivery path promoted {flag}")
    _assert_no_approval_language(packet)


def _assert_no_approval_language(packet: dict[str, Any]) -> None:
    serialized = json.dumps(packet, sort_keys=True).lower()
    for fragment in FORBIDDEN_APPROVAL_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(
                f"Retail Reality approval request forbidden approval fragment: {fragment}"
            )


def write_retail_reality_human_operator_approval_request(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_retail_reality_human_operator_approval_request()
    path = target_dir / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_retail_reality_human_operator_approval_request(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("Retail Reality approval request must be JSON object")
    sample = _load_source_sample(source_dir)
    decision = _load_source_decision(source_dir)
    _assert_approval_request(packet, source_sample=sample, source_decision=decision)
    return packet
