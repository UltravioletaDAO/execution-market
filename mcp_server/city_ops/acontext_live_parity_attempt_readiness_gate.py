"""Fail-closed readiness gate for a future live Acontext parity attempt.

The blocker-delta read surface is useful for humans, but it should not be
mistaken for authorization to perform a live write/retrieve run.  This module
turns that read surface into an explicit attempt gate: the only current verdict
is "blocked until prerequisites are cleared and preflight is re-run".

It never writes to Acontext, never retrieves from Acontext, never registers a
route, and never promotes runtime, customer, dispatch, reputation, GPS/raw
metadata, payment, production, or worker-doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_live_preflight_blocker_delta_read_surface import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA,
    SURFACE_BLOCKED_CLAIMS,
    load_acontext_live_preflight_blocker_delta_read_surface,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA = (
    "city_ops.acontext_live_parity_attempt_readiness_gate.v1"
)
ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME = (
    "acontext_live_parity_attempt_readiness_gate.json"
)
ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM = (
    "admin_acontext_live_parity_attempt_gate_landed"
)

GATE_BLOCKED_CLAIMS = [
    *SURFACE_BLOCKED_CLAIMS,
    "acontext_live_write_retrieve_attempt_started",
    "acontext_live_write_retrieve_attempt_completed",
    "acontext_live_parity_attempt_authorized_by_gate",
    "acontext_prerequisites_fully_cleared_by_gate",
    "live_acontext_sink_ready_by_gate",
    "runtime_parity_proven_by_gate",
    "live_memory_transport_swap_ready",
    "customer_visible_aas_packaging_ready_by_gate",
    "customer_copy_ready_by_gate",
    "public_route_ready_by_gate",
    "operator_queue_launch_ready_by_gate",
    "autonomous_city_dispatch_ready_by_gate",
    "erc8004_reputation_ready_by_gate",
    "payment_coverage_reverified_by_gate",
    "production_infrastructure_reverified_by_gate",
    "exact_gps_or_metadata_exposure_allowed_by_gate",
    "worker_copyable_municipal_doctrine_ready_by_gate",
]

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "gate_promotes_live_readiness",
    "attempt_allowed",
    "ready_to_attempt_live_transport",
    "acontext_sink_ready",
    "session_rebuild_ready",
    "runtime_parity_proven",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "live_memory_transport_swap_ready",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "autonomous_dispatch_ready",
    "operator_queue_launch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_gate",
    "production_infrastructure_reverified_by_this_gate",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_acontext_live_parity_attempt_readiness_gate(
    *,
    artifact_dir: str | Path | None = None,
    blocker_surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic fail-closed gate from the blocker read surface."""

    surface = blocker_surface or load_acontext_live_preflight_blocker_delta_read_surface(
        artifact_dir=artifact_dir
    )
    _assert_source_surface(surface)

    safe_to_claim = _dedupe(
        [
            *surface["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM,
            ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *surface["claim_boundaries"]["do_not_claim_yet"],
            *SURFACE_BLOCKED_CLAIMS,
            *GATE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    gate = {
        "schema": ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA,
        "gate_id": f"acontext_live_parity_attempt_gate:{surface['surface_id']}",
        "source_surface_id": surface["surface_id"],
        "source_delta_id": surface["source_delta_id"],
        "source_preflight_id": surface["source_preflight_id"],
        "proof_anchor_id": surface["proof_anchor_id"],
        "coordination_session_id": surface["coordination_session_id"],
        "compact_decision_id": surface["compact_decision_id"],
        "review_packet_id": surface["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME
            ],
            "consumes_only": [
                ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME
            ],
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
            "network_route_registered": False,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "dispatch_enabled": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "attempt_policy": _attempt_policy(surface),
        "readiness": _gate_readiness(surface),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_decision_cards": _operator_decision_cards(surface),
        "source_blocker_summary": surface["blocker_delta_summary"],
        "source_next_smallest_proof": list(surface["next_smallest_proof"]),
        "gate_verdict": "live_parity_attempt_blocked_prerequisites_missing",
        "operator_instruction": (
            "Do not run a live Acontext write/retrieve attempt from this gate. "
            "Clear the remaining SDK/API/dashboard blockers, re-run the preflight, "
            "then build a new gate from the resulting read surface."
        ),
    }
    _assert_gate_conservative(gate, surface)
    return gate


def write_acontext_live_parity_attempt_readiness_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic fail-closed Acontext parity-attempt gate."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    gate = build_acontext_live_parity_attempt_readiness_gate(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_live_parity_attempt_readiness_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted fail-closed Acontext parity-attempt gate."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        gate = json.load(fh)
    surface = load_acontext_live_preflight_blocker_delta_read_surface(
        artifact_dir=base_dir
    )
    _assert_gate_conservative(gate, surface)
    return gate


def _attempt_policy(surface: dict[str, Any]) -> dict[str, Any]:
    summary = surface["blocker_delta_summary"]
    remaining_blockers = list(summary["remaining_blockers"])
    return {
        "attempt_allowed": False,
        "attempt_status": "blocked_until_prerequisites_clear_and_preflight_is_rerun",
        "blocked_by": remaining_blockers,
        "cleared_but_not_authorizing": list(summary["cleared_blockers"]),
        "may_run_preflight_only": True,
        "may_run_live_write": False,
        "may_run_live_retrieve": False,
        "may_claim_runtime_parity": False,
        "must_rebuild_gate_after_preflight": True,
        "allowed_next_action_classes": [
            "install_or_mount_acontext_python_sdk",
            "start_or_reach_local_acontext_api",
            "start_or_reach_local_acontext_dashboard",
            "rerun_preflight_without_live_write_or_retrieve",
        ],
        "forbidden_next_action_classes": [
            "live_acontext_write",
            "live_acontext_retrieve",
            "customer_copy_generation",
            "public_route_mount",
            "dispatch_or_queue_launch",
            "reputation_receipt_attachment",
            "payment_or_production_claim_without_fresh_probe",
            "exact_gps_or_raw_metadata_release",
            "worker_copyable_municipal_doctrine",
        ],
    }


def _gate_readiness(surface: dict[str, Any]) -> dict[str, Any]:
    source = surface["readiness"]
    return {
        "gate_landed": True,
        "gate_promotes_live_readiness": False,
        "source_surface_landed": bool(source["surface_landed"]),
        "docker_available": bool(source["docker_available"]),
        "acontext_python_sdk_available": bool(source["acontext_python_sdk_available"]),
        "local_acontext_api_reachable": bool(source["local_acontext_api_reachable"]),
        "local_acontext_dashboard_reachable": bool(
            source["local_acontext_dashboard_reachable"]
        ),
        "attempt_allowed": False,
        "ready_to_attempt_live_transport": False,
        "acontext_sink_ready": False,
        "session_rebuild_ready": False,
        "runtime_parity_proven": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "live_memory_transport_swap_ready": False,
        "customer_visible_aas_packaging_ready": False,
        "public_route_ready": False,
        "autonomous_dispatch_ready": False,
        "operator_queue_launch_ready": False,
        "erc8004_reputation_ready": False,
        "payment_coverage_reverified_by_this_gate": False,
        "production_infrastructure_reverified_by_this_gate": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
    }


def _operator_decision_cards(surface: dict[str, Any]) -> list[dict[str, Any]]:
    summary = surface["blocker_delta_summary"]
    return [
        {
            "card": "current_verdict",
            "status": "blocked",
            "decision": "do_not_attempt_live_write_retrieve",
            "reason": "remaining_prerequisites_present",
            "remaining_blockers": list(summary["remaining_blockers"]),
            "cleared_blockers": list(summary["cleared_blockers"]),
            "authorizes_live_write": False,
            "authorizes_live_retrieve": False,
        },
        {
            "card": "allowed_next_work",
            "status": "preflight_prerequisite_work_only",
            "steps": [
                "clear remaining Acontext SDK/API/dashboard prerequisites",
                "rerun the live-preflight probe without performing writes or retrievals",
                "rebuild blocker delta, read surface, and this gate from the new preflight result",
            ],
            "authorizes_customer_or_worker_surface": False,
        },
        {
            "card": "claims_to_keep_sticky",
            "status": "blocked_claims_must_travel_with_every_summary",
            "sticky_claims": [
                "runtime_parity_proven",
                "live_acontext_write_completed",
                "live_acontext_retrieval_completed",
                "customer_visible_aas_packaging_ready",
                "public_route_ready",
                "dispatch_ready",
                "erc8004_reputation_ready",
                "exact_gps_or_metadata_exposure_allowed",
                "worker_copyable_municipal_doctrine_ready",
            ],
        },
    ]


def _assert_source_surface(surface: dict[str, Any]) -> None:
    if surface.get("schema") != ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("Acontext parity attempt gate requires blocker read surface")
    readiness = surface.get("readiness") or {}
    if readiness.get("surface_landed") is not True:
        raise CityOpsContractError("Acontext parity attempt gate requires landed source surface")
    for flag in [
        "ready_to_attempt_live_transport",
        "acontext_sink_ready",
        "runtime_parity_proven",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"Acontext parity attempt gate refuses ready source: {flag}")
    summary = surface.get("blocker_delta_summary") or {}
    if summary.get("may_attempt_live_parity") is not False:
        raise CityOpsContractError("Acontext parity attempt gate requires blocked source summary")
    if not summary.get("remaining_blockers"):
        raise CityOpsContractError("Acontext parity attempt gate requires remaining blockers")
    forbidden_safe = set(surface.get("claim_boundaries", {}).get("safe_to_claim", [])) & set(
        GATE_BLOCKED_CLAIMS
    )
    if forbidden_safe:
        raise CityOpsContractError(
            f"Acontext parity attempt gate source has blocked safe claims: {sorted(forbidden_safe)}"
        )


def _assert_gate_conservative(gate: dict[str, Any], surface: dict[str, Any]) -> None:
    _assert_source_surface(surface)
    if gate.get("schema") != ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA:
        raise CityOpsContractError("Acontext parity attempt gate schema drift")
    if gate.get("source_surface_id") != surface["surface_id"]:
        raise CityOpsContractError("Acontext parity attempt gate source surface drift")
    if gate.get("gate_verdict") != "live_parity_attempt_blocked_prerequisites_missing":
        raise CityOpsContractError("Acontext parity attempt gate verdict drift")

    derived = gate.get("derived_from") or {}
    if derived.get("consumes_only") != [
        ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME
    ]:
        raise CityOpsContractError("Acontext parity attempt gate source artifact drift")
    for flag in [
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_customer_copy",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        if derived.get(flag) is not False:
            raise CityOpsContractError(f"Acontext parity attempt gate derived drift: {flag}")

    access = gate.get("access_policy") or {}
    for flag in _FALSE_ACCESS_FLAGS:
        if access.get(flag) is not False:
            raise CityOpsContractError(f"Acontext parity attempt gate access drift: {flag}")

    readiness = gate.get("readiness") or {}
    if readiness.get("gate_landed") is not True:
        raise CityOpsContractError("Acontext parity attempt gate landed flag missing")
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Acontext parity attempt gate readiness promoted: {flag}"
            )

    policy = gate.get("attempt_policy") or {}
    if policy.get("attempt_allowed") is not False:
        raise CityOpsContractError("Acontext parity attempt gate allowed live attempt")
    if policy.get("may_run_preflight_only") is not True:
        raise CityOpsContractError("Acontext parity attempt gate must allow preflight-only work")
    for flag in ["may_run_live_write", "may_run_live_retrieve", "may_claim_runtime_parity"]:
        if policy.get(flag) is not False:
            raise CityOpsContractError(f"Acontext parity attempt gate policy promoted: {flag}")
    if policy.get("blocked_by") != surface["blocker_delta_summary"]["remaining_blockers"]:
        raise CityOpsContractError("Acontext parity attempt gate blocker drift")

    boundaries = gate.get("claim_boundaries") or {}
    safe = boundaries.get("safe_to_claim") or []
    blocked = boundaries.get("do_not_claim_yet") or []
    _assert_claim_boundaries(safe, blocked)
    if ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("Acontext parity attempt gate safe claim missing")
    missing = set(GATE_BLOCKED_CLAIMS) - set(blocked)
    if missing:
        raise CityOpsContractError(
            f"Acontext parity attempt gate missing blocked claims: {sorted(missing)}"
        )
    for card in gate.get("operator_decision_cards") or []:
        if card.get("authorizes_live_write") is True:
            raise CityOpsContractError("Acontext parity attempt gate card authorized live write")
        if card.get("authorizes_live_retrieve") is True:
            raise CityOpsContractError("Acontext parity attempt gate card authorized live retrieve")
        if card.get("authorizes_customer_or_worker_surface") is True:
            raise CityOpsContractError("Acontext parity attempt gate card authorized customer/worker surface")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"Acontext parity attempt gate claim overlap: {sorted(overlap)}"
        )
    forbidden_safe = set(safe_to_claim) & set(GATE_BLOCKED_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"Acontext parity attempt gate has blocked safe claims: {sorted(forbidden_safe)}"
        )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
