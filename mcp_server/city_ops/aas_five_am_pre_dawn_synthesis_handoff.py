"""Internal/admin 5 AM pre-dawn synthesis handoff for AAS.

This artifact synthesizes the June 11 dream-session ladder into a daytime
operations handoff without crossing the current AAS no-answer boundary. It
consumes only the reviewed 4 AM pattern-recognition multiplier ladder and turns
it into actionable daytime recommendations, integration connections, and strict
claim boundaries.

It records no operator answer or approval, creates no answer receipt, performs
no live Acontext write/retrieve, mutates no IRC/session manager, exposes no
public/customer/worker surface, launches no queue or dispatch, emits no
reputation/Worker Skill DNA, reverifies no payment/production state, exposes no
GPS/raw metadata/private context, grants no authority claim, publishes no worker
doctrine, and uses no stopped project as an active source.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_four_am_pattern_recognition_multiplier_ladder import (
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME,
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM,
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SCHEMA,
    AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_STATUS,
    LADDER_FALSE_FLAGS,
    PATTERN_RECOGNITION_BLOCKED_CLAIMS,
    load_aas_four_am_pattern_recognition_multiplier_ladder,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA = (
    "city_ops.aas_five_am_pre_dawn_synthesis_handoff.v1"
)
AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME = (
    "aas_five_am_pre_dawn_synthesis_handoff.json"
)
AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM = (
    "internal_admin_aas_5am_pre_dawn_synthesis_handoff_2026_06_11_landed"
)
AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_ID = (
    "execution_market.aas.pre_dawn_synthesis_handoff.2026_06_11_0500"
)
AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_STATUS = (
    "read_only_synthesis_no_answer_no_runtime_or_external_promotion"
)

SYNTHESIS_FALSE_FLAGS = {
    **LADDER_FALSE_FLAGS,
    "synthesis_records_operator_answer": False,
    "synthesis_records_operator_approval": False,
    "synthesis_selects_future_answer": False,
    "synthesis_creates_answer_receipt": False,
    "synthesis_approves_product_exposure": False,
    "synthesis_approves_runtime_memory": False,
    "synthesis_repairs_docker": False,
    "synthesis_writes_live_acontext": False,
    "synthesis_retrieves_live_acontext": False,
    "synthesis_mutates_irc_session_manager": False,
    "synthesis_enables_cross_project_autorouting": False,
    "synthesis_creates_customer_copy": False,
    "synthesis_creates_worker_instruction": False,
    "synthesis_launches_queue_or_dispatch": False,
    "synthesis_emits_reputation_or_worker_skill_dna": False,
    "synthesis_reverifies_payment_or_production": False,
    "synthesis_exposes_gps_or_raw_metadata": False,
    "synthesis_releases_private_context": False,
    "synthesis_grants_authority_claims": False,
    "synthesis_publishes_worker_doctrine": False,
    "synthesis_uses_stopped_projects_as_active_sources": False,
}

FIVE_AM_SYNTHESIS_BLOCKED_CLAIMS = [
    *PATTERN_RECOGNITION_BLOCKED_CLAIMS,
    "five_am_synthesis_records_operator_answer",
    "five_am_synthesis_records_operator_approval",
    "five_am_synthesis_selects_future_answer",
    "five_am_synthesis_creates_answer_receipt",
    "five_am_synthesis_treats_recommendation_as_approval",
    "five_am_synthesis_repairs_docker_or_starts_acontext",
    "five_am_synthesis_writes_or_retrieves_live_acontext",
    "five_am_synthesis_mutates_irc_session_manager",
    "five_am_synthesis_enables_cross_project_autorouting",
    "five_am_synthesis_creates_public_customer_worker_surface",
    "five_am_synthesis_authorizes_catalog_pricing_queue_or_dispatch",
    "five_am_synthesis_emits_erc8004_reputation_or_worker_skill_dna",
    "five_am_synthesis_reverifies_payment_or_production",
    "five_am_synthesis_releases_exact_gps_or_raw_metadata",
    "five_am_synthesis_releases_private_context",
    "five_am_synthesis_grants_domain_authority_claims",
    "five_am_synthesis_publishes_worker_copyable_doctrine",
    "five_am_synthesis_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(FIVE_AM_SYNTHESIS_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_record_created",
    "answer_receipt_created",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "docker_repaired",
    "live_acontext_ready",
    "runtime_parity_proven",
    "irc_session_manager_mutated",
    "cross_project_autorouting_ready",
    "customer_copy_ready",
    "public_dashboard_ready",
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


def build_aas_five_am_pre_dawn_synthesis_handoff(
    *,
    artifact_dir: str | Path | None = None,
    ladder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic 5 AM pre-dawn synthesis handoff."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    source = ladder or load_aas_four_am_pattern_recognition_multiplier_ladder(
        artifact_dir=base_dir
    )
    _assert_ladder_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM,
            AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *FIVE_AM_SYNTHESIS_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    handoff = {
        "schema": AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA,
        "handoff_id": AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_ID,
        "handoff_status": AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_STATUS,
        "source_pattern_ladder": {
            "file": AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME,
            "safe_claim": AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM,
            "digest_sha256": _stable_digest(source),
            "source_role": "current_4am_pattern_recognition_multiplier_ladder",
        },
        "derived_from": _derived_from(),
        "scope_guard": _scope_guard(),
        "access_policy": _access_policy(),
        "readiness": _readiness(),
        "integration_synthesis": _integration_synthesis(source),
        "handoff_packet_contract_synthesis": _handoff_packet_contract_synthesis(source),
        "daytime_recommendations": _daytime_recommendations(),
        "handoff_cards": _handoff_cards(source),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "handoff_verdict": "five_am_pre_dawn_synthesis_landed_internal_only",
        "operator_instruction": (
            "Use this as the June 11 daytime handoff: preserve the stopped-project "
            "firewall, keep AAS in no-answer hold unless one explicit allowed "
            "operator value exists, and treat all integration ideas as internal/admin "
            "decision support until a separate answer receipt validates movement."
        ),
    }
    _assert_handoff_conservative(handoff)
    return handoff


def write_aas_five_am_pre_dawn_synthesis_handoff(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic 5 AM pre-dawn synthesis handoff."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    handoff = build_aas_five_am_pre_dawn_synthesis_handoff(artifact_dir=base_dir)
    path = base_dir / AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME
    path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_five_am_pre_dawn_synthesis_handoff(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted 5 AM pre-dawn synthesis handoff."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    with (base_dir / AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        handoff = json.load(fh)
    expected = build_aas_five_am_pre_dawn_synthesis_handoff(artifact_dir=base_dir)
    _assert_handoff_conservative(handoff)
    if handoff != expected:
        raise CityOpsContractError("5 AM pre-dawn synthesis handoff drifted")
    return handoff


def _derived_from() -> dict[str, Any]:
    return {
        "read_only": True,
        "source_artifacts": [AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME],
        "consumes_only": [AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME],
        "forbidden_inputs": [
            "raw_transcripts",
            "unreviewed_memory",
            "private_operator_context",
            "live_acontext_sink_writes",
            "live_acontext_retrievals",
            "payment_processor_probe",
            "production_health_probe",
            "gps_or_raw_metadata_payloads",
            "customer_copy_drafts",
            "worker_instruction_templates",
            "stopped_project_codebases_as_active_sources",
        ],
    }


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
        "karmacadabra_v2_work_skipped_because_stop_list_wins": True,
        "one_allowed_repo_family": "projects/execution-market",
    }


def _access_policy() -> dict[str, bool | str]:
    access: dict[str, bool | str] = {
        "audience": "internal_admin_only",
        "requires_admin_context": True,
    }
    for key in [
        "network_route_registered",
        "public_route_registered",
        "customer_visible",
        "worker_visible",
        "operator_queue_launched",
        "dispatch_enabled",
        "runtime_adapter_registered",
        "runtime_adapter_enabled",
        "irc_session_manager_mutated",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "emits_reputation_receipts",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        access[key] = False
    return access


def _readiness() -> dict[str, bool]:
    readiness = {
        "five_am_handoff_landed": True,
        "source_pattern_ladder_consumed": True,
        "night_insights_synthesized": True,
        "tonights_guardrails_synthesized": True,
        "daytime_recommendations_documented": True,
        "stopped_project_firewall_preserved": True,
        "operator_answer_gate_preserved": True,
        "handoff_packet_contract_consumed": True,
    }
    readiness.update(SYNTHESIS_FALSE_FLAGS)
    return readiness


def _integration_synthesis(source: dict[str, Any]) -> list[dict[str, str]]:
    cards = {card["pattern"]: card for card in source["pattern_recognition_cards"]}
    return [
        {
            "system": "memory_to_acontext",
            "connection": cards["memory_system_data"]["insight"],
            "daytime_use": "prepare a clean answer-receipt packet and Docker/Acontext prerequisite checklist; do not write live memory yet",
            "blocked_until": "explicit runtime-memory operator answer plus restored Docker reachability and read-only inventory",
        },
        {
            "system": "irc_and_session_coordination",
            "connection": cards["irc_coordination"]["insight"],
            "daytime_use": "standardize handoff packets around source ref, safe claim, blocked claims, and next gate",
            "blocked_until": "separate runtime adapter contract and explicit operator answer before mutation",
        },
        {
            "system": "cross_project_intelligence",
            "connection": cards["cross_project_intelligence_flows"]["insight"],
            "daytime_use": "treat stopped projects as routing/firewall signals, not implementation sources",
            "blocked_until": "one explicit operator answer receipt validates a product/runtime lane",
        },
        {
            "system": "agent_coordination",
            "connection": cards["agent_coordination_scaling"]["insight"],
            "daytime_use": "score agents by boundary survival and one-next-proof discipline",
            "blocked_until": "internal metric gate with no public/customer/worker visibility",
        },
    ]


def _handoff_packet_contract_synthesis(source: dict[str, Any]) -> dict[str, Any]:
    contract = source["handoff_packet_contract"]
    return {
        "source_contract_status": contract["contract_status"],
        "required_fields": list(contract["required_fields"]),
        "consumer_rules_to_preserve": [rule["rule"] for rule in contract["consumer_rules"]],
        "daytime_operating_rule": (
            "Any daytime summary, Acontext candidate, IRC handoff, memory note, or future "
            "agent prompt must carry the six required fields before it can recommend action."
        ),
        "fail_closed_posture": "pause_aas_proof_layering",
        "blocked_behavior_count": len(contract["forbidden_consumer_behaviors"]),
    }


def _daytime_recommendations() -> list[dict[str, str]]:
    return [
        {
            "priority": "P0",
            "recommendation": "pause_aas_proof_layering",
            "why": "No explicit operator answer exists; more no-answer proof layers risk implying movement.",
            "action": "Daytime operator can either explicitly pause or provide exactly one allowed answer value.",
        },
        {
            "priority": "P1",
            "recommendation": "if_product_lane_selected_create_retail_reality_answer_or_hold_record",
            "why": "Product/public/customer/worker movement needs a separate receipt before exposure.",
            "action": "Validate the separate answer artifact against aas_operator_answer_receipt_gate.json first.",
        },
        {
            "priority": "P1",
            "recommendation": "if_runtime_memory_lane_selected_restore_docker_then_rerun_read_only_inventory",
            "why": "Acontext runtime claims remain blocked until current Docker/API/core/UI truth is rechecked.",
            "action": "Repair reachability outside this handoff, then perform read-only inventory before any live write/retrieve.",
        },
        {
            "priority": "P2",
            "recommendation": "keep_stopped_project_firewall_visible",
            "why": "The stale cron payload keeps requesting stopped projects; preserving the firewall is part of AAS quality control.",
            "action": "Continue not pulling or editing AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2 in dreams.",
        },
    ]


def _handoff_cards(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "current_truth",
            "summary": "The 4 AM pattern ladder landed as internal/admin read-only decision support; no operator answer exists.",
            "source_safe_claim": AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM,
        },
        {
            "card": "next_gate",
            "summary": "Stop at pause_aas_proof_layering or keep_both_lanes_held unless Saúl gives one explicit allowed value.",
            "allowed_values": [gate for gate in source["next_required_gates"]],
        },
        {
            "card": "blocked_surface",
            "summary": "No public/customer/worker route, queue, dispatch, reputation, Worker Skill DNA, payment, production, GPS/raw metadata, or private-context claim is authorized.",
            "blocked_claim_count": len(FIVE_AM_SYNTHESIS_BLOCKED_CLAIMS),
        },
        {
            "card": "handoff_packet_contract",
            "summary": "Future consumers must carry source_file, source_digest_sha256, safe_claim, blocked_claims, next_gate, and recommended_posture; missing fields mean hold.",
            "source_contract_status": source["handoff_packet_contract"]["contract_status"],
        },
    ]


def _assert_ladder_conservative(ladder: dict[str, Any]) -> None:
    if ladder.get("schema") != AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SCHEMA:
        raise CityOpsContractError("5 AM synthesis source ladder schema drift")
    if ladder.get("ladder_status") != AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_STATUS:
        raise CityOpsContractError("5 AM synthesis source ladder status drift")
    safe = set(ladder.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM not in safe:
        raise CityOpsContractError("5 AM synthesis source ladder safe claim missing")
    _assert_no_forbidden_safe(safe, "source ladder")
    blocked = set(ladder.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(PATTERN_RECOGNITION_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"5 AM synthesis source ladder missing blocked claims: {sorted(missing)}"
        )
    for key, expected in LADDER_FALSE_FLAGS.items():
        if ladder.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"5 AM synthesis source ladder promoted {key}")
    contract = ladder.get("handoff_packet_contract", {})
    required_fields = set(contract.get("required_fields", []))
    missing_required = {
        "source_file",
        "source_digest_sha256",
        "safe_claim",
        "blocked_claims",
        "next_gate",
        "recommended_posture",
    } - required_fields
    if missing_required:
        raise CityOpsContractError(
            f"5 AM synthesis source ladder missing handoff packet fields: {sorted(missing_required)}"
        )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    _assert_no_forbidden_safe(safe, "handoff")
    missing = set(FIVE_AM_SYNTHESIS_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"5 AM synthesis missing blocked claims: {sorted(missing)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"5 AM synthesis safe/blocked overlap: {sorted(overlap)}"
        )


def _assert_no_forbidden_safe(safe: set[str], source: str) -> None:
    forbidden = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden:
        raise CityOpsContractError(
            f"5 AM synthesis {source} forbidden safe claims: {sorted(forbidden)}"
        )


def _assert_handoff_conservative(handoff: dict[str, Any]) -> None:
    if handoff.get("schema") != AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_SCHEMA:
        raise CityOpsContractError("5 AM synthesis schema drift")
    if handoff.get("handoff_status") != AAS_FIVE_AM_PRE_DAWN_SYNTHESIS_HANDOFF_STATUS:
        raise CityOpsContractError("5 AM synthesis status drift")
    readiness = handoff.get("readiness", {})
    for key, expected in SYNTHESIS_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"5 AM synthesis promoted {key}")
    access = handoff.get("access_policy", {})
    for key, value in access.items():
        if key in {"audience", "requires_admin_context"}:
            continue
        if value is not False:
            raise CityOpsContractError(f"5 AM synthesis access promoted {key}")
    derived = handoff.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("5 AM synthesis is not read-only")
    required_forbidden = {
        "raw_transcripts",
        "unreviewed_memory",
        "private_operator_context",
        "live_acontext_sink_writes",
        "live_acontext_retrievals",
        "stopped_project_codebases_as_active_sources",
    }
    forbidden_inputs = set(derived.get("forbidden_inputs", []))
    if not required_forbidden <= forbidden_inputs:
        raise CityOpsContractError("5 AM synthesis missing forbidden inputs")
    _assert_claim_boundaries(
        handoff.get("claim_boundaries", {}).get("safe_to_claim", []),
        handoff.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    contract = handoff.get("handoff_packet_contract_synthesis", {})
    if contract.get("fail_closed_posture") != "pause_aas_proof_layering":
        raise CityOpsContractError("5 AM synthesis handoff packet posture drift")
    required = set(contract.get("required_fields", []))
    if "blocked_claims" not in required or "recommended_posture" not in required:
        raise CityOpsContractError("5 AM synthesis handoff packet fields drift")
