"""Internal/admin strength-connection control packet for AAS.

This module joins the current AAS coordination metrics read surface with the
intelligence-flow compounder.  It is a conservative handoff packet: it names how
current strengths reinforce each other, but it does not promote live Acontext,
IRC runtime, payment, production, customer, dispatch, reputation, GPS/metadata,
or worker-doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_coordination_observability_success_metrics_read_surface import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SAFE_CLAIM,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA,
    READ_SURFACE_BLOCKED_CLAIMS,
    load_aas_coordination_observability_success_metrics_read_surface,
)
from .aas_intelligence_flow_compounder import (
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA,
    INTELLIGENCE_FLOW_BLOCKED_CLAIMS,
    load_aas_intelligence_flow_compounder,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA = (
    "city_ops.aas_strength_connection_control_packet.v1"
)
AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME = (
    "aas_strength_connection_control_packet.json"
)
AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM = (
    "admin_aas_strength_connection_control_packet_landed"
)

STRENGTH_CONNECTION_BLOCKED_CLAIMS = [
    *READ_SURFACE_BLOCKED_CLAIMS,
    *INTELLIGENCE_FLOW_BLOCKED_CLAIMS,
    "strength_packet_promotes_live_acontext_memory",
    "strength_packet_changes_irc_runtime_session_manager",
    "strength_packet_makes_cross_project_autorouting_ready",
    "strength_packet_is_customer_or_public_dashboard",
    "strength_packet_authorizes_dispatch_or_operator_queue",
    "strength_packet_emits_erc8004_reputation_or_worker_skill_dna",
    "strength_packet_revalidates_eight_chain_payments",
    "strength_packet_revalidates_production_infrastructure",
    "strength_packet_allows_gps_or_raw_metadata",
    "strength_packet_publishes_worker_copyable_doctrine",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "writes_municipal_memory",
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
    "pricing_or_customer_quote_ready",
    "payment_coverage_reverified_by_this_packet",
    "production_infrastructure_reverified_by_this_packet",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_strength_connection_control_packet(
    *,
    artifact_dir: str | Path | None = None,
    metrics_surface: dict[str, Any] | None = None,
    intelligence_compounder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin strength-connection packet."""

    surface = metrics_surface or load_aas_coordination_observability_success_metrics_read_surface(
        artifact_dir=artifact_dir
    )
    compounder = intelligence_compounder or load_aas_intelligence_flow_compounder(
        artifact_dir=artifact_dir
    )
    _assert_metrics_surface_conservative(surface)
    _assert_compounder_conservative(compounder)
    _assert_sources_share_invariant_ids(surface, compounder)

    safe_to_claim = _dedupe(
        [
            *surface["claim_boundaries"]["safe_to_claim"],
            *compounder["claim_boundaries"]["safe_to_claim"],
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SAFE_CLAIM,
            AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
            AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *surface["claim_boundaries"]["do_not_claim_yet"],
            *compounder["claim_boundaries"]["do_not_claim_yet"],
            *STRENGTH_CONNECTION_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    packet = {
        "schema": AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA,
        "packet_id": f"aas_strength_connection_control_packet:{surface['proof_anchor_id']}",
        "proof_anchor_id": surface["proof_anchor_id"],
        "coordination_session_id": surface["coordination_session_id"],
        "compact_decision_id": surface["compact_decision_id"],
        "review_packet_id": surface["review_packet_id"],
        "source_metrics_surface_id": surface["surface_id"],
        "source_intelligence_compounder_id": compounder["compounder_id"],
        "derived_from": _derived_from(),
        "access_policy": _access_policy(),
        "readiness": _readiness(),
        "handoff_header": _handoff_header(surface),
        "strength_connection_cards": _strength_connection_cards(surface, compounder),
        "integration_lane_cards": _integration_lane_cards(surface, compounder),
        "control_plane_action_cards": _control_plane_action_cards(),
        "one_next_proof_queue": _one_next_proof_queue(compounder),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "packet_verdict": "strength_connections_mapped_internal_admin_only",
        "operator_instruction": (
            "Use this packet as the compact 3am handoff after DREAM-PRIORITIES: "
            "carry the four invariant IDs, use strengths only at their declared or "
            "consumed verification level, pick one next proof, and keep every live, "
            "customer, dispatch, payment, production, reputation, GPS, and worker-doctrine "
            "claim quarantined until a separate gate proves it."
        ),
    }
    _assert_packet_conservative(packet)
    return packet


def write_aas_strength_connection_control_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic strength-connection packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_strength_connection_control_packet(artifact_dir=base_dir)
    path = base_dir / AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_strength_connection_control_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted strength-connection packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        packet = json.load(fh)
    surface = load_aas_coordination_observability_success_metrics_read_surface(
        artifact_dir=base_dir
    )
    compounder = load_aas_intelligence_flow_compounder(artifact_dir=base_dir)
    _assert_packet_conservative(packet)
    if packet != build_aas_strength_connection_control_packet(
        artifact_dir=base_dir,
        metrics_surface=surface,
        intelligence_compounder=compounder,
    ):
        raise CityOpsContractError("strength-connection control packet drifted from sources")
    return packet


def _derived_from() -> dict[str, Any]:
    payload = {
        "read_only": True,
        "source_artifacts": [
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME,
            AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
        ],
        "consumes_only": [
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME,
            AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
        ],
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
    payload = {
        "audience": "internal_admin_only",
        "requires_admin_context": True,
    }
    for flag in _FALSE_ACCESS_FLAGS:
        payload[flag] = False
    return payload


def _readiness() -> dict[str, bool]:
    readiness = {
        "packet_landed": True,
        "source_metrics_surface_consumed": True,
        "source_intelligence_compounder_consumed": True,
        "strength_connections_named": True,
        "four_id_handoff_preserved": True,
        "one_next_proof_queue_preserved": True,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _handoff_header(surface: dict[str, Any]) -> dict[str, str]:
    return {
        "proof_anchor_id": surface["proof_anchor_id"],
        "coordination_session_id": surface["coordination_session_id"],
        "compact_decision_id": surface["compact_decision_id"],
        "review_packet_id": surface["review_packet_id"],
        "handoff_rule": "include_these_four_ids_before_any_recommendation",
    }


def _strength_connection_cards(
    surface: dict[str, Any], compounder: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "strength": "latest_city_ops_code_changes",
            "verification_badge": "consumed_from_local_artifact_graph",
            "source": surface["source_board_id"],
            "amplifies": "uses landed read surfaces as the bounded implementation substrate",
            "safe_reuse": "extend from persisted fixtures and tested builders, not raw session memory",
            "reverified_by_this_packet": False,
            "authorizes_live_or_customer_readiness": False,
        },
        {
            "strength": "eight_chain_payment_integration_perfection",
            "verification_badge": "declared_context_only_not_reverified_here",
            "source": "current_strength_context",
            "amplifies": "keeps AAS packaging shaped around production-grade payment confidence",
            "safe_reuse": "treat as context until a separate payment/infra probe refreshes it",
            "reverified_by_this_packet": False,
            "authorizes_live_or_customer_readiness": False,
        },
        {
            "strength": "intelligent_memory_with_26_plus_insights",
            "verification_badge": "declared_context_plus_reviewed_memory_search_not_live_sink",
            "source": compounder["compounder_id"],
            "amplifies": "turns prior insights into bounded Acontext candidates and next-proof constraints",
            "safe_reuse": "carry reviewed insight IDs and blocker state; do not write live memory here",
            "reverified_by_this_packet": False,
            "authorizes_live_or_customer_readiness": False,
        },
        {
            "strength": "production_infrastructure_operational",
            "verification_badge": "declared_context_only_not_reverified_here",
            "source": "current_strength_context",
            "amplifies": "biases the roadmap toward deployable admin seams once separate probes pass",
            "safe_reuse": "keep deployment confidence separate from this planning artifact",
            "reverified_by_this_packet": False,
            "authorizes_live_or_customer_readiness": False,
        },
        {
            "strength": "legendary_agent_coordination",
            "verification_badge": "consumed_from_coordination_metrics_surface",
            "source": surface["surface_id"],
            "amplifies": "makes invariant IDs, declared-vs-verified badges, sticky blocked claims, and one next-proof discipline the default handoff protocol",
            "safe_reuse": "score future work by boundary preservation and compact proof deltas",
            "reverified_by_this_packet": False,
            "authorizes_live_or_customer_readiness": False,
        },
    ]


def _integration_lane_cards(
    surface: dict[str, Any], compounder: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "lane": "memory_system_to_acontext",
            "source_signal": compounder["intelligence_flows"][0]["flow"],
            "safe_connection": "reviewed memory becomes Acontext candidate packets after prerequisites clear",
            "next_gate": "empty prerequisite gate plus one live write/retrieve parity pass",
            "authorizes_live_runtime": False,
        },
        {
            "lane": "irc_session_management",
            "source_signal": "four_id_header_from_metrics_surface",
            "safe_connection": "IRC/admin handoffs pass invariant IDs instead of transcripts",
            "next_gate": "separate runtime session-manager enhancement proof",
            "authorizes_runtime_session_manager_change": False,
        },
        {
            "lane": "cross_project_decision_support",
            "source_signal": compounder["decision_table"][2]["decision"],
            "safe_connection": "adjacent AAS decisions reuse the same safe/blocked claim pair discipline",
            "next_gate": "separate customer/public packaging or autorouting approval gate",
            "authorizes_autonomous_routing": False,
        },
        {
            "lane": "agent_observability_success_metrics",
            "source_signal": surface["agent_success_rubric_cards"][0]["rubric"],
            "safe_connection": "future agents can be judged by claim-boundary integrity and one-next-proof discipline",
            "next_gate": "separate private scoring gate before any reputation or public metric",
            "authorizes_live_dashboard_or_reputation": False,
        },
    ]


def _control_plane_action_cards() -> list[dict[str, Any]]:
    return [
        {
            "action": "make_strength_packet_the_first_internal_handoff_after_dream_priorities",
            "why": "prevents stale cron priorities from reopening stopped projects or broadening scope",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "action": "convert_every_strength_into_one_gate_or_one_quarantine",
            "why": "keeps confidence useful without turning declared context into fake proof",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "action": "use_coordination_quality_as_internal_agent_selection_signal_only",
            "why": "rewards small verified deltas before any ERC-8004 reputation or Skill DNA path exists",
            "customer_visible": False,
            "may_auto_promote": False,
        },
    ]


def _one_next_proof_queue(compounder: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "slot": 1,
            "proof": "acontext_runtime_memory_prerequisites_then_single_live_parity_attempt",
            "source_recommendation": compounder["decision_table"][0]["internal_recommendation"],
            "fallback_if_blocked": "add only internal/admin guardrails that preserve four IDs, claim boundaries, and one next-proof discipline",
            "customer_visible": False,
            "may_auto_promote": False,
        }
    ]


def _assert_metrics_surface_conservative(surface: dict[str, Any]) -> None:
    if surface.get("schema") != AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("unexpected coordination metrics read surface schema")
    _assert_false_flags(surface.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(
        surface.get("readiness", {}),
        [
            "surface_promotes_live_readiness",
            "live_acontext_memory_integration_ready",
            "acontext_sink_ready",
            "runtime_parity_proven",
            "irc_session_manager_runtime_enhanced",
            "cross_project_decision_support_customer_ready",
            "agent_observability_live_dashboard_ready",
            "customer_visible_packaging_ready",
            "public_route_ready",
            "autonomous_dispatch_ready",
            "erc8004_reputation_ready",
            "worker_skill_dna_ready",
            "payment_coverage_reverified_by_this_surface",
            "production_infrastructure_reverified_by_this_surface",
            "gps_or_metadata_exposure_allowed",
            "worker_copyable_doctrine_ready",
        ],
    )
    _assert_claim_boundaries(
        surface["claim_boundaries"]["safe_to_claim"],
        surface["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_compounder_conservative(compounder: dict[str, Any]) -> None:
    if compounder.get("schema") != AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA:
        raise CityOpsContractError("unexpected intelligence-flow compounder schema")
    _assert_false_flags(compounder.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(
        compounder.get("readiness", {}),
        [
            "compounder_promotes_live_readiness",
            "live_acontext_memory_integration_ready",
            "irc_runtime_coordination_ready",
            "cross_project_autorouting_ready",
            "autonomous_prioritization_ready",
            "customer_visible_packaging_ready",
            "public_route_ready",
            "controlled_pilot_ready",
            "operator_queue_launch_ready",
            "dispatch_ready",
            "autonomous_dispatch_ready",
            "erc8004_reputation_ready",
            "agent_success_score_reputation_ready",
            "payment_coverage_reverified_by_this_compounder",
            "production_infrastructure_reverified_by_this_compounder",
            "gps_or_metadata_exposure_allowed",
            "worker_copyable_doctrine_ready",
        ],
    )
    for flow in compounder.get("intelligence_flows", []):
        for key, value in flow.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("source compounder promoted authorization")
    _assert_claim_boundaries(
        compounder["claim_boundaries"]["safe_to_claim"],
        compounder["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_sources_share_invariant_ids(
    surface: dict[str, Any], compounder: dict[str, Any]
) -> None:
    for key in [
        "proof_anchor_id",
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
    ]:
        if surface.get(key) != compounder.get(key):
            raise CityOpsContractError(f"source invariant id mismatch: {key}")


def _assert_packet_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected strength-connection packet schema")
    _assert_false_flags(packet.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(packet.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(packet.get("readiness", {}), _FALSE_READINESS_FLAGS)
    for card in packet.get("strength_connection_cards", []):
        if card.get("authorizes_live_or_customer_readiness") is not False:
            raise CityOpsContractError("strength card promoted readiness")
        if card.get("reverified_by_this_packet") is not False:
            raise CityOpsContractError("strength card reverified external claim")
    for lane in packet.get("integration_lane_cards", []):
        for key, value in lane.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("integration lane promoted authorization")
    for action in packet.get("control_plane_action_cards", []):
        if action.get("customer_visible") is not False:
            raise CityOpsContractError("control action promoted visibility")
        if action.get("may_auto_promote") is not False:
            raise CityOpsContractError("control action promoted readiness")
    for proof in packet.get("one_next_proof_queue", []):
        if proof.get("customer_visible") is not False:
            raise CityOpsContractError("next proof promoted visibility")
        if proof.get("may_auto_promote") is not False:
            raise CityOpsContractError("next proof promoted readiness")
    _assert_claim_boundaries(
        packet["claim_boundaries"]["safe_to_claim"],
        packet["claim_boundaries"]["do_not_claim_yet"],
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
