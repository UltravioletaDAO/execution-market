"""AAS claim quarantine board.

This module turns the cross-family AAS approval-state matrix into a single
internal/admin board that keeps tempting launch, customer, runtime, payment,
reputation, GPS/raw-metadata, and domain-authority claims quarantined until the
smallest explicit proof artifact exists.  It deliberately does not approve
customer copy, delivery, publication, pricing, public routes, pilots, queues,
dispatch, reputation, live Acontext/runtime parity, payment/production health,
GPS/raw metadata release, domain/legal authority, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_cross_family_approval_state_matrix import (
    AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME,
    AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM,
    AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SCHEMA,
    MATRIX_BLOCKED_CLAIMS,
    MATRIX_FALSE_FLAGS,
    load_aas_cross_family_approval_state_matrix,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CLAIM_QUARANTINE_BOARD_SCHEMA = "city_ops.aas_claim_quarantine_board.v1"
AAS_CLAIM_QUARANTINE_BOARD_FILENAME = "aas_claim_quarantine_board.json"
AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM = "admin_aas_claim_quarantine_board_landed"

BOARD_ID = "execution_market.aas.claim_quarantine_board.2026_05_21"
SCOPE = "internal_admin_claim_quarantine_board_only_no_customer_exposure"
BOARD_STATUS = "all_launch_customer_runtime_and_authority_claims_quarantined"

QUARANTINE_BUCKETS = [
    {
        "bucket_id": "customer_and_public_exposure",
        "label": "Customer/public exposure",
        "claims": [
            "customer_copy_ready",
            "customer_delivery_approved",
            "publication_approved",
            "publishable",
            "public_route_ready",
            "catalog_ready",
            "front_door_sku_ready",
        ],
        "next_smallest_proof": (
            "separate human operator delivery/publication decision that names an "
            "approved delivery path and passes fresh redaction/domain-authority checks"
        ),
    },
    {
        "bucket_id": "pricing_and_operator_launch",
        "label": "Pricing/operator launch",
        "claims": [
            "public_price_ready",
            "customer_quote_ready",
            "operator_queue_launch_ready",
            "controlled_pilot_ready",
            "operator_workflow_launch_ready",
        ],
        "next_smallest_proof": (
            "operator-reviewed pricing/workflow approval artifact after customer exposure "
            "boundaries are approved; not derivable from package labels alone"
        ),
    },
    {
        "bucket_id": "dispatch_reputation_and_worker_dna",
        "label": "Dispatch/reputation/worker Skill DNA",
        "claims": [
            "dispatch_ready",
            "autonomous_dispatch_ready",
            "erc8004_reputation_ready",
            "reputation_receipts_attachable",
            "worker_skill_dna_ready",
            "worker_copyable_doctrine_ready",
        ],
        "next_smallest_proof": (
            "live-safe dispatch route plus explicit reputation receipt policy; worker-copyable "
            "doctrine requires separately reviewed repeatable cases"
        ),
    },
    {
        "bucket_id": "runtime_payment_and_production",
        "label": "Runtime/payment/production readiness",
        "claims": [
            "live_acontext_runtime_parity",
            "live_acontext_ready",
            "runtime_parity_proven",
            "payment_production_reverified",
            "payment_coverage_reverified",
            "production_infrastructure_reverified",
        ],
        "next_smallest_proof": (
            "fresh live runtime preflight, successful Acontext transport parity proof, and "
            "separate payment/production health verification from current infrastructure"
        ),
    },
    {
        "bucket_id": "location_metadata_and_domain_authority",
        "label": "Location metadata/domain authority",
        "claims": [
            "gps_release_ready",
            "raw_metadata_release_ready",
            "exact_gps_or_raw_metadata_release_allowed",
            "domain_authority_ready",
            "legal_or_regulator_authority_ready",
            "emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
        ],
        "next_smallest_proof": (
            "explicit scoped authority review and redaction pass; never inferred from an "
            "approval-state matrix or package review packet"
        ),
    },
]

BOARD_FALSE_FLAGS = {
    "board_creates_human_approval": False,
    "board_approves_selected_boundary": False,
    "board_authorizes_customer_copy": False,
    "board_authorizes_customer_delivery": False,
    "board_authorizes_publication": False,
    "board_registers_public_or_catalog_route": False,
    "board_approves_public_price_or_quote": False,
    "board_authorizes_controlled_pilot": False,
    "board_authorizes_operator_queue_launch": False,
    "board_authorizes_dispatch": False,
    "board_emits_or_authorizes_reputation": False,
    "board_proves_worker_skill_dna": False,
    "board_proves_live_acontext_or_runtime_parity": False,
    "board_reverifies_payment_or_production_health": False,
    "board_allows_exact_gps_or_raw_metadata_release": False,
    "board_grants_domain_legal_notarial_custody_or_incident_authority": False,
    "board_creates_worker_copyable_aas_doctrine": False,
}

FORBIDDEN_SAFE_CLAIMS = {
    claim for bucket in QUARANTINE_BUCKETS for claim in bucket["claims"]
} | set(MATRIX_BLOCKED_CLAIMS)

REQUIRED_MATRIX_ZERO_COUNTS = [
    "families_with_delivery_authorization",
    "families_publishable",
    "families_with_public_or_catalog_routes",
    "families_ready_for_dispatch",
    "families_with_reputation_attachment_ready",
    "families_with_live_acontext_runtime_parity",
    "families_allowed_to_release_exact_gps_or_raw_metadata",
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


def _quarantined_claims() -> list[str]:
    return _dedupe([claim for bucket in QUARANTINE_BUCKETS for claim in bucket["claims"]])


def build_aas_claim_quarantine_board(
    *,
    artifact_dir: Path | None = None,
    matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the conservative internal/admin quarantine board."""

    source_matrix = matrix or load_aas_cross_family_approval_state_matrix(
        artifact_dir=artifact_dir
    )
    _assert_source_matrix_is_held(source_matrix)

    quarantined_claims = _quarantined_claims()
    safe_to_claim = _dedupe(
        [
            *source_matrix["safe_to_claim"],
            AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_matrix["do_not_claim_yet"],
            *MATRIX_BLOCKED_CLAIMS,
            *quarantined_claims,
        ]
    )

    board: dict[str, Any] = {
        "schema": AAS_CLAIM_QUARANTINE_BOARD_SCHEMA,
        "board_id": BOARD_ID,
        "scope": SCOPE,
        "board_status": BOARD_STATUS,
        "source_artifact": {
            "file": AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_FILENAME,
            "schema": source_matrix["schema"],
            "id": source_matrix["matrix_id"],
            "digest_sha256": _canonical_digest(source_matrix),
            "safe_claim": AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM,
        },
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "quarantined_claims": quarantined_claims,
        "quarantine_buckets": _bucket_cards(source_matrix),
        "family_hold_cards": _family_hold_cards(source_matrix),
        "matrix_summary_snapshot": dict(source_matrix["matrix_summary"]),
        "next_smallest_proof_queue": _next_smallest_proof_queue(source_matrix),
        **BOARD_FALSE_FLAGS,
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this board as a launch-claim quarantine checklist. A claim leaving quarantine "
            "requires the named smallest proof artifact; the matrix itself is not approval, "
            "not customer copy, not a route, not dispatch, not reputation, and not runtime parity."
        ),
    }
    _assert_board_is_conservative(board, source_matrix=source_matrix)
    return board


def write_aas_claim_quarantine_board(artifact_dir: Path | None = None) -> Path:
    """Persist the deterministic AAS claim quarantine board fixture."""

    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    board = build_aas_claim_quarantine_board(artifact_dir=target_dir)
    path = target_dir / AAS_CLAIM_QUARANTINE_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_claim_quarantine_board(artifact_dir: Path | None = None) -> dict[str, Any]:
    """Load and validate the persisted quarantine board."""

    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_CLAIM_QUARANTINE_BOARD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        board = json.load(fh)
    if not isinstance(board, dict):
        raise CityOpsContractError("AAS claim quarantine board must be a JSON object")
    matrix = load_aas_cross_family_approval_state_matrix(artifact_dir=source_dir)
    _assert_board_is_conservative(board, source_matrix=matrix)
    return board


def _bucket_cards(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    zero_summary = matrix["matrix_summary"]
    return [
        {
            "bucket_id": bucket["bucket_id"],
            "label": bucket["label"],
            "status": "quarantined_not_safe_to_claim",
            "claims": list(bucket["claims"]),
            "source_matrix_zero_counts": {
                key: zero_summary[key] for key in REQUIRED_MATRIX_ZERO_COUNTS
            },
            "next_smallest_proof": bucket["next_smallest_proof"],
            "safe_to_use_now": "internal_admin_review_and_planning_only",
            "may_publish_or_launch": False,
        }
        for bucket in QUARANTINE_BUCKETS
    ]


def _family_hold_cards(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for row in matrix["approval_state_rows"]:
        cards.append(
            {
                "family_id": row["family_id"],
                "family_label": row["family_label"],
                "state": row["state"],
                "selected_boundary_label": row["selected_boundary_label"],
                "human_operator_approval_record_exists": row["human_operator_approval_record_exists"],
                "selected_boundary_approved": row["selected_boundary_approved"],
                "authorized_delivery_path_authorized": False,
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "claim_quarantine_status": "held_until_named_next_smallest_proof",
                "next_smallest_proof": row["next_smallest_proof"],
            }
        )
    return cards


def _next_smallest_proof_queue(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    queue = [
        {
            "rank": 1,
            "proof_id": "named_delivery_path_decision_for_compliance_boundary",
            "family_id": "compliance_desk_as_a_service",
            "unblocks_only_if_passed": [
                "customer_delivery_approved_for_named_path",
                "publication_approved_for_named_path_if_explicit",
            ],
            "still_requires_afterward": [
                "public_route_or_catalog_review",
                "pricing_operator_queue_review",
                "dispatch_reputation_runtime_review",
            ],
        },
        {
            "rank": 2,
            "proof_id": "human_approval_record_for_one_pending_family",
            "family_id": "document_handoff_or_incident_verification",
            "unblocks_only_if_passed": ["selected_boundary_approved_for_that_family"],
            "still_requires_afterward": ["separate_delivery_publication_gate"],
        },
        {
            "rank": 3,
            "proof_id": "live_runtime_payment_reputation_preflight_bundle",
            "family_id": "cross_family_runtime_track",
            "unblocks_only_if_passed": [
                "runtime_parity_review",
                "payment_production_review",
                "reputation_receipt_policy_review",
            ],
            "still_requires_afterward": ["customer_exposure_and_dispatch_approval"],
        },
    ]
    queue.append(
        {
            "rank": 4,
            "proof_id": "keep_all_claims_quarantined",
            "family_id": "all",
            "unblocks_only_if_passed": [],
            "still_requires_afterward": _quarantined_claims(),
            "source_matrix_next_smallest_proof": matrix["next_smallest_proof"],
        }
    )
    return queue


def _assert_source_matrix_is_held(matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SCHEMA:
        raise CityOpsContractError("claim quarantine source matrix schema drift")
    if AAS_CROSS_FAMILY_APPROVAL_STATE_MATRIX_SAFE_CLAIM not in matrix.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("claim quarantine source matrix safe claim missing")
    forbidden_safe = set(matrix.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"claim quarantine source matrix forbidden safe claims: {sorted(forbidden_safe)}"
        )
    if set(matrix.get("safe_to_claim", [])) & set(matrix.get("do_not_claim_yet", [])):
        raise CityOpsContractError("claim quarantine source matrix safe/blocked overlap")
    summary = matrix.get("matrix_summary", {})
    if summary.get("family_count") != 3:
        raise CityOpsContractError("claim quarantine source matrix family count drift")
    for key in REQUIRED_MATRIX_ZERO_COUNTS:
        if summary.get(key) != 0:
            raise CityOpsContractError(f"claim quarantine source matrix promoted {key}")
    for flag in MATRIX_FALSE_FLAGS:
        if matrix.get(flag) is not False:
            raise CityOpsContractError(f"claim quarantine source matrix promoted false flag {flag}")
    for row in matrix.get("approval_state_rows", []):
        for flag in [
            "authorized_delivery_path_authorized",
            "customer_delivery_authorized",
            "publication_authorized",
        ]:
            if row.get(flag) is not False:
                raise CityOpsContractError(f"claim quarantine source matrix row promoted {flag}")


def _assert_board_is_conservative(
    board: dict[str, Any], *, source_matrix: dict[str, Any]
) -> None:
    _assert_source_matrix_is_held(source_matrix)
    if board.get("schema") != AAS_CLAIM_QUARANTINE_BOARD_SCHEMA:
        raise CityOpsContractError("claim quarantine board schema drift")
    if board.get("board_id") != BOARD_ID:
        raise CityOpsContractError("claim quarantine board id drift")
    if board.get("scope") != SCOPE:
        raise CityOpsContractError("claim quarantine board scope drift")
    if board.get("board_status") != BOARD_STATUS:
        raise CityOpsContractError("claim quarantine board status drift")
    if board.get("source_artifact", {}).get("digest_sha256") != _canonical_digest(
        source_matrix
    ):
        raise CityOpsContractError("claim quarantine board source digest drift")
    safe_to_claim = board.get("safe_to_claim", [])
    do_not_claim_yet = board.get("do_not_claim_yet", [])
    if AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("claim quarantine board safe claim missing")
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"claim quarantine board forbidden safe claims: {sorted(forbidden_safe)}"
        )
    if set(safe_to_claim) & set(do_not_claim_yet):
        raise CityOpsContractError("claim quarantine board safe/blocked overlap")
    missing_blocked = set(_quarantined_claims()) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"claim quarantine board missing quarantined claims: {sorted(missing_blocked)}"
        )
    if board.get("still_blocked_claims") != do_not_claim_yet:
        raise CityOpsContractError("claim quarantine board blocked claims drift")
    if board.get("quarantined_claims") != _quarantined_claims():
        raise CityOpsContractError("claim quarantine board claim list drift")
    if [bucket.get("bucket_id") for bucket in board.get("quarantine_buckets", [])] != [
        bucket["bucket_id"] for bucket in QUARANTINE_BUCKETS
    ]:
        raise CityOpsContractError("claim quarantine board bucket order drift")
    for bucket in board.get("quarantine_buckets", []):
        if bucket.get("status") != "quarantined_not_safe_to_claim":
            raise CityOpsContractError("claim quarantine board bucket status drift")
        if bucket.get("may_publish_or_launch") is not False:
            raise CityOpsContractError("claim quarantine board bucket launch promoted")
    if len(board.get("family_hold_cards", [])) != 3:
        raise CityOpsContractError("claim quarantine board family hold card count drift")
    for card in board.get("family_hold_cards", []):
        for flag in [
            "authorized_delivery_path_authorized",
            "customer_delivery_authorized",
            "publication_authorized",
        ]:
            if card.get(flag) is not False:
                raise CityOpsContractError(f"claim quarantine board card promoted {flag}")
    for flag, expected in BOARD_FALSE_FLAGS.items():
        if board.get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine board promoted false flag {flag}")
