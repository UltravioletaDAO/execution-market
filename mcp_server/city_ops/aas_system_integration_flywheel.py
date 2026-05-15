"""System-integration flywheel for City-as-a-Service AAS planning.

This module connects the current CaaS strengths into one conservative handoff
artifact. It is deliberately read-only: it consumes the decision-support
readiness matrix and records how memory/Acontext, IRC session management,
cross-project decision support, and observability should reinforce one another
without claiming live Acontext parity, autonomous dispatch, public packaging,
or newly verified payment coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .decision_support_readiness_matrix import (
    DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM,
    DECISION_SUPPORT_READINESS_MATRIX_SCHEMA,
    build_decision_support_readiness_matrix,
    load_decision_support_readiness_matrix,
)
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir

AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA = "city_ops.aas_system_integration_flywheel.v1"
AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME = "aas_system_integration_flywheel.json"
AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM = "aas_system_integration_flywheel_landed"

DECLARED_STRENGTHS = [
    {
        "strength": "latest_city_ops_code_changes",
        "verification_level": "consumed_from_local_artifact_graph",
        "safe_use": "treat recent city_ops proof slices as the bounded implementation substrate",
    },
    {
        "strength": "eight_chain_payment_integration",
        "verification_level": "declared_not_reverified_by_this_artifact",
        "safe_use": "use as production-confidence context only; do not claim fresh payment verification",
    },
    {
        "strength": "intelligent_memory_with_26_plus_insights",
        "verification_level": "declared_not_recounted_by_this_artifact",
        "safe_use": "shape memory/Acontext bridge requirements without writing live memory",
    },
    {
        "strength": "production_infrastructure_operational",
        "verification_level": "declared_not_reverified_by_this_artifact",
        "safe_use": "prefer deployable admin/operator seams, but keep this artifact non-deploying",
    },
    {
        "strength": "legendary_agent_coordination",
        "verification_level": "consumed_from_decision_support_matrix",
        "safe_use": "codify invariant-ID handoff and claim-boundary preservation",
    },
]

REQUIRED_AXES = [
    "memory_system_to_acontext_bridge",
    "irc_session_management",
    "cross_project_decision_support",
    "agent_observability_success_metrics",
]

CRITICAL_FALSE_FLAGS = [
    "flywheel_promotes_live_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "customer_visible_packaging_ready",
    "payment_coverage_reverified_by_this_artifact",
    "worker_copyable_doctrine_ready",
]

FLYWHEEL_BLOCKED_CLAIMS = [
    "live_acontext_sink_ready",
    "runtime_parity_proven",
    "autonomous_city_dispatch_ready",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "payment_coverage_reverified_by_this_artifact",
    "eight_chain_payment_perfection_revalidated_by_this_artifact",
    "worker_copyable_municipal_doctrine_ready",
    "raw_transcript_replay_required_for_normal_handoff",
]


def build_aas_system_integration_flywheel(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    decision_support_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative integration flywheel from the readiness matrix."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    matrix = decision_support_matrix or _load_or_build_matrix(proof_anchor_id, base_dir)
    _assert_matrix_contract(proof_anchor_id, matrix)

    axes = matrix["handoff_axes"]
    axis_by_name = {axis["axis"]: axis for axis in axes}
    missing_axes = [axis for axis in REQUIRED_AXES if axis not in axis_by_name]
    if missing_axes:
        raise CityOpsContractError(f"system integration flywheel missing axes: {missing_axes}")

    safe_to_claim = _dedupe(
        [
            *matrix["claim_boundaries"].get("safe_to_claim", []),
            DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *matrix["claim_boundaries"].get("do_not_claim_yet", []),
            *FLYWHEEL_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_blocked_claims_safe(safe_to_claim)
    _assert_blocked_claims_preserved(matrix, do_not_claim_yet)

    readiness = _readiness(matrix)
    connections = _connection_loops(axis_by_name)
    metrics = _success_metrics(matrix, connections, axes)

    flywheel = {
        "schema": AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA,
        "flywheel_id": f"aas_system_integration_flywheel:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": matrix["coordination_session_id"],
        "compact_decision_id": matrix["compact_decision_id"],
        "review_packet_id": matrix["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                "decision_support_readiness_matrix.json",
                *matrix["derived_from"].get("source_artifacts", []),
            ],
            "writes_live_sink": False,
            "raw_conversation_reopened": False,
            "semantic_reinterpretation_performed": False,
            "payment_system_reverified": False,
            "production_infrastructure_reverified": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": readiness,
        "declared_strength_inputs": DECLARED_STRENGTHS,
        "connection_loops": connections,
        "system_integration_metrics": metrics,
        "session_management_enhancements": _session_management_enhancements(matrix),
        "operator_next_actions": _operator_next_actions(matrix),
        "flywheel_verdict": _flywheel_verdict(readiness),
        "next_smallest_proof": _dedupe(
            [
                *matrix["next_smallest_proof"],
                "run one live Acontext write/retrieve parity pass before promoting sink readiness",
                "add one dashboard/admin consumer that renders this flywheel without changing claim boundaries",
                "rerun payment and production probes separately before repeating 8/8 or operational claims",
            ]
        ),
    }
    _assert_flywheel_contract(flywheel)
    return flywheel


def write_aas_system_integration_flywheel(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic system-integration flywheel fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    flywheel = build_aas_system_integration_flywheel(
        proof_anchor_id,
        artifact_dir=base_dir,
    )
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME
    path.write_text(json.dumps(flywheel, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_system_integration_flywheel(
    *,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the persisted system-integration flywheel."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME).open(
        "r",
        encoding="utf-8",
    ) as fh:
        flywheel = json.load(fh)
    _assert_flywheel_contract(flywheel)
    return flywheel


def _load_or_build_matrix(proof_anchor_id: str, artifact_dir: Path) -> dict[str, Any]:
    path = artifact_dir / "decision_support_readiness_matrix.json"
    if path.exists():
        return load_decision_support_readiness_matrix(artifact_dir=artifact_dir)
    return build_decision_support_readiness_matrix(proof_anchor_id, artifact_dir=artifact_dir)


def _readiness(matrix: dict[str, Any]) -> dict[str, Any]:
    source = matrix["readiness"]
    return {
        "flywheel_artifact_ready": True,
        "flywheel_promotes_live_readiness": False,
        "decision_support_matrix_ready": bool(source.get("decision_support_matrix_ready")),
        "memory_to_acontext_bridge_planned": True,
        "irc_session_handoff_planned": True,
        "cross_project_decision_support_planned": True,
        "agent_observability_metrics_planned": True,
        "ready_to_attempt_live_transport": bool(source.get("ready_to_attempt_live_transport")),
        "local_transport_parity_fixture_passed": bool(source.get("local_transport_parity_fixture_passed")),
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "customer_visible_packaging_ready": False,
        "payment_coverage_reverified_by_this_artifact": False,
        "worker_copyable_doctrine_ready": False,
        "blockers": _dedupe(
            [
                *source.get("blockers", []),
                "live_acontext_write_retrieve_parity_not_completed_here",
                "payment_and_production_claims_need_separate_probe_before_restatement",
            ]
        ),
    }


def _connection_loops(axis_by_name: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "loop": "reviewed_memory_to_acontext_to_better_dispatch",
            "source_strength": "intelligent_memory_with_26_plus_insights",
            "uses_axis": "memory_system_to_acontext_bridge",
            "axis_state": axis_by_name["memory_system_to_acontext_bridge"]["state"],
            "decision_support_effect": "convert reviewed municipal episodes into compact retrieval candidates without live sink writes",
            "guardrail": "do not promote acontext_sink_ready until live write/retrieve parity passes",
        },
        {
            "loop": "irc_session_ids_to_cross_session_continuity",
            "source_strength": "legendary_agent_coordination",
            "uses_axis": "irc_session_management",
            "axis_state": axis_by_name["irc_session_management"]["state"],
            "decision_support_effect": "handoff by coordination_session_id, compact_decision_id, review_packet_id, and proof_anchor_id",
            "guardrail": "no raw transcript replay on the normal path",
        },
        {
            "loop": "decision_matrix_to_cross_project_operator_choices",
            "source_strength": "latest_city_ops_code_changes",
            "uses_axis": "cross_project_decision_support",
            "axis_state": axis_by_name["cross_project_decision_support"]["state"],
            "decision_support_effect": "reuse safe/blocked verdicts across AAS families without copying customer-facing claims",
            "guardrail": "require a second reviewed municipal case before cross-case doctrine",
        },
        {
            "loop": "observability_to_agent_success_metrics",
            "source_strength": "production_infrastructure_operational",
            "uses_axis": "agent_observability_success_metrics",
            "axis_state": axis_by_name["agent_observability_success_metrics"]["state"],
            "decision_support_effect": "measure whether future agents preserve boundaries, consume IDs, and recommend the next proof",
            "guardrail": "do not treat planning metrics as a live dashboard or customer-visible metric surface",
        },
        {
            "loop": "payment_confidence_to_deployable_aas_boundaries",
            "source_strength": "eight_chain_payment_integration",
            "uses_axis": "cross_project_decision_support",
            "axis_state": axis_by_name["cross_project_decision_support"]["state"],
            "decision_support_effect": "keep AAS packaging aligned with operational payment rails while separating proof claims",
            "guardrail": "this artifact does not rerun or restate 8/8 chain payment verification",
        },
    ]


def _success_metrics(
    matrix: dict[str, Any],
    connections: list[dict[str, Any]],
    axes: list[dict[str, Any]],
) -> dict[str, Any]:
    ready_axis_count = sum(1 for axis in axes if axis.get("ready_now") is True)
    return {
        "required_axis_count": len(REQUIRED_AXES),
        "ready_axis_count_from_matrix": ready_axis_count,
        "blocked_axis_count_from_matrix": len(axes) - ready_axis_count,
        "connection_loop_count": len(connections),
        "declared_strength_count": len(DECLARED_STRENGTHS),
        "claim_boundary_preservation": "pass",
        "safe_claim_count": len(matrix["claim_boundaries"].get("safe_to_claim", [])) + 1,
        "blocked_claim_count": len(
            _dedupe([*matrix["claim_boundaries"].get("do_not_claim_yet", []), *FLYWHEEL_BLOCKED_CLAIMS])
        ),
        "future_agent_success_definition": [
            "consume flywheel_id plus invariant IDs without reopening raw transcript context",
            "preserve safe_to_claim and do_not_claim_yet together",
            "distinguish declared strengths from independently reverified facts",
            "recommend live Acontext parity or admin rendering as the next smallest proof",
        ],
    }


def _session_management_enhancements(matrix: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "enhancement": "four_id_session_header",
            "implementation_rule": "include proof_anchor_id, coordination_session_id, compact_decision_id, and review_packet_id at the top of every IRC/admin handoff",
        },
        {
            "enhancement": "declared_vs_verified_badges",
            "implementation_rule": "label payment, infrastructure, and memory-strength claims by verification_level before agents repeat them",
        },
        {
            "enhancement": "blocked_claim_sticky_footer",
            "implementation_rule": "render blocked claims after every recommendation, not only in debug artifacts",
        },
        {
            "enhancement": "single_next_proof_slot",
            "implementation_rule": f"default next proof remains: {matrix['recommended_next_action']}",
        },
    ]


def _operator_next_actions(matrix: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "action": "live_acontext_parity_probe",
            "why": "turn the memory/Acontext bridge from planned or attemptable into verified sink behavior",
            "claim_unlocked_only_if_passes": "acontext_live_transport_parity_landed",
        },
        {
            "action": "admin_flywheel_read_surface",
            "why": "let operators see how strengths connect without reading the full proof bundle",
            "claim_unlocked_only_if_passes": "admin_system_integration_flywheel_surface_landed",
        },
        {
            "action": "separate_payment_and_infra_probe",
            "why": "avoid mixing AAS planning proof with payment or production-health claims",
            "claim_unlocked_only_if_passes": "payment_and_infra_status_reverified_for_aas_packaging",
        },
        {
            "action": "preserve_matrix_recommendation",
            "why": "keep the current decision-support next step visible",
            "claim_unlocked_only_if_passes": matrix["recommended_next_action"],
        },
    ]


def _flywheel_verdict(readiness: dict[str, Any]) -> str:
    if readiness["ready_to_attempt_live_transport"]:
        return "system_integration_flywheel_landed_live_acontext_attemptable_not_ready"
    return "system_integration_flywheel_landed_live_acontext_blocked"


def _assert_matrix_contract(proof_anchor_id: str, matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != DECISION_SUPPORT_READINESS_MATRIX_SCHEMA:
        raise CityOpsContractError("system integration flywheel requires readiness matrix")
    if matrix.get("proof_anchor_id") != proof_anchor_id:
        raise CityOpsContractError("system integration flywheel proof anchor drift")
    derived = matrix.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("system integration flywheel requires read-only matrix")
    if derived.get("writes_live_sink") is not False:
        raise CityOpsContractError("system integration flywheel refuses sink-writing matrix")
    if derived.get("raw_conversation_reopened") is not False:
        raise CityOpsContractError("system integration flywheel refuses raw replay matrix")
    if matrix.get("readiness", {}).get("acontext_sink_ready") is not False:
        raise CityOpsContractError("system integration flywheel refuses promoted Acontext readiness")
    _assert_no_blocked_claims_safe(matrix.get("claim_boundaries", {}).get("safe_to_claim", []))


def _assert_flywheel_contract(flywheel: dict[str, Any]) -> None:
    if flywheel.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA:
        raise CityOpsContractError("system integration flywheel schema drift")
    derived = flywheel.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("system integration flywheel must be read-only")
    if derived.get("writes_live_sink") is not False:
        raise CityOpsContractError("system integration flywheel cannot write live sink")
    if derived.get("payment_system_reverified") is not False:
        raise CityOpsContractError("system integration flywheel cannot reverify payments")
    readiness = flywheel.get("readiness", {})
    for flag in CRITICAL_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"system integration flywheel promoted {flag}")
    safe_to_claim = flywheel.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim = flywheel.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    _assert_no_blocked_claims_safe(safe_to_claim)
    missing = set(FLYWHEEL_BLOCKED_CLAIMS) - set(do_not_claim)
    if missing:
        raise CityOpsContractError(f"system integration flywheel missing blocked claims: {sorted(missing)}")
    loops = flywheel.get("connection_loops", [])
    if {loop.get("uses_axis") for loop in loops} < set(REQUIRED_AXES):
        raise CityOpsContractError("system integration flywheel does not cover every required axis")
    if len(flywheel.get("declared_strength_inputs", [])) != len(DECLARED_STRENGTHS):
        raise CityOpsContractError("system integration flywheel strength input drift")


def _assert_no_blocked_claims_safe(safe_to_claim: list[str]) -> None:
    blocked_safe = sorted(set(safe_to_claim) & set(FLYWHEEL_BLOCKED_CLAIMS))
    if blocked_safe:
        raise CityOpsContractError(
            f"system integration flywheel blocked claims marked safe: {blocked_safe}"
        )


def _assert_blocked_claims_preserved(
    matrix: dict[str, Any],
    do_not_claim_yet: list[str],
) -> None:
    inherited = set(matrix["claim_boundaries"].get("do_not_claim_yet", []))
    expected = inherited | set(FLYWHEEL_BLOCKED_CLAIMS)
    missing = sorted(expected - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(f"system integration flywheel softened blocked claims: {missing}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
