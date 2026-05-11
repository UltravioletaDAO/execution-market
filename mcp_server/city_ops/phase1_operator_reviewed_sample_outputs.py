"""Operator-reviewed sample outputs for Phase 1 City Counter Ops offers.

This module produces internal/admin-only sample output packets against the
customer-output schema review gate. The packets are examples of bounded wording
shape, not customer copy approval, not a public catalog, not a pilot launch, not
live Acontext/runtime parity, not dispatch, not reputation, not exact GPS/raw
metadata exposure, and not worker-copyable municipal doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_customer_output_schema_review_gate import (
    BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS,
    FORBIDDEN_CUSTOMER_OUTPUT_FIELDS,
    PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SAFE_CLAIM,
    PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SCHEMA,
    REQUIRED_OFFER_ORDER,
    load_phase1_customer_output_schema_review_gate,
)
from .phase1_review_output_schemas import OFFER_SPEC_DIR

PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SCHEMA = (
    "city_ops.phase1_operator_reviewed_sample_outputs.v1"
)
PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME = (
    "phase1_operator_reviewed_sample_outputs.json"
)
PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM = (
    "phase1_operator_reviewed_sample_outputs_landed"
)

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
    "customer_sample_publication_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "customer_output_ready",
    "customer_copy_created",
    "customer_schema_ready_for_public_use",
    "pilot_authorized",
    "sample_output_publication_ready",
}

READINESS_FALSE_FLAGS = [
    "customer_copy_created",
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
    "sample_outputs_publishable",
]

REQUIRED_SAMPLE_REVIEW_FLAGS = [
    "privacy_boundary_review_passed",
    "legal_advice_exclusion_review_passed",
    "non_guarantee_language_review_passed",
]

FORBIDDEN_SAMPLE_KEYS = set(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS) | {
    "customer_private_name",
    "customer_contact_details",
    "office_private_contact",
    "dispatch_assignment",
    "worker_instruction",
}

FORBIDDEN_TEXT_FRAGMENTS = [
    "guaranteed approval",
    "legal sufficiency",
    "regulator acceptance",
    "filing success",
    "exact gps",
    "raw metadata",
    "erc-8004 reputation receipt",
    "erc8004 reputation receipt",
    "dispatch instruction",
]

SAMPLE_OUTPUT_SPECS: dict[str, dict[str, Any]] = {
    "counter_reality_check": {
        "case_reference": "sample-counter-reality-check-001",
        "plain_language_status": (
            "Reviewed source suggests a redirect or outdated packet path that an "
            "operator can explain carefully after final review."
        ),
        "reviewed_evidence_summary": (
            "Synthetic reviewed fixture only: the source was checked for a redirect "
            "or outdated packet signal without using private operator context."
        ),
        "what_was_checked": [
            "Whether the reviewed source indicated a redirect/outdated-packet condition.",
            "Whether the source stayed inside the internal package record boundary.",
            "Whether blocked claims remained adjacent to the sample language.",
        ],
        "what_was_not_checked": [
            "No city relationship, influence, acceptance, or approval was checked.",
            "No legal advice or legal conclusion was produced.",
            "No reusable office doctrine was created for workers.",
        ],
        "limitations_and_non_guarantees": [
            "This is an internal wording sample, not customer-ready copy.",
            "It does not promise acceptance, approval, legal adequacy, or filing outcome.",
            "Operator review is required before any customer-visible use.",
        ],
        "recommended_next_action": (
            "Operator may prepare a careful customer-facing explanation only after "
            "a separate publish approval; otherwise keep this as internal support."
        ),
    },
    "packet_submission_attempt": {
        "case_reference": "sample-packet-submission-attempt-001",
        "plain_language_status": (
            "Reviewed source supports describing a bounded submission-attempt artifact; "
            "operator closure is still required."
        ),
        "reviewed_evidence_summary": (
            "Synthetic reviewed fixture only: a fixable non-redirect rejection pattern "
            "was checked through the internal package record."
        ),
        "what_was_checked": [
            "Whether the reviewed artifact described a submission attempt boundary.",
            "Whether the sample avoids raw transcripts and unreviewed memory as authority.",
            "Whether non-guarantee language remains present."
        ],
        "what_was_not_checked": [
            "No acceptance by an office was checked.",
            "No broad office reuse or future filing pathway was proven.",
            "No live Acontext write/retrieve parity was attempted."
        ],
        "limitations_and_non_guarantees": [
            "This sample is internal/admin only and cannot be sent as-is.",
            "It does not state that any packet was accepted or completed.",
            "It requires operator review before closure or customer exposure."
        ],
        "recommended_next_action": (
            "Operator may convert the reviewed artifact into a bounded status note "
            "only after separate privacy and publish review."
        ),
    },
    "posting_compliance_check": {
        "case_reference": "sample-posting-compliance-check-001",
        "plain_language_status": (
            "Reviewed source supports a partial observed posting/compliance check; "
            "privacy-sensitive evidence remains excluded."
        ),
        "reviewed_evidence_summary": (
            "Synthetic reviewed fixture only: partial posting evidence was summarized "
            "without coordinates, source metadata blobs, or private contact details."
        ),
        "what_was_checked": [
            "Whether the reviewed source supported a partial observed status.",
            "Whether the sample avoids coordinates, source metadata blobs, and private contact details.",
            "Whether approval/completion language remains blocked."
        ],
        "what_was_not_checked": [
            "No checklist completion was checked.",
            "No agency approval or completion was checked.",
            "No worker-visible municipal doctrine was created."
        ],
        "limitations_and_non_guarantees": [
            "This sample is internal/admin only and not a customer evidence packet.",
            "It does not state compliance completion or approval.",
            "A separate privacy review is required before any evidence language is exposed."
        ],
        "recommended_next_action": (
            "Operator may request a privacy-safe customer summary only after a separate "
            "evidence and publish review."
        ),
    },
}


def build_phase1_operator_reviewed_sample_outputs(
    *,
    fixture_dir: str | Path | None = None,
    schema_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build conservative internal sample outputs against the schema gate."""

    gate = schema_gate or load_phase1_customer_output_schema_review_gate(
        fixture_dir=fixture_dir
    )
    _assert_source_gate(gate)

    safe_to_claim = _dedupe(
        [
            *gate.get("safe_to_claim", []),
            PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *gate.get("do_not_claim_yet", []),
        ]
    )

    samples = [
        _build_offer_sample_output(offer_id, gate)
        for offer_id in REQUIRED_OFFER_ORDER
    ]

    packet = {
        "schema": PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SCHEMA,
        "sample_packet_id": "city_counter_ops.phase1_operator_reviewed_sample_outputs.2026_05_11",
        "scope": "internal_admin_sample_output_review_only",
        "source_schema_gate_id": gate["gate_id"],
        "offer_order": list(REQUIRED_OFFER_ORDER),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "sample_review_status": "operator_reviewed_internal_samples_not_customer_copy",
        "sample_output_fields": list(BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS),
        "forbidden_customer_output_fields": list(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS),
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
        "sample_outputs_publishable": False,
        "separate_reviews": {
            "privacy_boundary_review_passed": True,
            "legal_advice_exclusion_review_passed": True,
            "non_guarantee_language_review_passed": True,
            "operator_publish_approval": False,
            "customer_delivery_approval": False,
        },
        "offer_sample_outputs": samples,
        "operator_instruction": (
            "Use these only as internal/admin wording-shape samples. They are not "
            "customer-ready copy and must not be published, routed, dispatched, or "
            "used to claim pilot/catalog readiness."
        ),
        "next_smallest_proof": (
            "Add a tiny publication-approval checklist over these samples only if "
            "Saúl wants customer-facing Phase 1 copy; keep live Acontext/runtime, "
            "dispatch, reputation, GPS/raw metadata, and worker-doctrine gates separate."
        ),
    }
    _assert_packet_is_conservative(packet)
    return packet


def write_phase1_operator_reviewed_sample_outputs(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the internal sample output packet beside reviewed outputs."""

    packet = build_phase1_operator_reviewed_sample_outputs(fixture_dir=fixture_dir)
    return _write_packet(packet, fixture_dir=fixture_dir)


def load_phase1_operator_reviewed_sample_outputs(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted internal sample output packet."""

    path = _packet_dir(fixture_dir) / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("operator-reviewed sample outputs must be a JSON object")
    _assert_packet_is_conservative(packet)
    return packet


def _build_offer_sample_output(offer_id: str, gate: dict[str, Any]) -> dict[str, Any]:
    spec = SAMPLE_OUTPUT_SPECS[offer_id]
    schema_review = _schema_review_for_offer(gate, offer_id)
    sample = {
        "offer": offer_id,
        "source_package_id": schema_review["source_package_id"],
        "schema_review_status": schema_review["schema_review_status"],
        "sample_review_status": "operator_reviewed_internal_sample_not_customer_copy",
        "sample_publishable": False,
        "customer_copy_ready": False,
        "customer_pilot_exposure_allowed": False,
        "allowed_field_values": {
            "task_id_or_local_case_reference": spec["case_reference"],
            "offer_type": offer_id,
            "plain_language_status": spec["plain_language_status"],
            "reviewed_evidence_summary": spec["reviewed_evidence_summary"],
            "what_was_checked": spec["what_was_checked"],
            "what_was_not_checked": spec["what_was_not_checked"],
            "limitations_and_non_guarantees": spec["limitations_and_non_guarantees"],
            "recommended_next_action": spec["recommended_next_action"],
            "operator_review_notice": (
                "Internal/admin sample only. Requires separate operator publish approval "
                "before any customer-visible use."
            ),
        },
        "forbidden_fields_absent": list(FORBIDDEN_CUSTOMER_OUTPUT_FIELDS),
        "separate_reviews": {
            "privacy_boundary_review_passed": True,
            "legal_advice_exclusion_review_passed": True,
            "non_guarantee_language_review_passed": True,
            "operator_publish_approval": False,
            "customer_delivery_approval": False,
        },
    }
    _assert_sample_is_conservative(offer_id, sample)
    return sample


def _schema_review_for_offer(gate: dict[str, Any], offer_id: str) -> dict[str, Any]:
    for review in gate.get("offer_schema_reviews", []):
        if review.get("offer") == offer_id:
            return review
    raise CityOpsContractError(f"sample outputs missing schema review for {offer_id}")


def _write_packet(packet: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_packet_is_conservative(packet)
    base_dir = _packet_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _packet_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("operator-reviewed sample outputs source gate schema mismatch")
    if gate.get("scope") != "internal_admin_schema_review_only":
        raise CityOpsContractError("operator-reviewed sample outputs source gate scope drift")
    if gate.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("operator-reviewed sample outputs source offer order drift")
    if PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SAFE_CLAIM not in gate.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("operator-reviewed sample outputs source safe claim drift")
    for flag in [
        "customer_copy_created",
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
    ]:
        if gate.get(flag) is not False:
            raise CityOpsContractError(
                f"operator-reviewed sample outputs source gate promoted readiness: {flag}"
            )
    missing_blocked = [
        claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in gate.get("do_not_claim_yet", [])
        and claim != "customer_sample_publication_ready"
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"operator-reviewed sample outputs source missing blocked claims: {missing_blocked}"
        )


def _assert_packet_is_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SCHEMA:
        raise CityOpsContractError("operator-reviewed sample outputs schema mismatch")
    if packet.get("scope") != "internal_admin_sample_output_review_only":
        raise CityOpsContractError("operator-reviewed sample outputs scope drift")
    if packet.get("sample_review_status") != "operator_reviewed_internal_samples_not_customer_copy":
        raise CityOpsContractError("operator-reviewed sample outputs status drift")
    if packet.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("operator-reviewed sample outputs offer order drift")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"operator-reviewed sample outputs promoted readiness: {flag}"
            )
    safe_to_claim = list(packet.get("safe_to_claim", []))
    do_not_claim_yet = list(packet.get("do_not_claim_yet", []))
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"operator-reviewed sample outputs has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"operator-reviewed sample outputs claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"operator-reviewed sample outputs missing blocked claims: {missing_blocked}"
        )
    if packet.get("sample_output_fields") != BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("operator-reviewed sample outputs field list drift")
    if packet.get("forbidden_customer_output_fields") != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("operator-reviewed sample outputs forbidden field drift")
    _assert_review_flags(packet.get("separate_reviews", {}), context="packet")
    samples = packet.get("offer_sample_outputs")
    if not isinstance(samples, list) or len(samples) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("operator-reviewed sample outputs sample count mismatch")
    for expected_offer, sample in zip(REQUIRED_OFFER_ORDER, samples):
        _assert_sample_is_conservative(expected_offer, sample)


def _assert_sample_is_conservative(expected_offer: str, sample: dict[str, Any]) -> None:
    if sample.get("offer") != expected_offer:
        raise CityOpsContractError("operator-reviewed sample outputs offer drift")
    if sample.get("sample_review_status") != "operator_reviewed_internal_sample_not_customer_copy":
        raise CityOpsContractError("operator-reviewed sample outputs sample status drift")
    for flag in [
        "sample_publishable",
        "customer_copy_ready",
        "customer_pilot_exposure_allowed",
    ]:
        if sample.get(flag) is not False:
            raise CityOpsContractError(
                f"operator-reviewed sample outputs sample promoted readiness: {expected_offer}:{flag}"
            )
    values = sample.get("allowed_field_values")
    if not isinstance(values, dict):
        raise CityOpsContractError("operator-reviewed sample outputs missing field values")
    if list(values.keys()) != BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("operator-reviewed sample outputs allowed field drift")
    forbidden_keys = sorted(FORBIDDEN_SAMPLE_KEYS & set(values.keys()))
    if forbidden_keys:
        raise CityOpsContractError(
            f"operator-reviewed sample outputs included forbidden keys: {forbidden_keys}"
        )
    if sample.get("forbidden_fields_absent") != FORBIDDEN_CUSTOMER_OUTPUT_FIELDS:
        raise CityOpsContractError("operator-reviewed sample outputs absent forbidden field drift")
    _assert_review_flags(sample.get("separate_reviews", {}), context=expected_offer)
    _assert_sample_text_is_safe(values, context=expected_offer)


def _assert_review_flags(review: dict[str, Any], *, context: str) -> None:
    if not isinstance(review, dict):
        raise CityOpsContractError(f"operator-reviewed sample outputs missing review flags: {context}")
    missing = [flag for flag in REQUIRED_SAMPLE_REVIEW_FLAGS if review.get(flag) is not True]
    if missing:
        raise CityOpsContractError(
            f"operator-reviewed sample outputs missing review gates: {context}:{missing}"
        )
    for flag in ["operator_publish_approval", "customer_delivery_approval"]:
        if review.get(flag) is not False:
            raise CityOpsContractError(
                f"operator-reviewed sample outputs promoted publish approval: {context}:{flag}"
            )


def _assert_sample_text_is_safe(values: dict[str, Any], *, context: str) -> None:
    serialized = json.dumps(values, sort_keys=True).lower()
    for fragment in FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(
                f"operator-reviewed sample outputs forbidden text fragment: {context}:{fragment}"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
