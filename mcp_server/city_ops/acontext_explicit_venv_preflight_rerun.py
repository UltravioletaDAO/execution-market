"""Explicit-venv Acontext preflight rerun artifact for City-as-a-Service.

The 1 AM recovery attempt proved the dedicated ``~/clawd/.venv-acontext`` runner
can import Acontext, while the active Homebrew Python runner still cannot.  This
module captures the next safe seam: use the dedicated venv as an explicit
read-only preflight runner, but keep the live write/retrieve gate closed until
local Acontext services are actually reachable and a fresh gate is rebuilt.

It never writes to Acontext, never retrieves from Acontext, never starts a
customer/public route, and never promotes runtime, dispatch, reputation,
payment, production, GPS/raw metadata, or worker-doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_prerequisite_recovery_attempt_log import (
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME,
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM,
    ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA,
    RECOVERY_ATTEMPT_BLOCKED_CLAIMS,
    load_acontext_prerequisite_recovery_attempt_log,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SCHEMA = (
    "city_ops.acontext_explicit_venv_preflight_rerun.v1"
)
ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_FILENAME = (
    "acontext_explicit_venv_preflight_rerun.json"
)
ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SAFE_CLAIM = (
    "admin_acontext_explicit_venv_preflight_rerun_landed"
)

EXPLICIT_VENV_PREFLIGHT_RERUN_BLOCKED_CLAIMS = [
    *RECOVERY_ATTEMPT_BLOCKED_CLAIMS,
    "active_runner_sdk_wired_by_explicit_venv_rerun",
    "acontext_compose_pull_completed_by_explicit_venv_rerun",
    "acontext_services_started_by_explicit_venv_rerun",
    "acontext_api_dashboard_reachable_by_explicit_venv_rerun",
    "acontext_preflight_rebuilt_empty_by_explicit_venv_rerun",
    "acontext_live_parity_attempt_authorized_by_explicit_venv_rerun",
    "acontext_live_write_completed_by_explicit_venv_rerun",
    "acontext_live_retrieval_completed_by_explicit_venv_rerun",
    "acontext_sink_ready_by_explicit_venv_rerun",
    "runtime_parity_proven_by_explicit_venv_rerun",
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
    "attempt_allowed",
    "ready_to_attempt_live_transport",
    "all_prerequisites_cleared",
    "active_runner_sdk_available",
    "compose_pull_settled",
    "compose_pull_completed",
    "compose_services_started",
    "api_reachable_after_rerun",
    "dashboard_reachable_after_rerun",
    "preflight_rebuilt_with_empty_blockers",
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
    "payment_coverage_reverified_by_this_rerun",
    "production_infrastructure_reverified_by_this_rerun",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may16_2am_explicit_venv_observation() -> dict[str, Any]:
    """Return the deterministic 2 AM explicit-venv preflight observation."""

    return {
        "observation_window": "2026-05-16T02:00:00-04:00",
        "runner_mode": "explicit_dedicated_venv_probe",
        "docker_available": True,
        "acontext_cli_installed": True,
        "compose_manifest_found": True,
        "compose_env_file_found": True,
        "dedicated_sdk_venv_found": True,
        "dedicated_sdk_venv_path": "~/clawd/.venv-acontext",
        "explicit_runner_sdk_available": True,
        "explicit_runner_acontext_version": "0.1.13",
        "active_runner_sdk_available": False,
        "active_runner_sdk_blocker": "active_homebrew_python_has_no_acontext_module",
        "compose_pull_command_started": True,
        "compose_pull_settled": False,
        "compose_pull_completed": False,
        "compose_pull_stopped_by_operator": True,
        "compose_pull_stop_reason": "silent_multi_image_pull_did_not_settle_inside_2am_window",
        "compose_services_started": False,
        "local_acontext_api_reachable": False,
        "local_acontext_dashboard_reachable": False,
        "read_only_preflight_scope": True,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_explicit_venv_preflight_rerun(
    *,
    artifact_dir: str | Path | None = None,
    recovery_log: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed explicit-venv preflight rerun artifact."""

    source_log = recovery_log or load_acontext_prerequisite_recovery_attempt_log(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may16_2am_explicit_venv_observation()
    _assert_source_recovery_log(source_log)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source_log["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SAFE_CLAIM,
            ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_log["claim_boundaries"]["do_not_claim_yet"],
            *EXPLICIT_VENV_PREFLIGHT_RERUN_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    rerun = {
        "schema": ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SCHEMA,
        "rerun_id": f"acontext_explicit_venv_preflight_rerun:{source_log['log_id']}",
        "source_recovery_log_id": source_log["log_id"],
        "source_board_id": source_log["source_board_id"],
        "source_gate_id": source_log["source_gate_id"],
        "source_delta_id": source_log["source_delta_id"],
        "source_preflight_id": source_log["source_preflight_id"],
        "proof_anchor_id": source_log["proof_anchor_id"],
        "coordination_session_id": source_log["coordination_session_id"],
        "compact_decision_id": source_log["compact_decision_id"],
        "review_packet_id": source_log["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME],
            "consumes_only": [ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_FILENAME],
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
        "explicit_venv_observation": dict(observed),
        "runner_path_decision": _runner_path_decision(observed),
        "preflight_cards": _preflight_cards(observed),
        "readiness": _rerun_readiness(observed),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_next_actions": _operator_next_actions(observed),
        "rerun_verdict": "explicit_venv_preflight_rerun_logged_still_not_live_ready",
        "operator_instruction": (
            "Use the dedicated venv as the explicit preflight runner if needed, but "
            "do not run a live Acontext write/retrieve attempt until compose pull and "
            "service startup settle, API and dashboard health probes pass, a read-only "
            "preflight is rebuilt with empty blockers, and a new gate explicitly allows "
            "exactly one parity attempt."
        ),
    }
    _assert_rerun_conservative(rerun)
    return rerun


def write_acontext_explicit_venv_preflight_rerun(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic explicit-venv preflight rerun artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    rerun = build_acontext_explicit_venv_preflight_rerun(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_FILENAME
    path.write_text(json.dumps(rerun, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_explicit_venv_preflight_rerun(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted explicit-venv preflight rerun artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        rerun = json.load(fh)
    _assert_rerun_conservative(rerun)
    return rerun


def _runner_path_decision(observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_runner_status": "blocked_missing_sdk",
        "explicit_venv_status": "available_for_read_only_preflight_only",
        "recommended_runner_for_next_preflight": "~/clawd/.venv-acontext/bin/python",
        "active_runner_must_be_wired_before_default_gate": True,
        "explicit_runner_may_replace_active_runner_for_preflight": True,
        "explicit_runner_authorizes_live_write": False,
        "explicit_runner_authorizes_live_retrieve": False,
        "explicit_runner_version": observed.get("explicit_runner_acontext_version"),
    }


def _preflight_cards(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card_id": "runner_path",
            "status": "explicit_venv_available_active_runner_blocked",
            "explicit_runner_sdk_available": bool(
                observed.get("explicit_runner_sdk_available")
            ),
            "active_runner_sdk_available": bool(observed.get("active_runner_sdk_available")),
            "authorizes_live_attempt": False,
        },
        {
            "card_id": "compose_pull_state",
            "status": "pull_started_not_settled",
            "compose_pull_command_started": bool(
                observed.get("compose_pull_command_started")
            ),
            "compose_pull_settled": bool(observed.get("compose_pull_settled")),
            "compose_pull_completed": bool(observed.get("compose_pull_completed")),
            "compose_pull_stopped_by_operator": bool(
                observed.get("compose_pull_stopped_by_operator")
            ),
            "stop_reason": observed.get("compose_pull_stop_reason"),
            "compose_services_started": bool(observed.get("compose_services_started")),
            "authorizes_api_dashboard_claim": False,
        },
        {
            "card_id": "local_reachability",
            "status": "services_still_unreachable",
            "local_acontext_api_reachable": bool(
                observed.get("local_acontext_api_reachable")
            ),
            "local_acontext_dashboard_reachable": bool(
                observed.get("local_acontext_dashboard_reachable")
            ),
            "authorizes_runtime_parity_claim": False,
        },
    ]


def _rerun_readiness(observed: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    if not observed.get("compose_pull_settled"):
        blockers.append("compose_pull_not_settled")
    if not observed.get("compose_pull_completed"):
        blockers.append("compose_image_pull_not_completed")
    if not observed.get("compose_services_started"):
        blockers.append("acontext_compose_services_not_started")
    if not observed.get("local_acontext_api_reachable"):
        blockers.append("local_acontext_api_unreachable")
    if not observed.get("local_acontext_dashboard_reachable"):
        blockers.append("local_acontext_dashboard_unreachable")
    if not observed.get("active_runner_sdk_available"):
        blockers.append("active_runner_acontext_sdk_missing_or_explicit_venv_required")

    return {
        "explicit_venv_preflight_rerun_landed": True,
        "docker_available": bool(observed.get("docker_available")),
        "acontext_cli_installed": bool(observed.get("acontext_cli_installed")),
        "compose_manifest_found": bool(observed.get("compose_manifest_found")),
        "compose_env_file_found": bool(observed.get("compose_env_file_found")),
        "dedicated_sdk_venv_found": bool(observed.get("dedicated_sdk_venv_found")),
        "explicit_runner_sdk_available": bool(
            observed.get("explicit_runner_sdk_available")
        ),
        "active_runner_sdk_available": bool(observed.get("active_runner_sdk_available")),
        "compose_pull_command_started": bool(observed.get("compose_pull_command_started")),
        "compose_pull_settled": bool(observed.get("compose_pull_settled")),
        "compose_pull_completed": bool(observed.get("compose_pull_completed")),
        "compose_services_started": bool(observed.get("compose_services_started")),
        "api_reachable_after_rerun": bool(observed.get("local_acontext_api_reachable")),
        "dashboard_reachable_after_rerun": bool(
            observed.get("local_acontext_dashboard_reachable")
        ),
        "ready_to_attempt_live_transport": False,
        "attempt_allowed": False,
        "all_prerequisites_cleared": False,
        "preflight_rebuilt_with_empty_blockers": False,
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
        "payment_coverage_reverified_by_this_rerun": False,
        "production_infrastructure_reverified_by_this_rerun": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
        "blockers": blockers,
    }


def _operator_next_actions(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "action_id": "let_compose_pull_settle_or_restart_pull_with_long_window",
            "required": not bool(observed.get("compose_pull_settled")),
            "success_signal": "compose pull exits cleanly and all referenced images exist locally",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "start_compose_services_and_healthcheck_api_dashboard",
            "required": not bool(observed.get("compose_services_started")),
            "success_signal": "API and dashboard respond locally from compose services",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "rerun_preflight_with_explicit_venv_runner",
            "required": True,
            "success_signal": "read-only preflight shows docker, SDK, API, and dashboard all available",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "rebuild_blocker_delta_surface_and_attempt_gate",
            "required": True,
            "success_signal": "new gate explicitly allows exactly one live parity attempt",
            "authorizes_live_attempt_by_itself": False,
        },
    ]


def _assert_source_recovery_log(log: dict[str, Any]) -> None:
    if log.get("schema") != ACONTEXT_PREREQUISITE_RECOVERY_ATTEMPT_LOG_SCHEMA:
        raise CityOpsContractError("explicit-venv rerun requires recovery log source")
    readiness = log.get("readiness") or {}
    if readiness.get("ready_to_attempt_live_transport"):
        raise CityOpsContractError("explicit-venv rerun must not consume ready log")
    if not readiness.get("recovery_attempt_log_landed"):
        raise CityOpsContractError("recovery attempt source is not landed")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    if observed.get("live_acontext_write_performed"):
        raise CityOpsContractError("explicit-venv rerun cannot record live write")
    if observed.get("live_acontext_retrieval_performed"):
        raise CityOpsContractError("explicit-venv rerun cannot record live retrieval")
    if observed.get("compose_pull_completed") and not observed.get("compose_pull_settled"):
        raise CityOpsContractError("pull completion requires settled pull command")
    if observed.get("compose_services_started") and not observed.get("compose_pull_completed"):
        raise CityOpsContractError("services cannot start before pull completion")
    if observed.get("local_acontext_api_reachable") and not observed.get(
        "compose_services_started"
    ):
        raise CityOpsContractError("API reachability requires started compose services")
    if observed.get("local_acontext_dashboard_reachable") and not observed.get(
        "compose_services_started"
    ):
        raise CityOpsContractError("dashboard reachability requires started compose services")
    if not observed.get("explicit_runner_sdk_available"):
        raise CityOpsContractError("explicit-venv rerun requires available explicit SDK")


def _assert_claim_boundaries(safe: list[str], blocked: list[str]) -> None:
    overlap = set(safe) & set(blocked)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _assert_rerun_conservative(rerun: dict[str, Any]) -> None:
    if rerun.get("schema") != ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_SCHEMA:
        raise CityOpsContractError("unexpected explicit-venv preflight rerun schema")
    for key in _FALSE_ACCESS_FLAGS:
        if rerun["access_policy"].get(key):
            raise CityOpsContractError(f"access policy drift: {key}")
    readiness = rerun.get("readiness") or {}
    for key in _FALSE_READINESS_FLAGS:
        if readiness.get(key):
            raise CityOpsContractError(f"promoted readiness: {key}")
    if not readiness.get("explicit_venv_preflight_rerun_landed"):
        raise CityOpsContractError("explicit-venv preflight rerun did not land")
    if rerun.get("rerun_verdict") != (
        "explicit_venv_preflight_rerun_logged_still_not_live_ready"
    ):
        raise CityOpsContractError("unexpected ready verdict in explicit-venv rerun")
    if set(rerun["claim_boundaries"]["safe_to_claim"]) & set(
        rerun["claim_boundaries"]["do_not_claim_yet"]
    ):
        raise CityOpsContractError("safe and blocked claims overlap")
    if rerun["derived_from"].get("writes_live_acontext"):
        raise CityOpsContractError("explicit-venv rerun cannot write live Acontext")
    if rerun["derived_from"].get("retrieves_live_acontext"):
        raise CityOpsContractError("explicit-venv rerun cannot retrieve live Acontext")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
