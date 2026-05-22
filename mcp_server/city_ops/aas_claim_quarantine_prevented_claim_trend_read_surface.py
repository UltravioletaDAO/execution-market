"""Internal/admin read surface for AAS prevented-claim trend summary.

The prevented-claim trend summary identifies the recurring blocked claims that
agent coordination keeps trying to promote.  This module renders those trends as
operator cards for the AAS ladder without changing authority: no customer copy,
no delivery/publication, no public/catalog route, no pricing, no pilot or queue
launch, no dispatch, no ERC-8004 reputation, no worker Skill DNA, no live
Acontext/runtime parity, no payment/production reverification, no GPS/raw
metadata release, and no worker-copyable doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_claim_quarantine_prevented_claim_trend_summary import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SCHEMA,
    TREND_SUMMARY_BLOCKED_CLAIMS,
    TREND_SUMMARY_FALSE_ACCESS_FLAGS,
    TREND_SUMMARY_READINESS_FLAGS,
    build_aas_claim_quarantine_prevented_claim_trend_summary,
    load_aas_claim_quarantine_prevented_claim_trend_summary,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA = (
    "city_ops.aas_claim_quarantine_prevented_claim_trend_read_surface.v1"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME = (
    "aas_claim_quarantine_prevented_claim_trend_read_surface.json"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM = (
    "internal_admin_aas_claim_quarantine_prevented_claim_trend_read_surface_landed"
)

TREND_READ_SURFACE_ID = (
    "execution_market.aas.claim_quarantine.prevented_claim_trend_read_surface.2026_05_22"
)
TREND_READ_SURFACE_SCOPE = "internal_admin_prevented_claim_trend_cards_only_no_route"
TREND_READ_SURFACE_STATUS = "prevented_claim_trends_rendered_as_operator_cards_only"
TREND_READ_SURFACE_VERDICT = "prevented_claim_trend_cards_ready_for_internal_review_only"

TREND_READ_SURFACE_BLOCKED_CLAIMS = [
    *TREND_SUMMARY_BLOCKED_CLAIMS,
    "trend_read_surface_is_network_route",
    "trend_read_surface_is_human_approval_record",
    "trend_read_surface_approves_customer_copy",
    "trend_read_surface_authorizes_customer_delivery",
    "trend_read_surface_authorizes_publication",
    "trend_read_surface_registers_public_or_catalog_route",
    "trend_read_surface_approves_public_price_or_quote",
    "trend_read_surface_authorizes_controlled_pilot_or_queue_launch",
    "trend_read_surface_authorizes_dispatch",
    "trend_read_surface_authorizes_erc8004_reputation",
    "trend_read_surface_proves_worker_skill_dna",
    "trend_read_surface_proves_live_acontext_or_runtime_parity",
    "trend_read_surface_reverifies_payment_or_production",
    "trend_read_surface_allows_exact_gps_or_raw_metadata",
    "trend_read_surface_grants_domain_legal_notarial_custody_or_incident_authority",
    "trend_read_surface_creates_worker_copyable_aas_doctrine",
]

TREND_READ_SURFACE_READINESS_FLAGS = {
    "trend_read_surface_landed": True,
    "source_trend_summary_verified": True,
    "operator_cards_ready": True,
    "connection_map_ready": True,
    "next_proof_slots_preserved": True,
    "network_route_registered": False,
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

TREND_READ_SURFACE_FALSE_FLAGS = {
    "surface_is_network_route": False,
    "surface_is_human_approval_record": False,
    "surface_approves_customer_copy": False,
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


def build_aas_claim_quarantine_prevented_claim_trend_read_surface(
    *,
    artifact_dir: str | Path | None = None,
    trend_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic operator cards from the prevented-claim trend summary."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    summary = trend_summary or load_aas_claim_quarantine_prevented_claim_trend_summary(
        artifact_dir=base_dir
    )
    _assert_source_summary_contract(summary)

    safe_to_claim = _dedupe(
        [
            *summary["claim_boundaries"]["safe_to_claim"],
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *summary["claim_boundaries"]["do_not_claim_yet"],
            *TREND_READ_SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    cards = _operator_cards(summary)
    surface = {
        "schema": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA,
        "surface_id": TREND_READ_SURFACE_ID,
        "scope": TREND_READ_SURFACE_SCOPE,
        "surface_status": TREND_READ_SURFACE_STATUS,
        "source_artifact": {
            "file": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME,
            "schema": summary["schema"],
            "id": summary["summary_id"],
            "safe_claim": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SAFE_CLAIM,
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME],
            "consumes_only": [AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME],
            "forbidden_inputs": [
                "raw_transcripts",
                "unreviewed_memory",
                "private_operator_context",
                "freeform_worker_chat",
                "live_acontext_sink_writes",
                "live_acontext_retrievals",
                "payment_processor_probe",
                "production_health_probe",
                "gps_or_raw_metadata_payloads",
                "customer_copy_drafts",
                "worker_instruction_templates",
            ],
            "reads_raw_transcripts": False,
            "reads_unreviewed_memory": False,
            "reads_private_operator_context": False,
            "adds_route": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "writes_municipal_memory": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
            "semantic_reinterpretation_performed": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "network_route_registered": False,
            **TREND_SUMMARY_FALSE_ACCESS_FLAGS,
        },
        "readiness": dict(TREND_READ_SURFACE_READINESS_FLAGS),
        "operator_cards": cards,
        "connection_map": _connection_map(summary, cards),
        "recommended_next_actions": [
            "Use the cards as an internal operator briefing before choosing any selected-boundary approval-record work.",
            "Treat repeated prevented claims as a signal to improve proof sequencing, not as evidence that launch is ready.",
            "If customer exposure is desired, create a separate human approval artifact naming exact text, redactions, delivery path, and still-blocked claims.",
        ],
        "not_next_actions": [
            "Do not mount this surface as a customer/public route without a separate route preflight and approval decision.",
            "Do not publish copy, quote pricing, launch a pilot, dispatch workers, attach reputation, or infer worker Skill DNA from this surface.",
            "Do not write live Acontext, expose GPS/raw metadata, claim payment/production health, or create worker-copyable doctrine from this surface.",
        ],
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
            "operator_card_count": len(cards),
        },
        **TREND_READ_SURFACE_FALSE_FLAGS,
        "surface_verdict": TREND_READ_SURFACE_VERDICT,
    }
    _assert_trend_read_surface_contract(surface, summary)
    return surface


def load_aas_claim_quarantine_prevented_claim_trend_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted trend read surface."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    path = base_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = load_aas_claim_quarantine_prevented_claim_trend_summary(artifact_dir=base_dir)
    _assert_trend_read_surface_contract(payload, summary)
    return payload


def write_aas_claim_quarantine_prevented_claim_trend_read_surface(
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic prevented-claim trend read surface."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _operator_cards(summary: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for row in summary["trend_rows"]:
        cards.append(
            {
                "rank": row["rank"],
                "bucket_id": row["bucket_id"],
                "label": row["label"],
                "display_badge": row["display_badge"],
                "prevented_claim_count": row["prevented_claim_count"],
                "operator_readout": (
                    "This is a repeated blocked-claim bucket. Keep it visible so agents "
                    "stop re-promoting it before the named proof exists."
                ),
                "exact_next_proof_needed": row["exact_next_proof_needed"],
                "may_leave_quarantine_without_named_proof": False,
                "may_publish_or_launch": False,
                "may_dispatch_or_attach_reputation": False,
                "may_write_live_acontext": False,
                "may_create_worker_copyable_doctrine": False,
            }
        )
    return sorted(cards, key=lambda card: (-card["prevented_claim_count"], card["rank"]))


def _connection_map(summary: dict[str, Any], cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    top_bucket = cards[0]["bucket_id"]
    prevented_count = summary["trend_summary"]["prevented_claim_count"]
    return [
        {
            "connection": "memory_patterns_to_reviewed_proof_slots",
            "insight": "memory is valuable when it becomes bounded reviewed candidates, not raw runtime truth",
            "evidence": top_bucket,
            "multiplier_effect": "future agents inherit the next proof needed before repeating stale launch claims",
            "authorizes_live_acontext": False,
        },
        {
            "connection": "irc_coordination_to_state_cards",
            "insight": "IRC/session coordination scales through state cards and digests, not transcript replay",
            "evidence": "route_panel_handoff_packet_plus_prevented_claim_trend_summary",
            "multiplier_effect": "handoffs preserve claim boundaries even when session context is stale",
            "authorizes_runtime_mutation": False,
        },
        {
            "connection": "cross_project_intelligence_to_priority_firewall",
            "insight": "cross-project intelligence compounds only when active stop-lists stay enforceable",
            "evidence": "stale AutoJob Frontier KK payload blocked by active AAS boundary",
            "multiplier_effect": "dream work remains pointed at CaaS/AAS instead of scattering into old wins",
            "authorizes_autorouting": False,
        },
        {
            "connection": "agent_success_metrics_to_restraint_reputation_candidate",
            "insight": "the strongest coordination signal can be refusing to launch without proof",
            "evidence": f"{prevented_count} prevented claims preserved as blocked",
            "multiplier_effect": "future reputation can reward proof discipline after a separate reputation gate exists",
            "emits_reputation_receipts": False,
        },
        {
            "connection": "claim_quarantine_to_product_surface_sequence",
            "insight": "quarantine does not slow product; it creates the safe order for productization",
            "evidence": "operator cards keep exact next-proof requirements beside every bucket",
            "multiplier_effect": "one approved boundary can later become customer-visible without dragging unapproved neighbors",
            "authorizes_customer_or_public_surface": False,
        },
    ]


def _assert_source_summary_contract(summary: dict[str, Any]) -> None:
    if summary.get("schema") != AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SCHEMA:
        raise CityOpsContractError("trend read surface requires prevented-claim trend summary schema")
    if summary.get("scope") != "internal_admin_prevented_claim_trend_summary_only_no_customer_exposure":
        raise CityOpsContractError("trend read surface summary scope drift")
    if summary.get("summary_verdict") != "prevented_claim_trend_summary_ready_for_internal_review_learning_only":
        raise CityOpsContractError("trend read surface summary verdict drift")
    if summary.get("trend_summary", {}).get("claims_can_leave_prevented_state_without_named_proof") is not False:
        raise CityOpsContractError("trend read surface refuses summary proof bypass")
    if not summary.get("trend_rows"):
        raise CityOpsContractError("trend read surface requires trend rows")
    for flag in TREND_SUMMARY_FALSE_ACCESS_FLAGS:
        if summary.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"trend read surface refuses source access drift: {flag}")
    for flag, expected in TREND_SUMMARY_READINESS_FLAGS.items():
        if summary.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"trend read surface refuses source readiness drift: {flag}")


def _assert_trend_read_surface_contract(surface: dict[str, Any], summary: dict[str, Any]) -> None:
    _assert_source_summary_contract(summary)
    if surface.get("schema") != AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("trend read surface schema drift")
    if surface.get("scope") != TREND_READ_SURFACE_SCOPE:
        raise CityOpsContractError("trend read surface scope drift")
    if surface.get("surface_verdict") != TREND_READ_SURFACE_VERDICT:
        raise CityOpsContractError("trend read surface verdict drift")
    if surface.get("source_artifact", {}).get("id") != summary.get("summary_id"):
        raise CityOpsContractError("trend read surface source id drift")

    safe_to_claim = surface["claim_boundaries"]["safe_to_claim"]
    do_not_claim_yet = surface["claim_boundaries"]["do_not_claim_yet"]
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)
    missing_blocked = sorted(set(TREND_READ_SURFACE_BLOCKED_CLAIMS) - set(do_not_claim_yet))
    if missing_blocked:
        raise CityOpsContractError(f"trend read surface missing blocked claims: {missing_blocked}")

    if len(surface.get("operator_cards", [])) != len(summary["trend_rows"]):
        raise CityOpsContractError("trend read surface card count drift")
    if len(surface.get("connection_map", [])) != 5:
        raise CityOpsContractError("trend read surface connection map count drift")

    for container in [surface.get("derived_from", {}), surface.get("access_policy", {})]:
        for flag in [
            "writes_customer_copy",
            "writes_live_acontext",
            "retrieves_live_acontext",
            "enables_dispatch_automation",
            "emits_reputation_receipts",
            "exposes_gps_or_metadata",
            "publishes_worker_doctrine",
        ]:
            if flag in container and container.get(flag) is not False:
                raise CityOpsContractError(f"trend read surface promoted forbidden flag: {flag}")

    for flag, expected in TREND_READ_SURFACE_READINESS_FLAGS.items():
        if surface.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"trend read surface readiness flag drift: {flag}")
    for flag in TREND_READ_SURFACE_FALSE_FLAGS:
        if surface.get(flag) is not False:
            raise CityOpsContractError(f"trend read surface false flag promoted: {flag}")

    for card in surface["operator_cards"]:
        for flag in [
            "may_leave_quarantine_without_named_proof",
            "may_publish_or_launch",
            "may_dispatch_or_attach_reputation",
            "may_write_live_acontext",
            "may_create_worker_copyable_doctrine",
        ]:
            if card.get(flag) is not False:
                raise CityOpsContractError(f"trend read surface card promoted: {flag}")
        if not card.get("exact_next_proof_needed"):
            raise CityOpsContractError("trend read surface card missing next proof")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"trend read surface claim overlap: {overlap}")
