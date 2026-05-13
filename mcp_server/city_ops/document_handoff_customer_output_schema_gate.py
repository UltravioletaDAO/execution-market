"""Document / Handoff adjacent-AAS customer-output schema gate.

This module advances the Document / Handoff adjacent package by exactly one rung:
from a read-only internal/admin operator surface to a conservative schema gate
for future customer output. It defines permitted/forbidden customer-output
fields only. It does not create customer copy, publish a route, authorize a
pilot, dispatch work, attach reputation receipts, expose exact GPS/raw metadata,
claim legal/notarial/identity/acceptance/filing/custody outcomes, or create worker-copyable handoff
doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    READINESS_FALSE_FLAGS,
)
from .document_handoff_fixture_review_gate import (
    ARTIFACT_DIR,
    DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
)
from .document_handoff_internal_package_record import (
    DOCUMENT_HANDOFF_INTERNAL_PACKAGE_RECORD_FILENAME,
    DOCUMENT_HANDOFF_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
)
from .document_handoff_local_reviewed_fixture import (
    DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
)
from .document_handoff_operator_read_surface import (
    DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME,
    DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_SCHEMA,
    SURFACE_ID,
    load_document_handoff_operator_read_surface,
)
from .contracts import CityOpsContractError

DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA = (
    "city_ops.document_handoff_customer_output_schema_gate.v1"
)
DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME = (
    "document_handoff_customer_output_schema_gate.json"
)
DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM = (
    "document_handoff_customer_output_schema_gate_landed"
)

GATE_ID = "execution_market.aas.document_handoff.customer_output_schema_gate.001"
SCOPE = "internal_admin_customer_output_schema_gate_only"
GATE_STATUS = "schema_gate_landed_not_customer_copy_not_public_not_approved"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

ALLOWED_CUSTOMER_OUTPUT_FIELDS = [
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

FORBIDDEN_CUSTOMER_OUTPUT_FIELDS = [
    "exact_gps_coordinates",
    "raw_metadata_blob",
    "raw_transcript_as_authority",
    "private_operator_context",
    "private_sender_identity",
    "private_recipient_identity",
    "legal_service_claim",
    "notarial_act_claim",
    "identity_verification_claim",
    "guaranteed_acceptance_claim",
    "filing_success_claim",
    "custody_guarantee_claim",
    "dispatch_instruction_or_assignment",
    "erc8004_reputation_receipt",
    "worker_copyable_handoff_doctrine",
    "customer_public_launch_readiness_claim",
    "catalog_or_pilot_readiness_claim",
]

SCHEMA_GATE_BLOCKED_CLAIMS = [
    "schema_gate_customer_copy_ready",
    "schema_gate_customer_delivery_ready",
    "schema_gate_publication_ready",
    "schema_gate_catalog_ready",
    "schema_gate_controlled_pilot_ready",
    "schema_gate_public_route_ready",
    "schema_gate_dispatch_ready",
    "schema_gate_reputation_ready",
    "schema_gate_worker_doctrine_ready",
    "schema_gate_live_acontext_ready",
    "schema_gate_exact_gps_or_raw_metadata_release_ready",
    "schema_gate_legal_service_ready",
    "schema_gate_notarial_act_ready",
    "schema_gate_identity_verification_ready",
    "schema_gate_guaranteed_acceptance_ready",
    "schema_gate_filing_success_ready",
    "schema_gate_custody_guarantee_ready",
    "document_handoff_customer_public_launch_ready",
    "document_handoff_customer_sample_output_ready",
    "document_handoff_customer_delivery_approval_ready",
    "document_handoff_catalog_or_pilot_readiness_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(SCHEMA_GATE_BLOCKED_CLAIMS) | {
    "customer_copy_ready",
    "customer_output_ready",
    "customer_output_schema_ready",
    "document_handoff_customer_output_schema_ready",
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
}

_SCHEMA_FALSE_FLAGS = [
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
    "legal_service_ready",
    "notarial_act_ready",
    "identity_verification_ready",
    "guaranteed_acceptance_ready",
    "filing_success_ready",
    "custody_guarantee_ready",
    "customer_public_launch_ready",
    "catalog_or_pilot_readiness_ready",
]

REQUIRED_INHERITED_SAFE_CLAIMS = [
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_SAFE_CLAIM,
]


def build_document_handoff_customer_output_schema_gate(
    *, operator_surface: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the conservative Document / Handoff customer-output schema gate.

    The gate consumes only the persisted/operator-surface builder payload and
    records a future customer-output field boundary. It is not customer copy,
    launch readiness, approval, routing, dispatch, or reputation evidence.
    """

    source_surface = operator_surface or load_document_handoff_operator_read_surface()
    _assert_source_surface_is_conservative(source_surface)

    safe_to_claim = _dedupe(
        [
            *source_surface.get("safe_to_claim", []),
            DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_surface.get("do_not_claim_yet", []),
            *SCHEMA_GATE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    gate = {
        "schema": DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA,
        "gate_id": GATE_ID,
        "scope": SCOPE,
        "gate_status": GATE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_surface_id": source_surface["surface_id"],
        "source_surface_schema": source_surface["schema"],
        "source_surface_file": DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME,
        "source_safe_claims_inherited": list(REQUIRED_INHERITED_SAFE_CLAIMS),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "source_contract": {
            "consumes_only": [DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME],
            "source_builder": "build_document_handoff_operator_read_surface",
            "source_is_read_only_operator_surface": True,
            "source_operator_cards_used_as_schema_inputs_only": True,
            "source_payload_reinterpreted_as_customer_copy": False,
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
        "schema_review": {
            "review_status": "allowed_and_forbidden_fields_defined_not_customer_copy",
            "customer_output_schema_gate_landed": True,
            "allowed_customer_output_fields": list(ALLOWED_CUSTOMER_OUTPUT_FIELDS),
            "forbidden_customer_output_fields": list(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS),
            "required_operator_notices": [
                "operator_review_notice",
                "privacy_redaction_notice",
                "limitations_and_non_guarantees",
            ],
            "required_boundary_notes": [
                "Status must remain plain-language and non-authoritative.",
                "Evidence summary must describe only reviewed evidence, not raw metadata.",
                "Handoff summaries must preserve scoped windows and source/recipient type without private identity.",
                "Receipt/stamp language must be source-bounded and must not claim official acceptance.",
                "Limitations must preserve non-guarantee, non-legal-service, and custody-scope boundaries.",
                "Recommended next step must be advisory and must not dispatch, promise acceptance, or promise filing outcomes.",
            ],
        },
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "schema_gate_readiness": {flag: False for flag in _SCHEMA_FALSE_FLAGS},
        "schema_review_checks": [
            {
                "check_id": check_id,
                "status": "passed_for_schema_gate_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check_id in [
                "source_operator_read_surface_safe_claims_present",
                "schema_gate_consumes_only_operator_read_surface",
                "allowed_customer_output_fields_are_plain_language_only",
                "forbidden_fields_block_exact_location_raw_metadata_and_private_context",
                "forbidden_claims_block_legal_notarial_identity_acceptance_filing_and_custody_language",
                "dispatch_reputation_worker_doctrine_public_launch_and_catalog_readiness_still_blocked",
                "customer_copy_requires_separate_internal_sample_output_and_explicit_hold_or_approval_decision",
            ]
        ],
        "operator_instruction": (
            "Use this only as an internal/admin schema boundary for a later Document / Handoff "
            "sample output. Do not publish it, route it, dispatch from it, attach "
            "reputation receipts, expose exact GPS/raw metadata, or treat it as legal "
            "service, notarial action, identity verification, guaranteed acceptance, filing, "
            "custody, catalog, pilot, or customer-delivery readiness."
        ),
        "next_smallest_proof": (
            "Draft one internal/admin sample Document / Handoff output against this schema, "
            "then record an explicit hold/approval decision separately. Keep publication, "
            "routes, dispatch, reputation, exact GPS/raw metadata, legal/notarial/private-identity/"
            "acceptance/filing/custody claims, catalog/pilot/customer readiness, and "
            "worker-copyable doctrine blocked."
        ),
    }
    _assert_gate_is_conservative(gate, source_surface=source_surface)
    return gate


def write_document_handoff_customer_output_schema_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Document / Handoff customer-output schema gate."""

    gate = build_document_handoff_customer_output_schema_gate()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_document_handoff_customer_output_schema_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Document / Handoff schema gate."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    if not isinstance(gate, dict):
        raise CityOpsContractError("Document / Handoff customer-output schema gate must be a JSON object")
    _assert_gate_is_conservative(
        gate,
        source_surface=_load_source_operator_surface_for_dir(source_dir),
    )
    return gate


def _load_source_operator_surface_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME).exists():
        return load_document_handoff_operator_read_surface(artifact_dir=source_dir)
    return load_document_handoff_operator_read_surface()


def _assert_source_surface_is_conservative(surface: dict[str, Any]) -> None:
    if surface.get("schema") != DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("Document / Handoff schema gate source surface schema drift")
    if surface.get("surface_id") != SURFACE_ID:
        raise CityOpsContractError("Document / Handoff schema gate source surface id drift")
    if surface.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Document / Handoff schema gate source family drift")
    if surface.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Document / Handoff schema gate source offer drift")
    if DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_SAFE_CLAIM not in surface.get("safe_to_claim", []):
        raise CityOpsContractError("Document / Handoff schema gate source safe claim missing")
    for claim in REQUIRED_INHERITED_SAFE_CLAIMS:
        if claim not in surface.get("safe_to_claim", []):
            raise CityOpsContractError("Document / Handoff schema gate source inherited safe claim missing")
    ladder = surface.get("ladder_boundary", {})
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff schema gate source promoted readiness")
    for flag in READINESS_FALSE_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff schema gate source promoted readiness: {flag}")
    access = surface.get("access_policy", {})
    for flag in (
        "customer_visible",
        "worker_visible",
        "dispatch_enabled",
        "emits_reputation_receipts",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
        "public_route_registered",
        "network_route_registered",
    ):
        if access.get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff schema gate source access overclaims: {flag}")
    derived = surface.get("derived_from", {})
    if derived.get("consumes_only") != [DOCUMENT_HANDOFF_INTERNAL_PACKAGE_RECORD_FILENAME]:
        raise CityOpsContractError("Document / Handoff schema gate source input drift")


def _assert_gate_is_conservative(
    gate: dict[str, Any], *, source_surface: dict[str, Any]
) -> None:
    _assert_source_surface_is_conservative(source_surface)
    if gate.get("schema") != DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("Document / Handoff customer-output schema gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("Document / Handoff customer-output schema gate id drift")
    if gate.get("scope") != SCOPE:
        raise CityOpsContractError("Document / Handoff customer-output schema gate scope drift")
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("Document / Handoff customer-output schema gate status drift")
    if gate.get("source_surface_id") != source_surface.get("surface_id"):
        raise CityOpsContractError("Document / Handoff customer-output schema gate source drift")
    if gate.get("source_surface_file") != DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME:
        raise CityOpsContractError("Document / Handoff customer-output schema gate source file drift")

    safe_to_claim = list(gate.get("safe_to_claim", []))
    do_not_claim_yet = list(gate.get("do_not_claim_yet", []))
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    if DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("Document / Handoff customer-output schema gate safe claim missing")
    for claim in REQUIRED_INHERITED_SAFE_CLAIMS:
        if claim not in safe_to_claim:
            raise CityOpsContractError("Document / Handoff customer-output schema gate inherited claim missing")
    missing_blocked = (set(source_surface.get("do_not_claim_yet", [])) | set(SCHEMA_GATE_BLOCKED_CLAIMS)) - set(
        do_not_claim_yet
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Document / Handoff customer-output schema gate missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = gate.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff customer-output schema gate covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff customer-output schema gate next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff customer-output schema gate promoted readiness")

    source_contract = gate.get("source_contract", {})
    if source_contract.get("consumes_only") != [DOCUMENT_HANDOFF_OPERATOR_READ_SURFACE_FILENAME]:
        raise CityOpsContractError("Document / Handoff customer-output schema gate input drift")
    for flag in (
        "source_payload_reinterpreted_as_customer_copy",
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
            raise CityOpsContractError(
                f"Document / Handoff customer-output schema gate source contract overclaims: {flag}"
            )

    schema_review = gate.get("schema_review", {})
    if schema_review.get("review_status") != "allowed_and_forbidden_fields_defined_not_customer_copy":
        raise CityOpsContractError("Document / Handoff customer-output schema gate review status drift")
    if schema_review.get("customer_output_schema_gate_landed") is not True:
        raise CityOpsContractError("Document / Handoff customer-output schema gate completion missing")
    _assert_field_boundaries(
        list(schema_review.get("allowed_customer_output_fields", [])),
        list(schema_review.get("forbidden_customer_output_fields", [])),
    )

    for flag in READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Document / Handoff customer-output schema gate promoted readiness: {flag}")
    schema_gate_readiness = gate.get("schema_gate_readiness", {})
    for flag in _SCHEMA_FALSE_FLAGS:
        if schema_gate_readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Document / Handoff customer-output schema gate promoted schema readiness: {flag}"
            )

    checks = gate.get("schema_review_checks")
    if not isinstance(checks, list) or len(checks) != 7:
        raise CityOpsContractError("Document / Handoff customer-output schema gate checks drift")
    for item in checks:
        if item.get("status") != "passed_for_schema_gate_only":
            raise CityOpsContractError("Document / Handoff customer-output schema gate check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError("Document / Handoff customer-output schema gate stopped blocking promotion")

    _assert_no_exact_location_or_outcome_claims(gate)


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(
            f"Document / Handoff customer-output schema gate has forbidden safe claims: {forbidden}"
        )
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(
            f"Document / Handoff customer-output schema gate claim overlap: {overlap}"
        )


def _assert_field_boundaries(allowed: list[str], forbidden: list[str]) -> None:
    if allowed != ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Document / Handoff customer-output schema gate allowed field drift")
    if forbidden != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("Document / Handoff customer-output schema gate forbidden field drift")
    overlap = sorted(set(allowed) & set(forbidden))
    if overlap:
        raise CityOpsContractError(
            f"Document / Handoff customer-output schema gate field overlap: {overlap}"
        )


def _assert_no_exact_location_or_outcome_claims(gate: dict[str, Any]) -> None:
    serialized = json.dumps(gate, sort_keys=True).lower()
    forbidden_substrings = [
        "latitude",
        "longitude",
        "gps:",
        "guaranteed handoff completed",
        "acceptance guaranteed",
        "custody guaranteed",
        "filing succeeded",
        "official acceptance confirmed",
        "legal service provided",
        "notarial act completed",
        "identity verified",
        "driver license",
        "passport",
    ]
    for substring in forbidden_substrings:
        if substring in serialized:
            raise CityOpsContractError(
                "Document / Handoff customer-output schema gate leaked exact location or outcome claim"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
