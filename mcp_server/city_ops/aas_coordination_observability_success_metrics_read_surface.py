"""Read surface for the AAS coordination observability success-metrics board.

This module converts the internal/admin coordination metrics board into a
bounded operator-facing payload.  It is intentionally pass-through and
conservative: it does not write or retrieve live Acontext, does not modify IRC
session management runtime, does not register a public/customer route, does not
enable dispatch, does not emit reputation receipts, and does not reverify
payment or production infrastructure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA,
    COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    load_aas_coordination_observability_success_metrics_board,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA = (
    "city_ops.aas_coordination_observability_success_metrics_read_surface.v1"
)
AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME = (
    "aas_coordination_observability_success_metrics_read_surface.json"
)
AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SAFE_CLAIM = (
    "admin_aas_coordination_observability_success_metrics_read_surface_landed"
)

READ_SURFACE_BLOCKED_CLAIMS = [
    *COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    "coordination_metrics_read_surface_is_live_dashboard",
    "coordination_metrics_read_surface_changes_irc_runtime",
    "coordination_metrics_read_surface_writes_live_acontext",
    "coordination_metrics_read_surface_retrieves_live_acontext",
    "coordination_metrics_read_surface_public_or_customer_visible",
    "coordination_metrics_read_surface_authorizes_dispatch",
    "coordination_metrics_read_surface_emits_reputation",
    "coordination_metrics_read_surface_reverifies_payment_or_production",
    "coordination_metrics_read_surface_allows_gps_or_raw_metadata",
    "coordination_metrics_read_surface_publishes_worker_doctrine",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "writes_municipal_memory",
    "writes_customer_copy",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "reverifies_payment_coverage",
    "reverifies_production_infrastructure",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
    "semantic_reinterpretation_performed",
]

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "surface_promotes_live_readiness",
    "live_acontext_memory_integration_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "irc_session_manager_runtime_enhanced",
    "cross_project_decision_support_customer_ready",
    "agent_observability_live_dashboard_ready",
    "success_metrics_public_or_customer_visible",
    "customer_visible_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_coverage_reverified_by_this_surface",
    "production_infrastructure_reverified_by_this_surface",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_coordination_observability_success_metrics_read_surface(
    *,
    artifact_dir: str | Path | None = None,
    metrics_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic internal/admin cards from the metrics board."""

    source_board = metrics_board or load_aas_coordination_observability_success_metrics_board(
        artifact_dir=artifact_dir
    )
    _assert_source_board_conservative(source_board)

    safe_to_claim = _dedupe(
        [
            *source_board["claim_boundaries"]["safe_to_claim"],
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_board["claim_boundaries"]["do_not_claim_yet"],
            *COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
            *READ_SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    surface = {
        "schema": AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA,
        "surface_id": (
            "aas_coordination_observability_success_metrics_read_surface:"
            f"{source_board['board_id']}"
        ),
        "source_board_id": source_board["board_id"],
        "proof_anchor_id": source_board["proof_anchor_id"],
        "coordination_session_id": source_board["coordination_session_id"],
        "compact_decision_id": source_board["compact_decision_id"],
        "review_packet_id": source_board["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME],
            "consumes_only": [AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME],
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
            "semantic_reinterpretation_performed": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "network_route_registered": False,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "dispatch_enabled": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "render_contract": {
            "render_status": "internal_admin_coordination_metrics_read_surface_landed_not_route",
            "suggested_internal_path": "/internal/admin/city-ops/aas-coordination-observability-success-metrics",
            "network_route_registered": False,
            "layout": "four_id_header_track_cards_metric_cards_agent_success_rubric_sticky_claim_footer",
            "allowed_interpretation": "pass_through_metrics_board_fields_only",
            "response_fields": [
                "four_id_session_header",
                "integration_track_cards",
                "success_metric_cards",
                "session_management_cards",
                "agent_success_rubric_cards",
                "operator_next_action_cards",
                "claim_boundary_footer",
                "readiness",
            ],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": _surface_readiness(source_board),
        "four_id_session_header": _four_id_session_header(source_board),
        "integration_track_cards": _integration_track_cards(source_board),
        "success_metric_cards": _success_metric_cards(source_board),
        "session_management_cards": list(source_board["session_management_enhancement_cards"]),
        "agent_success_rubric_cards": _agent_success_rubric_cards(source_board),
        "operator_next_action_cards": list(source_board["operator_next_action_cards"]),
        "claim_boundary_footer": _claim_boundary_footer(safe_to_claim, do_not_claim_yet),
        "source_verdict": source_board["board_verdict"],
        "surface_verdict": "coordination_metrics_read_surface_landed_internal_admin_only",
        "operator_instruction": source_board["operator_instruction"],
    }
    _assert_surface_conservative(surface, source_board)
    return surface


def write_aas_coordination_observability_success_metrics_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic internal/admin metrics read surface fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    surface = build_aas_coordination_observability_success_metrics_read_surface(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_coordination_observability_success_metrics_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted metrics read surface."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (
        base_dir / AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_FILENAME
    ).open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    board = load_aas_coordination_observability_success_metrics_board(
        artifact_dir=base_dir
    )
    _assert_surface_conservative(surface, board)
    if surface != build_aas_coordination_observability_success_metrics_read_surface(
        artifact_dir=base_dir, metrics_board=board
    ):
        raise CityOpsContractError("coordination metrics read surface drifted from source board")
    return surface


def _surface_readiness(board: dict[str, Any]) -> dict[str, bool]:
    readiness = {
        "coordination_metrics_read_surface_landed": True,
        "source_metrics_board_consumed": board["readiness"]["coordination_metrics_board_landed"],
        "track_cards_renderable": True,
        "success_metric_cards_renderable": True,
        "agent_success_rubric_renderable": True,
        "sticky_claim_footer_renderable": True,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _four_id_session_header(board: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof_anchor_id": board["proof_anchor_id"],
        "coordination_session_id": board["coordination_session_id"],
        "compact_decision_id": board["compact_decision_id"],
        "review_packet_id": board["review_packet_id"],
        "source_board_id": board["board_id"],
        "normal_handoff_rule": "handoff by IDs and reviewed board fields; do not reopen raw transcripts",
    }


def _integration_track_cards(board: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for track in board["integration_tracks"]:
        cards.append(
            {
                "track": track["track"],
                "current_state": track["current_state"],
                "success_metric": track["success_metric"],
                "authorization_flags": {
                    key: value
                    for key, value in track.items()
                    if key.startswith("authorizes_")
                },
                "render_policy": "operator_read_only_pass_through",
                "customer_visible": False,
            }
        )
    return cards


def _success_metric_cards(board: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric": card["metric"],
            "pass_condition": card["pass_condition"],
            "observed": card["observed"],
            "target": card["target"],
            "customer_visible": False,
            "render_policy": "score_context_not_live_dashboard",
        }
        for card in board["success_metric_cards"]
    ]


def _agent_success_rubric_cards(board: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = {card["metric"]: card for card in board["success_metric_cards"]}
    return [
        {
            "rubric": "claim_boundary_integrity",
            "source_metric": "claim_boundary_integrity",
            "success_condition": metrics["claim_boundary_integrity"]["pass_condition"],
            "observed": metrics["claim_boundary_integrity"]["observed"],
            "score_can_be_customer_visible": False,
        },
        {
            "rubric": "four_id_handoff_completeness",
            "source_metric": "four_id_handoff_completeness",
            "success_condition": metrics["four_id_handoff_completeness"]["pass_condition"],
            "observed": metrics["four_id_handoff_completeness"]["observed"],
            "score_can_be_customer_visible": False,
        },
        {
            "rubric": "acontext_prerequisite_honesty",
            "source_metric": "acontext_prerequisite_honesty",
            "success_condition": metrics["acontext_prerequisite_honesty"]["pass_condition"],
            "observed": metrics["acontext_prerequisite_honesty"]["observed"],
            "score_can_be_customer_visible": False,
        },
        {
            "rubric": "one_next_proof_discipline",
            "source_metric": "one_next_proof_discipline",
            "success_condition": metrics["one_next_proof_discipline"]["pass_condition"],
            "observed": metrics["one_next_proof_discipline"]["observed"],
            "score_can_be_customer_visible": False,
        },
    ]


def _claim_boundary_footer(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> dict[str, Any]:
    return {
        "footer_policy": "sticky_safe_and_blocked_claims_travel_together",
        "safe_to_claim_count": len(safe_to_claim),
        "do_not_claim_yet_count": len(do_not_claim_yet),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "blocked_claims_may_be_hidden": False,
    }


def _assert_source_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA:
        raise CityOpsContractError("unexpected coordination metrics board schema")
    if AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM not in board[
        "claim_boundaries"
    ]["safe_to_claim"]:
        raise CityOpsContractError("coordination metrics board safe claim missing")
    _assert_false_flags(board.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(board.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(board.get("readiness", {}), _FALSE_READINESS_FLAGS)
    _assert_no_claim_overlap(
        board["claim_boundaries"]["safe_to_claim"],
        board["claim_boundaries"]["do_not_claim_yet"],
    )
    for track in board.get("integration_tracks", []):
        for key, value in track.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("coordination metrics track promoted authorization")


def _assert_surface_conservative(surface: dict[str, Any], board: dict[str, Any]) -> None:
    if surface.get("schema") != AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("unexpected coordination metrics read surface schema")
    for key in [
        "proof_anchor_id",
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
    ]:
        if surface.get(key) != board.get(key):
            raise CityOpsContractError(f"coordination metrics read surface id drift: {key}")
    if surface.get("source_board_id") != board.get("board_id"):
        raise CityOpsContractError("coordination metrics read surface board id drift")
    _assert_false_flags(surface.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(surface.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(surface.get("readiness", {}), _FALSE_READINESS_FLAGS)
    if surface.get("render_contract", {}).get("network_route_registered") is not False:
        raise CityOpsContractError("coordination metrics read surface registered route")
    if surface.get("readiness", {}).get("coordination_metrics_read_surface_landed") is not True:
        raise CityOpsContractError("coordination metrics read surface not landed")
    _assert_claim_boundaries(
        surface["claim_boundaries"]["safe_to_claim"],
        surface["claim_boundaries"]["do_not_claim_yet"],
    )
    for card in surface.get("integration_track_cards", []):
        if card.get("customer_visible") is not False:
            raise CityOpsContractError("coordination metrics track card became customer visible")
        for value in card.get("authorization_flags", {}).values():
            if value is not False:
                raise CityOpsContractError("coordination metrics read surface promoted authorization")
    for card in surface.get("success_metric_cards", []):
        if card.get("customer_visible") is not False:
            raise CityOpsContractError("coordination metrics metric card became customer visible")
    for card in surface.get("agent_success_rubric_cards", []):
        if card.get("score_can_be_customer_visible") is not False:
            raise CityOpsContractError("coordination metrics rubric became customer visible")


def _assert_false_flags(payload: dict[str, Any], flags: list[str]) -> None:
    for flag in flags:
        if flag in payload and payload[flag] is not False:
            raise CityOpsContractError(f"promoted forbidden flag: {flag}")


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"coordination metrics read surface claim overlap: {sorted(overlap)}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"coordination metrics read surface claim overlap: {sorted(overlap)}")
    missing = set(READ_SURFACE_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"coordination metrics read surface missing blocked claims: {sorted(missing)}"
        )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
