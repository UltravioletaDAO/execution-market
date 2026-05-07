"""Coordination intelligence snapshot for City-as-a-Service proof blocks.

This module converts proof observability into a small strategic packet for
operators and future agents.  It captures the coordination patterns that are
safe to reuse without opening raw transcripts, inventing live Acontext readiness,
or turning cautious operator guidance into worker-copyable doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir
from .proof_observability import (
    PROOF_OBSERVABILITY_SAFE_CLAIM,
    build_proof_observability_snapshot,
)

COORDINATION_INTELLIGENCE_SCHEMA = "city_ops.coordination_intelligence_snapshot.v1"
COORDINATION_INTELLIGENCE_SAFE_CLAIM = "coordination_intelligence_snapshot_landed"
COORDINATION_INTELLIGENCE_BLOCKED_CLAIMS = [
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
    "multi_jurisdiction_playbook_ready",
    "autonomous_city_dispatch_ready",
]
CRITICAL_FALSE_FLAGS = [
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "worker_copyable_doctrine_ready",
]


def build_coordination_intelligence_snapshot(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    proof_observability_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only pattern-recognition packet from proof observability.

    The snapshot answers the 4am dream question: which coordination patterns
    compound?  It deliberately derives only from the metrics fixture, so it can
    guide strategy without re-reading private chat, raw worker transcripts, or
    unreviewed memory.
    """

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    observability = proof_observability_snapshot or _load_or_build_observability(
        proof_anchor_id,
        base_dir,
    )
    _assert_observability_contract(proof_anchor_id, observability)

    safe_to_claim = _dedupe(
        [
            *observability["claim_boundaries"].get("safe_to_claim", []),
            PROOF_OBSERVABILITY_SAFE_CLAIM,
            COORDINATION_INTELLIGENCE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *observability["claim_boundaries"].get("do_not_claim_yet", []),
            *COORDINATION_INTELLIGENCE_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_blocked_claims_safe(safe_to_claim)
    _assert_do_not_claim_preserved(observability, do_not_claim_yet)

    readiness = _coordination_readiness(observability)
    patterns = _coordination_patterns(observability)
    multiplier_effects = _multiplier_effects(observability, patterns)
    scaling_rules = _scaling_rules(observability)

    return {
        "schema": COORDINATION_INTELLIGENCE_SCHEMA,
        "snapshot_id": f"coordination_intelligence:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": observability["coordination_session_id"],
        "compact_decision_id": observability["compact_decision_id"],
        "review_packet_id": observability["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": ["proof_observability_snapshot.json"],
            "forbidden_sources": list(
                observability["derived_from"]["forbidden_sources"]
            ),
            "writes_live_sink": False,
            "semantic_reinterpretation_performed": False,
            "raw_conversation_reopened": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "coordination_patterns": patterns,
        "multiplier_effects": multiplier_effects,
        "scaling_rules": scaling_rules,
        "readiness": readiness,
        "decision_support": _decision_support(observability, readiness),
        "coordination_verdict": _coordination_verdict(readiness),
        "next_smallest_proof": list(observability["next_smallest_proof"]),
    }


def write_coordination_intelligence_snapshot_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic coordination intelligence fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    snapshot = build_coordination_intelligence_snapshot(
        proof_anchor_id,
        artifact_dir=base_dir,
    )
    path = base_dir / "coordination_intelligence_snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_or_build_observability(
    proof_anchor_id: str,
    artifact_dir: Path,
) -> dict[str, Any]:
    path = artifact_dir / "proof_observability_snapshot.json"
    if path.exists():
        return _load_json(path)
    return build_proof_observability_snapshot(proof_anchor_id, artifact_dir=artifact_dir)


def _coordination_readiness(observability: dict[str, Any]) -> dict[str, Any]:
    inherited = observability["readiness"]
    return {
        "coordination_intelligence_ready": True,
        "patterns_promote_readiness": False,
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


def _coordination_patterns(observability: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = observability["metrics"]
    return [
        {
            "pattern": "compact_artifact_spine",
            "status": "active",
            "why_it_scales": (
                "future sessions can consume reviewed compact artifacts instead of "
                "re-reading raw transcripts or private context"
            ),
            "evidence": [
                observability["coordination_session_id"],
                observability["compact_decision_id"],
                observability["review_packet_id"],
            ],
        },
        {
            "pattern": "claim_boundary_visibility",
            "status": "active",
            "why_it_scales": (
                "safe claims and blocked claims travel together, so handoffs can move "
                "fast without accidental promotion"
            ),
            "evidence": {
                "safe_claim_count": metrics["safe_claim_count"],
                "blocked_claim_count": metrics["blocked_claim_count"],
            },
        },
        {
            "pattern": "operator_only_learning_reuse",
            "status": "active_but_conservative",
            "why_it_scales": (
                "reviewed municipal learning can improve dispatch prep while the "
                "system still blocks direct worker-copyable doctrine"
            ),
            "evidence": {
                "worker_copyable_surface_enabled": metrics[
                    "worker_copyable_surface_enabled"
                ],
                "copyable_worker_instruction_allowed": metrics[
                    "copyable_worker_instruction_allowed"
                ],
            },
        },
        {
            "pattern": "transport_is_not_truth",
            "status": "blocked_until_live_sink",
            "why_it_scales": (
                "Acontext should carry already-reviewed meaning; it should not become "
                "the place where future agents strengthen claims"
            ),
            "evidence": {
                "local_transport_parity_fixture_passed": metrics[
                    "local_transport_parity_fixture_passed"
                ],
                "ready_to_attempt_live_transport": metrics[
                    "ready_to_attempt_live_transport"
                ],
                "live_acontext_write_performed": metrics[
                    "live_acontext_write_performed"
                ],
                "live_acontext_retrieval_performed": metrics[
                    "live_acontext_retrieval_performed"
                ],
            },
        },
    ]


def _multiplier_effects(
    observability: dict[str, Any],
    patterns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blocked = observability["metrics"]["acontext_blocker_count"]
    return [
        {
            "effect": "memory_system_data_becomes_dispatch_capital",
            "multiplier": "one reviewed redirect can change many future dispatches",
            "requires_next": "prove live transport parity before increasing surface area",
        },
        {
            "effect": "irc_coordination_lessons_become_product_rules",
            "multiplier": (
                "handoff via invariant IDs and compact packets scales better than "
                "asking every agent to infer from chat history"
            ),
            "requires_next": "keep coordination_session_id and proof_anchor_id on every artifact",
        },
        {
            "effect": "cross_project_intelligence_flow_without_privacy_leakage",
            "multiplier": (
                "other agent systems can consume bounded verdicts, not raw private "
                "municipal conversations"
            ),
            "requires_next": "continue forbidding raw_transcript and unreviewed_memory sources",
        },
        {
            "effect": "execution_market_as_operational_memory_layer",
            "multiplier": (
                "the marketplace stops being only task fulfillment and starts becoming "
                "reviewed real-world process memory"
            ),
            "requires_next": "clear live Acontext blockers" if blocked else "run live sink parity",
        },
        {
            "effect": "coordination_patterns_ranked_for_scale",
            "multiplier": f"{len(patterns)} reusable patterns captured from one proof block",
            "requires_next": "add a second reviewed municipal case before broadening doctrine",
        },
    ]


def _scaling_rules(observability: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "rule": "coordinate_by_invariant_ids",
            "reason": "coordination_session_id, compact_decision_id, review_packet_id, and proof_anchor_id survive handoffs better than prose summaries",
        },
        {
            "rule": "promote_only_after_review",
            "reason": "raw uploads and unreviewed memory can inform review but cannot become durable municipal doctrine",
        },
        {
            "rule": "keep_blocked_claims_adjacent_to_safe_claims",
            "reason": "fast agent coordination is safest when every handoff includes what not to say yet",
        },
        {
            "rule": "ship_transport_parity_before_ui_broadening",
            "reason": "a polished console over unproven live retrieval would hide the most important risk",
        },
        {
            "rule": "add_cases_before_doctrine",
            "reason": "one redirect proof can justify cautious operator guidance, not general worker-copyable city doctrine",
        },
    ]


def _decision_support(
    observability: dict[str, Any], readiness: dict[str, Any]
) -> dict[str, Any]:
    if readiness["ready_to_attempt_live_transport"]:
        state = "coordination_intelligence_ready_live_transport_attemptable"
        next_action = "run one live local Acontext write/retrieve parity pass"
    else:
        state = "coordination_intelligence_ready_live_transport_blocked"
        blockers = readiness["blockers"]
        next_action = (
            f"clear Acontext prerequisites: {', '.join(blockers)}"
            if blockers
            else "rerun live preflight before any sink write"
        )

    return {
        "current_state": state,
        "recommended_next_action": next_action,
        "highest_value_connection": (
            "reviewed municipal proof blocks can become the common handoff language "
            "between memory, IRC-style coordination, dispatch, and Acontext transport"
        ),
        "do_not_start_yet": [
            "AutoJob integration",
            "Frontier Academy guide expansion",
            "KK v2",
            "worker-copyable municipal doctrine",
            "broad operator workflow UI",
        ],
        "decision_basis": list(observability["decision_support"]["decision_basis"]),
    }


def _coordination_verdict(readiness: dict[str, Any]) -> str:
    if readiness["ready_to_attempt_live_transport"]:
        return "coordination_intelligence_landed_live_transport_attemptable"
    return "coordination_intelligence_landed_live_transport_blocked"


def _assert_observability_contract(
    proof_anchor_id: str,
    observability: dict[str, Any],
) -> None:
    if observability.get("schema") != "city_ops.proof_observability_snapshot.v1":
        raise CityOpsContractError("coordination intelligence requires proof observability")
    if observability.get("proof_anchor_id") != proof_anchor_id:
        raise CityOpsContractError("coordination intelligence identity drift")

    derived_from = observability.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("coordination intelligence requires read-only source")
    if derived_from.get("writes_live_sink") is not False:
        raise CityOpsContractError("coordination intelligence cannot write live sink")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("coordination intelligence cannot reinterpret semantics")

    readiness = observability.get("readiness", {})
    for flag in CRITICAL_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"coordination intelligence refuses promoted {flag}")


def _assert_no_blocked_claims_safe(safe_to_claim: list[str]) -> None:
    blocked_safe = sorted(
        set(safe_to_claim) & set(COORDINATION_INTELLIGENCE_BLOCKED_CLAIMS)
    )
    if blocked_safe:
        raise CityOpsContractError(
            f"coordination intelligence blocked claims safe: {blocked_safe}"
        )


def _assert_do_not_claim_preserved(
    observability: dict[str, Any],
    do_not_claim_yet: list[str],
) -> None:
    inherited = set(observability["claim_boundaries"].get("do_not_claim_yet", []))
    expected = inherited | set(COORDINATION_INTELLIGENCE_BLOCKED_CLAIMS)
    missing = sorted(expected - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(
            f"coordination intelligence softened do-not-claim: {missing}"
        )


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
