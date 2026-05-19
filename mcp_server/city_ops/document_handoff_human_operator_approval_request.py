"""Document / Handoff human-operator approval request.

This module is the cautious next rung after the internal Document / Handoff
package-review decision. It creates a pending request for a human operator to
review exactly one package label/text boundary. It is intentionally not a human
approval record, not customer copy, not delivery, not publication, not a public
route/catalog/pilot, not pricing, not queue launch, not dispatch, not
reputation, not live Acontext/runtime parity, not exact GPS/raw metadata
exposure, not legal/notarial/private-identity/acceptance/filing/custody
authority, and not worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .document_handoff_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .document_handoff_package_review_decision import (
    ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS,
    DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME,
    DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
    DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SCHEMA,
    FORBIDDEN_FIELD_CLASSES,
    NEXT_REQUIRED_GATE,
    PACKAGE_REVIEW_BLOCKED_CLAIMS as SOURCE_PACKAGE_REQUIRED_BLOCKED_CLAIMS,
    PACKAGE_REVIEW_DECISION,
    PACKAGE_REVIEW_FALSE_FLAGS,
    SELECTED_INTERNAL_LABEL,
    load_document_handoff_package_review_decision,
)

DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA = (
    "city_ops.document_handoff_human_operator_approval_request.v1"
)
DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME = (
    "document_handoff_human_operator_approval_request.json"
)
DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM = (
    "document_handoff_human_operator_approval_request_landed"
)

REQUEST_ID = "execution_market.aas.document_handoff.human_operator_approval_request.001"
SCOPE = "internal_admin_document_handoff_human_operator_approval_request_only"
SELECTED_TEXT_BOUNDARY_KEY = "document_handoff_internal_package_label"
APPROVAL_REQUEST_STATUS = "pending_human_operator_review_not_approved"
AUTHORIZED_DELIVERY_PATH = "none_until_separate_human_operator_approval_record"

REQUIRED_PRE_APPROVAL_CHECKS = [
    "source_package_review_decision_still_held",
    "selected_text_boundary_exact_value_preserved",
    "allowed_future_fields_still_allowlisted_only",
    "forbidden_authority_classes_still_blocked",
    "privacy_redaction_required_before_any_approval",
    "exact_gps_and_raw_metadata_reverification_required_before_any_approval",
    "legal_notarial_identity_acceptance_filing_custody_language_absent_before_any_approval",
    "authorized_delivery_path_required_but_absent",
    "operator_publish_approval_required_but_absent",
    "customer_delivery_approval_required_but_absent",
]

REDACTION_AND_AUTHORITY_REQUIREMENTS = [
    "exact_gps_removed",
    "raw_metadata_removed",
    "raw_transcript_not_used_as_authority",
    "private_sender_identity_removed",
    "private_recipient_identity_removed",
    "private_operator_context_removed",
    "legal_service_language_absent",
    "notarial_act_language_absent",
    "private_identity_verification_language_absent",
    "guaranteed_acceptance_language_absent",
    "filing_success_language_absent",
    "custody_guarantee_language_absent",
    "dispatch_instruction_language_absent",
    "reputation_receipt_language_absent",
    "worker_copyable_handoff_doctrine_absent",
]

REQUEST_READINESS_FALSE_FLAGS = [
    *PACKAGE_REVIEW_FALSE_FLAGS,
    "human_operator_approval_recorded",
    "selected_text_boundary_approved",
    "pre_approval_checks_passed",
    "redaction_requirements_passed",
    "authority_requirements_passed",
    "authorized_delivery_path_recorded",
    "operator_publish_approval",
    "customer_delivery_approval",
]

REQUEST_BLOCKED_CLAIMS = [
    *SOURCE_PACKAGE_REQUIRED_BLOCKED_CLAIMS,
    "document_handoff_human_operator_approval_recorded",
    "document_handoff_selected_text_boundary_approved",
    "document_handoff_pre_approval_checks_passed",
    "document_handoff_customer_copy_created",
    "document_handoff_customer_copy_ready",
    "document_handoff_authorized_delivery_path_recorded",
    "document_handoff_customer_delivery_approved",
    "document_handoff_publication_approved",
    "document_handoff_public_route_ready",
    "document_handoff_catalog_route_ready",
    "document_handoff_controlled_pilot_ready",
    "document_handoff_public_price_approved",
    "document_handoff_customer_quote_ready",
    "document_handoff_operator_queue_launch_ready",
    "document_handoff_dispatch_enabled",
    "document_handoff_reputation_ready",
    "document_handoff_live_runtime_ready",
    "document_handoff_exact_gps_or_raw_metadata_release_ready",
    "document_handoff_legal_notarial_identity_acceptance_filing_custody_claim_ready",
    "document_handoff_worker_copyable_handoff_doctrine_ready",
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
    "legal_service_ready",
    "notarial_act_ready",
    "private_identity_ready",
    "guaranteed_acceptance_ready",
    "filing_success_ready",
    "custody_guarantee_ready",
    "worker_copyable_doctrine_ready",
}

REQUEST_FALSE_TOP_LEVEL_FLAGS = {
    "human_operator_approval_recorded": False,
    "selected_text_boundary_approved": False,
    "pre_approval_checks_passed": False,
    "redaction_requirements_passed": False,
    "authority_requirements_passed": False,
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
    "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed": False,
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
    return load_document_handoff_package_review_decision(artifact_dir=artifact_dir)


def _assert_source_package_review(decision: dict[str, Any]) -> None:
    if decision.get("schema") != DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("document handoff approval request source schema drift")
    if decision.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("document handoff approval request source family drift")
    if decision.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("document handoff approval request source offer drift")
    if decision.get("package_review_decision") != PACKAGE_REVIEW_DECISION:
        raise CityOpsContractError("document handoff approval request source promoted decision")
    if decision.get("selected_internal_label") != SELECTED_INTERNAL_LABEL:
        raise CityOpsContractError("document handoff approval request source label drift")
    if decision.get("selected_internal_label_customer_copy_approved") is not False:
        raise CityOpsContractError("document handoff approval request source label promoted")
    if decision.get("next_required_gate_before_any_delivery_path") != NEXT_REQUIRED_GATE:
        raise CityOpsContractError("document handoff approval request source next gate drift")
    if decision.get("next_gate_satisfied") is not False:
        raise CityOpsContractError("document handoff approval request source next gate promoted")
    if DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM not in decision.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff approval request source safe claim missing")
    forbidden_safe = set(decision.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"document handoff approval request source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SOURCE_PACKAGE_REQUIRED_BLOCKED_CLAIMS) - set(
        decision.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"document handoff approval request source missing blocked claims: {sorted(missing_blocked)}"
        )
    if decision.get("allowed_future_customer_output_fields") != ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("document handoff approval request source allowed field drift")
    if set(FORBIDDEN_FIELD_CLASSES) - set(decision.get("forbidden_field_classes", [])):
        raise CityOpsContractError("document handoff approval request source forbidden classes drift")
    for flag in PACKAGE_REVIEW_FALSE_FLAGS:
        if decision.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request source promoted readiness {flag}"
            )
    summary = decision.get("package_review_summary", {})
    for flag in [
        "customer_copy_approved",
        "customer_delivery_approved",
        "publication_approved",
        "public_price_or_customer_quote_approved",
        "queue_dispatch_reputation_runtime_gps_legal_worker_doctrine_approved",
    ]:
        if summary.get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request source summary promoted {flag}"
            )
    for row in decision.get("review_questions", []):
        if row.get("approval_granted") is not False:
            raise CityOpsContractError("document handoff approval request source question approved")


def _selected_text_boundary(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": SELECTED_TEXT_BOUNDARY_KEY,
        "package_family_id": source["package_family_id"],
        "offer_id": source["offer_id"],
        "candidate_text_boundary": "internal_package_label_only",
        "candidate_text_value": source["selected_internal_label"],
        "candidate_text_fields": ["selected_internal_label"],
        "approval_request_boundary": (
            "human_operator_may_review_this_exact_document_handoff_label_later_"
            "but_no_approval_is_recorded_here"
        ),
        "source_customer_copy_approved": source["selected_internal_label_customer_copy_approved"],
        "source_next_gate_satisfied": source["next_gate_satisfied"],
        "selected_text_boundary_approved": False,
        "human_operator_approval_recorded": False,
        "customer_delivery_authorized_by_boundary": False,
        "publication_authorized_by_boundary": False,
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
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed": False,
    }


def build_document_handoff_human_operator_approval_request(
    *,
    artifact_dir: Path | None = None,
    source_package_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a pending, no-approval Document / Handoff human-operator request."""

    source = source_package_review or _load_source_package_review(artifact_dir=artifact_dir)
    _assert_source_package_review(source)

    safe_to_claim = _dedupe(
        [
            *source.get("safe_to_claim", []),
            DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUEST_BLOCKED_CLAIMS,
            *source.get("do_not_claim_yet", []),
        ]
    )

    packet: dict[str, Any] = {
        "schema": DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
        "request_id": REQUEST_ID,
        "scope": SCOPE,
        "source_package_review_file": DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME,
        "source_package_review_schema": source["schema"],
        "source_package_review_decision_id": source["decision_id"],
        "source_package_review_digest_sha256": _canonical_digest(source),
        "source_safe_claim": DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
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
            "This packet only asks a human operator to review one exact Document / "
            "Handoff label boundary later. It does not record approval, create "
            "customer copy, authorize delivery, publish, launch a route/catalog/pilot/"
            "queue, dispatch workers, attach reputation, expose exact GPS/raw metadata, "
            "or make legal/notarial/identity/acceptance/filing/custody claims."
        ),
        "next_smallest_proof": (
            "If a human operator approves this exact boundary later, create a separate "
            "approval record that names the exact approved text, passed checks, authorized "
            "delivery path, and still-blocked claims."
        ),
    }
    _assert_approval_request(packet)
    return packet


def _assert_approval_request(packet: dict[str, Any]) -> None:
    if packet.get("schema") != DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("document handoff approval request schema drift")
    if packet.get("request_id") != REQUEST_ID:
        raise CityOpsContractError("document handoff approval request id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("document handoff approval request scope drift")
    if packet.get("source_package_review_file") != DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME:
        raise CityOpsContractError("document handoff approval request source file drift")
    if packet.get("source_package_review_schema") != DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("document handoff approval request source schema drift")
    if packet.get("source_safe_claim") != DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM:
        raise CityOpsContractError("document handoff approval request source safe claim drift")
    if packet.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("document handoff approval request family drift")
    if packet.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("document handoff approval request offer drift")
    if DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff approval request safe claim missing")
    if DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff approval request source safe claim missing")
    forbidden_safe = set(packet.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"document handoff approval request has forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(REQUEST_BLOCKED_CLAIMS) - set(packet.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"document handoff approval request missing blocked claims: {sorted(missing_blocked)}"
        )
    if packet.get("still_blocked_claims") != packet.get("do_not_claim_yet"):
        raise CityOpsContractError("document handoff approval request blocked claims drift")
    if packet.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("document handoff approval request status drift")
    if packet.get("selected_text_boundary_count") != 1:
        raise CityOpsContractError("document handoff approval request must name exactly one boundary")
    boundary = packet.get("selected_text_boundary", {})
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("document handoff approval request boundary key drift")
    if boundary.get("candidate_text_boundary") != "internal_package_label_only":
        raise CityOpsContractError("document handoff approval request boundary type drift")
    if boundary.get("candidate_text_value") != SELECTED_INTERNAL_LABEL:
        raise CityOpsContractError("document handoff approval request boundary value drift")
    for flag in [
        "selected_text_boundary_approved",
        "human_operator_approval_recorded",
        "customer_delivery_authorized_by_boundary",
        "publication_authorized_by_boundary",
        "source_customer_copy_approved",
        "source_next_gate_satisfied",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"document handoff approval request boundary promoted {flag}")
    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        if packet.get(flag) is not expected:
            raise CityOpsContractError(f"document handoff approval request promoted {flag}")
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"document handoff approval request promoted readiness {flag}")
        if boundary.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request boundary promoted readiness {flag}"
            )
    if [item.get("check") for item in packet.get("pre_approval_checks", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("document handoff approval request pre-approval checks drift")
    for item in packet.get("pre_approval_checks", []):
        for flag in [
            "required_before_human_approval",
        ]:
            if item.get(flag) is not True:
                raise CityOpsContractError("document handoff approval request pre-check not required")
        for flag in ["passed_here", "approval_granted", "customer_delivery_allowed", "publication_allowed"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"document handoff approval request pre-check promoted {flag}"
                )
    if [
        item.get("check")
        for item in packet.get("redaction_and_authority_requirements", [])
    ] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("document handoff approval request redaction requirements drift")
    for item in packet.get("redaction_and_authority_requirements", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("document handoff approval request redaction not required")
        for flag in ["passed_here", "authorizes_delivery_or_publication"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"document handoff approval request redaction promoted {flag}"
                )
    path = packet.get("authorized_delivery_path", {})
    if path.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("document handoff approval request delivery path drift")
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
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed",
    ]:
        if path.get(flag) is not False:
            raise CityOpsContractError(f"document handoff approval request delivery path promoted {flag}")


def write_document_handoff_human_operator_approval_request(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_document_handoff_human_operator_approval_request(artifact_dir=target_dir)
    path = target_dir / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def load_document_handoff_human_operator_approval_request(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("document handoff approval request must be JSON object")
    _assert_approval_request(packet)
    return packet
