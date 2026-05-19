"""Document / Handoff approval-request read surface.

This module consumes the pending Document / Handoff human-operator approval
request and creates a read-only internal/admin surface for a future operator to
review. It is intentionally not a human approval record, not customer copy, not
delivery, not publication, not pricing, not queue launch, not dispatch, not
reputation, not live Acontext/runtime parity, not exact GPS/raw metadata
exposure, not legal/notarial/private-identity/acceptance/filing/custody
authority, and not worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .document_handoff_fixture_review_gate import ARTIFACT_DIR, OFFER_ID, PACKAGE_FAMILY_ID
from .document_handoff_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUEST_BLOCKED_CLAIMS as SOURCE_REQUEST_REQUIRED_BLOCKED_CLAIMS,
    REQUEST_FALSE_TOP_LEVEL_FLAGS,
    REQUEST_ID,
    REQUEST_READINESS_FALSE_FLAGS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    SELECTED_TEXT_BOUNDARY_KEY,
    load_document_handoff_human_operator_approval_request,
)

DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SCHEMA = (
    "city_ops.document_handoff_approval_request_read_surface.v1"
)
DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME = (
    "document_handoff_approval_request_read_surface.json"
)
DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM = (
    "document_handoff_approval_request_read_surface_landed"
)

SURFACE_ID = "execution_market.aas.document_handoff.approval_request_read_surface.001"
SCOPE = "internal_admin_document_handoff_approval_request_read_surface_only"
SURFACE_STATUS = "read_only_pending_request_surface_no_human_approval_recorded"
MOUNT_STATUS = "internal_admin_mount_contract_only_no_network_route_registered"

SURFACE_FALSE_FLAGS = {
    "surface_is_human_approval_record": False,
    "surface_satisfies_pre_approval_checks": False,
    "surface_satisfies_redaction_or_authority_checks": False,
    "surface_authorizes_delivery_path": False,
    "surface_authorizes_customer_delivery": False,
    "surface_authorizes_publication": False,
    "surface_authorizes_public_route": False,
    "surface_authorizes_catalog_route": False,
    "surface_authorizes_controlled_pilot": False,
    "surface_authorizes_public_price_or_customer_quote": False,
    "surface_authorizes_queue_launch": False,
    "surface_authorizes_dispatch": False,
    "surface_authorizes_reputation": False,
    "surface_authorizes_live_runtime": False,
    "surface_authorizes_exact_gps_or_raw_metadata_exposure": False,
    "surface_authorizes_legal_notarial_identity_acceptance_filing_or_custody_claims": False,
    "surface_authorizes_worker_skill_dna_or_copyable_doctrine": False,
}

SURFACE_BLOCKED_CLAIMS = [
    *SOURCE_REQUEST_REQUIRED_BLOCKED_CLAIMS,
    "document_handoff_approval_request_read_surface_is_human_approval",
    "document_handoff_approval_request_read_surface_satisfies_pre_approval_checks",
    "document_handoff_approval_request_read_surface_satisfies_redactions",
    "document_handoff_approval_request_read_surface_authorizes_delivery_path",
    "document_handoff_approval_request_read_surface_authorizes_customer_delivery",
    "document_handoff_approval_request_read_surface_authorizes_publication",
    "document_handoff_approval_request_read_surface_authorizes_public_route_or_catalog",
    "document_handoff_approval_request_read_surface_authorizes_controlled_pilot_or_sku",
    "document_handoff_approval_request_read_surface_authorizes_public_price_or_quote",
    "document_handoff_approval_request_read_surface_authorizes_queue_or_dispatch",
    "document_handoff_approval_request_read_surface_authorizes_reputation_or_runtime",
    "document_handoff_approval_request_read_surface_authorizes_exact_gps_or_raw_metadata",
    "document_handoff_approval_request_read_surface_authorizes_legal_notarial_identity_acceptance_filing_custody_claims",
    "document_handoff_approval_request_read_surface_authorizes_worker_skill_dna_or_copyable_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(SURFACE_BLOCKED_CLAIMS) | {
    "human_operator_approval_recorded",
    "human_approved",
    "operator_approved",
    "selected_text_boundary_approved",
    "pre_approval_checks_passed",
    "redaction_requirements_passed",
    "authority_requirements_passed",
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "authorized_delivery_path_ready",
    "authorized_delivery_path_approved",
    "publishable",
    "publication_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "public_price_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "legal_service_ready",
    "notarial_act_ready",
    "private_identity_ready",
    "guaranteed_acceptance_ready",
    "filing_success_ready",
    "custody_guarantee_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
}

REVIEW_QUEUE_ITEMS = [
    "read_exact_selected_text_boundary",
    "verify_source_request_digest_before_review",
    "verify_pre_approval_checks_with_external_evidence_later",
    "verify_redactions_and_authority_limits_later",
    "record_separate_human_operator_approval_artifact_if_and_only_if_approved",
    "keep_customer_delivery_publication_queue_dispatch_reputation_runtime_and_worker_doctrine_blocked",
]


def _canonical_digest(payload: dict[str, Any]) -> str:
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


def _load_source_request(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_document_handoff_human_operator_approval_request(artifact_dir=artifact_dir)


def _assert_source_request_is_conservative(request: dict[str, Any]) -> None:
    if request.get("schema") != DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("document handoff approval request read surface source schema drift")
    if request.get("request_id") != REQUEST_ID:
        raise CityOpsContractError("document handoff approval request read surface source id drift")
    if request.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("document handoff approval request read surface source family drift")
    if request.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("document handoff approval request read surface source offer drift")
    if request.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("document handoff approval request read surface source status drift")
    if DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in request.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff approval request read surface source safe claim missing")
    forbidden_safe = set(request.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"document handoff approval request read surface source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SOURCE_REQUEST_REQUIRED_BLOCKED_CLAIMS) - set(
        request.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"document handoff approval request read surface source missing blocked claims: {sorted(missing_blocked)}"
        )
    if request.get("selected_text_boundary_count") != 1:
        raise CityOpsContractError("document handoff approval request read surface source boundary count drift")
    boundary = request.get("selected_text_boundary", {})
    if boundary.get("key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("document handoff approval request read surface source boundary key drift")
    if boundary.get("candidate_text_boundary") != "internal_package_label_only":
        raise CityOpsContractError("document handoff approval request read surface source boundary type drift")
    for flag in [
        "selected_text_boundary_approved",
        "human_operator_approval_recorded",
        "customer_delivery_authorized_by_boundary",
        "publication_authorized_by_boundary",
        "source_customer_copy_approved",
        "source_next_gate_satisfied",
    ]:
        if boundary.get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface source boundary promoted {flag}"
            )
    for flag, expected in REQUEST_FALSE_TOP_LEVEL_FLAGS.items():
        if request.get(flag) is not expected:
            raise CityOpsContractError(
                f"document handoff approval request read surface source promoted {flag}"
            )
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if request.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface source promoted readiness {flag}"
            )
        if boundary.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface source boundary promoted readiness {flag}"
            )
    if [item.get("check") for item in request.get("pre_approval_checks", [])] != REQUIRED_PRE_APPROVAL_CHECKS:
        raise CityOpsContractError("document handoff approval request read surface source pre-check drift")
    for item in request.get("pre_approval_checks", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("document handoff approval request read surface source pre-check not required")
        for flag in ["passed_here", "approval_granted", "customer_delivery_allowed", "publication_allowed"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"document handoff approval request read surface source pre-check promoted {flag}"
                )
    if [
        item.get("check")
        for item in request.get("redaction_and_authority_requirements", [])
    ] != REDACTION_AND_AUTHORITY_REQUIREMENTS:
        raise CityOpsContractError("document handoff approval request read surface source redaction drift")
    for item in request.get("redaction_and_authority_requirements", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("document handoff approval request read surface source redaction not required")
        for flag in ["passed_here", "authorizes_delivery_or_publication"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"document handoff approval request read surface source redaction promoted {flag}"
                )
    path = request.get("authorized_delivery_path", {})
    if path.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("document handoff approval request read surface source delivery path drift")
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
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed",
    ]:
        if path.get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface source delivery path promoted {flag}"
            )


def _build_operator_cards(request: dict[str, Any]) -> list[dict[str, Any]]:
    boundary = request["selected_text_boundary"]
    delivery_path = request["authorized_delivery_path"]
    return [
        {
            "card": "pending_boundary",
            "status": "visible_internal_admin_only_not_approved",
            "values": {
                "selected_text_boundary_count": request["selected_text_boundary_count"],
                "selected_text_boundary_key": boundary["key"],
                "candidate_text_boundary": boundary["candidate_text_boundary"],
                "candidate_text_value": boundary["candidate_text_value"],
                "selected_text_boundary_approved": False,
                "human_operator_approval_recorded": False,
            },
        },
        {
            "card": "pre_approval_checks",
            "status": "requirements_visible_but_unmet_by_this_surface",
            "values": [dict(item) for item in request["pre_approval_checks"]],
        },
        {
            "card": "redaction_and_authority_requirements",
            "status": "requirements_visible_but_unmet_by_this_surface",
            "values": [dict(item) for item in request["redaction_and_authority_requirements"]],
        },
        {
            "card": "authorized_delivery_path",
            "status": "none_recorded_no_delivery_no_publication_no_dispatch",
            "values": dict(delivery_path),
        },
        {
            "card": "review_queue",
            "status": "operator_worklist_only_no_approval",
            "values": [
                {
                    "item": item,
                    "requires_future_human_operator_action": True,
                    "satisfied_by_this_surface": False,
                    "approval_granted_by_this_surface": False,
                }
                for item in REVIEW_QUEUE_ITEMS
            ],
        },
        {
            "card": "claim_boundaries",
            "status": "visible_without_softening",
            "values": {
                "safe_to_claim": list(request["safe_to_claim"]),
                "do_not_claim_yet": list(request["do_not_claim_yet"]),
            },
        },
    ]


def build_document_handoff_approval_request_read_surface(
    *,
    artifact_dir: Path | None = None,
    source_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only internal/admin surface for the pending request."""

    request = source_request or _load_source_request(artifact_dir=artifact_dir)
    _assert_source_request_is_conservative(request)

    safe_to_claim = _dedupe(
        [
            *request.get("safe_to_claim", []),
            DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *SURFACE_BLOCKED_CLAIMS,
            *request.get("do_not_claim_yet", []),
        ]
    )

    surface: dict[str, Any] = {
        "schema": DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SCHEMA,
        "surface_id": SURFACE_ID,
        "scope": SCOPE,
        "surface_status": SURFACE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_request_file": DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
        "source_request_id": request["request_id"],
        "source_request_schema": request["schema"],
        "source_request_digest_sha256": _canonical_digest(request),
        "source_safe_claim": DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "approval_request_snapshot": {
            "approval_request_status": request["approval_request_status"],
            "selected_text_boundary_count": request["selected_text_boundary_count"],
            "selected_text_boundary_key": request["selected_text_boundary"]["key"],
            "candidate_text_boundary": request["selected_text_boundary"]["candidate_text_boundary"],
            "candidate_text_value": request["selected_text_boundary"]["candidate_text_value"],
            "human_operator_approval_recorded": False,
            "selected_text_boundary_approved": False,
            "customer_delivery_authorized": False,
            "publication_authorized": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "network_route_registered": False,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "dispatch_enabled": False,
        },
        "mount_contract": {
            "mount_status": MOUNT_STATUS,
            "method": "GET",
            "suggested_internal_path": "/internal/admin/aas/document-handoff/approval-request-review",
            "network_route_registered": False,
            "response_fields": [
                "approval_request_snapshot",
                "operator_cards",
                "safe_to_claim",
                "do_not_claim_yet",
                "surface_flags",
            ],
        },
        "operator_cards": _build_operator_cards(request),
        "surface_flags": dict(SURFACE_FALSE_FLAGS),
        **SURFACE_FALSE_FLAGS,
        "readiness": {flag: False for flag in REQUEST_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this only as a read-only internal/admin surface for a pending "
            "Document / Handoff approval request. It is not the approval record. "
            "It does not satisfy pre-approval checks, redactions, authority review, "
            "delivery path authorization, publication, queue launch, dispatch, "
            "reputation, live runtime parity, exact GPS/raw metadata release, legal/"
            "notarial/private-identity/acceptance/filing/custody claims, or worker doctrine."
        ),
        "next_smallest_proof": (
            "A real human operator may later create a separate approval record for "
            "this exact selected text boundary only, with external review evidence, "
            "passed redactions, an explicit delivery-path decision, and still-blocked claims."
        ),
    }
    _assert_read_surface(surface, source_request=request)
    return surface


def _assert_read_surface(surface: dict[str, Any], *, source_request: dict[str, Any]) -> None:
    _assert_source_request_is_conservative(source_request)
    if surface.get("schema") != DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("document handoff approval request read surface schema drift")
    if surface.get("surface_id") != SURFACE_ID:
        raise CityOpsContractError("document handoff approval request read surface id drift")
    if surface.get("scope") != SCOPE:
        raise CityOpsContractError("document handoff approval request read surface scope drift")
    if surface.get("surface_status") != SURFACE_STATUS:
        raise CityOpsContractError("document handoff approval request read surface status drift")
    if surface.get("source_request_file") != DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME:
        raise CityOpsContractError("document handoff approval request read surface source file drift")
    if surface.get("source_request_id") != source_request.get("request_id"):
        raise CityOpsContractError("document handoff approval request read surface source id mismatch")
    if surface.get("source_request_schema") != DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("document handoff approval request read surface source schema drift")
    if surface.get("source_safe_claim") != DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM:
        raise CityOpsContractError("document handoff approval request read surface source safe claim drift")
    if surface.get("source_request_digest_sha256") != _canonical_digest(source_request):
        raise CityOpsContractError("document handoff approval request read surface source digest drift")
    if DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_SAFE_CLAIM not in surface.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff approval request read surface safe claim missing")
    if DOCUMENT_HANDOFF_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in surface.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("document handoff approval request read surface source safe claim missing")
    forbidden_safe = set(surface.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"document handoff approval request read surface has forbidden safe claims: {sorted(forbidden_safe)}"
        )
    overlap = set(surface.get("safe_to_claim", [])) & set(surface.get("do_not_claim_yet", []))
    if overlap:
        raise CityOpsContractError(
            f"document handoff approval request read surface claim overlap: {sorted(overlap)}"
        )
    missing_blocked = set(SURFACE_BLOCKED_CLAIMS) - set(surface.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"document handoff approval request read surface missing blocked claims: {sorted(missing_blocked)}"
        )
    if surface.get("still_blocked_claims") != surface.get("do_not_claim_yet"):
        raise CityOpsContractError("document handoff approval request read surface blocked claims drift")

    snapshot = surface.get("approval_request_snapshot", {})
    if snapshot.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("document handoff approval request read surface snapshot status drift")
    if snapshot.get("selected_text_boundary_count") != 1:
        raise CityOpsContractError("document handoff approval request read surface snapshot boundary count drift")
    if snapshot.get("selected_text_boundary_key") != SELECTED_TEXT_BOUNDARY_KEY:
        raise CityOpsContractError("document handoff approval request read surface snapshot boundary drift")
    for flag in [
        "human_operator_approval_recorded",
        "selected_text_boundary_approved",
        "customer_delivery_authorized",
        "publication_authorized",
    ]:
        if snapshot.get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface snapshot promoted {flag}"
            )

    for flag, expected in SURFACE_FALSE_FLAGS.items():
        if surface.get(flag) is not expected:
            raise CityOpsContractError(f"document handoff approval request read surface promoted {flag}")
        if surface.get("surface_flags", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"document handoff approval request read surface flag summary promoted {flag}"
            )
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface promoted readiness {flag}"
            )

    access = surface.get("access_policy", {})
    if access.get("audience") != "internal_admin_only" or access.get("requires_admin_context") is not True:
        raise CityOpsContractError("document handoff approval request read surface access drift")
    for flag in [
        "network_route_registered",
        "public_route_registered",
        "customer_visible",
        "worker_visible",
        "dispatch_enabled",
    ]:
        if access.get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface access promoted {flag}"
            )
    mount = surface.get("mount_contract", {})
    if mount.get("mount_status") != MOUNT_STATUS:
        raise CityOpsContractError("document handoff approval request read surface mount status drift")
    if mount.get("network_route_registered") is not False:
        raise CityOpsContractError("document handoff approval request read surface registered network route")

    cards = surface.get("operator_cards")
    if not isinstance(cards, list) or len(cards) != 6:
        raise CityOpsContractError("document handoff approval request read surface cards drift")
    cards_by_name = {card.get("card"): card for card in cards if isinstance(card, dict)}
    for required_card in [
        "pending_boundary",
        "pre_approval_checks",
        "redaction_and_authority_requirements",
        "authorized_delivery_path",
        "review_queue",
        "claim_boundaries",
    ]:
        if required_card not in cards_by_name:
            raise CityOpsContractError("document handoff approval request read surface missing card")
    pending = cards_by_name["pending_boundary"].get("values", {})
    for flag in ["selected_text_boundary_approved", "human_operator_approval_recorded"]:
        if pending.get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface pending card promoted {flag}"
            )
    for item in cards_by_name["pre_approval_checks"].get("values", []):
        for flag in ["passed_here", "approval_granted", "customer_delivery_allowed", "publication_allowed"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"document handoff approval request read surface pre-check card promoted {flag}"
                )
    for item in cards_by_name["redaction_and_authority_requirements"].get("values", []):
        for flag in ["passed_here", "authorizes_delivery_or_publication"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"document handoff approval request read surface redaction card promoted {flag}"
                )
    delivery_values = cards_by_name["authorized_delivery_path"].get("values", {})
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
        "legal_notarial_identity_acceptance_filing_or_custody_claim_allowed",
    ]:
        if delivery_values.get(flag) is not False:
            raise CityOpsContractError(
                f"document handoff approval request read surface delivery card promoted {flag}"
            )
    for item in cards_by_name["review_queue"].get("values", []):
        if item.get("requires_future_human_operator_action") is not True:
            raise CityOpsContractError("document handoff approval request read surface review queue softened")
        for flag in ["satisfied_by_this_surface", "approval_granted_by_this_surface"]:
            if item.get(flag) is not False:
                raise CityOpsContractError(
                    f"document handoff approval request read surface review queue promoted {flag}"
                )

    _assert_no_private_coordinate_or_authority_overclaim(surface)


def _assert_no_private_coordinate_or_authority_overclaim(surface: dict[str, Any]) -> None:
    serialized = json.dumps(surface, sort_keys=True).lower()
    forbidden_substrings = [
        "latitude",
        "longitude",
        "gps:",
        "guaranteed acceptance",
        "acceptance guaranteed",
        "custody guaranteed",
        "filing success confirmed",
        "official acceptance confirmed",
        "legal service provided",
        "notarial act completed",
        "driver license",
        "passport",
    ]
    for substring in forbidden_substrings:
        if substring in serialized:
            raise CityOpsContractError(
                "document handoff approval request read surface leaked coordinate/private authority overclaim"
            )


def write_document_handoff_approval_request_read_surface(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    surface = build_document_handoff_approval_request_read_surface(artifact_dir=target_dir)
    path = target_dir / DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2) + "\n", encoding="utf-8")
    return path


def load_document_handoff_approval_request_read_surface(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / DOCUMENT_HANDOFF_APPROVAL_REQUEST_READ_SURFACE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    if not isinstance(surface, dict):
        raise CityOpsContractError("document handoff approval request read surface must be JSON object")
    _assert_read_surface(surface, source_request=_load_source_request(artifact_dir=source_dir))
    return surface
