"""Held customer-delivery checklist for the one approved Phase 1 offer card.

This module consumes the Phase 1 offer-card approval coverage matrix and the
single-offer text-boundary approval record. It records the next delivery-facing
control point without promoting the offer into customer delivery, publication,
catalog routing, dispatch, live Acontext/runtime parity, reputation, exact
GPS/raw metadata exposure, or worker-copyable municipal doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_customer_output_schema_review_gate import REQUIRED_OFFER_ORDER
from .phase1_offer_card_approval_coverage_matrix import (
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME,
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM,
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SCHEMA,
    load_phase1_offer_card_approval_coverage_matrix,
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

PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SCHEMA = (
    "city_ops.phase1_approved_offer_customer_delivery_hold_checklist.v1"
)
PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME = (
    "phase1_approved_offer_customer_delivery_hold_checklist.json"
)
PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SAFE_CLAIM = (
    "phase1_approved_offer_customer_delivery_hold_checklist_landed"
)

CHECKLIST_ID = (
    "city_counter_ops.phase1_approved_offer_customer_delivery_hold_checklist."
    "counter_reality_check.2026_05_12"
)
CHECKLIST_SCOPE = (
    "internal_admin_single_approved_offer_customer_delivery_hold_checklist_only"
)
CHECKLIST_STATUS = "text_boundary_approved_customer_delivery_hold_required"
CUSTOMER_DELIVERY_VERDICT = "hold_not_ready_not_authorized"

REQUIRED_BLOCKED_CLAIMS = [
    "customer_delivery_hold_required",
    "customer_delivery_approval_missing",
    "operator_publish_approval_missing",
    "publication_approval_missing",
    "authorized_customer_delivery_path_missing",
    "two_phase1_offer_cards_missing_human_operator_text_boundary_approval",
    "phase1_approval_coverage_incomplete",
    "customer_delivery_approval",
    "operator_publish_approval",
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

REQUIRED_DELIVERY_PREREQUISITES = [
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approval",
    "authorized_customer_delivery_path",
    "named_customer_scope_confirmation",
    "redactions_reverified_after_text_freeze",
    "limitations_and_non_guarantees_present",
    "no_exact_gps_or_raw_metadata",
    "no_legal_or_regulator_acceptance_claim",
    "no_dispatch_or_reputation_receipt_attachment",
]


def build_phase1_approved_offer_customer_delivery_hold_checklist(
    *,
    fixture_dir: str | Path | None = None,
    coverage_matrix: dict[str, Any] | None = None,
    approval_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the held delivery checklist for the one text-boundary-approved card."""

    matrix_source = coverage_matrix or load_phase1_offer_card_approval_coverage_matrix(
        fixture_dir=fixture_dir
    )
    approval_source = approval_record or load_phase1_offer_card_human_operator_approval_record(
        fixture_dir=fixture_dir
    )
    _assert_sources_are_conservative(matrix_source, approval_source)

    safe_to_claim = _dedupe(
        [
            *matrix_source.get("safe_to_claim", []),
            PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
            PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM,
            PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *matrix_source.get("do_not_claim_yet", []),
            *approval_source.get("do_not_claim_yet", []),
        ]
    )

    packet = {
        "schema": PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SCHEMA,
        "checklist_id": CHECKLIST_ID,
        "scope": CHECKLIST_SCOPE,
        "source_coverage_matrix_id": matrix_source["matrix_id"],
        "source_coverage_matrix_schema": matrix_source["schema"],
        "source_coverage_artifact_filename": PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME,
        "source_approval_record_id": approval_source["approval_record_id"],
        "source_approval_record_schema": approval_source["schema"],
        "source_approval_artifact_filename": PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
        "offer_order": list(REQUIRED_OFFER_ORDER),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "delivery_hold_status": CHECKLIST_STATUS,
        "customer_delivery_verdict": CUSTOMER_DELIVERY_VERDICT,
        "approved_offer": APPROVED_OFFER,
        "approved_text_boundary_snapshot": _build_text_boundary_snapshot(approval_source),
        "delivery_prerequisites": _build_delivery_prerequisites(),
        "redaction_checks_carried_forward": _build_redaction_checks_carried_forward(approval_source),
        "authorized_delivery_path_boundary": {
            "approved_record_path": AUTHORIZED_DELIVERY_PATH,
            "customer_delivery_allowed": False,
            "public_route_allowed": False,
            "catalog_route_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "exact_gps_or_raw_metadata_allowed": False,
        },
        "delivery_channel_hold": {
            "internal_admin_operator_queue_only": True,
            "customer_email_allowed": False,
            "customer_dashboard_allowed": False,
            "public_catalog_allowed": False,
            "api_route_allowed": False,
            "worker_visible_instruction_allowed": False,
        },
        "coverage_context": {
            "text_boundary_approved_offer_count": 1,
            "unapproved_offer_cards": matrix_source["approval_summary"]["unapproved_offers"],
            "coverage_complete": False,
            "customer_delivery_ready": False,
            "operator_publish_ready": False,
            "publication_ready": False,
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
            "Use this checklist as a hold record only. The approved offer has a text "
            "boundary record, but customer delivery still requires separate operator "
            "publish approval, customer-delivery approval, a named authorized path, "
            "fresh redaction verification, and no dispatch/reputation/GPS/raw-metadata "
            "promotion."
        ),
        "next_smallest_proof": (
            "Either add text-boundary approval records for the two remaining offer cards "
            "or create a separate explicit customer-delivery approval artifact for this "
            "one offer. Do not publish, route, dispatch, or attach reputation by default."
        ),
    }
    _assert_packet_is_conservative(packet)
    return packet


def write_phase1_approved_offer_customer_delivery_hold_checklist(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the held delivery checklist beside reviewed Phase 1 outputs."""

    packet = build_phase1_approved_offer_customer_delivery_hold_checklist(
        fixture_dir=fixture_dir
    )
    return _write_packet(packet, fixture_dir=fixture_dir)


def load_phase1_approved_offer_customer_delivery_hold_checklist(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted held delivery checklist."""

    path = _packet_dir(fixture_dir) / PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("delivery hold checklist must be a JSON object")
    _assert_packet_is_conservative(packet)
    return packet


def _build_text_boundary_snapshot(approval_source: dict[str, Any]) -> dict[str, Any]:
    card = approval_source["approved_offer_card"]
    snapshot = {
        "offer": card.get("offer"),
        "source_package_id": card.get("source_package_id"),
        "approved_text_fields": list(card.get("approved_text_fields", [])),
        "approved_title_text": card.get("approved_title_text"),
        "approved_positioning_text": card.get("approved_positioning_text"),
        "approved_section_names": list(card.get("approved_section_names", [])),
        "approved_limitation_text": list(card.get("approved_limitation_text", [])),
        "approval_boundary": card.get("approval_boundary"),
        "customer_delivery_ready": False,
        "publication_ready": False,
    }
    _assert_text_boundary_snapshot_is_conservative(snapshot)
    return snapshot


def _build_delivery_prerequisites() -> list[dict[str, Any]]:
    return [
        {
            "prerequisite": prerequisite,
            "satisfied": False,
            "required_before_customer_exposure": True,
            "approval_boundary": "delivery_hold_check_only_not_customer_delivery",
        }
        for prerequisite in REQUIRED_DELIVERY_PREREQUISITES
    ]


def _build_redaction_checks_carried_forward(
    approval_source: dict[str, Any]
) -> list[dict[str, Any]]:
    redactions = approval_source.get("redactions_passed", [])
    return [
        {
            "check": redaction.get("check"),
            "source_passed": redaction.get("passed"),
            "fresh_delivery_reverification_required": True,
            "customer_delivery_allowed": False,
        }
        for redaction in redactions
    ]


def _write_packet(packet: dict[str, Any], *, fixture_dir: str | Path | None = None) -> Path:
    _assert_packet_is_conservative(packet)
    base_dir = _packet_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def _packet_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_sources_are_conservative(
    matrix_source: dict[str, Any], approval_source: dict[str, Any]
) -> None:
    if matrix_source.get("schema") != PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SCHEMA:
        raise CityOpsContractError("delivery hold source coverage schema mismatch")
    if matrix_source.get("scope") != "internal_admin_phase1_offer_card_approval_coverage_matrix_only":
        raise CityOpsContractError("delivery hold source coverage scope drift")
    if matrix_source.get("approval_coverage_status") != (
        "one_offer_text_boundary_approved_two_offer_cards_unapproved_"
        "all_customer_delivery_blocked"
    ):
        raise CityOpsContractError("delivery hold source coverage status drift")
    summary = matrix_source.get("approval_summary", {})
    if summary.get("approved_offer_count") != 1 or summary.get("approved_offers") != [APPROVED_OFFER]:
        raise CityOpsContractError("delivery hold source must have one approved offer")
    if summary.get("unapproved_offers") != ["packet_submission_attempt", "posting_compliance_check"]:
        raise CityOpsContractError("delivery hold source unapproved offer drift")
    for flag in [
        "coverage_complete",
        "customer_delivery_ready",
        "operator_publish_ready",
        "publication_ready",
        "catalog_route_ready",
        "dispatch_ready",
        "reputation_ready",
        "exact_gps_or_raw_metadata_release_ready",
    ]:
        if summary.get(flag) is not False:
            raise CityOpsContractError(
                f"delivery hold source coverage promoted summary readiness: {flag}"
            )
    if approval_source.get("schema") != PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA:
        raise CityOpsContractError("delivery hold source approval schema mismatch")
    if approval_source.get("approved_offer_count") != 1 or approval_source.get("approved_offer") != APPROVED_OFFER:
        raise CityOpsContractError("delivery hold source approval offer drift")
    if approval_source.get("authorized_delivery_path", {}).get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("delivery hold source approval path drift")
    for source_name, source in [
        ("coverage", matrix_source),
        ("approval", approval_source),
    ]:
        for flag in READINESS_FALSE_FLAGS:
            if flag in source and source.get(flag) is not False:
                raise CityOpsContractError(
                    f"delivery hold source {source_name} promoted readiness: {flag}"
                )
    rows = matrix_source.get("coverage_rows")
    if not isinstance(rows, list) or len(rows) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("delivery hold source coverage row count mismatch")
    approved_rows = [row for row in rows if row.get("human_operator_text_boundary_approved")]
    if len(approved_rows) != 1 or approved_rows[0].get("offer") != APPROVED_OFFER:
        raise CityOpsContractError("delivery hold source approved row drift")
    if PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM not in matrix_source.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("delivery hold source coverage safe claim drift")
    if PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM not in approval_source.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("delivery hold source approval safe claim drift")


def _assert_packet_is_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SCHEMA:
        raise CityOpsContractError("delivery hold checklist schema mismatch")
    if packet.get("scope") != CHECKLIST_SCOPE:
        raise CityOpsContractError("delivery hold checklist scope drift")
    if packet.get("delivery_hold_status") != CHECKLIST_STATUS:
        raise CityOpsContractError("delivery hold checklist status drift")
    if packet.get("customer_delivery_verdict") != CUSTOMER_DELIVERY_VERDICT:
        raise CityOpsContractError("delivery hold checklist verdict drift")
    if packet.get("approved_offer") != APPROVED_OFFER:
        raise CityOpsContractError("delivery hold checklist approved offer drift")
    if packet.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("delivery hold checklist offer order drift")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"delivery hold checklist promoted readiness: {flag}"
            )
    safe_to_claim = list(packet.get("safe_to_claim", []))
    do_not_claim_yet = list(packet.get("do_not_claim_yet", []))
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"delivery hold checklist has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"delivery hold checklist claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"delivery hold checklist missing blocked claims: {missing_blocked}"
        )
    if packet.get("still_blocked_claims") != do_not_claim_yet:
        raise CityOpsContractError("delivery hold checklist blocked claim mirror drift")
    _assert_text_boundary_snapshot_is_conservative(
        packet.get("approved_text_boundary_snapshot", {})
    )
    prerequisites = packet.get("delivery_prerequisites")
    if not isinstance(prerequisites, list) or [p.get("prerequisite") for p in prerequisites] != REQUIRED_DELIVERY_PREREQUISITES:
        raise CityOpsContractError("delivery hold checklist prerequisite order drift")
    for prerequisite in prerequisites:
        if prerequisite.get("satisfied") is not False:
            raise CityOpsContractError("delivery hold checklist prerequisite promoted")
        if prerequisite.get("required_before_customer_exposure") is not True:
            raise CityOpsContractError("delivery hold checklist prerequisite boundary drift")
    redactions = packet.get("redaction_checks_carried_forward")
    if not isinstance(redactions, list) or [r.get("check") for r in redactions] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("delivery hold checklist redaction order drift")
    for redaction in redactions:
        if redaction.get("source_passed") is not True:
            raise CityOpsContractError("delivery hold checklist redaction source not passed")
        if redaction.get("fresh_delivery_reverification_required") is not True:
            raise CityOpsContractError("delivery hold checklist redaction reverification drift")
        if redaction.get("customer_delivery_allowed") is not False:
            raise CityOpsContractError("delivery hold checklist redaction promoted delivery")
    if packet.get("authorized_delivery_path_boundary") != {
        "approved_record_path": AUTHORIZED_DELIVERY_PATH,
        "customer_delivery_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
    }:
        raise CityOpsContractError("delivery hold checklist path boundary drift")
    channel = packet.get("delivery_channel_hold", {})
    if channel.get("internal_admin_operator_queue_only") is not True:
        raise CityOpsContractError("delivery hold checklist internal queue marker drift")
    for key in [
        "customer_email_allowed",
        "customer_dashboard_allowed",
        "public_catalog_allowed",
        "api_route_allowed",
        "worker_visible_instruction_allowed",
    ]:
        if channel.get(key) is not False:
            raise CityOpsContractError(f"delivery hold checklist channel promoted: {key}")
    context = packet.get("coverage_context", {})
    if context.get("text_boundary_approved_offer_count") != 1:
        raise CityOpsContractError("delivery hold checklist coverage context count drift")
    if context.get("unapproved_offer_cards") != [
        "packet_submission_attempt",
        "posting_compliance_check",
    ]:
        raise CityOpsContractError("delivery hold checklist coverage context unapproved drift")
    for flag in [
        "coverage_complete",
        "customer_delivery_ready",
        "operator_publish_ready",
        "publication_ready",
    ]:
        if context.get(flag) is not False:
            raise CityOpsContractError(
                f"delivery hold checklist coverage context promoted readiness: {flag}"
            )


def _assert_text_boundary_snapshot_is_conservative(snapshot: dict[str, Any]) -> None:
    if snapshot.get("offer") != APPROVED_OFFER:
        raise CityOpsContractError("delivery hold checklist text boundary offer drift")
    if snapshot.get("approval_boundary") != "text_shape_only_not_customer_copy_not_publication":
        raise CityOpsContractError("delivery hold checklist text boundary drift")
    for key in [
        "approved_title_text",
        "approved_positioning_text",
        "approved_section_names",
        "approved_limitation_text",
    ]:
        if not snapshot.get(key):
            raise CityOpsContractError(f"delivery hold checklist missing approved text: {key}")
    if snapshot.get("customer_delivery_ready") is not False:
        raise CityOpsContractError("delivery hold checklist text boundary promoted delivery")
    if snapshot.get("publication_ready") is not False:
        raise CityOpsContractError("delivery hold checklist text boundary promoted publication")
    serialized = json.dumps(snapshot, sort_keys=True).lower()
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
                f"delivery hold checklist forbidden text fragment: {fragment}"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
