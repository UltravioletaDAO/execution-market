"""Customer-output schema review gate for Phase 1 City Counter Ops packages.

This module creates an internal/admin-only schema review over the three Phase 1
internal package records. It defines what a future customer-facing output schema
may contain, but it deliberately does not draft customer copy, expose a public
catalog, authorize a pilot, prove live Acontext/runtime parity, dispatch work,
promote reputation/worker Skill DNA, expose exact GPS/raw metadata, or create
worker-copyable municipal doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_packet_submission_internal_package_record import (
    PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    load_phase1_packet_submission_internal_package_record,
)
from .phase1_remaining_offer_internal_package_records import (
    PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    load_phase1_counter_reality_check_internal_package_record,
    load_phase1_posting_compliance_internal_package_record,
)
from .phase1_review_output_schemas import OFFER_SPEC_DIR

PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SCHEMA = (
    "city_ops.phase1_customer_output_schema_review_gate.v1"
)
PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME = (
    "phase1_customer_output_schema_review_gate.json"
)
PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SAFE_CLAIM = (
    "phase1_customer_output_schema_review_gate_landed"
)

REQUIRED_OFFER_ORDER = [
    "counter_reality_check",
    "packet_submission_attempt",
    "posting_compliance_check",
]

EXPECTED_PACKAGE_SCHEMAS = {
    "counter_reality_check": "city_ops.phase1_counter_reality_check_internal_package_record.v1",
    "packet_submission_attempt": "city_ops.phase1_packet_submission_internal_package_record.v1",
    "posting_compliance_check": "city_ops.phase1_posting_compliance_internal_package_record.v1",
}

EXPECTED_PACKAGE_SAFE_CLAIMS = {
    "counter_reality_check": PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    "packet_submission_attempt": PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    "posting_compliance_check": PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
}

REQUIRED_BLOCKED_CLAIMS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "front_door_sku_ready",
    "filing_success_ready",
    "broad_office_reuse_ready",
    "city_relationship_or_influence",
    "guaranteed_approval",
    "legal_sufficiency",
    "regulator_acceptance",
    "live_acontext_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "autonomous_dispatch_readiness",
    "dispatch_routing_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_municipal_doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "exact_gps_or_metadata_exposure",
    "raw_metadata_exposure_allowed",
]

SOURCE_REQUIRED_BLOCKED_CLAIMS = [
    claim
    for claim in REQUIRED_BLOCKED_CLAIMS
    if claim not in {"customer_pilot_exposure_ready", "front_door_sku_ready"}
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "customer_output_ready",
    "customer_schema_ready_for_public_use",
    "pilot_authorized",
}

READINESS_FALSE_FLAGS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "customer_pilot_exposure_allowed",
    "front_door_sku_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
]

SOURCE_PACKAGE_FALSE_FLAGS = [
    "customer_output_schema_reviewed",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
]

BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS = [
    "task_id_or_local_case_reference",
    "offer_type",
    "plain_language_status",
    "reviewed_evidence_summary",
    "what_was_checked",
    "what_was_not_checked",
    "limitations_and_non_guarantees",
    "recommended_next_action",
    "operator_review_notice",
]

FORBIDDEN_CUSTOMER_OUTPUT_FIELDS = [
    "exact_gps_coordinates",
    "raw_metadata_blob",
    "raw_transcript_as_authority",
    "private_operator_context",
    "city_contact_private_details",
    "guaranteed_approval_language",
    "legal_advice_or_legal_sufficiency",
    "regulator_acceptance_claim",
    "filing_success_claim",
    "worker_copyable_municipal_doctrine",
    "dispatch_instruction_or_assignment",
    "erc8004_reputation_receipt",
]

OFFER_FIELD_NOTES = {
    "counter_reality_check": {
        "required_disclaimer": "Counter-output may describe a redirect/outdated packet check only; it must not claim city influence, filing success, approval, or legal sufficiency.",
        "privacy_note": "Do not reveal private operator context or unreviewed source material.",
        "next_gate": "operator-approved customer wording sample after privacy/legal/non-guarantee review",
    },
    "packet_submission_attempt": {
        "required_disclaimer": "Packet-output may describe a reviewed submission attempt artifact only; it must not claim acceptance, filing success, or office reuse.",
        "privacy_note": "Do not include raw transcript authority, unreviewed memory, exact GPS, or raw metadata.",
        "next_gate": "operator-approved customer wording sample after proof-boundary review",
    },
    "posting_compliance_check": {
        "required_disclaimer": "Posting-output may describe a partial observed posting/compliance check only; it must not claim checklist completion, regulator acceptance, or approval.",
        "privacy_note": "Exact GPS and raw metadata remain blocked; only generalized location/evidence summaries are allowed.",
        "next_gate": "separate GPS/raw-metadata privacy review before any customer evidence language",
    },
}


def build_phase1_customer_output_schema_review_gate(
    *,
    fixture_dir: str | Path | None = None,
    counter_package_record: dict[str, Any] | None = None,
    packet_package_record: dict[str, Any] | None = None,
    posting_package_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the schema-only customer-output review gate.

    The gate consumes the three conservative internal package records and records
    a future customer-output schema shape. It is not customer copy and not pilot
    authorization.
    """

    records = {
        "counter_reality_check": counter_package_record
        or load_phase1_counter_reality_check_internal_package_record(
            fixture_dir=fixture_dir
        ),
        "packet_submission_attempt": packet_package_record
        or load_phase1_packet_submission_internal_package_record(
            fixture_dir=fixture_dir
        ),
        "posting_compliance_check": posting_package_record
        or load_phase1_posting_compliance_internal_package_record(
            fixture_dir=fixture_dir
        ),
    }
    _assert_source_package_records(records)

    reviews = [_build_offer_schema_review(offer_id, records[offer_id]) for offer_id in REQUIRED_OFFER_ORDER]

    safe_to_claim = _dedupe(
        [
            PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SAFE_CLAIM,
            PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
            PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
            PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *records["counter_reality_check"].get("do_not_claim_yet", []),
            *records["packet_submission_attempt"].get("do_not_claim_yet", []),
            *records["posting_compliance_check"].get("do_not_claim_yet", []),
        ]
    )

    gate = {
        "schema": PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SCHEMA,
        "gate_id": "city_counter_ops.phase1_customer_output_schema_review.2026_05_11",
        "scope": "internal_admin_schema_review_only",
        "source_counter_package_id": records["counter_reality_check"]["package_id"],
        "source_packet_package_id": records["packet_submission_attempt"]["package_id"],
        "source_posting_package_id": records["posting_compliance_check"]["package_id"],
        "offer_order": REQUIRED_OFFER_ORDER,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "schema_review_status": "reviewed_for_future_customer_output_shape_not_copy",
        "customer_output_schema_review_gate_complete": True,
        "customer_copy_created": False,
        "customer_copy_ready": False,
        "customer_visible_catalog_ready": False,
        "public_service_catalog_ready": False,
        "customer_pilot_exposure_allowed": False,
        "front_door_sku_ready": False,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "worker_copyable_doctrine_ready": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
        "shared_allowed_customer_output_fields": list(BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS),
        "shared_forbidden_customer_output_fields": list(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS),
        "offer_schema_reviews": reviews,
        "operator_instruction": (
            "Use this as an internal schema boundary for drafting the next artifact. "
            "Do not publish customer copy, open a public catalog, expose a pilot SKU, "
            "or dispatch work from this gate."
        ),
        "next_smallest_proof": (
            "Draft one operator-reviewed sample output per offer against this schema, "
            "with separate privacy/legal/non-guarantee review. Keep live Acontext, runtime, "
            "dispatch, reputation, GPS/raw metadata, pilot exposure, and worker-doctrine gates separate."
        ),
    }
    _assert_gate_is_conservative(gate)
    return gate


def write_phase1_customer_output_schema_review_gate(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the customer-output schema review gate beside reviewed outputs."""

    gate = build_phase1_customer_output_schema_review_gate(fixture_dir=fixture_dir)
    return _write_gate(gate, fixture_dir=fixture_dir)


def load_phase1_customer_output_schema_review_gate(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted customer-output schema review gate."""

    path = _gate_dir(fixture_dir) / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    if not isinstance(gate, dict):
        raise CityOpsContractError("customer output schema gate must be a JSON object")
    _assert_gate_is_conservative(gate)
    return gate


def _write_gate(gate: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_gate_is_conservative(gate)
    base_dir = _gate_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    return path


def _gate_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _build_offer_schema_review(offer_id: str, record: dict[str, Any]) -> dict[str, Any]:
    notes = OFFER_FIELD_NOTES[offer_id]
    return {
        "offer": offer_id,
        "source_package_id": record["package_id"],
        "source_proof_status_label": record["proof_status_label"],
        "source_reviewed_fixture_ids": record["reviewed_fixture_ids"],
        "schema_review_status": "schema_shape_reviewed_not_customer_copy",
        "customer_output_schema_review_gate_complete": True,
        "customer_copy_created": False,
        "customer_copy_ready": False,
        "customer_pilot_exposure_allowed": False,
        "allowed_customer_output_fields": list(BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS),
        "forbidden_customer_output_fields": list(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS),
        "required_disclaimer": notes["required_disclaimer"],
        "privacy_note": notes["privacy_note"],
        "next_gate": notes["next_gate"],
    }


def _assert_source_package_records(records: dict[str, dict[str, Any]]) -> None:
    missing = [offer_id for offer_id in REQUIRED_OFFER_ORDER if offer_id not in records]
    if missing:
        raise CityOpsContractError(f"customer output schema gate missing package records: {missing}")

    for offer_id in REQUIRED_OFFER_ORDER:
        record = records[offer_id]
        if record.get("schema") != EXPECTED_PACKAGE_SCHEMAS[offer_id]:
            raise CityOpsContractError(f"customer output schema gate package schema mismatch: {offer_id}")
        if record.get("offer") != offer_id:
            raise CityOpsContractError(f"customer output schema gate package offer drift: {offer_id}")
        if EXPECTED_PACKAGE_SAFE_CLAIMS[offer_id] not in record.get("safe_to_claim", []):
            raise CityOpsContractError(f"customer output schema gate package safe claim drift: {offer_id}")
        if record.get("operator_review_required_before_closure") is not True:
            raise CityOpsContractError("customer output schema gate requires operator review source")
        if record.get("forbidden_claims_preserved") is not True:
            raise CityOpsContractError("customer output schema gate requires preserved forbidden claims")
        for flag in SOURCE_PACKAGE_FALSE_FLAGS:
            if record.get(flag) is not False:
                raise CityOpsContractError(
                    f"customer output schema gate package readiness drift: {offer_id}:{flag}"
                )
        blocked = list(record.get("do_not_claim_yet", []))
        missing_blocked = [
            claim for claim in SOURCE_REQUIRED_BLOCKED_CLAIMS if claim not in blocked
        ]
        if missing_blocked:
            raise CityOpsContractError(
                f"customer output schema gate package missing blocked claims: {offer_id}:{missing_blocked}"
            )


def _assert_gate_is_conservative(gate: dict[str, Any]) -> None:
    if gate.get("schema") != PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("customer output schema gate schema mismatch")
    if gate.get("scope") != "internal_admin_schema_review_only":
        raise CityOpsContractError("customer output schema gate scope drift")
    if gate.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("customer output schema gate offer order drift")
    if gate.get("schema_review_status") != "reviewed_for_future_customer_output_shape_not_copy":
        raise CityOpsContractError("customer output schema gate review status drift")
    if gate.get("customer_output_schema_review_gate_complete") is not True:
        raise CityOpsContractError("customer output schema gate must be complete")
    if gate.get("customer_copy_created") is not False:
        raise CityOpsContractError("customer output schema gate created customer copy")

    promoted = [flag for flag in READINESS_FALSE_FLAGS if gate.get(flag) is True]
    if promoted:
        raise CityOpsContractError(f"customer output schema gate promoted readiness: {promoted}")
    missing_false = [flag for flag in READINESS_FALSE_FLAGS if gate.get(flag) is not False]
    if missing_false:
        raise CityOpsContractError(
            f"customer output schema gate readiness flags must be false: {missing_false}"
        )

    safe_to_claim = list(gate.get("safe_to_claim", []))
    do_not_claim_yet = list(gate.get("do_not_claim_yet", []))
    if not safe_to_claim or not do_not_claim_yet:
        raise CityOpsContractError("customer output schema gate missing claims")
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"customer output schema gate has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"customer output schema gate claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"customer output schema gate missing blocked claims: {missing_blocked}"
        )

    allowed = list(gate.get("shared_allowed_customer_output_fields", []))
    forbidden = list(gate.get("shared_forbidden_customer_output_fields", []))
    _assert_field_boundaries(allowed, forbidden, context="shared")

    reviews = gate.get("offer_schema_reviews")
    if not isinstance(reviews, list) or len(reviews) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("customer output schema gate offer review count mismatch")
    for expected_offer, review in zip(REQUIRED_OFFER_ORDER, reviews):
        _assert_offer_review_is_conservative(expected_offer, review, forbidden)


def _assert_offer_review_is_conservative(
    expected_offer: str, review: dict[str, Any], shared_forbidden: list[str]
) -> None:
    if review.get("offer") != expected_offer:
        raise CityOpsContractError("customer output schema gate offer review drift")
    if review.get("schema_review_status") != "schema_shape_reviewed_not_customer_copy":
        raise CityOpsContractError("customer output schema gate offer review status drift")
    if review.get("customer_output_schema_review_gate_complete") is not True:
        raise CityOpsContractError("customer output schema gate offer review incomplete")
    for flag in [
        "customer_copy_created",
        "customer_copy_ready",
        "customer_pilot_exposure_allowed",
    ]:
        if review.get(flag) is not False:
            raise CityOpsContractError(
                f"customer output schema gate offer promoted readiness: {expected_offer}:{flag}"
            )
    _assert_field_boundaries(
        list(review.get("allowed_customer_output_fields", [])),
        list(review.get("forbidden_customer_output_fields", [])),
        context=expected_offer,
    )
    if review.get("forbidden_customer_output_fields") != shared_forbidden:
        raise CityOpsContractError("customer output schema gate forbidden field drift")
    if not review.get("required_disclaimer") or not review.get("privacy_note"):
        raise CityOpsContractError("customer output schema gate missing disclaimer/privacy note")
    if not review.get("next_gate"):
        raise CityOpsContractError("customer output schema gate missing next gate")


def _assert_field_boundaries(
    allowed: list[str], forbidden: list[str], *, context: str
) -> None:
    if allowed != BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError(f"customer output schema gate allowed field drift: {context}")
    if forbidden != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError(f"customer output schema gate forbidden field drift: {context}")
    overlap = sorted(set(allowed) & set(forbidden))
    if overlap:
        raise CityOpsContractError(
            f"customer output schema gate field overlap: {context}:{overlap}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
