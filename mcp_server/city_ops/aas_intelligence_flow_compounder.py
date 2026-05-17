"""Internal/admin intelligence-flow compounder for AAS coordination.

This module turns the coordination multiplier pattern map into a bounded
intelligence-flow artifact: which cross-project insights can compound inside
Execution Market AAS, which routing decisions remain internal/admin only, and
which claims must stay quarantined until separate proof exists.

It is intentionally conservative. It reads only the reviewed pattern map,
performs no live Acontext writes or retrievals, creates no customer/public
surface, enables no dispatch, emits no reputation receipt, and does not reverify
payment or production infrastructure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_coordination_multiplier_pattern_map import (
    AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME,
    AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SAFE_CLAIM,
    AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA,
    MULTIPLIER_PATTERN_BLOCKED_CLAIMS,
    load_aas_coordination_multiplier_pattern_map,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA = "city_ops.aas_intelligence_flow_compounder.v1"
AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME = "aas_intelligence_flow_compounder.json"
AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM = (
    "admin_aas_intelligence_flow_compounder_landed"
)

INTELLIGENCE_FLOW_BLOCKED_CLAIMS = [
    *MULTIPLIER_PATTERN_BLOCKED_CLAIMS,
    "intelligence_flow_customer_visible_by_compounder",
    "intelligence_flow_public_route_ready_by_compounder",
    "cross_project_intelligence_autonomous_prioritization_ready_by_compounder",
    "cross_project_intelligence_autonomous_routing_ready_by_compounder",
    "memory_system_live_write_retrieve_ready_by_compounder",
    "irc_runtime_coordination_channel_ready_by_compounder",
    "agent_selection_reputation_or_payment_ready_by_compounder",
    "operator_queue_or_dispatch_ready_by_compounder",
    "pricing_or_customer_quote_ready_by_compounder",
    "customer_delivery_approval_ready_by_compounder",
    "controlled_pilot_ready_by_compounder",
    "payment_or_production_reverified_by_compounder",
    "gps_or_raw_metadata_release_allowed_by_compounder",
    "worker_copyable_doctrine_ready_by_compounder",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "reads_customer_copy_drafts",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "writes_customer_copy",
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
    "pricing_or_customer_quote_ready",
    "payment_coverage_reverified_by_this_compounder",
    "production_infrastructure_reverified_by_this_compounder",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_intelligence_flow_compounder(
    *,
    artifact_dir: str | Path | None = None,
    pattern_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin intelligence-flow artifact."""

    source = pattern_map or load_aas_coordination_multiplier_pattern_map(
        artifact_dir=artifact_dir
    )
    _assert_pattern_map_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SAFE_CLAIM,
            AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *INTELLIGENCE_FLOW_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    compounder = {
        "schema": AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA,
        "compounder_id": f"aas_intelligence_flow_compounder:{source['proof_anchor_id']}",
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "source_pattern_map_id": source["map_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME],
            "consumes_only": [AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_FILENAME],
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
            "reads_customer_copy_drafts": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "writes_customer_copy": False,
            "changes_runtime_session_manager": False,
            "enables_cross_project_autorouting": False,
            "enables_autonomous_prioritization": False,
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
            "operator_queue_launched": False,
            "dispatch_enabled": False,
            "autonomous_prioritization_enabled": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "readiness": _readiness(),
        "intelligence_flows": _intelligence_flows(source),
        "compounder_rules": _compounder_rules(source),
        "quarantine_rules": _quarantine_rules(),
        "decision_table": _decision_table(),
        "operator_next_actions": _operator_next_actions(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "compounder_verdict": "cross_project_intelligence_flows_mapped_internal_only",
        "operator_instruction": (
            "Use this compounder as an internal filter for AAS dream/day handoffs: "
            "carry the four invariant IDs, transform insights into one next proof, "
            "and quarantine every customer, dispatch, reputation, payment, GPS, live "
            "memory, and worker-doctrine claim until a separate gate proves it."
        ),
    }
    _assert_compounder_conservative(compounder)
    return compounder


def write_aas_intelligence_flow_compounder(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic intelligence-flow compounder."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    compounder = build_aas_intelligence_flow_compounder(artifact_dir=base_dir)
    path = base_dir / AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME
    path.write_text(json.dumps(compounder, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_intelligence_flow_compounder(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted intelligence-flow compounder."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        compounder = json.load(fh)
    source = load_aas_coordination_multiplier_pattern_map(artifact_dir=base_dir)
    _assert_compounder_conservative(compounder)
    if compounder != build_aas_intelligence_flow_compounder(
        artifact_dir=base_dir, pattern_map=source
    ):
        raise CityOpsContractError("intelligence-flow compounder drifted from source map")
    return compounder


def _readiness() -> dict[str, bool]:
    readiness = {
        "compounder_landed": True,
        "source_pattern_map_consumed": True,
        "intelligence_flows_identified": True,
        "quarantine_rules_documented": True,
        "one_next_proof_queue_preserved": True,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _intelligence_flows(source: dict[str, Any]) -> list[dict[str, Any]]:
    edges = {edge["edge"]: edge for edge in source["pattern_edges"]}
    return [
        {
            "flow": "memory_prerequisites_to_next_proof",
            "source_edge": "memory_to_runtime_truth",
            "signal": edges["memory_to_runtime_truth"]["pattern"],
            "internal_multiplier": (
                "agents inherit the exact blocker and next proof instead of repeating "
                "optimistic runtime-memory attempts"
            ),
            "safe_reuse": "copy blocker state and next-proof wording into handoffs",
            "authorizes_live_runtime": False,
            "authorizes_customer_copy": False,
        },
        {
            "flow": "irc_handoff_ids_to_coordination_compression",
            "source_edge": "irc_to_handoff_continuity",
            "signal": edges["irc_to_handoff_continuity"]["pattern"],
            "internal_multiplier": (
                "four IDs let agents resume context without exposing raw transcripts or "
                "private operator details"
            ),
            "safe_reuse": "require proof_anchor_id, coordination_session_id, compact_decision_id, review_packet_id",
            "authorizes_runtime_session_manager_change": False,
            "authorizes_public_route": False,
        },
        {
            "flow": "cross_project_patterns_to_claim_quarantine",
            "source_edge": "cross_project_to_claim_discipline",
            "signal": edges["cross_project_to_claim_discipline"]["pattern"],
            "internal_multiplier": (
                "adjacent AAS ideas can reuse the proof ladder only when blocked claims "
                "travel with the safe claim"
            ),
            "safe_reuse": "move safe_to_claim and do_not_claim_yet as one pair",
            "authorizes_autonomous_routing": False,
            "authorizes_customer_copy_or_public_route": False,
        },
        {
            "flow": "agent_selection_to_boundary_preservation",
            "source_edge": "observability_to_agent_selection",
            "signal": edges["observability_to_agent_selection"]["pattern"],
            "internal_multiplier": (
                "coordination quality can favor agents that leave smaller, verified "
                "proof deltas rather than larger unproved surfaces"
            ),
            "safe_reuse": "score internal handoffs by boundary preservation and one-next-proof discipline",
            "authorizes_reputation_or_public_score": False,
            "authorizes_dispatch_automation": False,
        },
    ]


def _compounder_rules(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rule": "treat_cross_project_intelligence_as_a_filter_not_autopilot",
            "source_pattern_map_id": source["map_id"],
            "safe_effect": "rank internal next-proof choices by evidence freshness and blocker specificity",
            "promotes_readiness_now": False,
            "customer_visible": False,
        },
        {
            "rule": "convert_every_insight_to_one_verifiable_next_proof",
            "safe_effect": "reduce coordination fan-out and make each dream handoff testable",
            "promotes_readiness_now": False,
            "customer_visible": False,
        },
        {
            "rule": "never_separate_safe_claims_from_blocked_claims",
            "safe_effect": "prevents old launch claims from riding along with fresh internal artifacts",
            "promotes_readiness_now": False,
            "customer_visible": False,
        },
        {
            "rule": "keep_agent_quality_private_until_a_separate_scoring_gate_exists",
            "safe_effect": "supports internal operator judgment without emitting reputation receipts",
            "promotes_readiness_now": False,
            "customer_visible": False,
        },
    ]


def _quarantine_rules() -> list[dict[str, Any]]:
    return [
        {
            "claim_class": "live_runtime_memory",
            "required_separate_gate": "Acontext services healthy plus empty gate plus one write/retrieve parity pass",
            "current_compounder_action": "carry blocker and next-proof state only",
            "may_auto_promote": False,
        },
        {
            "claim_class": "customer_or_public_packaging",
            "required_separate_gate": "human-operator approval record for one exact boundary",
            "current_compounder_action": "keep customer delivery and publication false",
            "may_auto_promote": False,
        },
        {
            "claim_class": "dispatch_or_operator_queue",
            "required_separate_gate": "separate queue/dispatch policy and route readiness artifact",
            "current_compounder_action": "block launch, routing, and autonomous assignment",
            "may_auto_promote": False,
        },
        {
            "claim_class": "reputation_or_worker_skill_dna",
            "required_separate_gate": "separate ERC-8004 and worker-instruction proof path",
            "current_compounder_action": "block public scores, receipts, and worker-copyable doctrine",
            "may_auto_promote": False,
        },
        {
            "claim_class": "payment_or_production_health",
            "required_separate_gate": "fresh payment/API/dashboard/infra probe",
            "current_compounder_action": "do not repeat stale infra confidence as current proof",
            "may_auto_promote": False,
        },
    ]


def _decision_table() -> list[dict[str, Any]]:
    return [
        {
            "decision": "next_runtime_memory_step",
            "internal_recommendation": "fix_or_bypass_docker_pull_stall_then_inventory_all_required_images",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "decision": "next_customer_exposure_step",
            "internal_recommendation": "real_human_operator_approval_record_for_one_exact_boundary_or_keep_held",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "decision": "next_coordination_scaling_step",
            "internal_recommendation": "reuse_four_id_header_and_safe_blocked_claim_pairs_in_every_aas_handoff",
            "customer_visible": False,
            "may_auto_promote": False,
        },
    ]


def _operator_next_actions() -> list[dict[str, Any]]:
    return [
        {
            "action": "use_compounder_as_4am_pattern_recognition_entrypoint",
            "how": "start from flows, then pick exactly one proof gate to advance",
            "unlocks": "better internal coordination only",
        },
        {
            "action": "keep_acontext_path_prerequisite_first",
            "how": "resolve Docker pull stall or trusted cache before any compose startup claim",
            "unlocks": "possible later read-only preflight rerun",
        },
        {
            "action": "keep_customer_and_dispatch_claims_in_separate_gates",
            "how": "do not infer launch, route, pricing, dispatch, or reputation readiness from pattern insight",
            "unlocks": "nothing automatically from this compounder",
        },
    ]


def _assert_pattern_map_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_SCHEMA:
        raise CityOpsContractError("unexpected coordination multiplier pattern map schema")
    _assert_false_flags(
        source.get("readiness", {}),
        [
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
        ],
    )
    for edge in source.get("pattern_edges", []):
        for key, value in edge.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("source pattern map promoted authorization")
    for hypothesis in source.get("multiplier_hypotheses", []):
        if hypothesis.get("promotes_readiness_now") is not False:
            raise CityOpsContractError("source pattern map promoted readiness")
    _assert_claim_boundaries(
        source["claim_boundaries"]["safe_to_claim"],
        source["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_compounder_conservative(compounder: dict[str, Any]) -> None:
    if compounder.get("schema") != AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA:
        raise CityOpsContractError("unexpected intelligence-flow compounder schema")
    _assert_false_flags(compounder.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(compounder.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(compounder.get("readiness", {}), _FALSE_READINESS_FLAGS)
    for flow in compounder.get("intelligence_flows", []):
        for key, value in flow.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("intelligence flow promoted authorization")
    for rule in compounder.get("compounder_rules", []):
        if rule.get("promotes_readiness_now") is not False:
            raise CityOpsContractError("compounder rule promoted readiness")
        if rule.get("customer_visible") is not False:
            raise CityOpsContractError("compounder rule promoted visibility")
    for rule in compounder.get("quarantine_rules", []):
        if rule.get("may_auto_promote") is not False:
            raise CityOpsContractError("quarantine rule promoted readiness")
    for decision in compounder.get("decision_table", []):
        if decision.get("may_auto_promote") is not False:
            raise CityOpsContractError("decision table promoted readiness")
        if decision.get("customer_visible") is not False:
            raise CityOpsContractError("decision table promoted visibility")
    _assert_claim_boundaries(
        compounder["claim_boundaries"]["safe_to_claim"],
        compounder["claim_boundaries"]["do_not_claim_yet"],
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
