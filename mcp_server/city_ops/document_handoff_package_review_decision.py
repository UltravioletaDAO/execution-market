"""Internal Document / Handoff package-review decision.

This module implements the recommended no-human/no-live-runtime AAS slice for
Document / Handoff Logistics. It consumes the existing explicit hold decision
and answers only internal package-review questions: safe internal label,
allowed future evidence fields, forbidden authority language, and the next gate
required before any delivery path exists.

It deliberately does not approve customer copy, customer delivery,
publication, public/catalog routes, pilots, pricing, queues, dispatch,
reputation, live Acontext/runtime parity, exact GPS/raw metadata release,
legal/notarial/private-identity/acceptance/filing/custody claims, or
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .document_handoff_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .document_handoff_sample_output_review_decision import (
    DECISION_BLOCKED_CLAIMS as SOURCE_DECISION_BLOCKED_CLAIMS,
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
    REVIEW_DECISION as SOURCE_REVIEW_DECISION,
    load_document_handoff_sample_output_review_decision,
)

DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SCHEMA = (
    "city_ops.document_handoff_package_review_decision.v1"
)
DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME = (
    "document_handoff_package_review_decision.json"
)
DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM = (
    "document_handoff_package_review_decision_landed"
)

DECISION_ID = "execution_market.aas.document_handoff.package_review_decision.001"
SCOPE = "internal_admin_document_handoff_package_review_decision_only"
SOURCE_POLICY = "consume_only_document_handoff_sample_output_review_decision_json"
PACKAGE_REVIEW_DECISION = "hold_internal_package_review_only_not_customer_copy"
SELECTED_INTERNAL_LABEL = "Document handoff proof run"

ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS = [
    "plain_language_status",
    "handoff_window_summary",
    "chain_of_custody_event_summary",
    "recipient_or_source_type_summary",
    "receipt_or_stamp_summary",
    "failed_handoff_reason",
    "queue_or_wait_boundary",
    "what_was_checked",
    "what_was_not_checked",
    "limitations_and_non_guarantees",
    "recommended_next_action",
    "operator_review_notice",
    "privacy_redaction_notice",
]

FORBIDDEN_FIELD_CLASSES = [
    "exact_gps_or_raw_metadata",
    "raw_transcript_authority",
    "private_operator_sender_or_recipient_context",
    "legal_service_or_legal_advice",
    "notarial_act_or_notary_implied_service",
    "private_identity_verification",
    "guaranteed_acceptance_or_filing_success",
    "custody_guarantee_outside_documented_windows",
    "dispatch_instruction_or_worker_instruction",
    "reputation_receipt_or_credential_claim",
    "worker_copyable_handoff_doctrine",
    "customer_public_launch_or_catalog_pilot_readiness",
]

NEXT_REQUIRED_GATE = (
    "separate_human_operator_approval_artifact_for_one_exact_document_handoff_text_boundary"
)

PACKAGE_REVIEW_FALSE_FLAGS = [
    "package_label_customer_copy_approved",
    "package_label_customer_delivery_approved",
    "package_label_publication_approved",
    "selected_text_boundary_approved",
    "customer_delivery_path_authorized",
    "customer_copy_created",
    "customer_copy_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_route_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "operator_workflow_launch_ready",
    "dispatch_enabled",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "raw_transcript_authority_allowed",
    "private_identity_release_ready",
    "legal_service_ready",
    "notarial_act_ready",
    "guaranteed_acceptance_ready",
    "filing_success_ready",
    "custody_guarantee_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
]

PACKAGE_REVIEW_BLOCKED_CLAIMS = [
    *SOURCE_DECISION_BLOCKED_CLAIMS,
    "document_handoff_package_label_customer_copy_ready",
    "document_handoff_customer_delivery_ready",
    "document_handoff_publication_ready",
    "document_handoff_public_route_ready",
    "document_handoff_catalog_ready",
    "document_handoff_controlled_pilot_ready",
    "document_handoff_front_door_sku_ready",
    "document_handoff_public_price_ready",
    "document_handoff_customer_quote_ready",
    "document_handoff_operator_queue_launch_ready",
    "document_handoff_dispatch_ready",
    "document_handoff_reputation_receipts_ready",
    "document_handoff_live_acontext_ready",
    "document_handoff_runtime_parity_ready",
    "document_handoff_exact_gps_or_raw_metadata_release_ready",
    "document_handoff_raw_transcript_authority_ready",
    "document_handoff_private_identity_release_ready",
    "document_handoff_legal_service_ready",
    "document_handoff_notarial_act_ready",
    "document_handoff_guaranteed_acceptance_ready",
    "document_handoff_filing_success_ready",
    "document_handoff_custody_guarantee_ready",
    "document_handoff_worker_skill_dna_ready",
    "document_handoff_worker_copyable_doctrine_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(PACKAGE_REVIEW_BLOCKED_CLAIMS) | set(PACKAGE_REVIEW_FALSE_FLAGS) | {
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approval",
    "publication_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "controlled_pilot_ready",
    "dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "legal_service",
    "notarial_act",
    "identity_verified",
    "guaranteed_acceptance",
    "filing_success",
    "custody_guarantee",
    "worker_copyable_doctrine_ready",
}

REQUIRED_SOURCE_FALSE_FLAGS = [
    "customer_copy_ready",
    "customer_delivery_approval",
    "publication_approved",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
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


def _load_source_decision(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_document_handoff_sample_output_review_decision(artifact_dir=artifact_dir)


def _assert_source_decision(decision: dict[str, Any]) -> None:
    if decision.get("schema") != DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("package review source decision schema drift")
    if decision.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("package review source family drift")
    if decision.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("package review source offer drift")
    if decision.get("review_decision") != SOURCE_REVIEW_DECISION:
        raise CityOpsContractError("package review source decision promoted from hold")
    if decision.get("explicit_hold_decision_recorded") is not True:
        raise CityOpsContractError("package review source hold missing")
    if DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM not in decision.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("package review source safe claim missing")
    forbidden_safe = set(decision.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"package review source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SOURCE_DECISION_BLOCKED_CLAIMS) - set(
        decision.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"package review source missing blocked claims: {sorted(missing_blocked)}"
        )
    for container in ["readiness", "decision_readiness"]:
        flags = decision.get(container, {})
        for flag in REQUIRED_SOURCE_FALSE_FLAGS:
            if flag in flags and flags.get(flag) is not False:
                raise CityOpsContractError(
                    f"package review source promoted {container} flag {flag}"
                )
    boundary = decision.get("sample_output_boundary", {})
    required_false = [
        "sample_text_approved_for_customer",
        "sample_text_publishable",
        "customer_delivery_allowed",
        "public_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed",
    ]
    for flag in required_false:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"package review source boundary promoted {flag}")


def _build_review_questions() -> list[dict[str, Any]]:
    return [
        {
            "question": "Which internal label remains safest?",
            "answer": SELECTED_INTERNAL_LABEL,
            "decision": "internal_label_only_not_customer_copy",
            "approval_granted": False,
        },
        {
            "question": "Which handoff evidence fields may remain in a future schema?",
            "answer": list(ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS),
            "decision": "field_allowlist_only_no_customer_output_created",
            "approval_granted": False,
        },
        {
            "question": "Which authority classes remain forbidden?",
            "answer": list(FORBIDDEN_FIELD_CLASSES),
            "decision": "forbidden_classes_stay_blocked",
            "approval_granted": False,
        },
        {
            "question": "What exact next gate is required before any delivery path exists?",
            "answer": NEXT_REQUIRED_GATE,
            "decision": "separate_human_operator_artifact_required_before_promotion",
            "approval_granted": False,
        },
    ]


def build_document_handoff_package_review_decision(
    *,
    artifact_dir: Path | None = None,
    source_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the internal/admin Document / Handoff package-review decision."""

    source = source_decision or _load_source_decision(artifact_dir=artifact_dir)
    _assert_source_decision(source)

    safe_to_claim = _dedupe(
        [
            *source.get("safe_to_claim", []),
            DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *PACKAGE_REVIEW_BLOCKED_CLAIMS,
            *source.get("do_not_claim_yet", []),
        ]
    )

    decision = {
        "schema": DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SCHEMA,
        "decision_id": DECISION_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "source_decision_file": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
        "source_decision_schema": source["schema"],
        "source_decision_id": source["decision_id"],
        "source_decision_digest_sha256": _canonical_digest(source),
        "source_safe_claim": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "package_review_decision": PACKAGE_REVIEW_DECISION,
        "selected_internal_label": SELECTED_INTERNAL_LABEL,
        "selected_internal_label_customer_copy_approved": False,
        "allowed_future_customer_output_fields": list(ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS),
        "forbidden_field_classes": list(FORBIDDEN_FIELD_CLASSES),
        "next_required_gate_before_any_delivery_path": NEXT_REQUIRED_GATE,
        "next_gate_satisfied": False,
        "review_questions": _build_review_questions(),
        "package_review_summary": {
            "source_hold_preserved": True,
            "internal_label_reviewed": True,
            "allowed_future_fields_named": True,
            "forbidden_authority_classes_named": True,
            "next_gate_named": True,
            "customer_copy_approved": False,
            "customer_delivery_approved": False,
            "publication_approved": False,
            "public_price_or_customer_quote_approved": False,
            "queue_dispatch_reputation_runtime_gps_legal_worker_doctrine_approved": False,
        },
        "readiness": {flag: False for flag in PACKAGE_REVIEW_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this as an internal Document / Handoff package-review decision only. "
            "It may inform a future human approval brief, but it does not authorize "
            "customer delivery, publication, route/catalog/pilot exposure, pricing, "
            "queue launch, dispatch, reputation, live runtime, exact metadata release, "
            "legal/notarial/identity/acceptance/filing/custody claims, or worker doctrine."
        ),
    }
    _assert_package_review_decision(decision)
    return decision


def _assert_package_review_decision(decision: dict[str, Any]) -> None:
    if decision.get("schema") != DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("document handoff package review schema drift")
    if decision.get("decision_id") != DECISION_ID:
        raise CityOpsContractError("document handoff package review id drift")
    if decision.get("scope") != SCOPE:
        raise CityOpsContractError("document handoff package review scope drift")
    if decision.get("source_policy") != SOURCE_POLICY:
        raise CityOpsContractError("document handoff package review source policy drift")
    if decision.get("source_decision_file") != DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME:
        raise CityOpsContractError("document handoff package review source file drift")
    if decision.get("source_decision_schema") != DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("document handoff package review source schema drift")
    if decision.get("source_safe_claim") != DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM:
        raise CityOpsContractError("document handoff package review source safe claim drift")
    if decision.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("document handoff package review family drift")
    if decision.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("document handoff package review offer drift")
    if DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_SAFE_CLAIM not in decision.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff package review safe claim missing")
    if DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM not in decision.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff package review source safe claim missing")
    forbidden_safe = set(decision.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"document handoff package review has forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PACKAGE_REVIEW_BLOCKED_CLAIMS) - set(
        decision.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"document handoff package review missing blocked claims: {sorted(missing_blocked)}"
        )
    if decision.get("still_blocked_claims") != decision.get("do_not_claim_yet"):
        raise CityOpsContractError("document handoff package review blocked claims drift")
    if decision.get("package_review_decision") != PACKAGE_REVIEW_DECISION:
        raise CityOpsContractError("document handoff package review decision promoted")
    if decision.get("selected_internal_label") != SELECTED_INTERNAL_LABEL:
        raise CityOpsContractError("document handoff package review label drift")
    if decision.get("selected_internal_label_customer_copy_approved") is not False:
        raise CityOpsContractError("document handoff package label promoted to customer copy")
    if decision.get("allowed_future_customer_output_fields") != ALLOWED_FUTURE_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("document handoff allowed field drift")
    forbidden_fields = set(decision.get("forbidden_field_classes", []))
    missing_forbidden_fields = set(FORBIDDEN_FIELD_CLASSES) - forbidden_fields
    if missing_forbidden_fields:
        raise CityOpsContractError(
            f"document handoff forbidden field drift: {sorted(missing_forbidden_fields)}"
        )
    if decision.get("next_required_gate_before_any_delivery_path") != NEXT_REQUIRED_GATE:
        raise CityOpsContractError("document handoff next gate drift")
    if decision.get("next_gate_satisfied") is not False:
        raise CityOpsContractError("document handoff next gate promoted")
    for flag in PACKAGE_REVIEW_FALSE_FLAGS:
        if decision.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"document handoff package review promoted {flag}")
    summary = decision.get("package_review_summary", {})
    required_true = [
        "source_hold_preserved",
        "internal_label_reviewed",
        "allowed_future_fields_named",
        "forbidden_authority_classes_named",
        "next_gate_named",
    ]
    for flag in required_true:
        if summary.get(flag) is not True:
            raise CityOpsContractError(f"document handoff package review summary drift {flag}")
    required_false = [
        "customer_copy_approved",
        "customer_delivery_approved",
        "publication_approved",
        "public_price_or_customer_quote_approved",
        "queue_dispatch_reputation_runtime_gps_legal_worker_doctrine_approved",
    ]
    for flag in required_false:
        if summary.get(flag) is not False:
            raise CityOpsContractError(f"document handoff package review summary promoted {flag}")
    for row in decision.get("review_questions", []):
        if row.get("approval_granted") is not False:
            raise CityOpsContractError("document handoff package review question promoted")


def write_document_handoff_package_review_decision(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    decision = build_document_handoff_package_review_decision(artifact_dir=target_dir)
    path = target_dir / DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME
    path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    return path


def load_document_handoff_package_review_decision(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / DOCUMENT_HANDOFF_PACKAGE_REVIEW_DECISION_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        decision = json.load(fh)
    _assert_package_review_decision(decision)
    return decision
