"""Internal/admin AAS system-integration decision-support map.

This proof block consumes the current AAS source-of-truth index and maps the
system-integration strengths into non-authorizing decision-support lanes. It is
read-only and default-off: no operator answer, approval, runtime mutation, live
Acontext write/retrieval, IRC/session-manager mutation, customer/worker surface,
dispatch, reputation, Worker Skill DNA, payment reverification, private context,
raw location metadata, authority claim, or stopped-project integration is
created.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_source_of_truth_index import (
    AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
    AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM,
    AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA,
    AAS_SOURCE_OF_TRUTH_INDEX_STATUS,
    SOURCE_OF_TRUTH_BLOCKED_CLAIMS,
    load_aas_source_of_truth_index,
)
from .aas_two_lane_operator_answer_schema import DEFAULT_EFFECTIVE_DECISION
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SCHEMA = (
    "city_ops.aas_system_integration_decision_support_map.v1"
)
AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME = (
    "aas_system_integration_decision_support_map.json"
)
AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM = (
    "internal_admin_aas_system_integration_decision_support_map_landed"
)
AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_ID = (
    "execution_market.aas.system_integration_decision_support_map.2026_06_03_0300"
)
AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_STATUS = (
    "read_only_decision_support_no_answer_no_approval_no_runtime_or_external_promotion"
)

INTEGRATION_LANES = [
    {
        "lane": "memory_acontext_readiness",
        "strength_connected": "intelligent_memory_insights_and_acontext_planning",
        "current_use": "carry_forward_sanitized_claim_boundaries_and_next_gate_refs_only",
        "blocked_promotion": "no_live_acontext_write_or_retrieval_without_separate_operator_answer_and_runtime_parity_gate",
    },
    {
        "lane": "irc_session_management",
        "strength_connected": "legendary_agent_coordination_and_session_handoff_discipline",
        "current_use": "preserve_sanitized_four_id_handoff_shape_as_review_context_only",
        "blocked_promotion": "no_irc_session_manager_mutation_or_adapter_enablement",
    },
    {
        "lane": "cross_project_decision_support",
        "strength_connected": "source_of_truth_index_demotes_stale_context_and_blocks_stopped_tracks",
        "current_use": "filter_decisions_to_current_aas_entrypoints_only",
        "blocked_promotion": "no_cross_project_autorouting_or_stopped_project_work",
    },
    {
        "lane": "agent_observability_success_metrics",
        "strength_connected": "no_answer_observability_rubric_and_success_metric_boundaries",
        "current_use": "measure_boundary_preservation_in_internal_admin_handoffs_only",
        "blocked_promotion": "no_dashboard_public_metric_reputation_or_worker_skill_dna",
    },
    {
        "lane": "payment_production_context",
        "strength_connected": "production_infrastructure_and_multi_chain_payment_context",
        "current_use": "treat_payment_status_as_historical_context_not_reverified_claim",
        "blocked_promotion": "no_payment_or_production_reverification_claim_from_this_map",
    },
]

DECISION_SUPPORT_FALSE_FLAGS = {
    "decision_support_records_operator_answer": False,
    "decision_support_records_operator_approval": False,
    "decision_support_selects_future_answer": False,
    "decision_support_creates_answer_record": False,
    "decision_support_approves_product_exposure": False,
    "decision_support_approves_runtime_memory_wiring": False,
    "decision_support_registers_runtime_adapter": False,
    "decision_support_enables_runtime_adapter": False,
    "decision_support_mutates_irc_session_manager": False,
    "decision_support_writes_live_acontext": False,
    "decision_support_retrieves_live_acontext": False,
    "decision_support_enables_cross_project_autorouting": False,
    "decision_support_creates_customer_copy": False,
    "decision_support_creates_worker_instruction": False,
    "decision_support_creates_dashboard_metric": False,
    "decision_support_enables_catalog_pricing_queue_or_dispatch": False,
    "decision_support_emits_erc8004_reputation": False,
    "decision_support_emits_worker_skill_dna": False,
    "decision_support_reverifies_payment_or_production": False,
    "decision_support_releases_exact_gps_or_raw_metadata": False,
    "decision_support_releases_private_context": False,
    "decision_support_grants_domain_authority_claims": False,
    "decision_support_publishes_worker_copyable_doctrine": False,
    "decision_support_integrates_stopped_projects": False,
}

DECISION_SUPPORT_BLOCKED_CLAIMS = [
    *SOURCE_OF_TRUTH_BLOCKED_CLAIMS,
    "decision_support_map_records_operator_answer",
    "decision_support_map_records_operator_approval",
    "decision_support_map_selects_future_answer",
    "decision_support_map_treats_lane_selection_as_approval",
    "decision_support_map_creates_answer_record",
    "decision_support_map_approves_product_exposure",
    "decision_support_map_approves_runtime_memory_wiring",
    "decision_support_map_registers_or_enables_runtime_adapter",
    "decision_support_map_mutates_irc_session_manager",
    "decision_support_map_writes_or_retrieves_live_acontext",
    "decision_support_map_authorizes_cross_project_autorouting",
    "decision_support_map_creates_customer_public_worker_surface",
    "decision_support_map_creates_dashboard_or_public_metric",
    "decision_support_map_authorizes_catalog_pricing_queue_or_dispatch",
    "decision_support_map_emits_erc8004_reputation_or_worker_skill_dna",
    "decision_support_map_reverifies_payment_or_production",
    "decision_support_map_releases_exact_gps_or_raw_metadata",
    "decision_support_map_releases_private_context",
    "decision_support_map_grants_domain_authority_claims",
    "decision_support_map_publishes_worker_copyable_doctrine",
    "decision_support_map_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(DECISION_SUPPORT_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "future_answer_selected",
    "answer_record_created",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "cross_project_autorouting_ready",
    "customer_copy_ready",
    "dashboard_metric_ready",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _assert_source_index(index: dict[str, Any]) -> None:
    if index.get("schema") != AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA:
        raise CityOpsContractError("AAS decision-support map source index schema drift")
    if index.get("index_status") != AAS_SOURCE_OF_TRUTH_INDEX_STATUS:
        raise CityOpsContractError("AAS decision-support map source index status drift")
    safe = set(index.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS decision-support map source safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS decision-support map source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(index.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(SOURCE_OF_TRUTH_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS decision-support map source missing blocked claims: {sorted(missing)}"
        )
    posture = index.get("current_no_answer_posture", {})
    if posture.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS decision-support map source recorded operator answer")
    if posture.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS decision-support map source recorded operator approval")
    if posture.get("selected_decision") is not None:
        raise CityOpsContractError("AAS decision-support map source selected decision")
    if posture.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS decision-support map source effective decision drift")
    firewall = index.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS decision-support map source allowed {key}")


def build_aas_system_integration_decision_support_map(
    *,
    artifact_dir: str | Path | None = None,
    source_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin system-integration support map."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    index = source_index or load_aas_source_of_truth_index(artifact_dir=source_dir)
    _assert_source_index(index)

    safe_to_claim = _dedupe(
        [
            *index["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *index["claim_boundaries"]["do_not_claim_yet"],
            *DECISION_SUPPORT_BLOCKED_CLAIMS,
        ]
    )

    decision_map = {
        "schema": AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SCHEMA,
        "map_id": AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_ID,
        "scope": "internal_admin_aas_system_integration_decision_support_only",
        "map_status": AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_STATUS,
        "source_policy": "consume_current_source_of_truth_index_only",
        "source_index": {
            "file": AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
            "schema": index["schema"],
            "index_id": index["index_id"],
            "safe_claim": AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM,
            "digest_sha256": _stable_digest(index),
            "effective_decision": index["current_no_answer_posture"]["effective_decision"],
        },
        "integration_lanes": [
            {
                **lane,
                "decision_support_only": True,
                "selected_by_this_map": False,
                "approval_granted_by_this_map": False,
                "runtime_or_external_promotion_allowed": False,
            }
            for lane in INTEGRATION_LANES
        ],
        "current_no_answer_decision": {
            "operator_answer_recorded": False,
            "operator_approval_recorded": False,
            "selected_future_answer": None,
            "effective_decision": DEFAULT_EFFECTIVE_DECISION,
            "lane_selection_is_approval": False,
            "map_is_answer_record": False,
        },
        "decision_support_questions": [
            {
                "question": "Should the next daytime move record one real two-lane operator answer or keep both lanes held?",
                "requires_separate_answer_record": True,
                "answered_by_this_map": False,
            },
            {
                "question": "If no real answer exists, should proof layering pause instead of adding more read-only ceremony?",
                "requires_separate_answer_record": True,
                "answered_by_this_map": False,
            },
            {
                "question": "If runtime memory is later approved, which disabled/default-off wiring gate runs first?",
                "requires_separate_approval_record": True,
                "answered_by_this_map": False,
            },
        ],
        "readiness": {
            "internal_admin_decision_support_map_landed": True,
            "source_index_verified": True,
            "integration_lanes_mapped": True,
            "default_off_non_authorizing": True,
            **DECISION_SUPPORT_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "still_blocked_claims": do_not_claim_yet,
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "operator_guidance": {
            "first_read": "DREAM-PRIORITIES.md",
            "use_this_map_for": "internal_admin_decision_support_only",
            "if_no_real_answer": "hold_both_lanes_or_pause_proof_layering",
            "if_real_answer_exists": "create_separate_two_lane_operator_answer_record_first",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_dashboard_spec": True,
        },
        "map_verdict": (
            "system_integration_decision_support_map_landed_no_answer_no_approval_"
            "all_strengths_connected_as_internal_admin_lanes_only_no_runtime_product_"
            "reputation_payment_dispatch_or_stopped_project_promotion"
        ),
    }
    _assert_aas_system_integration_decision_support_map(decision_map, source_index=index)
    return decision_map


def _assert_aas_system_integration_decision_support_map(
    decision_map: dict[str, Any], *, source_index: dict[str, Any]
) -> None:
    _assert_source_index(source_index)
    if decision_map.get("schema") != AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SCHEMA:
        raise CityOpsContractError("AAS decision-support map schema drift")
    if decision_map.get("map_id") != AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_ID:
        raise CityOpsContractError("AAS decision-support map id drift")
    if decision_map.get("map_status") != AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_STATUS:
        raise CityOpsContractError("AAS decision-support map status drift")
    source = decision_map.get("source_index", {})
    if source.get("file") != AAS_SOURCE_OF_TRUTH_INDEX_FILENAME:
        raise CityOpsContractError("AAS decision-support map source file drift")
    if source.get("digest_sha256") != _stable_digest(source_index):
        raise CityOpsContractError("AAS decision-support map source digest drift")
    if source.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS decision-support map source effective decision drift")

    lanes = decision_map.get("integration_lanes", [])
    if [lane.get("lane") for lane in lanes] != [lane["lane"] for lane in INTEGRATION_LANES]:
        raise CityOpsContractError("AAS decision-support map lane drift")
    for lane in lanes:
        if lane.get("decision_support_only") is not True:
            raise CityOpsContractError("AAS decision-support map lane not support-only")
        for key in [
            "selected_by_this_map",
            "approval_granted_by_this_map",
            "runtime_or_external_promotion_allowed",
        ]:
            if lane.get(key) is not False:
                raise CityOpsContractError(f"AAS decision-support map lane promoted {key}")

    current = decision_map.get("current_no_answer_decision", {})
    if current.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS decision-support map recorded operator answer")
    if current.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS decision-support map recorded operator approval")
    if current.get("selected_future_answer") is not None:
        raise CityOpsContractError("AAS decision-support map selected future answer")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS decision-support map effective decision drift")
    if current.get("lane_selection_is_approval") is not False:
        raise CityOpsContractError("AAS decision-support map treated lane as approval")

    readiness = decision_map.get("readiness", {})
    for key, expected in DECISION_SUPPORT_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS decision-support map promoted readiness {key}")

    safe = set(decision_map.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(decision_map.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS decision-support map safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS decision-support map forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(DECISION_SUPPORT_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS decision-support map missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"AAS decision-support map claim overlap: {sorted(overlap)}")
    if decision_map.get("still_blocked_claims") != decision_map.get("claim_boundaries", {}).get(
        "do_not_claim_yet"
    ):
        raise CityOpsContractError("AAS decision-support map blocked claims drift")

    firewall = decision_map.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS decision-support map allowed {key}")


def write_aas_system_integration_decision_support_map(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    decision_map = build_aas_system_integration_decision_support_map(artifact_dir=target_dir)
    target_path = target_dir / AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME
    target_path.write_text(
        json.dumps(decision_map, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target_path


def load_aas_system_integration_decision_support_map(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME
    decision_map = json.loads(path.read_text(encoding="utf-8"))
    source_index = load_aas_source_of_truth_index(artifact_dir=source_dir)
    _assert_aas_system_integration_decision_support_map(
        decision_map, source_index=source_index
    )
    return decision_map
