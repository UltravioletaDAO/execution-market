"""Internal/admin exponential value connection board for AAS dream sessions.

This module consumes the stale-cron firewall work queue and turns the 4 AM
pattern-recognition prompt into a deterministic AAS-only board. It maps how
memory, IRC/session coordination, cross-project intelligence, and agent
handoff discipline create multiplier effects without promoting stopped
projects, live runtime mutation, customer/public/worker surfaces, dispatch,
reputation, payments, GPS/raw metadata, private context, or worker-copyable
doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_stale_cron_firewall_work_queue import (
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME,
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM,
    AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SCHEMA,
    FIREWALL_BLOCKED_CLAIMS,
    load_aas_stale_cron_firewall_work_queue,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SCHEMA = (
    "city_ops.aas_exponential_value_connection_board.v1"
)
AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME = (
    "aas_exponential_value_connection_board.json"
)
AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM = (
    "internal_admin_aas_exponential_value_connection_board_landed"
)
AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_ID = (
    "execution_market.aas.exponential_value_connection_board.2026_06_12_0400"
)
AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_STATUS = (
    "internal_admin_pattern_recognition_only_no_runtime_or_stopped_project_movement"
)

PATTERN_QUESTIONS = [
    "what_patterns_emerge_from_memory_system_data",
    "how_irc_coordination_insights_inform_strategy",
    "what_cross_project_intelligence_flows_create_multiplier_effects",
    "which_agent_coordination_patterns_scale_best",
]

VALUE_CONNECTION_BLOCKED_CLAIMS = [
    *FIREWALL_BLOCKED_CLAIMS,
    "exponential_value_board_records_operator_answer_or_approval",
    "exponential_value_board_creates_answer_receipt",
    "exponential_value_board_selects_future_answer",
    "exponential_value_board_integrates_or_expands_stopped_projects",
    "exponential_value_board_performs_autojob_pull_or_analysis",
    "exponential_value_board_expands_frontier_academy",
    "exponential_value_board_continues_kk_v2",
    "exponential_value_board_creates_customer_public_or_worker_surface",
    "exponential_value_board_authorizes_catalog_pricing_quote_route_queue_or_dispatch",
    "exponential_value_board_mutates_runtime_acontext_irc_or_session_manager",
    "exponential_value_board_performs_live_acontext_write_or_retrieve",
    "exponential_value_board_reverifies_payment_production_or_chain_state",
    "exponential_value_board_emits_erc8004_reputation_or_worker_skill_dna",
    "exponential_value_board_releases_exact_gps_raw_metadata_private_context_or_pii",
    "exponential_value_board_grants_domain_legal_safety_repair_insurance_or_sla_authority",
    "exponential_value_board_publishes_worker_copyable_doctrine",
]

VALUE_CONNECTION_READINESS = {
    "board_landed": True,
    "source_firewall_queue_verified": True,
    "dream_priorities_precedence_preserved": True,
    "pattern_questions_answered_inside_aas_only": True,
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


def build_aas_exponential_value_connection_board(
    *,
    artifact_dir: str | Path | None = None,
    firewall_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic 4 AM AAS value-connection board."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    source = firewall_queue or load_aas_stale_cron_firewall_work_queue(
        artifact_dir=base_dir
    )
    _assert_firewall_queue_source(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM,
            AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *VALUE_CONNECTION_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    board: dict[str, Any] = {
        "schema": AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SCHEMA,
        "board_id": AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_ID,
        "board_status": AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_STATUS,
        "source_firewall_queue": {
            "file": AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME,
            "schema": source["schema"],
            "queue_id": source["queue_id"],
            "safe_claim": AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM,
            "digest_sha256": _stable_digest(source),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "source_precedence": "dream_priorities_wins_over_stale_cron_payload",
            "allowed_lane": "Execution Market AAS / City-as-a-Service internal/admin planning",
            "selected_posture_now": "pause_aas_proof_layering",
        },
        "pattern_questions": list(PATTERN_QUESTIONS),
        "connection_patterns": _connection_patterns(source),
        "multiplier_effects": _multiplier_effects(),
        "scaling_rules": _scaling_rules(),
        "operator_next_decision_surface": _operator_next_decision_surface(),
        "readiness": dict(VALUE_CONNECTION_READINESS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "board_digest_sha256": "",
    }
    board["board_digest_sha256"] = _stable_digest(
        {k: v for k, v in board.items() if k != "board_digest_sha256"}
    )
    _assert_value_board_conservative(board, firewall_queue=source)
    return board


def write_aas_exponential_value_connection_board(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic 4 AM value-connection board."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    board = build_aas_exponential_value_connection_board(artifact_dir=base_dir)
    path = base_dir / AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_exponential_value_connection_board(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted 4 AM value-connection board."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    packet = json.loads(
        (base_dir / AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source = load_aas_stale_cron_firewall_work_queue(artifact_dir=base_dir)
    _assert_value_board_conservative(packet, firewall_queue=source)
    return packet


def _connection_patterns(source: dict[str, Any]) -> list[dict[str, str]]:
    source_connections = {
        row["aas_connection"]: row for row in source["system_integration_connections"]
    }
    return [
        {
            "question": "what_patterns_emerge_from_memory_system_data",
            "pattern": "reviewed_memory_becomes_useful_when_reduced_to_digest_plus_claim_boundaries",
            "aas_multiplier": "future agents can resume from source_digest safe_to_claim do_not_claim_yet and one_next_gate without rereading private/raw context",
            "source_connection": "memory_to_acontext_digest_carry_forward",
            "safe_action": source_connections["memory_to_acontext_digest_carry_forward"]["safe_action"],
            "blocked_promotion": source_connections["memory_to_acontext_digest_carry_forward"]["blocked_promotion"],
        },
        {
            "question": "how_irc_coordination_insights_inform_strategy",
            "pattern": "irc_and_session_coordination_scale_through_small_invariant_handoff_capsules",
            "aas_multiplier": "handoffs preserve proof_anchor coordination_session compact_decision review_packet posture and next_gate instead of raw transcript replay",
            "source_connection": "irc_session_management_handoff_capsules",
            "safe_action": source_connections["irc_session_management_handoff_capsules"]["safe_action"],
            "blocked_promotion": source_connections["irc_session_management_handoff_capsules"]["blocked_promotion"],
        },
        {
            "question": "what_cross_project_intelligence_flows_create_multiplier_effects",
            "pattern": "cross_project_intelligence_compounds_as_a_firewall_filter_not_an_autorouter",
            "aas_multiplier": "stale_or_attractive_context is converted into skip reasons allowed_lane and one safe AAS action instead of unauthorized project motion",
            "source_connection": "decision_menu_without_autorouting",
            "safe_action": source_connections["decision_menu_without_autorouting"]["safe_action"],
            "blocked_promotion": source_connections["decision_menu_without_autorouting"]["blocked_promotion"],
        },
        {
            "question": "which_agent_coordination_patterns_scale_best",
            "pattern": "one_next_proof_relay_scales_better_than_volume_or_ceremony",
            "aas_multiplier": "each agent leaves exactly one allowed next proof and keeps future_gated actions false until real evidence appears",
            "source_connection": "firewall_compliance_metric",
            "safe_action": source_connections["firewall_compliance_metric"]["safe_action"],
            "blocked_promotion": source_connections["firewall_compliance_metric"]["blocked_promotion"],
        },
        {
            "question": "what_connections_create_exponential_value",
            "pattern": "payment_production_maturity_is_powerful_only_after_answer_runtime_and_delivery_gates",
            "aas_multiplier": "launch prerequisites travel as downstream context while AAS keeps product authority separate from infrastructure confidence",
            "source_connection": "future_launch_prerequisite_context_only",
            "safe_action": source_connections["future_launch_prerequisite_context_only"]["safe_action"],
            "blocked_promotion": source_connections["future_launch_prerequisite_context_only"]["blocked_promotion"],
        },
    ]


def _multiplier_effects() -> list[dict[str, str]]:
    return [
        {
            "effect": "memory_compaction",
            "why_it_multiplies": "every clean artifact lowers future context load while preserving boundaries",
            "first_safe_artifact": "digest_backed_internal_admin_handoff_card",
        },
        {
            "effect": "coordination_survival",
            "why_it_multiplies": "handoffs become resilient when the stop lines move with the safe claims",
            "first_safe_artifact": "invariant_id_claim_boundary_next_gate_tuple",
        },
        {
            "effect": "stale_context_immunity",
            "why_it_multiplies": "old priorities stop becoming accidental roadmaps",
            "first_safe_artifact": "priority_firewall_decision_row",
        },
        {
            "effect": "agent_quality_selection",
            "why_it_multiplies": "best agents are identifiable by proof discipline not output size",
            "first_safe_artifact": "boundary_preservation_and_one_next_proof_score",
        },
    ]


def _scaling_rules() -> list[dict[str, str]]:
    return [
        {
            "rule": "carry_small_truth_not_big_context",
            "test": "artifact has source digest safe claims blocked claims posture and next gate",
            "failure_mode": "raw context replay leaks private data or revives stopped work",
        },
        {
            "rule": "separate_observation_from_authority",
            "test": "observed documented heard and inconclusive stay distinct from approved launched dispatched or certified",
            "failure_mode": "internal evidence turns into customer or legal claims",
        },
        {
            "rule": "one_next_proof_only",
            "test": "future-gated actions stay false and one concrete next proof is named",
            "failure_mode": "agents layer ceremonies after the stop condition is already known",
        },
        {
            "rule": "firewall_before_flywheel",
            "test": "DREAM-PRIORITIES and blocked claims are checked before multiplier work",
            "failure_mode": "cross-project intelligence becomes unauthorized autorouting",
        },
    ]


def _operator_next_decision_surface() -> dict[str, Any]:
    return {
        "default_posture": "pause_aas_proof_layering",
        "allowed_now": [
            "hold_pause_aas_proof_layering_and_do_not_add_downstream_proof_wrappers",
            "read_dream_priorities_first_and_ignore_stopped_project_instructions",
        ],
        "future_gated_only": [
            "create_one_separate_digest_backed_answer_receipt_if_a_real_operator_answer_arrives",
            "run_existing_acontext_runtime_prerequisite_gates_if_runtime_truth_becomes_available",
        ],
        "not_authorized": [
            "autojob_pull_or_integration",
            "frontier_academy_expansion",
            "kk_v2_continuation",
            "customer_public_worker_surface",
            "catalog_pricing_queue_route_or_dispatch",
            "runtime_memory_or_irc_session_manager_mutation",
            "reputation_worker_skill_dna_payment_or_production_claim",
        ],
    }


def _assert_firewall_queue_source(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SCHEMA:
        raise CityOpsContractError("AAS value board source firewall schema drift")
    if AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("AAS value board source firewall safe claim missing")
    if packet.get("selected_posture_now") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS value board source posture drift")
    priority = packet.get("governing_priority", {})
    if priority.get("source_precedence") != "dream_priorities_wins_over_stale_cron_payload":
        raise CityOpsContractError("AAS value board source priority precedence drift")
    readiness = packet.get("readiness", {})
    for forbidden in [
        "stopped_project_pull_performed",
        "autojob_work_performed",
        "frontier_academy_work_performed",
        "kk_v2_work_performed",
        "runtime_acontext_irc_or_session_manager_mutated",
        "payment_or_production_reverified",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"AAS value board source promoted {forbidden}")


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS value board claim overlap: {sorted(overlap)}"
        )


def _assert_value_board_conservative(
    packet: dict[str, Any], *, firewall_queue: dict[str, Any]
) -> None:
    _assert_firewall_queue_source(firewall_queue)
    if packet.get("schema") != AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SCHEMA:
        raise CityOpsContractError("AAS value board schema drift")
    if packet.get("board_id") != AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_ID:
        raise CityOpsContractError("AAS value board id drift")
    if packet.get("board_status") != AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_STATUS:
        raise CityOpsContractError("AAS value board status drift")
    source = packet.get("source_firewall_queue", {})
    if source.get("digest_sha256") != _stable_digest(firewall_queue):
        raise CityOpsContractError("AAS value board source digest drift")

    priority = packet.get("governing_priority", {})
    if priority.get("selected_posture_now") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS value board promoted posture")
    if priority.get("allowed_lane") != "Execution Market AAS / City-as-a-Service internal/admin planning":
        raise CityOpsContractError("AAS value board allowed lane drift")

    if packet.get("pattern_questions") != PATTERN_QUESTIONS:
        raise CityOpsContractError("AAS value board pattern question drift")
    if len(packet.get("connection_patterns", [])) != 5:
        raise CityOpsContractError("AAS value board connection pattern drift")
    if len(packet.get("multiplier_effects", [])) != 4:
        raise CityOpsContractError("AAS value board multiplier effect drift")
    if len(packet.get("scaling_rules", [])) != 4:
        raise CityOpsContractError("AAS value board scaling rule drift")

    readiness = packet.get("readiness", {})
    for key, expected in VALUE_CONNECTION_READINESS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS value board readiness promoted {key}")

    surface = packet.get("operator_next_decision_surface", {})
    if surface.get("default_posture") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS value board decision surface posture drift")
    if "autojob_pull_or_integration" not in surface.get("not_authorized", []):
        raise CityOpsContractError("AAS value board stopped-project block missing")
    if any("autojob" in action for action in surface.get("allowed_now", [])):
        raise CityOpsContractError("AAS value board allowed stopped project")

    safe = packet.get("claim_boundaries", {}).get("safe_to_claim", [])
    blocked = packet.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_EXPONENTIAL_VALUE_CONNECTION_BOARD_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS value board safe claim missing")
    if not set(VALUE_CONNECTION_BLOCKED_CLAIMS) <= set(blocked):
        raise CityOpsContractError("AAS value board blocked claims missing")
    _assert_no_claim_overlap(safe, blocked)

    expected_digest = _stable_digest(
        {k: v for k, v in packet.items() if k != "board_digest_sha256"}
    )
    if packet.get("board_digest_sha256") != expected_digest:
        raise CityOpsContractError("AAS value board digest drift")
