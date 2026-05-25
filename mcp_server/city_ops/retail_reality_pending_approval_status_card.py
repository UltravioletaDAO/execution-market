"""Retail Reality pending-approval internal/admin status card.

This module advances the Retail Reality AAS approval-boundary ladder by one
safe, read-only rung after the pending human-operator approval request. It
creates an internal/admin queue/status-card artifact that lets operators see
there is a pending request without turning the request into approval, customer
copy, publication, public/catalog routing, pricing, dispatch, reputation, live
runtime parity, exact-location/raw-metadata release, retail authority, or
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
    REQUIRED_PRE_APPROVAL_CHECKS,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
    SELECTED_TEXT_BOUNDARY_KEY,
    load_retail_reality_human_operator_approval_request,
)

RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA = (
    "city_ops.retail_reality_pending_approval_status_card.v1"
)
RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME = (
    "retail_reality_pending_approval_status_card.json"
)
RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM = (
    "retail_reality_pending_approval_status_card_landed"
)

STATUS_CARD_ID = "execution_market.aas.retail_reality.pending_approval_status_card.001"
SCOPE = "internal_admin_retail_reality_pending_approval_status_card_only"
STATUS_CARD_STATUS = "read_only_pending_approval_status_card_not_approval_not_customer_ready"

COVERED_LADDER_STEP = "pending_approval_status_card"
NEXT_REQUIRED_LADDER_STEPS = [
    "separate_human_operator_approval_record_if_authorized",
    "or_leave_request_pending_and_hold_customer_exposure",
]

STATUS_CARD_ACCESS_FALSE_FLAGS = {
    "network_route_registered": False,
    "public_route_registered": False,
    "customer_visible": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "worker_visible": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "writes_customer_copy": False,
    "writes_catalog_copy": False,
    "writes_dispatch_instructions": False,
    "emits_reputation_receipts": False,
    "exposes_exact_gps_or_raw_metadata": False,
    "exposes_private_context": False,
    "private_context_release_allowed": False,
    "publishes_worker_doctrine": False,
    "records_human_operator_approval": False,
    "records_customer_delivery_approval": False,
    "records_publication_approval": False,
}

STATUS_CARD_DERIVED_FALSE_FLAGS = {
    "candidate_text_values_visible": False,
    "candidate_text_rewritten": False,
    "customer_copy_created": False,
    "approval_inferred_from_request": False,
    "delivery_path_inferred_from_request": False,
    "publication_path_inferred_from_request": False,
    "routing_inferred_from_request": False,
    "pricing_inferred_from_request": False,
    "dispatch_inferred_from_request": False,
    "reputation_inferred_from_request": False,
    "runtime_parity_inferred_from_request": False,
    "retail_authority_inferred_from_request": False,
    "worker_doctrine_inferred_from_request": False,
}

STATUS_CARD_FALSE_FLAGS = sorted(
    set(REQUEST_READINESS_FALSE_FLAGS)
    | set(REQUEST_FALSE_TOP_LEVEL_FLAGS)
    | set(STATUS_CARD_ACCESS_FALSE_FLAGS)
    | set(STATUS_CARD_DERIVED_FALSE_FLAGS)
)

STATUS_CARD_BLOCKED_CLAIMS = [
    "retail_reality_pending_status_card_human_operator_approval_recorded",
    "retail_reality_pending_status_card_selected_boundary_approved",
    "retail_reality_pending_status_card_customer_copy_ready",
    "retail_reality_pending_status_card_customer_delivery_ready",
    "retail_reality_pending_status_card_publication_ready",
    "retail_reality_pending_status_card_public_route_ready",
    "retail_reality_pending_status_card_catalog_route_ready",
    "retail_reality_pending_status_card_controlled_pilot_ready",
    "retail_reality_pending_status_card_pricing_or_quote_ready",
    "retail_reality_pending_status_card_operator_queue_launch_ready",
    "retail_reality_pending_status_card_dispatch_ready",
    "retail_reality_pending_status_card_reputation_ready",
    "retail_reality_pending_status_card_live_runtime_ready",
    "retail_reality_pending_status_card_exact_gps_or_raw_metadata_release_ready",
    "retail_reality_pending_status_card_private_context_release_ready",
    "retail_reality_pending_status_card_retail_authority_ready",
    "retail_reality_pending_status_card_worker_copyable_retail_doctrine_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUEST_BLOCKED_CLAIMS) | set(STATUS_CARD_BLOCKED_CLAIMS) | {
    "human_operator_approval_recorded",
    "selected_text_boundary_approved",
    "customer_copy_ready",
    "customer_delivery_ready",
    "publication_ready",
    "public_route_ready",
    "catalog_ready",
    "controlled_pilot_ready",
    "pricing_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "private_retail_context_release_ready",
    "retail_authority_ready",
    "worker_copyable_retail_doctrine",
}

FORBIDDEN_STATUS_FRAGMENTS = [
    "approved for customer",
    "customer delivery authorized",
    "publication authorized",
    "route ready",
    "dispatch ready",
    "reputation ready",
    "exact gps allowed",
    "raw metadata allowed",
]


def _canonical_digest(payload: Any) -> str:
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


def _load_source_request(artifact_dir: str | Path | None = None) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else None
    if source_dir is not None and (
        source_dir / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    ).exists():
        return load_retail_reality_human_operator_approval_request(artifact_dir=source_dir)
    return load_retail_reality_human_operator_approval_request()


def _assert_source_request(request: dict[str, Any]) -> None:
    if request.get("schema") != RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("Retail Reality pending status card source request schema drift")
    if request.get("request_id") != REQUEST_ID:
        raise CityOpsContractError("Retail Reality pending status card source request id drift")
    if request.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("Retail Reality pending status card source request status promoted")
    if request.get("scope") != "internal_admin_retail_reality_human_operator_approval_request_only":
        raise CityOpsContractError("Retail Reality pending status card source request scope drift")
    if RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in request.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality pending status card source safe claim missing")
    forbidden_safe = set(request.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality pending status card source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    for claim in REQUEST_BLOCKED_CLAIMS:
        if claim not in request.get("do_not_claim_yet", []):
            raise CityOpsContractError(
                f"Retail Reality pending status card source missing blocked claim: {claim}"
            )
    for flag in REQUEST_FALSE_TOP_LEVEL_FLAGS:
        if request.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality pending status card source promoted {flag}")
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if request.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality pending status card source promoted readiness {flag}"
            )
    boundary = request.get("selected_text_boundary", {})
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("Retail Reality pending status card source boundary key drift")
    if boundary.get("selected_text_boundary_approved") is not False:
        raise CityOpsContractError("Retail Reality pending status card source boundary promoted")
    if boundary.get("candidate_text_digest_sha256") is None:
        raise CityOpsContractError("Retail Reality pending status card source boundary digest missing")
    for flag in [
        "human_operator_approval_recorded",
        "customer_delivery_authorized_by_boundary",
        "publication_authorized_by_boundary",
        "dispatch_authorized_by_boundary",
        "reputation_authorized_by_boundary",
        "exact_gps_or_raw_metadata_authorized_by_boundary",
        "private_context_release_authorized_by_boundary",
        "retail_authority_claims_authorized_by_boundary",
        "worker_doctrine_authorized_by_boundary",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality pending status card source boundary promoted {flag}"
            )
    path = request.get("authorized_delivery_path", {})
    if path.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("Retail Reality pending status card source delivery path drift")
    for flag in [
        "path_recorded",
        "customer_delivery_allowed",
        "publication_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "controlled_pilot_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
        "private_retail_context_release_allowed",
        "retail_authority_claims_allowed",
        "worker_doctrine_allowed",
    ]:
        if path.get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality pending status card source delivery path promoted {flag}"
            )


def _status_queue_item(source_request: dict[str, Any]) -> dict[str, Any]:
    boundary = source_request["selected_text_boundary"]
    return {
        "queue_item_id": "retail_reality.pending_human_operator_review.001",
        "request_id": source_request["request_id"],
        "approval_request_status": source_request["approval_request_status"],
        "status_label": "pending_human_review_not_approved",
        "source_request_digest_sha256": _canonical_digest(source_request),
        "selected_text_boundary_key": boundary["key"],
        "selected_text_boundary_digest_sha256": boundary["candidate_text_digest_sha256"],
        "candidate_text_field_names": list(boundary["candidate_text_fields"]),
        "candidate_text_values_visible": False,
        "candidate_text_values_hidden_reason": (
            "status_card_is_not_customer_copy_and_displays_digest_plus_field_names_only"
        ),
        "pre_approval_check_count": len(source_request["pre_approval_checks"]),
        "pre_approval_checks_passed_here": 0,
        "redaction_and_authority_requirement_count": len(
            source_request["redaction_and_authority_requirements"]
        ),
        "redaction_and_authority_requirements_passed_here": 0,
        "authorized_delivery_path": AUTHORIZED_DELIVERY_PATH,
        "authorized_delivery_path_recorded": False,
        "next_operator_action": "review_exact_boundary_or_leave_hold_without_customer_exposure",
    }


def _display_cards(source_request: dict[str, Any]) -> list[dict[str, Any]]:
    queue_item = _status_queue_item(source_request)
    return [
        {
            "card_id": "pending_status",
            "title": "Retail Reality pending human review",
            "status": queue_item["status_label"],
            "source_request_id": source_request["request_id"],
            "source_request_digest_sha256": queue_item["source_request_digest_sha256"],
            "approval_recorded": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
        },
        {
            "card_id": "selected_boundary_digest",
            "title": "Selected text boundary digest",
            "boundary_key": queue_item["selected_text_boundary_key"],
            "boundary_digest_sha256": queue_item["selected_text_boundary_digest_sha256"],
            "candidate_text_field_names": queue_item["candidate_text_field_names"],
            "candidate_text_values_visible": False,
            "customer_copy_created": False,
        },
        {
            "card_id": "review_requirements",
            "title": "Checks still required before any separate approval record",
            "pre_approval_check_count": queue_item["pre_approval_check_count"],
            "pre_approval_checks_passed_here": 0,
            "redaction_and_authority_requirement_count": queue_item[
                "redaction_and_authority_requirement_count"
            ],
            "redaction_and_authority_requirements_passed_here": 0,
            "required_check_names": list(REQUIRED_PRE_APPROVAL_CHECKS),
            "required_redaction_and_authority_names": list(REDACTION_AND_AUTHORITY_REQUIREMENTS),
        },
        {
            "card_id": "blocked_claims",
            "title": "Claims still blocked",
            "safe_to_claim": list(source_request["safe_to_claim"]),
            "do_not_claim_yet": list(source_request["do_not_claim_yet"]),
            "human_approval_record_ready": False,
            "customer_public_dispatch_reputation_runtime_or_retail_authority_ready": False,
        },
    ]


def build_retail_reality_pending_approval_status_card(
    *,
    artifact_dir: str | Path | None = None,
    source_approval_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only internal/admin status card for pending Retail Reality approval."""

    source_request = source_approval_request or _load_source_request(artifact_dir=artifact_dir)
    _assert_source_request(source_request)

    safe_to_claim = _dedupe(
        [
            *source_request.get("safe_to_claim", []),
            RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_request.get("do_not_claim_yet", []),
            *STATUS_CARD_BLOCKED_CLAIMS,
        ]
    )
    queue_item = _status_queue_item(source_request)

    card: dict[str, Any] = {
        "schema": RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA,
        "status_card_id": STATUS_CARD_ID,
        "scope": SCOPE,
        "status_card_status": STATUS_CARD_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_approval_request_file": RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
        "source_approval_request_schema": source_request["schema"],
        "source_approval_request_id": source_request["request_id"],
        "source_approval_request_status": source_request["approval_request_status"],
        "source_approval_request_digest_sha256": queue_item["source_request_digest_sha256"],
        "source_safe_claims_inherited": [
            RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
        ],
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": [
                *source_request["ladder_boundary"]["covered_steps"],
                COVERED_LADDER_STEP,
            ],
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "access_policy": {
            "surface": "internal_admin_only",
            "route_registered": False,
            "public_route_registered": False,
            "customer_visible": False,
            "catalog_visible": False,
            "pass_through_digest_only_status": True,
            **STATUS_CARD_ACCESS_FALSE_FLAGS,
        },
        "status_queue_item_count": 1,
        "status_queue_items": [queue_item],
        "display_cards": _display_cards(source_request),
        "derived_output_contract": {
            **STATUS_CARD_DERIVED_FALSE_FLAGS,
            "reads_only_pending_approval_request_artifact": True,
            "source_candidate_text_values_hidden": True,
            "source_digest_and_boundary_digest_preserved": True,
            "safe_and_blocked_claims_remain_adjacent": True,
        },
        **REQUEST_FALSE_TOP_LEVEL_FLAGS,
        "readiness": {flag: False for flag in STATUS_CARD_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this internal/admin card only to see that a Retail Reality approval request "
            "is pending human review. It hides candidate text values and shows digests, "
            "field names, remaining checks, safe claims, and blocked claims. It does not "
            "record approval, create customer copy, authorize delivery, publish, launch a "
            "route/catalog/pilot/queue, dispatch workers, attach reputation, prove runtime "
            "parity, expose exact location/raw metadata, assert retail authority, or publish "
            "worker doctrine."
        ),
        "next_smallest_proof": (
            "Keep this as an internal queue/status card unless a separate human-operator "
            "approval record is explicitly authorized for the exact source boundary."
        ),
    }
    _assert_status_card(card, source_request=source_request)
    return card


def _assert_status_card(card: dict[str, Any], *, source_request: dict[str, Any]) -> None:
    _assert_source_request(source_request)
    if card.get("schema") != RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA:
        raise CityOpsContractError("Retail Reality pending status card schema drift")
    if card.get("status_card_id") != STATUS_CARD_ID:
        raise CityOpsContractError("Retail Reality pending status card id drift")
    if card.get("scope") != SCOPE:
        raise CityOpsContractError("Retail Reality pending status card scope drift")
    if card.get("status_card_status") != STATUS_CARD_STATUS:
        raise CityOpsContractError("Retail Reality pending status card status drift")
    if card.get("source_approval_request_file") != RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME:
        raise CityOpsContractError("Retail Reality pending status card source file drift")
    if card.get("source_approval_request_schema") != RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("Retail Reality pending status card source schema drift")
    if card.get("source_approval_request_id") != REQUEST_ID:
        raise CityOpsContractError("Retail Reality pending status card source id drift")
    if card.get("source_approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("Retail Reality pending status card source status promoted")
    if card.get("source_approval_request_digest_sha256") != _canonical_digest(source_request):
        raise CityOpsContractError("Retail Reality pending status card source digest drift")
    if RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM not in card.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality pending status card safe claim missing")
    if RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in card.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality pending status card inherited safe claim missing")
    forbidden_safe = set(card.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality pending status card has forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = (set(source_request.get("do_not_claim_yet", [])) | set(STATUS_CARD_BLOCKED_CLAIMS)) - set(
        card.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality pending status card missing blocked claims: {sorted(missing_blocked)}"
        )
    if card.get("still_blocked_claims") != card.get("do_not_claim_yet"):
        raise CityOpsContractError("Retail Reality pending status card blocked claims drift")

    ladder = card.get("ladder_boundary", {})
    if ladder.get("covered_steps", [])[-1:] != [COVERED_LADDER_STEP]:
        raise CityOpsContractError("Retail Reality pending status card ladder step drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality pending status card next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality pending status card promoted ladder")

    access = card.get("access_policy", {})
    if access.get("surface") != "internal_admin_only":
        raise CityOpsContractError("Retail Reality pending status card access surface drift")
    if access.get("pass_through_digest_only_status") is not True:
        raise CityOpsContractError("Retail Reality pending status card pass-through marker missing")
    for flag, expected in STATUS_CARD_ACCESS_FALSE_FLAGS.items():
        if access.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality pending status card access promoted {flag}")

    if card.get("status_queue_item_count") != 1 or len(card.get("status_queue_items", [])) != 1:
        raise CityOpsContractError("Retail Reality pending status card must expose exactly one queue item")
    queue_item = card["status_queue_items"][0]
    boundary = source_request["selected_text_boundary"]
    if queue_item.get("request_id") != source_request.get("request_id"):
        raise CityOpsContractError("Retail Reality pending status card queue source id drift")
    if queue_item.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("Retail Reality pending status card queue status promoted")
    if queue_item.get("source_request_digest_sha256") != _canonical_digest(source_request):
        raise CityOpsContractError("Retail Reality pending status card queue source digest drift")
    if queue_item.get("selected_text_boundary_key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("Retail Reality pending status card queue boundary key drift")
    if queue_item.get("selected_text_boundary_digest_sha256") != boundary.get(
        "candidate_text_digest_sha256"
    ):
        raise CityOpsContractError("Retail Reality pending status card queue boundary digest drift")
    if queue_item.get("candidate_text_field_names") != boundary.get("candidate_text_fields"):
        raise CityOpsContractError("Retail Reality pending status card queue field names drift")
    if "candidate_text_values" in queue_item:
        raise CityOpsContractError("Retail Reality pending status card candidate text leaked")
    for flag in [
        "candidate_text_values_visible",
        "authorized_delivery_path_recorded",
    ]:
        if queue_item.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality pending status card queue promoted {flag}")
    if queue_item.get("pre_approval_check_count") != len(REQUIRED_PRE_APPROVAL_CHECKS):
        raise CityOpsContractError("Retail Reality pending status card pre-check count drift")
    if queue_item.get("redaction_and_authority_requirement_count") != len(
        REDACTION_AND_AUTHORITY_REQUIREMENTS
    ):
        raise CityOpsContractError("Retail Reality pending status card redaction count drift")

    display_cards = card.get("display_cards", [])
    if [item.get("card_id") for item in display_cards] != [
        "pending_status",
        "selected_boundary_digest",
        "review_requirements",
        "blocked_claims",
    ]:
        raise CityOpsContractError("Retail Reality pending status card display card drift")
    for item in display_cards:
        if "candidate_text_values" in item:
            raise CityOpsContractError("Retail Reality pending status card display candidate text leaked")
        for promoted_flag in [
            "approval_recorded",
            "customer_delivery_allowed",
            "publication_allowed",
            "customer_copy_created",
            "human_approval_record_ready",
            "customer_public_dispatch_reputation_runtime_or_retail_authority_ready",
        ]:
            if item.get(promoted_flag) is not None and item.get(promoted_flag) is not False:
                raise CityOpsContractError(
                    f"Retail Reality pending status card display promoted {promoted_flag}"
                )

    derived = card.get("derived_output_contract", {})
    if derived.get("reads_only_pending_approval_request_artifact") is not True:
        raise CityOpsContractError("Retail Reality pending status card source contract drift")
    if derived.get("source_candidate_text_values_hidden") is not True:
        raise CityOpsContractError("Retail Reality pending status card source text visibility drift")
    if derived.get("source_digest_and_boundary_digest_preserved") is not True:
        raise CityOpsContractError("Retail Reality pending status card digest contract drift")
    for flag, expected in STATUS_CARD_DERIVED_FALSE_FLAGS.items():
        if derived.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality pending status card derived promoted {flag}")

    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        if card.get(flag) is not expected:
            raise CityOpsContractError(f"Retail Reality pending status card promoted {flag}")
    for flag in STATUS_CARD_FALSE_FLAGS:
        if card.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality pending status card promoted readiness {flag}")
    _assert_no_status_promotion_language(card)


def _assert_no_status_promotion_language(card: dict[str, Any]) -> None:
    serialized = json.dumps(card, sort_keys=True).lower()
    for fragment in FORBIDDEN_STATUS_FRAGMENTS:
        if fragment in serialized:
            raise CityOpsContractError(
                f"Retail Reality pending status card forbidden promotion fragment: {fragment}"
            )


def write_retail_reality_pending_approval_status_card(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    card = build_retail_reality_pending_approval_status_card()
    path = target_dir / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME
    path.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_retail_reality_pending_approval_status_card(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        card = json.load(fh)
    if not isinstance(card, dict):
        raise CityOpsContractError("Retail Reality pending status card must be JSON object")
    request = _load_source_request(source_dir)
    _assert_status_card(card, source_request=request)
    return card
