"""Publication-approval checklist for Phase 1 City Counter Ops samples.

This module creates an internal/admin-only checklist over the operator-reviewed
sample outputs. It is deliberately a checklist, not an approval, not customer
copy, not a public catalog, not live Acontext/runtime parity, not dispatch, not
reputation, not exact GPS/raw metadata exposure, and not worker-copyable
municipal doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_operator_reviewed_sample_outputs import (
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME,
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM,
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SCHEMA,
    load_phase1_operator_reviewed_sample_outputs,
)
from .phase1_customer_output_schema_review_gate import REQUIRED_OFFER_ORDER
from .phase1_review_output_schemas import OFFER_SPEC_DIR

PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SCHEMA = (
    "city_ops.phase1_sample_publication_approval_checklist.v1"
)
PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME = (
    "phase1_sample_publication_approval_checklist.json"
)
PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM = (
    "phase1_sample_publication_approval_checklist_landed"
)

REQUIRED_BLOCKED_CLAIMS = [
    "publication_approval_ready",
    "sample_output_publication_ready",
    "customer_sample_publication_ready",
    "customer_copy_created",
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

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "customer_output_ready",
    "customer_copy_created",
    "customer_schema_ready_for_public_use",
    "pilot_authorized",
    "sample_outputs_publishable",
    "publication_approved",
}

READINESS_FALSE_FLAGS = [
    "customer_copy_created",
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "customer_pilot_exposure_allowed",
    "front_door_sku_ready",
    "sample_outputs_publishable",
    "publication_approved",
    "publish_route_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
]

CHECKLIST_GATE_ORDER = [
    "source_sample_packet_validated",
    "safe_and_blocked_claims_travel_together",
    "privacy_boundary_review_required",
    "legal_advice_exclusion_required",
    "non_guarantee_language_required",
    "evidence_redaction_review_required",
    "exact_gps_and_raw_metadata_exclusion_required",
    "no_dispatch_or_reputation_claim_required",
    "operator_publish_approval_required",
    "customer_delivery_approval_required",
]

STRUCTURAL_GATES_ALREADY_VERIFIED = {
    "source_sample_packet_validated",
    "safe_and_blocked_claims_travel_together",
    "privacy_boundary_review_required",
    "legal_advice_exclusion_required",
    "non_guarantee_language_required",
    "exact_gps_and_raw_metadata_exclusion_required",
    "no_dispatch_or_reputation_claim_required",
}

APPROVAL_GATES_REMAIN_FALSE = {
    "evidence_redaction_review_required",
    "operator_publish_approval_required",
    "customer_delivery_approval_required",
}


def build_phase1_sample_publication_approval_checklist(
    *,
    fixture_dir: str | Path | None = None,
    sample_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative internal checklist over Phase 1 sample outputs."""

    source = sample_outputs or load_phase1_operator_reviewed_sample_outputs(
        fixture_dir=fixture_dir
    )
    _assert_source_sample_outputs(source)

    safe_to_claim = _dedupe(
        [
            *source.get("safe_to_claim", []),
            PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *source.get("do_not_claim_yet", []),
        ]
    )

    packet = {
        "schema": PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SCHEMA,
        "checklist_id": "city_counter_ops.phase1_sample_publication_approval_checklist.2026_05_11",
        "scope": "internal_admin_publication_approval_checklist_only",
        "source_sample_packet_id": source["sample_packet_id"],
        "source_sample_schema": source["schema"],
        "source_artifact_filename": PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME,
        "offer_order": list(REQUIRED_OFFER_ORDER),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "publication_approval_status": "not_approved_internal_checklist_only",
        "customer_copy_created": False,
        "customer_copy_ready": False,
        "customer_visible_catalog_ready": False,
        "public_service_catalog_ready": False,
        "customer_pilot_exposure_allowed": False,
        "front_door_sku_ready": False,
        "sample_outputs_publishable": False,
        "publication_approved": False,
        "publish_route_ready": False,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "worker_skill_dna_ready": False,
        "worker_copyable_doctrine_ready": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
        "approval_gates_required": list(CHECKLIST_GATE_ORDER),
        "approval_gates_status": _build_gate_status(),
        "offer_publication_reviews": [
            _build_offer_publication_review(sample)
            for sample in source.get("offer_sample_outputs", [])
        ],
        "operator_instruction": (
            "Treat this as a pre-publication checklist only. It does not approve "
            "customer copy or publication. Keep blocked claims attached to any "
            "future customer-facing draft, and require separate operator and "
            "customer-delivery approvals before exposure."
        ),
        "next_smallest_proof": (
            "If Saúl wants customer-facing Phase 1 copy, create one draft packet "
            "that consumes this checklist and still keeps publication_approved=false "
            "until explicit operator review is recorded."
        ),
    }
    _assert_packet_is_conservative(packet)
    return packet


def write_phase1_sample_publication_approval_checklist(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the internal checklist beside reviewed Phase 1 outputs."""

    packet = build_phase1_sample_publication_approval_checklist(fixture_dir=fixture_dir)
    return _write_packet(packet, fixture_dir=fixture_dir)


def load_phase1_sample_publication_approval_checklist(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted internal publication checklist."""

    path = _packet_dir(fixture_dir) / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("sample publication checklist must be a JSON object")
    _assert_packet_is_conservative(packet)
    return packet


def _build_gate_status() -> dict[str, dict[str, Any]]:
    status: dict[str, dict[str, Any]] = {}
    for gate in CHECKLIST_GATE_ORDER:
        if gate in STRUCTURAL_GATES_ALREADY_VERIFIED:
            status[gate] = {
                "verified": True,
                "approval_granted": False,
                "note": "Structural boundary checked; this is not publish approval.",
            }
        else:
            status[gate] = {
                "verified": False,
                "approval_granted": False,
                "note": "Required before any customer-visible publication.",
            }
    return status


def _build_offer_publication_review(sample: dict[str, Any]) -> dict[str, Any]:
    offer = sample.get("offer")
    review = {
        "offer": offer,
        "source_package_id": sample.get("source_package_id"),
        "source_sample_review_status": sample.get("sample_review_status"),
        "allowed_field_values_present": list(sample.get("allowed_field_values", {}).keys()),
        "blocked_fields_absent": list(sample.get("forbidden_fields_absent", [])),
        "publication_ready": False,
        "sample_publishable": False,
        "customer_copy_ready": False,
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
        "required_before_publication": [
            "final privacy/redaction review",
            "operator publish approval",
            "customer delivery approval",
            "blocked-claim adjacency check",
            "evidence-source limitation check",
        ],
    }
    _assert_offer_review_is_conservative(review)
    return review


def _write_packet(packet: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_packet_is_conservative(packet)
    base_dir = _packet_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _packet_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_source_sample_outputs(source: dict[str, Any]) -> None:
    if source.get("schema") != PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SCHEMA:
        raise CityOpsContractError("sample publication checklist source schema mismatch")
    if source.get("scope") != "internal_admin_sample_output_review_only":
        raise CityOpsContractError("sample publication checklist source scope drift")
    if source.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("sample publication checklist source offer order drift")
    if PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM not in source.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("sample publication checklist source safe claim drift")
    for flag in [
        "customer_copy_created",
        "customer_copy_ready",
        "customer_visible_catalog_ready",
        "public_service_catalog_ready",
        "customer_pilot_exposure_allowed",
        "front_door_sku_ready",
        "sample_outputs_publishable",
        "live_acontext_ready",
        "runtime_parity_proven",
        "autonomous_dispatch_ready",
        "reputation_ready",
        "worker_copyable_doctrine_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        if source.get(flag) is not False:
            raise CityOpsContractError(
                f"sample publication checklist source promoted readiness: {flag}"
            )
    for sample in source.get("offer_sample_outputs", []):
        if sample.get("sample_publishable") is not False:
            raise CityOpsContractError("sample publication checklist source publishable sample")
        reviews = sample.get("separate_reviews", {})
        if reviews.get("operator_publish_approval") is not False:
            raise CityOpsContractError("sample publication checklist source publish approval drift")
        if reviews.get("customer_delivery_approval") is not False:
            raise CityOpsContractError("sample publication checklist source delivery approval drift")
    required_source_blocked = [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "dispatch_routing_ready",
        "erc8004_reputation_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "customer_sample_publication_ready",
    ]
    missing_blocked = [
        claim for claim in required_source_blocked if claim not in source.get("do_not_claim_yet", [])
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"sample publication checklist source missing blocked claims: {missing_blocked}"
        )


def _assert_packet_is_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SCHEMA:
        raise CityOpsContractError("sample publication checklist schema mismatch")
    if packet.get("scope") != "internal_admin_publication_approval_checklist_only":
        raise CityOpsContractError("sample publication checklist scope drift")
    if packet.get("publication_approval_status") != "not_approved_internal_checklist_only":
        raise CityOpsContractError("sample publication checklist status drift")
    if packet.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("sample publication checklist offer order drift")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"sample publication checklist promoted readiness: {flag}"
            )
    safe_to_claim = list(packet.get("safe_to_claim", []))
    do_not_claim_yet = list(packet.get("do_not_claim_yet", []))
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"sample publication checklist has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"sample publication checklist claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"sample publication checklist missing blocked claims: {missing_blocked}"
        )
    if packet.get("approval_gates_required") != CHECKLIST_GATE_ORDER:
        raise CityOpsContractError("sample publication checklist gate order drift")
    _assert_gate_status_is_conservative(packet.get("approval_gates_status", {}))
    reviews = packet.get("offer_publication_reviews")
    if not isinstance(reviews, list) or len(reviews) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("sample publication checklist offer review count mismatch")
    for expected_offer, review in zip(REQUIRED_OFFER_ORDER, reviews):
        if review.get("offer") != expected_offer:
            raise CityOpsContractError("sample publication checklist offer review order drift")
        _assert_offer_review_is_conservative(review)


def _assert_gate_status_is_conservative(status: dict[str, Any]) -> None:
    if not isinstance(status, dict):
        raise CityOpsContractError("sample publication checklist missing gate status")
    if list(status.keys()) != CHECKLIST_GATE_ORDER:
        raise CityOpsContractError("sample publication checklist gate status order drift")
    for gate, value in status.items():
        if not isinstance(value, dict):
            raise CityOpsContractError("sample publication checklist gate status shape drift")
        if value.get("approval_granted") is not False:
            raise CityOpsContractError(
                f"sample publication checklist gate approval promoted: {gate}"
            )
        if gate in APPROVAL_GATES_REMAIN_FALSE and value.get("verified") is not False:
            raise CityOpsContractError(
                f"sample publication checklist approval gate prematurely verified: {gate}"
            )


def _assert_offer_review_is_conservative(review: dict[str, Any]) -> None:
    for flag in [
        "publication_ready",
        "sample_publishable",
        "customer_copy_ready",
        "operator_publish_approval",
        "customer_delivery_approval",
    ]:
        if review.get(flag) is not False:
            raise CityOpsContractError(
                f"sample publication checklist offer review promoted readiness: {review.get('offer')}:{flag}"
            )
    required = review.get("required_before_publication")
    if not isinstance(required, list) or "operator publish approval" not in required:
        raise CityOpsContractError("sample publication checklist missing publish prerequisite")
    if "customer delivery approval" not in required:
        raise CityOpsContractError("sample publication checklist missing delivery prerequisite")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
