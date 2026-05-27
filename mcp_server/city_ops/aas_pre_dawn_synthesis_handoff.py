"""Internal/admin pre-dawn synthesis handoff for Execution Market AAS.

This module compresses the May 27 night work into a deterministic daytime
handoff artifact.  It consumes only the internal/admin exponential-value
pathfinder and turns it into ordered next actions, explicit stopped-track
notes, and sticky claim boundaries.  It does not pull or inspect AutoJob, does
not expand Frontier Academy, does not work on KK v2, does not write live
Acontext, does not mutate IRC/runtime managers, creates no customer/public
surface, enables no dispatch, emits no reputation receipt, does not reverify
payment or production infrastructure, and exposes no GPS/raw metadata or worker
doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_exponential_value_pathfinder import (
    AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
    AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM,
    AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA,
    EXPONENTIAL_VALUE_BLOCKED_CLAIMS,
    load_aas_exponential_value_pathfinder,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA = "city_ops.aas_pre_dawn_synthesis_handoff.v1"
AAS_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME = "aas_pre_dawn_synthesis_handoff.json"
AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM = (
    "admin_aas_pre_dawn_synthesis_handoff_landed"
)

PRE_DAWN_SYNTHESIS_BLOCKED_CLAIMS = [
    *EXPONENTIAL_VALUE_BLOCKED_CLAIMS,
    "synthesis_pulled_or_analyzed_autojob",
    "synthesis_expanded_frontier_academy",
    "synthesis_worked_on_kk_v2",
    "synthesis_worked_on_karmacadabra_v2",
    "synthesis_authorizes_daytime_customer_delivery",
    "synthesis_authorizes_public_catalog_or_route",
    "synthesis_authorizes_pricing_quote_or_paid_pilot",
    "synthesis_authorizes_queue_launch_or_dispatch",
    "synthesis_authorizes_live_acontext_write_or_retrieval",
    "synthesis_changes_irc_or_session_runtime",
    "synthesis_emits_erc8004_reputation_or_worker_skill_dna",
    "synthesis_reverifies_payment_or_production_infrastructure",
    "synthesis_allows_gps_raw_metadata_or_private_context_exposure",
    "synthesis_publishes_worker_copyable_doctrine",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "pulls_autojob_repo",
    "analyzes_autojob_codebase",
    "expands_frontier_academy_guides",
    "works_on_kk_v2",
    "works_on_karmacadabra_v2",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "changes_irc_runtime_manager",
    "creates_customer_copy",
    "creates_public_route",
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
    "writes_live_acontext",
    "retrieves_live_acontext",
    "changes_runtime_manager",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "daytime_customer_delivery_ready",
    "public_catalog_or_route_ready",
    "pricing_or_paid_pilot_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "live_acontext_memory_integration_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "irc_runtime_coordination_ready",
    "irc_session_manager_runtime_enhanced",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_coverage_reverified_by_this_handoff",
    "production_infrastructure_reverified_by_this_handoff",
    "gps_or_metadata_exposure_allowed",
    "private_context_release_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_pre_dawn_synthesis_handoff(
    *,
    artifact_dir: str | Path | None = None,
    pathfinder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin 5 AM synthesis handoff."""

    source = pathfinder or load_aas_exponential_value_pathfinder(artifact_dir=artifact_dir)
    _assert_pathfinder_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM,
            AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *PRE_DAWN_SYNTHESIS_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    handoff = {
        "schema": AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA,
        "handoff_id": f"aas_pre_dawn_synthesis_handoff:{source['proof_anchor_id']}",
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "source_pathfinder_id": source["pathfinder_id"],
        "derived_from": _derived_from(),
        "scope_guard": _scope_guard(),
        "access_policy": _access_policy(),
        "readiness": _readiness(),
        "night_synthesis": _night_synthesis(source),
        "daytime_priority_queue": _daytime_priority_queue(source),
        "handoff_cards": _handoff_cards(source),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "handoff_verdict": "pre_dawn_synthesis_ready_for_daytime_internal_admin_coordination_only",
        "operator_instruction": (
            "Use this 5 AM handoff as the daytime entrypoint: keep the dream-session "
            "stop list intact, pick one internal/admin proof slot, and require a separate "
            "human/operator approval artifact before any customer/public/pricing/dispatch/"
            "reputation/runtime promotion."
        ),
    }
    _assert_handoff_conservative(handoff)
    return handoff


def write_aas_pre_dawn_synthesis_handoff(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic pre-dawn synthesis handoff."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    handoff = build_aas_pre_dawn_synthesis_handoff(artifact_dir=base_dir)
    path = base_dir / AAS_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME
    path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_pre_dawn_synthesis_handoff(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted pre-dawn synthesis handoff."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        handoff = json.load(fh)
    source = load_aas_exponential_value_pathfinder(artifact_dir=base_dir)
    _assert_handoff_conservative(handoff)
    if handoff != build_aas_pre_dawn_synthesis_handoff(
        artifact_dir=base_dir,
        pathfinder=source,
    ):
        raise CityOpsContractError("pre-dawn synthesis handoff drifted from pathfinder")
    return handoff


def _derived_from() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "read_only": True,
        "source_artifacts": [AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME],
        "consumes_only": [AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME],
        "forbidden_inputs": [
            "autojob_repository_or_codebase",
            "frontier_academy_guide_files",
            "kk_v2_swarm_files_or_live_api_tests",
            "karmacadabra_v2_files",
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


def _scope_guard() -> dict[str, Any]:
    return {
        "governing_file": "~/clawd/DREAM-PRIORITIES.md",
        "active_focus": "Execution Market AAS / City-as-a-Service only",
        "stale_cron_tracks_skipped": [
            "AutoJob",
            "Frontier Academy",
            "KK v2",
            "KarmaCadabra v2",
        ],
        "autojob_pull_skipped_because_stop_list_wins": True,
        "frontier_expansion_skipped_because_stop_list_wins": True,
        "kk_v2_work_skipped_because_stop_list_wins": True,
        "one_allowed_repo_family": "projects/execution-market",
    }


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
        "handoff_landed": True,
        "source_pathfinder_consumed": True,
        "stop_list_preserved": True,
        "daytime_priority_queue_documented": True,
        "claim_boundaries_preserved": True,
        "one_next_proof_selected_from_existing_pathfinder": True,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _night_synthesis(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "connection": "portfolio_boundaries_to_exponential_pathfinder",
            "what_changed": (
                "the night converted AAS portfolio status, operator authorization questions, "
                "and coordination flywheel signals into a single internal/admin next-proof map"
            ),
            "source_pathfinder_id": source["pathfinder_id"],
            "safe_meaning": "strategy is executable as proof slots, not as launch permission",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "connection": "stopped_tracks_to_priority_firewall",
            "what_changed": (
                "stale AutoJob, Frontier Academy, KK v2, and KarmaCadabra prompts are now "
                "explicitly represented as skipped scope, reducing recurrence risk"
            ),
            "safe_meaning": "adjacent-project ideas can only return through separate daytime human instruction",
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "connection": "acontext_memory_to_one_proof_queue",
            "what_changed": (
                "the highest multiplier remains one Acontext prerequisite/parity proof, but only "
                "after a separate gate proves Docker/runtime readiness"
            ),
            "safe_meaning": "live memory integration is a candidate next proof, not an achieved fact",
            "customer_visible": False,
            "may_auto_promote": False,
        },
    ]


def _daytime_priority_queue(source: dict[str, Any]) -> list[dict[str, Any]]:
    recommended = source["recommended_next_proof"]
    return [
        {
            "rank": 1,
            "priority": recommended["proof"],
            "source": "aas_exponential_value_pathfinder.recommended_next_proof",
            "action": (
                "Build or run exactly one internal/admin prerequisite/parity attempt record "
                "for Acontext runtime memory if Docker/runtime readiness can be proven first"
            ),
            "fallback_if_blocked": recommended["fallback_if_blocked"],
            "requires_separate_human_approval": False,
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "rank": 2,
            "priority": "answer_one_portfolio_operator_authorization_question_only_if_human_input_exists",
            "source": "aas_portfolio_operator_authorization_packet",
            "action": (
                "If Saúl supplies a real answer, record exactly one approval/hold artifact; "
                "otherwise keep Retail Reality and Compliance Desk internal/admin-only"
            ),
            "requires_separate_human_approval": True,
            "customer_visible": False,
            "may_auto_promote": False,
        },
        {
            "rank": 3,
            "priority": "preserve_priority_firewall_and_claim_quarantine",
            "source": "DREAM-PRIORITIES.md + pathfinder claim boundaries",
            "action": (
                "Do not pull AutoJob, expand Frontier Academy, work KK v2, or infer customer "
                "launch claims from internal AAS artifacts"
            ),
            "requires_separate_human_approval": True,
            "customer_visible": False,
            "may_auto_promote": False,
        },
    ]


def _handoff_cards(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "start_here",
            "summary": "Use the pathfinder's four IDs and one-next-proof queue as the daytime start point.",
            "proof_anchor_id": source["proof_anchor_id"],
            "coordination_session_id": source["coordination_session_id"],
            "compact_decision_id": source["compact_decision_id"],
            "review_packet_id": source["review_packet_id"],
        },
        {
            "card": "do_not_start_here",
            "summary": "Do not reopen stopped dream tracks from stale cron payloads.",
            "blocked_tracks": ["AutoJob", "Frontier Academy", "KK v2", "KarmaCadabra v2"],
        },
        {
            "card": "claim_boundary",
            "summary": "The only new claim is that an internal/admin handoff exists.",
            "safe_claim": AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
            "blocked_claim_count": len(PRE_DAWN_SYNTHESIS_BLOCKED_CLAIMS),
        },
    ]


def _assert_pathfinder_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA:
        raise CityOpsContractError("unexpected exponential-value pathfinder schema")
    for loop in source.get("exponential_value_loops", []):
        for key, value in loop.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("source pathfinder promoted authorization")
        if loop.get("may_auto_promote") is not False:
            raise CityOpsContractError("source pathfinder promoted readiness")
    recommended = source.get("recommended_next_proof", {})
    if recommended.get("customer_visible") is not False:
        raise CityOpsContractError("source recommended proof promoted visibility")
    if recommended.get("may_auto_promote") is not False:
        raise CityOpsContractError("source recommended proof promoted readiness")
    _assert_claim_boundaries(
        source["claim_boundaries"]["safe_to_claim"],
        source["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_handoff_conservative(handoff: dict[str, Any]) -> None:
    if handoff.get("schema") != AAS_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA:
        raise CityOpsContractError("unexpected pre-dawn synthesis handoff schema")
    _assert_false_flags(handoff.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(handoff.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(handoff.get("readiness", {}), _FALSE_READINESS_FLAGS)
    if handoff["scope_guard"].get("autojob_pull_skipped_because_stop_list_wins") is not True:
        raise CityOpsContractError("AutoJob stop-list skip was not preserved")
    for row in handoff.get("night_synthesis", []):
        if row.get("customer_visible") is not False:
            raise CityOpsContractError("night synthesis promoted visibility")
        if row.get("may_auto_promote") is not False:
            raise CityOpsContractError("night synthesis promoted readiness")
    for row in handoff.get("daytime_priority_queue", []):
        if row.get("customer_visible") is not False:
            raise CityOpsContractError("daytime priority promoted visibility")
        if row.get("may_auto_promote") is not False:
            raise CityOpsContractError("daytime priority promoted readiness")
    _assert_claim_boundaries(
        handoff["claim_boundaries"]["safe_to_claim"],
        handoff["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_false_flags(payload: dict[str, Any], flags: list[str]) -> None:
    for flag in flags:
        if payload.get(flag) is not False:
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
