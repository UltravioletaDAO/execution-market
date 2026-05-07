"""Observability snapshot for City-as-a-Service proof-block readiness.

This module converts the thin operator/debug surface into a small, deterministic
metrics artifact.  It is intentionally not a dashboard and not a live Acontext
sink.  Its job is to make the current CaaS proof ladder measurable while keeping
all conservative claim boundaries visible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .operator_debug_surface import OPERATOR_DEBUG_SURFACE_SAFE_CLAIM
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir

PROOF_OBSERVABILITY_SCHEMA = "city_ops.proof_observability_snapshot.v1"
PROOF_OBSERVABILITY_SAFE_CLAIM = "proof_observability_metrics_landed"
PROOF_OBSERVABILITY_BLOCKED_CLAIMS = [
    "closure_proof_landed",
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "acontext_live_transport_parity_landed",
    "worker-copyable municipal doctrine",
    "polished_review_console_ready",
    "office_memory_view_ready",
    "broad_operator_workflow_ready",
]
CRITICAL_READINESS_FLAGS = [
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
]


def build_proof_observability_snapshot(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    operator_debug_surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only metrics snapshot from the operator/debug surface.

    The snapshot is safe to hand to a coordinator or morning brief because it
    reports what is measurable, what remains blocked, and the next action.  It
    cannot promote session rebuild, Acontext sink, runtime parity, or
    worker-copyable municipal doctrine readiness.
    """

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    surface = operator_debug_surface or _load_json(base_dir / "operator_debug_surface.json")
    _assert_surface_contract(proof_anchor_id, surface)

    safe_to_claim = _dedupe(
        [
            *surface["claim_boundaries"].get("safe_to_claim", []),
            OPERATOR_DEBUG_SURFACE_SAFE_CLAIM,
            PROOF_OBSERVABILITY_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *surface["claim_boundaries"].get("do_not_claim_yet", []),
            *PROOF_OBSERVABILITY_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_blocked_claims_safe(safe_to_claim)
    _assert_do_not_claim_preserved(surface, do_not_claim_yet)

    readiness = _observability_readiness(surface)
    metrics = _metrics(surface, safe_to_claim, do_not_claim_yet)
    signals = _signals(surface, metrics)
    decision_support = _decision_support(surface, metrics)

    return {
        "schema": PROOF_OBSERVABILITY_SCHEMA,
        "snapshot_id": f"proof_observability:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": surface["coordination_session_id"],
        "compact_decision_id": surface["compact_decision_id"],
        "review_packet_id": surface["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": ["operator_debug_surface.json"],
            "forbidden_sources": list(surface["derived_from"]["forbidden_sources"]),
            "writes_live_sink": False,
            "semantic_reinterpretation_performed": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "metrics": metrics,
        "signals": signals,
        "readiness": readiness,
        "decision_support": decision_support,
        "observability_verdict": _observability_verdict(readiness),
        "next_smallest_proof": list(surface["next_smallest_proof"]),
    }


def write_proof_observability_snapshot_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic CaaS proof observability fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    snapshot = build_proof_observability_snapshot(proof_anchor_id, artifact_dir=base_dir)
    path = base_dir / "proof_observability_snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _observability_readiness(surface: dict[str, Any]) -> dict[str, Any]:
    surface_readiness = surface["readiness"]
    return {
        "observability_snapshot_ready": True,
        "metrics_promote_readiness": False,
        "session_rebuild_ready": False,
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "worker_copyable_doctrine_ready": False,
        "ready_to_attempt_live_transport": bool(
            surface_readiness.get("ready_to_attempt_live_transport")
        ),
        "local_transport_parity_fixture_passed": bool(
            surface_readiness.get("local_transport_parity_fixture_passed")
        ),
        "live_acontext_write_performed": bool(
            surface_readiness.get("live_acontext_write_performed")
        ),
        "live_acontext_retrieval_performed": bool(
            surface_readiness.get("live_acontext_retrieval_performed")
        ),
        "blockers": list(surface_readiness.get("blockers", [])),
    }


def _metrics(
    surface: dict[str, Any], safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> dict[str, Any]:
    readiness = surface["readiness"]
    cards = surface.get("debug_cards", [])
    operator_visibility = surface["operator_visibility"]
    critical_false_count = sum(
        1 for flag in CRITICAL_READINESS_FLAGS if readiness.get(flag) is False
    )
    return {
        "safe_claim_count": len(safe_to_claim),
        "blocked_claim_count": len(do_not_claim_yet),
        "debug_card_count": len(cards),
        "acontext_blocker_count": len(readiness.get("blockers", [])),
        "critical_readiness_false_count": critical_false_count,
        "critical_readiness_flag_count": len(CRITICAL_READINESS_FLAGS),
        "all_critical_readiness_flags_false": critical_false_count
        == len(CRITICAL_READINESS_FLAGS),
        "local_transport_parity_fixture_passed": bool(
            readiness.get("local_transport_parity_fixture_passed")
        ),
        "ready_to_attempt_live_transport": bool(
            readiness.get("ready_to_attempt_live_transport")
        ),
        "worker_copyable_surface_enabled": bool(
            operator_visibility.get("worker_copyable_surface_enabled")
        ),
        "copyable_worker_instruction_allowed": bool(
            operator_visibility["copyable_worker_instruction"].get("allowed")
        ),
        "live_acontext_write_performed": bool(
            readiness.get("live_acontext_write_performed")
        ),
        "live_acontext_retrieval_performed": bool(
            readiness.get("live_acontext_retrieval_performed")
        ),
    }


def _signals(surface: dict[str, Any], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    blocker_count = metrics["acontext_blocker_count"]
    return [
        {
            "signal": "claim_boundary_visibility",
            "status": "passed",
            "evidence": "safe_to_claim and do_not_claim_yet cards remain explicit",
        },
        {
            "signal": "operator_guidance_boundary",
            "status": "passed",
            "evidence": surface["operator_visibility"]["guidance_placement"],
        },
        {
            "signal": "local_transport_parity_fixture",
            "status": "passed"
            if metrics["local_transport_parity_fixture_passed"]
            else "blocked",
            "evidence": surface["readiness"].get("local_transport_parity_fixture_passed"),
        },
        {
            "signal": "live_acontext_prerequisites",
            "status": "attemptable" if blocker_count == 0 else "blocked",
            "evidence": list(surface["readiness"].get("blockers", [])),
        },
        {
            "signal": "readiness_honesty",
            "status": "passed"
            if metrics["all_critical_readiness_flags_false"]
            else "failed",
            "evidence": {
                flag: surface["readiness"].get(flag) for flag in CRITICAL_READINESS_FLAGS
            },
        },
    ]


def _decision_support(surface: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    if metrics["ready_to_attempt_live_transport"]:
        current_state = "observable_and_live_transport_attemptable"
        recommended_next_action = "run one live local Acontext write/retrieve parity pass"
    else:
        current_state = "observable_but_live_transport_blocked"
        blockers = surface["readiness"].get("blockers", [])
        recommended_next_action = (
            f"clear Acontext prerequisites: {', '.join(blockers)}"
            if blockers
            else "rerun live preflight before any sink write"
        )

    return {
        "current_state": current_state,
        "recommended_next_action": recommended_next_action,
        "highest_value_workstream": "CaaS Acontext transport parity without semantic strengthening",
        "decision_basis": [
            "operator/debug surface is read-only",
            "local transport parity fixture passed",
            "live sink writes are still false",
            "worker-copyable municipal doctrine remains blocked",
        ],
        "do_not_start_yet": [
            "worker-copyable municipal doctrine",
            "polished Review Console",
            "broad Office Memory View",
            "multi-template expansion",
        ],
    }


def _observability_verdict(readiness: dict[str, Any]) -> str:
    if readiness["ready_to_attempt_live_transport"]:
        return "proof_observability_metrics_landed_live_transport_attemptable"
    return "proof_observability_metrics_landed_live_transport_blocked"


def _assert_surface_contract(proof_anchor_id: str, surface: dict[str, Any]) -> None:
    if surface.get("schema") != "city_ops.operator_debug_surface.v1":
        raise CityOpsContractError("proof observability requires operator debug surface")
    if surface.get("proof_anchor_id") != proof_anchor_id:
        raise CityOpsContractError("proof observability identity drift")

    derived_from = surface.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("proof observability requires read-only surface")
    if derived_from.get("writes_live_sink") is not False:
        raise CityOpsContractError("proof observability cannot write live sink")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("proof observability cannot reinterpret semantics")

    operator_visibility = surface.get("operator_visibility", {})
    if operator_visibility.get("worker_copyable_surface_enabled") is not False:
        raise CityOpsContractError("proof observability refuses worker-copyable surface")
    copyable = operator_visibility.get("copyable_worker_instruction", {})
    if copyable.get("allowed") is not False:
        raise CityOpsContractError("proof observability refuses worker-copyable upgrade")

    readiness = surface.get("readiness", {})
    for flag in CRITICAL_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"proof observability refuses promoted {flag}")


def _assert_no_blocked_claims_safe(safe_to_claim: list[str]) -> None:
    blocked_safe = sorted(set(safe_to_claim) & set(PROOF_OBSERVABILITY_BLOCKED_CLAIMS))
    if blocked_safe:
        raise CityOpsContractError(f"proof observability blocked claims safe: {blocked_safe}")


def _assert_do_not_claim_preserved(
    surface: dict[str, Any], do_not_claim_yet: list[str]
) -> None:
    inherited = set(surface["claim_boundaries"].get("do_not_claim_yet", []))
    expected = inherited | set(PROOF_OBSERVABILITY_BLOCKED_CLAIMS)
    missing = sorted(expected - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(f"proof observability softened do-not-claim: {missing}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
