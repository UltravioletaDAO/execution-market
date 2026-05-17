"""Runtime-memory blocker decision board for City-as-a-Service AAS.

This module turns the latest Acontext Docker pull-path diagnostic into a
bounded internal/admin decision board.  It connects the runtime blocker back to
memory/Acontext integration planning, IRC/session handoff discipline,
cross-project decision support, and agent observability metrics without claiming
that live runtime, dispatch, customer packaging, reputation, payment, or
production infrastructure readiness has advanced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
    COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    load_aas_coordination_observability_success_metrics_board,
)
from .acontext_docker_pull_path_diagnostic import (
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME,
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM,
    DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS,
    load_acontext_docker_pull_path_diagnostic,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SCHEMA = (
    "city_ops.aas_runtime_memory_blocker_decision_board.v1"
)
AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_FILENAME = (
    "aas_runtime_memory_blocker_decision_board.json"
)
AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SAFE_CLAIM = (
    "admin_aas_runtime_memory_blocker_decision_board_landed"
)

RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_BLOCKED_CLAIMS = [
    *DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS,
    *COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    "docker_layer_fetch_blocker_resolved_by_runtime_memory_board",
    "trusted_image_cache_selected_by_runtime_memory_board",
    "all_acontext_images_present_by_runtime_memory_board",
    "compose_services_started_by_runtime_memory_board",
    "acontext_api_reachable_by_runtime_memory_board",
    "acontext_dashboard_reachable_by_runtime_memory_board",
    "live_acontext_write_completed_by_runtime_memory_board",
    "live_acontext_retrieval_completed_by_runtime_memory_board",
    "runtime_parity_proven_by_runtime_memory_board",
    "memory_system_acontext_integration_ready_by_runtime_memory_board",
    "irc_session_manager_runtime_changed_by_runtime_memory_board",
    "cross_project_decision_support_customer_ready_by_runtime_memory_board",
    "agent_observability_live_dashboard_ready_by_runtime_memory_board",
    "autonomous_dispatch_ready_by_runtime_memory_board",
    "customer_visible_aas_packaging_ready_by_runtime_memory_board",
    "public_route_ready_by_runtime_memory_board",
    "operator_queue_launch_ready_by_runtime_memory_board",
    "erc8004_reputation_ready_by_runtime_memory_board",
    "payment_or_production_reverified_by_runtime_memory_board",
    "gps_or_raw_metadata_release_allowed_by_runtime_memory_board",
    "worker_copyable_doctrine_ready_by_runtime_memory_board",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "starts_compose_services",
    "writes_municipal_memory",
    "writes_customer_copy",
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
    "dispatch_enabled",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "starts_compose_services",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "docker_layer_fetch_blocker_resolved",
    "trusted_image_cache_selected",
    "all_required_images_present",
    "compose_services_started",
    "acontext_api_reachable",
    "acontext_dashboard_reachable",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "memory_system_acontext_integration_ready",
    "irc_session_manager_runtime_changed",
    "cross_project_decision_support_customer_ready",
    "agent_observability_live_dashboard_ready",
    "autonomous_dispatch_ready",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_board",
    "production_infrastructure_reverified_by_this_board",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_aas_runtime_memory_blocker_decision_board(
    *,
    artifact_dir: str | Path | None = None,
    docker_diagnostic: dict[str, Any] | None = None,
    metrics_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative runtime-memory blocker decision board."""

    diagnostic = docker_diagnostic or load_acontext_docker_pull_path_diagnostic(
        artifact_dir=artifact_dir
    )
    metrics = metrics_board or load_aas_coordination_observability_success_metrics_board(
        artifact_dir=artifact_dir
    )
    _assert_docker_diagnostic_still_blocked(diagnostic)
    _assert_metrics_board_conservative(metrics)
    _assert_sources_share_invariant_ids(diagnostic, metrics)

    safe_to_claim = _dedupe(
        [
            *metrics["claim_boundaries"]["safe_to_claim"],
            *diagnostic["claim_boundaries"]["safe_to_claim"],
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
            ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM,
            AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *metrics["claim_boundaries"]["do_not_claim_yet"],
            *diagnostic["claim_boundaries"]["do_not_claim_yet"],
            *RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    board = {
        "schema": AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SCHEMA,
        "board_id": f"aas_runtime_memory_blocker_decision_board:{diagnostic['proof_anchor_id']}",
        "proof_anchor_id": diagnostic["proof_anchor_id"],
        "coordination_session_id": diagnostic["coordination_session_id"],
        "compact_decision_id": diagnostic["compact_decision_id"],
        "review_packet_id": diagnostic["review_packet_id"],
        "packet_id": diagnostic["packet_id"],
        "source_diagnostic_id": diagnostic["diagnostic_id"],
        "source_metrics_board_id": metrics["board_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME,
                AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
            ],
            "forbidden_inputs": [
                "raw_transcripts",
                "unreviewed_memory",
                "private_operator_context",
                "registry_tokens_or_credentials",
                "raw_docker_logs",
                "live_acontext_sink_writes",
                "live_acontext_retrievals",
                "payment_processor_probe",
                "production_health_probe",
                "gps_or_raw_metadata_payloads",
                "customer_copy_drafts",
                "worker_instruction_templates",
            ],
            **{flag: False for flag in _FALSE_DERIVED_FLAGS},
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **{flag: False for flag in _FALSE_ACCESS_FLAGS},
        },
        "readiness": _readiness(diagnostic),
        "blocker_summary": _blocker_summary(diagnostic),
        "resolution_decision_tree": _resolution_decision_tree(diagnostic),
        "session_management_enhancement_cards": _session_management_cards(diagnostic),
        "cross_project_decision_support_cards": _decision_support_cards(diagnostic),
        "agent_success_metric_cards": _agent_success_metric_cards(diagnostic, metrics),
        "operator_next_actions": _operator_next_actions(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "board_verdict": "runtime_memory_blocker_board_landed_docker_pull_still_blocks_live_acontext",
        "operator_instruction": (
            "Use this board as the daytime pickup ticket for the Acontext runtime-memory "
            "blocker. Fix or bypass the Docker layer-fetch path first, then prove local "
            "image inventory, compose health, API/dashboard health, and exactly one "
            "write/retrieve parity pass before promoting any live memory, session-manager, "
            "customer, dispatch, reputation, payment, production, GPS, or worker-doctrine claim."
        ),
    }
    _assert_board_conservative(board)
    return board


def write_aas_runtime_memory_blocker_decision_board(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic runtime-memory blocker decision board."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    board = build_aas_runtime_memory_blocker_decision_board(artifact_dir=base_dir)
    path = base_dir / AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_runtime_memory_blocker_decision_board(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted runtime-memory blocker decision board."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        board = json.load(fh)
    _assert_board_conservative(board)
    return board


def _readiness(diagnostic: dict[str, Any]) -> dict[str, Any]:
    inventory = diagnostic["image_inventory"]
    retry = diagnostic["explicit_platform_retry_summary"]
    return {
        "runtime_memory_blocker_board_landed": True,
        "docker_context_available": bool(
            diagnostic["docker_context_summary"].get("docker_context_available")
        ),
        "docker_pull_path_blocker_confirmed": bool(
            retry.get("explicit_platform_retry_blocker_remains")
        ),
        "explicit_platform_pull_still_stalls": bool(retry.get("timed_out_without_output")),
        "missing_required_image_count": inventory["missing_required_image_count"],
        "decision_support_next_action_ranked": True,
        "session_handoff_enhancement_planned": True,
        "claim_boundary_preservation_ready": True,
        **{flag: False for flag in _FALSE_READINESS_FLAGS},
    }


def _blocker_summary(diagnostic: dict[str, Any]) -> dict[str, Any]:
    inventory = diagnostic["image_inventory"]
    retry = diagnostic["explicit_platform_retry_summary"]
    return {
        "primary_blocker": "docker_layer_fetch_stalls_before_first_acontext_image",
        "evidence": [
            "docker_context_available",
            "buildx_advertises_linux_arm64",
            "explicit_linux_arm64_pull_timed_out_without_output",
            "first_ghcr_acontext_image_not_present_after_retry",
            "required_acontext_images_missing",
        ],
        "first_image": retry["image"],
        "first_image_platform": retry["platform"],
        "missing_required_images": inventory["missing_required_images"],
        "recommended_resolution_class": "fix_docker_layer_fetch_or_use_trusted_prepopulated_image_cache_before_compose",
        "must_not_do_next": [
            "start_compose_before_required_image_inventory_is_complete",
            "declare_acontext_runtime_ready_from_manifest_availability_only",
            "write_or_retrieve_live_acontext_memory_before_healthchecks_and_empty_gate",
        ],
    }


def _resolution_decision_tree(diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    missing_count = diagnostic["image_inventory"]["missing_required_image_count"]
    return [
        {
            "rank": 1,
            "option": "repair_docker_desktop_containerd_or_network_layer_fetch",
            "why_first": "current context and buildx are alive, so the remaining fault is below compose and before service health",
            "success_gate": "first GHCR image pulls or is locally present without timeout, then all required image inventory passes",
            "authorizes_live_runtime": False,
            "blocked_until": [
                "all_required_images_present",
                "compose_services_started",
                "api_and_dashboard_healthchecks_pass",
                "live_write_retrieve_parity_passes",
            ],
        },
        {
            "rank": 2,
            "option": "use_trusted_prepopulated_image_cache_or_mirror",
            "why_second": "bypasses local layer-fetch stall without changing Acontext semantics if image provenance is trusted",
            "success_gate": f"all {missing_count} currently missing required images become present from trusted source",
            "authorizes_live_runtime": False,
            "blocked_until": [
                "image_provenance_reviewed",
                "all_required_images_present",
                "compose_services_started",
                "api_and_dashboard_healthchecks_pass",
                "live_write_retrieve_parity_passes",
            ],
        },
        {
            "rank": 3,
            "option": "defer_live_runtime_and_continue_fixture_backed_handoffs",
            "why_third": "keeps coordination, decision support, and observability moving without inventing memory readiness",
            "success_gate": "future agents preserve invariant IDs and blocked claims while blocker remains unresolved",
            "authorizes_live_runtime": False,
            "blocked_until": [
                "docker_or_cache_path_fixed",
                "runtime_health_and_parity_proven",
            ],
        },
        {
            "rank": 4,
            "option": "replace_acontext_runtime_for_pilot",
            "why_last": "requires a separate architecture decision because it changes the memory substrate under test",
            "success_gate": "new substrate has explicit contract, fixture parity, live write/retrieve parity, and migration risk review",
            "authorizes_live_runtime": False,
            "blocked_until": [
                "architecture_decision_record_approved",
                "equivalent_retrieval_contract_proven",
                "live_write_retrieve_parity_passes",
            ],
        },
    ]


def _session_management_cards(diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "four_id_pickup_ticket",
            "purpose": "let IRC/session agents resume without raw transcript replay",
            "ids": {
                "proof_anchor_id": diagnostic["proof_anchor_id"],
                "coordination_session_id": diagnostic["coordination_session_id"],
                "compact_decision_id": diagnostic["compact_decision_id"],
                "review_packet_id": diagnostic["review_packet_id"],
            },
            "runtime_session_manager_changed": False,
        },
        {
            "card": "blocker_state_event",
            "purpose": "emit one compact state transition into future coordination logs",
            "event_name": "city_acontext_runtime_blocker_confirmed",
            "payload_shape": [
                "proof_anchor_id",
                "source_diagnostic_id",
                "primary_blocker",
                "missing_required_image_count",
                "next_safe_action",
            ],
            "runtime_session_manager_changed": False,
        },
        {
            "card": "no_raw_context_reopen_rule",
            "purpose": "make future agents consume artifact IDs and claim boundaries instead of private transcript memory",
            "reads_raw_transcripts": False,
            "reads_unreviewed_memory": False,
            "runtime_session_manager_changed": False,
        },
    ]


def _decision_support_cards(diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "next_action_selector",
            "decision": "fix_or_bypass_docker_layer_fetch_before_any_compose_start",
            "source_evidence": diagnostic["diagnostic_id"],
            "customer_visible": False,
        },
        {
            "card": "claim_boundary_gate",
            "decision": "carry safe_to_claim and do_not_claim_yet together in every downstream handoff",
            "source_evidence": diagnostic["diagnostic_id"],
            "customer_visible": False,
        },
        {
            "card": "runtime_promotion_gate",
            "decision": "only promote after inventory, compose, healthcheck, empty readiness gate, and live parity all pass",
            "source_evidence": diagnostic["diagnostic_id"],
            "customer_visible": False,
        },
    ]


def _agent_success_metric_cards(
    diagnostic: dict[str, Any], metrics_board: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "metric": "claim_boundary_integrity",
            "observed": True,
            "target": "safe and blocked claims remain disjoint across diagnostic and metrics board",
            "customer_visible": False,
        },
        {
            "metric": "four_id_handoff_completeness",
            "observed": True,
            "target": "proof, coordination session, compact decision, and review packet IDs are preserved",
            "customer_visible": False,
        },
        {
            "metric": "docker_inventory_gate",
            "observed": False,
            "target": "all required Acontext images are locally present before compose",
            "current_missing_required_image_count": diagnostic["image_inventory"][
                "missing_required_image_count"
            ],
            "customer_visible": False,
        },
        {
            "metric": "live_runtime_parity_gate",
            "observed": False,
            "target": "one write/retrieve parity pass after healthchecks and empty readiness gate",
            "customer_visible": False,
        },
        {
            "metric": "coordination_metrics_board_continuity",
            "observed": metrics_board["readiness"]["coordination_metrics_board_landed"],
            "target": "operator metrics continue to guide agents without becoming a live dashboard claim",
            "customer_visible": False,
        },
    ]


def _operator_next_actions() -> list[dict[str, Any]]:
    return [
        {
            "order": 1,
            "action": "diagnose Docker Desktop/containerd/network layer-fetch stall outside customer/runtime paths",
            "done_when": "first GHCR Acontext image can be pulled or trusted-cache-loaded without timeout",
        },
        {
            "order": 2,
            "action": "verify all required Acontext images are present locally from trusted provenance",
            "done_when": "image inventory reports zero missing required images",
        },
        {
            "order": 3,
            "action": "start compose only after image inventory passes",
            "done_when": "Acontext API and dashboard healthchecks pass locally",
        },
        {
            "order": 4,
            "action": "rerun read-only preflight and rebuild the readiness gate",
            "done_when": "gate blockers are empty without suppressing claim boundaries",
        },
        {
            "order": 5,
            "action": "attempt exactly one live write/retrieve parity pass",
            "done_when": "write and retrieval match the reviewed fixture contract without raw transcript or unreviewed memory input",
        },
    ]


def _assert_docker_diagnostic_still_blocked(diagnostic: dict[str, Any]) -> None:
    if diagnostic.get("schema") != "city_ops.acontext_docker_pull_path_diagnostic.v1":
        raise CityOpsContractError("unexpected Docker diagnostic schema")
    readiness = diagnostic.get("readiness", {})
    for flag in [
        "first_required_image_pulled",
        "all_required_images_present",
        "compose_services_started",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "acontext_sink_ready",
        "runtime_parity_proven",
    ]:
        if readiness.get(flag):
            raise CityOpsContractError(f"Docker diagnostic promoted readiness: {flag}")
    retry = diagnostic.get("explicit_platform_retry_summary", {})
    if not retry.get("explicit_platform_retry_blocker_remains"):
        raise CityOpsContractError("Docker diagnostic no longer records pull blocker")
    if diagnostic.get("image_inventory", {}).get("all_required_images_present"):
        raise CityOpsContractError("Docker diagnostic image inventory is no longer blocked")


def _assert_metrics_board_conservative(metrics: dict[str, Any]) -> None:
    if metrics.get("schema") != "city_ops.aas_coordination_observability_success_metrics_board.v1":
        raise CityOpsContractError("unexpected coordination metrics board schema")
    readiness = metrics.get("readiness", {})
    for flag in [
        "live_acontext_memory_integration_ready",
        "agent_observability_live_dashboard_ready",
        "customer_visible_packaging_ready",
        "public_route_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
    ]:
        if readiness.get(flag):
            raise CityOpsContractError(f"metrics board promoted readiness: {flag}")


def _assert_sources_share_invariant_ids(
    diagnostic: dict[str, Any], metrics: dict[str, Any]
) -> None:
    for key in ["proof_anchor_id", "coordination_session_id", "compact_decision_id", "review_packet_id"]:
        if diagnostic.get(key) != metrics.get(key):
            raise CityOpsContractError(f"source invariant id mismatch: {key}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"blocked claims marked safe: {overlap}")


def _assert_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_SCHEMA:
        raise CityOpsContractError("unexpected runtime-memory blocker board schema")
    for section, flags in [
        ("derived_from", _FALSE_DERIVED_FLAGS),
        ("access_policy", _FALSE_ACCESS_FLAGS),
        ("readiness", _FALSE_READINESS_FLAGS),
    ]:
        values = board.get(section, {})
        for flag in flags:
            if values.get(flag) is not False:
                raise CityOpsContractError(f"runtime-memory blocker board promoted forbidden flag: {section}.{flag}")
    readiness = board.get("readiness", {})
    if not readiness.get("docker_pull_path_blocker_confirmed"):
        raise CityOpsContractError("runtime-memory blocker board lost blocker confirmation")
    _assert_claim_boundaries(
        board.get("claim_boundaries", {}).get("safe_to_claim", []),
        board.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
