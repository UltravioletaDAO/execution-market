"""Handoff packet for the AAS prevented-claim trend route proof.

This module deliberately does not add another route, customer surface, approval,
delivery path, dispatch path, reputation receipt, runtime claim, GPS/metadata
release, or worker-copyable doctrine. It turns the existing internal/admin
prevented-claim trend route preflight into a compact pickup artifact so the next
operator/agent can continue from a stable boundary without promoting route mount
success into product readiness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_claim_quarantine_admin_route import (
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SCHEMA,
    PREVENTED_CLAIM_TREND_ROUTE_BLOCKED_CLAIMS,
    PREVENTED_CLAIM_TREND_ROUTE_FALSE_READINESS_FLAGS,
    ROUTE_FALSE_ACCESS_FLAGS,
    build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight,
)
from .aas_claim_quarantine_prevented_claim_trend_read_surface import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SCHEMA = (
    "city_ops.aas_claim_quarantine_prevented_claim_trend_route_handoff_packet.v1"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_FILENAME = (
    "aas_claim_quarantine_prevented_claim_trend_route_handoff_packet.json"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SAFE_CLAIM = (
    "internal_admin_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet_landed"
)

HANDOFF_ID = "execution_market.aas.claim_quarantine.prevented_claim_trend_route_handoff.2026_05_23"
HANDOFF_SCOPE = "internal_admin_prevented_claim_trend_route_pickup_only_no_more_route_expansion"
HANDOFF_VERDICT = (
    "prevented_claim_trend_route_handoff_ready_stop_route_expansion_until_human_approval_or_runtime_truth"
)

HANDOFF_BLOCKED_CLAIMS = [
    "trend_route_handoff_is_human_approval_record",
    "trend_route_handoff_approves_customer_copy",
    "trend_route_handoff_authorizes_customer_delivery",
    "trend_route_handoff_authorizes_publication",
    "trend_route_handoff_registers_public_or_catalog_route",
    "trend_route_handoff_approves_public_price_or_quote",
    "trend_route_handoff_authorizes_controlled_pilot_or_queue_launch",
    "trend_route_handoff_authorizes_dispatch",
    "trend_route_handoff_authorizes_erc8004_reputation",
    "trend_route_handoff_proves_worker_skill_dna",
    "trend_route_handoff_proves_live_acontext_or_runtime_parity",
    "trend_route_handoff_reverifies_payment_or_production",
    "trend_route_handoff_allows_exact_gps_or_raw_metadata",
    "trend_route_handoff_grants_domain_legal_regulator_or_incident_authority",
    "trend_route_handoff_creates_worker_copyable_aas_doctrine",
    "trend_route_handoff_turns_prevented_overclaim_into_launch_readiness",
]

HANDOFF_FALSE_ACCESS_FLAGS = {
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "writes_municipal_memory": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "publishes_worker_doctrine": False,
}

HANDOFF_READINESS_FLAGS = {
    "handoff_packet_landed": True,
    "source_preflight_verified": True,
    "daytime_pickup_ready": True,
    "internal_admin_route_boundary_ready": True,
    "prevented_claim_trend_route_ready_for_internal_review_only": True,
    "route_expansion_paused": True,
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


def build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
    *,
    artifact_dir: str | Path | None = None,
    route_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin trend-route handoff packet."""

    preflight = route_preflight or load_aas_claim_quarantine_prevented_claim_trend_route_preflight(
        artifact_dir=artifact_dir
    )
    _assert_route_preflight_contract(preflight)

    safe_to_claim = _dedupe(
        [
            *preflight["claim_boundaries"]["safe_to_claim"],
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM,
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *preflight["claim_boundaries"]["do_not_claim_yet"],
            *PREVENTED_CLAIM_TREND_ROUTE_BLOCKED_CLAIMS,
            *HANDOFF_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    packet = {
        "schema": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SCHEMA,
        "handoff_id": HANDOFF_ID,
        "scope": HANDOFF_SCOPE,
        "source_preflight": {
            "file": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME,
            "schema": preflight["schema"],
            "id": preflight["preflight_id"],
            "safe_claim": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM,
            "digest_sha256": _stable_digest(preflight),
            "route_path": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH,
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME
            ],
            "consumes_only": [
                INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME
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
            "publishes_worker_doctrine": False,
            "exposes_gps_or_metadata": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **HANDOFF_FALSE_ACCESS_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "handoff_cards": _handoff_cards(preflight, safe_to_claim, do_not_claim_yet),
        "coordination_patterns": _coordination_patterns(preflight),
        "recommended_next_actions": [
            "Use this packet as the single deterministic pickup artifact for the prevented-claim trend route proof.",
            "Do not add more route layers unless a new proof-preserving operator need appears.",
            "If customer exposure is desired, create a separate real human-operator decision for an exact delivery path and keep this route packet read-only.",
            "If runtime-memory work resumes, repair Acontext prerequisites first and prove exactly one live write/retrieve parity pass before claiming runtime readiness.",
        ],
        "not_next_actions": [
            "Do not infer approval, delivery, publication, catalog readiness, pilot readiness, dispatch, reputation, worker Skill DNA, live Acontext parity, payment/production proof, GPS/raw metadata release, legal authority, or worker-copyable doctrine from this packet.",
            "Do not convert prevented-claim trends into customer copy or public launch messaging.",
            "Do not reopen raw transcripts, raw worker uploads, unreviewed memory, or private operator context to explain this handoff.",
        ],
        "readiness": dict(HANDOFF_READINESS_FLAGS),
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
        },
        "handoff_verdict": HANDOFF_VERDICT,
    }
    _assert_handoff_packet_contract(packet, preflight)
    return packet


def load_aas_claim_quarantine_prevented_claim_trend_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted route preflight or rebuild it deterministically."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    path = base_dir / INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME
    if path.exists():
        preflight = json.loads(path.read_text(encoding="utf-8"))
    else:
        preflight = build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight(
            artifact_dir=base_dir
        )
    _assert_route_preflight_contract(preflight)
    return preflight


def load_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted trend-route handoff packet fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    path = base_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    preflight = load_aas_claim_quarantine_prevented_claim_trend_route_preflight(
        artifact_dir=base_dir
    )
    _assert_handoff_packet_contract(packet, preflight)
    return packet


def write_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic trend-route handoff packet fixture."""

    packet = build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _handoff_cards(
    preflight: dict[str, Any], safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> list[dict[str, Any]]:
    return [
        {
            "card": "source_preflight",
            "preflight_id": preflight["preflight_id"],
            "verdict": preflight["preflight_verdict"],
            "route_path": preflight["route_contract"]["path"],
            "mounted_route_count": preflight["mount_contract"]["mounted_route_count"],
        },
        {
            "card": "internal_admin_route",
            "values": [
                {
                    "route_key": route["route_key"],
                    "path": route["path"],
                    "methods": route["methods"],
                    "public_or_customer_visible": route["public_or_customer_visible"],
                    "dispatch_enabled": route["dispatch_enabled"],
                    "emits_reputation_receipts": route["emits_reputation_receipts"],
                }
                for route in preflight["mounted_routes"]
            ],
        },
        {"card": "safe_to_claim", "values": safe_to_claim},
        {"card": "do_not_claim_yet", "values": do_not_claim_yet},
        {
            "card": "next_smallest_proof",
            "values": [
                "real_human_operator_delivery_path_decision_if_customer_exposure_is_desired",
                "acontext_prerequisite_repair_then_one_live_write_retrieve_parity_pass_if_runtime_work_resumes",
                "otherwise_stop_route_expansion_and keep_internal_admin_claim_quarantine_packets_as_pickup_state",
            ],
        },
    ]


def _coordination_patterns(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pattern": "prevented_overclaim_as_roadmap_signal",
            "status": "active",
            "why_it_scales": (
                "blocked claims become explicit next-proof slots instead of silently "
                "leaking into launch language"
            ),
            "evidence": preflight["claim_boundaries"]["do_not_claim_yet"],
        },
        {
            "pattern": "admin_route_as_pass_through_not_product_launch",
            "status": "guardrail",
            "why_it_scales": (
                "the route is useful for operators because it returns a reviewed persisted "
                "artifact as-is, not because it creates customer/public readiness"
            ),
            "evidence": preflight["mounted_routes"][0]["path"],
        },
        {
            "pattern": "route_expansion_pause",
            "status": "recommended",
            "why_it_scales": (
                "the next product truth is human approval or runtime parity, not another "
                "wrapper around the same route proof"
            ),
            "evidence": "route_expansion_paused=true",
        },
    ]


def _assert_route_preflight_contract(preflight: dict[str, Any]) -> None:
    if preflight.get("schema") != (
        INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SCHEMA
    ):
        raise CityOpsContractError("trend route handoff requires route preflight schema")
    if preflight.get("preflight_id") != (
        "aas_claim_quarantine_prevented_claim_trend_route_preflight:internal_admin:v1"
    ):
        raise CityOpsContractError("trend route handoff preflight id drift")

    derived_from = preflight.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("trend route handoff requires read-only source preflight")
    for flag in [
        "semantic_reinterpretation_performed",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"trend route handoff refuses source drift: {flag}")

    route_contract = preflight.get("route_contract", {})
    if route_contract.get("path") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH:
        raise CityOpsContractError("trend route handoff path drift")
    if route_contract.get("method") != "GET":
        raise CityOpsContractError("trend route handoff method drift")
    if route_contract.get("returns_payload_as_is") is not True:
        raise CityOpsContractError("trend route handoff requires pass-through response")

    if preflight.get("mount_contract", {}).get("mounted_route_count") != 1:
        raise CityOpsContractError("trend route handoff route-count drift")
    if len(preflight.get("mounted_routes", [])) != 1:
        raise CityOpsContractError("trend route handoff requires one mounted route")
    mounted = preflight["mounted_routes"][0]
    if mounted.get("path") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH:
        raise CityOpsContractError("trend route handoff mounted path drift")
    if mounted.get("methods") != ["GET"]:
        raise CityOpsContractError("trend route handoff mounted method drift")
    if "verify_internal_admin_key" not in mounted.get("dependency_names", []):
        raise CityOpsContractError("trend route handoff admin auth missing")
    for flag in [
        "public_or_customer_visible",
        "writes_live_acontext",
        "dispatch_enabled",
        "emits_reputation_receipts",
    ]:
        if mounted.get(flag) is not False:
            raise CityOpsContractError(f"trend route handoff refuses route drift: {flag}")

    access_policy = preflight.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("trend route handoff audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("trend route handoff requires admin context")
    for flag, expected in ROUTE_FALSE_ACCESS_FLAGS.items():
        if access_policy.get(flag) is not expected:
            raise CityOpsContractError(f"trend route handoff refuses access drift: {flag}")
    for flag, expected in PREVENTED_CLAIM_TREND_ROUTE_FALSE_READINESS_FLAGS.items():
        if preflight.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"trend route handoff refuses readiness drift: {flag}"
            )

    _assert_no_claim_overlap(
        preflight.get("claim_boundaries", {}).get("safe_to_claim", []),
        preflight.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_handoff_packet_contract(
    packet: dict[str, Any], preflight: dict[str, Any]
) -> None:
    if packet.get("schema") != (
        AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SCHEMA
    ):
        raise CityOpsContractError("invalid trend route handoff packet schema")
    if packet.get("source_preflight", {}).get("id") != preflight.get("preflight_id"):
        raise CityOpsContractError("trend route handoff source preflight mismatch")
    if packet.get("source_preflight", {}).get("digest_sha256") != _stable_digest(preflight):
        raise CityOpsContractError("trend route handoff source digest drift")

    derived_from = packet.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("trend route handoff packet must be read-only")
    if derived_from.get("consumes_only") != [
        INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME
    ]:
        raise CityOpsContractError("trend route handoff consumes unexpected artifacts")
    for flag in [
        "raw_conversation_reopened",
        "raw_worker_evidence_reopened",
        "unreviewed_memory_reopened",
        "private_operator_context_reopened",
        "semantic_reinterpretation_performed",
        "adds_route",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"trend route handoff refuses derived drift: {flag}")

    for flag, expected in HANDOFF_FALSE_ACCESS_FLAGS.items():
        if packet.get("access_policy", {}).get(flag) is not expected:
            raise CityOpsContractError(f"trend route handoff refuses access drift: {flag}")
    for flag, expected in HANDOFF_READINESS_FLAGS.items():
        if packet.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"trend route handoff refuses readiness drift: {flag}"
            )

    cards = packet.get("handoff_cards", [])
    if [card.get("card") for card in cards[2:4]] != ["safe_to_claim", "do_not_claim_yet"]:
        raise CityOpsContractError("trend route handoff requires adjacent claim cards")
    if cards[2].get("values") != packet["claim_boundaries"]["safe_to_claim"]:
        raise CityOpsContractError("trend route handoff safe claim card drift")
    if cards[3].get("values") != packet["claim_boundaries"]["do_not_claim_yet"]:
        raise CityOpsContractError("trend route handoff blocked claim card drift")
    _assert_no_claim_overlap(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _assert_no_claim_overlap(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"trend route handoff refuses claim overlap: {overlap}")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
