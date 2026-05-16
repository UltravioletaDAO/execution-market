"""Internal/admin coordination multiplier pattern map for AAS.

This module converts the coordination observability success-metrics board into a
small pattern map: which agent-coordination habits actually compound across the
AAS ladder, and which ones must remain blocked until a separate proof exists.

It is intentionally conservative.  It is read-only, internal/admin only, reads
no raw transcripts or unreviewed memory, performs no live Acontext writes or
retrievals, creates no customer/public surface, enables no dispatch, emits no
reputation receipt, and does not reverify payment or production infrastructure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA,
    COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    load_aas_coordination_observability_success_metrics_board,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA = (
    "city_ops.aas_coordination_multiplier_pattern_map.v1"
)
AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME = (
    "aas_coordination_multiplier_pattern_map.json"
)
AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SAFE_CLAIM = (
    "admin_aas_coordination_multiplier_pattern_map_landed"
)

MULTIPLIER_PATTERN_BLOCKED_CLAIMS = [
    *COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    "coordination_patterns_customer_visible_by_pattern_map",
    "coordination_patterns_public_route_ready_by_pattern_map",
    "irc_runtime_manager_changed_by_pattern_map",
    "memory_system_live_acontext_bridge_ready_by_pattern_map",
    "cross_project_intelligence_autonomous_routing_ready_by_pattern_map",
    "agent_success_score_public_or_reputation_ready_by_pattern_map",
    "operator_queue_launch_ready_by_pattern_map",
    "pricing_or_customer_quote_approved_by_pattern_map",
    "dispatch_policy_ready_by_pattern_map",
    "erc8004_reputation_receipts_ready_by_pattern_map",
    "payment_or_production_reverified_by_pattern_map",
    "gps_or_raw_metadata_release_allowed_by_pattern_map",
    "worker_copyable_doctrine_ready_by_pattern_map",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "writes_customer_copy",
    "changes_runtime_session_manager",
    "enables_cross_project_autorouting",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "reverifies_payment_coverage",
    "reverifies_production_infrastructure",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
    "semantic_reinterpretation_performed",
]

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "operator_queue_launched",
    "dispatch_enabled",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "pattern_map_promotes_live_readiness",
    "live_acontext_memory_integration_ready",
    "irc_runtime_manager_change_ready",
    "cross_project_autorouting_ready",
    "customer_visible_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "agent_success_score_reputation_ready",
    "pricing_or_customer_quote_ready",
    "payment_coverage_reverified_by_this_map",
    "production_infrastructure_reverified_by_this_map",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_coordination_multiplier_pattern_map(
    *,
    artifact_dir: str | Path | None = None,
    metrics_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin pattern map from the metrics board."""

    board = metrics_board or load_aas_coordination_observability_success_metrics_board(
        artifact_dir=artifact_dir
    )
    _assert_metrics_board_conservative(board)

    safe_to_claim = _dedupe(
        [
            *board["claim_boundaries"]["safe_to_claim"],
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
            AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *board["claim_boundaries"]["do_not_claim_yet"],
            *MULTIPLIER_PATTERN_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    pattern_map = {
        "schema": AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA,
        "map_id": f"aas_coordination_multiplier_pattern_map:{board['proof_anchor_id']}",
        "proof_anchor_id": board["proof_anchor_id"],
        "coordination_session_id": board["coordination_session_id"],
        "compact_decision_id": board["compact_decision_id"],
        "review_packet_id": board["review_packet_id"],
        "source_board_id": board["board_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME],
            "consumes_only": [AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME],
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
            "reads_raw_transcripts": False,
            "reads_unreviewed_memory": False,
            "reads_private_operator_context": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "writes_customer_copy": False,
            "changes_runtime_session_manager": False,
            "enables_cross_project_autorouting": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
            "semantic_reinterpretation_performed": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "network_route_registered": False,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "operator_queue_launched": False,
            "dispatch_enabled": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "readiness": _readiness(),
        "pattern_edges": _pattern_edges(board),
        "multiplier_hypotheses": _multiplier_hypotheses(board),
        "scaling_rules": _scaling_rules(board),
        "operator_next_actions": _operator_next_actions(board),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "map_verdict": "coordination_multiplier_patterns_mapped_internal_only",
        "operator_instruction": (
            "Use this map as the coordination pattern playbook for future AAS agents: "
            "four IDs first, declared-vs-verified badges, sticky blocked claims, "
            "one-next-proof discipline, and prerequisite honesty. Do not treat it as "
            "approval for live memory, IRC runtime changes, customer/public surfaces, "
            "dispatch, payment claims, reputation, GPS/raw metadata release, or worker doctrine."
        ),
    }
    _assert_pattern_map_conservative(pattern_map)
    return pattern_map


def write_aas_coordination_multiplier_pattern_map(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic coordination multiplier pattern map."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    pattern_map = build_aas_coordination_multiplier_pattern_map(artifact_dir=base_dir)
    path = base_dir / AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME
    path.write_text(json.dumps(pattern_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_coordination_multiplier_pattern_map(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted coordination multiplier pattern map."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        pattern_map = json.load(fh)
    board = load_aas_coordination_observability_success_metrics_board(artifact_dir=base_dir)
    _assert_pattern_map_conservative(pattern_map)
    if pattern_map != build_aas_coordination_multiplier_pattern_map(
        artifact_dir=base_dir, metrics_board=board
    ):
        raise CityOpsContractError("coordination multiplier pattern map drifted from source board")
    return pattern_map


def _readiness() -> dict[str, bool]:
    readiness = {
        "pattern_map_landed": True,
        "source_metrics_board_consumed": True,
        "coordination_patterns_identified": True,
        "scaling_rules_documented": True,
        "next_proof_slots_preserved": True,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _pattern_edges(board: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = {card["metric"]: card for card in board["success_metric_cards"]}
    return [
        {
            "edge": "memory_to_runtime_truth",
            "pattern": "prerequisite honesty compounds faster than optimistic runtime claims",
            "source_metric": "acontext_prerequisite_honesty",
            "observed": bool(metrics["acontext_prerequisite_honesty"]["observed"]),
            "multiplier_effect": "future agents can continue setup without reopening raw logs or overclaiming sink readiness",
            "authorizes_live_runtime": False,
        },
        {
            "edge": "irc_to_handoff_continuity",
            "pattern": "four stable IDs scale better than raw transcript replay",
            "source_metric": "four_id_handoff_completeness",
            "observed": bool(metrics["four_id_handoff_completeness"]["observed"]),
            "multiplier_effect": "handoffs become compact, comparable, and safe to pass between agents",
            "authorizes_runtime_session_manager_change": False,
        },
        {
            "edge": "cross_project_to_claim_discipline",
            "pattern": "safe claims only remain useful when blocked claims travel beside them",
            "source_metric": "claim_boundary_integrity",
            "observed": bool(metrics["claim_boundary_integrity"]["observed"]),
            "multiplier_effect": "adjacent AAS packages can reuse insights without inheriting launch claims",
            "authorizes_customer_copy_or_public_route": False,
        },
        {
            "edge": "observability_to_agent_selection",
            "pattern": "agent quality should score boundary preservation plus one-next-proof behavior",
            "source_metric": "one_next_proof_discipline",
            "observed": bool(metrics["one_next_proof_discipline"]["observed"]),
            "multiplier_effect": "future swarms can pick agents that reduce coordination risk instead of merely adding output volume",
            "authorizes_reputation_or_public_score": False,
        },
    ]


def _multiplier_hypotheses(board: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = {track["track"]: track for track in board["integration_tracks"]}
    return [
        {
            "hypothesis": "memory_bridge_becomes_compounding_after_live_parity",
            "input_track": "memory_system_to_acontext_integration",
            "current_state": tracks["memory_system_to_acontext_integration"]["current_state"],
            "proof_required_before_promotion": "empty readiness gate plus one successful live write/retrieve parity pass",
            "safe_now": "preserve blocker state and explicit-venv preflight path",
            "promotes_readiness_now": False,
        },
        {
            "hypothesis": "irc_coordination_scales_through_id_headers_not_context_bulk",
            "input_track": "irc_session_management_enhancement",
            "current_state": tracks["irc_session_management_enhancement"]["current_state"],
            "proof_required_before_promotion": "separate runtime session-manager change with tests and rollback",
            "safe_now": "require four-id handoff headers in future AAS artifacts",
            "promotes_readiness_now": False,
        },
        {
            "hypothesis": "cross_project_intelligence_is_a_filter_not_an_autopilot",
            "input_track": "cross_project_decision_support",
            "current_state": tracks["cross_project_decision_support"]["current_state"],
            "proof_required_before_promotion": "operator-approved routing policy with customer/public boundaries tested",
            "safe_now": "reuse only safe/blocked verdict pairs for internal prioritization",
            "promotes_readiness_now": False,
        },
        {
            "hypothesis": "agent_success_metrics_should_reward_not_launching_too_early",
            "input_track": "agent_observability_success_metrics",
            "current_state": tracks["agent_observability_success_metrics"]["current_state"],
            "proof_required_before_promotion": "separate private dashboard or scoring artifact; no ERC-8004 receipt by default",
            "safe_now": "score boundary preservation, ID continuity, prerequisite honesty, and one-next-proof discipline",
            "promotes_readiness_now": False,
        },
    ]


def _scaling_rules(board: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rule": "start_every_future_aas_handoff_with_four_ids",
            "required_fields": [
                "proof_anchor_id",
                "coordination_session_id",
                "compact_decision_id",
                "review_packet_id",
            ],
            "source_values_present": all(
                board.get(key)
                for key in [
                    "proof_anchor_id",
                    "coordination_session_id",
                    "compact_decision_id",
                    "review_packet_id",
                ]
            ),
            "customer_visible": False,
        },
        {
            "rule": "badge_every_strength_as_declared_or_verified",
            "reason": "prevents stale production/payment claims from becoming fresh proof",
            "authorizes_new_strength_claims": False,
            "customer_visible": False,
        },
        {
            "rule": "carry_sticky_blocked_claims_across_all_reuse",
            "minimum": "safe_to_claim and do_not_claim_yet must stay adjacent and disjoint",
            "source_boundary_integrity": True,
            "customer_visible": False,
        },
        {
            "rule": "one_next_proof_slot_per_agent_window",
            "reason": "coordination scales when every agent leaves one concrete proof gate, not five vague branches",
            "current_next_proof": "complete Acontext prerequisites then rerun read-only preflight before any live parity attempt",
            "customer_visible": False,
        },
    ]


def _operator_next_actions(board: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "action": "reuse_pattern_map_in_next_aas_handoff",
            "how": "copy the four-id header plus safe/blocked claim adjacency into the next proof artifact",
            "unlocks": "better agent continuity only",
        },
        {
            "action": "finish_acontext_prerequisites_before_runtime_claim",
            "how": "complete compose startup and API/dashboard reachability, then rebuild preflight chain",
            "unlocks": "possible live parity attempt only if the gate is empty",
        },
        {
            "action": "keep_customer_and_dispatch_claims_blocked",
            "how": "route customer exposure, queue launch, dispatch, reputation, and pricing through separate approval artifacts",
            "unlocks": "nothing automatically from this map",
        },
    ]


def _assert_metrics_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA:
        raise CityOpsContractError("unexpected coordination metrics board schema")
    _assert_false_flags(board.get("readiness", {}), [
        "live_acontext_memory_integration_ready",
        "irc_session_manager_runtime_enhanced",
        "cross_project_decision_support_customer_ready",
        "agent_observability_live_dashboard_ready",
        "success_metrics_public_or_customer_visible",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "payment_coverage_reverified_by_this_board",
        "production_infrastructure_reverified_by_this_board",
        "gps_or_metadata_exposure_allowed",
        "worker_copyable_doctrine_ready",
    ])
    for track in board.get("integration_tracks", []):
        for key, value in track.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("source metrics board promoted authorization")
    _assert_claim_boundaries(
        board["claim_boundaries"]["safe_to_claim"],
        board["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_pattern_map_conservative(pattern_map: dict[str, Any]) -> None:
    if pattern_map.get("schema") != AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA:
        raise CityOpsContractError("unexpected coordination multiplier pattern map schema")
    _assert_false_flags(pattern_map.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(pattern_map.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(pattern_map.get("readiness", {}), _FALSE_READINESS_FLAGS)
    for edge in pattern_map.get("pattern_edges", []):
        for key, value in edge.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("pattern edge promoted authorization")
    for hypothesis in pattern_map.get("multiplier_hypotheses", []):
        if hypothesis.get("promotes_readiness_now") is not False:
            raise CityOpsContractError("hypothesis promoted readiness")
    _assert_claim_boundaries(
        pattern_map["claim_boundaries"]["safe_to_claim"],
        pattern_map["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_false_flags(payload: dict[str, Any], flags: list[str]) -> None:
    for flag in flags:
        if flag in payload and payload[flag] is not False:
            raise CityOpsContractError(f"promoted forbidden flag: {flag}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
