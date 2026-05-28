"""Compact handoff packet for the AAS system-integration flywheel route proof.

This module deliberately stops at the internal/admin route boundary landed by
``aas_system_integration_flywheel_admin_route``. It creates no additional route,
customer copy, public/catalog surface, dispatch path, reputation receipt, live
Acontext/runtime claim, payment or production reverification, GPS/raw metadata
release, authority claim, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_system_integration_flywheel_admin_route import (
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SCHEMA,
    ROUTE_BLOCKED_CLAIMS,
    ROUTE_FALSE_ACCESS_FLAGS,
    ROUTE_READINESS_FLAGS,
    _assert_internal_admin_aas_system_integration_flywheel_route_preflight,
    build_internal_admin_aas_system_integration_flywheel_route_preflight,
    load_internal_admin_aas_system_integration_flywheel_read_surface,
)
from .aas_system_integration_flywheel_read_surface import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SCHEMA = (
    "city_ops.aas_system_integration_flywheel_route_handoff_packet.v1"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME = (
    "aas_system_integration_flywheel_route_handoff_packet.json"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM = (
    "internal_admin_aas_system_integration_flywheel_route_handoff_packet_landed"
)

HANDOFF_ID = "execution_market.aas.system_integration_flywheel.route_handoff.2026_05_28"
HANDOFF_SCOPE = "internal_admin_system_integration_route_pickup_only_no_more_route_expansion"
HANDOFF_VERDICT = (
    "system_integration_flywheel_route_handoff_ready_stop_route_expansion_until_runtime_or_operator_truth"
)

HANDOFF_BLOCKED_CLAIMS = [
    "system_integration_flywheel_route_handoff_is_customer_or_public_surface",
    "system_integration_flywheel_route_handoff_authorizes_customer_copy",
    "system_integration_flywheel_route_handoff_authorizes_customer_delivery",
    "system_integration_flywheel_route_handoff_authorizes_publication",
    "system_integration_flywheel_route_handoff_registers_catalog_or_public_route",
    "system_integration_flywheel_route_handoff_authorizes_pricing_or_customer_quote",
    "system_integration_flywheel_route_handoff_authorizes_queue_launch_or_dispatch",
    "system_integration_flywheel_route_handoff_authorizes_erc8004_reputation",
    "system_integration_flywheel_route_handoff_proves_worker_skill_dna",
    "system_integration_flywheel_route_handoff_proves_live_acontext_or_runtime_parity",
    "system_integration_flywheel_route_handoff_reverifies_payment_or_production",
    "system_integration_flywheel_route_handoff_allows_exact_gps_or_raw_metadata",
    "system_integration_flywheel_route_handoff_grants_legal_regulator_notarial_or_custody_authority",
    "system_integration_flywheel_route_handoff_grants_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
    "system_integration_flywheel_route_handoff_creates_worker_copyable_doctrine",
    "system_integration_flywheel_route_handoff_turns_route_preflight_into_launch_readiness",
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
    "route_expansion_paused": True,
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "public_or_catalog_route_ready": False,
    "pricing_or_customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "live_acontext_runtime_parity_ready": False,
    "payment_or_production_reverified": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "exact_gps_or_raw_metadata_release_ready": False,
    "domain_authority_ready": False,
    "worker_copyable_doctrine_ready": False,
}


def build_aas_system_integration_flywheel_route_handoff_packet(
    *,
    artifact_dir: str | Path | None = None,
    route_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin route handoff packet."""

    preflight = route_preflight or load_aas_system_integration_flywheel_route_preflight(
        artifact_dir=artifact_dir
    )
    _assert_route_preflight_contract(preflight, artifact_dir=artifact_dir)

    safe_to_claim = _dedupe(
        [
            *preflight["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
            INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *preflight["claim_boundaries"]["do_not_claim_yet"],
            *ROUTE_BLOCKED_CLAIMS,
            *HANDOFF_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    packet = {
        "schema": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SCHEMA,
        "handoff_id": HANDOFF_ID,
        "scope": HANDOFF_SCOPE,
        "source_preflight": {
            "file": INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME,
            "schema": preflight["schema"],
            "id": preflight["preflight_id"],
            "safe_claim": INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM,
            "digest_sha256": _stable_digest(preflight),
            "route_path": INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH,
            "response_source": AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
            ],
            "consumes_only": [
                INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
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
            "Use this packet as the single daytime pickup artifact for the system-integration flywheel route proof.",
            "Do not add more route layers unless a new proof-preserving internal/admin need is explicit.",
            "If runtime-memory work resumes, prove Docker/Acontext prerequisites first, then attempt exactly one live write/retrieve parity pass.",
            "If customer exposure is desired, create a separate real human-operator decision artifact for one exact boundary and delivery path.",
        ],
        "not_next_actions": [
            "Do not infer customer copy, delivery, publication, catalog, pricing, queue launch, dispatch, reputation, Worker Skill DNA, live Acontext parity, payment/production proof, GPS/raw metadata release, authority, or worker-copyable doctrine from this packet.",
            "Do not reopen raw transcripts, raw worker uploads, unreviewed memory, or private operator context to explain this handoff.",
            "Do not turn the internal/admin route proof into launch messaging.",
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


def load_aas_system_integration_flywheel_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted route preflight or rebuild it deterministically."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
    if path.exists():
        preflight = json.loads(path.read_text(encoding="utf-8"))
    else:
        preflight = build_internal_admin_aas_system_integration_flywheel_route_preflight(
            artifact_dir=base_dir
        )
    _assert_route_preflight_contract(preflight, artifact_dir=base_dir)
    return preflight


def load_aas_system_integration_flywheel_route_handoff_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted route handoff packet fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    preflight = load_aas_system_integration_flywheel_route_preflight(artifact_dir=base_dir)
    _assert_handoff_packet_contract(packet, preflight)
    return packet


def write_aas_system_integration_flywheel_route_handoff_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic route handoff packet fixture."""

    packet = build_aas_system_integration_flywheel_route_handoff_packet(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _handoff_cards(
    preflight: dict[str, Any], safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> list[dict[str, Any]]:
    return [
        {
            "card": "source_route_preflight",
            "status": "verified_internal_admin_pass_through_only",
            "route_path": preflight["route_contract"]["path"],
            "response_source": preflight["route_contract"]["required_response_source"],
            "returns_payload_as_is": preflight["route_contract"]["returns_payload_as_is"],
            "admin_auth_boundary_proven": preflight["readiness"]["admin_auth_boundary_proven"],
        },
        {
            "card": "route_expansion_stop",
            "status": "stop_after_handoff_packet",
            "route_expansion_paused": True,
            "adds_route": False,
            "customer_visible": False,
            "public_or_catalog_route_ready": False,
            "dispatch_ready": False,
            "live_acontext_runtime_parity_ready": False,
        },
        {
            "card": "safe_to_claim",
            "status": "internal_admin_only",
            "claims": safe_to_claim,
        },
        {
            "card": "do_not_claim_yet",
            "status": "sticky_blocked_claims",
            "claims": do_not_claim_yet,
        },
    ]


def _coordination_patterns(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pattern": "route_preflight_to_handoff_without_promotion",
            "input": preflight["preflight_id"],
            "output": HANDOFF_ID,
            "invariant": "route mount success stays internal/admin and does not become launch readiness",
        },
        {
            "pattern": "four_id_surface_pickup",
            "input": preflight["source_surface_id"],
            "output": "daytime_agent_can_resume_from_digest_and_route_contract",
            "invariant": "no raw transcript, private context, or unreviewed memory replay required",
        },
        {
            "pattern": "runtime_truth_requires_separate_gate",
            "input": "acontext_runtime_memory_prerequisites",
            "output": "exactly_one_future_live_write_retrieve_parity_attempt_if_prerequisites_are_real",
            "invariant": "this handoff does not write or retrieve live Acontext",
        },
    ]


def _assert_route_preflight_contract(
    preflight: dict[str, Any], *, artifact_dir: str | Path | None = None
) -> None:
    if preflight.get("schema") != INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SCHEMA:
        raise CityOpsContractError("invalid system integration flywheel route preflight schema")
    surface = load_internal_admin_aas_system_integration_flywheel_read_surface(
        artifact_dir=artifact_dir
    )
    _assert_internal_admin_aas_system_integration_flywheel_route_preflight(
        preflight, surface
    )
    for flag, expected in ROUTE_FALSE_ACCESS_FLAGS.items():
        if preflight.get("access_policy", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"system integration flywheel route handoff refuses access drift: {flag}"
            )
    for flag, expected in ROUTE_READINESS_FLAGS.items():
        if preflight.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"system integration flywheel route handoff refuses readiness drift: {flag}"
            )


def _assert_handoff_packet_contract(
    packet: dict[str, Any], preflight: dict[str, Any]
) -> None:
    if packet.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SCHEMA:
        raise CityOpsContractError("invalid system integration flywheel route handoff schema")
    if packet.get("source_preflight", {}).get("id") != preflight.get("preflight_id"):
        raise CityOpsContractError("system integration flywheel route handoff source drift")
    derived = packet.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("system integration flywheel route handoff must stay read-only")
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
        if derived.get(flag) is not False:
            raise CityOpsContractError(
                f"system integration flywheel route handoff derived drift: {flag}"
            )
    access_policy = packet.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("system integration flywheel route handoff audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("system integration flywheel route handoff requires admin context")
    for flag, expected in HANDOFF_FALSE_ACCESS_FLAGS.items():
        if access_policy.get(flag) is not expected:
            raise CityOpsContractError(
                f"system integration flywheel route handoff access drift: {flag}"
            )
    for flag, expected in HANDOFF_READINESS_FLAGS.items():
        if packet.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"system integration flywheel route handoff readiness drift: {flag}"
            )
    safe_to_claim = packet.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = packet.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("system integration flywheel route handoff missing safe claim")
    missing = sorted(set(HANDOFF_BLOCKED_CLAIMS) - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(
            f"system integration flywheel route handoff missing blocked claims: {missing}"
        )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"system integration flywheel route handoff claim overlap: {overlap}"
        )


def _stable_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
