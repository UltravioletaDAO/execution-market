"""Acontext prerequisite recovery attempt log for City-as-a-Service.

This module records the 1 AM recovery attempt after the prerequisite activation
board: Docker is available and the dedicated SDK venv imports Acontext, but the
active runner still lacks the SDK and the compose startup did not complete into
reachable API/dashboard services.  The log is deliberately fail-closed: it is an
internal/admin proof-support artifact, not a live transport runner.

It never writes to Acontext, never retrieves from Acontext, never starts a
customer/public route, and never promotes runtime, dispatch, reputation,
payment, production, GPS/raw metadata, or worker-doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_prerequisite_activation_board import (
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM,
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA,
    ACTIVATION_BOARD_BLOCKED_CLAIMS,
    load_acontext_prerequisite_activation_board,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA = (
    "city_ops.acontext_prerequisite_recovery_attempt_log.v1"
)
ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME = (
    "acontext_prerequisite_recovery_attempt_log.json"
)
ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM = (
    "admin_acontext_prerequisite_recovery_attempt_log_landed"
)

RECOVERY_ATTEMPT_BLOCKED_CLAIMS = [
    *ACTIVATION_BOARD_BLOCKED_CLAIMS,
    "acontext_compose_pull_completed_by_recovery_attempt",
    "acontext_services_started_by_recovery_attempt",
    "acontext_api_dashboard_reachable_by_recovery_attempt",
    "active_runner_sdk_wired_by_recovery_attempt",
    "acontext_preflight_rerun_authorized_by_recovery_attempt",
    "acontext_live_parity_attempt_authorized_by_recovery_attempt",
    "acontext_live_write_completed_by_recovery_attempt",
    "acontext_live_retrieval_completed_by_recovery_attempt",
    "acontext_sink_ready_by_recovery_attempt",
    "runtime_parity_proven_by_recovery_attempt",
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
    "ready_to_attempt_live_transport",
    "attempt_allowed",
    "all_prerequisites_cleared",
    "compose_pull_completed",
    "compose_services_started",
    "api_reachable_after_attempt",
    "dashboard_reachable_after_attempt",
    "active_runner_sdk_available",
    "preflight_rerun_completed",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "live_memory_transport_swap_ready",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_log",
    "production_infrastructure_reverified_by_this_log",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may16_1am_recovery_attempt_observation() -> dict[str, Any]:
    """Return the deterministic 1 AM observed recovery-attempt shape."""

    return {
        "attempt_window": "2026-05-16T01:00:00-04:00",
        "docker_available": True,
        "acontext_cli_installed": True,
        "compose_manifest_found": True,
        "compose_env_file_found": True,
        "dedicated_sdk_venv_found": True,
        "dedicated_sdk_venv_imports_acontext": True,
        "dedicated_sdk_venv_acontext_version": "0.1.13",
        "active_runner_sdk_available": False,
        "active_runner_sdk_blocker": "active_homebrew_python_has_no_acontext_module",
        "compose_up_attempted": True,
        "compose_up_command": (
            "docker compose --env-file .env -f .docker-compose-1411407133.yaml up -d"
        ),
        "compose_pull_started": True,
        "compose_pull_completed": False,
        "compose_up_completed": False,
        "compose_attempt_stopped_by_operator": True,
        "compose_attempt_stop_reason": "silent_multi_image_pull_exceeded_cron_window",
        "compose_services_started": False,
        "local_acontext_api_reachable": False,
        "local_acontext_dashboard_reachable": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_prerequisite_recovery_attempt_log(
    *,
    artifact_dir: str | Path | None = None,
    activation_board: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed log for the Acontext prerequisite recovery attempt."""

    source_board = activation_board or load_acontext_prerequisite_activation_board(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may16_1am_recovery_attempt_observation()
    _assert_source_activation_board(source_board)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source_board["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM,
            ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_board["claim_boundaries"]["do_not_claim_yet"],
            *RECOVERY_ATTEMPT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    log = {
        "schema": ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA,
        "log_id": f"acontext_prerequisite_recovery_attempt_log:{source_board['board_id']}",
        "source_board_id": source_board["board_id"],
        "source_gate_id": source_board["source_gate_id"],
        "source_delta_id": source_board["source_delta_id"],
        "source_preflight_id": source_board["source_preflight_id"],
        "proof_anchor_id": source_board["proof_anchor_id"],
        "coordination_session_id": source_board["coordination_session_id"],
        "compact_decision_id": source_board["compact_decision_id"],
        "review_packet_id": source_board["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME],
            "consumes_only": [ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME],
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
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "starts_customer_or_public_services": False,
            "semantic_reinterpretation_performed": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "writes_customer_copy": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
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
        "recovery_observation": dict(observed),
        "recovery_cards": _recovery_cards(observed),
        "readiness": _recovery_readiness(observed),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_next_actions": _operator_next_actions(observed),
        "recovery_verdict": _recovery_verdict(observed),
        "operator_instruction": (
            "Treat this as an attempted prerequisite recovery log only. Do not rerun "
            "live parity until image pulls complete, compose services are healthy, the "
            "active runner can import Acontext, and the read-only preflight is rebuilt "
            "with empty blockers."
        ),
    }
    _assert_log_conservative(log)
    return log


def write_acontext_prerequisite_recovery_attempt_log(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext prerequisite recovery attempt log."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    log = build_acontext_prerequisite_recovery_attempt_log(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME
    path.write_text(json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_prerequisite_recovery_attempt_log(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted recovery attempt log."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        log = json.load(fh)
    _assert_log_conservative(log)
    return log


def _recovery_cards(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card_id": "local_assets_rechecked",
            "status": "partial_assets_present",
            "docker_available": bool(observed.get("docker_available")),
            "acontext_cli_installed": bool(observed.get("acontext_cli_installed")),
            "compose_manifest_found": bool(observed.get("compose_manifest_found")),
            "compose_env_file_found": bool(observed.get("compose_env_file_found")),
            "dedicated_sdk_venv_imports_acontext": bool(
                observed.get("dedicated_sdk_venv_imports_acontext")
            ),
            "active_runner_sdk_available": bool(
                observed.get("active_runner_sdk_available")
            ),
            "authorizes_live_attempt": False,
        },
        {
            "card_id": "compose_recovery_attempt",
            "status": "attempted_not_completed",
            "compose_up_attempted": bool(observed.get("compose_up_attempted")),
            "compose_pull_started": bool(observed.get("compose_pull_started")),
            "compose_pull_completed": bool(observed.get("compose_pull_completed")),
            "compose_services_started": bool(observed.get("compose_services_started")),
            "stop_reason": observed.get("compose_attempt_stop_reason"),
            "authorizes_api_dashboard_claim": False,
        },
        {
            "card_id": "post_attempt_reachability",
            "status": "still_unreachable",
            "local_acontext_api_reachable": bool(
                observed.get("local_acontext_api_reachable")
            ),
            "local_acontext_dashboard_reachable": bool(
                observed.get("local_acontext_dashboard_reachable")
            ),
            "live_acontext_write_performed": bool(
                observed.get("live_acontext_write_performed")
            ),
            "live_acontext_retrieval_performed": bool(
                observed.get("live_acontext_retrieval_performed")
            ),
            "authorizes_runtime_parity_claim": False,
        },
    ]


def _recovery_readiness(observed: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    if not observed.get("active_runner_sdk_available"):
        blockers.append("active_runner_acontext_sdk_missing")
    if not observed.get("compose_pull_completed"):
        blockers.append("compose_image_pull_not_completed")
    if not observed.get("compose_services_started"):
        blockers.append("acontext_compose_services_not_started")
    if not observed.get("local_acontext_api_reachable"):
        blockers.append("local_acontext_api_unreachable")
    if not observed.get("local_acontext_dashboard_reachable"):
        blockers.append("local_acontext_dashboard_unreachable")

    readiness: dict[str, Any] = {
        "recovery_attempt_log_landed": True,
        "docker_available": bool(observed.get("docker_available")),
        "acontext_cli_installed": bool(observed.get("acontext_cli_installed")),
        "compose_manifest_found": bool(observed.get("compose_manifest_found")),
        "compose_env_file_found": bool(observed.get("compose_env_file_found")),
        "dedicated_sdk_venv_found": bool(observed.get("dedicated_sdk_venv_found")),
        "dedicated_sdk_venv_imports_acontext": bool(
            observed.get("dedicated_sdk_venv_imports_acontext")
        ),
        "active_runner_sdk_available": bool(observed.get("active_runner_sdk_available")),
        "compose_up_attempted": bool(observed.get("compose_up_attempted")),
        "compose_pull_started": bool(observed.get("compose_pull_started")),
        "compose_pull_completed": bool(observed.get("compose_pull_completed")),
        "compose_services_started": bool(observed.get("compose_services_started")),
        "api_reachable_after_attempt": bool(
            observed.get("local_acontext_api_reachable")
        ),
        "dashboard_reachable_after_attempt": bool(
            observed.get("local_acontext_dashboard_reachable")
        ),
        "ready_to_attempt_live_transport": False,
        "attempt_allowed": False,
        "all_prerequisites_cleared": False,
        "preflight_rerun_completed": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "live_memory_transport_swap_ready": False,
        "customer_visible_aas_packaging_ready": False,
        "public_route_ready": False,
        "operator_queue_launch_ready": False,
        "autonomous_dispatch_ready": False,
        "erc8004_reputation_ready": False,
        "payment_coverage_reverified_by_this_log": False,
        "production_infrastructure_reverified_by_this_log": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
        "blockers": blockers,
    }
    return readiness


def _operator_next_actions(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "action_id": "complete_compose_image_pulls",
            "required": not bool(observed.get("compose_pull_completed")),
            "why": "compose up did not reach a completed pull/start state",
            "success_signal": "all Acontext images pulled and compose exits after container creation",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "start_and_healthcheck_local_services",
            "required": not bool(observed.get("compose_services_started")),
            "why": "no local Acontext service container reached a started/healthy state",
            "success_signal": "API and dashboard health probes respond locally",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "wire_active_runner_sdk_or_use_explicit_venv_runner",
            "required": not bool(observed.get("active_runner_sdk_available")),
            "why": "the active Homebrew Python runner still cannot import acontext",
            "success_signal": "the runner used by parity code imports acontext without path hacks",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "rerun_read_only_preflight_before_any_live_write",
            "required": True,
            "why": "setup work must be converted into a fresh blocker delta before transport writes",
            "success_signal": "preflight blockers are empty and the gate explicitly allows one attempt",
            "authorizes_live_attempt_by_itself": False,
        },
    ]


def _recovery_verdict(observed: dict[str, Any]) -> str:
    if (
        observed.get("active_runner_sdk_available")
        and observed.get("compose_pull_completed")
        and observed.get("compose_services_started")
        and observed.get("local_acontext_api_reachable")
        and observed.get("local_acontext_dashboard_reachable")
    ):
        return "unexpected_ready_state_requires_fresh_preflight"
    return "recovery_attempt_logged_still_not_live_ready"


def _assert_source_activation_board(board: dict[str, Any]) -> None:
    if board.get("schema") != ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA:
        raise CityOpsContractError("recovery attempt log requires activation board source")
    readiness = board.get("readiness") or {}
    if readiness.get("ready_to_attempt_live_transport"):
        raise CityOpsContractError("recovery log must not consume an already-ready board")
    if not readiness.get("activation_board_landed"):
        raise CityOpsContractError("activation board source is not landed")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    if observed.get("live_acontext_write_performed"):
        raise CityOpsContractError("recovery attempt log cannot record live write")
    if observed.get("live_acontext_retrieval_performed"):
        raise CityOpsContractError("recovery attempt log cannot record live retrieval")
    if observed.get("compose_services_started") and not observed.get("compose_pull_completed"):
        raise CityOpsContractError("compose services cannot start before pull completion")
    if observed.get("local_acontext_api_reachable") and not observed.get(
        "compose_services_started"
    ):
        raise CityOpsContractError("API reachability requires started compose services")
    if observed.get("local_acontext_dashboard_reachable") and not observed.get(
        "compose_services_started"
    ):
        raise CityOpsContractError("dashboard reachability requires started compose services")


def _assert_claim_boundaries(safe: list[str], blocked: list[str]) -> None:
    overlap = set(safe) & set(blocked)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _assert_log_conservative(log: dict[str, Any]) -> None:
    if log.get("schema") != ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA:
        raise CityOpsContractError("unexpected recovery attempt log schema")
    for key in _FALSE_ACCESS_FLAGS:
        if log["access_policy"].get(key):
            raise CityOpsContractError(f"access policy drift: {key}")
    readiness = log.get("readiness") or {}
    for key in _FALSE_READINESS_FLAGS:
        if readiness.get(key):
            raise CityOpsContractError(f"promoted readiness: {key}")
    if not readiness.get("recovery_attempt_log_landed"):
        raise CityOpsContractError("recovery attempt log did not land")
    if log.get("recovery_verdict") != "recovery_attempt_logged_still_not_live_ready":
        raise CityOpsContractError("unexpected ready verdict in conservative log")
    if set(log["claim_boundaries"]["safe_to_claim"]) & set(
        log["claim_boundaries"]["do_not_claim_yet"]
    ):
        raise CityOpsContractError("safe and blocked claims overlap")
    if log["derived_from"].get("writes_live_acontext"):
        raise CityOpsContractError("recovery log cannot write live Acontext")
    if log["derived_from"].get("retrieves_live_acontext"):
        raise CityOpsContractError("recovery log cannot retrieve live Acontext")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
