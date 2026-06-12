"""Internal/admin stale-cron firewall work queue for AAS dream sessions.

This module consumes the system-integration strength bridge packet and records
how a dream checkpoint should reconcile stale cron instructions with
``DREAM-PRIORITIES.md``. It is deliberately a read-only selector: it does not
pull stopped repositories, create customer/public/worker copy, register routes,
launch queues, dispatch workers, mutate Acontext/IRC/session-manager runtime,
reverify payments or production, emit ERC-8004 reputation, or expose private
context, GPS, raw metadata, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_system_integration_strength_bridge_packet import (
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME,
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SCHEMA,
    BRIDGE_LANES,
    STRENGTH_BRIDGE_BLOCKED_CLAIMS,
    load_aas_system_integration_strength_bridge_packet,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SCHEMA = (
    "city_ops.aas_stale_cron_firewall_work_queue.v1"
)
AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME = "aas_stale_cron_firewall_work_queue.json"
AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM = (
    "internal_admin_aas_stale_cron_firewall_work_queue_landed"
)
AAS_STALE_CRON_FIREWALL_WORK_QUEUE_ID = (
    "execution_market.aas.stale_cron_firewall_work_queue.2026_06_12_0300"
)
AAS_STALE_CRON_FIREWALL_WORK_QUEUE_STATUS = (
    "internal_admin_firewall_selector_only_no_stopped_project_or_runtime_movement"
)

STOPPED_LANE_DECISIONS = [
    {
        "lane": "autojob_pull_analysis_or_em_integration",
        "decision": "skip",
        "reason": "stopped_by_dream_priorities",
    },
    {
        "lane": "frontier_academy_guide_or_pdf_expansion",
        "decision": "skip",
        "reason": "stopped_by_dream_priorities",
    },
    {
        "lane": "kk_v2_swarm_reputation_lifecycle_or_orchestrator",
        "decision": "skip",
        "reason": "stopped_by_dream_priorities",
    },
    {
        "lane": "karmacadabra_v2",
        "decision": "skip",
        "reason": "stopped_by_dream_priorities",
    },
]

ALLOWED_NEXT_ACTIONS = [
    {
        "condition": "real_operator_answer_arrives",
        "action": "create_one_separate_digest_backed_answer_receipt_then_run_the_specific_gate",
        "allowed_now": False,
    },
    {
        "condition": "no_real_operator_answer_exists",
        "action": "hold_pause_aas_proof_layering_and_do_not_add_downstream_proof_wrappers",
        "allowed_now": True,
    },
    {
        "condition": "runtime_truth_becomes_available_later",
        "action": "run_existing_acontext_runtime_prerequisite_gates_before_one_live_parity_attempt",
        "allowed_now": False,
    },
    {
        "condition": "future_cron_mentions_stopped_projects",
        "action": "read_dream_priorities_first_and_ignore_stopped_project_instructions",
        "allowed_now": True,
    },
]

FIREWALL_READINESS = {
    "stale_cron_firewall_landed": True,
    "source_strength_bridge_verified": True,
    "dream_priorities_wins_over_cron_payload": True,
    "allowed_lane_is_execution_market_aas_only": True,
    "stopped_project_pull_performed": False,
    "autojob_work_performed": False,
    "frontier_academy_work_performed": False,
    "kk_v2_work_performed": False,
    "karmacadabra_v2_work_performed": False,
    "operator_answer_recorded": False,
    "operator_approval_recorded": False,
    "answer_receipt_created": False,
    "customer_public_worker_surface_created": False,
    "route_catalog_pricing_queue_or_dispatch_enabled": False,
    "runtime_acontext_irc_or_session_manager_mutated": False,
    "live_acontext_write_or_retrieve_performed": False,
    "payment_or_production_reverified": False,
    "erc8004_reputation_or_worker_skill_dna_emitted": False,
    "exact_gps_raw_metadata_private_context_or_pii_exposed": False,
    "worker_copyable_doctrine_published": False,
}

FIREWALL_BLOCKED_CLAIMS = [
    *STRENGTH_BRIDGE_BLOCKED_CLAIMS,
    "stale_cron_firewall_performed_autojob_pull_or_analysis",
    "stale_cron_firewall_expanded_frontier_academy",
    "stale_cron_firewall_continued_kk_v2",
    "stale_cron_firewall_created_operator_answer_or_approval",
    "stale_cron_firewall_created_answer_receipt",
    "stale_cron_firewall_selected_future_answer",
    "stale_cron_firewall_authorized_customer_public_or_worker_surface",
    "stale_cron_firewall_authorized_catalog_pricing_queue_route_or_dispatch",
    "stale_cron_firewall_mutated_runtime_acontext_irc_or_session_manager",
    "stale_cron_firewall_reverified_payment_production_or_chain_state",
    "stale_cron_firewall_emitted_reputation_or_worker_skill_dna",
    "stale_cron_firewall_released_exact_gps_raw_metadata_private_context_or_pii",
    "stale_cron_firewall_granted_domain_legal_safety_repair_insurance_or_sla_authority",
    "stale_cron_firewall_published_worker_copyable_doctrine",
]


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


def build_aas_stale_cron_firewall_work_queue(
    *,
    artifact_dir: str | Path | None = None,
    strength_bridge_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic stale-cron firewall selector."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    bridge = strength_bridge_packet or load_aas_system_integration_strength_bridge_packet(
        artifact_dir=base_dir
    )
    _assert_strength_bridge_source(bridge)

    safe_to_claim = _dedupe(
        [
            *bridge["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM,
            AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *bridge["claim_boundaries"]["do_not_claim_yet"],
            *FIREWALL_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    packet: dict[str, Any] = {
        "schema": AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SCHEMA,
        "queue_id": AAS_STALE_CRON_FIREWALL_WORK_QUEUE_ID,
        "queue_status": AAS_STALE_CRON_FIREWALL_WORK_QUEUE_STATUS,
        "source_strength_bridge": {
            "file": AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME,
            "schema": bridge["schema"],
            "packet_id": bridge["packet_id"],
            "safe_claim": AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM,
            "digest_sha256": _stable_digest(bridge),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "source_precedence": "dream_priorities_wins_over_stale_cron_payload",
            "allowed_lane": "Execution Market AAS / City-as-a-Service internal/admin planning",
            "disallowed_lane_count": len(STOPPED_LANE_DECISIONS),
        },
        "stale_payload_reconciliation": {
            "payload_theme": "system_integration_focus_with_stale_stopped_project_items",
            "allowed_execution": "connect_strengths_inside_AAS_only_without_new_permission",
            "stopped_lane_decisions": [dict(row) for row in STOPPED_LANE_DECISIONS],
            "future_agent_rule": (
                "If a cron payload requests AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2 "
                "while DREAM-PRIORITIES.md still stops them, record the skip and stay inside AAS."
            ),
        },
        "system_integration_connections": [
            {
                "source_strength": "intelligent_memory_with_reviewed_insights",
                "aas_connection": "memory_to_acontext_digest_carry_forward",
                "safe_action": "preserve_source_digest_safe_claim_blocked_claims_next_gate_and_posture",
                "blocked_promotion": "no_live_write_retrieve_or_runtime_parity_claim",
            },
            {
                "source_strength": "legendary_agent_coordination",
                "aas_connection": "irc_session_management_handoff_capsules",
                "safe_action": "use_read_only_handoff_fields_and_sticky_blocked_claims",
                "blocked_promotion": "no_session_manager_or_irc_runtime_mutation",
            },
            {
                "source_strength": "cross_project_decision_support",
                "aas_connection": "decision_menu_without_autorouting",
                "safe_action": "show_hold_or_one_allowed_future_answer_value_without_selecting_it",
                "blocked_promotion": "no_stopped_project_integration_or_customer_route",
            },
            {
                "source_strength": "agent_observability_success_metrics",
                "aas_connection": "firewall_compliance_metric",
                "safe_action": "score_priority_precedence_blocked_claim_preservation_and_one_next_gate_discipline",
                "blocked_promotion": "no_customer_metric_dashboard_or_public_success_claim",
            },
            {
                "source_strength": "eight_chain_payment_and_production_maturity",
                "aas_connection": "future_launch_prerequisite_context_only",
                "safe_action": "carry_as_downstream_question_for_later_deploy_or_payment_gate",
                "blocked_promotion": "no_payment_production_or_chain_reverification_from_this_queue",
            },
        ],
        "allowed_next_actions": [dict(action) for action in ALLOWED_NEXT_ACTIONS],
        "selected_posture_now": "pause_aas_proof_layering",
        "readiness": dict(FIREWALL_READINESS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "queue_digest_sha256": "",
    }
    packet["queue_digest_sha256"] = _stable_digest(
        {k: v for k, v in packet.items() if k != "queue_digest_sha256"}
    )
    _assert_firewall_queue_conservative(packet, strength_bridge_packet=bridge)
    return packet


def write_aas_stale_cron_firewall_work_queue(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the stale-cron firewall work queue."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_stale_cron_firewall_work_queue(artifact_dir=base_dir)
    path = base_dir / AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_stale_cron_firewall_work_queue(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted stale-cron firewall work queue."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    packet = json.loads(
        (base_dir / AAS_STALE_CRON_FIREWALL_WORK_QUEUE_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    bridge = load_aas_system_integration_strength_bridge_packet(artifact_dir=base_dir)
    _assert_firewall_queue_conservative(packet, strength_bridge_packet=bridge)
    return packet


def _assert_strength_bridge_source(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SCHEMA:
        raise CityOpsContractError("AAS stale-cron firewall source bridge schema drift")
    if AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("AAS stale-cron firewall source bridge safe claim missing")
    firewall = packet.get("governing_priority", {}).get("stopped_project_firewall", {})
    expected = {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }
    if firewall != expected:
        raise CityOpsContractError("AAS stale-cron firewall source bridge stopped-project drift")
    lanes = packet.get("system_integration_strength_bridge", {}).get("lanes", [])
    if [lane.get("lane") for lane in lanes] != BRIDGE_LANES:
        raise CityOpsContractError("AAS stale-cron firewall source bridge lane drift")


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS stale-cron firewall claim overlap: {sorted(overlap)}"
        )


def _assert_firewall_queue_conservative(
    packet: dict[str, Any], *, strength_bridge_packet: dict[str, Any]
) -> None:
    _assert_strength_bridge_source(strength_bridge_packet)
    if packet.get("schema") != AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SCHEMA:
        raise CityOpsContractError("AAS stale-cron firewall schema drift")
    if packet.get("queue_id") != AAS_STALE_CRON_FIREWALL_WORK_QUEUE_ID:
        raise CityOpsContractError("AAS stale-cron firewall id drift")
    if packet.get("queue_status") != AAS_STALE_CRON_FIREWALL_WORK_QUEUE_STATUS:
        raise CityOpsContractError("AAS stale-cron firewall status drift")
    source = packet.get("source_strength_bridge", {})
    if source.get("digest_sha256") != _stable_digest(strength_bridge_packet):
        raise CityOpsContractError("AAS stale-cron firewall source digest drift")
    if packet.get("selected_posture_now") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS stale-cron firewall posture drift")

    priority = packet.get("governing_priority", {})
    if priority.get("source_precedence") != "dream_priorities_wins_over_stale_cron_payload":
        raise CityOpsContractError("AAS stale-cron firewall priority precedence drift")
    if priority.get("allowed_lane") != "Execution Market AAS / City-as-a-Service internal/admin planning":
        raise CityOpsContractError("AAS stale-cron firewall allowed lane drift")

    stopped = packet.get("stale_payload_reconciliation", {}).get("stopped_lane_decisions", [])
    if stopped != STOPPED_LANE_DECISIONS:
        raise CityOpsContractError("AAS stale-cron firewall stopped lane decision drift")
    for row in stopped:
        if row.get("decision") != "skip" or row.get("reason") != "stopped_by_dream_priorities":
            raise CityOpsContractError("AAS stale-cron firewall stopped lane promoted")

    actions = packet.get("allowed_next_actions", [])
    if actions != ALLOWED_NEXT_ACTIONS:
        raise CityOpsContractError("AAS stale-cron firewall next action drift")
    if any(
        action["allowed_now"] is True
        for action in actions
        if action["condition"] in {"real_operator_answer_arrives", "runtime_truth_becomes_available_later"}
    ):
        raise CityOpsContractError("AAS stale-cron firewall promoted future-gated action")

    readiness = packet.get("readiness", {})
    for key, expected in FIREWALL_READINESS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS stale-cron firewall readiness promoted {key}")

    safe = packet.get("claim_boundaries", {}).get("safe_to_claim", [])
    blocked = packet.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_STALE_CRON_FIREWALL_WORK_QUEUE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS stale-cron firewall safe claim missing")
    if not set(FIREWALL_BLOCKED_CLAIMS) <= set(blocked):
        raise CityOpsContractError("AAS stale-cron firewall blocked claims missing")
    _assert_no_claim_overlap(safe, blocked)

    expected_digest = _stable_digest({k: v for k, v in packet.items() if k != "queue_digest_sha256"})
    if packet.get("queue_digest_sha256") != expected_digest:
        raise CityOpsContractError("AAS stale-cron firewall digest drift")
