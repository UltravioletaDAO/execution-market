"""Retail Reality internal/admin product-exposure boundary packet.

This module creates the smallest safe human-review artifact for exactly one AAS
candidate: Retail Reality as a Service. It intentionally stops at an
internal/admin product-exposure boundary packet. It is not publication, customer
delivery, catalog/pricing exposure, queue launch, dispatch, runtime mutation,
ERC-8004 reputation, Worker Skill DNA, payment/production readiness, exact
GPS/raw metadata release, private-context release, retail authority, or
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .retail_reality_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .retail_reality_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    REQUEST_BLOCKED_CLAIMS,
    REQUEST_FALSE_TOP_LEVEL_FLAGS,
    REQUEST_ID,
    REQUEST_READINESS_FALSE_FLAGS,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    SELECTED_TEXT_BOUNDARY_KEY,
)
from .retail_reality_pending_approval_status_card import (
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME,
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA,
    STATUS_CARD_BLOCKED_CLAIMS,
    STATUS_CARD_FALSE_FLAGS,
    STATUS_CARD_ID,
    STATUS_CARD_STATUS,
    load_retail_reality_pending_approval_status_card,
)

RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA = (
    "city_ops.retail_reality_product_exposure_boundary_packet.v1"
)
RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME = (
    "retail_reality_product_exposure_boundary_packet.json"
)
RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM = (
    "retail_reality_product_exposure_boundary_packet_landed"
)

PACKET_ID = "execution_market.aas.retail_reality.product_exposure_boundary_packet.001"
SCOPE = "internal_admin_retail_reality_product_exposure_boundary_human_review_only"
PACKET_STATUS = "prepared_for_human_review_not_submitted_not_approved_not_exposed"
PRODUCT_EXPOSURE_BOUNDARY_KEY = "retail_reality_single_candidate_product_exposure_review"
COVERED_LADDER_STEP = "single_candidate_product_exposure_boundary_packet"
NEXT_REQUIRED_LADDER_STEPS = [
    "separate_explicit_human_operator_answer_if_provided",
    "separate_human_operator_approval_or_hold_record_before_any_customer_exposure",
]

PACKET_FALSE_FLAGS = {
    "human_operator_answer_recorded": False,
    "human_operator_approval_recorded": False,
    "selected_text_boundary_approved": False,
    "product_exposure_approved": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "customer_delivery_approved": False,
    "customer_delivery_authorized": False,
    "publication_approved": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "public_or_catalog_route_ready": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "public_price_approved": False,
    "customer_quote_ready": False,
    "controlled_pilot_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_enabled": False,
    "autonomous_dispatch_ready": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "worker_copyable_doctrine_ready": False,
    "live_acontext_ready": False,
    "runtime_adapter_mutation_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_allowed": False,
    "private_context_release_allowed": False,
    "retail_authority_claims_allowed": False,
    "legal_regulator_or_authority_claims_allowed": False,
    "worker_copyable_retail_doctrine_ready": False,
}

ACCESS_FALSE_FLAGS = {
    "network_route_registered": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "worker_visible": False,
    "dispatch_enabled": False,
    "writes_customer_copy": False,
    "writes_catalog_copy": False,
    "writes_pricing_quote": False,
    "writes_dispatch_instructions": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "mutates_runtime_adapter_or_session_manager": False,
    "emits_reputation_receipts": False,
    "exposes_exact_gps_or_raw_metadata": False,
    "exposes_private_context": False,
    "publishes_worker_doctrine": False,
}

DERIVED_FALSE_FLAGS = {
    "candidate_text_values_visible": False,
    "candidate_text_rewritten": False,
    "customer_copy_created": False,
    "product_copy_created": False,
    "approval_inferred_from_status_card": False,
    "exposure_inferred_from_status_card": False,
    "delivery_path_inferred_from_status_card": False,
    "pricing_inferred_from_status_card": False,
    "queue_or_dispatch_inferred_from_status_card": False,
    "reputation_inferred_from_status_card": False,
    "runtime_parity_inferred_from_status_card": False,
    "retail_authority_inferred_from_status_card": False,
    "worker_doctrine_inferred_from_status_card": False,
}

READINESS_FALSE_FLAGS = sorted(
    set(REQUEST_READINESS_FALSE_FLAGS)
    | set(STATUS_CARD_FALSE_FLAGS)
    | set(PACKET_FALSE_FLAGS)
    | set(ACCESS_FALSE_FLAGS)
    | set(DERIVED_FALSE_FLAGS)
)

PACKET_BLOCKED_CLAIMS = [
    "retail_reality_product_exposure_human_operator_answer_recorded",
    "retail_reality_product_exposure_human_operator_approval_recorded",
    "retail_reality_product_exposure_selected_boundary_approved",
    "retail_reality_product_exposure_customer_copy_ready",
    "retail_reality_product_exposure_customer_delivery_approved",
    "retail_reality_product_exposure_publication_approved",
    "retail_reality_product_exposure_public_or_catalog_route_ready",
    "retail_reality_product_exposure_catalog_visible",
    "retail_reality_product_exposure_pricing_or_quote_ready",
    "retail_reality_product_exposure_controlled_pilot_ready",
    "retail_reality_product_exposure_operator_queue_launch_ready",
    "retail_reality_product_exposure_dispatch_ready",
    "retail_reality_product_exposure_erc8004_reputation_ready",
    "retail_reality_product_exposure_worker_skill_dna_ready",
    "retail_reality_product_exposure_live_acontext_or_runtime_ready",
    "retail_reality_product_exposure_payment_or_production_reverified",
    "retail_reality_product_exposure_exact_gps_or_raw_metadata_release_ready",
    "retail_reality_product_exposure_private_context_release_ready",
    "retail_reality_product_exposure_legal_regulator_authority_ready",
    "retail_reality_product_exposure_retail_authority_ready",
    "retail_reality_product_exposure_worker_copyable_retail_doctrine_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUEST_BLOCKED_CLAIMS) | set(STATUS_CARD_BLOCKED_CLAIMS) | set(
    PACKET_BLOCKED_CLAIMS
) | {
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "catalog_visible",
    "pricing_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "private_context_release_ready",
    "legal_or_regulator_authority_ready",
    "retail_authority_ready",
    "worker_copyable_doctrine_ready",
}

FORBIDDEN_TEXT_KEYS = {
    "candidate_text_values",
    "raw_gps",
    "raw_metadata",
    "private_context",
    "worker_copyable_doctrine",
}

FORBIDDEN_PROMOTION_FRAGMENTS = [
    "approved for customer",
    "customer delivery authorized",
    "publication authorized",
    "route ready",
    "dispatch ready",
    "reputation ready",
    "exact gps allowed",
    "raw metadata allowed",
    "legal authority granted",
    "regulator authority granted",
]


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _iter_nested_keys(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from _iter_nested_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_nested_keys(item)


def _load_status_card(artifact_dir: str | Path | None = None) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    return load_retail_reality_pending_approval_status_card(artifact_dir=source_dir)


def _assert_source_status_card(status_card: dict[str, Any]) -> None:
    if status_card.get("schema") != RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA:
        raise CityOpsContractError("Retail Reality product boundary source status card schema drift")
    if status_card.get("status_card_id") != STATUS_CARD_ID:
        raise CityOpsContractError("Retail Reality product boundary source status card id drift")
    if status_card.get("status_card_status") != STATUS_CARD_STATUS:
        raise CityOpsContractError("Retail Reality product boundary source status promoted")
    if status_card.get("source_approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("Retail Reality product boundary source request status promoted")
    if status_card.get("source_approval_request_id") != REQUEST_ID:
        raise CityOpsContractError("Retail Reality product boundary source request id drift")
    if RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM not in status_card.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality product boundary source safe claim missing")
    forbidden_safe = set(status_card.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality product boundary source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    for claim in [*REQUEST_BLOCKED_CLAIMS, *STATUS_CARD_BLOCKED_CLAIMS]:
        if claim not in status_card.get("do_not_claim_yet", []):
            raise CityOpsContractError(
                f"Retail Reality product boundary source missing blocked claim: {claim}"
            )
    if status_card.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Retail Reality product boundary source family drift")
    if status_card.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Retail Reality product boundary source offer drift")
    if status_card.get("status_queue_item_count") != 1 or len(status_card.get("status_queue_items", [])) != 1:
        raise CityOpsContractError("Retail Reality product boundary source must expose one queue item")
    queue_item = status_card["status_queue_items"][0]
    if queue_item.get("selected_text_boundary_key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("Retail Reality product boundary source boundary key drift")
    if queue_item.get("candidate_text_values_visible") is not False:
        raise CityOpsContractError("Retail Reality product boundary source candidate text visible")
    if queue_item.get("authorized_delivery_path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("Retail Reality product boundary source delivery path drift")
    if queue_item.get("authorized_delivery_path_recorded") is not False:
        raise CityOpsContractError("Retail Reality product boundary source delivery path promoted")
    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        if status_card.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality product boundary source promoted {flag}")
    for flag in STATUS_CARD_FALSE_FLAGS:
        if status_card.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality product boundary source promoted readiness {flag}"
            )
    leaked = FORBIDDEN_TEXT_KEYS & set(_iter_nested_keys(status_card))
    if leaked:
        raise CityOpsContractError(
            f"Retail Reality product boundary source leaked forbidden keys: {sorted(leaked)}"
        )


def _candidate_from_status_card(status_card: dict[str, Any]) -> dict[str, Any]:
    queue_item = status_card["status_queue_items"][0]
    return {
        "candidate_key": "retail_reality_as_a_service",
        "package_family_id": status_card["package_family_id"],
        "offer_id": status_card["offer_id"],
        "candidate_count": 1,
        "source_status_card_id": status_card["status_card_id"],
        "source_status_card_digest_sha256": _stable_digest(status_card),
        "source_approval_request_id": status_card["source_approval_request_id"],
        "source_approval_request_status": status_card["source_approval_request_status"],
        "selected_text_boundary_key": queue_item["selected_text_boundary_key"],
        "selected_text_boundary_digest_sha256": queue_item[
            "selected_text_boundary_digest_sha256"
        ],
        "candidate_text_field_names": list(queue_item["candidate_text_field_names"]),
        "candidate_text_values_visible": False,
        "candidate_text_values_hidden_reason": (
            "product_exposure_boundary_packet_is_not_customer_copy_and_uses_digest_only"
        ),
        "human_review_status": "pending_human_review_not_approved",
        "product_exposure_status": "not_exposed_internal_admin_review_only",
        "authorized_delivery_path": AUTHORIZED_DELIVERY_PATH,
        "authorized_delivery_path_recorded": False,
        "safe_human_review_question": (
            "Should this single Retail Reality boundary stay held, or should a separate "
            "human-operator approval-or-hold record be drafted later?"
        ),
    }


def _human_review_cards(candidate: dict[str, Any], blocked: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "card_id": "single_candidate_boundary",
            "candidate_key": candidate["candidate_key"],
            "package_family_id": candidate["package_family_id"],
            "offer_id": candidate["offer_id"],
            "candidate_count": 1,
            "human_review_status": candidate["human_review_status"],
            "product_exposure_status": candidate["product_exposure_status"],
            "product_exposure_approved": False,
            "customer_visible": False,
        },
        {
            "card_id": "selected_boundary_digest_only",
            "selected_text_boundary_key": candidate["selected_text_boundary_key"],
            "selected_text_boundary_digest_sha256": candidate[
                "selected_text_boundary_digest_sha256"
            ],
            "candidate_text_field_names": candidate["candidate_text_field_names"],
            "candidate_text_values_visible": False,
            "customer_copy_created": False,
        },
        {
            "card_id": "blocked_product_exposure_claims",
            "blocked_claim_count": len(blocked),
            "do_not_claim_yet": blocked,
            "customer_public_catalog_pricing_queue_dispatch_reputation_runtime_payment_authority_ready": False,
        },
        {
            "card_id": "next_separate_artifact_only",
            "allowed_next_artifacts": list(NEXT_REQUIRED_LADDER_STEPS),
            "approval_can_be_inferred_from_this_packet": False,
            "customer_exposure_can_be_inferred_from_this_packet": False,
        },
    ]


def build_retail_reality_product_exposure_boundary_packet(
    *,
    artifact_dir: str | Path | None = None,
    status_card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one internal/admin product-exposure boundary packet for human review."""

    source_status_card = status_card or _load_status_card(artifact_dir=artifact_dir)
    _assert_source_status_card(source_status_card)

    safe_to_claim = _dedupe(
        [
            *source_status_card["safe_to_claim"],
            RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_status_card["do_not_claim_yet"],
            *PACKET_BLOCKED_CLAIMS,
        ]
    )
    candidate = _candidate_from_status_card(source_status_card)

    packet = {
        "schema": RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA,
        "packet_id": PACKET_ID,
        "scope": SCOPE,
        "packet_status": PACKET_STATUS,
        "product_exposure_boundary_key": PRODUCT_EXPOSURE_BOUNDARY_KEY,
        "source_artifact": {
            "file": RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME,
            "schema": source_status_card["schema"],
            "id": source_status_card["status_card_id"],
            "safe_claim": RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
            "digest_sha256": _stable_digest(source_status_card),
        },
        "candidate_count": 1,
        "aas_candidates": [candidate],
        "ladder_boundary": {
            "covered_steps": [
                *source_status_card["ladder_boundary"]["covered_steps"],
                COVERED_LADDER_STEP,
            ],
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "access_policy": {
            "surface": "internal_admin_only",
            "audience": "human_operator_review_only",
            "requires_admin_context": True,
            "publishes_to_customer": False,
            **ACCESS_FALSE_FLAGS,
        },
        "derived_output_contract": {
            **DERIVED_FALSE_FLAGS,
            "reads_only_pending_status_card_artifact": True,
            "exactly_one_aas_candidate": True,
            "source_candidate_text_values_hidden": True,
            "source_digest_and_boundary_digest_preserved": True,
            "safe_and_blocked_claims_remain_adjacent": True,
            "no_external_submission_or_publication": True,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "human_review_cards": _human_review_cards(candidate, do_not_claim_yet),
        "human_review_instruction": (
            "Use this packet only as an internal/admin human-review boundary for one Retail "
            "Reality candidate. It does not record a human-operator answer, does not approve the "
            "boundary, and does not expose customer, public, catalog, pricing, queue, "
            "dispatch, reputation, runtime, payment, location, authority, or worker doctrine paths."
        ),
        "not_next_actions": [
            "Do not infer a human answer or approval from this packet.",
            "Do not publish customer copy, customer delivery, catalog pages, pricing, queue launch, dispatch instructions, reputation receipts, runtime adapter/session-manager changes, payment/production readiness, GPS/raw metadata, private context, authority claims, or worker-copyable doctrine.",
            "Do not use this packet for any stopped-project integration.",
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        **PACKET_FALSE_FLAGS,
        "still_blocked_claims": do_not_claim_yet,
        "packet_verdict": "single_retail_reality_product_exposure_boundary_ready_for_internal_human_review_only",
    }
    _assert_packet(packet, source_status_card=source_status_card)
    return packet


def _assert_packet(packet: dict[str, Any], *, source_status_card: dict[str, Any]) -> None:
    _assert_source_status_card(source_status_card)
    if packet.get("schema") != RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA:
        raise CityOpsContractError("Retail Reality product boundary packet schema drift")
    if packet.get("packet_id") != PACKET_ID:
        raise CityOpsContractError("Retail Reality product boundary packet id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("Retail Reality product boundary packet scope drift")
    if packet.get("packet_status") != PACKET_STATUS:
        raise CityOpsContractError("Retail Reality product boundary packet status drift")
    if packet.get("product_exposure_boundary_key") != PRODUCT_EXPOSURE_BOUNDARY_KEY:
        raise CityOpsContractError("Retail Reality product boundary key drift")

    if packet.get("candidate_count") != 1 or len(packet.get("aas_candidates", [])) != 1:
        raise CityOpsContractError("Retail Reality product boundary packet must contain exactly one candidate")
    candidate = packet["aas_candidates"][0]
    expected_candidate = _candidate_from_status_card(source_status_card)
    if candidate != expected_candidate:
        raise CityOpsContractError("Retail Reality product boundary candidate drift")
    if candidate.get("candidate_text_values_visible") is not False:
        raise CityOpsContractError("Retail Reality product boundary candidate text visible")
    if candidate.get("authorized_delivery_path_recorded") is not False:
        raise CityOpsContractError("Retail Reality product boundary delivery path promoted")

    source = packet.get("source_artifact", {})
    if source.get("file") != RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME:
        raise CityOpsContractError("Retail Reality product boundary source file drift")
    if source.get("schema") != RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA:
        raise CityOpsContractError("Retail Reality product boundary source schema drift")
    if source.get("id") != STATUS_CARD_ID:
        raise CityOpsContractError("Retail Reality product boundary source id drift")
    if source.get("digest_sha256") != _stable_digest(source_status_card):
        raise CityOpsContractError("Retail Reality product boundary source digest drift")

    ladder = packet.get("ladder_boundary", {})
    if ladder.get("covered_steps", [])[-1:] != [COVERED_LADDER_STEP]:
        raise CityOpsContractError("Retail Reality product boundary ladder step drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality product boundary next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality product boundary ladder promoted")

    safe_to_claim = packet.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = packet.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("Retail Reality product boundary safe claim missing")
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality product boundary forbidden safe claims: {sorted(forbidden_safe)}"
        )
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"Retail Reality product boundary claim overlap: {sorted(overlap)}"
        )
    missing_blocked = (
        set(source_status_card.get("do_not_claim_yet", [])) | set(PACKET_BLOCKED_CLAIMS)
    ) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality product boundary missing blocked claims: {sorted(missing_blocked)}"
        )
    if packet.get("still_blocked_claims") != do_not_claim_yet:
        raise CityOpsContractError("Retail Reality product boundary blocked claims drift")

    access = packet.get("access_policy", {})
    if access.get("surface") != "internal_admin_only":
        raise CityOpsContractError("Retail Reality product boundary access surface drift")
    if access.get("audience") != "human_operator_review_only":
        raise CityOpsContractError("Retail Reality product boundary audience drift")
    if access.get("publishes_to_customer") is not False:
        raise CityOpsContractError("Retail Reality product boundary publishes to customer")
    for flag, expected in ACCESS_FALSE_FLAGS.items():
        if access.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality product boundary access promoted {flag}")

    derived = packet.get("derived_output_contract", {})
    for flag, expected in DERIVED_FALSE_FLAGS.items():
        if derived.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality product boundary derived promoted {flag}")
    for flag in [
        "reads_only_pending_status_card_artifact",
        "exactly_one_aas_candidate",
        "source_candidate_text_values_hidden",
        "source_digest_and_boundary_digest_preserved",
        "safe_and_blocked_claims_remain_adjacent",
        "no_external_submission_or_publication",
    ]:
        if derived.get(flag) is not True:
            raise CityOpsContractError(f"Retail Reality product boundary derived missing {flag}")

    cards = packet.get("human_review_cards", [])
    if [card.get("card_id") for card in cards] != [
        "single_candidate_boundary",
        "selected_boundary_digest_only",
        "blocked_product_exposure_claims",
        "next_separate_artifact_only",
    ]:
        raise CityOpsContractError("Retail Reality product boundary card drift")
    for card in cards:
        if FORBIDDEN_TEXT_KEYS & set(_iter_nested_keys(card)):
            raise CityOpsContractError("Retail Reality product boundary card leaked forbidden text")
        for promoted_flag in [
            "product_exposure_approved",
            "customer_visible",
            "customer_copy_created",
            "customer_public_catalog_pricing_queue_dispatch_reputation_runtime_payment_authority_ready",
            "approval_can_be_inferred_from_this_packet",
            "customer_exposure_can_be_inferred_from_this_packet",
        ]:
            if card.get(promoted_flag) is not None and card.get(promoted_flag) is not False:
                raise CityOpsContractError(
                    f"Retail Reality product boundary card promoted {promoted_flag}"
                )

    for flag, expected in PACKET_FALSE_FLAGS.items():
        if packet.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality product boundary promoted {flag}")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality product boundary promoted readiness {flag}"
            )

    leaked = FORBIDDEN_TEXT_KEYS & set(_iter_nested_keys(packet))
    if leaked:
        raise CityOpsContractError(
            f"Retail Reality product boundary leaked forbidden keys: {sorted(leaked)}"
        )
    _assert_no_promotion_language(packet)


def _assert_no_promotion_language(packet: dict[str, Any]) -> None:
    serialized = json.dumps(packet, sort_keys=True).lower()
    for fragment in FORBIDDEN_PROMOTION_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(
                f"Retail Reality product boundary forbidden promotion fragment: {fragment}"
            )


def write_retail_reality_product_exposure_boundary_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_retail_reality_product_exposure_boundary_packet(artifact_dir=target_dir)
    path = target_dir / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_retail_reality_product_exposure_boundary_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("Retail Reality product boundary packet must be JSON object")
    status_card = _load_status_card(source_dir)
    _assert_packet(packet, source_status_card=status_card)
    return packet
