"""Decision-support readiness matrix for City-as-a-Service coordination loops.

This module turns the existing coordination intelligence snapshot into a compact
operator/agent matrix.  It is intentionally read-only: it names the seams that
connect municipal memory, IRC/session handoffs, Acontext transport, and success
metrics without claiming live Acontext, broad dispatch automation, or
worker-copyable doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .coordination_intelligence import (
    COORDINATION_INTELLIGENCE_SAFE_CLAIM,
    build_coordination_intelligence_snapshot,
)
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir

DECISION_SUPPORT_READINESS_MATRIX_SCHEMA = "city_ops.decision_support_readiness_matrix.v1"
DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM = "decision_support_readiness_matrix_landed"
DECISION_SUPPORT_READINESS_MATRIX_FILENAME = "decision_support_readiness_matrix.json"
DECISION_SUPPORT_BLOCKED_CLAIMS = [
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "acontext_live_transport_parity_landed",
    "autonomous_city_dispatch_ready",
    "polished_review_console_ready",
    "office_memory_view_ready",
    "broad_operator_workflow_ready",
    "customer_visible_catalog_ready",
    "public_route_ready",
    "worker Skill DNA readiness",
    "worker-copyable municipal doctrine",
]
CRITICAL_FALSE_FLAGS = [
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "worker_copyable_doctrine_ready",
]


def build_decision_support_readiness_matrix(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    coordination_intelligence_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative matrix from coordination intelligence.

    The matrix is meant for morning/daytime handoff decisions.  It answers which
    system-integration axis is actually ready, which one is merely attemptable,
    and which one must stay blocked until a stronger proof exists.
    """

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    coordination = coordination_intelligence_snapshot or _load_or_build_coordination(
        proof_anchor_id,
        base_dir,
    )
    _assert_coordination_contract(proof_anchor_id, coordination)

    safe_to_claim = _dedupe(
        [
            *coordination["claim_boundaries"].get("safe_to_claim", []),
            COORDINATION_INTELLIGENCE_SAFE_CLAIM,
            DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *coordination["claim_boundaries"].get("do_not_claim_yet", []),
            *DECISION_SUPPORT_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_blocked_claims_safe(safe_to_claim)
    _assert_do_not_claim_preserved(coordination, do_not_claim_yet)

    readiness = _readiness(coordination)
    axes = _handoff_axes(coordination, readiness)
    metrics = _success_metrics(coordination, axes)
    enhancements = _session_management_enhancements(coordination)
    verdict = _matrix_verdict(readiness)

    return {
        "schema": DECISION_SUPPORT_READINESS_MATRIX_SCHEMA,
        "matrix_id": f"decision_support_readiness:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": coordination["coordination_session_id"],
        "compact_decision_id": coordination["compact_decision_id"],
        "review_packet_id": coordination["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                "coordination_intelligence_snapshot.json",
                "proof_observability_snapshot.json",
            ],
            "forbidden_sources": list(coordination["derived_from"]["forbidden_sources"]),
            "writes_live_sink": False,
            "raw_conversation_reopened": False,
            "semantic_reinterpretation_performed": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": readiness,
        "handoff_axes": axes,
        "success_metrics": metrics,
        "session_management_enhancements": enhancements,
        "recommended_next_action": coordination["decision_support"][
            "recommended_next_action"
        ],
        "matrix_verdict": verdict,
        "next_smallest_proof": _dedupe(
            [
                *coordination["next_smallest_proof"],
                "add a second reviewed municipal case before promoting cross-case doctrine",
                "keep matrix consumption read-only until live Acontext parity is proven",
            ]
        ),
    }


def write_decision_support_readiness_matrix_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic decision-support readiness matrix fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    matrix = build_decision_support_readiness_matrix(
        proof_anchor_id,
        artifact_dir=base_dir,
    )
    path = base_dir / DECISION_SUPPORT_READINESS_MATRIX_FILENAME
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_decision_support_readiness_matrix(
    *,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the persisted readiness matrix fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    matrix = _load_json(base_dir / DECISION_SUPPORT_READINESS_MATRIX_FILENAME)
    _assert_matrix_contract(matrix)
    return matrix


def _load_or_build_coordination(
    proof_anchor_id: str,
    artifact_dir: Path,
) -> dict[str, Any]:
    path = artifact_dir / "coordination_intelligence_snapshot.json"
    if path.exists():
        return _load_json(path)
    return build_coordination_intelligence_snapshot(proof_anchor_id, artifact_dir=artifact_dir)


def _readiness(coordination: dict[str, Any]) -> dict[str, Any]:
    inherited = coordination["readiness"]
    return {
        "decision_support_matrix_ready": True,
        "matrix_promotes_readiness": False,
        "session_rebuild_ready": False,
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "worker_copyable_doctrine_ready": False,
        "ready_to_attempt_live_transport": bool(
            inherited.get("ready_to_attempt_live_transport")
        ),
        "local_transport_parity_fixture_passed": bool(
            inherited.get("local_transport_parity_fixture_passed")
        ),
        "live_acontext_write_performed": bool(
            inherited.get("live_acontext_write_performed")
        ),
        "live_acontext_retrieval_performed": bool(
            inherited.get("live_acontext_retrieval_performed")
        ),
        "blockers": list(inherited.get("blockers", [])),
    }


def _handoff_axes(
    coordination: dict[str, Any],
    readiness: dict[str, Any]
) -> list[dict[str, Any]]:
    attemptable = readiness["ready_to_attempt_live_transport"]
    live_state = "attemptable_not_ready" if attemptable else "blocked_prerequisites_missing"
    return [
        {
            "axis": "memory_system_to_acontext_bridge",
            "state": live_state,
            "ready_now": False,
            "safe_use": "operator planning from reviewed compact artifacts only",
            "blocked_until": "one live local Acontext write/retrieve parity pass",
            "evidence": [
                "coordination_intelligence_snapshot.json",
                "proof_observability_snapshot.json",
            ],
        },
        {
            "axis": "irc_session_management",
            "state": "compact_id_handoff_active",
            "ready_now": True,
            "safe_use": "handoff by invariant IDs instead of raw chat replay",
            "blocked_until": "session rebuild consumer proves complete runtime handoff",
            "evidence": [
                coordination["coordination_session_id"],
                coordination["compact_decision_id"],
                coordination["review_packet_id"],
            ],
        },
        {
            "axis": "cross_project_decision_support",
            "state": "bounded_verdict_reusable_operator_only",
            "ready_now": True,
            "safe_use": "share safe/blocked verdicts and next-proof rules across EM AAS planning",
            "blocked_until": "second reviewed municipal case confirms repeatability",
            "evidence": [
                "claim_boundaries.safe_to_claim",
                "claim_boundaries.do_not_claim_yet",
            ],
        },
        {
            "axis": "agent_observability_success_metrics",
            "state": "proof_block_metrics_landed",
            "ready_now": True,
            "safe_use": "track whether future agents preserve claim boundaries and reuse IDs",
            "blocked_until": "live Acontext and runtime parity metrics exist",
            "evidence": [
                "success_metrics.ready_axis_count",
                "success_metrics.blocked_axis_count",
                "success_metrics.claim_boundary_preservation",
            ],
        },
    ]


def _success_metrics(
    coordination: dict[str, Any], axes: list[dict[str, Any]]) -> dict[str, Any]:
    safe = coordination["claim_boundaries"]["safe_to_claim"]
    blocked = coordination["claim_boundaries"]["do_not_claim_yet"]
    ready_count = sum(1 for axis in axes if axis["ready_now"])
    blocked_count = len(axes) - ready_count
    return {
        "ready_axis_count": ready_count,
        "blocked_axis_count": blocked_count,
        "claim_boundary_preservation": "pass",
        "safe_claim_count": len(safe),
        "blocked_claim_count": len(blocked),
        "forbidden_source_count": len(coordination["derived_from"]["forbidden_sources"]),
        "raw_conversation_reopened": False,
        "live_sink_write_attempted": False,
        "agent_handoff_success_definition": [
            "agent consumes invariant IDs without raw transcript replay",
            "agent preserves safe/blocked claims together",
            "agent recommends the next proof without promoting readiness",
            "agent records whether live Acontext remained blocked or became attemptable",
        ],
    }


def _session_management_enhancements(coordination: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "enhancement": "handoff_by_invariant_ids",
            "implementation_rule": "carry coordination_session_id, compact_decision_id, review_packet_id, and proof_anchor_id in every packet",
        },
        {
            "enhancement": "safe_and_blocked_claim_cards",
            "implementation_rule": "render safe_to_claim and do_not_claim_yet adjacent in every operator/agent surface",
        },
        {
            "enhancement": "no_raw_replay_default",
            "implementation_rule": "future sessions consume reviewed artifacts unless an explicit audit requires raw source inspection",
        },
        {
            "enhancement": "next_proof_queue",
            "implementation_rule": "each handoff names one smallest next proof from coordination intelligence",
        },
        {
            "enhancement": "blocker_visibility",
            "implementation_rule": "show Acontext prerequisites before any sink write, retrieval, UI broadening, or customer copy",
        },
    ]


def _matrix_verdict(readiness: dict[str, Any]) -> str:
    if readiness["ready_to_attempt_live_transport"]:
        return "decision_support_matrix_landed_live_transport_attemptable"
    return "decision_support_matrix_landed_live_transport_blocked"


def _assert_coordination_contract(
    proof_anchor_id: str,
    coordination: dict[str, Any],
) -> None:
    if coordination.get("schema") != "city_ops.coordination_intelligence_snapshot.v1":
        raise CityOpsContractError("decision support matrix requires coordination intelligence")
    if coordination.get("proof_anchor_id") != proof_anchor_id:
        raise CityOpsContractError("decision support matrix identity drift")

    derived_from = coordination.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("decision support matrix requires read-only source")
    if derived_from.get("writes_live_sink") is not False:
        raise CityOpsContractError("decision support matrix cannot write live sink")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("decision support matrix cannot reinterpret semantics")
    if derived_from.get("raw_conversation_reopened") is not False:
        raise CityOpsContractError("decision support matrix cannot reopen raw conversation")

    readiness = coordination.get("readiness", {})
    for flag in CRITICAL_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"decision support matrix refuses promoted {flag}")


def _assert_matrix_contract(matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != DECISION_SUPPORT_READINESS_MATRIX_SCHEMA:
        raise CityOpsContractError("decision support matrix schema drift")
    if matrix.get("derived_from", {}).get("read_only") is not True:
        raise CityOpsContractError("decision support matrix persisted source drift")
    if matrix.get("derived_from", {}).get("writes_live_sink") is not False:
        raise CityOpsContractError("decision support matrix persisted sink drift")
    readiness = matrix.get("readiness", {})
    for flag in CRITICAL_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"decision support matrix persisted promoted {flag}")
    _assert_no_blocked_claims_safe(matrix.get("claim_boundaries", {}).get("safe_to_claim", []))


def _assert_no_blocked_claims_safe(safe_to_claim: list[str]) -> None:
    blocked_safe = sorted(set(safe_to_claim) & set(DECISION_SUPPORT_BLOCKED_CLAIMS))
    if blocked_safe:
        raise CityOpsContractError(
            f"decision support matrix blocked claims safe: {blocked_safe}"
        )


def _assert_do_not_claim_preserved(
    coordination: dict[str, Any],
    do_not_claim_yet: list[str],
) -> None:
    inherited = set(coordination["claim_boundaries"].get("do_not_claim_yet", []))
    expected = inherited | set(DECISION_SUPPORT_BLOCKED_CLAIMS)
    missing = sorted(expected - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(f"decision support matrix softened do-not-claim: {missing}")


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
