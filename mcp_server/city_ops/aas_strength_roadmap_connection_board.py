"""Internal/admin board connecting AAS strengths to the concept roadmap.

This board consumes the existing strength-connection control packet and the
AAS concept-gap implementation roadmap.  It deliberately stays read-only: no
Acontext writes, no IRC/session runtime changes, no product/customer/worker
surface, no queue/dispatch/reputation/payment movement, and no stopped-project
integration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS,
    ROADMAP_BLOCKED_CLAIMS,
    load_aas_concept_gap_implementation_roadmap,
)
from .aas_strength_connection_control_packet import (
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME,
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
    AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA,
    STRENGTH_CONNECTION_BLOCKED_CLAIMS,
    load_aas_strength_connection_control_packet,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR as AAS_PACKAGE_ARTIFACT_DIR
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SCHEMA = (
    "city_ops.aas_strength_roadmap_connection_board.v1"
)
AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_FILENAME = (
    "aas_strength_roadmap_connection_board.json"
)
AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SAFE_CLAIM = (
    "internal_admin_aas_strength_roadmap_connection_board_landed"
)
AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_ID = (
    "execution_market.aas.strength_roadmap_connection_board.2026_06_06_0300"
)
AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_STATUS = (
    "internal_admin_strength_to_roadmap_connection_no_answer_no_runtime_no_product_movement"
)

FALSE_FLAGS = {
    "board_records_operator_answer": False,
    "board_records_operator_approval": False,
    "board_creates_answer_receipt": False,
    "board_selects_product_lane": False,
    "board_promotes_customer_public_or_worker_surface": False,
    "board_creates_catalog_pricing_quote_or_route": False,
    "board_launches_queue_dispatch_or_worker_instruction": False,
    "board_emits_reputation_or_worker_skill_dna": False,
    "board_reverifies_payment_or_production": False,
    "board_writes_or_retrieves_live_acontext": False,
    "board_changes_irc_session_manager_runtime": False,
    "board_enables_cross_project_autorouting": False,
    "board_exposes_exact_gps_raw_metadata_or_private_context": False,
    "board_grants_domain_authority": False,
    "board_publishes_worker_copyable_doctrine": False,
    "board_integrates_or_expands_stopped_projects": False,
}

BOARD_BLOCKED_CLAIMS = [
    *STRENGTH_CONNECTION_BLOCKED_CLAIMS,
    *ROADMAP_BLOCKED_CLAIMS,
    "strength_roadmap_board_records_operator_answer",
    "strength_roadmap_board_records_operator_approval",
    "strength_roadmap_board_creates_answer_receipt",
    "strength_roadmap_board_selects_product_lane_or_launch_order",
    "strength_roadmap_board_creates_customer_public_or_worker_surface",
    "strength_roadmap_board_authorizes_catalog_pricing_quote_route_queue_or_dispatch",
    "strength_roadmap_board_creates_worker_instruction",
    "strength_roadmap_board_emits_erc8004_reputation_or_worker_skill_dna",
    "strength_roadmap_board_reverifies_payment_or_production",
    "strength_roadmap_board_writes_or_retrieves_live_acontext",
    "strength_roadmap_board_changes_irc_session_manager_runtime",
    "strength_roadmap_board_enables_cross_project_autorouting",
    "strength_roadmap_board_releases_exact_gps_raw_metadata_or_private_context",
    "strength_roadmap_board_grants_domain_authority",
    "strength_roadmap_board_publishes_worker_copyable_doctrine",
    "strength_roadmap_board_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(BOARD_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "product_lane_selected",
    "customer_surface_ready",
    "public_catalog_ready",
    "pricing_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "runtime_parity_proven",
    "live_acontext_ready",
    "irc_session_manager_enhanced",
    "cross_project_autorouting_ready",
    "gps_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}

STRENGTH_TO_ROADMAP_CARDS = [
    {
        "strength": "latest_city_ops_code_and_fixture_graph",
        "verification_level": "consumed_from_strength_packet_not_reverified_here",
        "roadmap_use": "ranked_planning_sequence_can_pick_one_low_authority_slice_without_scattered_context_rebuild",
        "primary_roadmap_lanes": ["retail_reality", "document_handoff", "compliance_desk"],
        "blocked_promotion": "not_a_launch_or_delivery_order",
    },
    {
        "strength": "eight_chain_payment_integration_confidence",
        "verification_level": "declared_context_only_not_reverified_here",
        "roadmap_use": "kept_as_later_commercial_confidence_after_product_boundary_and_operator_answer_gates_clear",
        "primary_roadmap_lanes": ["retail_reality", "document_handoff", "compliance_desk"],
        "blocked_promotion": "not_payment_readiness_not_quote_readiness",
    },
    {
        "strength": "reviewed_memory_and_insight_structure",
        "verification_level": "candidate_structure_only_not_live_acontext_sink",
        "roadmap_use": "feeds_read_only_runtime_prerequisite_inventory_after_explicit_runtime_memory_answer",
        "primary_roadmap_lanes": ["system_integration_runtime_memory"],
        "blocked_promotion": "not_live_write_retrieve_parity_not_memory_export_authority",
    },
    {
        "strength": "production_infrastructure_operational_confidence",
        "verification_level": "declared_context_only_not_reverified_here",
        "roadmap_use": "prevents_overbuilding_local_only_plans_but_does_not_change_deployment_or_route_state",
        "primary_roadmap_lanes": ["field_asset_ops", "event_readiness", "local_data_collection"],
        "blocked_promotion": "not_production_health_probe_not_public_route_ready",
    },
    {
        "strength": "agent_coordination_observability_and_success_metrics",
        "verification_level": "internal_admin_read_surface_only",
        "roadmap_use": "selects_the_next_single_proof_by_quality_of_handoff_and_blocked_claim_discipline",
        "primary_roadmap_lanes": ["incident_verification", "property_ops", "system_integration_runtime_memory"],
        "blocked_promotion": "not_erc8004_reputation_not_worker_skill_dna_not_autonomous_prioritization",
    },
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


def build_aas_strength_roadmap_connection_board(
    *,
    proof_artifact_dir: str | Path | None = None,
    package_artifact_dir: str | Path | None = None,
    strength_packet: dict[str, Any] | None = None,
    roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic read-only board connecting strengths to roadmap rows."""

    proof_dir = Path(proof_artifact_dir) if proof_artifact_dir else _default_proof_block_dir()
    package_dir = (
        Path(package_artifact_dir) if package_artifact_dir else AAS_PACKAGE_ARTIFACT_DIR
    )
    packet = strength_packet or load_aas_strength_connection_control_packet(
        artifact_dir=proof_dir
    )
    source_roadmap = roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=package_dir
    )
    _assert_strength_packet_conservative(packet)
    _assert_roadmap_conservative(source_roadmap)

    safe_to_claim = _dedupe(
        [
            *packet["claim_boundaries"]["safe_to_claim"],
            *source_roadmap["claim_boundaries"]["safe_to_claim"],
            AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
            AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *packet["claim_boundaries"]["do_not_claim_yet"],
            *source_roadmap["claim_boundaries"]["do_not_claim_yet"],
            *BOARD_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    board = {
        "schema": AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SCHEMA,
        "board_id": AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_ID,
        "board_status": AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_STATUS,
        "source_strength_packet": {
            "file": AAS_STRENGTH_CONNECTION_CONTROL_PACKET_FILENAME,
            "schema": packet["schema"],
            "packet_id": packet["packet_id"],
            "safe_claim": AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM,
            "digest_sha256": _stable_digest(packet),
        },
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": source_roadmap["schema"],
            "roadmap_id": source_roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(source_roadmap),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service strength-to-roadmap planning",
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
            "selected_product_lane": None,
            "recommended_no_human_posture": "pause_aas_proof_layering_or_keep_both_lanes_held",
        },
        "readiness": dict(FALSE_FLAGS),
        "strength_to_roadmap_cards": list(STRENGTH_TO_ROADMAP_CARDS),
        "roadmap_lane_order_snapshot": _roadmap_lane_order_snapshot(source_roadmap),
        "one_next_proof_rule": {
            "allowed_next_move": "choose_one_internal_admin_planning_slice_from_ranked_roadmap_only_after_rechecking_DREAM_PRIORITIES",
            "runtime_memory_lane_condition": "only_read_only_prerequisite_inventory_after_explicit_runtime_memory_answer",
            "forbidden_next_moves": [
                "operator_answer_synthesis",
                "customer_or_public_copy",
                "catalog_pricing_quote_route_queue_or_dispatch",
                "live_acontext_write_retrieve_or_irc_runtime_mutation",
                "erc8004_reputation_or_worker_skill_dna",
                "stopped_project_integration",
            ],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "board_digest_sha256": "",
    }
    board["board_digest_sha256"] = _stable_digest(
        {k: v for k, v in board.items() if k != "board_digest_sha256"}
    )
    _assert_board_conservative(board, strength_packet=packet, roadmap=source_roadmap)
    return board


def write_aas_strength_roadmap_connection_board(
    *,
    proof_artifact_dir: str | Path | None = None,
    package_artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic strength-to-roadmap connection board."""

    proof_dir = Path(proof_artifact_dir) if proof_artifact_dir else _default_proof_block_dir()
    proof_dir.mkdir(parents=True, exist_ok=True)
    board = build_aas_strength_roadmap_connection_board(
        proof_artifact_dir=proof_dir,
        package_artifact_dir=package_artifact_dir,
    )
    path = proof_dir / AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_strength_roadmap_connection_board(
    *,
    proof_artifact_dir: str | Path | None = None,
    package_artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the persisted strength-to-roadmap board."""

    proof_dir = Path(proof_artifact_dir) if proof_artifact_dir else _default_proof_block_dir()
    package_dir = (
        Path(package_artifact_dir) if package_artifact_dir else AAS_PACKAGE_ARTIFACT_DIR
    )
    board = json.loads(
        (proof_dir / AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    packet = load_aas_strength_connection_control_packet(artifact_dir=proof_dir)
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=package_dir)
    _assert_board_conservative(board, strength_packet=packet, roadmap=source_roadmap)
    if board != build_aas_strength_roadmap_connection_board(
        proof_artifact_dir=proof_dir,
        package_artifact_dir=package_dir,
        strength_packet=packet,
        roadmap=source_roadmap,
    ):
        raise CityOpsContractError("strength-to-roadmap connection board drifted from sources")
    return board


def _roadmap_lane_order_snapshot(roadmap: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "planning_sequence_rank": row["planning_sequence_rank"],
            "aas_family": row["aas_family"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "still_blocked": row["still_blocked"],
        }
        for row in roadmap["roadmap_rows"]
    ]


def _assert_strength_packet_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SCHEMA:
        raise CityOpsContractError("strength-to-roadmap board source packet schema drift")
    safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_STRENGTH_CONNECTION_CONTROL_PACKET_SAFE_CLAIM not in safe:
        raise CityOpsContractError("strength-to-roadmap board source packet safe claim missing")
    if set(STRENGTH_CONNECTION_BLOCKED_CLAIMS) - blocked:
        raise CityOpsContractError("strength-to-roadmap board source packet missing blocked claims")
    readiness = packet.get("readiness", {})
    for key in [
        "live_acontext_memory_integration_ready",
        "irc_session_manager_runtime_enhanced",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "payment_coverage_reverified_by_this_packet",
        "production_infrastructure_reverified_by_this_packet",
        "gps_or_metadata_exposure_allowed",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"strength-to-roadmap board source packet promoted {key}")


def _assert_roadmap_conservative(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("strength-to-roadmap board source roadmap schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("strength-to-roadmap board source roadmap status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("strength-to-roadmap board source roadmap safe claim missing")
    if set(ROADMAP_BLOCKED_CLAIMS) - blocked:
        raise CityOpsContractError("strength-to-roadmap board source roadmap missing blocked claims")
    for row in roadmap.get("roadmap_rows", []):
        if row.get("still_blocked") is not True:
            raise CityOpsContractError("strength-to-roadmap board source roadmap unblocked row")
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"strength-to-roadmap board source roadmap promoted {key}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"strength-to-roadmap board forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(BOARD_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"strength-to-roadmap board missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"strength-to-roadmap board claim overlap: {sorted(overlap)}"
        )


def _assert_board_conservative(
    board: dict[str, Any], *, strength_packet: dict[str, Any], roadmap: dict[str, Any]
) -> None:
    _assert_strength_packet_conservative(strength_packet)
    _assert_roadmap_conservative(roadmap)
    if board.get("schema") != AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_SCHEMA:
        raise CityOpsContractError("strength-to-roadmap board schema drift")
    if board.get("board_id") != AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_ID:
        raise CityOpsContractError("strength-to-roadmap board id drift")
    if board.get("board_status") != AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_STATUS:
        raise CityOpsContractError("strength-to-roadmap board status drift")
    if board.get("source_strength_packet", {}).get("digest_sha256") != _stable_digest(
        strength_packet
    ):
        raise CityOpsContractError("strength-to-roadmap board source packet digest drift")
    if board.get("source_roadmap", {}).get("digest_sha256") != _stable_digest(roadmap):
        raise CityOpsContractError("strength-to-roadmap board source roadmap digest drift")

    for key, expected in FALSE_FLAGS.items():
        if board.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"strength-to-roadmap board readiness promoted {key}")

    state = board.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"strength-to-roadmap board operator state promoted {key}")
    if state.get("selected_product_lane") is not None:
        raise CityOpsContractError("strength-to-roadmap board selected a product lane")

    cards = board.get("strength_to_roadmap_cards", [])
    if len(cards) != 5:
        raise CityOpsContractError("strength-to-roadmap board card count drift")
    for card in cards:
        if not card.get("blocked_promotion"):
            raise CityOpsContractError("strength-to-roadmap board card missing blocked promotion")

    snapshot = board.get("roadmap_lane_order_snapshot", [])
    if snapshot != _roadmap_lane_order_snapshot(roadmap):
        raise CityOpsContractError("strength-to-roadmap board roadmap snapshot drift")
    if not all(row.get("still_blocked") is True for row in snapshot):
        raise CityOpsContractError("strength-to-roadmap board unblocked roadmap snapshot")

    firewall = board.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"strength-to-roadmap board allowed {key}")

    _assert_claim_boundaries(
        board.get("claim_boundaries", {}).get("safe_to_claim", []),
        board.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
