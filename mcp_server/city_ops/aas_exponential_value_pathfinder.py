"""Internal/admin exponential-value pathfinder for AAS coordination.

This module turns the strength-connection control packet into a narrow
pathfinder: which late-night connections create compounding value, which proof
slot should move next, and which claims stay quarantined.  It is deliberately
read-only and internal/admin only.  It performs no live Acontext writes or
retrievals, changes no IRC runtime manager, creates no customer/public surface,
enables no dispatch, emits no reputation receipt, does not reverify payment or
production infrastructure, and exposes no GPS/raw metadata or worker doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_strength_connection_control_packet import (
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME,
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA,
    STRENGTH_CONNECTION_BLOCKED_CLAIMS,
    load_aas_strength_connection_control_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA = "city_ops.aas_exponential_value_pathfinder.v1"
AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME = "aas_exponential_value_pathfinder.json"
AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM = (
    "admin_aas_exponential_value_pathfinder_landed"
)

EXPONENTIAL_VALUE_BLOCKED_CLAIMS = [
    *STRENGTH_CONNECTION_BLOCKED_CLAIMS,
    "pathfinder_promotes_live_acontext_memory",
    "pathfinder_changes_irc_runtime_session_manager",
    "pathfinder_enables_cross_project_autorouting",
    "pathfinder_enables_autonomous_prioritization",
    "pathfinder_is_customer_or_public_dashboard",
    "pathfinder_authorizes_customer_delivery_or_publication",
    "pathfinder_authorizes_dispatch_or_operator_queue",
    "pathfinder_emits_erc8004_reputation_or_worker_skill_dna",
    "pathfinder_revalidates_payment_or_production_infrastructure",
    "pathfinder_allows_gps_or_raw_metadata",
    "pathfinder_publishes_worker_copyable_doctrine",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "changes_runtime_session_manager",
    "enables_cross_project_autorouting",
    "enables_autonomous_prioritization",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "reverifies_payment_coverage",
    "reverifies_production_infrastructure",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "operator_queue_launched",
    "dispatch_enabled",
    "autonomous_prioritization_enabled",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "pathfinder_promotes_live_readiness",
    "live_acontext_memory_integration_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "irc_runtime_coordination_ready",
    "irc_session_manager_runtime_enhanced",
    "cross_project_autorouting_ready",
    "autonomous_prioritization_ready",
    "agent_observability_live_dashboard_ready",
    "customer_visible_packaging_ready",
    "customer_delivery_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "agent_success_score_reputation_ready",
    "worker_skill_dna_ready",
    "pricing_or_customer_quote_ready",
    "payment_coverage_reverified_by_this_pathfinder",
    "production_infrastructure_reverified_by_this_pathfinder",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_exponential_value_pathfinder(
    *,
    artifact_dir: str | Path | None = None,
    strength_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin exponential-value pathfinder."""

    source = strength_packet or load_aas_strength_connection_control_packet(
        artifact_dir=artifact_dir
    )
    _assert_strength_packet_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
            AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *EXPONENTIAL_VALUE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    pathfinder = {
        "schema": AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA,
        "pathfinder_id": f"aas_exponential_value_pathfinder:{source['proof_anchor_id']}",
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "source_strength_packet_id": source["packet_id"],
        "derived_from": _derived_from(),
        "access_policy": _access_policy(),
        "readiness": _readiness(),
        "four_id_handoff_header": _four_id_handoff_header(source),
        "exponential_value_loops": _exponential_value_loops(source),
        "ranked_pathways": _ranked_pathways(source),
        "proof_selection_rules": _proof_selection_rules(),
        "recommended_next_proof": _recommended_next_proof(source),
        "quarantine_table": _quarantine_table(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "pathfinder_verdict": "exponential_value_connections_mapped_internal_admin_only",
        "operator_instruction": (
            "Use this pathfinder for 4am AAS strategy only: choose one proof slot, "
            "carry the four invariant IDs, and convert every breakthrough connection "
            "into a bounded admin artifact or a quarantine. It does not authorize live "
            "Acontext, IRC runtime changes, customer/public surfaces, dispatch, pricing, "
            "payment/production claims, reputation, GPS/raw metadata release, or worker doctrine."
        ),
    }
    _assert_pathfinder_conservative(pathfinder)
    return pathfinder


def write_aas_exponential_value_pathfinder(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic exponential-value pathfinder."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    pathfinder = build_aas_exponential_value_pathfinder(artifact_dir=base_dir)
    path = base_dir / AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME
    path.write_text(json.dumps(pathfinder, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_exponential_value_pathfinder(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted exponential-value pathfinder."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        pathfinder = json.load(fh)
    source = load_aas_strength_connection_control_packet(artifact_dir=base_dir)
    _assert_pathfinder_conservative(pathfinder)
    if pathfinder != build_aas_exponential_value_pathfinder(
        artifact_dir=base_dir,
        strength_packet=source,
    ):
        raise CityOpsContractError("exponential-value pathfinder drifted from strength packet")
    return pathfinder


def _derived_from() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "read_only": True,
        "source_artifacts": [AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME],
        "consumes_only": [AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME],
        "forbidden_inputs": [
            "raw_transcripts",
            "unreviewed_memory",
            "private_operator_context",
            "live_acontext_sink_writes",
            "live_acontext_retrievals",
            "irc_runtime_mutations",
            "payment_processor_probe",
            "production_health_probe",
            "gps_or_raw_metadata_payloads",
            "customer_copy_drafts",
            "worker_instruction_templates",
        ],
    }
    for flag in _FALSE_DERIVED_FLAGS:
        payload[flag] = False
    return payload


def _access_policy() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "audience": "internal_admin_only",
        "requires_admin_context": True,
    }
    for flag in _FALSE_ACCESS_FLAGS:
        payload[flag] = False
    return payload


def _readiness() -> dict[str, bool]:
    readiness = {
        "pathfinder_landed": True,
        "source_strength_packet_consumed": True,
        "exponential_value_loops_named": True,
        "ranked_pathways_documented": True,
        "one_next_proof_selected_from_existing_queue": True,
        "four_id_handoff_preserved": True,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _four_id_handoff_header(source: dict[str, Any]) -> dict[str, str]:
    return {
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "handoff_rule": "these_four_ids_precede_every_exponential_value_recommendation",
    }


def _exponential_value_loops(source: dict[str, Any]) -> list[dict[str, Any]]:
    lanes = {lane["lane"]: lane for lane in source["integration_lane_cards"]}
    strengths = {card["strength"]: card for card in source["strength_connection_cards"]}
    return [
        {
            "loop": "memory_insight_to_acontext_proof_loop",
            "source_signal": lanes["memory_system_to_acontext"]["source_signal"],
            "compounding_connection": (
                "reviewed memory insights become Acontext candidate packets only after "
                "the prerequisite gate and one live parity attempt prove the transport"
            ),
            "multiplier_effect": "every future AAS proof can reuse reviewed context without rereading raw transcripts",
            "first_safe_next_proof": lanes["memory_system_to_acontext"]["next_gate"],
            "value_score": 5,
            "authorizes_live_runtime": False,
            "authorizes_customer_surface": False,
            "may_auto_promote": False,
        },
        {
            "loop": "irc_four_id_to_swarm_handoff_loop",
            "source_signal": lanes["irc_session_management"]["source_signal"],
            "compounding_connection": (
                "IRC coordination scales when agents pass invariant IDs and blocked claims "
                "instead of broad transcript context"
            ),
            "multiplier_effect": "more agents can join without reopening stopped projects or leaking private context",
            "first_safe_next_proof": lanes["irc_session_management"]["next_gate"],
            "value_score": 4,
            "authorizes_runtime_session_manager_change": False,
            "authorizes_customer_surface": False,
            "may_auto_promote": False,
        },
        {
            "loop": "cross_project_signal_to_aas_gate_selection_loop",
            "source_signal": lanes["cross_project_decision_support"]["source_signal"],
            "compounding_connection": (
                "cross-project intelligence is useful only when converted into one named "
                "AAS proof gate plus explicit quarantine rules"
            ),
            "multiplier_effect": "strategy becomes executable without letting adjacent projects steer the dream session",
            "first_safe_next_proof": lanes["cross_project_decision_support"]["next_gate"],
            "value_score": 4,
            "authorizes_autonomous_routing": False,
            "authorizes_customer_surface": False,
            "may_auto_promote": False,
        },
        {
            "loop": "agent_observability_to_private_selection_loop",
            "source_signal": lanes["agent_observability_success_metrics"]["source_signal"],
            "compounding_connection": (
                "coordination quality can become an internal selection signal before any "
                "ERC-8004 reputation or Worker Skill DNA artifact exists"
            ),
            "multiplier_effect": "future agents are scored by proof discipline, not vibes or public claims",
            "first_safe_next_proof": lanes["agent_observability_success_metrics"]["next_gate"],
            "value_score": 3,
            "authorizes_reputation": False,
            "authorizes_worker_skill_dna": False,
            "may_auto_promote": False,
        },
        {
            "loop": "landed_code_to_proof_ladder_loop",
            "source_signal": strengths["latest_city_ops_code_changes"]["verification_badge"],
            "compounding_connection": (
                "small deterministic builders, persisted fixtures, and fail-closed tests "
                "turn each insight into a reusable AAS ladder rung"
            ),
            "multiplier_effect": "every dream can advance the portfolio without customer overclaim or stale priority drift",
            "first_safe_next_proof": source["one_next_proof_queue"][0]["proof"],
            "value_score": 5,
            "authorizes_customer_surface": False,
            "authorizes_dispatch": False,
            "may_auto_promote": False,
        },
    ]


def _ranked_pathways(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "pathway": "prove_acontext_runtime_memory_prerequisites_then_single_live_parity_attempt",
            "why_this_compounds": "unblocks reviewed memory reuse for every AAS family while preserving source boundaries",
            "source_queue_slot": source["one_next_proof_queue"][0]["slot"],
            "allowed_next_artifact_class": "internal_admin_prerequisite_or_parity_attempt_record",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "rank": 2,
            "pathway": "codify_four_id_irc_handoff_for_future_agents",
            "why_this_compounds": "lets coordination scale by IDs, claim boundaries, and one-proof discipline",
            "allowed_next_artifact_class": "internal_admin_runtime_design_or_read_surface_only",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "rank": 3,
            "pathway": "private_agent_success_scoring_gate",
            "why_this_compounds": "turns coordination quality into internal assignment signal before reputation exposure",
            "allowed_next_artifact_class": "internal_admin_private_scoring_gate_only",
            "customer_visible": False,
            "may_auto_promote": False,
        },
    ]


def _proof_selection_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule": "one_next_proof_only",
            "meaning": "pick exactly one proof slot before adding customer, dispatch, or reputation surface area",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "rule": "declared_context_never_equals_reverified_fact",
            "meaning": "payment, production, and live runtime claims require separate fresh probes",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "rule": "cross_project_intelligence_must_be_quarantined_into_aas_artifacts",
            "meaning": "adjacent signals can inform Execution Market AAS only through explicit safe/blocked claims",
            "customer_visible": False,
            "may_auto_promote": False,
        },
    ]


def _recommended_next_proof(source: dict[str, Any]) -> dict[str, Any]:
    queued = source["one_next_proof_queue"][0]
    return {
        "selected_from_source_queue": True,
        "source_slot": queued["slot"],
        "proof": queued["proof"],
        "selection_reason": (
            "it is the highest-multiplier blocker: once live memory prerequisites and one parity "
            "attempt are proven, reviewed AAS intelligence can flow without raw transcript replay"
        ),
        "fallback_if_blocked": queued["fallback_if_blocked"],
        "customer_visible": False,
        "may_auto_promote": False,
    }


def _quarantine_table() -> list[dict[str, Any]]:
    return [
        {
            "tempting_connection": "memory_system_data_directly_into_live_acontext",
            "quarantine_until": "separate prerequisite gate plus single live parity attempt passes",
            "blocked_claim": "pathfinder_promotes_live_acontext_memory",
        },
        {
            "tempting_connection": "irc_coordination_patterns_change_runtime_manager",
            "quarantine_until": "separate runtime-session-manager enhancement proof exists",
            "blocked_claim": "pathfinder_changes_irc_runtime_session_manager",
        },
        {
            "tempting_connection": "coordination_scores_become_erc8004_reputation_or_worker_skill_dna",
            "quarantine_until": "private scoring gate and explicit reputation publication approval exist",
            "blocked_claim": "pathfinder_emits_erc8004_reputation_or_worker_skill_dna",
        },
        {
            "tempting_connection": "portfolio_packaging_goes_customer_visible",
            "quarantine_until": "separate customer delivery/publication/pricing gate is approved",
            "blocked_claim": "pathfinder_authorizes_customer_delivery_or_publication",
        },
    ]


def _assert_strength_packet_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected strength-connection packet schema")
    _assert_false_flags(source.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(
        source.get("readiness", {}),
        [
            "packet_promotes_live_readiness",
            "live_acontext_memory_integration_ready",
            "acontext_sink_ready",
            "runtime_parity_proven",
            "irc_runtime_coordination_ready",
            "irc_session_manager_runtime_enhanced",
            "cross_project_autorouting_ready",
            "autonomous_prioritization_ready",
            "agent_observability_live_dashboard_ready",
            "customer_visible_packaging_ready",
            "public_route_ready",
            "operator_queue_launch_ready",
            "dispatch_ready",
            "autonomous_dispatch_ready",
            "erc8004_reputation_ready",
            "agent_success_score_reputation_ready",
            "worker_skill_dna_ready",
            "payment_coverage_reverified_by_this_packet",
            "production_infrastructure_reverified_by_this_packet",
            "gps_or_metadata_exposure_allowed",
            "worker_copyable_doctrine_ready",
        ],
    )
    for lane in source.get("integration_lane_cards", []):
        for key, value in lane.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("source strength lane promoted authorization")
    for proof in source.get("one_next_proof_queue", []):
        if proof.get("customer_visible") is not False:
            raise CityOpsContractError("source next proof promoted visibility")
        if proof.get("may_auto_promote") is not False:
            raise CityOpsContractError("source next proof promoted readiness")
    _assert_claim_boundaries(
        source["claim_boundaries"]["safe_to_claim"],
        source["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_pathfinder_conservative(pathfinder: dict[str, Any]) -> None:
    if pathfinder.get("schema") != AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA:
        raise CityOpsContractError("unexpected exponential-value pathfinder schema")
    _assert_false_flags(pathfinder.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(pathfinder.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(pathfinder.get("readiness", {}), _FALSE_READINESS_FLAGS)
    for loop in pathfinder.get("exponential_value_loops", []):
        for key, value in loop.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("value loop promoted authorization")
        if loop.get("may_auto_promote") is not False:
            raise CityOpsContractError("value loop promoted readiness")
    for pathway in pathfinder.get("ranked_pathways", []):
        if pathway.get("customer_visible") is not False:
            raise CityOpsContractError("pathway promoted visibility")
        if pathway.get("may_auto_promote") is not False:
            raise CityOpsContractError("pathway promoted readiness")
    for rule in pathfinder.get("proof_selection_rules", []):
        if rule.get("customer_visible") is not False:
            raise CityOpsContractError("proof rule promoted visibility")
        if rule.get("may_auto_promote") is not False:
            raise CityOpsContractError("proof rule promoted readiness")
    next_proof = pathfinder.get("recommended_next_proof", {})
    if next_proof.get("customer_visible") is not False:
        raise CityOpsContractError("recommended proof promoted visibility")
    if next_proof.get("may_auto_promote") is not False:
        raise CityOpsContractError("recommended proof promoted readiness")
    _assert_claim_boundaries(
        pathfinder["claim_boundaries"]["safe_to_claim"],
        pathfinder["claim_boundaries"]["do_not_claim_yet"],
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
