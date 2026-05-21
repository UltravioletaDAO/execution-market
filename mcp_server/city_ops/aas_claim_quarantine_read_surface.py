"""Read surface for the AAS claim quarantine board.

This module converts the internal/admin AAS claim quarantine board into a
bounded operator-facing payload for a future admin surface. It is deliberately
read-only: it does not create approval, customer copy, delivery, publication,
public/catalog routes, pricing, pilots, operator queue launch, dispatch,
ERC-8004 reputation, worker Skill DNA, live Acontext/runtime parity, payment or
production reverification, GPS/raw metadata release, domain authority, or
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_claim_quarantine_board import (
    AAS_CLAIM_QUARANTINE_BOARD_FILENAME,
    AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_BOARD_SCHEMA,
    BOARD_FALSE_FLAGS,
    BOARD_ID,
    BOARD_STATUS,
    FORBIDDEN_SAFE_CLAIMS as SOURCE_FORBIDDEN_SAFE_CLAIMS,
    QUARANTINE_BUCKETS,
    SCOPE as BOARD_SCOPE,
    load_aas_claim_quarantine_board,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA = (
    "city_ops.aas_claim_quarantine_read_surface.v1"
)
AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME = (
    "aas_claim_quarantine_read_surface.json"
)
AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM = (
    "admin_aas_claim_quarantine_read_surface_landed"
)

SURFACE_ID = "execution_market.aas.claim_quarantine_read_surface.2026_05_21"
SURFACE_SCOPE = "internal_admin_claim_quarantine_read_surface_only_no_customer_exposure"
SURFACE_STATUS = "read_only_launch_claim_quarantine_surface_landed_not_route"

SURFACE_FALSE_FLAGS = {
    "surface_is_human_approval_record": False,
    "surface_approves_selected_boundary": False,
    "surface_authorizes_customer_copy": False,
    "surface_authorizes_customer_delivery": False,
    "surface_authorizes_publication": False,
    "surface_registers_public_or_catalog_route": False,
    "surface_approves_public_price_or_quote": False,
    "surface_authorizes_controlled_pilot": False,
    "surface_authorizes_operator_queue_launch": False,
    "surface_authorizes_dispatch": False,
    "surface_emits_or_authorizes_reputation": False,
    "surface_proves_worker_skill_dna": False,
    "surface_proves_live_acontext_or_runtime_parity": False,
    "surface_reverifies_payment_or_production_health": False,
    "surface_allows_exact_gps_or_raw_metadata_release": False,
    "surface_grants_domain_legal_notarial_custody_or_incident_authority": False,
    "surface_creates_worker_copyable_aas_doctrine": False,
}

READINESS_FALSE_FLAGS = {
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "public_or_catalog_route_ready": False,
    "pricing_or_customer_quote_ready": False,
    "controlled_pilot_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "live_acontext_runtime_parity_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_ready": False,
    "domain_authority_ready": False,
    "worker_copyable_doctrine_ready": False,
}

ACCESS_FALSE_FLAGS = {
    "network_route_registered": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "publishes_worker_doctrine": False,
}

READ_SURFACE_BLOCKED_CLAIMS = [
    "claim_quarantine_read_surface_is_human_approval_record",
    "claim_quarantine_read_surface_approves_customer_copy",
    "claim_quarantine_read_surface_authorizes_delivery",
    "claim_quarantine_read_surface_authorizes_publication",
    "claim_quarantine_read_surface_registers_public_or_catalog_route",
    "claim_quarantine_read_surface_approves_public_price_or_quote",
    "claim_quarantine_read_surface_authorizes_pilot_or_queue_launch",
    "claim_quarantine_read_surface_authorizes_dispatch",
    "claim_quarantine_read_surface_authorizes_erc8004_reputation",
    "claim_quarantine_read_surface_proves_worker_skill_dna",
    "claim_quarantine_read_surface_proves_live_acontext_or_runtime_parity",
    "claim_quarantine_read_surface_reverifies_payment_or_production",
    "claim_quarantine_read_surface_allows_exact_gps_or_raw_metadata",
    "claim_quarantine_read_surface_grants_domain_or_legal_authority",
    "claim_quarantine_read_surface_creates_worker_copyable_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = SOURCE_FORBIDDEN_SAFE_CLAIMS | set(READ_SURFACE_BLOCKED_CLAIMS)


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


def build_aas_claim_quarantine_read_surface(
    *,
    artifact_dir: Path | None = None,
    board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic read-only internal/admin surface from the board."""

    source_board = board or load_aas_claim_quarantine_board(artifact_dir=artifact_dir)
    _assert_source_board_conservative(source_board)

    safe_to_claim = _dedupe(
        [
            *source_board["safe_to_claim"],
            AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_board["do_not_claim_yet"],
            *source_board["quarantined_claims"],
            *READ_SURFACE_BLOCKED_CLAIMS,
        ]
    )

    surface = {
        "schema": AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA,
        "surface_id": SURFACE_ID,
        "scope": SURFACE_SCOPE,
        "surface_status": SURFACE_STATUS,
        "source_artifact": {
            "file": AAS_CLAIM_QUARANTINE_BOARD_FILENAME,
            "schema": source_board["schema"],
            "id": source_board["board_id"],
            "scope": source_board["scope"],
            "status": source_board["board_status"],
            "safe_claim": AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM,
            "digest_sha256": _canonical_digest(source_board),
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_CLAIM_QUARANTINE_BOARD_FILENAME],
            "consumes_only": [AAS_CLAIM_QUARANTINE_BOARD_FILENAME],
            "forbidden_inputs": [
                "raw_transcripts",
                "unreviewed_memory",
                "private_operator_context",
                "live_acontext_sink_writes",
                "live_acontext_retrievals",
                "payment_processor_probe",
                "production_health_probe",
                "gps_or_raw_metadata_payloads",
                "customer_copy_drafts",
                "worker_instruction_templates",
            ],
            "semantic_reinterpretation_performed": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "writes_customer_copy": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **ACCESS_FALSE_FLAGS,
        },
        "render_contract": {
            "render_status": "internal_admin_claim_quarantine_read_surface_landed_not_route",
            "suggested_internal_path": "/internal/admin/city-ops/aas-claim-quarantine",
            "network_route_registered": False,
            "public_route_registered": False,
            "layout": (
                "source_header_bucket_cards_family_hold_cards_next_proof_queue_"
                "sticky_claim_boundary_footer"
            ),
            "allowed_interpretation": "pass_through_quarantine_board_fields_only",
            "response_fields": [
                "source_summary",
                "quarantine_bucket_cards",
                "family_hold_cards",
                "next_smallest_proof_queue",
                "claim_boundary_footer",
                "readiness",
            ],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": dict(READINESS_FALSE_FLAGS),
        **SURFACE_FALSE_FLAGS,
        "source_summary": _source_summary(source_board),
        "quarantine_bucket_cards": _quarantine_bucket_cards(source_board),
        "family_hold_cards": list(source_board["family_hold_cards"]),
        "next_smallest_proof_queue": list(source_board["next_smallest_proof_queue"]),
        "claim_boundary_footer": _claim_boundary_footer(safe_to_claim, do_not_claim_yet),
        "surface_verdict": "claim_quarantine_read_surface_landed_internal_admin_only",
        "operator_instruction": (
            "Render this as a sticky internal/admin launch-claim firewall. Every bucket remains "
            "quarantined until its named smallest proof exists; this surface is not approval, "
            "not customer delivery, not publication, not a route, not dispatch, not reputation, "
            "not runtime parity, and not worker doctrine."
        ),
    }
    _assert_surface_conservative(surface, source_board)
    return surface


def write_aas_claim_quarantine_read_surface(artifact_dir: Path | None = None) -> Path:
    """Persist the deterministic claim quarantine read-surface fixture."""

    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    surface = build_aas_claim_quarantine_read_surface(artifact_dir=target_dir)
    path = target_dir / AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_claim_quarantine_read_surface(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Load and validate the persisted claim quarantine read surface."""

    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    if not isinstance(surface, dict):
        raise CityOpsContractError("AAS claim quarantine read surface must be a JSON object")
    board = load_aas_claim_quarantine_board(artifact_dir=source_dir)
    _assert_surface_conservative(surface, board)
    expected = build_aas_claim_quarantine_read_surface(artifact_dir=source_dir, board=board)
    if surface != expected:
        raise CityOpsContractError("claim quarantine read surface drifted from source board")
    return surface


def _source_summary(board: dict[str, Any]) -> dict[str, Any]:
    summary = dict(board["matrix_summary_snapshot"])
    return {
        "source_board_id": board["board_id"],
        "source_board_status": board["board_status"],
        "source_scope": board["scope"],
        "family_count": summary["family_count"],
        "human_approval_records": summary["families_with_human_approval_record"],
        "delivery_authorizations": summary["families_with_delivery_authorization"],
        "publishable_families": summary["families_publishable"],
        "dispatch_ready_families": summary["families_ready_for_dispatch"],
        "runtime_parity_families": summary["families_with_live_acontext_runtime_parity"],
        "gps_release_ready_families": summary[
            "families_allowed_to_release_exact_gps_or_raw_metadata"
        ],
        "safe_claim": AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
        "honest_claim_scope": "internal_admin_read_surface_only",
    }


def _quarantine_bucket_cards(board: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for bucket in board["quarantine_buckets"]:
        cards.append(
            {
                "bucket_id": bucket["bucket_id"],
                "label": bucket["label"],
                "status": bucket["status"],
                "claim_count": len(bucket["claims"]),
                "claims": list(bucket["claims"]),
                "next_smallest_proof": bucket["next_smallest_proof"],
                "display_badge": "QUARANTINED — NOT SAFE TO CLAIM",
                "safe_to_use_now": bucket["safe_to_use_now"],
                "may_publish_or_launch": False,
            }
        )
    return cards


def _claim_boundary_footer(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> dict[str, Any]:
    return {
        "safe_claim_count": len(safe_to_claim),
        "blocked_claim_count": len(do_not_claim_yet),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "sticky_warning": (
            "Internal/admin read surface only. Do not quote quarantined claims as product "
            "readiness without a separate named proof artifact."
        ),
    }


def _assert_source_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_CLAIM_QUARANTINE_BOARD_SCHEMA:
        raise CityOpsContractError("claim quarantine read surface source schema drift")
    if board.get("board_id") != BOARD_ID:
        raise CityOpsContractError("claim quarantine read surface source id drift")
    if board.get("scope") != BOARD_SCOPE:
        raise CityOpsContractError("claim quarantine read surface source scope drift")
    if board.get("board_status") != BOARD_STATUS:
        raise CityOpsContractError("claim quarantine read surface source status drift")
    if AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM not in board.get("safe_to_claim", []):
        raise CityOpsContractError("claim quarantine read surface source safe claim missing")
    forbidden_safe = set(board.get("safe_to_claim", [])) & SOURCE_FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"claim quarantine read surface source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    if set(board.get("safe_to_claim", [])) & set(board.get("do_not_claim_yet", [])):
        raise CityOpsContractError("claim quarantine read surface source safe/blocked overlap")
    missing_blocked = set(board.get("quarantined_claims", [])) - set(
        board.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"claim quarantine read surface source missing blocked claims: {sorted(missing_blocked)}"
        )
    if [bucket.get("bucket_id") for bucket in board.get("quarantine_buckets", [])] != [
        bucket["bucket_id"] for bucket in QUARANTINE_BUCKETS
    ]:
        raise CityOpsContractError("claim quarantine read surface source bucket drift")
    for bucket in board.get("quarantine_buckets", []):
        if bucket.get("status") != "quarantined_not_safe_to_claim":
            raise CityOpsContractError("claim quarantine read surface source bucket status drift")
        if bucket.get("may_publish_or_launch") is not False:
            raise CityOpsContractError("claim quarantine read surface source bucket launch promoted")
        if set(bucket.get("source_matrix_zero_counts", {}).values()) != {0}:
            raise CityOpsContractError("claim quarantine read surface source matrix counts promoted")
    for flag, expected in BOARD_FALSE_FLAGS.items():
        if board.get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine read surface source promoted {flag}")
    for card in board.get("family_hold_cards", []):
        for flag in [
            "authorized_delivery_path_authorized",
            "customer_delivery_authorized",
            "publication_authorized",
        ]:
            if card.get(flag) is not False:
                raise CityOpsContractError(
                    f"claim quarantine read surface source family card promoted {flag}"
                )


def _assert_surface_conservative(
    surface: dict[str, Any], source_board: dict[str, Any]
) -> None:
    _assert_source_board_conservative(source_board)
    if surface.get("schema") != AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("claim quarantine read surface schema drift")
    if surface.get("surface_id") != SURFACE_ID:
        raise CityOpsContractError("claim quarantine read surface id drift")
    if surface.get("scope") != SURFACE_SCOPE:
        raise CityOpsContractError("claim quarantine read surface scope drift")
    if surface.get("surface_status") != SURFACE_STATUS:
        raise CityOpsContractError("claim quarantine read surface status drift")
    if surface.get("source_artifact", {}).get("digest_sha256") != _canonical_digest(
        source_board
    ):
        raise CityOpsContractError("claim quarantine read surface source digest drift")
    safe_to_claim = surface.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = surface.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("claim quarantine read surface safe claim missing")
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"claim quarantine read surface forbidden safe claims: {sorted(forbidden_safe)}"
        )
    if set(safe_to_claim) & set(do_not_claim_yet):
        raise CityOpsContractError("claim quarantine read surface safe/blocked overlap")
    missing_blocked = set(READ_SURFACE_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"claim quarantine read surface missing blocked claims: {sorted(missing_blocked)}"
        )
    for flag, expected in SURFACE_FALSE_FLAGS.items():
        if surface.get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine read surface promoted {flag}")
    for flag, expected in READINESS_FALSE_FLAGS.items():
        if surface.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"claim quarantine read surface promoted readiness {flag}"
            )
    for flag, expected in ACCESS_FALSE_FLAGS.items():
        if surface.get("access_policy", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"claim quarantine read surface promoted access policy {flag}"
            )
    render = surface.get("render_contract", {})
    for flag in ["network_route_registered", "public_route_registered"]:
        if render.get(flag) is not False:
            raise CityOpsContractError(f"claim quarantine read surface registered {flag}")
    if [card.get("bucket_id") for card in surface.get("quarantine_bucket_cards", [])] != [
        bucket["bucket_id"] for bucket in QUARANTINE_BUCKETS
    ]:
        raise CityOpsContractError("claim quarantine read surface bucket card drift")
    for card in surface.get("quarantine_bucket_cards", []):
        if card.get("display_badge") != "QUARANTINED — NOT SAFE TO CLAIM":
            raise CityOpsContractError("claim quarantine read surface badge drift")
        if card.get("may_publish_or_launch") is not False:
            raise CityOpsContractError("claim quarantine read surface bucket launch promoted")
    footer = surface.get("claim_boundary_footer", {})
    if footer.get("safe_to_claim") != safe_to_claim:
        raise CityOpsContractError("claim quarantine read surface footer safe claims drift")
    if footer.get("do_not_claim_yet") != do_not_claim_yet:
        raise CityOpsContractError("claim quarantine read surface footer blocked claims drift")
