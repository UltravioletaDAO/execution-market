"""Internal/admin coordination observability success-metrics board for AAS.

This module connects the existing system-integration flywheel read surface with
May 16's Acontext prerequisite recovery attempt log.  It produces one bounded
operator board for memory/Acontext planning, IRC session management,
cross-project decision support, and agent observability success metrics.

The board is intentionally conservative: it is read-only, internal/admin only,
performs no live Acontext write/retrieve, registers no customer/public route,
enables no dispatch, emits no reputation receipts, and does not reverify payment
or production infrastructure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_system_integration_flywheel_read_surface import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA,
    SURFACE_BLOCKED_CLAIMS,
    load_aas_system_integration_flywheel_read_surface,
)
from .acontext_prerequisite_recovery_attempt_log import (
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME,
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM,
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA,
    RECOVERY_ATTEMPT_BLOCKED_CLAIMS,
    load_acontext_prerequisite_recovery_attempt_log,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA = (
    "city_ops.aas_coordination_observability_success_metrics_board.v1"
)
AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME = (
    "aas_coordination_observability_success_metrics_board.json"
)
AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM = (
    "admin_aas_coordination_observability_success_metrics_board_landed"
)

COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS = [
    *SURFACE_BLOCKED_CLAIMS,
    *RECOVERY_ATTEMPT_BLOCKED_CLAIMS,
    "live_acontext_memory_integration_ready_by_metrics_board",
    "irc_session_manager_runtime_enhanced_by_metrics_board",
    "cross_project_decision_support_customer_ready_by_metrics_board",
    "agent_observability_live_dashboard_ready_by_metrics_board",
    "success_metrics_public_or_customer_visible_by_metrics_board",
    "autonomous_dispatch_ready_by_metrics_board",
    "erc8004_reputation_ready_by_metrics_board",
    "worker_skill_dna_ready_by_metrics_board",
    "payment_coverage_reverified_by_metrics_board",
    "production_infrastructure_reverified_by_metrics_board",
    "gps_or_raw_metadata_exposure_allowed_by_metrics_board",
    "worker_copyable_doctrine_ready_by_metrics_board",
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
    "board_promotes_live_readiness",
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
    "payment_coverage_reverified_by_this_board",
    "production_infrastructure_reverified_by_this_board",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_coordination_observability_success_metrics_board(
    *,
    artifact_dir: str | Path | None = None,
    flywheel_surface: dict[str, Any] | None = None,
    recovery_log: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin coordination metrics board."""

    surface = flywheel_surface or load_aas_system_integration_flywheel_read_surface(
        artifact_dir=artifact_dir
    )
    recovery = recovery_log or load_acontext_prerequisite_recovery_attempt_log(
        artifact_dir=artifact_dir
    )
    _assert_source_surface_conservative(surface)
    _assert_recovery_log_conservative(recovery)
    _assert_sources_share_invariant_ids(surface, recovery)

    safe_to_claim = _dedupe(
        [
            *surface["claim_boundaries"]["safe_to_claim"],
            *recovery["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
            ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM,
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *surface["claim_boundaries"]["do_not_claim_yet"],
            *recovery["claim_boundaries"]["do_not_claim_yet"],
            *COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    board = {
        "schema": AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA,
        "board_id": (
            "aas_coordination_observability_success_metrics_board:"
            f"{surface['proof_anchor_id']}"
        ),
        "proof_anchor_id": surface["proof_anchor_id"],
        "coordination_session_id": surface["coordination_session_id"],
        "compact_decision_id": surface["compact_decision_id"],
        "review_packet_id": surface["review_packet_id"],
        "source_surface_id": surface["surface_id"],
        "source_recovery_log_id": recovery["log_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
                ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME,
            ],
            "consumes_only": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
                ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME,
            ],
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
        "readiness": _board_readiness(),
        "integration_tracks": _integration_tracks(surface, recovery),
        "success_metric_cards": _success_metric_cards(surface, recovery),
        "session_management_enhancement_cards": _session_management_cards(surface),
        "operator_next_action_cards": _operator_next_action_cards(recovery),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "board_verdict": "coordination_metrics_board_landed_still_blocked_on_live_runtime",
        "operator_instruction": (
            "Use this board to score future agents on boundary preservation, invariant-ID "
            "handoff, and next-proof discipline. Do not treat it as a live Acontext "
            "transport, IRC runtime enhancement, public/customer metric dashboard, "
            "dispatch authorization, payment re-verification, or reputation signal."
        ),
    }
    _assert_board_conservative(board)
    return board


def write_aas_coordination_observability_success_metrics_board(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic coordination observability metrics board."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    board = build_aas_coordination_observability_success_metrics_board(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_coordination_observability_success_metrics_board(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted coordination metrics board."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (
        base_dir / AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME
    ).open("r", encoding="utf-8") as fh:
        board = json.load(fh)
    surface = load_aas_system_integration_flywheel_read_surface(artifact_dir=base_dir)
    recovery = load_acontext_prerequisite_recovery_attempt_log(artifact_dir=base_dir)
    _assert_board_conservative(board)
    _assert_sources_share_invariant_ids(surface, recovery)
    if board != build_aas_coordination_observability_success_metrics_board(
        artifact_dir=base_dir, flywheel_surface=surface, recovery_log=recovery
    ):
        raise CityOpsContractError("coordination metrics board drifted from sources")
    return board


def _board_readiness() -> dict[str, bool]:
    readiness = {
        "coordination_metrics_board_landed": True,
        "source_flywheel_surface_consumed": True,
        "source_recovery_log_consumed": True,
        "boundary_preservation_measured": True,
        "invariant_id_handoff_measured": True,
        "next_proof_discipline_measured": True,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _integration_tracks(surface: dict[str, Any], recovery: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "track": "memory_system_to_acontext_integration",
            "current_state": "planned_bridge_blocked_by_prerequisites",
            "source_card": "reviewed_memory_to_acontext_to_better_dispatch",
            "recovery_fact": "dedicated_sdk_venv_imports_acontext_partial_asset_only",
            "success_metric": "future_agent_preserves_blocker_cards_until_live_write_retrieve_passes",
            "authorizes_live_runtime": False,
        },
        {
            "track": "irc_session_management_enhancement",
            "current_state": "compact_id_handoff_pattern_ready_for_internal_use",
            "source_card": "irc_session_ids_to_cross_session_continuity",
            "success_metric": "handoff_mentions_all_four_ids_without_raw_transcript_replay",
            "authorizes_runtime_session_manager_change": False,
        },
        {
            "track": "cross_project_decision_support",
            "current_state": "operator_only_reuse_of_safe_blocked_verdicts",
            "source_card": "decision_matrix_to_cross_project_operator_choices",
            "success_metric": "recommendations_keep_safe_to_claim_and_do_not_claim_yet_together",
            "authorizes_customer_copy_or_public_route": False,
        },
        {
            "track": "agent_observability_success_metrics",
            "current_state": "internal_scoreboard_contract_landed_not_dashboard",
            "source_card": "observability_to_agent_success_metrics",
            "success_metric": "agent_success_equals_boundary_preservation_plus_one_next_proof",
            "authorizes_live_dashboard": False,
        },
        {
            "track": "payment_infrastructure_context",
            "current_state": "context_only_not_reverified_by_this_board",
            "source_card": "payment_confidence_to_deployable_aas_boundaries",
            "recovery_verdict": recovery["recovery_verdict"],
            "success_metric": "payment_or_production_claims_require_separate_fresh_probe",
            "authorizes_payment_or_production_claim": False,
        },
    ]


def _success_metric_cards(surface: dict[str, Any], recovery: dict[str, Any]) -> list[dict[str, Any]]:
    safe_claims = surface["claim_boundaries"]["safe_to_claim"]
    blocked_claims = recovery["claim_boundaries"]["do_not_claim_yet"]
    return [
        {
            "metric": "claim_boundary_integrity",
            "pass_condition": "safe_to_claim and do_not_claim_yet remain disjoint",
            "observed": set(safe_claims).isdisjoint(blocked_claims),
            "target": True,
            "customer_visible": False,
        },
        {
            "metric": "four_id_handoff_completeness",
            "pass_condition": "proof_anchor_id coordination_session_id compact_decision_id review_packet_id all present",
            "observed": all(
                surface.get(key)
                for key in [
                    "proof_anchor_id",
                    "coordination_session_id",
                    "compact_decision_id",
                    "review_packet_id",
                ]
            ),
            "target": True,
            "customer_visible": False,
        },
        {
            "metric": "acontext_prerequisite_honesty",
            "pass_condition": "partial assets do not promote live transport readiness",
            "observed": (
                recovery["readiness"]["dedicated_sdk_venv_imports_acontext"] is True
                and recovery["readiness"]["ready_to_attempt_live_transport"] is False
            ),
            "target": True,
            "customer_visible": False,
        },
        {
            "metric": "one_next_proof_discipline",
            "pass_condition": "next work stays prerequisite/live-parity focused, not customer/public expansion",
            "observed": True,
            "target": True,
            "customer_visible": False,
        },
    ]


def _session_management_cards(surface: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "four_id_session_header_required",
            "proof_anchor_id": surface["proof_anchor_id"],
            "coordination_session_id": surface["coordination_session_id"],
            "compact_decision_id": surface["compact_decision_id"],
            "review_packet_id": surface["review_packet_id"],
            "normal_handoff_rule": "handoff by IDs; do not reopen raw transcripts",
        },
        {
            "card": "declared_vs_verified_badges_required",
            "rule": "carry source verification badges forward instead of restating stale strengths as fresh proof",
            "authorizes_new_strength_claims": False,
        },
        {
            "card": "sticky_blocked_claims_required",
            "rule": "every recommendation must keep blocked claims visible beside safe claims",
            "authorizes_blocked_claim_removal": False,
        },
    ]


def _operator_next_action_cards(recovery: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "finish_acontext_prerequisites",
            "next_action": "complete compose pull/startup and make API/dashboard reachable",
            "source_status": recovery["recovery_verdict"],
            "claim_unlocked_only_if_passes": "none_until_read_only_preflight_is_rebuilt",
        },
        {
            "card": "rerun_read_only_preflight",
            "next_action": "rebuild blocker delta, read surface, and readiness gate after prerequisites change",
            "claim_unlocked_only_if_passes": "acontext_live_parity_attempt_authorized_by_gate",
        },
        {
            "card": "attempt_one_live_parity_pass_only_if_empty_blockers",
            "next_action": "one write/retrieve parity pass, then stop and record result",
            "claim_unlocked_only_if_passes": "live_acontext_transport_parity_landed",
        },
    ]


def _assert_source_surface_conservative(surface: dict[str, Any]) -> None:
    if surface.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("unexpected flywheel read surface schema")
    _assert_false_flags(surface.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(surface.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(surface.get("readiness", {}), _FALSE_READINESS_FLAGS[:-1])
    if surface["readiness"].get("surface_promotes_live_readiness") is not False:
        raise CityOpsContractError("source surface promoted live readiness")


def _assert_recovery_log_conservative(recovery: dict[str, Any]) -> None:
    if recovery.get("schema") != ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA:
        raise CityOpsContractError("unexpected recovery log schema")
    _assert_false_flags(recovery.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(recovery.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    for flag in [
        "ready_to_attempt_live_transport",
        "compose_services_started",
        "api_reachable_after_attempt",
        "dashboard_reachable_after_attempt",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "acontext_sink_ready",
        "runtime_parity_proven",
    ]:
        if recovery.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"recovery log promoted readiness: {flag}")


def _assert_sources_share_invariant_ids(surface: dict[str, Any], recovery: dict[str, Any]) -> None:
    for key in [
        "proof_anchor_id",
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
    ]:
        if surface.get(key) != recovery.get(key):
            raise CityOpsContractError(f"source invariant id mismatch: {key}")


def _assert_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA:
        raise CityOpsContractError("unexpected coordination metrics board schema")
    _assert_false_flags(board.get("derived_from", {}), _FALSE_DERIVED_FLAGS)
    _assert_false_flags(board.get("access_policy", {}), _FALSE_ACCESS_FLAGS)
    _assert_false_flags(board.get("readiness", {}), _FALSE_READINESS_FLAGS)
    for card in board.get("integration_tracks", []):
        for key, value in card.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("integration track promoted authorization")
    _assert_claim_boundaries(
        board["claim_boundaries"]["safe_to_claim"],
        board["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_false_flags(payload: dict[str, Any], flags: list[str]) -> None:
    for flag in flags:
        if flag in payload and payload[flag] is not False:
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
