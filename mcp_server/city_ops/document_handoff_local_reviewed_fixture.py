"""Document / Handoff Logistics adjacent-AAS local reviewed fixture.

This module advances Document / Handoff Logistics by exactly one rung: from an
internal fixture spec/review gate to one synthetic local reviewed fixture. It
remains internal/admin only. It does not create customer copy, publish a
catalog, authorize a pilot, prove live Acontext/runtime parity, dispatch work,
attach ERC-8004 reputation, expose exact GPS/raw metadata, or create
worker-copyable handoff doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    READINESS_FALSE_FLAGS,
)
from .contracts import CityOpsContractError
from .document_handoff_fixture_review_gate import (
    ARTIFACT_DIR,
    DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_BLOCKED_CLAIMS as GATE_BLOCKED_CLAIMS,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    load_document_handoff_fixture_review_gate,
)

DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SCHEMA = (
    "city_ops.document_handoff_local_reviewed_fixture.v1"
)
DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME = (
    "document_handoff_local_reviewed_fixture.json"
)
DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "document_handoff_local_reviewed_fixture_landed"
)

FIXTURE_ID = "execution_market.aas.document_handoff.local_reviewed_fixture.001"
SCOPE = "internal_admin_document_handoff_local_reviewed_fixture_only"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

LOCAL_FIXTURE_REVIEW_CHECKS = [
    "source_gate_safe_claims_present",
    "all_required_handoff_evidence_fields_populated",
    "reviewed_output_uses_only_allowed_fields",
    "chain_of_custody_is_scoped_to_documented_windows",
    "recipient_or_source_type_preserved_without_private_identity_exposure",
    "receipt_or_stamp_summary_source_bounded",
    "privacy_redaction_completed_for_local_fixture",
    "exact_gps_raw_metadata_signature_and_id_blobs_absent",
    "legal_service_notarial_identity_and_custody_guarantee_claims_absent",
    "non_guarantee_language_present",
    "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "document_handoff_local_fixture_customer_delivery_ready",
    "document_handoff_local_fixture_publication_ready",
    "document_handoff_local_fixture_catalog_ready",
    "document_handoff_local_fixture_dispatch_ready",
    "document_handoff_local_fixture_reputation_ready",
    "document_handoff_local_fixture_worker_doctrine_ready",
    "document_handoff_local_fixture_live_acontext_ready",
    "document_handoff_local_fixture_notarial_ready",
    "document_handoff_local_fixture_custody_guarantee_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(GATE_BLOCKED_CLAIMS) | set(ADDITIONAL_BLOCKED_CLAIMS)


def build_document_handoff_local_reviewed_fixture(
    *, gate: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one internal reviewed fixture for Document / Handoff Logistics.

    The fixture is synthetic and non-jurisdiction-specific. It proves the local
    review shape for a bounded handoff proof run without claiming legal service,
    notarial authority, guaranteed acceptance, customer readiness, dispatch,
    reputation attachment, live Acontext parity, exact location disclosure, or
    worker-copyable doctrine.
    """

    source_gate = gate or load_document_handoff_fixture_review_gate()
    _assert_source_gate(source_gate)

    reviewed_output = {
        "task_id_or_local_case_reference": "local_document_handoff_fixture_001",
        "offer_type": OFFER_ID,
        "plain_language_status": (
            "A bounded document handoff attempt was completed within the scoped "
            "window and produced source-bounded proof of the attempt. This is an "
            "operator-reviewed evidence snapshot, not a legal service, not a "
            "notarial act, and not a guarantee of acceptance or custody outside "
            "the documented window."
        ),
        "handoff_window_summary": (
            "Synthetic same-business-day pickup/drop-off window; no exact address, "
            "GPS coordinate, raw metadata, private identity document, or signature "
            "image is retained in the reviewed output."
        ),
        "chain_of_custody_event_summary": [
            "Prepared packet was observed as sealed before pickup within the scoped window.",
            "Worker captured a permitted queue/wait boundary note before counter handoff.",
            "Counter handoff was recorded as attempted and source-bounded to the documented window.",
            "No custody claim is made before pickup, after handoff, or outside the documented window.",
        ],
        "recipient_or_source_type_summary": (
            "Recipient/source is classified only as office_counter_staff_source; no "
            "private person name, ID document, signature image, or private contact "
            "detail is exposed."
        ),
        "receipt_or_stamp_summary": (
            "Permitted receipt/stamp proof is represented as a redacted synthetic "
            "receipt indicator. It proves only that a handoff proof artifact exists, "
            "not acceptance, legal sufficiency, or filing success."
        ),
        "failed_handoff_reason": "not_applicable_handoff_attempt_recorded_but_not_acceptance_guaranteed",
        "queue_or_wait_boundary": (
            "Queue/wait was bounded to the scoped attempt window; no unlimited waiting "
            "or future availability claim is made."
        ),
        "what_was_checked": [
            "scoped_pickup_or_dropoff_window",
            "sealed_packet_observation",
            "source_type_classification",
            "permitted_receipt_or_stamp_indicator",
            "queue_or_wait_boundary",
            "absence_of_exact_location_private_identity_signature_and_raw_metadata",
        ],
        "what_was_not_checked": [
            "legal_service",
            "notarial_act",
            "identity_verification_beyond_scoped_evidence",
            "guaranteed_acceptance",
            "custody_outside_documented_windows",
            "filing_success",
            "customer_delivery_readiness",
            "dispatch_readiness",
        ],
        "limitations_and_non_guarantees": [
            "This fixture is synthetic and local; it does not represent a real handoff case.",
            "The review does not provide legal service, notarial service, or acceptance guarantee.",
            "Recipient/source identity is intentionally summarized by type, not exposed as private identity data.",
            "Custody is only described for documented events inside the scoped window.",
            "No customer delivery, public catalog, dispatch route, or ERC-8004 reputation receipt is authorized.",
        ],
        "recommended_next_action": (
            "Create a Document / Handoff internal package record that consumes this "
            "local fixture and keeps customer/public/dispatch/reputation/privacy/"
            "worker-doctrine readiness false."
        ),
        "operator_review_notice": (
            "Reviewed for local fixture shape only. Keep all customer/public/pilot/"
            "dispatch/reputation/live-runtime/notarial/custody-guarantee/"
            "worker-doctrine readiness false."
        ),
    }

    fixture = {
        "schema": DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": FIXTURE_ID,
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_gate_id": source_gate["gate_id"],
        "source_gate_schema": source_gate["schema"],
        "source_safe_claims_inherited": [
            DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "safe_to_claim": [
            DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "do_not_claim_yet": _dedupe(
            [
                *GATE_BLOCKED_CLAIMS,
                *source_gate.get("do_not_claim_yet", []),
                *ADDITIONAL_BLOCKED_CLAIMS,
            ]
        ),
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "local_fixture": {
            "review_status": "reviewed_internal_fixture_only_not_promoted",
            "fixture_kind": "synthetic_non_jurisdiction_specific_document_handoff_proof_run",
            "customer_copy_changed": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "worker_copyable_doctrine_allowed": False,
            "notarial_claim_allowed": False,
            "custody_guarantee_allowed": False,
            "evidence_contract_snapshot": {
                "chain_of_custody_events_inside_scoped_windows": [
                    "synthetic_packet_observed_sealed_before_pickup_inside_scoped_window",
                    "synthetic_counter_handoff_attempt_recorded_inside_scoped_window",
                    "custody_language_limited_to_documented_events_only",
                ],
                "pickup_or_dropoff_timestamp": (
                    "relative_business_day_window_no_exact_location_or_raw_metadata"
                ),
                "recipient_or_source_type": (
                    "office_counter_staff_source_type_only_no_private_identity"
                ),
                "receipt_stamp_or_photo_where_available": (
                    "redacted_synthetic_receipt_indicator_no_signature_or_id_blob"
                ),
                "failed_handoff_reason": (
                    "not_applicable_for_fixture_attempt_recorded_without_acceptance_guarantee"
                ),
                "queue_or_wait_boundary": (
                    "bounded_queue_wait_note_inside_attempt_window_no_unlimited_waiting_claim"
                ),
                "recommended_next_action": (
                    "package_as_internal_record_before_any_customer_output_schema_or_approval_decision"
                ),
            },
            "reviewed_output_schema": {
                "status": "local_reviewed_fixture_internal_only_not_customer_output",
                "required_fields": list(REQUIRED_OUTPUT_FIELDS),
                "forbidden_fields": list(
                    source_gate["fixture_spec"]["reviewed_output_schema_draft"][
                        "forbidden_fields"
                    ]
                ),
            },
            "reviewed_output": reviewed_output,
        },
        "local_review_checks": [
            {
                "check_id": check,
                "status": "passed_for_local_fixture_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check in LOCAL_FIXTURE_REVIEW_CHECKS
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "operator_instruction": (
            "Use this fixture only to prove the Document / Handoff reviewed-output "
            "shape. The next valid step is an internal package record, not customer "
            "copy, catalog routing, dispatch, reputation, live Acontext, notarial "
            "claims, custody guarantees, or worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Create a Document / Handoff internal package record that consumes this "
            "local fixture and keeps customer/public/dispatch/reputation/privacy/"
            "notarial/custody/worker-doctrine readiness false."
        ),
    }
    _assert_fixture_is_conservative(fixture, source_gate=source_gate)
    return fixture


def write_document_handoff_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Document / Handoff local reviewed fixture."""

    fixture = build_document_handoff_local_reviewed_fixture()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_document_handoff_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Document / Handoff local reviewed fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    if not isinstance(fixture, dict):
        raise CityOpsContractError(
            "Document / Handoff local reviewed fixture must be a JSON object"
        )
    _assert_fixture_is_conservative(
        fixture, source_gate=load_document_handoff_fixture_review_gate()
    )
    return fixture


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Document / Handoff local fixture source gate family drift")
    if gate.get("fixture_spec", {}).get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Document / Handoff local fixture source gate offer drift")
    safe_claims = set(gate.get("safe_to_claim", []))
    for claim in (
        DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
        AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    ):
        if claim not in safe_claims:
            raise CityOpsContractError("Document / Handoff local fixture source safe claim missing")
    gate_ladder = gate.get("ladder_boundary", {})
    if gate_ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff local fixture source gate promoted readiness")


def _assert_fixture_is_conservative(
    fixture: dict[str, Any], *, source_gate: dict[str, Any]
) -> None:
    _assert_source_gate(source_gate)
    if fixture.get("schema") != DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SCHEMA:
        raise CityOpsContractError("Document / Handoff local reviewed fixture schema drift")
    if fixture.get("scope") != SCOPE:
        raise CityOpsContractError("Document / Handoff local reviewed fixture scope drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Document / Handoff local reviewed fixture family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Document / Handoff local reviewed fixture offer drift")
    if fixture.get("source_gate_id") != source_gate.get("gate_id"):
        raise CityOpsContractError("Document / Handoff local reviewed fixture source gate drift")

    safe_claims = set(fixture.get("safe_to_claim", []))
    if DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM not in safe_claims:
        raise CityOpsContractError("Document / Handoff local reviewed fixture safe claim missing")
    if safe_claims & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Document / Handoff local reviewed fixture has forbidden safe claims")
    for inherited_claim in fixture.get("source_safe_claims_inherited", []):
        if inherited_claim not in safe_claims:
            raise CityOpsContractError("Document / Handoff local reviewed fixture inherited claim missing")

    missing_blocked = (set(GATE_BLOCKED_CLAIMS) | set(ADDITIONAL_BLOCKED_CLAIMS)) - set(
        fixture.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            "Document / Handoff local reviewed fixture missing blocked claims: "
            f"{sorted(missing_blocked)}"
        )

    ladder = fixture.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff local reviewed fixture covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Document / Handoff local reviewed fixture next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Document / Handoff local reviewed fixture promoted readiness")

    readiness = fixture.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Document / Handoff local reviewed fixture promoted readiness: {flag}"
            )

    local_fixture = fixture.get("local_fixture")
    if not isinstance(local_fixture, dict):
        raise CityOpsContractError("Document / Handoff local fixture payload must be an object")
    if local_fixture.get("review_status") != "reviewed_internal_fixture_only_not_promoted":
        raise CityOpsContractError("Document / Handoff local fixture review status drift")
    for false_flag in (
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_copyable_doctrine_allowed",
        "notarial_claim_allowed",
        "custody_guarantee_allowed",
    ):
        if local_fixture.get(false_flag) is not False:
            raise CityOpsContractError(f"Document / Handoff local fixture promoted {false_flag}")

    evidence = local_fixture.get("evidence_contract_snapshot", {})
    if set(REQUIRED_EVIDENCE_FIELDS) - set(evidence):
        raise CityOpsContractError("Document / Handoff local fixture lost required evidence fields")

    schema = local_fixture.get("reviewed_output_schema", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(schema.get("required_fields", []))):
        raise CityOpsContractError("Document / Handoff local fixture lost required output fields")
    forbidden_fields = set(schema.get("forbidden_fields", []))
    for field in (
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "private_recipient_identity",
        "private_sender_identity",
        "signature_or_id_document_blob",
        "legal_service_claim",
        "notarial_act_claim",
        "identity_verification_claim_beyond_scoped_evidence",
        "guaranteed_acceptance_language",
        "custody_guarantee_outside_documented_windows",
        "worker_copyable_handoff_doctrine",
    ):
        if field not in forbidden_fields:
            raise CityOpsContractError("Document / Handoff local fixture lost forbidden output fields")

    reviewed_output = local_fixture.get("reviewed_output", {})
    if set(REQUIRED_OUTPUT_FIELDS) - set(reviewed_output):
        raise CityOpsContractError("Document / Handoff local fixture reviewed output lost required fields")
    _assert_no_private_location_identity_or_handoff_overclaims(reviewed_output)

    checks = fixture.get("local_review_checks")
    if not isinstance(checks, list) or len(checks) != len(LOCAL_FIXTURE_REVIEW_CHECKS):
        raise CityOpsContractError("Document / Handoff local fixture review checks drift")
    check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
    if check_ids != LOCAL_FIXTURE_REVIEW_CHECKS:
        raise CityOpsContractError("Document / Handoff local fixture review check order drift")
    for item in checks:
        if item.get("status") != "passed_for_local_fixture_only":
            raise CityOpsContractError("Document / Handoff local fixture review check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Document / Handoff local fixture review check stopped blocking promotion"
            )


def _assert_no_private_location_identity_or_handoff_overclaims(
    reviewed_output: dict[str, Any]
) -> None:
    serialized = json.dumps(reviewed_output, sort_keys=True).lower()
    forbidden_substrings = [
        "latitude",
        "longitude",
        "gps:",
        "home address",
        "driver license",
        "passport",
        "social security",
        "notarized",
        "notarial act completed",
        "legal service provided",
        "guaranteed acceptance",
        "acceptance guaranteed",
        "custody guaranteed",
        "custody guarantee",
        "filing success confirmed",
    ]
    for substring in forbidden_substrings:
        if substring in serialized:
            raise CityOpsContractError(
                "Document / Handoff local fixture leaked private location, identity, "
                "or handoff overclaim"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
