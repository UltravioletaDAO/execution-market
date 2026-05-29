"""Read-only pickup brief for AAS session handoff capsules.

This module turns the conservative AAS session handoff capsule into a compact
operator/agent pickup brief.  It is intentionally a consumer of the capsule, not
a new route layer or runtime mutation.  Its job is to make the 4 AM pattern
recognition prompt actionable while preserving the same claim boundaries: four
stable IDs, one safe claim, sticky blocked claims, one next proof, and a hard
stop line before live Acontext/customer/dispatch/reputation/payment/GPS/worker
copyable claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_next_truth_selector import SELECTED_NEXT_PROOF, SELECTED_NEXT_TRACK
from .aas_session_handoff_capsule import (
    AAS_SESSION_HANDOFF_CAPSULE_FILENAME,
    AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM,
    AAS_SESSION_HANDOFF_CAPSULE_SCHEMA,
    load_aas_session_handoff_capsule,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SESSION_HANDOFF_PICKUP_BRIEF_SCHEMA = "city_ops.aas_session_handoff_pickup_brief.v1"
AAS_SESSION_HANDOFF_PICKUP_BRIEF_FILENAME = "aas_session_handoff_pickup_brief.json"
AAS_SESSION_HANDOFF_PICKUP_BRIEF_SAFE_CLAIM = (
    "internal_admin_aas_session_handoff_pickup_brief_landed"
)

AAS_SESSION_HANDOFF_PICKUP_BRIEF_ID = (
    "execution_market.aas.session_handoff_pickup_brief.2026_05_29_0400"
)
AAS_SESSION_HANDOFF_PICKUP_BRIEF_VERDICT = (
    "pickup_brief_ready_for_agent_handoff_no_runtime_or_customer_promotion"
)

PICKUP_BRIEF_BLOCKED_CLAIMS = [
    "pickup_brief_mutates_irc_runtime_session_manager",
    "pickup_brief_reads_or_replays_raw_transcripts",
    "pickup_brief_writes_live_acontext_memory",
    "pickup_brief_retrieves_live_acontext_memory",
    "pickup_brief_proves_memory_acontext_parity",
    "pickup_brief_authorizes_live_parity_attempt",
    "pickup_brief_authorizes_more_route_layers",
    "pickup_brief_authorizes_customer_copy_delivery_or_publication",
    "pickup_brief_authorizes_public_or_catalog_route",
    "pickup_brief_authorizes_operator_queue_launch_or_dispatch",
    "pickup_brief_authorizes_pricing_or_customer_quote",
    "pickup_brief_authorizes_erc8004_reputation_or_worker_skill_dna",
    "pickup_brief_reverifies_payment_or_production",
    "pickup_brief_allows_exact_gps_or_raw_metadata",
    "pickup_brief_grants_domain_or_emergency_authority",
    "pickup_brief_creates_worker_copyable_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "runtime_session_manager_mutated",
    "raw_transcript_replay_required",
    "live_acontext_memory_integration_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "one_live_parity_attempt_authorized",
    "more_route_layers_allowed",
    "customer_copy_ready",
    "customer_delivery_ready",
    "publication_ready",
    "public_or_catalog_route_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "pricing_or_customer_quote_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_coverage_reverified_by_this_brief",
    "production_infrastructure_reverified_by_this_brief",
    "gps_or_metadata_exposure_allowed",
    "domain_or_emergency_authority_ready",
    "worker_copyable_doctrine_ready",
]


def build_aas_session_handoff_pickup_brief(
    *,
    artifact_dir: str | Path | None = None,
    capsule: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic read-only pickup brief from the handoff capsule."""

    source_capsule = capsule or load_aas_session_handoff_capsule(artifact_dir=artifact_dir)
    _assert_capsule_conservative(source_capsule)

    safe_to_claim = _dedupe(
        [
            *source_capsule["claim_boundaries"]["safe_to_claim"],
            AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM,
            AAS_SESSION_HANDOFF_PICKUP_BRIEF_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_capsule["claim_boundaries"]["do_not_claim_yet"],
            *PICKUP_BRIEF_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    brief = {
        "schema": AAS_SESSION_HANDOFF_PICKUP_BRIEF_SCHEMA,
        "brief_id": AAS_SESSION_HANDOFF_PICKUP_BRIEF_ID,
        "scope": "internal_admin_agent_pickup_brief_only_no_runtime_mutation",
        "source_artifact": {
            "file": AAS_SESSION_HANDOFF_CAPSULE_FILENAME,
            "schema": source_capsule["schema"],
            "id": source_capsule["capsule_id"],
            "safe_claim": AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM,
        },
        "derived_from": _derived_from(),
        "access_policy": _access_policy(),
        "readiness": _readiness(source_capsule),
        "four_id_header": dict(source_capsule["four_id_header"]),
        "first_message_template": _first_message_template(source_capsule),
        "pattern_recognition": _pattern_recognition(source_capsule),
        "coordination_scaling_rules": _coordination_scaling_rules(source_capsule),
        "next_pickup_order": _next_pickup_order(source_capsule),
        "stop_conditions": _stop_conditions(source_capsule),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "brief_verdict": AAS_SESSION_HANDOFF_PICKUP_BRIEF_VERDICT,
        "operator_instruction": (
            "Use this brief to start the next AAS agent or IRC handoff. Copy the "
            "four-ID header and selected proof exactly, then either clear Acontext "
            "runtime prerequisites or stop. Do not use this brief as approval for "
            "customer copy, public routes, dispatch, pricing, ERC-8004 reputation, "
            "Worker Skill DNA, payment/production status, raw metadata release, or "
            "worker-copyable doctrine."
        ),
    }
    _assert_brief_conservative(brief, source_capsule)
    return brief


def write_aas_session_handoff_pickup_brief(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic pickup brief fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    brief = build_aas_session_handoff_pickup_brief(artifact_dir=base_dir)
    path = base_dir / AAS_SESSION_HANDOFF_PICKUP_BRIEF_FILENAME
    path.write_text(json.dumps(brief, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_session_handoff_pickup_brief(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted pickup brief fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    brief = json.loads(
        (base_dir / AAS_SESSION_HANDOFF_PICKUP_BRIEF_FILENAME).read_text(encoding="utf-8")
    )
    capsule = load_aas_session_handoff_capsule(artifact_dir=base_dir)
    _assert_brief_conservative(brief, capsule)
    if brief != build_aas_session_handoff_pickup_brief(
        artifact_dir=base_dir, capsule=capsule
    ):
        raise CityOpsContractError("AAS session handoff pickup brief drifted from capsule")
    return brief


def _derived_from() -> dict[str, bool]:
    return {
        "read_only": True,
        "capsule_consumer_only": True,
        "mutates_irc_runtime_session_manager": False,
        "reads_raw_transcripts": False,
        "reads_unreviewed_memory": False,
        "reads_private_operator_context": False,
        "writes_live_acontext": False,
        "retrieves_live_acontext": False,
        "writes_municipal_memory": False,
        "writes_customer_copy": False,
        "enables_dispatch_automation": False,
        "emits_reputation_receipts": False,
        "reverifies_payment_coverage": False,
        "reverifies_production_infrastructure": False,
        "exposes_gps_or_metadata": False,
        "publishes_worker_doctrine": False,
    }


def _access_policy() -> dict[str, bool | str]:
    return {
        "visibility": "internal_admin_only",
        "customer_visible": False,
        "public_route_registered": False,
        "catalog_route_registered": False,
        "operator_queue_enabled": False,
        "dispatch_enabled": False,
        "gps_or_raw_metadata_release_allowed": False,
        "customer_copy_publication_allowed": False,
        "pricing_quote_allowed": False,
        "reputation_publication_allowed": False,
        "worker_copyable_doctrine_allowed": False,
    }


def _readiness(capsule: dict[str, Any]) -> dict[str, bool]:
    readiness = {
        "pickup_brief_landed": True,
        "capsule_consumed": True,
        "four_id_header_preserved": True,
        "selected_next_proof_preserved": True,
        "one_next_proof_slot_preserved": True,
        "claim_boundaries_preserved": True,
        "safe_and_blocked_claims_adjacent": True,
    }
    readiness.update({flag: False for flag in _FALSE_READINESS_FLAGS})
    # Keep this asserted instead of inferred: the source capsule itself must still
    # say no live attempt is authorized now.
    readiness["source_capsule_authorizes_live_attempt_now"] = bool(
        capsule["session_handoff_capsule"]["one_next_proof_slot"][
            "authorizes_live_attempt_now"
        ]
    )
    return readiness


def _first_message_template(capsule: dict[str, Any]) -> dict[str, Any]:
    header_lines = list(capsule["session_handoff_capsule"]["header_lines"])
    selected = capsule["session_handoff_capsule"]["one_next_proof_slot"]
    return {
        "format": "copy_this_as_the_first_handoff_block",
        "lines": [
            *header_lines,
            f"safe_claim: {AAS_SESSION_HANDOFF_PICKUP_BRIEF_SAFE_CLAIM}",
            f"selected_next_track: {selected['track']}",
            f"selected_next_proof: {selected['proof']}",
            "stop_condition: stop if Acontext prerequisites remain blocked or the gate is non-empty",
        ],
        "must_not_include": [
            "raw transcript excerpts",
            "private operator context",
            "customer-facing claims",
            "exact GPS/raw metadata",
            "payment or production status unless separately reverified",
        ],
    }


def _pattern_recognition(capsule: dict[str, Any]) -> list[dict[str, str | list[str]]]:
    one_next_proof = capsule["session_handoff_capsule"]["one_next_proof_slot"]
    return [
        {
            "pattern": "memory_system_data_compounds_only_after_review",
            "connection": (
                "Reviewed AAS artifacts become useful when carried as compact IDs and "
                "claim boundaries, not as raw transcript replay."
            ),
            "multiplier_effect": (
                "Later agents can resume from the same proof anchor and selected proof "
                "without re-litigating the whole night."
            ),
            "next_safe_use": one_next_proof["proof"],
            "blocked_until": [
                "empty_readiness_gate",
                "single_bounded_live_write_retrieve_parity_attempt",
            ],
        },
        {
            "pattern": "irc_coordination_scales_with_four_ids",
            "connection": (
                "IRC/session handoffs should start with proof_anchor_id, "
                "coordination_session_id, compact_decision_id, and review_packet_id."
            ),
            "multiplier_effect": (
                "A small invariant header beats long chat history and reduces accidental "
                "claim promotion."
            ),
            "next_safe_use": "copy_the_first_message_template_into_the_next_handoff",
            "blocked_until": ["separate_runtime_session_manager_mutation_proof"],
        },
        {
            "pattern": "cross_project_intelligence_is_a_filter_not_an_autopilot",
            "connection": (
                "Signals from stopped or adjacent projects may inform AAS boundaries, but "
                "they do not reopen AutoJob, Frontier Academy, KK v2, or customer routes "
                "during dream sessions."
            ),
            "multiplier_effect": (
                "The strategy benefits from broader intelligence while the actual work "
                "stays inside Execution Market AAS."
            ),
            "next_safe_use": "choose_the_narrowest_AAS_next_proof_only",
            "blocked_until": ["explicit_human_priority_change", "separate_customer_publication_gate"],
        },
        {
            "pattern": "agent_coordination_quality_is_boundary_survival",
            "connection": (
                "The best scaling metric is whether agents preserve safe and blocked "
                "claims together with one next proof, not how many artifacts they add."
            ),
            "multiplier_effect": (
                "Agent swarms become safer when continuity and restraint are measurable."
            ),
            "next_safe_use": "score_private_handoffs_by_claim_boundary_survival",
            "blocked_until": ["separate_erc8004_reputation_or_worker_skill_dna_gate"],
        },
    ]


def _coordination_scaling_rules(capsule: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rule": "start_with_four_id_header",
            "required_fields": list(capsule["four_id_header"].keys()),
            "failure_mode_prevented": "raw_transcript_dependency",
        },
        {
            "rule": "carry_safe_and_blocked_claims_together",
            "required_fields": ["safe_to_claim", "do_not_claim_yet"],
            "failure_mode_prevented": "approval_request_becomes_approval",
        },
        {
            "rule": "keep_exactly_one_next_proof_slot",
            "required_fields": ["track", "proof", "requires_empty_readiness_gate_first"],
            "failure_mode_prevented": "parallel_drift_into_unproven_launch_claims",
        },
        {
            "rule": "stop_before_runtime_or_customer_promotion",
            "required_fields": ["stop_condition", "blocked_claim_footer"],
            "failure_mode_prevented": "internal_admin_artifact_becomes_customer_surface",
        },
    ]


def _next_pickup_order(capsule: dict[str, Any]) -> list[dict[str, Any]]:
    selected = capsule["session_handoff_capsule"]["one_next_proof_slot"]
    return [
        {
            "step": 1,
            "action": "copy_four_id_header_and_claim_boundaries",
            "expected_output": "handoff_starts_from_same_capsule_context",
            "stop_if_failed": True,
        },
        {
            "step": 2,
            "action": "continue_selected_runtime_prerequisite_track",
            "track": selected["track"],
            "proof": selected["proof"],
            "stop_if_failed": True,
        },
        {
            "step": 3,
            "action": "clear_docker_image_api_dashboard_prerequisites",
            "expected_output": "readiness_gate_can_be_rebuilt",
            "stop_if_failed": True,
        },
        {
            "step": 4,
            "action": "rerun_read_only_preflight_gate",
            "expected_output": "empty_gate_or_blocker_delta",
            "stop_if_failed": True,
        },
        {
            "step": 5,
            "action": "attempt_one_live_parity_pass_only_if_gate_empty_and_authorized",
            "expected_output": "bounded_write_retrieve_parity_result_or_no_attempt",
            "requires_empty_readiness_gate_first": True,
            "authorized_now": False,
        },
    ]


def _stop_conditions(capsule: dict[str, Any]) -> list[str]:
    return _dedupe(
        [
            capsule["session_handoff_capsule"]["stop_condition"],
            "stop if Docker/Acontext images, API, or dashboard prerequisites remain blocked",
            "stop if the rebuilt readiness gate is non-empty",
            "stop if the next task would add route layers instead of runtime/operator truth",
            "stop if the next task would create customer copy, public route, dispatch, pricing, reputation, Worker Skill DNA, payment/production, GPS/raw metadata, authority, or worker-doctrine claims",
        ]
    )


def _assert_capsule_conservative(capsule: dict[str, Any]) -> None:
    if capsule.get("schema") != AAS_SESSION_HANDOFF_CAPSULE_SCHEMA:
        raise CityOpsContractError("source capsule schema mismatch")
    readiness = capsule.get("readiness", {})
    for flag in [
        "runtime_session_manager_mutated",
        "raw_transcript_replay_required",
        "live_acontext_memory_integration_ready",
        "runtime_parity_proven",
        "one_live_parity_attempt_authorized",
        "more_route_layers_allowed",
        "customer_delivery_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "gps_or_metadata_exposure_allowed",
        "worker_copyable_doctrine_ready",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"source capsule promoted blocked readiness: {flag}")
    one_next_proof = capsule["session_handoff_capsule"]["one_next_proof_slot"]
    if one_next_proof.get("track") != SELECTED_NEXT_TRACK:
        raise CityOpsContractError("source capsule changed selected next track")
    if one_next_proof.get("proof") != SELECTED_NEXT_PROOF:
        raise CityOpsContractError("source capsule changed selected next proof")
    if one_next_proof.get("authorizes_live_attempt_now") is not False:
        raise CityOpsContractError("source capsule authorizes live attempt now")
    if one_next_proof.get("requires_empty_readiness_gate_first") is not True:
        raise CityOpsContractError("source capsule lost empty-gate prerequisite")
    access = capsule.get("access_policy", {})
    for flag in [
        "customer_visible",
        "public_route_registered",
        "dispatch_enabled",
        "gps_or_raw_metadata_release_allowed",
    ]:
        if access.get(flag) is not False:
            raise CityOpsContractError(f"source capsule promoted access policy: {flag}")
    _assert_claim_boundaries(
        capsule["claim_boundaries"]["safe_to_claim"],
        capsule["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_brief_conservative(brief: dict[str, Any], capsule: dict[str, Any]) -> None:
    if brief.get("schema") != AAS_SESSION_HANDOFF_PICKUP_BRIEF_SCHEMA:
        raise CityOpsContractError("AAS session handoff pickup brief schema mismatch")
    if brief.get("four_id_header") != capsule.get("four_id_header"):
        raise CityOpsContractError("AAS session handoff pickup brief lost four-ID header")
    if brief.get("brief_verdict") != AAS_SESSION_HANDOFF_PICKUP_BRIEF_VERDICT:
        raise CityOpsContractError("AAS session handoff pickup brief verdict mismatch")
    readiness = brief.get("readiness", {})
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"AAS pickup brief promoted blocked readiness: {flag}")
    if readiness.get("source_capsule_authorizes_live_attempt_now") is not False:
        raise CityOpsContractError("AAS pickup brief inherited live attempt authorization")
    access = brief.get("access_policy", {})
    for flag in [
        "customer_visible",
        "public_route_registered",
        "catalog_route_registered",
        "operator_queue_enabled",
        "dispatch_enabled",
        "gps_or_raw_metadata_release_allowed",
        "customer_copy_publication_allowed",
        "pricing_quote_allowed",
        "reputation_publication_allowed",
        "worker_copyable_doctrine_allowed",
    ]:
        if access.get(flag) is not False:
            raise CityOpsContractError(f"AAS pickup brief promoted access policy: {flag}")
    safe = brief["claim_boundaries"]["safe_to_claim"]
    blocked = brief["claim_boundaries"]["do_not_claim_yet"]
    _assert_claim_boundaries(safe, blocked)
    if AAS_SESSION_HANDOFF_PICKUP_BRIEF_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS pickup brief missing safe claim")
    for blocked_claim in PICKUP_BRIEF_BLOCKED_CLAIMS:
        if blocked_claim not in blocked:
            raise CityOpsContractError(f"AAS pickup brief missing blocked claim: {blocked_claim}")
    selected_lines = "\n".join(brief["first_message_template"]["lines"])
    if SELECTED_NEXT_PROOF not in selected_lines:
        raise CityOpsContractError("AAS pickup brief lost selected next proof")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim).intersection(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"AAS pickup brief claim overlap: {sorted(overlap)}")


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
