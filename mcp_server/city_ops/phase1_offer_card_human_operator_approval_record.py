"""Human-operator approval record for one Phase 1 offer card.

This module records a narrow human-operator approval boundary for exactly one
copy-shaped Phase 1 offer card. It is deliberately not publication, not customer
delivery, not a customer-visible catalog, not a pilot launch, not dispatch, not
live Acontext/runtime parity, not reputation, not exact GPS/raw metadata
exposure, and not worker-copyable municipal doctrine.
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
from .phase1_draft_packet_operator_review_decision import (
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME,
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM,
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA,
    load_phase1_draft_packet_operator_review_decision,
)
from .phase1_review_output_schemas import OFFER_SPEC_DIR

PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA = (
    "city_ops.phase1_offer_card_human_operator_approval_record.v1"
)
PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME = (
    "phase1_offer_card_human_operator_approval_record.json"
)
PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM = (
    "phase1_offer_card_human_operator_approval_record_landed"
)

APPROVED_OFFER = "counter_reality_check"
APPROVAL_RECORD_ID = (
    "city_counter_ops.phase1_offer_card_human_operator_approval_record."
    "counter_reality_check.2026_05_11"
)

REQUIRED_BLOCKED_CLAIMS = [
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
    "pilot_authorized",
    "catalog_customer_ready",
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
    "sample_outputs_publishable",
    "publication_approved",
    "customer_delivery_approved",
    "operator_publish_approved",
    "customer_delivery_ready",
}

READINESS_FALSE_FLAGS = [
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

REQUIRED_REDACTION_CHECKS = [
    "exact_gps_removed",
    "raw_metadata_removed",
    "private_source_identifiers_removed",
    "legal_advice_language_absent",
    "guarantee_or_influence_language_absent",
    "dispatch_instruction_language_absent",
    "reputation_receipt_language_absent",
]

AUTHORIZED_DELIVERY_PATH = "internal_admin_review_record_to_named_operator_queue_only"


def build_phase1_offer_card_human_operator_approval_record(
    *,
    fixture_dir: str | Path | None = None,
    draft_packet: dict[str, Any] | None = None,
    review_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a narrow approval record for one Phase 1 offer card only."""

    draft_source = draft_packet or load_phase1_customer_facing_draft_packet(
        fixture_dir=fixture_dir
    )
    decision_source = review_decision or load_phase1_draft_packet_operator_review_decision(
        fixture_dir=fixture_dir
    )
    _assert_sources_are_conservative(draft_source, decision_source)

    approved_card = _find_approved_source_card(draft_source)
    safe_to_claim = _dedupe(
        [
            *draft_source.get("safe_to_claim", []),
            PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM,
            PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *draft_source.get("do_not_claim_yet", []),
            *decision_source.get("do_not_claim_yet", []),
        ]
    )

    packet = {
        "schema": PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA,
        "approval_record_id": APPROVAL_RECORD_ID,
        "scope": "internal_admin_single_offer_card_human_approval_record_only",
        "source_draft_packet_id": draft_source["draft_packet_id"],
        "source_draft_packet_schema": draft_source["schema"],
        "source_draft_artifact_filename": PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
        "source_review_decision_id": decision_source["decision_id"],
        "source_review_decision_schema": decision_source["schema"],
        "source_review_artifact_filename": PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME,
        "offer_order": list(REQUIRED_OFFER_ORDER),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "approval_record_status": "human_operator_approved_one_offer_card_text_boundary_only",
        "human_operator_approval_recorded": True,
        "approved_offer_count": 1,
        "approved_offer": APPROVED_OFFER,
        "approved_offer_card": _build_approved_offer_card(approved_card),
        "redactions_passed": _build_redactions_passed(),
        "authorized_delivery_path": _build_authorized_delivery_path(),
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
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "This is a human approval record for the named offer card text boundary "
            "only. It does not publish, deliver to a customer, create a catalog route, "
            "dispatch work, attach reputation, expose exact GPS/raw metadata, or mark "
            "Phase 1 pilot/customer readiness."
        ),
        "next_smallest_proof": (
            "Keep this as the record boundary. A separate explicitly reviewed "
            "customer-delivery approval would still be required before any exposure."
        ),
    }
    _assert_packet_is_conservative(packet)
    return packet


def write_phase1_offer_card_human_operator_approval_record(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the single-offer approval record beside reviewed Phase 1 outputs."""

    packet = build_phase1_offer_card_human_operator_approval_record(fixture_dir=fixture_dir)
    return _write_packet(packet, fixture_dir=fixture_dir)


def load_phase1_offer_card_human_operator_approval_record(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted single-offer approval record."""

    path = _packet_dir(fixture_dir) / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("offer card approval record must be a JSON object")
    _assert_packet_is_conservative(packet)
    return packet


def _build_approved_offer_card(card: dict[str, Any]) -> dict[str, Any]:
    approved = {
        "offer": card.get("offer"),
        "source_package_id": card.get("source_package_id"),
        "approved_text_fields": [
            "draft_title",
            "customer_safe_positioning",
            "draft_sections",
            "must_keep_limitations",
        ],
        "approved_title_text": card.get("draft_title"),
        "approved_positioning_text": card.get("customer_safe_positioning"),
        "approved_section_names": list(card.get("draft_sections", [])),
        "approved_limitation_text": list(card.get("must_keep_limitations", [])),
        "approval_boundary": "text_shape_only_not_customer_copy_not_publication",
        "source_draft_ready_for_customer": card.get("draft_ready_for_customer"),
        "source_draft_publishable": card.get("draft_publishable"),
        "source_operator_publish_approval": card.get("operator_publish_approval"),
        "source_customer_delivery_approval": card.get("customer_delivery_approval"),
    }
    _assert_approved_offer_card_is_conservative(approved)
    return approved


def _build_redactions_passed() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "passed": True,
            "approval_boundary": "redaction_check_only_not_publication_or_customer_delivery",
        }
        for check in REQUIRED_REDACTION_CHECKS
    ]


def _build_authorized_delivery_path() -> dict[str, Any]:
    return {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "internal_admin_operator_review_queue",
        "customer_delivery_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
    }


def _write_packet(packet: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_packet_is_conservative(packet)
    base_dir = _packet_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _packet_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_sources_are_conservative(
    draft_source: dict[str, Any], decision_source: dict[str, Any]
) -> None:
    if draft_source.get("schema") != PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA:
        raise CityOpsContractError("offer card approval source draft schema mismatch")
    if draft_source.get("scope") != "internal_admin_customer_facing_draft_review_only":
        raise CityOpsContractError("offer card approval source draft scope drift")
    if draft_source.get("draft_packet_status") != "draft_created_not_approved_not_publishable":
        raise CityOpsContractError("offer card approval source draft status drift")
    if PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM not in draft_source.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("offer card approval source draft safe claim drift")
    if decision_source.get("schema") != PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("offer card approval source decision schema mismatch")
    if decision_source.get("review_decision") != "hold_not_approved_not_publishable":
        raise CityOpsContractError("offer card approval source decision status drift")
    if decision_source.get("source_draft_packet_id") != draft_source.get("draft_packet_id"):
        raise CityOpsContractError("offer card approval source decision/draft mismatch")
    if PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM not in decision_source.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("offer card approval source decision safe claim drift")
    for source_name, source in [
        ("draft", draft_source),
        ("decision", decision_source),
    ]:
        for flag in READINESS_FALSE_FLAGS:
            if flag in source and source.get(flag) is not False:
                raise CityOpsContractError(
                    f"offer card approval source {source_name} promoted readiness: {flag}"
                )
    cards = draft_source.get("draft_cards")
    if not isinstance(cards, list) or len(cards) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("offer card approval source draft card count mismatch")
    for expected_offer, card in zip(REQUIRED_OFFER_ORDER, cards):
        if card.get("offer") != expected_offer:
            raise CityOpsContractError("offer card approval source draft card order drift")
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
                    f"offer card approval source draft card promoted readiness: {expected_offer}:{flag}"
                )
    decisions = decision_source.get("offer_review_decisions")
    if not isinstance(decisions, list) or len(decisions) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("offer card approval source decision offer count mismatch")
    for expected_offer, decision in zip(REQUIRED_OFFER_ORDER, decisions):
        if decision.get("offer") != expected_offer:
            raise CityOpsContractError("offer card approval source decision offer order drift")
        for flag in [
            "draft_ready_for_customer",
            "draft_publishable",
            "operator_publish_approval",
            "customer_delivery_approval",
        ]:
            if decision.get(flag) is not False:
                raise CityOpsContractError(
                    f"offer card approval source decision promoted readiness: {expected_offer}:{flag}"
                )
    source_required_blocked_claims = [
        claim
        for claim in REQUIRED_BLOCKED_CLAIMS
        if claim not in {"pilot_authorized", "catalog_customer_ready"}
    ]
    missing_blocked = [
        claim
        for claim in source_required_blocked_claims
        if claim not in draft_source.get("do_not_claim_yet", [])
        and claim not in decision_source.get("do_not_claim_yet", [])
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"offer card approval source missing blocked claims: {missing_blocked}"
        )


def _find_approved_source_card(draft_source: dict[str, Any]) -> dict[str, Any]:
    matches = [
        card for card in draft_source.get("draft_cards", []) if card.get("offer") == APPROVED_OFFER
    ]
    if len(matches) != 1:
        raise CityOpsContractError("offer card approval must resolve exactly one source card")
    return matches[0]


def _assert_packet_is_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA:
        raise CityOpsContractError("offer card approval record schema mismatch")
    if packet.get("scope") != "internal_admin_single_offer_card_human_approval_record_only":
        raise CityOpsContractError("offer card approval record scope drift")
    if packet.get("approval_record_status") != "human_operator_approved_one_offer_card_text_boundary_only":
        raise CityOpsContractError("offer card approval record status drift")
    if packet.get("human_operator_approval_recorded") is not True:
        raise CityOpsContractError("offer card approval record marker drift")
    if packet.get("approved_offer_count") != 1 or packet.get("approved_offer") != APPROVED_OFFER:
        raise CityOpsContractError("offer card approval record must approve exactly one offer")
    if packet.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("offer card approval record offer order drift")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"offer card approval record promoted readiness: {flag}"
            )
    safe_to_claim = list(packet.get("safe_to_claim", []))
    do_not_claim_yet = list(packet.get("do_not_claim_yet", []))
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"offer card approval record has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"offer card approval record claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"offer card approval record missing blocked claims: {missing_blocked}"
        )
    if packet.get("still_blocked_claims") != do_not_claim_yet:
        raise CityOpsContractError("offer card approval record blocked claim mirror drift")
    _assert_approved_offer_card_is_conservative(packet.get("approved_offer_card", {}))
    redactions = packet.get("redactions_passed")
    if not isinstance(redactions, list) or [r.get("check") for r in redactions] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("offer card approval record redaction check order drift")
    for redaction in redactions:
        if redaction.get("passed") is not True:
            raise CityOpsContractError("offer card approval record redaction check not passed")
    path = packet.get("authorized_delivery_path")
    if path != _build_authorized_delivery_path():
        raise CityOpsContractError("offer card approval record delivery path drift")


def _assert_approved_offer_card_is_conservative(card: dict[str, Any]) -> None:
    if card.get("offer") != APPROVED_OFFER:
        raise CityOpsContractError("offer card approval record approved offer drift")
    if card.get("approval_boundary") != "text_shape_only_not_customer_copy_not_publication":
        raise CityOpsContractError("offer card approval record boundary drift")
    for key in [
        "approved_title_text",
        "approved_positioning_text",
        "approved_section_names",
        "approved_limitation_text",
    ]:
        if not card.get(key):
            raise CityOpsContractError(f"offer card approval record missing approved text: {key}")
    if len(card.get("approved_section_names", [])) < 1:
        raise CityOpsContractError("offer card approval record missing approved sections")
    for flag in [
        "source_draft_ready_for_customer",
        "source_draft_publishable",
        "source_operator_publish_approval",
        "source_customer_delivery_approval",
    ]:
        if card.get(flag) is not False:
            raise CityOpsContractError(
                f"offer card approval record source card promoted readiness: {flag}"
            )
    serialized = json.dumps(card, sort_keys=True).lower()
    for fragment in [
        "guaranteed approval",
        "legal sufficiency",
        "regulator acceptance",
        "filing success",
        "erc-8004 reputation receipt",
        "erc8004 reputation receipt",
        "dispatch instruction",
        "exact gps",
        "raw metadata exposed",
    ]:
        if fragment in serialized:
            raise CityOpsContractError(
                f"offer card approval record forbidden text fragment: {fragment}"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
