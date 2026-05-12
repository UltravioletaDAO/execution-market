"""Approval coverage matrix for Phase 1 City Counter Ops offer cards.

This module compares the three copy-shaped Phase 1 offer cards against the
single-offer human-operator approval record. It is deliberately an internal
coverage matrix, not customer delivery, not publication, not a customer-visible
catalog, not dispatch, not live Acontext/runtime parity, not reputation, not
exact GPS/raw metadata exposure, and not worker-copyable municipal doctrine.
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
from .phase1_offer_card_human_operator_approval_record import (
    APPROVED_OFFER,
    AUTHORIZED_DELIVERY_PATH,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA,
    REQUIRED_REDACTION_CHECKS,
    load_phase1_offer_card_human_operator_approval_record,
)
from .phase1_review_output_schemas import OFFER_SPEC_DIR

PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SCHEMA = (
    "city_ops.phase1_offer_card_approval_coverage_matrix.v1"
)
PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME = (
    "phase1_offer_card_approval_coverage_matrix.json"
)
PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM = (
    "phase1_offer_card_approval_coverage_matrix_landed"
)

MATRIX_ID = "city_counter_ops.phase1_offer_card_approval_coverage_matrix.2026_05_11"
MATRIX_SCOPE = "internal_admin_phase1_offer_card_approval_coverage_matrix_only"
MATRIX_STATUS = (
    "one_offer_text_boundary_approved_two_offer_cards_unapproved_"
    "all_customer_delivery_blocked"
)

REQUIRED_BLOCKED_CLAIMS = [
    "phase1_approval_coverage_incomplete",
    "two_phase1_offer_cards_missing_human_operator_text_boundary_approval",
    "operator_publish_approval_missing_for_all_offer_cards",
    "customer_delivery_approval_missing_for_all_offer_cards",
    "publication_approval_missing_for_all_offer_cards",
    "catalog_route_authorization_missing_for_all_offer_cards",
    "dispatch_authorization_missing_for_all_offer_cards",
    "reputation_attachment_authorization_missing_for_all_offer_cards",
    "exact_gps_or_raw_metadata_release_authorization_missing_for_all_offer_cards",
    "operator_publish_approval",
    "customer_delivery_approval",
    "draft_packet_publication_ready",
    "publication_approval_ready",
    "publication_approved",
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
    "phase1_approval_coverage_complete",
    "all_offer_cards_approved",
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
    "catalog_route_ready",
    "controlled_pilot_authorized",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
]

BASE_MISSING_APPROVALS = [
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approval",
    "catalog_route_authorization",
    "controlled_pilot_authorization",
    "dispatch_authorization",
    "reputation_attachment_authorization",
    "exact_gps_or_raw_metadata_release_authorization",
]

UNAPPROVED_OFFER_EXTRA_MISSING = [
    "human_operator_text_boundary_approval",
    "offer_specific_redaction_review_record",
]


def build_phase1_offer_card_approval_coverage_matrix(
    *,
    fixture_dir: str | Path | None = None,
    draft_packet: dict[str, Any] | None = None,
    review_decision: dict[str, Any] | None = None,
    approval_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the internal approval-coverage matrix for all three offer cards."""

    draft_source = draft_packet or load_phase1_customer_facing_draft_packet(
        fixture_dir=fixture_dir
    )
    decision_source = review_decision or load_phase1_draft_packet_operator_review_decision(
        fixture_dir=fixture_dir
    )
    approval_source = approval_record or load_phase1_offer_card_human_operator_approval_record(
        fixture_dir=fixture_dir
    )
    _assert_sources_are_conservative(draft_source, decision_source, approval_source)

    safe_to_claim = _dedupe(
        [
            *draft_source.get("safe_to_claim", []),
            PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM,
            PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
            PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *draft_source.get("do_not_claim_yet", []),
            *decision_source.get("do_not_claim_yet", []),
            *approval_source.get("do_not_claim_yet", []),
        ]
    )

    approved_offers = [approval_source["approved_offer"]]
    unapproved_offers = [offer for offer in REQUIRED_OFFER_ORDER if offer not in approved_offers]

    packet = {
        "schema": PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SCHEMA,
        "matrix_id": MATRIX_ID,
        "scope": MATRIX_SCOPE,
        "source_draft_packet_id": draft_source["draft_packet_id"],
        "source_draft_packet_schema": draft_source["schema"],
        "source_draft_artifact_filename": PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
        "source_review_decision_id": decision_source["decision_id"],
        "source_review_decision_schema": decision_source["schema"],
        "source_review_artifact_filename": PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME,
        "source_approval_record_id": approval_source["approval_record_id"],
        "source_approval_record_schema": approval_source["schema"],
        "source_approval_artifact_filename": PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
        "offer_order": list(REQUIRED_OFFER_ORDER),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "approval_coverage_status": MATRIX_STATUS,
        "approval_summary": {
            "approved_offer_count": len(approved_offers),
            "approved_offers": approved_offers,
            "unapproved_offers": unapproved_offers,
            "coverage_complete": False,
            "customer_delivery_ready": False,
            "operator_publish_ready": False,
            "publication_ready": False,
            "catalog_route_ready": False,
            "dispatch_ready": False,
            "reputation_ready": False,
            "exact_gps_or_raw_metadata_release_ready": False,
        },
        "coverage_rows": [
            _build_coverage_row(
                offer=offer,
                draft_card=_find_draft_card(draft_source, offer),
                approval_source=approval_source,
            )
            for offer in REQUIRED_OFFER_ORDER
        ],
        "authorized_delivery_path_boundary": {
            "approved_record_path": AUTHORIZED_DELIVERY_PATH,
            "customer_delivery_allowed": False,
            "public_route_allowed": False,
            "catalog_route_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "exact_gps_or_raw_metadata_allowed": False,
        },
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
        "catalog_route_ready": False,
        "controlled_pilot_authorized": False,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "worker_skill_dna_ready": False,
        "worker_copyable_doctrine_ready": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this as an internal approval coverage matrix only. One offer card "
            "has a text-boundary approval record; two offer cards remain missing "
            "that record, and all three still lack operator publish approval, "
            "customer delivery approval, publication approval, catalog routing, "
            "dispatch, reputation attachment, and exact GPS/raw metadata release."
        ),
        "next_smallest_proof": (
            "Either add separate human-operator text-boundary approval records for "
            "Packet Submission Attempt and Posting Compliance Check, or keep the "
            "single approved record held until an explicit customer-delivery approval "
            "artifact is reviewed. Do not publish or route publicly by default."
        ),
    }
    _assert_packet_is_conservative(packet)
    return packet


def write_phase1_offer_card_approval_coverage_matrix(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the approval coverage matrix beside reviewed Phase 1 outputs."""

    packet = build_phase1_offer_card_approval_coverage_matrix(fixture_dir=fixture_dir)
    return _write_packet(packet, fixture_dir=fixture_dir)


def load_phase1_offer_card_approval_coverage_matrix(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted approval coverage matrix."""

    path = _packet_dir(fixture_dir) / PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("offer card approval coverage matrix must be a JSON object")
    _assert_packet_is_conservative(packet)
    return packet


def _build_coverage_row(
    *, offer: str, draft_card: dict[str, Any], approval_source: dict[str, Any]
) -> dict[str, Any]:
    approved = offer == approval_source.get("approved_offer")
    missing_approvals = list(BASE_MISSING_APPROVALS)
    if not approved:
        missing_approvals = [*UNAPPROVED_OFFER_EXTRA_MISSING, *missing_approvals]
    row = {
        "offer": offer,
        "source_package_id": draft_card.get("source_package_id"),
        "draft_card_present": True,
        "human_operator_text_boundary_approved": approved,
        "approved_text_fields": (
            list(approval_source["approved_offer_card"].get("approved_text_fields", []))
            if approved
            else []
        ),
        "approved_delivery_path": AUTHORIZED_DELIVERY_PATH if approved else None,
        "redaction_checks_recorded": list(REQUIRED_REDACTION_CHECKS) if approved else [],
        "missing_approvals_before_customer_exposure": missing_approvals,
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
        "publication_approved": False,
        "catalog_route_ready": False,
        "controlled_pilot_authorized": False,
        "dispatch_ready": False,
        "reputation_ready": False,
        "exact_gps_or_raw_metadata_release_ready": False,
        "row_verdict": (
            "text_boundary_approved_but_customer_delivery_still_blocked"
            if approved
            else "missing_human_operator_text_boundary_approval"
        ),
    }
    _assert_row_is_conservative(row, approved=approved)
    return row


def _write_packet(packet: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_packet_is_conservative(packet)
    base_dir = _packet_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _packet_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_sources_are_conservative(
    draft_source: dict[str, Any],
    decision_source: dict[str, Any],
    approval_source: dict[str, Any],
) -> None:
    if draft_source.get("schema") != PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA:
        raise CityOpsContractError("approval coverage matrix source draft schema mismatch")
    if draft_source.get("scope") != "internal_admin_customer_facing_draft_review_only":
        raise CityOpsContractError("approval coverage matrix source draft scope drift")
    if PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM not in draft_source.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval coverage matrix source draft safe claim drift")
    if decision_source.get("schema") != PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA:
        raise CityOpsContractError("approval coverage matrix source decision schema mismatch")
    if decision_source.get("review_decision") != "hold_not_approved_not_publishable":
        raise CityOpsContractError("approval coverage matrix source decision status drift")
    if decision_source.get("source_draft_packet_id") != draft_source.get("draft_packet_id"):
        raise CityOpsContractError("approval coverage matrix source decision/draft mismatch")
    if approval_source.get("schema") != PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA:
        raise CityOpsContractError("approval coverage matrix source approval schema mismatch")
    if approval_source.get("source_draft_packet_id") != draft_source.get("draft_packet_id"):
        raise CityOpsContractError("approval coverage matrix source approval/draft mismatch")
    if approval_source.get("source_review_decision_id") != decision_source.get("decision_id"):
        raise CityOpsContractError("approval coverage matrix source approval/decision mismatch")
    if approval_source.get("approved_offer_count") != 1:
        raise CityOpsContractError("approval coverage matrix source must approve exactly one offer")
    if approval_source.get("approved_offer") != APPROVED_OFFER:
        raise CityOpsContractError("approval coverage matrix source approved offer drift")
    path = approval_source.get("authorized_delivery_path", {})
    for flag in [
        "customer_delivery_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
    ]:
        if path.get(flag) is not False:
            raise CityOpsContractError(
                f"approval coverage matrix source delivery path promoted readiness: {flag}"
            )
    for source_name, source in [
        ("draft", draft_source),
        ("decision", decision_source),
        ("approval", approval_source),
    ]:
        for flag in READINESS_FALSE_FLAGS:
            if flag in source and source.get(flag) is not False:
                raise CityOpsContractError(
                    f"approval coverage matrix source {source_name} promoted readiness: {flag}"
                )
    cards = draft_source.get("draft_cards")
    if not isinstance(cards, list) or len(cards) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("approval coverage matrix source draft card count mismatch")
    for expected_offer, card in zip(REQUIRED_OFFER_ORDER, cards):
        if card.get("offer") != expected_offer:
            raise CityOpsContractError("approval coverage matrix source draft card order drift")
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
                    f"approval coverage matrix source draft card promoted readiness: {expected_offer}:{flag}"
                )


def _assert_packet_is_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SCHEMA:
        raise CityOpsContractError("offer card approval coverage matrix schema mismatch")
    if packet.get("scope") != MATRIX_SCOPE:
        raise CityOpsContractError("offer card approval coverage matrix scope drift")
    if packet.get("approval_coverage_status") != MATRIX_STATUS:
        raise CityOpsContractError("offer card approval coverage matrix status drift")
    if packet.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("offer card approval coverage matrix offer order drift")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"offer card approval coverage matrix promoted readiness: {flag}"
            )
    summary = packet.get("approval_summary", {})
    if summary.get("approved_offer_count") != 1:
        raise CityOpsContractError("offer card approval coverage matrix approved count drift")
    if summary.get("approved_offers") != [APPROVED_OFFER]:
        raise CityOpsContractError("offer card approval coverage matrix approved offer drift")
    if summary.get("unapproved_offers") != [
        offer for offer in REQUIRED_OFFER_ORDER if offer != APPROVED_OFFER
    ]:
        raise CityOpsContractError("offer card approval coverage matrix unapproved offers drift")
    for key, value in summary.items():
        if key.endswith("ready") or key == "coverage_complete":
            if value is not False:
                raise CityOpsContractError(
                    f"offer card approval coverage matrix summary promoted readiness: {key}"
                )
    safe_to_claim = list(packet.get("safe_to_claim", []))
    do_not_claim_yet = list(packet.get("do_not_claim_yet", []))
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"offer card approval coverage matrix has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"offer card approval coverage matrix claim overlap: {overlap}"
        )
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"offer card approval coverage matrix missing blocked claims: {missing_blocked}"
        )
    if packet.get("still_blocked_claims") != do_not_claim_yet:
        raise CityOpsContractError("offer card approval coverage matrix blocked claim mirror drift")
    rows = packet.get("coverage_rows")
    if not isinstance(rows, list) or len(rows) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("offer card approval coverage matrix row count mismatch")
    approved_rows = []
    for expected_offer, row in zip(REQUIRED_OFFER_ORDER, rows):
        if row.get("offer") != expected_offer:
            raise CityOpsContractError("offer card approval coverage matrix row order drift")
        approved = row.get("human_operator_text_boundary_approved") is True
        _assert_row_is_conservative(row, approved=approved)
        if approved:
            approved_rows.append(row.get("offer"))
    if approved_rows != [APPROVED_OFFER]:
        raise CityOpsContractError("offer card approval coverage matrix approved row drift")
    boundary = packet.get("authorized_delivery_path_boundary", {})
    for flag in [
        "customer_delivery_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(
                f"offer card approval coverage matrix delivery boundary promoted readiness: {flag}"
            )


def _assert_row_is_conservative(row: dict[str, Any], *, approved: bool) -> None:
    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "publication_approved",
        "catalog_route_ready",
        "controlled_pilot_authorized",
        "dispatch_ready",
        "reputation_ready",
        "exact_gps_or_raw_metadata_release_ready",
    ]:
        if row.get(flag) is not False:
            raise CityOpsContractError(
                f"offer card approval coverage matrix row promoted readiness: {row.get('offer')}:{flag}"
            )
    missing = row.get("missing_approvals_before_customer_exposure")
    if not isinstance(missing, list):
        raise CityOpsContractError("offer card approval coverage matrix row missing approvals drift")
    for required in BASE_MISSING_APPROVALS:
        if required not in missing:
            raise CityOpsContractError(
                f"offer card approval coverage matrix row missing required approval: {required}"
            )
    if approved:
        if row.get("offer") != APPROVED_OFFER:
            raise CityOpsContractError("offer card approval coverage matrix approved row offer drift")
        if row.get("approved_delivery_path") != AUTHORIZED_DELIVERY_PATH:
            raise CityOpsContractError("offer card approval coverage matrix approved path drift")
        if row.get("redaction_checks_recorded") != REQUIRED_REDACTION_CHECKS:
            raise CityOpsContractError("offer card approval coverage matrix redaction checks drift")
        if row.get("row_verdict") != "text_boundary_approved_but_customer_delivery_still_blocked":
            raise CityOpsContractError("offer card approval coverage matrix approved verdict drift")
    else:
        if row.get("approved_text_fields") != []:
            raise CityOpsContractError("offer card approval coverage matrix unapproved row fields drift")
        if row.get("approved_delivery_path") is not None:
            raise CityOpsContractError("offer card approval coverage matrix unapproved row path drift")
        if row.get("redaction_checks_recorded") != []:
            raise CityOpsContractError("offer card approval coverage matrix unapproved row redaction drift")
        for required in UNAPPROVED_OFFER_EXTRA_MISSING:
            if required not in missing:
                raise CityOpsContractError(
                    f"offer card approval coverage matrix unapproved row missing approval: {required}"
                )
        if row.get("row_verdict") != "missing_human_operator_text_boundary_approval":
            raise CityOpsContractError("offer card approval coverage matrix unapproved verdict drift")


def _find_draft_card(draft_source: dict[str, Any], offer: str) -> dict[str, Any]:
    matches = [card for card in draft_source.get("draft_cards", []) if card.get("offer") == offer]
    if len(matches) != 1:
        raise CityOpsContractError(
            f"offer card approval coverage matrix must resolve exactly one draft card: {offer}"
        )
    return matches[0]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
