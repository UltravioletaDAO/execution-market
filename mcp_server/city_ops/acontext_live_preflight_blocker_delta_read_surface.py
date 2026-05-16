"""Internal/admin read surface for the Acontext preflight blocker delta.

The blocker delta records partial prerequisite progress toward a future live
Acontext write/retrieve parity pass.  This module renders that delta as
operator-readable cards without changing authority: no live Acontext sink is
written or read, no public/customer route is registered, no dispatch path is
enabled, and no runtime parity claim is promoted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_live_preflight_blocker_delta import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SCHEMA,
    BLOCKER_DELTA_BLOCKED_CLAIMS,
    load_acontext_live_preflight_blocker_delta,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA = (
    "city_ops.acontext_live_preflight_blocker_delta_read_surface.v1"
)
ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME = (
    "acontext_live_preflight_blocker_delta_read_surface.json"
)
ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM = (
    "admin_acontext_blocker_delta_surface_landed"
)

SURFACE_BLOCKED_CLAIMS = [
    "acontext_prerequisites_fully_cleared",
    "acontext_live_parity_attempt_authorized",
    "live_acontext_sink_ready",
    "runtime_parity_proven",
    "live_acontext_write_completed",
    "live_acontext_retrieval_completed",
    "session_rebuild_ready",
    "customer_visible_aas_packaging_ready",
    "customer_copy_ready",
    "public_route_ready",
    "autonomous_city_dispatch_ready",
    "operator_queue_launch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_surface",
    "production_infrastructure_reverified_by_this_surface",
    "exact_gps_or_metadata_exposure_allowed",
    "worker_copyable_municipal_doctrine_ready",
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
    "surface_promotes_live_readiness",
    "ready_to_attempt_live_transport",
    "acontext_sink_ready",
    "session_rebuild_ready",
    "runtime_parity_proven",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "autonomous_dispatch_ready",
    "operator_queue_launch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_surface",
    "production_infrastructure_reverified_by_this_surface",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_acontext_live_preflight_blocker_delta_read_surface(
    *,
    artifact_dir: str | Path | None = None,
    delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic internal/admin cards from a blocked Acontext delta."""

    source_delta = delta or load_acontext_live_preflight_blocker_delta(
        artifact_dir=artifact_dir
    )
    _assert_source_delta_mountable(source_delta)

    safe_to_claim = _dedupe(
        [
            *source_delta["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM,
            ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_delta["claim_boundaries"]["do_not_claim_yet"],
            *BLOCKER_DELTA_BLOCKED_CLAIMS,
            *SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    surface = {
        "schema": ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA,
        "surface_id": f"acontext_blocker_delta_read_surface:{source_delta['delta_id']}",
        "source_delta_id": source_delta["delta_id"],
        "source_preflight_id": source_delta["source_preflight_id"],
        "proof_anchor_id": source_delta["proof_anchor_id"],
        "coordination_session_id": source_delta["coordination_session_id"],
        "compact_decision_id": source_delta["compact_decision_id"],
        "review_packet_id": source_delta["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME],
            "consumes_only": [ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME],
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
        "render_contract": {
            "render_status": "internal_admin_acontext_blocker_delta_surface_landed_not_route",
            "suggested_internal_path": "/internal/admin/city-ops/acontext-preflight-blockers",
            "network_route_registered": False,
            "layout": "four_id_header_blocker_cards_next_prerequisite_sticky_claim_footer",
            "allowed_interpretation": "pass_through_blocker_delta_fields_only",
            "response_fields": [
                "four_id_session_header",
                "blocker_delta_summary",
                "prerequisite_status_cards",
                "operator_next_action_cards",
                "claim_boundary_footer",
                "readiness",
            ],
        },
        "readiness": _surface_readiness(source_delta),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "four_id_session_header": _four_id_session_header(source_delta),
        "blocker_delta_summary": _blocker_delta_summary(source_delta),
        "prerequisite_status_cards": _prerequisite_status_cards(source_delta),
        "operator_next_action_cards": _operator_next_action_cards(source_delta),
        "claim_boundary_footer": _claim_boundary_footer(safe_to_claim, do_not_claim_yet),
        "source_verdict": source_delta["delta_verdict"],
        "surface_verdict": _surface_verdict(source_delta),
        "next_smallest_proof": list(source_delta["next_smallest_proof"]),
    }
    _assert_surface_conservative(surface, source_delta)
    return surface


def write_acontext_live_preflight_blocker_delta_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic internal/admin blocker-delta read surface."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    surface = build_acontext_live_preflight_blocker_delta_read_surface(
        artifact_dir=base_dir
    )
    path = base_dir / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_live_preflight_blocker_delta_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted internal/admin blocker-delta surface."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (
        base_dir / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_FILENAME
    ).open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    delta = load_acontext_live_preflight_blocker_delta(artifact_dir=base_dir)
    _assert_surface_conservative(surface, delta)
    return surface


def _surface_readiness(delta: dict[str, Any]) -> dict[str, Any]:
    source_readiness = delta["readiness"]
    return {
        "surface_landed": True,
        "surface_promotes_live_readiness": False,
        "source_blocker_delta_landed": bool(source_readiness["blocker_delta_landed"]),
        "docker_available": bool(source_readiness["docker_available"]),
        "acontext_python_sdk_available": bool(
            source_readiness["acontext_python_sdk_available"]
        ),
        "local_acontext_api_reachable": bool(
            source_readiness["local_acontext_api_reachable"]
        ),
        "local_acontext_dashboard_reachable": bool(
            source_readiness["local_acontext_dashboard_reachable"]
        ),
        "ready_to_attempt_live_transport": False,
        "acontext_sink_ready": False,
        "session_rebuild_ready": False,
        "runtime_parity_proven": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "customer_visible_aas_packaging_ready": False,
        "public_route_ready": False,
        "autonomous_dispatch_ready": False,
        "operator_queue_launch_ready": False,
        "erc8004_reputation_ready": False,
        "payment_coverage_reverified_by_this_surface": False,
        "production_infrastructure_reverified_by_this_surface": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
    }


def _four_id_session_header(delta: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof_anchor_id": delta["proof_anchor_id"],
        "coordination_session_id": delta["coordination_session_id"],
        "compact_decision_id": delta["compact_decision_id"],
        "review_packet_id": delta["review_packet_id"],
        "normal_handoff_rule": (
            "Use persisted IDs and blocker cards; do not reopen raw transcripts or "
            "treat this as live Acontext parity."
        ),
    }


def _blocker_delta_summary(delta: dict[str, Any]) -> dict[str, Any]:
    return {
        "baseline_blockers": list(delta["baseline_blockers"]),
        "current_blockers": list(delta["current_blockers"]),
        "cleared_blockers": list(delta["cleared_blockers"]),
        "remaining_blockers": list(delta["remaining_blockers"]),
        "newly_blocked": list(delta["newly_blocked"]),
        "operator_note": delta["operator_note"],
        "may_attempt_live_parity": False,
        "may_claim_runtime_parity": False,
    }


def _prerequisite_status_cards(delta: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for card in delta["prerequisite_cards"]:
        status = card["status"]
        cards.append(
            {
                "prerequisite": card["prerequisite"],
                "status": status,
                "badge": f"prerequisite_{status}_not_authority",
                "required_for_live_parity": bool(card["required_for_live_parity"]),
                "authorizes_live_write": False,
                "operator_copy": _operator_copy_for_prerequisite(card["prerequisite"], status),
            }
        )
    return cards


def _operator_next_action_cards(delta: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "step_number": index + 1,
            "action": action,
            "must_rerun_read_only_preflight": index == len(delta["next_smallest_proof"]) - 1,
            "authorizes_live_write": False,
        }
        for index, action in enumerate(delta["next_smallest_proof"])
    ]


def _operator_copy_for_prerequisite(prerequisite: str, status: str) -> str:
    if status == "cleared":
        return f"{prerequisite} is present, but this alone does not authorize a live write."
    return f"{prerequisite} is still blocking the live parity attempt."


def _claim_boundary_footer(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> dict[str, Any]:
    return {
        "placement": "sticky_after_every_blocker_recommendation",
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "short_warning": (
            "This surface is an internal blocker display only; it does not clear "
            "Acontext prerequisites or prove runtime parity."
        ),
    }


def _surface_verdict(delta: dict[str, Any]) -> str:
    if delta["remaining_blockers"] or delta["newly_blocked"]:
        return "admin_acontext_blocker_delta_surface_landed_live_transport_blocked"
    return "unexpected_surface_without_blockers_should_not_promote_live_parity"


def _assert_source_delta_mountable(delta: dict[str, Any]) -> None:
    if delta.get("schema") != ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SCHEMA:
        raise CityOpsContractError("Acontext blocker-delta surface requires delta source")
    readiness = delta.get("readiness") or {}
    if readiness.get("blocker_delta_landed") is not True:
        raise CityOpsContractError("Acontext blocker-delta surface missing source delta")
    if readiness.get("ready_to_attempt_live_transport") is not False:
        raise CityOpsContractError("Acontext blocker-delta surface cannot mount ready source")
    for flag in (
        "acontext_sink_ready",
        "runtime_parity_proven",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ):
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Acontext blocker-delta surface source promoted {flag}"
            )
    if not delta.get("current_blockers"):
        raise CityOpsContractError("Acontext blocker-delta surface requires blockers")
    forbidden_safe = set(delta.get("claim_boundaries", {}).get("safe_to_claim", [])) & set(
        SURFACE_BLOCKED_CLAIMS
    )
    if forbidden_safe:
        raise CityOpsContractError(
            f"Acontext blocker-delta source has blocked safe claims: {sorted(forbidden_safe)}"
        )


def _assert_surface_conservative(surface: dict[str, Any], delta: dict[str, Any]) -> None:
    if surface.get("schema") != ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("Acontext blocker-delta surface schema drift")
    _assert_source_delta_mountable(delta)
    if surface.get("source_delta_id") != delta.get("delta_id"):
        raise CityOpsContractError("Acontext blocker-delta surface source mismatch")
    for section in ("access_policy", "render_contract"):
        values = surface.get(section) or {}
        for flag in _FALSE_ACCESS_FLAGS:
            if flag in values and values.get(flag) is not False:
                raise CityOpsContractError(
                    f"Acontext blocker-delta surface promoted {section}.{flag}"
                )
    derived = surface.get("derived_from") or {}
    for flag in (
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_customer_copy",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ):
        if derived.get(flag) is not False:
            raise CityOpsContractError(
                f"Acontext blocker-delta surface derived flag promoted {flag}"
            )
    readiness = surface.get("readiness") or {}
    if readiness.get("surface_landed") is not True:
        raise CityOpsContractError("Acontext blocker-delta surface missing landed flag")
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Acontext blocker-delta surface promoted readiness {flag}"
            )
    for card in surface.get("prerequisite_status_cards", []):
        if card.get("authorizes_live_write") is not False:
            raise CityOpsContractError(
                "Acontext blocker-delta surface card authorized live write"
            )
    for card in surface.get("operator_next_action_cards", []):
        if card.get("authorizes_live_write") is not False:
            raise CityOpsContractError(
                "Acontext blocker-delta surface action authorized live write"
            )
    _assert_claim_boundaries(
        surface.get("claim_boundaries", {}).get("safe_to_claim", []),
        surface.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"Acontext blocker-delta surface claim overlap: {overlap}")
    forbidden = sorted(set(safe_to_claim) & set(SURFACE_BLOCKED_CLAIMS))
    if forbidden:
        raise CityOpsContractError(
            f"Acontext blocker-delta surface forbidden safe claims: {forbidden}"
        )


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
