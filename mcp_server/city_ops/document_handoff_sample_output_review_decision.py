"""Explicit hold decision for the Document / Handoff internal sample output.

This module advances the Document / Handoff adjacent-AAS ladder by exactly one
conservative rung: it records the required explicit decision over the internal
sample output, and the decision is a hold. It does not approve customer copy,
publication, customer delivery, a public catalog, a pilot, a route, dispatch,
live Acontext/runtime parity, ERC-8004 reputation, exact GPS/raw metadata
release, legal/notarial/private-identity/acceptance/filing/custody outcomes, or
worker-copyable handoff doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import READINESS_FALSE_FLAGS
from .contracts import CityOpsContractError
from .document_handoff_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .document_handoff_internal_sample_output import (
    DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME,
    DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
    DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SCHEMA,
    SAMPLE_OUTPUT_ID,
    load_document_handoff_internal_sample_output,
)

DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA = (
    "city_ops.document_handoff_sample_output_review_decision.v1"
)
DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME = (
    "document_handoff_sample_output_review_decision.json"
)
DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM = (
    "document_handoff_sample_output_review_decision_landed"
)

DECISION_ID = "execution_market.aas.document_handoff.sample_output_review_decision.001"
SCOPE = "internal_admin_document_handoff_sample_output_hold_decision_only"
DECISION_STATUS = "explicit_hold_recorded_not_approved_not_publishable"
REVIEW_DECISION = "hold_not_approved_not_publishable"

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
    "explicit_approval_or_hold_decision",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "human_operator_customer_delivery_approval_record_if_authorized",
]

DECISION_BLOCKED_CLAIMS = [
    "sample_output_customer_copy_ready",
    "sample_output_customer_delivery_ready",
    "sample_output_publication_ready",
    "sample_output_catalog_ready",
    "sample_output_controlled_pilot_ready",
    "sample_output_public_route_ready",
    "sample_output_dispatch_ready",
    "sample_output_reputation_ready",
    "sample_output_worker_doctrine_ready",
    "sample_output_live_acontext_ready",
    "sample_output_exact_gps_or_raw_metadata_release_ready",
    "sample_output_legal_service_ready",
    "sample_output_notarial_act_ready",
    "sample_output_private_identity_ready",
    "sample_output_guaranteed_acceptance_ready",
    "sample_output_filing_success_ready",
    "sample_output_custody_guarantee_ready",
    "sample_output_operator_approval_ready",
    "sample_output_customer_delivery_approval_ready",
    "sample_output_publication_approval_ready",
    "sample_output_customer_public_launch_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(DECISION_BLOCKED_CLAIMS) | {
    "customer_copy_ready",
    "customer_output_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "legal_service",
    "notarial_act_without_separate_credential_scope",
    "identity_verification_beyond_scoped_evidence",
    "guaranteed_acceptance",
    "filing_success_ready",
    "custody_guarantee",
    "custody_guarantee_outside_documented_windows",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "dispatch_routing_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_handoff_doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "customer_sample_publication_ready",
    "sample_output_publication_ready",
    "sample_output_approved",
    "sample_output_customer_delivery_approved",
}

DECISION_READINESS_FALSE_FLAGS = [
    "operator_approval_granted",
    "operator_publish_approval",
    "customer_delivery_approval",
    "customer_copy_created",
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_allowed",
    "front_door_sku_ready",
    "sample_output_publishable",
    "sample_output_publication_ready",
    "publication_approved",
    "publish_route_ready",
    "catalog_route_ready",
    "controlled_pilot_authorized",
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
    "legal_service_ready",
    "notarial_act_ready",
    "identity_verification_ready",
    "private_identity_release_ready",
    "guaranteed_acceptance_ready",
    "filing_success_ready",
    "custody_guarantee_ready",
    "customer_public_launch_ready",
    "catalog_or_pilot_readiness_ready",
]

REQUIRED_SOURCE_BLOCKED_CLAIMS = [
    "internal_sample_customer_copy_ready",
    "internal_sample_customer_delivery_ready",
    "internal_sample_publication_ready",
    "internal_sample_catalog_ready",
    "internal_sample_dispatch_ready",
    "internal_sample_reputation_ready",
    "internal_sample_worker_doctrine_ready",
    "internal_sample_live_acontext_ready",
    "internal_sample_exact_gps_or_raw_metadata_release_ready",
    "internal_sample_legal_service_ready",
    "internal_sample_notarial_act_ready",
    "internal_sample_private_identity_ready",
    "internal_sample_guaranteed_acceptance_ready",
    "internal_sample_filing_success_ready",
    "internal_sample_custody_guarantee_ready",
    "internal_sample_operator_approval_ready",
    "internal_sample_hold_decision_ready",
]

REQUIRED_REVIEW_FINDINGS = [
    "sample_consumes_only_schema_gate_artifact",
    "sample_populates_only_allowed_document_handoff_fields",
    "privacy_redaction_notice_is_present",
    "limitations_and_non_guarantees_are_present",
    "legal_notarial_identity_acceptance_filing_and_custody_exclusions_are_present",
    "publication_and_customer_delivery_remain_unapproved",
    "dispatch_reputation_live_acontext_and_worker_doctrine_remain_absent",
    "exact_location_raw_metadata_and_private_identity_claims_remain_absent",
]

HOLD_REASONS = [
    "Internal/admin sample exists only as a wording-shape artifact.",
    "No customer delivery path has been authorized.",
    "No operator publication approval has been granted.",
    "No public catalog, route, controlled pilot, dispatch, or reputation attachment is authorized.",
    "Legal-service, notarial, private-identity, acceptance, filing, and custody claims remain blocked.",
    "Exact-location and raw metadata release remain blocked.",
    "Worker-copyable handoff doctrine remains blocked.",
]

FORBIDDEN_TEXT_FRAGMENTS = [
    "guaranteed approval",
    "guaranteed acceptance",
    "acceptance guaranteed",
    "legal service provided",
    "notarial act completed",
    "identity verified",
    "filing success confirmed",
    "custody guaranteed",
    "latitude",
    "longitude",
    "gps:",
    "raw metadata attached",
    "driver license",
    "passport",
    "erc-8004 reputation receipt",
    "erc8004 reputation receipt",
    "dispatch instruction",
]


def build_document_handoff_sample_output_review_decision(
    *, sample_output: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build a conservative explicit hold decision over the sample output."""

    source = sample_output or load_document_handoff_internal_sample_output()
    _assert_source_sample_is_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source.get("safe_to_claim", []),
            DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source.get("do_not_claim_yet", []),
            *DECISION_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    packet = {
        "schema": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
        "decision_id": DECISION_ID,
        "scope": SCOPE,
        "decision_status": DECISION_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_sample_output_id": source["sample_output_id"],
        "source_sample_output_schema": source["schema"],
        "source_sample_output_file": DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "review_decision": REVIEW_DECISION,
        "explicit_hold_decision_recorded": True,
        "operator_review_recorded": True,
        "operator_approval_granted": False,
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
        "publication_approved": False,
        "sample_output_publishable": False,
        "customer_copy_created": False,
        "customer_copy_ready": False,
        "customer_visible_catalog_ready": False,
        "public_service_catalog_ready": False,
        "controlled_concierge_pilot_ready": False,
        "customer_pilot_exposure_allowed": False,
        "front_door_sku_ready": False,
        "publish_route_ready": False,
        "catalog_route_ready": False,
        "controlled_pilot_authorized": False,
        "network_route_registered": False,
        "public_route_registered": False,
        "dispatch_enabled": False,
        "dispatch_instruction_ready": False,
        "emits_reputation_receipts": False,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "worker_skill_dna_ready": False,
        "worker_copyable_doctrine_ready": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
        "sample_output_boundary": {
            "consumes_only": [DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME],
            "source_sample_review_status": source["sample_output"]["sample_review_status"],
            "source_sample_is_synthetic": source["sample_output"]["synthetic_fixture_only"],
            "source_sample_is_jurisdiction_specific": source["sample_output"]["jurisdiction_specific"],
            "sample_text_approved_for_customer": False,
            "sample_text_publishable": False,
            "customer_delivery_allowed": False,
            "public_route_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "exact_gps_or_raw_metadata_allowed": False,
            "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed": False,
        },
        "review_findings": _build_review_findings(),
        "hold_reasons": list(HOLD_REASONS),
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "decision_readiness": {flag: False for flag in DECISION_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "This records an explicit hold over the Document / Handoff internal sample. "
            "Do not publish it, deliver it to a customer, register a route, dispatch from "
            "it, attach reputation receipts, expose exact GPS/raw metadata, or treat it "
            "as legal-service, notarial, private-identity, acceptance, filing, custody, "
            "catalog, pilot, or customer-delivery readiness."
        ),
        "next_smallest_proof": (
            "If Saúl wants customer exposure later, create a separate human-operator "
            "approval artifact that names the exact sample text, redactions, delivery "
            "path, and still-blocked claims. Default remains hold."
        ),
    }
    _assert_decision_is_conservative(packet, source_sample=source)
    return packet


def write_document_handoff_sample_output_review_decision(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Document / Handoff sample-output hold decision."""

    packet = build_document_handoff_sample_output_review_decision()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_document_handoff_sample_output_review_decision(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the Document / Handoff sample-output hold decision."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("Document / Handoff sample output review decision must be a JSON object")
    _assert_decision_is_conservative(
        packet,
        source_sample=_load_source_sample_for_dir(source_dir),
    )
    return packet


def _load_source_sample_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME).exists():
        return load_document_handoff_internal_sample_output(artifact_dir=source_dir)
    return load_document_handoff_internal_sample_output()


def _build_review_findings() -> list[dict[str, Any]]:
    return [
        {
            "finding": finding,
            "verified": True,
            "approval_granted": False,
            "hold_required": True,
        }
        for finding in REQUIRED_REVIEW_FINDINGS
    ]


def _assert_source_sample_is_conservative(sample: dict[str, Any]) -> None:
    if sample.get("schema") != DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SCHEMA:
        raise CityOpsContractError("Document / Handoff sample decision source schema drift")
    if sample.get("sample_output_id") != SAMPLE_OUTPUT_ID:
        raise CityOpsContractError("Document / Handoff sample decision source id drift")
    if sample.get("scope") != "internal_admin_document_handoff_sample_output_only":
        raise CityOpsContractError("Document / Handoff sample decision source scope drift")
    if sample.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Document / Handoff sample decision source offer drift")
    if DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM not in sample.get("safe_to_claim", []):
        raise CityOpsContractError("Document / Handoff sample decision source safe claim missing")
    ladder = sample.get("ladder_boundary", {})
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff sample decision source promoted readiness")
    if ladder.get("next_required_steps_before_promotion") != ["explicit_approval_or_hold_decision"]:
        raise CityOpsContractError("Document / Handoff sample decision source next step drift")
    missing_blocked = [
        claim for claim in REQUIRED_SOURCE_BLOCKED_CLAIMS if claim not in sample.get("do_not_claim_yet", [])
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"Document / Handoff sample decision source missing blocked claims: {missing_blocked}"
        )
    for flag in READINESS_FALSE_FLAGS:
        if sample.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff sample decision source promoted readiness: {flag}")
    for flag, value in sample.get("sample_output_readiness", {}).items():
        if value is not False:
            raise CityOpsContractError(
                f"Document / Handoff sample decision source promoted sample readiness: {flag}"
            )
    source_contract = sample.get("source_contract", {})
    for flag in [
        "writes_customer_copy",
        "writes_live_acontext",
        "emits_reputation_receipts",
        "enables_dispatch_automation",
        "publishes_worker_doctrine",
        "exposes_exact_gps_or_raw_metadata",
    ]:
        if source_contract.get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff sample decision source contract overclaims: {flag}")
    sample_output = sample.get("sample_output", {})
    if sample_output.get("sample_review_status") != "internal_admin_sample_against_schema_gate_not_customer_copy":
        raise CityOpsContractError("Document / Handoff sample decision source review status drift")
    if sample_output.get("jurisdiction_specific") is not False:
        raise CityOpsContractError("Document / Handoff sample decision source became jurisdiction-specific")
    reviews = sample_output.get("separate_reviews", {})
    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "explicit_hold_or_approval_decision_recorded",
    ]:
        if reviews.get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff sample decision source promoted review flag: {flag}")


def _assert_decision_is_conservative(
    packet: dict[str, Any], *, source_sample: dict[str, Any]
) -> None:
    _assert_source_sample_is_conservative(source_sample)
    if packet.get("schema") != DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("Document / Handoff sample output review decision schema drift")
    if packet.get("decision_id") != DECISION_ID:
        raise CityOpsContractError("Document / Handoff sample output review decision id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("Document / Handoff sample output review decision scope drift")
    if packet.get("decision_status") != DECISION_STATUS:
        raise CityOpsContractError("Document / Handoff sample output review decision status drift")
    if packet.get("source_sample_output_id") != source_sample.get("sample_output_id"):
        raise CityOpsContractError("Document / Handoff sample output review decision source drift")

    _assert_claim_boundaries(packet.get("safe_to_claim", []), packet.get("do_not_claim_yet", []))
    if DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM not in packet.get("safe_to_claim", []):
        raise CityOpsContractError("Document / Handoff sample output review decision safe claim missing")
    missing_blocked = (set(source_sample.get("do_not_claim_yet", [])) | set(DECISION_BLOCKED_CLAIMS)) - set(
        packet.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Document / Handoff sample output review decision missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = packet.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff sample output review decision covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff sample output review decision next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff sample output review decision promoted ladder")

    if packet.get("review_decision") != REVIEW_DECISION:
        raise CityOpsContractError("Document / Handoff sample output review decision changed verdict")
    if packet.get("explicit_hold_decision_recorded") is not True:
        raise CityOpsContractError("Document / Handoff sample output review decision missing explicit hold")
    if packet.get("operator_review_recorded") is not True:
        raise CityOpsContractError("Document / Handoff sample output review decision missing operator review record")
    for flag in DECISION_READINESS_FALSE_FLAGS:
        if packet.get(flag, packet.get("decision_readiness", {}).get(flag)) is not False:
            raise CityOpsContractError(
                f"Document / Handoff sample output review decision promoted readiness: {flag}"
            )
    for flag in READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Document / Handoff sample output review decision promoted base readiness: {flag}"
            )

    boundary = packet.get("sample_output_boundary", {})
    if boundary.get("consumes_only") != [DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME]:
        raise CityOpsContractError("Document / Handoff sample output review decision input drift")
    for flag in [
        "sample_text_approved_for_customer",
        "sample_text_publishable",
        "customer_delivery_allowed",
        "public_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff sample output review decision boundary overclaims: {flag}")

    findings = packet.get("review_findings")
    if not isinstance(findings, list) or [item.get("finding") for item in findings] != REQUIRED_REVIEW_FINDINGS:
        raise CityOpsContractError("Document / Handoff sample output review decision findings drift")
    for item in findings:
        if item.get("verified") is not True:
            raise CityOpsContractError("Document / Handoff sample output review decision finding not verified")
        if item.get("approval_granted") is not False or item.get("hold_required") is not True:
            raise CityOpsContractError("Document / Handoff sample output review decision finding promoted approval")
    if packet.get("hold_reasons") != HOLD_REASONS:
        raise CityOpsContractError("Document / Handoff sample output review decision hold reasons drift")
    if packet.get("still_blocked_claims") != packet.get("do_not_claim_yet"):
        raise CityOpsContractError("Document / Handoff sample output review decision blocked claim mirror drift")
    _assert_no_forbidden_text(packet)


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(
            f"Document / Handoff sample output review decision has forbidden safe claims: {forbidden}"
        )
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(
            f"Document / Handoff sample output review decision claim overlap: {overlap}"
        )


def _assert_no_forbidden_text(packet: dict[str, Any]) -> None:
    serialized = json.dumps(packet, sort_keys=True).lower()
    for fragment in FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(
                f"Document / Handoff sample output review decision forbidden text fragment: {fragment}"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
