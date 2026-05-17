"""Runtime-memory Acontext prerequisite probe for City-as-a-Service.

This artifact records the May 16 22:01 EDT prerequisite probe after the
runtime-memory preflight rerun.  It checks Docker/compose/CLI/SDK/API/dashboard
readiness and keeps the live parity gate closed: compose image pulling still did
not complete, no services started, the default active runner still cannot import
``acontext``, and localhost API/dashboard health checks still fail.

It never writes to Acontext, never retrieves from Acontext, never starts a
customer/public route, and never promotes runtime, dispatch, reputation,
payment, production, GPS/raw metadata, or worker-doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_runtime_memory_preflight_rerun import (
    ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM,
    ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA,
    RUNTIME_MEMORY_PREFLIGHT_RERUN_BLOCKED_CLAIMS,
    load_acontext_runtime_memory_preflight_rerun,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SCHEMA = (
    "city_ops.acontext_runtime_memory_prerequisite_probe.v1"
)
ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME = (
    "acontext_runtime_memory_prerequisite_probe.json"
)
ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM = (
    "admin_acontext_runtime_memory_prerequisite_probe_landed"
)

RUNTIME_MEMORY_PREREQUISITE_PROBE_BLOCKED_CLAIMS = [
    *RUNTIME_MEMORY_PREFLIGHT_RERUN_BLOCKED_CLAIMS,
    "acontext_cli_available_by_runtime_memory_prerequisite_probe",
    "default_active_runner_sdk_import_ready_by_runtime_memory_prerequisite_probe",
    "compose_long_window_pull_completed_by_runtime_memory_prerequisite_probe",
    "compose_services_started_by_runtime_memory_prerequisite_probe",
    "localhost_api_reachable_by_runtime_memory_prerequisite_probe",
    "localhost_dashboard_reachable_by_runtime_memory_prerequisite_probe",
    "readiness_gate_rebuilt_empty_by_runtime_memory_prerequisite_probe",
    "one_live_parity_attempt_authorized_by_runtime_memory_prerequisite_probe",
    "live_acontext_write_completed_by_runtime_memory_prerequisite_probe",
    "live_acontext_retrieval_completed_by_runtime_memory_prerequisite_probe",
    "runtime_parity_proven_by_runtime_memory_prerequisite_probe",
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
    "compose_pull_completed",
    "compose_services_started",
    "api_reachable_after_probe",
    "dashboard_reachable_after_probe",
    "default_active_runner_sdk_import_ready",
    "acontext_cli_available_on_path",
    "readiness_gate_rebuilt_with_empty_blockers",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_probe",
    "production_infrastructure_reverified_by_this_probe",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may16_2201_runtime_memory_prerequisite_observation() -> dict[str, Any]:
    """Return the deterministic May 16 22:01 prerequisite probe observation."""

    return {
        "observation_window": "2026-05-16T22:01:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "docker": {
            "checked": True,
            "daemon_available": True,
            "version_command_exit_code": 0,
        },
        "compose": {
            "checked": True,
            "compose_available": True,
            "compose_manifest_found": True,
            "compose_env_file_found": True,
            "service_names_observed": [
                "acontext-server-jaeger",
                "acontext-server-pg",
                "acontext-server-rabbitmq",
                "acontext-server-redis",
                "acontext-server-seaweedfs",
                "acontext-server-seaweedfs-setup",
                "acontext-server-core",
                "acontext-server-api",
                "acontext-server-ui",
            ],
            "pull_command_started": True,
            "pull_window_seconds_approx": 585,
            "pull_completed": False,
            "pull_stopped_by_operator": True,
            "pull_stop_reason": "no_progress_after_about_10_minutes_sigkill",
            "individual_redis_pull_completed": False,
            "individual_redis_pull_timeout_seconds": 180,
            "compose_up_started": False,
            "services_started": False,
            "containers_running": False,
            "local_images_observed": ["pgvector/pgvector:pg16"],
        },
        "cli": {
            "checked": True,
            "acontext_binary_on_path": False,
            "python_module_cli_available": False,
            "error": "which acontext failed and python -m acontext has no __main__",
        },
        "sdk": {
            "checked": True,
            "dedicated_venv_found": True,
            "dedicated_venv_path": "~/clawd/.venv-acontext",
            "dedicated_venv_imports_acontext": True,
            "dedicated_venv_acontext_version": "0.1.13",
            "default_active_runner_imports_acontext": False,
            "default_active_runner_error": "ModuleNotFoundError: No module named 'acontext'",
            "explicit_venv_bridge_available_for_read_only_preflight": True,
        },
        "api": {
            "checked": True,
            "url": "http://localhost:8029/api/v1",
            "reachable": False,
            "error": "connection refused",
        },
        "dashboard": {
            "checked": True,
            "url": "http://localhost:3000",
            "reachable": False,
            "error": "connection refused",
        },
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
    }


def build_acontext_runtime_memory_prerequisite_probe(
    *,
    artifact_dir: str | Path | None = None,
    runtime_rerun: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed runtime-memory prerequisite probe artifact."""

    source_rerun = runtime_rerun or load_acontext_runtime_memory_preflight_rerun(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may16_2201_runtime_memory_prerequisite_observation()
    _assert_source_rerun_blocked(source_rerun)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source_rerun["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM,
            ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_rerun["claim_boundaries"]["do_not_claim_yet"],
            *RUNTIME_MEMORY_PREREQUISITE_PROBE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    probe = {
        "schema": ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SCHEMA,
        "probe_id": f"acontext_runtime_memory_prerequisite_probe:{source_rerun['rerun_id']}",
        "source_rerun_id": source_rerun["rerun_id"],
        "proof_anchor_id": source_rerun["proof_anchor_id"],
        "coordination_session_id": source_rerun["coordination_session_id"],
        "compact_decision_id": source_rerun["compact_decision_id"],
        "review_packet_id": source_rerun["review_packet_id"],
        "packet_id": source_rerun["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME],
            "source_schema": source_rerun["schema"],
            "source_verdict": source_rerun["rerun_verdict"],
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
        "runtime_memory_prerequisite_observation": dict(observed),
        "prerequisite_cards": _prerequisite_cards(observed),
        "readiness": _readiness(observed),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_next_actions": _operator_next_actions(observed),
        "probe_verdict": "runtime_memory_prerequisites_still_block_live_parity",
        "operator_instruction": (
            "Treat this as prerequisite evidence only. Do not run live Acontext "
            "write/retrieve parity until image pulls complete, services start, "
            "localhost API/dashboard probes pass, the default runner import path or "
            "explicit runner decision is resolved, and a rebuilt gate has empty blockers."
        ),
    }
    _assert_probe_conservative(probe)
    return probe


def write_acontext_runtime_memory_prerequisite_probe(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the runtime-memory prerequisite probe artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    probe = build_acontext_runtime_memory_prerequisite_probe(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME
    path.write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_runtime_memory_prerequisite_probe(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted runtime-memory prerequisite probe."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        probe = json.load(fh)
    _assert_probe_conservative(probe)
    return probe


def _prerequisite_cards(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card_id": "docker_and_compose",
            "status": "available_but_pull_not_completed",
            "docker_daemon_available": bool(observed["docker"].get("daemon_available")),
            "compose_available": bool(observed["compose"].get("compose_available")),
            "pull_completed": bool(observed["compose"].get("pull_completed")),
            "services_started": bool(observed["compose"].get("services_started")),
            "authorizes_live_attempt": False,
        },
        {
            "card_id": "cli_and_sdk",
            "status": "explicit_sdk_available_default_runner_and_cli_blocked",
            "acontext_cli_available_on_path": bool(
                observed["cli"].get("acontext_binary_on_path")
            ),
            "dedicated_venv_imports_acontext": bool(
                observed["sdk"].get("dedicated_venv_imports_acontext")
            ),
            "default_active_runner_imports_acontext": bool(
                observed["sdk"].get("default_active_runner_imports_acontext")
            ),
            "authorizes_live_attempt": False,
        },
        {
            "card_id": "localhost_reachability",
            "status": "api_and_dashboard_unreachable",
            "api_reachable": bool(observed["api"].get("reachable")),
            "dashboard_reachable": bool(observed["dashboard"].get("reachable")),
            "authorizes_live_attempt": False,
        },
        {
            "card_id": "live_parity_gate",
            "status": "not_rebuilt_empty_not_authorized",
            "readiness_gate_rebuilt_with_empty_blockers": bool(
                observed.get("readiness_gate_rebuilt_with_empty_blockers")
            ),
            "live_acontext_write_performed": bool(
                observed.get("live_acontext_write_performed")
            ),
            "live_acontext_retrieval_performed": bool(
                observed.get("live_acontext_retrieval_performed")
            ),
            "authorizes_live_attempt": False,
        },
    ]


def _readiness(observed: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    if not observed["cli"].get("acontext_binary_on_path"):
        blockers.append("acontext_cli_not_on_path")
    if not observed["sdk"].get("default_active_runner_imports_acontext"):
        blockers.append("default_active_runner_acontext_import_missing")
    if not observed["compose"].get("pull_completed"):
        blockers.append("compose_image_pull_not_completed")
    if not observed["compose"].get("services_started"):
        blockers.append("acontext_compose_services_not_started")
    if not observed["api"].get("reachable"):
        blockers.append("local_acontext_api_unreachable")
    if not observed["dashboard"].get("reachable"):
        blockers.append("local_acontext_dashboard_unreachable")
    if not observed.get("readiness_gate_rebuilt_with_empty_blockers"):
        blockers.append("readiness_gate_not_rebuilt_empty")

    return {
        "runtime_memory_prerequisite_probe_landed": True,
        "docker_available": bool(observed["docker"].get("daemon_available")),
        "compose_available": bool(observed["compose"].get("compose_available")),
        "acontext_cli_available_on_path": False,
        "dedicated_venv_imports_acontext": bool(
            observed["sdk"].get("dedicated_venv_imports_acontext")
        ),
        "default_active_runner_sdk_import_ready": False,
        "explicit_venv_bridge_available_for_read_only_preflight": bool(
            observed["sdk"].get("explicit_venv_bridge_available_for_read_only_preflight")
        ),
        "compose_pull_completed": False,
        "compose_services_started": False,
        "api_reachable_after_probe": False,
        "dashboard_reachable_after_probe": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
        "ready_to_attempt_live_transport": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "customer_visible_aas_packaging_ready": False,
        "public_route_ready": False,
        "operator_queue_launch_ready": False,
        "autonomous_dispatch_ready": False,
        "erc8004_reputation_ready": False,
        "payment_coverage_reverified_by_this_probe": False,
        "production_infrastructure_reverified_by_this_probe": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
        "remaining_blockers": blockers,
    }


def _operator_next_actions(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "action_id": "resolve_docker_pull_hang_or_pre_pull_images_individually",
            "status": "blocked",
            "success_signal": "all compose images exist locally and compose pull exits cleanly",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "start_acontext_compose_services",
            "status": "blocked_until_pull_completes",
            "success_signal": "docker compose ps shows API and UI containers running/healthy",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "verify_localhost_api_dashboard",
            "status": "blocked_until_services_start",
            "success_signal": "http://localhost:8029/api/v1 and http://localhost:3000 respond locally",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "resolve_default_runner_or_formally_use_explicit_venv_runner",
            "status": "blocked",
            "success_signal": "default runner imports acontext or the gate records the explicit venv as the authorized preflight runner",
            "authorizes_live_attempt_by_itself": False,
        },
        {
            "action_id": "rebuild_read_only_preflight_delta_surface_and_gate",
            "status": "next_after_prerequisites",
            "success_signal": "rebuilt gate has empty blockers and authorizes exactly one live parity attempt",
            "authorizes_live_attempt_by_itself": False,
        },
    ]


def _assert_source_rerun_blocked(rerun: dict[str, Any]) -> None:
    if rerun.get("schema") != ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA:
        raise CityOpsContractError("prerequisite probe requires runtime-memory rerun source")
    readiness = rerun.get("readiness") or {}
    if readiness.get("ready_to_attempt_live_transport") is not False:
        raise CityOpsContractError("prerequisite probe cannot consume ready transport")
    if not readiness.get("remaining_blockers"):
        raise CityOpsContractError("prerequisite probe requires remaining blockers")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    if observed.get("live_acontext_write_performed"):
        raise CityOpsContractError("prerequisite probe cannot record live write")
    if observed.get("live_acontext_retrieval_performed"):
        raise CityOpsContractError("prerequisite probe cannot record live retrieval")
    if observed.get("readiness_gate_rebuilt_with_empty_blockers"):
        raise CityOpsContractError("prerequisite probe cannot record empty rebuilt gate")
    if observed["compose"].get("services_started") and not observed["compose"].get(
        "pull_completed"
    ):
        raise CityOpsContractError("services cannot start before pull completion")
    if observed["api"].get("reachable") and not observed["compose"].get("services_started"):
        raise CityOpsContractError("API reachability requires started services")
    if observed["dashboard"].get("reachable") and not observed["compose"].get(
        "services_started"
    ):
        raise CityOpsContractError("dashboard reachability requires started services")
    if not observed["sdk"].get("dedicated_venv_imports_acontext"):
        raise CityOpsContractError("prerequisite probe requires dedicated SDK progress")


def _assert_probe_conservative(probe: dict[str, Any]) -> None:
    if probe.get("schema") != ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SCHEMA:
        raise CityOpsContractError("runtime-memory prerequisite probe schema drift")
    if probe.get("probe_verdict") != "runtime_memory_prerequisites_still_block_live_parity":
        raise CityOpsContractError("runtime-memory prerequisite probe verdict drift")
    for flag in _FALSE_ACCESS_FLAGS:
        if probe.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"runtime-memory prerequisite access promoted {flag}")
    readiness = probe.get("readiness", {})
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"runtime-memory prerequisite readiness promoted {flag}")
    if readiness.get("runtime_memory_prerequisite_probe_landed") is not True:
        raise CityOpsContractError("runtime-memory prerequisite landed flag missing")
    if not readiness.get("remaining_blockers"):
        raise CityOpsContractError("runtime-memory prerequisite probe requires blockers")
    _assert_claim_boundaries(
        probe.get("claim_boundaries", {}).get("safe_to_claim", []),
        probe.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    for card in probe.get("prerequisite_cards", []):
        if card.get("authorizes_live_attempt") is not False:
            raise CityOpsContractError("prerequisite card authorized live attempt")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"runtime-memory prerequisite claim overlap: {overlap}")
    if ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("runtime-memory prerequisite safe claim missing")
    missing = sorted(
        set(RUNTIME_MEMORY_PREREQUISITE_PROBE_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    )
    if missing:
        raise CityOpsContractError(f"runtime-memory prerequisite blocked claims missing: {missing}")


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
