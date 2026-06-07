"""Internal/admin AAS system-integration strength bridge packet.

This slice consumes the no-answer daytime operator prompt packet and turns the
3 AM system-integration theme into a conservative, digest-backed bridge between
current strengths: memory/Acontext planning, IRC/session coordination, decision
support, observability, payment maturity, production infrastructure, and agent
coordination. It is deliberately not an operator answer, approval record, answer
receipt, customer/worker/public copy, route, queue, dispatch surface, live
runtime mutation, payment reverification, reputation action, or stopped-project
integration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_no_answer_daytime_operator_prompt_packet import (
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM,
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SCHEMA,
    AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_STATUS,
    PROMPT_ALLOWED_ANSWER_VALUES,
    PROMPT_BLOCKED_CLAIMS,
    load_aas_no_answer_daytime_operator_prompt_packet,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SCHEMA = (
    "city_ops.aas_system_integration_strength_bridge_packet.v1"
)
AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME = (
    "aas_system_integration_strength_bridge_packet.json"
)
AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM = (
    "internal_admin_aas_system_integration_strength_bridge_packet_landed"
)
AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_ID = (
    "execution_market.aas.system_integration_strength_bridge_packet.2026_06_07_0300"
)
AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_STATUS = (
    "internal_admin_bridge_packet_only_no_answer_no_runtime_payment_or_stopped_project_movement"
)

FALSE_FLAGS = {
    "bridge_records_operator_answer": False,
    "bridge_records_operator_approval": False,
    "bridge_creates_answer_receipt": False,
    "bridge_selects_future_answer": False,
    "bridge_creates_customer_public_or_worker_copy": False,
    "bridge_creates_catalog_pricing_quote_route_or_queue": False,
    "bridge_launches_dispatch_or_worker_instruction": False,
    "bridge_mutates_runtime_acontext_irc_or_session_manager": False,
    "bridge_reverifies_payment_or_production": False,
    "bridge_emits_reputation_or_worker_skill_dna": False,
    "bridge_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "bridge_grants_domain_legal_regulatory_safety_repair_or_sla_authority": False,
    "bridge_publishes_worker_copyable_doctrine": False,
    "bridge_integrates_or_expands_stopped_projects": False,
}

BRIDGE_LANES = [
    "memory_acontext_planning",
    "irc_session_management",
    "cross_project_decision_support",
    "agent_observability_success_metrics",
    "payment_integration_strength_reference",
    "production_infrastructure_operational_reference",
    "agent_coordination_handoff",
]

REQUIRED_PACKET_FIELDS = [
    "source_file",
    "source_digest_sha256",
    "safe_claim",
    "blocked_claims",
    "next_gate",
    "recommended_posture",
]

STRENGTH_BRIDGE_BLOCKED_CLAIMS = [
    *PROMPT_BLOCKED_CLAIMS,
    "strength_bridge_records_operator_answer",
    "strength_bridge_records_operator_approval",
    "strength_bridge_creates_answer_receipt",
    "strength_bridge_selects_future_answer",
    "strength_bridge_treats_system_integration_as_permission",
    "strength_bridge_creates_customer_public_or_worker_surface",
    "strength_bridge_authorizes_catalog_pricing_quote_route_queue_or_dispatch",
    "strength_bridge_creates_worker_instruction_or_worker_copyable_doctrine",
    "strength_bridge_mutates_runtime_acontext_irc_or_session_manager",
    "strength_bridge_reverifies_payment_production_or_chain_integrations",
    "strength_bridge_attaches_reputation_worker_skill_dna_or_portable_credential",
    "strength_bridge_releases_exact_gps_raw_metadata_private_context_or_pii",
    "strength_bridge_grants_domain_legal_regulatory_safety_repair_or_sla_authority",
    "strength_bridge_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(STRENGTH_BRIDGE_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "route_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "live_acontext_ready",
    "irc_session_manager_mutated",
    "runtime_parity_proven",
    "payment_production_reverified",
    "eight_chain_payment_reverified",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "gps_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
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


def _assert_source_prompt_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SCHEMA:
        raise CityOpsContractError("AAS strength bridge source prompt schema drift")
    if packet.get("packet_status") != AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_STATUS:
        raise CityOpsContractError("AAS strength bridge source prompt status drift")
    safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS strength bridge source prompt safe claim missing")
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(PROMPT_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS strength bridge source prompt missing blocked claims: {sorted(missing_blocked)}"
        )
    state = packet.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS strength bridge source prompt promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS strength bridge source prompt selected decision")
    prompt = packet.get("daytime_prompt_packet", {})
    if prompt.get("allowed_answer_values") != PROMPT_ALLOWED_ANSWER_VALUES:
        raise CityOpsContractError("AAS strength bridge source prompt answer value drift")
    if prompt.get("still_blocked") is not True:
        raise CityOpsContractError("AAS strength bridge source prompt unblocked")
    firewall = packet.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS strength bridge source prompt allowed {key}")


def _build_bridge_lanes(prompt_packet: dict[str, Any]) -> list[dict[str, Any]]:
    source_digest = _stable_digest(prompt_packet)
    safe_claim = AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM
    blocked_claims = prompt_packet["claim_boundaries"]["do_not_claim_yet"]
    next_gate = "separate_explicit_operator_answer_receipt_then_specific_gate"

    return [
        {
            "lane": "memory_acontext_planning",
            "strength_reference": "intelligent_memory_and_acontext_planning",
            "safe_bridge_use": "carry_digest_backed_packets_and_reviewed_summaries_only",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "source_file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "source_digest_sha256": source_digest,
            "safe_claim": safe_claim,
            "blocked_claims": blocked_claims,
            "next_gate": next_gate,
            "recommended_posture": "digest_only_no_live_runtime_memory_write_or_retrieve",
        },
        {
            "lane": "irc_session_management",
            "strength_reference": "legendary_agent_coordination_and_session_handoff",
            "safe_bridge_use": "share_handoff_capsules_with_safe_claim_blocked_claims_next_gate_and_posture",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "source_file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "source_digest_sha256": source_digest,
            "safe_claim": safe_claim,
            "blocked_claims": blocked_claims,
            "next_gate": next_gate,
            "recommended_posture": "read_only_handoff_no_irc_or_session_manager_mutation",
        },
        {
            "lane": "cross_project_decision_support",
            "strength_reference": "cross_project_decision_support_without_cross_project_execution",
            "safe_bridge_use": "present_one_allowed_answer_value_or_hold_without_selecting_for_the_operator",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "source_file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "source_digest_sha256": source_digest,
            "safe_claim": safe_claim,
            "blocked_claims": blocked_claims,
            "next_gate": next_gate,
            "recommended_posture": "decision_menu_only_no_autorouting_or_stopped_project_integration",
        },
        {
            "lane": "agent_observability_success_metrics",
            "strength_reference": "agent_observability_and_success_metrics",
            "safe_bridge_use": "track_internal_counts_for_prompt_packet_integrity_blocked_claim_preservation_and_test_status",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "source_file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "source_digest_sha256": source_digest,
            "safe_claim": safe_claim,
            "blocked_claims": blocked_claims,
            "next_gate": next_gate,
            "recommended_posture": "internal_admin_metrics_only_no_dashboard_or_customer_metric_promotion",
        },
        {
            "lane": "payment_integration_strength_reference",
            "strength_reference": "eight_chain_payment_integration_maturity_reference",
            "safe_bridge_use": "name_payment_maturity_as_future_downstream_prerequisite_context_only",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "source_file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "source_digest_sha256": source_digest,
            "safe_claim": safe_claim,
            "blocked_claims": blocked_claims,
            "next_gate": next_gate,
            "recommended_posture": "no_payment_or_chain_reverification_from_this_bridge",
        },
        {
            "lane": "production_infrastructure_operational_reference",
            "strength_reference": "production_infrastructure_operational_reference",
            "safe_bridge_use": "carry_a_deploy_gate_question_for_future_served_or_runtime_surfaces",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "source_file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "source_digest_sha256": source_digest,
            "safe_claim": safe_claim,
            "blocked_claims": blocked_claims,
            "next_gate": next_gate,
            "recommended_posture": "no_deploy_claim_for_internal_admin_fixture_and_docs_only",
        },
        {
            "lane": "agent_coordination_handoff",
            "strength_reference": "agent_coordination_at_legendary_levels",
            "safe_bridge_use": "give_future_agents_a_small_firewall_first_packet_before_any_execution",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "source_file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "source_digest_sha256": source_digest,
            "safe_claim": safe_claim,
            "blocked_claims": blocked_claims,
            "next_gate": next_gate,
            "recommended_posture": "start_from_dream_priorities_and_prompt_packet_before_action",
        },
    ]


def build_aas_system_integration_strength_bridge_packet(
    *,
    artifact_dir: str | Path | None = None,
    source_prompt_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the conservative AAS system-integration strength bridge packet."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    prompt_packet = source_prompt_packet or load_aas_no_answer_daytime_operator_prompt_packet(
        artifact_dir=source_dir
    )
    _assert_source_prompt_packet(prompt_packet)

    packet = {
        "schema": AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SCHEMA,
        "packet_id": AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_ID,
        "packet_status": AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_STATUS,
        "source_prompt_packet": {
            "file": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME,
            "schema": prompt_packet["schema"],
            "packet_id": prompt_packet["packet_id"],
            "safe_claim": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM,
            "digest_sha256": _stable_digest(prompt_packet),
            "allowed_answer_values": prompt_packet["daytime_prompt_packet"]["allowed_answer_values"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service system-integration planning",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_decision": None,
            "recommended_no_human_posture": "use_strength_bridge_as_read_only_handoff_then_wait_for_one_explicit_answer_or_hold",
        },
        "readiness": dict(FALSE_FLAGS),
        "system_integration_strength_bridge": {
            "allowed_use": "internal_admin_strength_connection_packet_only",
            "bridge_goal": "connect_current_system_strengths_to_the_no_answer_aas_packet_without_creating_permission",
            "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
            "lanes": _build_bridge_lanes(prompt_packet),
            "handoff_rule": (
                "Every future memory, Acontext, IRC, observability, payment, production, or agent-coordination "
                "consumer must carry source_file, source_digest_sha256, safe_claim, blocked_claims, next_gate, "
                "and recommended_posture before acting. Missing fields mean hold, not infer."
            ),
            "still_blocked": True,
        },
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM,
                AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(STRENGTH_BRIDGE_BLOCKED_CLAIMS),
        },
        "packet_digest_sha256": "",
    }
    packet["packet_digest_sha256"] = _stable_digest(
        {k: v for k, v in packet.items() if k != "packet_digest_sha256"}
    )
    _assert_strength_bridge_packet_conservative(packet, source_prompt_packet=prompt_packet)
    return packet


def write_aas_system_integration_strength_bridge_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the AAS system-integration strength bridge packet."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_system_integration_strength_bridge_packet(artifact_dir=base_dir)
    path = base_dir / AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_system_integration_strength_bridge_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted strength bridge packet."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    packet = json.loads(
        (base_dir / AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_prompt_packet = load_aas_no_answer_daytime_operator_prompt_packet(
        artifact_dir=base_dir
    )
    _assert_strength_bridge_packet_conservative(
        packet, source_prompt_packet=source_prompt_packet
    )
    return packet


def _assert_strength_bridge_packet_conservative(
    packet: dict[str, Any], *, source_prompt_packet: dict[str, Any]
) -> None:
    _assert_source_prompt_packet(source_prompt_packet)
    if packet.get("schema") != AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SCHEMA:
        raise CityOpsContractError("AAS strength bridge packet schema drift")
    if packet.get("packet_id") != AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_ID:
        raise CityOpsContractError("AAS strength bridge packet id drift")
    if packet.get("packet_status") != AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_STATUS:
        raise CityOpsContractError("AAS strength bridge packet status drift")

    source = packet.get("source_prompt_packet", {})
    if source.get("digest_sha256") != _stable_digest(source_prompt_packet):
        raise CityOpsContractError("AAS strength bridge packet source digest drift")
    if source.get("allowed_answer_values") != PROMPT_ALLOWED_ANSWER_VALUES:
        raise CityOpsContractError("AAS strength bridge packet source answer values drift")

    state = packet.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS strength bridge packet promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS strength bridge packet selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if packet.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS strength bridge packet readiness promoted {key}")

    bridge = packet.get("system_integration_strength_bridge", {})
    if bridge.get("allowed_use") != "internal_admin_strength_connection_packet_only":
        raise CityOpsContractError("AAS strength bridge packet use drift")
    if bridge.get("still_blocked") is not True:
        raise CityOpsContractError("AAS strength bridge packet unblocked")
    if set(REQUIRED_PACKET_FIELDS) - set(bridge.get("required_packet_fields", [])):
        raise CityOpsContractError("AAS strength bridge packet missing required fields")
    lanes = bridge.get("lanes", [])
    lane_names = [lane.get("lane") for lane in lanes]
    if lane_names != BRIDGE_LANES:
        raise CityOpsContractError("AAS strength bridge packet lane drift")
    for lane in lanes:
        missing = set(REQUIRED_PACKET_FIELDS) - set(lane.get("required_packet_fields", []))
        if missing:
            raise CityOpsContractError(
                f"AAS strength bridge packet lane missing required fields: {sorted(missing)}"
            )
        if lane.get("source_digest_sha256") != _stable_digest(source_prompt_packet):
            raise CityOpsContractError("AAS strength bridge packet lane source digest drift")
        if lane.get("safe_claim") != AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM:
            raise CityOpsContractError("AAS strength bridge packet lane safe claim drift")
        if lane.get("next_gate") != "separate_explicit_operator_answer_receipt_then_specific_gate":
            raise CityOpsContractError("AAS strength bridge packet lane next gate drift")
        if not lane.get("recommended_posture"):
            raise CityOpsContractError("AAS strength bridge packet lane posture missing")

    safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS strength bridge packet safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS strength bridge packet forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(STRENGTH_BRIDGE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS strength bridge packet missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS strength bridge packet claim overlap: {sorted(overlap)}"
        )

    firewall = packet.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS strength bridge packet allowed {key}")
