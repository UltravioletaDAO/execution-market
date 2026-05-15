"""Single-boundary human-operator approval request for held AAS families.

This module is the cautious customer-exposure fork after the internal
packaging/pricing/operator-workflow review board. It creates one request packet
for a human operator to review exactly one held text boundary. It is not a
human approval record, not customer delivery, not publication, not a public
route, not pricing approval, not dispatch, not reputation, not live
Acontext/runtime parity, not exact GPS/raw metadata exposure, and not
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_packaging_pricing_operator_workflow_review_board import (
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME,
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM,
    AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA,
    BOARD_ID,
    BOARD_READINESS_FALSE_FLAGS,
    REQUIRED_BLOCKED_CLAIMS as BOARD_REQUIRED_BLOCKED_CLAIMS,
    build_aas_packaging_pricing_operator_workflow_review_board,
    load_aas_packaging_pricing_operator_workflow_review_board,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA = (
    "city_ops.aas_single_boundary_human_operator_approval_request.v1"
)
AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME = (
    "aas_single_boundary_human_operator_approval_request.json"
)
AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM = (
    "aas_single_boundary_human_operator_approval_request_landed"
)

REQUEST_ID = "execution_market.aas.single_boundary_human_operator_approval_request.001"
SCOPE = "internal_admin_single_boundary_human_operator_approval_request_only"
SELECTED_BOUNDARY_KEY = "compliance_desk"
APPROVAL_REQUEST_STATUS = "pending_human_operator_review_not_approved"
AUTHORIZED_DELIVERY_PATH = "none_until_separate_human_operator_approval_record"

REQUIRED_REDACTION_CHECKS = [
    "exact_gps_removed",
    "raw_metadata_removed",
    "private_source_identifiers_removed",
    "domain_authority_language_absent",
    "legal_regulator_or_inspection_guarantee_language_absent",
    "dispatch_instruction_language_absent",
    "reputation_receipt_language_absent",
    "public_price_or_customer_quote_language_absent",
]

REQUEST_READINESS_FALSE_FLAGS = [
    *BOARD_READINESS_FALSE_FLAGS,
    "human_operator_approval_recorded",
    "selected_boundary_approved",
    "customer_delivery_path_authorized",
    "customer_copy_created",
    "customer_copy_ready",
    "publication_approved",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
]

REQUIRED_BLOCKED_CLAIMS = [
    *BOARD_REQUIRED_BLOCKED_CLAIMS,
    "human_operator_approval_recorded",
    "selected_boundary_approved",
    "customer_copy_created",
    "customer_copy_ready",
    "customer_delivery_path_authorized",
    "customer_delivery_approved",
    "publication_approved",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "approval_request_publishable",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "human_operator_approval_recorded",
    "selected_boundary_approved",
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "publication_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "public_price_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "worker_copyable_doctrine_ready",
}

REQUIRED_SOURCE_SUMMARY_FLAGS = {
    "all_rows_remain_held": True,
    "customer_copy_approved": False,
    "customer_delivery_approved": False,
    "publication_approved": False,
    "public_prices_or_customer_quotes_approved": False,
    "routes_pilots_dispatch_reputation_live_runtime_gps_worker_doctrine_approved": False,
}


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


def _load_source_board(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_packaging_pricing_operator_workflow_review_board(
        artifact_dir=artifact_dir
    )


def _assert_source_board(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA:
        raise CityOpsContractError("approval request source board schema drift")
    if board.get("board_id") != BOARD_ID:
        raise CityOpsContractError("approval request source board id drift")
    if AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM not in board.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval request source board safe claim missing")
    forbidden_safe = set(board.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval request source board forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(BOARD_REQUIRED_BLOCKED_CLAIMS) - set(
        board.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"approval request source board missing blocked claims: {sorted(missing_blocked)}"
        )
    summary = board.get("summary", {})
    for flag, expected in REQUIRED_SOURCE_SUMMARY_FLAGS.items():
        if summary.get(flag) is not expected:
            raise CityOpsContractError(f"approval request source board summary drift {flag}")
    for flag in BOARD_READINESS_FALSE_FLAGS:
        if board.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"approval request source board promoted readiness {flag}")
    rows = board.get("review_rows", [])
    if len(rows) != 3:
        raise CityOpsContractError("approval request source board row count drift")
    matches = [row for row in rows if row.get("key") == SELECTED_BOUNDARY_KEY]
    if len(matches) != 1:
        raise CityOpsContractError("approval request source board selected boundary missing")
    for row in rows:
        if row.get("still_held") is not True:
            raise CityOpsContractError("approval request source board row stopped being held")
        for field in [
            "package_label_customer_copy_approved",
            "public_price_approved",
            "customer_quote_ready",
            "operator_queue_launch_ready",
        ]:
            if row.get(field) is not False:
                raise CityOpsContractError(f"approval request source board promoted row {field}")
        for flag in BOARD_READINESS_FALSE_FLAGS:
            if row.get("readiness", {}).get(flag) is not False:
                raise CityOpsContractError(
                    f"approval request source board row promoted readiness {flag}"
                )


def _selected_boundary(board: dict[str, Any]) -> dict[str, Any]:
    row = next(row for row in board["review_rows"] if row["key"] == SELECTED_BOUNDARY_KEY)
    return {
        "key": row["key"],
        "family_id": row["family_id"],
        "family_label": row["family_label"],
        "offer_id": row["offer_id"],
        "candidate_text_boundary": "internal_package_label_only",
        "candidate_text_value": row["package_label_under_review"],
        "candidate_text_fields": ["package_label_under_review"],
        "approval_request_boundary": (
            "human_operator_may_review_this_one_label_later_but_no_approval_is_recorded_here"
        ),
        "blocked_authority_class": row["blocked_authority_class"],
        "pricing_unit_context_not_approved_price": row["pricing_unit_under_review"],
        "operator_queue_context_not_launch_ready": row["operator_queue_under_review"],
        "source_package_label_customer_copy_approved": row[
            "package_label_customer_copy_approved"
        ],
        "source_public_price_approved": row["public_price_approved"],
        "source_customer_quote_ready": row["customer_quote_ready"],
        "source_operator_queue_launch_ready": row["operator_queue_launch_ready"],
        "selected_boundary_approved": False,
        "human_operator_approval_recorded": False,
        "readiness": {flag: False for flag in REQUEST_READINESS_FALSE_FLAGS},
    }


def _redaction_requirements() -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "required_before_human_approval": True,
            "passed_here": False,
            "approval_boundary": "requirement_only_not_approval_or_delivery",
        }
        for check in REQUIRED_REDACTION_CHECKS
    ]


def _delivery_path() -> dict[str, Any]:
    return {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "no_customer_delivery_no_publication_no_dispatch",
        "customer_delivery_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
    }


def build_aas_single_boundary_human_operator_approval_request(
    *,
    artifact_dir: Path | None = None,
    source_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one pending human-operator approval request from the review board."""

    board = source_board or _load_source_board(artifact_dir=artifact_dir)
    _assert_source_board(board)

    safe_to_claim = _dedupe(
        [
            *board.get("safe_to_claim", []),
            AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*REQUIRED_BLOCKED_CLAIMS, *board.get("do_not_claim_yet", [])])

    packet = {
        "schema": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
        "request_id": REQUEST_ID,
        "scope": SCOPE,
        "source_board_file": AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME,
        "source_board_schema": board["schema"],
        "source_board_id": board["board_id"],
        "source_board_digest_sha256": _canonical_digest(board),
        "source_safe_claim": AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "approval_request_status": APPROVAL_REQUEST_STATUS,
        "human_operator_approval_recorded": False,
        "selected_boundary_count": 1,
        "selected_boundary": _selected_boundary(board),
        "redaction_requirements": _redaction_requirements(),
        "authorized_delivery_path": _delivery_path(),
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
        "customer_delivery_path_authorized": False,
        "customer_copy_created": False,
        "customer_copy_ready": False,
        "customer_visible_catalog_ready": False,
        "public_service_catalog_ready": False,
        "publication_approved": False,
        "public_route_ready": False,
        "controlled_pilot_ready": False,
        "front_door_sku_ready": False,
        "public_price_approved": False,
        "customer_quote_ready": False,
        "operator_queue_launch_ready": False,
        "dispatch_enabled": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "erc8004_reputation_ready": False,
        "worker_skill_dna_ready": False,
        "worker_copyable_doctrine_ready": False,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
        "readiness": {flag: False for flag in REQUEST_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "This packet only asks a human operator to review one held internal label boundary. "
            "It does not record approval, create customer copy, authorize delivery, publish, "
            "launch a route or queue, dispatch workers, attach reputation, expose exact GPS/raw "
            "metadata, or make domain-authority claims."
        ),
        "next_smallest_proof": (
            "If a human approves this exact boundary later, create a separate approval record "
            "that names exact approved text, passed redactions, authorized delivery path, and "
            "still-blocked claims."
        ),
    }
    _assert_packet(packet)
    return packet


def _assert_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA:
        raise CityOpsContractError("approval request schema drift")
    if packet.get("request_id") != REQUEST_ID:
        raise CityOpsContractError("approval request id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("approval request scope drift")
    if packet.get("source_board_file") != AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME:
        raise CityOpsContractError("approval request source board file drift")
    if packet.get("source_board_schema") != AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA:
        raise CityOpsContractError("approval request source board schema drift")
    if packet.get("source_board_id") != BOARD_ID:
        raise CityOpsContractError("approval request source board id drift")
    if packet.get("source_safe_claim") != AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM:
        raise CityOpsContractError("approval request source safe claim drift")
    if AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("approval request safe claim missing")
    forbidden_safe = set(packet.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"approval request has forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(packet.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"approval request missing blocked claims: {sorted(missing_blocked)}"
        )
    if packet.get("approval_request_status") != APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("approval request status drift")
    if packet.get("human_operator_approval_recorded") is not False:
        raise CityOpsContractError("approval request recorded human approval")
    if packet.get("selected_boundary_count") != 1:
        raise CityOpsContractError("approval request must name exactly one boundary")
    boundary = packet.get("selected_boundary", {})
    if boundary.get("key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("approval request selected boundary drift")
    if boundary.get("selected_boundary_approved") is not False:
        raise CityOpsContractError("approval request selected boundary approved")
    if boundary.get("human_operator_approval_recorded") is not False:
        raise CityOpsContractError("approval request boundary recorded human approval")
    for source_flag in [
        "source_package_label_customer_copy_approved",
        "source_public_price_approved",
        "source_customer_quote_ready",
        "source_operator_queue_launch_ready",
    ]:
        if boundary.get(source_flag) is not False:
            raise CityOpsContractError(f"approval request boundary source promoted {source_flag}")
    for flag in REQUEST_READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"approval request promoted readiness {flag}")
        if boundary.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"approval request boundary promoted readiness {flag}")
    if [item.get("check") for item in packet.get("redaction_requirements", [])] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("approval request redaction requirements drift")
    for item in packet.get("redaction_requirements", []):
        if item.get("required_before_human_approval") is not True:
            raise CityOpsContractError("approval request redaction requirement not required")
        if item.get("passed_here") is not False:
            raise CityOpsContractError("approval request redaction marked passed before approval")
    delivery = packet.get("authorized_delivery_path", {})
    if delivery.get("path") != AUTHORIZED_DELIVERY_PATH:
        raise CityOpsContractError("approval request delivery path drift")
    for field in [
        "customer_delivery_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
    ]:
        if delivery.get(field) is not False:
            raise CityOpsContractError(f"approval request delivery path promoted {field}")
    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "customer_delivery_path_authorized",
        "customer_copy_created",
        "customer_copy_ready",
        "customer_visible_catalog_ready",
        "public_service_catalog_ready",
        "publication_approved",
        "public_route_ready",
        "controlled_pilot_ready",
        "front_door_sku_ready",
        "public_price_approved",
        "customer_quote_ready",
        "operator_queue_launch_ready",
        "dispatch_enabled",
        "autonomous_dispatch_ready",
        "reputation_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "worker_copyable_doctrine_ready",
        "live_acontext_ready",
        "runtime_parity_proven",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        if packet.get(flag) is not False:
            raise CityOpsContractError(f"approval request promoted readiness {flag}")
    if packet.get("still_blocked_claims") != packet.get("do_not_claim_yet"):
        raise CityOpsContractError("approval request blocked claims drift")


def write_aas_single_boundary_human_operator_approval_request(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_single_boundary_human_operator_approval_request(
        artifact_dir=target_dir
    )
    path = target_dir / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_single_boundary_human_operator_approval_request(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    _assert_packet(packet)
    return packet
