"""Prevented-claim panel for the AAS claim quarantine surface.

This module turns the internal/admin claim quarantine read surface into a
review-oriented panel that records which tempting launch claims were prevented
and the exact next proof needed before each bucket can move. It is deliberately
internal/admin-only and read-only: it does not create approval, customer copy,
delivery, publication, public/catalog routes, pricing, pilots, operator queue
launch, dispatch, ERC-8004 reputation, worker Skill DNA, live Acontext/runtime
parity, payment or production reverification, GPS/raw metadata release, domain
authority, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_claim_quarantine_read_surface import (
    AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
    AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA,
    ACCESS_FALSE_FLAGS as SOURCE_ACCESS_FALSE_FLAGS,
    READ_SURFACE_BLOCKED_CLAIMS,
    READINESS_FALSE_FLAGS as SOURCE_READINESS_FALSE_FLAGS,
    load_aas_claim_quarantine_read_surface,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA = (
    "city_ops.aas_claim_quarantine_prevented_claim_panel.v1"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME = (
    "aas_claim_quarantine_prevented_claim_panel.json"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM = (
    "admin_aas_claim_quarantine_prevented_claim_panel_landed"
)

PANEL_ID = "execution_market.aas.claim_quarantine_prevented_claim_panel.2026_05_22"
PANEL_SCOPE = "internal_admin_prevented_claim_panel_only_no_customer_exposure"
PANEL_STATUS = "quarantined_claims_recorded_as_prevented_review_claims"

PANEL_BLOCKED_CLAIMS = [
    "prevented_claim_panel_is_human_approval_record",
    "prevented_claim_panel_approves_customer_copy",
    "prevented_claim_panel_authorizes_delivery",
    "prevented_claim_panel_authorizes_publication",
    "prevented_claim_panel_registers_public_or_catalog_route",
    "prevented_claim_panel_approves_public_price_or_quote",
    "prevented_claim_panel_authorizes_pilot_or_queue_launch",
    "prevented_claim_panel_authorizes_dispatch",
    "prevented_claim_panel_authorizes_erc8004_reputation",
    "prevented_claim_panel_proves_worker_skill_dna",
    "prevented_claim_panel_proves_live_acontext_or_runtime_parity",
    "prevented_claim_panel_reverifies_payment_or_production",
    "prevented_claim_panel_allows_exact_gps_or_raw_metadata",
    "prevented_claim_panel_grants_domain_or_legal_authority",
    "prevented_claim_panel_creates_worker_copyable_doctrine",
]

PANEL_FALSE_FLAGS = {
    "panel_is_human_approval_record": False,
    "panel_approves_selected_boundary": False,
    "panel_authorizes_customer_copy": False,
    "panel_authorizes_customer_delivery": False,
    "panel_authorizes_publication": False,
    "panel_registers_public_or_catalog_route": False,
    "panel_approves_public_price_or_quote": False,
    "panel_authorizes_controlled_pilot": False,
    "panel_authorizes_operator_queue_launch": False,
    "panel_authorizes_dispatch": False,
    "panel_emits_or_authorizes_reputation": False,
    "panel_proves_worker_skill_dna": False,
    "panel_proves_live_acontext_or_runtime_parity": False,
    "panel_reverifies_payment_or_production_health": False,
    "panel_allows_exact_gps_or_raw_metadata_release": False,
    "panel_grants_domain_legal_notarial_custody_or_incident_authority": False,
    "panel_creates_worker_copyable_aas_doctrine": False,
}

PANEL_READINESS_FALSE_FLAGS = {
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
    "all_prevented_claims_have_named_next_proof": True,
}

PANEL_ACCESS_FALSE_FLAGS = {
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


def _source_prevented_claims(surface: dict[str, Any]) -> list[str]:
    return _dedupe(
        [
            claim
            for bucket in surface["quarantine_bucket_cards"]
            for claim in bucket["claims"]
        ]
    )


def build_aas_claim_quarantine_prevented_claim_panel(
    *,
    artifact_dir: Path | None = None,
    surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the internal/admin prevented-claim panel from the read surface."""

    source_surface = surface or load_aas_claim_quarantine_read_surface(
        artifact_dir=artifact_dir
    )
    _assert_source_surface_is_quarantined(source_surface)

    prevented_claims = _source_prevented_claims(source_surface)
    safe_to_claim = _dedupe(
        [
            *source_surface["claim_boundaries"]["safe_to_claim"],
            AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_surface["claim_boundaries"]["do_not_claim_yet"],
            *READ_SURFACE_BLOCKED_CLAIMS,
            *PANEL_BLOCKED_CLAIMS,
            *prevented_claims,
        ]
    )

    panel: dict[str, Any] = {
        "schema": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA,
        "panel_id": PANEL_ID,
        "scope": PANEL_SCOPE,
        "panel_status": PANEL_STATUS,
        "source_artifact": {
            "file": AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
            "schema": source_surface["schema"],
            "id": source_surface["surface_id"],
            "scope": source_surface["scope"],
            "status": source_surface["surface_status"],
            "safe_claim": AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
            "digest_sha256": _canonical_digest(source_surface),
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME],
            "consumes_only": [AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME],
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
            "classification_performed": "quarantined_claims_marked_prevented",
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
            **PANEL_ACCESS_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": dict(PANEL_READINESS_FALSE_FLAGS),
        **PANEL_FALSE_FLAGS,
        "prevented_claim_summary": {
            "source_bucket_count": len(source_surface["quarantine_bucket_cards"]),
            "prevented_bucket_count": len(source_surface["quarantine_bucket_cards"]),
            "prevented_claim_count": len(prevented_claims),
            "claims_can_leave_prevented_state_without_named_proof": False,
            "panel_safe_to_use_now": "internal_admin_review_learning_only",
        },
        "prevented_claim_cards": _prevented_claim_cards(source_surface),
        "next_proof_queue": _next_proof_queue(source_surface),
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "prevented_claims": prevented_claims,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
            "prevented_claim_count": len(prevented_claims),
        },
        "panel_verdict": "claim_quarantine_prevented_claim_panel_landed_internal_admin_only",
        "operator_instruction": (
            "Use this panel as the review-regret ledger for tempting launch claims. "
            "Each card names the claims that were prevented and the exact next proof "
            "needed before any claim can leave quarantine. The panel is not approval, "
            "not customer copy, not delivery, not publication, not a public route, not "
            "dispatch, not reputation, not runtime parity, and not worker doctrine."
        ),
    }
    _assert_panel_is_conservative(panel, source_surface)
    return panel


def write_aas_claim_quarantine_prevented_claim_panel(
    artifact_dir: Path | None = None,
) -> Path:
    """Persist the deterministic prevented-claim panel fixture."""

    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    panel = build_aas_claim_quarantine_prevented_claim_panel(artifact_dir=target_dir)
    path = target_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME
    path.write_text(json.dumps(panel, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_claim_quarantine_prevented_claim_panel(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Load and validate the persisted prevented-claim panel fixture."""

    target_dir = artifact_dir or ARTIFACT_DIR
    path = target_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME
    panel = json.loads(path.read_text(encoding="utf-8"))
    source_surface = load_aas_claim_quarantine_read_surface(artifact_dir=target_dir)
    _assert_panel_is_conservative(panel, source_surface)
    return panel


def _prevented_claim_cards(surface: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for rank, bucket in enumerate(surface["quarantine_bucket_cards"], start=1):
        cards.append(
            {
                "rank": rank,
                "bucket_id": bucket["bucket_id"],
                "label": bucket["label"],
                "review_disposition": "prevented_by_claim_quarantine",
                "display_badge": "PREVENTED — PROOF REQUIRED",
                "prevented_claims": list(bucket["claims"]),
                "prevented_claim_count": len(bucket["claims"]),
                "exact_next_proof_needed": bucket["next_smallest_proof"],
                "operator_action": "keep_blocked_until_named_proof_exists",
                "may_override_without_new_proof": False,
                "may_publish_or_launch": False,
                "may_dispatch_or_attach_reputation": False,
                "may_create_worker_copyable_doctrine": False,
            }
        )
    return cards


def _next_proof_queue(surface: dict[str, Any]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for item in surface["next_smallest_proof_queue"]:
        queued = dict(item)
        queued["panel_interpretation"] = (
            "proof_needed_before_any_matching_claim_can_leave_prevented_state"
        )
        queued["customer_or_dispatch_authority_created_by_queue_item"] = False
        queue.append(queued)
    return queue


def _assert_source_surface_is_quarantined(surface: dict[str, Any]) -> None:
    if surface.get("schema") != AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("source surface schema drift")
    if surface.get("access_policy", {}).get("audience") != "internal_admin_only":
        raise CityOpsContractError("source surface audience drift")
    for flag in SOURCE_ACCESS_FALSE_FLAGS:
        if surface["access_policy"].get(flag) is not False:
            raise CityOpsContractError(f"source access flag promoted: {flag}")
    for flag in SOURCE_READINESS_FALSE_FLAGS:
        if surface["readiness"].get(flag) is not False:
            raise CityOpsContractError(f"source readiness flag promoted: {flag}")
    for bucket in surface.get("quarantine_bucket_cards", []):
        if bucket.get("status") != "quarantined_not_safe_to_claim":
            raise CityOpsContractError("source bucket status drift")
        if bucket.get("may_publish_or_launch") is not False:
            raise CityOpsContractError("source bucket launch promoted")
        if not bucket.get("next_smallest_proof"):
            raise CityOpsContractError("source bucket missing next proof")
        if not bucket.get("claims"):
            raise CityOpsContractError("source bucket missing claims")


def _assert_panel_is_conservative(
    panel: dict[str, Any], source_surface: dict[str, Any]
) -> None:
    _assert_source_surface_is_quarantined(source_surface)
    if panel.get("schema") != AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA:
        raise CityOpsContractError("prevented-claim panel schema drift")
    if panel.get("scope") != PANEL_SCOPE:
        raise CityOpsContractError("prevented-claim panel scope drift")
    if panel.get("source_artifact", {}).get("digest_sha256") != _canonical_digest(
        source_surface
    ):
        raise CityOpsContractError("prevented-claim panel source digest drift")

    prevented_claims = _source_prevented_claims(source_surface)
    safe_to_claim = panel["claim_boundaries"]["safe_to_claim"]
    do_not_claim_yet = panel["claim_boundaries"]["do_not_claim_yet"]
    forbidden_safe = set(prevented_claims) | set(PANEL_BLOCKED_CLAIMS)
    leaked = sorted(forbidden_safe & set(safe_to_claim))
    if leaked:
        raise CityOpsContractError(f"forbidden safe claims: {leaked}")
    missing_blocked = sorted(set(prevented_claims) - set(do_not_claim_yet))
    if missing_blocked:
        raise CityOpsContractError(f"prevented claims missing from blocked list: {missing_blocked}")

    for flag in PANEL_FALSE_FLAGS:
        if panel.get(flag) is not False:
            raise CityOpsContractError(f"panel false flag promoted: {flag}")
    for flag, expected in PANEL_READINESS_FALSE_FLAGS.items():
        if panel["readiness"].get(flag) is not expected:
            raise CityOpsContractError(f"panel readiness flag drift: {flag}")
    for flag in PANEL_ACCESS_FALSE_FLAGS:
        if panel["access_policy"].get(flag) is not False:
            raise CityOpsContractError(f"panel access flag promoted: {flag}")

    cards = panel.get("prevented_claim_cards", [])
    if len(cards) != len(source_surface["quarantine_bucket_cards"]):
        raise CityOpsContractError("prevented-claim card count drift")
    for card, bucket in zip(cards, source_surface["quarantine_bucket_cards"], strict=True):
        if card.get("bucket_id") != bucket["bucket_id"]:
            raise CityOpsContractError("prevented-claim bucket drift")
        if card.get("review_disposition") != "prevented_by_claim_quarantine":
            raise CityOpsContractError("prevented-claim disposition drift")
        if card.get("prevented_claims") != bucket["claims"]:
            raise CityOpsContractError("prevented-claim list drift")
        if card.get("prevented_claim_count") != len(bucket["claims"]):
            raise CityOpsContractError("prevented-claim count drift")
        if card.get("exact_next_proof_needed") != bucket["next_smallest_proof"]:
            raise CityOpsContractError("prevented-claim next proof drift")
        for flag in [
            "may_override_without_new_proof",
            "may_publish_or_launch",
            "may_dispatch_or_attach_reputation",
            "may_create_worker_copyable_doctrine",
        ]:
            if card.get(flag) is not False:
                raise CityOpsContractError(f"prevented-claim card promoted: {flag}")
