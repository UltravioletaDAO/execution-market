"""Acontext live-preflight blocker delta for City-as-a-Service.

This module records the smallest useful progress after a live Acontext preflight
probe: which prerequisites cleared and which still block the write/retrieve
parity attempt.  It is intentionally not a live transport runner.  It never
writes to Acontext, never retrieves from Acontext, and never promotes runtime,
sink, customer, dispatch, or reputation readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_live_preflight import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKED_CLAIMS,
    ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM,
    ACONTEXT_LIVE_PREFLIGHT_SCHEMA,
    build_acontext_live_preflight_result,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SCHEMA = (
    "city_ops.acontext_live_preflight_blocker_delta.v1"
)
ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME = (
    "acontext_live_preflight_blocker_delta.json"
)
ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM = (
    "acontext_live_preflight_blocker_delta_landed"
)

BASELINE_BLOCKERS = [
    "docker_daemon_unavailable",
    "acontext_python_sdk_missing",
    "local_acontext_api_unreachable",
    "local_acontext_dashboard_unreachable",
]

BLOCKER_DELTA_BLOCKED_CLAIMS = [
    *ACONTEXT_LIVE_PREFLIGHT_BLOCKED_CLAIMS,
    "acontext_prerequisites_fully_cleared",
    "acontext_live_parity_attempt_authorized",
    "live_acontext_sink_ready",
    "runtime_parity_proven",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "autonomous_city_dispatch_ready",
    "operator_queue_launch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_delta",
    "production_infrastructure_reverified_by_this_delta",
    "exact_gps_or_metadata_exposure_allowed",
    "worker_copyable_municipal_doctrine_ready",
]

_FALSE_READINESS_FLAGS = [
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
    "payment_coverage_reverified_by_this_delta",
    "production_infrastructure_reverified_by_this_delta",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may15_7am_partial_acontext_probe() -> dict[str, Any]:
    """Return the deterministic 7am observed probe shape for fixture tests.

    Docker is available, but the Python SDK plus local Acontext API/dashboard
    are still absent.  The probe records no sink write and no retrieval.
    """

    return {
        "docker": {
            "checked": True,
            "available": True,
            "exit_code": 0,
            "error": None,
        },
        "python_sdk": {
            "checked": True,
            "package": "acontext",
            "available": False,
        },
        "api": {
            "checked": True,
            "url": "http://localhost:8029/api/v1",
            "reachable": False,
            "status_code": None,
            "error": "connection refused during 7am cron preflight",
        },
        "dashboard": {
            "checked": True,
            "url": "http://localhost:3000",
            "reachable": False,
            "status_code": None,
            "error": "connection refused during 7am cron preflight",
        },
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_live_preflight_blocker_delta(
    *,
    artifact_dir: str | Path | None = None,
    preflight: dict[str, Any] | None = None,
    baseline_blockers: list[str] | None = None,
) -> dict[str, Any]:
    """Build a conservative delta over a blocked Acontext live preflight."""

    source_preflight = preflight or build_acontext_live_preflight_result(
        artifact_dir=artifact_dir,
        probe=build_may15_7am_partial_acontext_probe(),
    )
    baseline = baseline_blockers or BASELINE_BLOCKERS
    _assert_source_preflight(source_preflight)

    readiness = source_preflight["readiness"]
    current_blockers = list(readiness.get("blockers", []))
    cleared_blockers = [item for item in baseline if item not in current_blockers]
    remaining_blockers = [item for item in current_blockers if item in baseline]
    newly_blocked = [item for item in current_blockers if item not in baseline]

    safe_to_claim = _dedupe(
        [
            *source_preflight["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM,
            ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_preflight["claim_boundaries"]["do_not_claim_yet"],
            *BLOCKER_DELTA_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    delta = {
        "schema": ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SCHEMA,
        "delta_id": f"acontext_live_preflight_blocker_delta:{source_preflight['preflight_id']}",
        "source_preflight_id": source_preflight["preflight_id"],
        "proof_anchor_id": source_preflight["proof_anchor_id"],
        "coordination_session_id": source_preflight["coordination_session_id"],
        "compact_decision_id": source_preflight["compact_decision_id"],
        "review_packet_id": source_preflight["review_packet_id"],
        "packet_id": source_preflight["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_schema": source_preflight["schema"],
            "source_verdict": source_preflight["preflight_verdict"],
            "consumes_only": ["acontext_live_preflight_result"],
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
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "writes_customer_copy": False,
            "enables_dispatch": False,
            "emits_reputation_receipts": False,
        },
        "baseline_blockers": list(baseline),
        "current_blockers": current_blockers,
        "cleared_blockers": cleared_blockers,
        "remaining_blockers": remaining_blockers,
        "newly_blocked": newly_blocked,
        "prerequisite_cards": _prerequisite_cards(readiness),
        "readiness": _delta_readiness(readiness),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_note": (
            "Docker is no longer the blocker, but Acontext SDK/API/dashboard remain "
            "absent; do not attempt or claim live write/retrieve parity yet."
        ),
        "next_smallest_proof": _next_smallest_proof(remaining_blockers, newly_blocked),
        "delta_verdict": _delta_verdict(cleared_blockers, remaining_blockers, newly_blocked),
    }
    _assert_delta_conservative(delta)
    return delta


def write_acontext_live_preflight_blocker_delta(
    *, artifact_dir: str | Path | None = None, preflight: dict[str, Any] | None = None
) -> Path:
    """Persist the deterministic Acontext live-preflight blocker delta."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    delta = build_acontext_live_preflight_blocker_delta(
        artifact_dir=base_dir if preflight is None else None,
        preflight=preflight,
    )
    path = base_dir / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME
    path.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_live_preflight_blocker_delta(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext blocker-delta artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        delta = json.load(fh)
    _assert_delta_conservative(delta)
    return delta


def _assert_source_preflight(preflight: dict[str, Any]) -> None:
    if preflight.get("schema") != ACONTEXT_LIVE_PREFLIGHT_SCHEMA:
        raise CityOpsContractError("Acontext blocker delta requires live preflight source")
    readiness = preflight.get("readiness") or {}
    if readiness.get("ready_to_attempt_live_transport") is not False:
        raise CityOpsContractError("Acontext blocker delta cannot replace a ready live parity run")
    if readiness.get("acontext_sink_ready") is not False:
        raise CityOpsContractError("Acontext blocker delta cannot accept sink-ready source")
    if readiness.get("runtime_parity_proven") is not False:
        raise CityOpsContractError("Acontext blocker delta cannot accept runtime parity source")
    if readiness.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("Acontext blocker delta cannot accept live write source")
    if readiness.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("Acontext blocker delta cannot accept live retrieval source")
    if not readiness.get("blockers"):
        raise CityOpsContractError("Acontext blocker delta requires at least one blocker")
    forbidden_safe = set(preflight.get("claim_boundaries", {}).get("safe_to_claim", [])) & set(
        BLOCKER_DELTA_BLOCKED_CLAIMS
    )
    if forbidden_safe:
        raise CityOpsContractError(
            f"Acontext blocker delta source has forbidden safe claims: {sorted(forbidden_safe)}"
        )


def _prerequisite_cards(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "prerequisite": "docker_daemon",
            "status": "cleared" if readiness["docker_available"] else "blocked",
            "required_for_live_parity": True,
            "authorizes_live_write": False,
        },
        {
            "prerequisite": "acontext_python_sdk",
            "status": "cleared" if readiness["acontext_python_sdk_available"] else "blocked",
            "required_for_live_parity": True,
            "authorizes_live_write": False,
        },
        {
            "prerequisite": "local_acontext_api",
            "status": "cleared" if readiness["local_acontext_api_reachable"] else "blocked",
            "required_for_live_parity": True,
            "authorizes_live_write": False,
        },
        {
            "prerequisite": "local_acontext_dashboard",
            "status": "cleared" if readiness["local_acontext_dashboard_reachable"] else "blocked",
            "required_for_live_parity": True,
            "authorizes_live_write": False,
        },
    ]


def _delta_readiness(source_readiness: dict[str, Any]) -> dict[str, Any]:
    return {
        "blocker_delta_landed": True,
        "docker_available": bool(source_readiness["docker_available"]),
        "acontext_python_sdk_available": bool(
            source_readiness["acontext_python_sdk_available"]
        ),
        "local_acontext_api_reachable": bool(source_readiness["local_acontext_api_reachable"]),
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
        "payment_coverage_reverified_by_this_delta": False,
        "production_infrastructure_reverified_by_this_delta": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
    }


def _next_smallest_proof(remaining_blockers: list[str], newly_blocked: list[str]) -> list[str]:
    if newly_blocked:
        return [
            "resolve newly observed Acontext preflight blockers before changing CaaS semantics",
            "rerun the read-only preflight and regenerate this delta",
            "attempt no live sink write until blockers are empty",
        ]
    if remaining_blockers == [
        "acontext_python_sdk_missing",
        "local_acontext_api_unreachable",
        "local_acontext_dashboard_unreachable",
    ]:
        return [
            "install or expose the Acontext Python SDK/CLI in this environment",
            "start the local Acontext API at http://localhost:8029/api/v1",
            "start the local Acontext dashboard at http://localhost:3000",
            "rerun the read-only preflight before any live write/retrieve parity attempt",
        ]
    return [
        "clear the remaining blockers shown in current_blockers",
        "rerun the read-only preflight",
        "attempt exactly one live write/retrieve parity pass only when blockers are empty",
    ]


def _delta_verdict(
    cleared_blockers: list[str], remaining_blockers: list[str], newly_blocked: list[str]
) -> str:
    if newly_blocked:
        return "live_transport_blocked_with_new_prerequisite_regression"
    if cleared_blockers and remaining_blockers:
        return "live_transport_still_blocked_with_partial_prerequisite_progress"
    if remaining_blockers:
        return "live_transport_still_blocked_no_prerequisite_progress"
    return "unexpected_no_blockers_delta_should_not_promote_live_parity"


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"Acontext blocker delta claim overlap: {overlap}")
    forbidden = sorted(set(safe_to_claim) & set(BLOCKER_DELTA_BLOCKED_CLAIMS))
    if forbidden:
        raise CityOpsContractError(f"Acontext blocker delta forbidden safe claims: {forbidden}")


def _assert_delta_conservative(delta: dict[str, Any]) -> None:
    if delta.get("schema") != ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SCHEMA:
        raise CityOpsContractError("Acontext blocker delta schema drift")
    if delta.get("derived_from", {}).get("writes_live_acontext") is not False:
        raise CityOpsContractError("Acontext blocker delta drifted into live writes")
    if delta.get("derived_from", {}).get("retrieves_live_acontext") is not False:
        raise CityOpsContractError("Acontext blocker delta drifted into live retrievals")
    readiness = delta.get("readiness") or {}
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"Acontext blocker delta promoted readiness {flag}")
    if readiness.get("blocker_delta_landed") is not True:
        raise CityOpsContractError("Acontext blocker delta missing landed flag")
    if not delta.get("current_blockers"):
        raise CityOpsContractError("Acontext blocker delta must preserve current blockers")
    for card in delta.get("prerequisite_cards", []):
        if card.get("authorizes_live_write") is not False:
            raise CityOpsContractError("Acontext blocker delta card authorized live write")
    _assert_claim_boundaries(
        delta.get("claim_boundaries", {}).get("safe_to_claim", []),
        delta.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
