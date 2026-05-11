"""Operator review hold decision for Phase 1 customer-facing draft packet.

This module records a conservative internal/admin decision over the Phase 1
customer-facing draft packet. It intentionally records a hold, not approval:
no publication, no customer delivery, no public/catalog route, no pilot launch,
no dispatch, no live Acontext/runtime parity, no reputation, no exact GPS/raw
metadata exposure, and no worker-copyable municipal doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_customer_facing_draft_packet import (
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM,
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA,
    load_phase1_customer_facing_draft_packet,
)
from .phase1_customer_output_schema_review_gate import REQUIRED_OFFER_ORDER
from .phase1_review_output_schemas import OFFER_SPEC_DIR

PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA = (
    "city_ops.phase1_draft_packet_operator_review_decision.v1"
)
PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME = (
    "phase1_draft_packet_operator_review_decision.json"
)
PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM = (
    "phase1_draft_packet_operator_review_decision_landed"
)

REQUIRED_BLOCKED_CLAIMS = [
    "operator_review_granted",
    "operator_publish_approval",
    "customer_delivery_approval",
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
    "operator_review_approved",
}

READINESS_FALSE_FLAGS = [
    "operator_review_granted",
    "operator_publish_approval",
    "customer_delivery_approval",
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

REQUIRED_REVIEW_FINDINGS = [
    "safe_and_blocked_claims_remain_adjacent",
    "draft_cards_are_copy_shaped_but_not_customer_ready",
    "required_before_send_reviews_are_present",
    "publication_and_customer_delivery_remain_unapproved",
    "dispatch_and_reputation_claims_remain_absent",
    "exact_gps_and_raw_metadata_remain_excluded",
]

PER_OFFER_DECISION = "hold_for_explicit_human_operator_review"


def build_phase1_draft_packet_operator_review_decision(
    *,
    fixture_dir: str | Path | None = None,
    draft_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative hold decision over the draft packet."""

    source = draft_packet or load_phase1_customer_facing_draft_packet(
        fixture_dir=fixture_dir
    )
    _assert_source_draft_packet(source)

    safe_to_claim = _dedupe(
        [
            *source.get("safe_to_claim", []),
            PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *source.get("do_not_claim_yet", []),
        ]
    )

    packet = {
        "schema": PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA,
        "decision_id": "city_counter_ops.phase1_draft_packet_operator_review_decision.2026_05_11",
        "scope": "internal_admin_publication_hold_decision_only",
        "source_draft_packet_id": source["draft_packet_id"],
        "source_draft_packet_schema": source["schema"],
        "source_artifact_filename": PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
        "offer_order": list(REQUIRED_OFFER_ORDER),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "review_decision": "hold_not_approved_not_publishable",
        "operator_review_recorded": True,
        "operator_review_granted": False,
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
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
        "review_findings": _build_review_findings(),
        "offer_review_decisions": [
            _build_offer_review_decision(card)
            for card in source.get("draft_cards", [])
        ],
        "operator_instruction": (
            "This decision records that the copy-shaped packet exists and has been "
            "held for explicit human operator review. Do not publish, deliver, route, "
            "dispatch, attach reputation, expose raw location/metadata, or flip "
            "publication_approved from this artifact."
        ),
        "next_smallest_proof": (
            "If Saúl wants to proceed, capture a separate human operator approval "
            "artifact that names exactly which offer card is approved, which redactions "
            "passed, and which delivery path is authorized."
        ),
    }
    _assert_packet_is_conservative(packet)
    return packet


def write_phase1_draft_packet_operator_review_decision(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the conservative hold decision beside reviewed Phase 1 outputs."""

    packet = build_phase1_draft_packet_operator_review_decision(fixture_dir=fixture_dir)
    return _write_packet(packet, fixture_dir=fixture_dir)


def load_phase1_draft_packet_operator_review_decision(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted conservative hold decision."""

    path = _packet_dir(fixture_dir) / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("draft packet operator review decision must be a JSON object")
    _assert_packet_is_conservative(packet)
    return packet


def _build_review_findings() -> list[dict[str, Any]]:
    return [
        {
            "finding": finding,
            "verified": True,
            "approval_granted": False,
        }
        for finding in REQUIRED_REVIEW_FINDINGS
    ]


def _build_offer_review_decision(card: dict[str, Any]) -> dict[str, Any]:
    offer = card.get("offer")
    if offer not in REQUIRED_OFFER_ORDER:
        raise CityOpsContractError(f"unknown draft card offer for review decision: {offer}")
    decision = {
        "offer": offer,
        "source_package_id": card.get("source_package_id"),
        "source_draft_title": card.get("draft_title"),
        "review_decision": PER_OFFER_DECISION,
        "draft_ready_for_customer": False,
        "draft_publishable": False,
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
        "required_before_send": list(card.get("required_before_send", [])),
        "hold_reason": (
            "Draft shape is useful for review, but explicit human operator approval, "
            "final privacy/redaction review, and customer delivery approval are still missing."
        ),
    }
    _assert_offer_decision_is_conservative(decision)
    return decision


def _write_packet(packet: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_packet_is_conservative(packet)
    base_dir = _packet_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _packet_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_source_draft_packet(source: dict[str, Any]) -> None:
    if source.get("schema") != PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA:
        raise CityOpsContractError("draft packet operator review decision source schema mismatch")
    if source.get("scope") != "internal_admin_customer_facing_draft_review_only":
        raise CityOpsContractError("draft packet operator review decision source scope drift")
    if source.get("draft_packet_status") != "draft_created_not_approved_not_publishable":
        raise CityOpsContractError("draft packet operator review decision source status drift")
    if source.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("draft packet operator review decision source offer order drift")
    if PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM not in source.get("safe_to_claim", []):
        raise CityOpsContractError("draft packet operator review decision source safe claim drift")
    for flag in READINESS_FALSE_FLAGS:
        if flag in {
            "operator_review_granted",
            "operator_publish_approval",
            "customer_delivery_approval",
        }:
            continue
        if source.get(flag) is not False:
            raise CityOpsContractError(
                f"draft packet operator review decision source promoted readiness: {flag}"
            )
    missing_blocked = [
        claim for claim in REQUIRED_BLOCKED_CLAIMS
        if claim not in source.get("do_not_claim_yet", [])
        and claim not in {"operator_review_granted", "operator_publish_approval", "customer_delivery_approval"}
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"draft packet operator review decision source missing blocked claims: {missing_blocked}"
        )
    cards = source.get("draft_cards")
    if not isinstance(cards, list) or len(cards) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("draft packet operator review decision source card count mismatch")
    for expected_offer, card in zip(REQUIRED_OFFER_ORDER, cards):
        if card.get("offer") != expected_offer:
            raise CityOpsContractError("draft packet operator review decision source card order drift")
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
                    f"draft packet operator review decision source card promoted readiness: {expected_offer}:{flag}"
                )


def _assert_packet_is_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("draft packet operator review decision schema mismatch")
    if packet.get("scope") != "internal_admin_publication_hold_decision_only":
        raise CityOpsContractError("draft packet operator review decision scope drift")
    if packet.get("review_decision") != "hold_not_approved_not_publishable":
        raise CityOpsContractError("draft packet operator review decision status drift")
    if packet.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("draft packet operator review decision offer order drift")
    if packet.get("operator_review_recorded") is not True:
        raise CityOpsContractError("draft packet operator review decision record marker drift")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"draft packet operator review decision promoted readiness: {flag}"
            )
    safe_to_claim = list(packet.get("safe_to_claim", []))
    do_not_claim_yet = list(packet.get("do_not_claim_yet", []))
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"draft packet operator review decision has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"draft packet operator review decision claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"draft packet operator review decision missing blocked claims: {missing_blocked}"
        )
    findings = packet.get("review_findings")
    if not isinstance(findings, list) or len(findings) != len(REQUIRED_REVIEW_FINDINGS):
        raise CityOpsContractError("draft packet operator review decision finding count mismatch")
    for expected, finding in zip(REQUIRED_REVIEW_FINDINGS, findings):
        if finding.get("finding") != expected:
            raise CityOpsContractError("draft packet operator review decision finding order drift")
        if finding.get("verified") is not True or finding.get("approval_granted") is not False:
            raise CityOpsContractError("draft packet operator review decision finding approval drift")
    decisions = packet.get("offer_review_decisions")
    if not isinstance(decisions, list) or len(decisions) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("draft packet operator review decision offer count mismatch")
    for expected_offer, decision in zip(REQUIRED_OFFER_ORDER, decisions):
        if decision.get("offer") != expected_offer:
            raise CityOpsContractError("draft packet operator review decision offer order drift")
        _assert_offer_decision_is_conservative(decision)


def _assert_offer_decision_is_conservative(decision: dict[str, Any]) -> None:
    if decision.get("review_decision") != PER_OFFER_DECISION:
        raise CityOpsContractError(
            f"draft packet operator review decision promoted offer decision: {decision.get('offer')}"
        )
    for flag in [
        "draft_ready_for_customer",
        "draft_publishable",
        "operator_publish_approval",
        "customer_delivery_approval",
    ]:
        if decision.get(flag) is not False:
            raise CityOpsContractError(
                f"draft packet operator review decision offer promoted readiness: {decision.get('offer')}:{flag}"
            )
    required = decision.get("required_before_send")
    if not isinstance(required, list):
        raise CityOpsContractError("draft packet operator review decision missing send prerequisites")
    for item in [
        "final privacy/redaction review",
        "operator publish approval",
        "customer delivery approval",
        "blocked-claim adjacency check",
        "no dispatch or reputation claim check",
    ]:
        if item not in required:
            raise CityOpsContractError(
                f"draft packet operator review decision missing send prerequisite: {decision.get('offer')}:{item}"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
