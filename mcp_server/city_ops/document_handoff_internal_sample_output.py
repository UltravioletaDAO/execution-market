"""Document / Handoff adjacent-AAS internal/admin sample output.

This module advances the Document / Handoff package by exactly one conservative
rung: from the customer-output schema gate to one internal/admin sample output
for the document_handoff_proof_run. The sample consumes only the persisted
schema-gate artifact, populates only allowed schema fields, and remains
synthetic and non-jurisdiction-specific. It is not customer copy, not
publication approval, not a catalog or pilot, not dispatch, not live
Acontext/runtime parity, not ERC-8004 reputation, not exact GPS/raw metadata
exposure, not a legal/notarial/private-identity/acceptance/filing/custody
claim, and not worker-copyable handoff doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import READINESS_FALSE_FLAGS
from .contracts import CityOpsContractError
from .document_handoff_customer_output_schema_gate import (
    ALLOWED_CUSTOMER_OUTPUT_FIELDS,
    DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME,
    DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA,
    FORBIDDEN_CUSTOMER_OUTPUT_FIELDS,
    GATE_ID,
    load_document_handoff_customer_output_schema_gate,
)
from .document_handoff_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID

DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SCHEMA = (
    "city_ops.document_handoff_internal_sample_output.v1"
)
DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME = (
    "document_handoff_internal_sample_output.json"
)
DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM = (
    "document_handoff_internal_sample_output_landed"
)

SAMPLE_OUTPUT_ID = "execution_market.aas.document_handoff.internal_sample_output.001"
SCOPE = "internal_admin_document_handoff_sample_output_only"
SAMPLE_STATUS = "internal_sample_output_landed_not_customer_copy_not_public_not_approved"

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
]
NEXT_REQUIRED_LADDER_STEPS = ["explicit_approval_or_hold_decision"]

SAMPLE_OUTPUT_BLOCKED_CLAIMS = [
    "internal_sample_customer_copy_ready",
    "internal_sample_customer_delivery_ready",
    "internal_sample_publication_ready",
    "internal_sample_catalog_ready",
    "internal_sample_controlled_pilot_ready",
    "internal_sample_public_route_ready",
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

FORBIDDEN_SAFE_CLAIMS = set(SAMPLE_OUTPUT_BLOCKED_CLAIMS) | {
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
}

_SAMPLE_READINESS_FALSE_FLAGS = [
    "customer_copy_created",
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_allowed",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
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
    "explicit_hold_or_approval_decision_recorded",
]

REQUIRED_SAMPLE_REVIEW_FLAGS = [
    "privacy_redaction_review_passed",
    "limitations_preserved_review_passed",
    "non_guarantee_language_review_passed",
    "legal_notarial_and_custody_exclusion_review_passed",
]

FORBIDDEN_SAMPLE_KEYS = set(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS) | {
    "task_id_or_local_case_reference",
    "offer_type",
    "customer_private_name",
    "customer_contact_details",
    "sender_private_identity",
    "recipient_private_identity",
    "jurisdiction_name",
    "office_private_contact",
    "dispatch_assignment",
    "worker_instruction",
}

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

SAMPLE_FIELD_VALUES = {
    "plain_language_status": (
        "Internal review sample: the synthetic source supports a cautious note that "
        "a handoff attempt was documented within a bounded handoff window. This is "
        "not proof of acceptance, filing, custody, legal service, or notarial action."
    ),
    "handoff_window_summary": (
        "The reviewed synthetic artifact describes a bounded pickup and drop-off "
        "window only; it does not expose exact addresses, exact coordinates, or raw "
        "source metadata."
    ),
    "chain_of_custody_event_summary": (
        "A scoped chain-of-custody event summary was observed for internal review: "
        "source prepared, handoff attempted, and outcome recorded at a high level."
    ),
    "recipient_or_source_type_summary": (
        "Recipient/source details are summarized by generic type only, with private "
        "identity and contact details withheld."
    ),
    "receipt_or_stamp_summary": (
        "The synthetic source includes a receipt/stamp-style signal summary, but this "
        "sample does not treat it as official acceptance or a notarial act."
    ),
    "failed_handoff_reason": (
        "If the handoff is incomplete, the only retained reason is a plain-language "
        "operational reason from the synthetic review, not a legal conclusion."
    ),
    "queue_or_wait_boundary": (
        "Queue/wait language is limited to the reviewed handoff window and is not a "
        "promise of service timing, acceptance, filing outcome, or custody status."
    ),
    "what_was_checked": [
        "Whether the reviewed synthetic artifact described the handoff window and event sequence.",
        "Whether the wording stayed inside the Document / Handoff schema-gate allowed fields.",
        "Whether privacy, limitation, non-guarantee, and operator-review notices remained present.",
    ],
    "what_was_not_checked": [
        "No legal-service, notarial, private-identity, guaranteed-acceptance, filing-success, or custody-guarantee conclusion was checked or produced.",
        "No exact location, raw metadata, raw transcript, private contact, or private identity detail was checked for release.",
        "No dispatch path, worker instruction, public route, catalog entry, pilot, or reputation receipt was created.",
    ],
    "limitations_and_non_guarantees": [
        "Internal/admin sample only; not customer-ready copy and not a public handoff report.",
        "Based on a synthetic non-jurisdiction-specific fixture, not live municipal, courier, court, agency, or notarial data.",
        "Does not promise acceptance, filing outcome, legal adequacy, notarial status, identity verification, custody status, or service timing.",
        "A separate explicit hold/approval decision is required before any customer-visible use.",
    ],
    "recommended_next_action": (
        "Keep this sample held for internal review. The next safe step is a separate "
        "explicit hold/approval decision over this exact sample, not publication."
    ),
    "operator_review_notice": (
        "Internal/admin sample only. Operator review has checked wording boundaries, "
        "but no customer delivery, public posting, catalog, pilot, dispatch, reputation, "
        "legal-service, notarial, identity, acceptance, filing, or custody readiness is approved."
    ),
    "privacy_redaction_notice": (
        "Privacy-sensitive details, private sender/recipient identity, private contacts, "
        "exact-location data, source metadata blobs, and raw transcripts are excluded from this sample."
    ),
}


def build_document_handoff_internal_sample_output(
    *, schema_gate: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one conservative Document / Handoff internal/admin sample output."""

    gate = schema_gate or load_document_handoff_customer_output_schema_gate()
    _assert_source_gate(gate)

    safe_to_claim = _dedupe(
        [
            *gate.get("safe_to_claim", []),
            DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *gate.get("do_not_claim_yet", []),
            *SAMPLE_OUTPUT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    sample = {
        "schema": DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SCHEMA,
        "sample_output_id": SAMPLE_OUTPUT_ID,
        "scope": SCOPE,
        "sample_status": SAMPLE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_schema_gate_id": gate["gate_id"],
        "source_schema_gate_schema": gate["schema"],
        "source_schema_gate_file": DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "source_contract": {
            "consumes_only": [DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME],
            "source_loader": "load_document_handoff_customer_output_schema_gate",
            "source_is_schema_gate_only": True,
            "reads_operator_surface_directly": False,
            "reads_raw_review_fixture": False,
            "reads_raw_transcripts": False,
            "reads_raw_metadata": False,
            "reads_private_operator_context": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "emits_reputation_receipts": False,
            "enables_dispatch_automation": False,
            "publishes_worker_doctrine": False,
            "exposes_exact_gps_or_raw_metadata": False,
        },
        "sample_output": {
            "sample_review_status": "internal_admin_sample_against_schema_gate_not_customer_copy",
            "sample_offer": OFFER_ID,
            "jurisdiction_specific": False,
            "synthetic_fixture_only": True,
            "allowed_customer_output_fields": list(ALLOWED_CUSTOMER_OUTPUT_FIELDS),
            "field_values": dict(SAMPLE_FIELD_VALUES),
            "forbidden_customer_output_fields_absent": list(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS),
            "separate_reviews": {
                "privacy_redaction_review_passed": True,
                "limitations_preserved_review_passed": True,
                "non_guarantee_language_review_passed": True,
                "legal_notarial_and_custody_exclusion_review_passed": True,
                "operator_publish_approval": False,
                "customer_delivery_approval": False,
                "explicit_hold_or_approval_decision_recorded": False,
            },
        },
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "sample_output_readiness": {flag: False for flag in _SAMPLE_READINESS_FALSE_FLAGS},
        "sample_output_checks": [
            {
                "check_id": check_id,
                "status": "passed_for_internal_sample_only",
                "blocks_promotion_until_explicit_decision": True,
            }
            for check_id in [
                "source_schema_gate_safe_claim_present",
                "sample_consumes_only_customer_output_schema_gate",
                "sample_populates_only_allowed_schema_fields",
                "privacy_redaction_notice_preserved",
                "limitations_and_non_guarantees_preserved",
                "customer_public_catalog_pilot_dispatch_reputation_live_acontext_still_blocked",
                "legal_notarial_private_identity_acceptance_filing_custody_gps_raw_metadata_and_worker_doctrine_claims_still_blocked",
                "next_step_is_explicit_hold_or_approval_decision_not_publication",
            ]
        ],
        "operator_instruction": (
            "Use this only as an internal/admin wording-shape sample for Document / Handoff. "
            "Do not publish it, route it, dispatch from it, attach reputation receipts, "
            "expose exact GPS/raw metadata, or treat it as legal-service, notarial, "
            "private-identity, guaranteed-acceptance, filing, custody, catalog, pilot, "
            "customer-delivery, or worker-doctrine readiness."
        ),
        "next_smallest_proof": (
            "Record a separate explicit hold/approval decision over this sample. Default "
            "to hold; this is not publication. Do not publish, route, dispatch, attach "
            "reputation receipts, expose exact GPS/raw metadata, or claim customer/catalog/"
            "pilot/legal/notarial/private-identity/acceptance/filing/custody readiness."
        ),
    }
    _assert_sample_packet_is_conservative(sample, source_gate=gate)
    return sample


def write_document_handoff_internal_sample_output(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Document / Handoff internal/admin sample output."""

    sample = build_document_handoff_internal_sample_output()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME
    path.write_text(json.dumps(sample, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_document_handoff_internal_sample_output(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Document / Handoff sample output."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        sample = json.load(fh)
    if not isinstance(sample, dict):
        raise CityOpsContractError("Document / Handoff internal sample output must be a JSON object")
    _assert_sample_packet_is_conservative(
        sample,
        source_gate=_load_source_schema_gate_for_dir(source_dir),
    )
    return sample


def _load_source_schema_gate_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME).exists():
        return load_document_handoff_customer_output_schema_gate(artifact_dir=source_dir)
    return load_document_handoff_customer_output_schema_gate()


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("Document / Handoff internal sample source gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("Document / Handoff internal sample source gate id drift")
    if gate.get("scope") != "internal_admin_customer_output_schema_gate_only":
        raise CityOpsContractError("Document / Handoff internal sample source gate scope drift")
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Document / Handoff internal sample source family drift")
    if gate.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Document / Handoff internal sample source offer drift")
    if DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("Document / Handoff internal sample source safe claim missing")
    ladder = gate.get("ladder_boundary", {})
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff internal sample source promoted readiness")
    if ladder.get("next_required_steps_before_promotion") != [
        "internal_sample_output",
        "explicit_approval_or_hold_decision",
    ]:
        raise CityOpsContractError("Document / Handoff internal sample source next step drift")
    schema_review = gate.get("schema_review", {})
    if schema_review.get("allowed_customer_output_fields") != ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Document / Handoff internal sample source allowed field drift")
    if schema_review.get("forbidden_customer_output_fields") != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Document / Handoff internal sample source forbidden field drift")
    for flag in READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff internal sample source promoted readiness: {flag}")
    for flag, value in gate.get("schema_gate_readiness", {}).items():
        if value is not False:
            raise CityOpsContractError(f"Document / Handoff internal sample source promoted schema readiness: {flag}")
    for claim in [
        "document_handoff_customer_sample_output_ready",
        "document_handoff_catalog_or_pilot_readiness_ready",
        "schema_gate_dispatch_ready",
        "schema_gate_reputation_ready",
        "schema_gate_exact_gps_or_raw_metadata_release_ready",
        "schema_gate_legal_service_ready",
        "schema_gate_notarial_act_ready",
        "schema_gate_identity_verification_ready",
        "schema_gate_guaranteed_acceptance_ready",
        "schema_gate_filing_success_ready",
        "schema_gate_custody_guarantee_ready",
        "schema_gate_worker_doctrine_ready",
    ]:
        if claim not in gate.get("do_not_claim_yet", []):
            raise CityOpsContractError(f"Document / Handoff internal sample source missing blocked claim: {claim}")


def _assert_sample_packet_is_conservative(
    sample: dict[str, Any], *, source_gate: dict[str, Any]
) -> None:
    _assert_source_gate(source_gate)
    if sample.get("schema") != DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SCHEMA:
        raise CityOpsContractError("Document / Handoff internal sample schema drift")
    if sample.get("sample_output_id") != SAMPLE_OUTPUT_ID:
        raise CityOpsContractError("Document / Handoff internal sample id drift")
    if sample.get("scope") != SCOPE:
        raise CityOpsContractError("Document / Handoff internal sample scope drift")
    if sample.get("sample_status") != SAMPLE_STATUS:
        raise CityOpsContractError("Document / Handoff internal sample status drift")
    if sample.get("source_schema_gate_id") != source_gate.get("gate_id"):
        raise CityOpsContractError("Document / Handoff internal sample source gate drift")
    if sample.get("source_schema_gate_file") != DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME:
        raise CityOpsContractError("Document / Handoff internal sample source file drift")

    safe_to_claim = list(sample.get("safe_to_claim", []))
    do_not_claim_yet = list(sample.get("do_not_claim_yet", []))
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    if DOCUMENT_HANDOFF_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("Document / Handoff internal sample safe claim missing")
    if DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("Document / Handoff internal sample inherited schema gate claim missing")
    missing_blocked = (set(source_gate.get("do_not_claim_yet", [])) | set(SAMPLE_OUTPUT_BLOCKED_CLAIMS)) - set(
        do_not_claim_yet
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Document / Handoff internal sample missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = sample.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff internal sample covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff internal sample next step drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff internal sample promoted readiness")

    source_contract = sample.get("source_contract", {})
    if source_contract.get("consumes_only") != [DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME]:
        raise CityOpsContractError("Document / Handoff internal sample input drift")
    for flag in (
        "reads_operator_surface_directly",
        "reads_raw_review_fixture",
        "reads_raw_transcripts",
        "reads_raw_metadata",
        "reads_private_operator_context",
        "writes_customer_copy",
        "writes_live_acontext",
        "emits_reputation_receipts",
        "enables_dispatch_automation",
        "publishes_worker_doctrine",
        "exposes_exact_gps_or_raw_metadata",
    ):
        if source_contract.get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff internal sample source contract overclaims: {flag}")

    _assert_sample_output_is_conservative(sample.get("sample_output", {}))

    for flag in READINESS_FALSE_FLAGS:
        if sample.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff internal sample promoted readiness: {flag}")
    for flag in _SAMPLE_READINESS_FALSE_FLAGS:
        if sample.get("sample_output_readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff internal sample promoted sample readiness: {flag}")

    checks = sample.get("sample_output_checks")
    if not isinstance(checks, list) or len(checks) != 8:
        raise CityOpsContractError("Document / Handoff internal sample checks drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_sample_only":
            raise CityOpsContractError("Document / Handoff internal sample check status drift")
        if item.get("blocks_promotion_until_explicit_decision") is not True:
            raise CityOpsContractError("Document / Handoff internal sample stopped blocking promotion")

    _assert_no_forbidden_text(sample)


def _assert_sample_output_is_conservative(sample_output: dict[str, Any]) -> None:
    if sample_output.get("sample_review_status") != "internal_admin_sample_against_schema_gate_not_customer_copy":
        raise CityOpsContractError("Document / Handoff internal sample review status drift")
    if sample_output.get("sample_offer") != OFFER_ID:
        raise CityOpsContractError("Document / Handoff internal sample offer drift")
    if sample_output.get("jurisdiction_specific") is not False:
        raise CityOpsContractError("Document / Handoff internal sample became jurisdiction-specific")
    if sample_output.get("synthetic_fixture_only") is not True:
        raise CityOpsContractError("Document / Handoff internal sample stopped being synthetic-only")
    if sample_output.get("allowed_customer_output_fields") != ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Document / Handoff internal sample allowed fields drift")
    if sample_output.get("forbidden_customer_output_fields_absent") != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Document / Handoff internal sample forbidden absent fields drift")
    values = sample_output.get("field_values")
    if not isinstance(values, dict):
        raise CityOpsContractError("Document / Handoff internal sample missing field values")
    if set(values.keys()) != set(ALLOWED_CUSTOMER_OUTPUT_FIELDS):
        raise CityOpsContractError("Document / Handoff internal sample populated disallowed field")
    forbidden_keys = sorted(FORBIDDEN_SAMPLE_KEYS & set(values.keys()))
    if forbidden_keys:
        raise CityOpsContractError(f"Document / Handoff internal sample included forbidden keys: {forbidden_keys}")
    _assert_review_flags(sample_output.get("separate_reviews", {}))


def _assert_review_flags(review: dict[str, Any]) -> None:
    if not isinstance(review, dict):
        raise CityOpsContractError("Document / Handoff internal sample missing separate reviews")
    missing = [flag for flag in REQUIRED_SAMPLE_REVIEW_FLAGS if review.get(flag) is not True]
    if missing:
        raise CityOpsContractError(f"Document / Handoff internal sample missing review gates: {missing}")
    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "explicit_hold_or_approval_decision_recorded",
    ]:
        if review.get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff internal sample promoted review flag: {flag}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(f"Document / Handoff internal sample has forbidden safe claims: {forbidden}")
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(f"Document / Handoff internal sample claim overlap: {overlap}")


def _assert_no_forbidden_text(sample: dict[str, Any]) -> None:
    serialized = json.dumps(sample, sort_keys=True).lower()
    for fragment in FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(f"Document / Handoff internal sample forbidden text fragment: {fragment}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
