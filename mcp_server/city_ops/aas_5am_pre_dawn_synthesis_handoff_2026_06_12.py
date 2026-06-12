"""Internal/admin 5 AM pre-dawn synthesis handoff for June 12 AAS work.

This artifact consumes the 4 AM exponential value connection board and turns the
night's AAS-only discoveries into a daytime handoff. It deliberately stays on the
safe side of the current no-answer boundary: no stopped-project work, no operator
answer or approval, no customer/public/worker surface, no queue/dispatch,
no live Acontext/IRC/session-manager mutation, no reputation/Worker Skill DNA,
no payment or production reverification, and no GPS/raw metadata/private-context
release.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_exponential_value_connection_board import (
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME,
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM,
    AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SCHEMA,
    VALUE_CONNECTION_BLOCKED_CLAIMS,
    load_aas_exponential_value_connection_board,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SCHEMA = (
    "city_ops.aas_5am_pre_dawn_synthesis_handoff_2026_06_12.v1"
)
AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_FILENAME = (
    "aas_5am_pre_dawn_synthesis_handoff_2026_06_12.json"
)
AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SAFE_CLAIM = (
    "internal_admin_aas_5am_pre_dawn_synthesis_handoff_2026_06_12_landed"
)
AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_ID = (
    "execution_market.aas.pre_dawn_synthesis_handoff.2026_06_12_0500"
)
AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_STATUS = (
    "internal_admin_daytime_handoff_only_no_answer_or_external_promotion"
)

FIVE_AM_2026_06_12_BLOCKED_CLAIMS = [
    *VALUE_CONNECTION_BLOCKED_CLAIMS,
    "five_am_2026_06_12_records_operator_answer",
    "five_am_2026_06_12_records_operator_approval",
    "five_am_2026_06_12_creates_answer_receipt",
    "five_am_2026_06_12_selects_future_answer",
    "five_am_2026_06_12_treats_synthesis_as_authority",
    "five_am_2026_06_12_performs_live_acontext_write_or_retrieve",
    "five_am_2026_06_12_mutates_irc_or_session_manager",
    "five_am_2026_06_12_creates_customer_public_or_worker_surface",
    "five_am_2026_06_12_authorizes_catalog_pricing_quote_route_queue_or_dispatch",
    "five_am_2026_06_12_emits_erc8004_reputation_or_worker_skill_dna",
    "five_am_2026_06_12_reverifies_payment_production_or_chain_state",
    "five_am_2026_06_12_releases_gps_raw_metadata_private_context_or_pii",
    "five_am_2026_06_12_grants_legal_safety_repair_insurance_or_sla_authority",
    "five_am_2026_06_12_publishes_worker_copyable_doctrine",
    "five_am_2026_06_12_works_on_autojob_frontier_academy_kk_v2_or_karmacadabra",
]

FIVE_AM_2026_06_12_READINESS = {
    "handoff_landed": True,
    "source_connection_board_verified": True,
    "dream_priorities_precedence_preserved": True,
    "daytime_recommendations_prepared": True,
    "memory_update_prepared": True,
    "operator_answer_recorded": False,
    "operator_approval_recorded": False,
    "answer_receipt_created": False,
    "future_answer_selected": False,
    "autojob_work_performed": False,
    "frontier_academy_work_performed": False,
    "kk_v2_work_performed": False,
    "karmacadabra_v2_work_performed": False,
    "customer_public_worker_surface_created": False,
    "catalog_pricing_quote_route_queue_or_dispatch_authorized": False,
    "runtime_acontext_irc_or_session_manager_mutated": False,
    "live_acontext_write_or_retrieve_performed": False,
    "payment_or_production_reverified": False,
    "erc8004_reputation_or_worker_skill_dna_emitted": False,
    "exact_gps_raw_metadata_private_context_or_pii_exposed": False,
    "worker_copyable_doctrine_published": False,
}

_FORBIDDEN_SAFE_CLAIMS = set(FIVE_AM_2026_06_12_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "future_answer_selected",
    "customer_copy_ready",
    "public_dashboard_ready",
    "worker_instruction_ready",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
    "live_acontext_ready",
    "irc_session_manager_mutated",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "private_context_release_ready",
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


def build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(
    *,
    artifact_dir: str | Path | None = None,
    connection_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic June 12 5 AM AAS handoff."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    source = connection_board or load_aas_exponential_value_connection_board(
        artifact_dir=base_dir
    )
    _assert_connection_board_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM,
            AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *FIVE_AM_2026_06_12_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    handoff: dict[str, Any] = {
        "schema": AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SCHEMA,
        "handoff_id": AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_ID,
        "handoff_status": AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_STATUS,
        "source_connection_board": {
            "file": AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME,
            "schema": source["schema"],
            "board_id": source["board_id"],
            "safe_claim": AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM,
            "digest_sha256": _stable_digest(source),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "source_precedence": "dream_priorities_wins_over_stale_cron_payload",
            "allowed_lane": "Execution Market AAS / City-as-a-Service internal/admin planning",
            "selected_posture_now": "pause_aas_proof_layering",
        },
        "night_synthesis": _night_synthesis(source),
        "daytime_priority_queue": _daytime_priority_queue(),
        "memory_update_packet": _memory_update_packet(source),
        "strategic_recommendations": _strategic_recommendations(),
        "handoff_cards": _handoff_cards(source),
        "readiness": dict(FIVE_AM_2026_06_12_READINESS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "handoff_digest_sha256": "",
    }
    handoff["handoff_digest_sha256"] = _stable_digest(
        {k: v for k, v in handoff.items() if k != "handoff_digest_sha256"}
    )
    _assert_handoff_conservative(handoff, connection_board=source)
    return handoff


def write_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic June 12 5 AM AAS handoff."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    handoff = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_FILENAME
    path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted June 12 5 AM AAS handoff."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    packet = json.loads(
        (base_dir / AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source = load_aas_exponential_value_connection_board(artifact_dir=base_dir)
    _assert_handoff_conservative(packet, connection_board=source)
    expected = build_aas_5am_pre_dawn_synthesis_handoff_2026_06_12(
        artifact_dir=base_dir,
        connection_board=source,
    )
    if packet != expected:
        raise CityOpsContractError("June 12 5 AM pre-dawn synthesis handoff drifted")
    return packet


def _night_synthesis(source: dict[str, Any]) -> list[dict[str, str]]:
    patterns = {row["question"]: row for row in source["connection_patterns"]}
    return [
        {
            "system": "memory_system",
            "insight": patterns[
                "what_patterns_emerge_from_memory_system_data"
            ]["pattern"],
            "daytime_use": "update durable memory with digest-backed safe claims, blocked claims, posture, and one next gate; do not replay raw/private context",
            "next_gate": "operator_answer_receipt_or_hold",
        },
        {
            "system": "acontext_and_runtime_memory",
            "insight": "Acontext remains a future runtime lane, not a live truth claim, until prerequisite gates pass",
            "daytime_use": "if runtime-memory lane is selected later, run existing prerequisite gates before any write/retrieve claim",
            "next_gate": "acontext_prerequisite_gate_only_if_selected",
        },
        {
            "system": "irc_session_coordination",
            "insight": patterns[
                "how_irc_coordination_insights_inform_strategy"
            ]["pattern"],
            "daytime_use": "carry compact source refs and blocked claims across agents instead of long transcript dependencies",
            "next_gate": "compact_handoff_card_review",
        },
        {
            "system": "execution_market_aas_strategy",
            "insight": patterns[
                "what_cross_project_intelligence_flows_create_multiplier_effects"
            ]["pattern"],
            "daytime_use": "use stale-context detection as a product-control pattern for AAS operations; do not autoroute into stopped projects",
            "next_gate": "priority_firewall_before_any_new_lane",
        },
    ]


def _daytime_priority_queue() -> list[dict[str, str]]:
    return [
        {
            "priority": "P0",
            "action": "keep_pause_aas_proof_layering",
            "why": "No explicit operator answer or runtime truth appeared overnight; more wrapper proofs would add noise, not readiness.",
            "success_check": "Any daytime AAS move names one source artifact, one safe claim, blocked claims, and exactly one next gate.",
        },
        {
            "priority": "P1",
            "action": "if_saúl_answers_create_one_digest_backed_answer_receipt",
            "why": "The intake packet and repaired template are ready, but only a real allowed answer can move the lane.",
            "success_check": "Receipt validates blocked_claims_preserved true and uses an opaque non-secret reference, not private context.",
        },
        {
            "priority": "P1",
            "action": "refresh_the_source_of_truth_index_only_when_selecting_the_daytime_entrypoint",
            "why": "The useful daytime entrypoint is now the June 12 chain: intake repair, stale-cron firewall, value board, and this handoff.",
            "success_check": "Index/digests are refreshed as coordination metadata only, not as launch/customer authority.",
        },
        {
            "priority": "P2",
            "action": "turn_firewall_pattern_into_operator_cockpit_copy_later",
            "why": "The strongest product pattern is not more planning; it is a visible stop/go control that prevents stale prompts from driving work.",
            "success_check": "Copy stays internal/admin unless separately approved for public/customer exposure.",
        },
    ]


def _memory_update_packet(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "write_to_daily_memory": True,
        "write_to_long_term_memory": False,
        "reason": "Daily memory should preserve the June 12 priority override and handoff chain; long-term memory does not need another duplicated no-answer hold unless Saúl changes direction.",
        "memory_lines": [
            "DREAM-PRIORITIES.md overrode stale AutoJob/Frontier/KK cron priorities again; AAS/City-as-a-Service remained the only active dream lane.",
            "June 12 AAS chain now has an intake packet repair, stale-cron firewall queue, exponential value connection board, and 5 AM synthesis handoff.",
            "Daytime next gate remains exactly one explicit allowed operator answer or continued pause_aas_proof_layering.",
        ],
        "source_board_digest_sha256": _stable_digest(source),
    }


def _strategic_recommendations() -> list[dict[str, str]]:
    return [
        {
            "recommendation": "make_the_priority_firewall_a_first_class_AAS_control",
            "rationale": "The stale cron conflict is a real operational failure mode for agent-run services; turning it into a stop/go control is product value, not just housekeeping.",
            "boundary": "internal/admin until customer exposure is separately approved",
        },
        {
            "recommendation": "treat_digest_backed_handoffs_as_AAS_infrastructure",
            "rationale": "Small handoff capsules let many agents coordinate without leaking raw context or resurrecting stopped work.",
            "boundary": "no live runtime or Acontext write claim from this artifact",
        },
        {
            "recommendation": "avoid_more_no_answer_proof_wrappers",
            "rationale": "The chain is now strong enough for daytime selection; more wrappers increase drift risk without adding authority.",
            "boundary": "wait for one explicit answer, one runtime prerequisite pass, or a changed DREAM-PRIORITIES.md",
        },
    ]


def _handoff_cards(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "morning_entrypoint",
            "use": "Start from this handoff plus the 4 AM value board, not the stale cron payload.",
            "source_digest_sha256": _stable_digest(source),
            "safe_claim": AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SAFE_CLAIM,
            "next_gate": "operator_answer_receipt_or_hold",
        },
        {
            "card": "stopped_project_firewall",
            "use": "AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped for dreams unless DREAM-PRIORITIES.md changes.",
            "next_gate": "reread_dream_priorities_before_any_future_dream_work",
        },
        {
            "card": "daytime_decision",
            "use": "If Saúl wants movement, ask for/select exactly one allowed AAS operator answer value; otherwise keep hold.",
            "next_gate": "single_digest_backed_answer_receipt",
        },
    ]


def _assert_connection_board_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SCHEMA:
        raise CityOpsContractError("unexpected source connection board schema")
    if source.get("board_status") != "internal_admin_pattern_recognition_only_no_runtime_or_stopped_project_movement":
        raise CityOpsContractError("unexpected source connection board status")
    readiness = source.get("readiness", {})
    for key, expected in {
        "stopped_project_pull_performed": False,
        "autojob_work_performed": False,
        "frontier_academy_work_performed": False,
        "kk_v2_work_performed": False,
        "karmacadabra_v2_work_performed": False,
        "operator_answer_recorded": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "future_answer_selected": False,
        "customer_public_worker_surface_created": False,
        "catalog_pricing_quote_route_queue_or_dispatch_authorized": False,
        "runtime_acontext_irc_or_session_manager_mutated": False,
        "live_acontext_write_or_retrieve_performed": False,
        "payment_or_production_reverified": False,
        "erc8004_reputation_or_worker_skill_dna_emitted": False,
        "exact_gps_raw_metadata_private_context_or_pii_exposed": False,
        "worker_copyable_doctrine_published": False,
    }.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"source connection board promoted {key}")
    if AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("source connection board safe claim missing")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"overlapping safe and blocked claims: {sorted(overlap)}")
    forbidden = set(safe_to_claim) & _FORBIDDEN_SAFE_CLAIMS
    if forbidden:
        raise CityOpsContractError(f"forbidden safe claims: {sorted(forbidden)}")


def _assert_handoff_conservative(
    handoff: dict[str, Any], *, connection_board: dict[str, Any]
) -> None:
    _assert_connection_board_conservative(connection_board)
    if handoff.get("schema") != AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_SCHEMA:
        raise CityOpsContractError("unexpected 5 AM handoff schema")
    if handoff.get("handoff_status") != AAS_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_12_STATUS:
        raise CityOpsContractError("unexpected 5 AM handoff status")
    if handoff.get("source_connection_board", {}).get("digest_sha256") != _stable_digest(
        connection_board
    ):
        raise CityOpsContractError("source connection board digest mismatch")
    readiness = handoff.get("readiness", {})
    for key, expected in FIVE_AM_2026_06_12_READINESS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"5 AM handoff readiness drifted: {key}")
    boundaries = handoff.get("claim_boundaries", {})
    _assert_claim_boundaries(
        boundaries.get("safe_to_claim", []), boundaries.get("do_not_claim_yet", [])
    )
    if not set(FIVE_AM_2026_06_12_BLOCKED_CLAIMS) <= set(
        boundaries.get("do_not_claim_yet", [])
    ):
        raise CityOpsContractError("5 AM blocked claims not preserved")
    expected_digest = _stable_digest(
        {k: v for k, v in handoff.items() if k != "handoff_digest_sha256"}
    )
    if handoff.get("handoff_digest_sha256") != expected_digest:
        raise CityOpsContractError("5 AM handoff digest mismatch")
