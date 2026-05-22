"""Internal/admin prevented-claim trend summary for AAS claim quarantine.

This module turns the deterministic route+panel handoff packet into a compact
review-learning summary. It is intentionally conservative: the summary helps
operators see which blocked AAS launch claims recur most often, but it does not
create approval, customer copy, delivery, publication, public/catalog routes,
pricing, pilots, operator queue launch, dispatch, ERC-8004 reputation, worker
Skill DNA, live Acontext/runtime parity, payment/production reverification,
GPS/raw metadata release, domain authority, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_claim_quarantine_prevented_claim_panel import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA,
    PANEL_ACCESS_FALSE_FLAGS,
    PANEL_BLOCKED_CLAIMS,
    PANEL_FALSE_FLAGS,
    PANEL_READINESS_FALSE_FLAGS,
    load_aas_claim_quarantine_prevented_claim_panel,
)
from .aas_claim_quarantine_route_panel_handoff_packet import (
    AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME,
    AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SCHEMA,
    HANDOFF_BLOCKED_CLAIMS,
    HANDOFF_FALSE_ACCESS_FLAGS,
    build_aas_claim_quarantine_route_panel_handoff_packet,
    load_aas_claim_quarantine_route_panel_handoff_packet,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SCHEMA = (
    "city_ops.aas_claim_quarantine_prevented_claim_trend_summary.v1"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME = (
    "aas_claim_quarantine_prevented_claim_trend_summary.json"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SAFE_CLAIM = (
    "internal_admin_aas_claim_quarantine_prevented_claim_trend_summary_landed"
)

TREND_SUMMARY_ID = "execution_market.aas.claim_quarantine.prevented_claim_trend_summary.2026_05_22"
TREND_SUMMARY_SCOPE = "internal_admin_prevented_claim_trend_summary_only_no_customer_exposure"
TREND_SUMMARY_STATUS = "prevented_claim_trends_summarized_for_operator_learning_only"
TREND_SUMMARY_VERDICT = "prevented_claim_trend_summary_ready_for_internal_review_learning_only"

TREND_SUMMARY_BLOCKED_CLAIMS = [
    "prevented_claim_trend_summary_is_human_approval_record",
    "prevented_claim_trend_summary_approves_customer_copy",
    "prevented_claim_trend_summary_authorizes_customer_delivery",
    "prevented_claim_trend_summary_authorizes_publication",
    "prevented_claim_trend_summary_registers_public_or_catalog_route",
    "prevented_claim_trend_summary_approves_public_price_or_quote",
    "prevented_claim_trend_summary_authorizes_controlled_pilot_or_queue_launch",
    "prevented_claim_trend_summary_authorizes_dispatch",
    "prevented_claim_trend_summary_authorizes_erc8004_reputation",
    "prevented_claim_trend_summary_proves_worker_skill_dna",
    "prevented_claim_trend_summary_proves_live_acontext_or_runtime_parity",
    "prevented_claim_trend_summary_reverifies_payment_or_production",
    "prevented_claim_trend_summary_allows_exact_gps_or_raw_metadata",
    "prevented_claim_trend_summary_grants_domain_legal_notarial_custody_or_incident_authority",
    "prevented_claim_trend_summary_creates_worker_copyable_aas_doctrine",
]

TREND_SUMMARY_FALSE_ACCESS_FLAGS = {
    **HANDOFF_FALSE_ACCESS_FLAGS,
    "network_route_registered": False,
}

TREND_SUMMARY_READINESS_FLAGS = {
    "trend_summary_landed": True,
    "source_handoff_verified": True,
    "source_panel_verified": True,
    "operator_learning_ready": True,
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

TREND_SUMMARY_FALSE_FLAGS = {
    "summary_is_human_approval_record": False,
    "summary_approves_selected_boundary": False,
    "summary_authorizes_customer_copy": False,
    "summary_authorizes_customer_delivery": False,
    "summary_authorizes_publication": False,
    "summary_registers_public_or_catalog_route": False,
    "summary_approves_public_price_or_quote": False,
    "summary_authorizes_controlled_pilot": False,
    "summary_authorizes_operator_queue_launch": False,
    "summary_authorizes_dispatch": False,
    "summary_emits_or_authorizes_reputation": False,
    "summary_proves_worker_skill_dna": False,
    "summary_proves_live_acontext_or_runtime_parity": False,
    "summary_reverifies_payment_or_production_health": False,
    "summary_allows_exact_gps_or_raw_metadata_release": False,
    "summary_grants_domain_legal_notarial_custody_or_incident_authority": False,
    "summary_creates_worker_copyable_aas_doctrine": False,
}


def build_aas_claim_quarantine_prevented_claim_trend_summary(
    *,
    artifact_dir: str | Path | None = None,
    handoff_packet: dict[str, Any] | None = None,
    prevented_claim_panel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin trend summary from handoff + panel."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    packet = handoff_packet or load_aas_claim_quarantine_route_panel_handoff_packet(
        artifact_dir=base_dir
    )
    panel = prevented_claim_panel or load_aas_claim_quarantine_prevented_claim_panel(
        artifact_dir=base_dir
    )
    _assert_handoff_packet_contract(packet)
    _assert_panel_contract(panel)

    safe_to_claim = _dedupe(
        [
            *packet["claim_boundaries"]["safe_to_claim"],
            *panel["claim_boundaries"]["safe_to_claim"],
            AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *packet["claim_boundaries"]["do_not_claim_yet"],
            *panel["claim_boundaries"]["do_not_claim_yet"],
            *HANDOFF_BLOCKED_CLAIMS,
            *PANEL_BLOCKED_CLAIMS,
            *TREND_SUMMARY_BLOCKED_CLAIMS,
        ]
    )
    prevented_claims = panel["claim_boundary_footer"]["prevented_claims"]
    do_not_claim_yet = _dedupe([*do_not_claim_yet, *prevented_claims])
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    rows = _trend_rows(panel)
    summary = {
        "schema": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SCHEMA,
        "summary_id": TREND_SUMMARY_ID,
        "scope": TREND_SUMMARY_SCOPE,
        "summary_status": TREND_SUMMARY_STATUS,
        "source_artifacts": {
            "route_panel_handoff_packet": {
                "file": AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME,
                "schema": packet["schema"],
                "id": packet["handoff_id"],
                "safe_claim": AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SAFE_CLAIM,
                "digest_sha256": _stable_digest(packet),
            },
            "prevented_claim_panel": {
                "file": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
                "schema": panel["schema"],
                "id": panel["panel_id"],
                "safe_claim": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
                "digest_sha256": _stable_digest(panel),
            },
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME,
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
            ],
            "consumes_only": [
                AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME,
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
            ],
            "raw_conversation_reopened": False,
            "raw_worker_evidence_reopened": False,
            "unreviewed_memory_reopened": False,
            "private_operator_context_reopened": False,
            "semantic_reinterpretation_performed": False,
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
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **TREND_SUMMARY_FALSE_ACCESS_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "trend_summary": {
            "source_bucket_count": len(rows),
            "prevented_claim_count": len(prevented_claims),
            "top_prevented_bucket": rows[0]["bucket_id"],
            "claims_can_leave_prevented_state_without_named_proof": False,
            "summary_safe_to_use_now": "internal_admin_review_learning_only",
        },
        "trend_rows": rows,
        "integration_signals": _integration_signals(rows),
        "recommended_next_actions": [
            "Use this summary to see which blocked AAS claims recur before choosing a human-operator approval-record path.",
            "Keep route mount, prevented panel, handoff packet, and trend summary together as one internal/admin decision-support chain.",
            "If customer exposure is desired, create a separate human-operator approval artifact naming exact text, redactions, delivery path, and still-blocked claims.",
        ],
        "not_next_actions": [
            "Do not publish customer copy, delivery, catalog, public route, pricing, pilot, or queue launch from this trend summary.",
            "Do not dispatch workers, attach ERC-8004 reputation, infer worker Skill DNA, or write live Acontext from this trend summary.",
            "Do not expose exact GPS/raw metadata, assert payment/production reverification, or create worker-copyable AAS doctrine from this trend summary.",
        ],
        "readiness": dict(TREND_SUMMARY_READINESS_FLAGS),
        **TREND_SUMMARY_FALSE_FLAGS,
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
            "prevented_claim_count": len(prevented_claims),
        },
        "summary_verdict": TREND_SUMMARY_VERDICT,
    }
    _assert_trend_summary_contract(summary, packet, panel)
    return summary


def load_aas_claim_quarantine_prevented_claim_trend_summary(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted trend summary fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    path = base_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    packet = load_aas_claim_quarantine_route_panel_handoff_packet(artifact_dir=base_dir)
    panel = load_aas_claim_quarantine_prevented_claim_panel(artifact_dir=base_dir)
    _assert_trend_summary_contract(payload, packet, panel)
    return payload


def write_aas_claim_quarantine_prevented_claim_trend_summary(
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic prevented-claim trend summary fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _trend_rows(panel: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in panel["prevented_claim_cards"]:
        rows.append(
            {
                "rank": card["rank"],
                "bucket_id": card["bucket_id"],
                "label": card["label"],
                "prevented_claim_count": card["prevented_claim_count"],
                "review_disposition": card["review_disposition"],
                "display_badge": card["display_badge"],
                "exact_next_proof_needed": card["exact_next_proof_needed"],
                "operator_learning_use": "trend_review_only_keep_claim_blocked_until_named_proof_exists",
                "may_publish_or_launch": False,
                "may_dispatch_or_attach_reputation": False,
                "may_write_live_acontext": False,
                "may_create_worker_copyable_doctrine": False,
            }
        )
    return sorted(rows, key=lambda row: (-row["prevented_claim_count"], row["rank"]))


def _integration_signals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "signal": "memory_to_acontext_candidate",
            "status": "bounded_candidate_not_live_sink",
            "evidence": rows[0]["bucket_id"],
            "operator_use": "capture recurring blocked-claim categories as reviewed candidates, not raw memory writes",
            "writes_live_acontext": False,
        },
        {
            "signal": "irc_session_management",
            "status": "review_learning_card_not_runtime_mutation",
            "evidence": "route_panel_handoff_packet_plus_prevented_claim_panel",
            "operator_use": "summarize coordination drift without replaying raw transcripts or changing IRC session behavior",
            "changes_irc_runtime": False,
        },
        {
            "signal": "cross_project_decision_support",
            "status": "aas_only_boundary",
            "evidence": "safe_to_claim_adjacent_to_do_not_claim_yet",
            "operator_use": "prevent stale AutoJob/Frontier/KK priorities from overriding active AAS boundaries during dreams",
            "cross_project_autorouting_enabled": False,
        },
        {
            "signal": "agent_observability_success_metrics",
            "status": "success_is_prevented_overclaim_not_launch",
            "evidence": f"{sum(row['prevented_claim_count'] for row in rows)} prevented claims remain blocked",
            "operator_use": "count prevented overclaims as coordination success until named proof exists",
            "emits_reputation_receipts": False,
        },
    ]


def _assert_handoff_packet_contract(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SCHEMA:
        raise CityOpsContractError("trend summary requires route+panel handoff packet schema")
    if packet.get("scope") != "internal_admin_route_and_prevented_claim_panel_pickup_only":
        raise CityOpsContractError("trend summary handoff scope drift")
    if packet.get("derived_from", {}).get("read_only") is not True:
        raise CityOpsContractError("trend summary requires read-only handoff")
    for flag in [
        "adds_route",
        "semantic_reinterpretation_performed",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if packet.get("derived_from", {}).get(flag) is not False:
            raise CityOpsContractError(f"trend summary refuses handoff drift: {flag}")
    for flag in HANDOFF_FALSE_ACCESS_FLAGS:
        if packet.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"trend summary refuses handoff access drift: {flag}")


def _assert_panel_contract(panel: dict[str, Any]) -> None:
    if panel.get("schema") != AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA:
        raise CityOpsContractError("trend summary requires prevented-claim panel schema")
    if panel.get("scope") != "internal_admin_prevented_claim_panel_only_no_customer_exposure":
        raise CityOpsContractError("trend summary panel scope drift")
    if panel.get("derived_from", {}).get("read_only") is not True:
        raise CityOpsContractError("trend summary requires read-only panel")
    if not panel.get("prevented_claim_cards"):
        raise CityOpsContractError("trend summary requires prevented-claim cards")
    if panel.get("prevented_claim_summary", {}).get(
        "claims_can_leave_prevented_state_without_named_proof"
    ) is not False:
        raise CityOpsContractError("trend summary refuses panel proof-bypass drift")
    for flag in PANEL_FALSE_FLAGS:
        if panel.get(flag) is not False:
            raise CityOpsContractError(f"trend summary refuses panel false-flag drift: {flag}")
    for flag in PANEL_ACCESS_FALSE_FLAGS:
        if panel.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"trend summary refuses panel access drift: {flag}")
    for flag, expected in PANEL_READINESS_FALSE_FLAGS.items():
        if panel.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"trend summary refuses panel readiness drift: {flag}")


def _assert_trend_summary_contract(
    summary: dict[str, Any], packet: dict[str, Any], panel: dict[str, Any]
) -> None:
    _assert_handoff_packet_contract(packet)
    _assert_panel_contract(panel)
    if summary.get("schema") != AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SCHEMA:
        raise CityOpsContractError("prevented-claim trend summary schema drift")
    if summary.get("scope") != TREND_SUMMARY_SCOPE:
        raise CityOpsContractError("prevented-claim trend summary scope drift")
    if summary.get("source_artifacts", {}).get("route_panel_handoff_packet", {}).get(
        "digest_sha256"
    ) != _stable_digest(packet):
        raise CityOpsContractError("trend summary handoff digest drift")
    if summary.get("source_artifacts", {}).get("prevented_claim_panel", {}).get(
        "digest_sha256"
    ) != _stable_digest(panel):
        raise CityOpsContractError("trend summary panel digest drift")

    safe_to_claim = summary["claim_boundaries"]["safe_to_claim"]
    do_not_claim_yet = summary["claim_boundaries"]["do_not_claim_yet"]
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)
    prevented_claims = set(panel["claim_boundary_footer"]["prevented_claims"])
    forbidden_safe = prevented_claims | set(TREND_SUMMARY_BLOCKED_CLAIMS)
    leaked = sorted(forbidden_safe & set(safe_to_claim))
    if leaked:
        raise CityOpsContractError(f"trend summary leaked blocked claims: {leaked}")
    missing_blocked = sorted(prevented_claims - set(do_not_claim_yet))
    if missing_blocked:
        raise CityOpsContractError(f"trend summary missing prevented claims: {missing_blocked}")

    rows = summary.get("trend_rows", [])
    if len(rows) != len(panel["prevented_claim_cards"]):
        raise CityOpsContractError("trend summary row count drift")
    if summary.get("trend_summary", {}).get("prevented_claim_count") != len(
        panel["claim_boundary_footer"]["prevented_claims"]
    ):
        raise CityOpsContractError("trend summary prevented count drift")
    if summary.get("trend_summary", {}).get(
        "claims_can_leave_prevented_state_without_named_proof"
    ) is not False:
        raise CityOpsContractError("trend summary proof-bypass promoted")

    for row in rows:
        for flag in [
            "may_publish_or_launch",
            "may_dispatch_or_attach_reputation",
            "may_write_live_acontext",
            "may_create_worker_copyable_doctrine",
        ]:
            if row.get(flag) is not False:
                raise CityOpsContractError(f"trend summary row promoted: {flag}")
        if not row.get("exact_next_proof_needed"):
            raise CityOpsContractError("trend summary row missing next proof")

    for flag in TREND_SUMMARY_FALSE_ACCESS_FLAGS:
        if summary.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"trend summary access flag promoted: {flag}")
    for flag, expected in TREND_SUMMARY_READINESS_FLAGS.items():
        if summary.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"trend summary readiness flag drift: {flag}")
    for flag in TREND_SUMMARY_FALSE_FLAGS:
        if summary.get(flag) is not False:
            raise CityOpsContractError(f"trend summary false flag promoted: {flag}")
    if summary.get("summary_verdict") != TREND_SUMMARY_VERDICT:
        raise CityOpsContractError("trend summary verdict drift")


def _stable_digest(payload: dict[str, Any]) -> str:
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


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"trend summary claim overlap: {overlap}")
