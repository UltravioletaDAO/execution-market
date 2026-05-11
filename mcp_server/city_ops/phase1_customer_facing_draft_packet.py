"""Internal/customer-facing draft packet for Phase 1 City Counter Ops offers.

This module creates one copy-shaped draft packet over the Phase 1 sample
publication checklist. The packet is deliberately internal/admin review material:
not approved, not publishable, not customer-deliverable, not a catalog, not a
pilot launch, not live Acontext/runtime parity, not dispatch, not reputation, not
exact GPS/raw metadata exposure, and not worker-copyable municipal doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_customer_output_schema_review_gate import REQUIRED_OFFER_ORDER
from .phase1_review_output_schemas import OFFER_SPEC_DIR
from .phase1_sample_publication_approval_checklist import (
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME,
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM,
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SCHEMA,
    load_phase1_sample_publication_approval_checklist,
)

PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA = (
    "city_ops.phase1_customer_facing_draft_packet.v1"
)
PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME = (
    "phase1_customer_facing_draft_packet.json"
)
PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM = (
    "phase1_customer_facing_draft_packet_landed"
)

REQUIRED_BLOCKED_CLAIMS = [
    "draft_packet_publication_ready",
    "publication_approval_ready",
    "publication_approved",
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
    "customer_delivery_approved",
}

READINESS_FALSE_FLAGS = [
    "customer_copy_created",
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_allowed",
    "front_door_sku_ready",
    "draft_packet_publishable",
    "draft_packet_publication_ready",
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

DRAFT_CARD_SPECS: dict[str, dict[str, Any]] = {
    "counter_reality_check": {
        "draft_title": "Counter Reality Check — bounded status draft",
        "customer_safe_positioning": (
            "A careful, reviewed summary of what a counter-facing source appears "
            "to support, with limitations and follow-up clearly separated."
        ),
        "draft_sections": [
            "What was checked",
            "What the reviewed source appears to support",
            "What this does not prove",
            "Recommended next step",
            "Operator review notice",
        ],
        "must_keep_limitations": [
            "Does not promise acceptance, approval, or influence.",
            "Does not provide legal advice or legal conclusions.",
            "Does not create reusable municipal instructions for workers.",
        ],
    },
    "packet_submission_attempt": {
        "draft_title": "Packet Submission Attempt — bounded handoff draft",
        "customer_safe_positioning": (
            "A concise, reviewed status draft for explaining a packet-submission "
            "attempt without turning it into a filing-success claim."
        ),
        "draft_sections": [
            "Attempt summary",
            "Evidence basis",
            "Observed outcome boundary",
            "Limitations and non-guarantees",
            "Recommended next step",
        ],
        "must_keep_limitations": [
            "Does not state that a packet was accepted or completed.",
            "Does not imply future office reuse or repeatability.",
            "Requires operator review before customer delivery.",
        ],
    },
    "posting_compliance_check": {
        "draft_title": "Posting Compliance Check — privacy-safe draft",
        "customer_safe_positioning": (
            "A privacy-safe draft shape for summarizing a posting-related check "
            "while excluding sensitive source details and completion claims."
        ),
        "draft_sections": [
            "Observed status summary",
            "Evidence reviewed",
            "Sensitive evidence excluded",
            "Limitations and non-guarantees",
            "Recommended next step",
        ],
        "must_keep_limitations": [
            "Does not state compliance completion or approval.",
            "Does not expose exact location metadata or raw source details.",
            "Requires separate evidence-redaction review before exposure.",
        ],
    },
}

REQUIRED_PRE_SEND_REVIEWS = [
    "final privacy/redaction review",
    "operator publish approval",
    "customer delivery approval",
    "blocked-claim adjacency check",
    "non-guarantee language check",
    "no dispatch or reputation claim check",
]

FORBIDDEN_TEXT_FRAGMENTS = [
    "guaranteed approval",
    "legal sufficiency",
    "regulator acceptance",
    "filing success",
    "erc-8004 reputation receipt",
    "erc8004 reputation receipt",
    "dispatch instruction",
]


def build_phase1_customer_facing_draft_packet(
    *,
    fixture_dir: str | Path | None = None,
    checklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one internal/admin draft packet over the publication checklist."""

    source = checklist or load_phase1_sample_publication_approval_checklist(
        fixture_dir=fixture_dir
    )
    _assert_source_checklist(source)

    safe_to_claim = _dedupe(
        [
            *source.get("safe_to_claim", []),
            PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *source.get("do_not_claim_yet", []),
        ]
    )

    packet = {
        "schema": PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA,
        "draft_packet_id": "city_counter_ops.phase1_customer_facing_draft_packet.2026_05_11",
        "scope": "internal_admin_customer_facing_draft_review_only",
        "source_checklist_id": source["checklist_id"],
        "source_checklist_schema": source["schema"],
        "source_artifact_filename": PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME,
        "offer_order": list(REQUIRED_OFFER_ORDER),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "draft_packet_status": "draft_created_not_approved_not_publishable",
        "customer_facing_draft_packet_created": True,
        "customer_copy_created": False,
        "customer_copy_ready": False,
        "customer_visible_catalog_ready": False,
        "public_service_catalog_ready": False,
        "controlled_concierge_pilot_ready": False,
        "customer_pilot_exposure_allowed": False,
        "front_door_sku_ready": False,
        "draft_packet_publishable": False,
        "draft_packet_publication_ready": False,
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
        "draft_cards": [
            _build_draft_card(review)
            for review in source.get("offer_publication_reviews", [])
        ],
        "operator_instruction": (
            "Use this as internal/admin draft-review material only. It is copy-shaped "
            "so an operator can evaluate tone and boundaries, but it is not customer "
            "copy, not approved, not publishable, and not routable."
        ),
        "next_smallest_proof": (
            "Record an explicit operator review decision against this draft packet. "
            "Do not flip publication_approved without a separate approval artifact."
        ),
    }
    _assert_packet_is_conservative(packet)
    return packet


def write_phase1_customer_facing_draft_packet(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the internal draft packet beside reviewed Phase 1 outputs."""

    packet = build_phase1_customer_facing_draft_packet(fixture_dir=fixture_dir)
    return _write_packet(packet, fixture_dir=fixture_dir)


def load_phase1_customer_facing_draft_packet(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted internal/customer-facing draft packet."""

    path = _packet_dir(fixture_dir) / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("customer-facing draft packet must be a JSON object")
    _assert_packet_is_conservative(packet)
    return packet


def _build_draft_card(review: dict[str, Any]) -> dict[str, Any]:
    offer = review.get("offer")
    if offer not in DRAFT_CARD_SPECS:
        raise CityOpsContractError(f"customer-facing draft packet unknown offer: {offer}")
    spec = DRAFT_CARD_SPECS[offer]
    card = {
        "offer": offer,
        "source_package_id": review.get("source_package_id"),
        "source_sample_review_status": review.get("source_sample_review_status"),
        "draft_title": spec["draft_title"],
        "customer_safe_positioning": spec["customer_safe_positioning"],
        "draft_sections": spec["draft_sections"],
        "must_keep_limitations": spec["must_keep_limitations"],
        "required_before_send": list(REQUIRED_PRE_SEND_REVIEWS),
        "draft_ready_for_customer": False,
        "draft_publishable": False,
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
        "source_publication_ready": review.get("publication_ready"),
        "source_sample_publishable": review.get("sample_publishable"),
    }
    _assert_draft_card_is_conservative(card)
    return card


def _write_packet(packet: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_packet_is_conservative(packet)
    base_dir = _packet_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _packet_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_source_checklist(source: dict[str, Any]) -> None:
    if source.get("schema") != PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SCHEMA:
        raise CityOpsContractError("customer-facing draft packet source schema mismatch")
    if source.get("scope") != "internal_admin_publication_approval_checklist_only":
        raise CityOpsContractError("customer-facing draft packet source scope drift")
    if source.get("publication_approval_status") != "not_approved_internal_checklist_only":
        raise CityOpsContractError("customer-facing draft packet source status drift")
    if source.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("customer-facing draft packet source offer order drift")
    if PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM not in source.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("customer-facing draft packet source safe claim drift")
    for flag in [
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
        "worker_copyable_doctrine_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        if source.get(flag) is not False:
            raise CityOpsContractError(
                f"customer-facing draft packet source promoted readiness: {flag}"
            )
    gate_status = source.get("approval_gates_status")
    if not isinstance(gate_status, dict):
        raise CityOpsContractError("customer-facing draft packet missing source gate status")
    for gate in [
        "evidence_redaction_review_required",
        "operator_publish_approval_required",
        "customer_delivery_approval_required",
    ]:
        status = gate_status.get(gate, {})
        if status.get("verified") is not False or status.get("approval_granted") is not False:
            raise CityOpsContractError(
                f"customer-facing draft packet source approval gate promoted: {gate}"
            )
    missing_blocked = [
        claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in source.get("do_not_claim_yet", [])
        and claim not in {"draft_packet_publication_ready", "publication_approved"}
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"customer-facing draft packet source missing blocked claims: {missing_blocked}"
        )
    reviews = source.get("offer_publication_reviews")
    if not isinstance(reviews, list) or len(reviews) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("customer-facing draft packet source review count mismatch")
    for expected_offer, review in zip(REQUIRED_OFFER_ORDER, reviews):
        if review.get("offer") != expected_offer:
            raise CityOpsContractError("customer-facing draft packet source review order drift")
        for flag in [
            "publication_ready",
            "sample_publishable",
            "customer_copy_ready",
            "operator_publish_approval",
            "customer_delivery_approval",
        ]:
            if review.get(flag) is not False:
                raise CityOpsContractError(
                    f"customer-facing draft packet source offer promoted readiness: {expected_offer}:{flag}"
                )


def _assert_packet_is_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA:
        raise CityOpsContractError("customer-facing draft packet schema mismatch")
    if packet.get("scope") != "internal_admin_customer_facing_draft_review_only":
        raise CityOpsContractError("customer-facing draft packet scope drift")
    if packet.get("draft_packet_status") != "draft_created_not_approved_not_publishable":
        raise CityOpsContractError("customer-facing draft packet status drift")
    if packet.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("customer-facing draft packet offer order drift")
    if packet.get("customer_facing_draft_packet_created") is not True:
        raise CityOpsContractError("customer-facing draft packet creation marker drift")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"customer-facing draft packet promoted readiness: {flag}"
            )
    safe_to_claim = list(packet.get("safe_to_claim", []))
    do_not_claim_yet = list(packet.get("do_not_claim_yet", []))
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"customer-facing draft packet has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"customer-facing draft packet claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"customer-facing draft packet missing blocked claims: {missing_blocked}"
        )
    cards = packet.get("draft_cards")
    if not isinstance(cards, list) or len(cards) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("customer-facing draft packet card count mismatch")
    for expected_offer, card in zip(REQUIRED_OFFER_ORDER, cards):
        if card.get("offer") != expected_offer:
            raise CityOpsContractError("customer-facing draft packet card order drift")
        _assert_draft_card_is_conservative(card)


def _assert_draft_card_is_conservative(card: dict[str, Any]) -> None:
    for flag in [
        "draft_ready_for_customer",
        "draft_publishable",
        "operator_publish_approval",
        "customer_delivery_approval",
        "source_publication_ready",
        "source_sample_publishable",
    ]:
        if card.get(flag) is not False:
            raise CityOpsContractError(
                f"customer-facing draft packet card promoted readiness: {card.get('offer')}:{flag}"
            )
    required = card.get("required_before_send")
    if not isinstance(required, list):
        raise CityOpsContractError("customer-facing draft packet missing send prerequisites")
    for item in REQUIRED_PRE_SEND_REVIEWS:
        if item not in required:
            raise CityOpsContractError(
                f"customer-facing draft packet missing send prerequisite: {card.get('offer')}:{item}"
            )
    serialized = json.dumps(card, sort_keys=True).lower()
    for fragment in FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(
                f"customer-facing draft packet forbidden text fragment: {card.get('offer')}:{fragment}"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
