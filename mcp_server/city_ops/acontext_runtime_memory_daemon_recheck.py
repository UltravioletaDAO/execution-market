"""Current daemon-down recheck for City-as-a-Service Acontext runtime memory.

This artifact records the May 23 02:00 EDT read-only prerequisite recheck after
prior Acontext pull-path diagnostics.  The local Docker context still points at
``desktop-linux``, but the Docker API socket is unavailable, Buildx cannot talk
to the daemon, no Acontext containers are running, and the local API/dashboard
remain unreachable.

It does not start Docker Desktop, does not pull images, does not start Compose,
does not write to or retrieve from Acontext, and does not authorize runtime,
dispatch, reputation, payment, production, GPS/raw metadata, customer/public, or
worker-copyable doctrine claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_docker_pull_path_diagnostic import (
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME,
    ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM,
    DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS,
    load_acontext_docker_pull_path_diagnostic,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA = (
    "city_ops.acontext_runtime_memory_daemon_recheck.v1"
)
ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME = (
    "acontext_runtime_memory_daemon_recheck.json"
)
ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM = (
    "admin_acontext_runtime_memory_daemon_recheck_landed"
)

DAEMON_RECHECK_BLOCKED_CLAIMS = [
    *DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS,
    "daemon_recheck_started_docker_desktop",
    "daemon_recheck_repaired_docker_socket",
    "daemon_recheck_restored_buildx_builder",
    "daemon_recheck_checked_complete_image_inventory",
    "daemon_recheck_pulled_required_acontext_images",
    "daemon_recheck_started_compose_services",
    "daemon_recheck_reached_acontext_api",
    "daemon_recheck_reached_acontext_dashboard",
    "daemon_recheck_rebuilt_empty_readiness_gate",
    "daemon_recheck_authorized_live_parity_attempt",
    "daemon_recheck_completed_live_acontext_write",
    "daemon_recheck_completed_live_acontext_retrieval",
    "daemon_recheck_proved_runtime_parity",
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
    "docker_daemon_available",
    "buildx_builder_available",
    "image_inventory_checked",
    "required_images_present",
    "compose_services_started",
    "acontext_containers_running",
    "api_reachable_after_recheck",
    "dashboard_reachable_after_recheck",
    "readiness_gate_rebuilt_with_empty_blockers",
    "one_live_parity_attempt_authorized",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_recheck",
    "production_infrastructure_reverified_by_this_recheck",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may23_0200_daemon_recheck_observation() -> dict[str, Any]:
    """Return the deterministic May 23 02:00 daemon-down observation."""

    return {
        "observation_window": "2026-05-23T02:00:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": "follow_next_safe_acontext_prerequisite_recheck_without_starting_services",
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "commands_observed": [
            "docker version --format '{{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}'",
            "docker context show",
            "docker buildx ls | head -5",
            "docker images --format '{{.Repository}}:{{.Tag}}' | grep required images",
            "docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep -i acontext",
            "curl --max-time 2 http://localhost:8029/api/v1/health",
            "curl --max-time 2 http://localhost:3000",
        ],
        "docker": {
            "context": "desktop-linux",
            "daemon_available": False,
            "docker_socket": "~/.docker/run/docker.sock",
            "socket_error_class": "missing_user_docker_socket",
            "version_command_returned_server_version": False,
            "api_error": "failed_to_connect_to_docker_api_socket",
        },
        "buildx": {
            "checked": True,
            "builder_status": "error",
            "default_builder_status": "error",
            "desktop_linux_builder_status": "error",
            "buildkit_version_observed": None,
            "platforms_observed": [],
        },
        "image_inventory": {
            "checked": False,
            "skipped_reason": "docker_daemon_unavailable",
            "required_image_count_known_from_prior_diagnostic": True,
            "complete_inventory_verified": False,
        },
        "containers": {
            "checked": False,
            "skipped_reason": "docker_daemon_unavailable",
            "acontext_containers_running": False,
        },
        "api": {
            "checked": True,
            "url": "http://localhost:8029/api/v1/health",
            "reachable": False,
            "error_class": "connection_refused",
        },
        "dashboard": {
            "checked": True,
            "url": "http://localhost:3000",
            "reachable": False,
            "error_class": "connection_refused",
        },
        "compose_services_started": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
    }


def build_acontext_runtime_memory_daemon_recheck(
    *,
    artifact_dir: str | Path | None = None,
    pull_path_diagnostic: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed runtime-memory daemon recheck artifact."""

    source = pull_path_diagnostic or load_acontext_docker_pull_path_diagnostic(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may23_0200_daemon_recheck_observation()
    _assert_source_pull_path_still_blocked(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM,
            ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *DAEMON_RECHECK_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    recheck = {
        "schema": ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA,
        "recheck_id": f"acontext_runtime_memory_daemon_recheck:{source['diagnostic_id']}",
        "source_diagnostic_id": source["diagnostic_id"],
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "packet_id": source["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME],
            "forbidden_inputs": [
                "registry_tokens",
                "raw_docker_logs_with_credentials",
                "private_operator_context",
                "raw_transcripts",
                "unreviewed_memory",
                "freeform_worker_chat",
                "live_acontext_sink_writes",
                "live_acontext_retrievals",
                "payment_processor_probe",
                "production_health_probe",
                "gps_or_raw_metadata_payloads",
                "customer_copy_drafts",
                "worker_instruction_templates",
            ],
            "starts_docker_desktop": False,
            "pulls_container_images": False,
            "starts_compose_services": False,
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
            **{flag: False for flag in _FALSE_ACCESS_FLAGS},
        },
        "daemon_recheck_observation": observed,
        "daemon_status_summary": _daemon_status_summary(observed),
        "runtime_blocker_cards": _runtime_blocker_cards(observed),
        "operator_next_actions": _operator_next_actions(),
        "readiness": _readiness(observed),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "recheck_verdict": "docker_daemon_unavailable_runtime_memory_still_blocked",
        "operator_instruction": (
            "Do not attempt live Acontext parity from this state. First restore the local "
            "Docker daemon/socket, then recheck image inventory, complete the trusted image "
            "pull/cache path, start compose, verify API/dashboard health, rebuild the "
            "readiness gate empty, and only then authorize exactly one write/retrieve parity pass."
        ),
    }
    _assert_recheck_conservative(recheck)
    return recheck


def write_acontext_runtime_memory_daemon_recheck(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic daemon recheck artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    recheck = build_acontext_runtime_memory_daemon_recheck(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME
    path.write_text(json.dumps(recheck, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_runtime_memory_daemon_recheck(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted daemon recheck artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        recheck = json.load(fh)
    source = load_acontext_docker_pull_path_diagnostic(artifact_dir=base_dir)
    _assert_recheck_conservative(recheck)
    if recheck != build_acontext_runtime_memory_daemon_recheck(
        artifact_dir=base_dir, pull_path_diagnostic=source
    ):
        raise CityOpsContractError("Acontext daemon recheck drifted from source diagnostic")
    return recheck


def _daemon_status_summary(observation: dict[str, Any]) -> dict[str, Any]:
    docker = observation["docker"]
    buildx = observation["buildx"]
    return {
        "docker_context": docker["context"],
        "docker_daemon_available": docker["daemon_available"],
        "docker_socket": docker["docker_socket"],
        "socket_error_class": docker["socket_error_class"],
        "buildx_builder_available": buildx["builder_status"] != "error",
        "daemon_unavailable_blocks_image_inventory": True,
        "daemon_unavailable_blocks_compose_startup": True,
        "daemon_unavailable_blocks_live_parity_attempt": True,
    }


def _runtime_blocker_cards(observation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "docker_daemon",
            "status": "blocked_socket_unavailable",
            "context": observation["docker"]["context"],
            "daemon_available": observation["docker"]["daemon_available"],
            "next_check": "restore Docker Desktop/user socket before image inventory or compose startup",
            "authorizes_live_attempt": False,
        },
        {
            "card": "buildx_and_inventory",
            "status": "blocked_by_daemon_unavailable",
            "buildx_status": observation["buildx"]["builder_status"],
            "image_inventory_checked": observation["image_inventory"]["checked"],
            "complete_inventory_verified": observation["image_inventory"]["complete_inventory_verified"],
            "authorizes_live_attempt": False,
        },
        {
            "card": "local_services",
            "status": "blocked_not_running",
            "api_reachable": observation["api"]["reachable"],
            "dashboard_reachable": observation["dashboard"]["reachable"],
            "compose_services_started": observation["compose_services_started"],
            "authorizes_live_attempt": False,
        },
        {
            "card": "live_parity_gate",
            "status": "closed",
            "readiness_gate_rebuilt_with_empty_blockers": observation[
                "readiness_gate_rebuilt_with_empty_blockers"
            ],
            "live_acontext_write_performed": observation["live_acontext_write_performed"],
            "live_acontext_retrieval_performed": observation[
                "live_acontext_retrieval_performed"
            ],
            "authorizes_live_attempt": False,
        },
    ]


def _operator_next_actions() -> list[dict[str, Any]]:
    return [
        {
            "step_id": "restore_local_docker_daemon",
            "action": "Start or repair Docker Desktop so the desktop-linux user socket responds.",
            "must_record": ["context", "socket_path", "server_version", "buildx_status"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "recheck_required_image_inventory",
            "action": "List required Acontext images after daemon restoration before any compose startup.",
            "must_record": ["required_image_count", "present_images", "missing_images"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "resolve_image_cache_or_pull_path",
            "action": "Complete required images via normal pull path or a trusted cache/mirror; never record credentials.",
            "must_record": ["image_source", "present_image_count", "credential_material_excluded"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "start_services_and_healthcheck",
            "action": "Start local Compose only after image inventory is complete, then verify API and dashboard health.",
            "must_record": ["compose_status", "api_health", "dashboard_health"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "rebuild_gate_before_one_live_pass",
            "action": "Rerun read-only preflight and rebuild the attempt gate before exactly one live parity pass.",
            "must_record": ["empty_blocker_gate", "write_allowed", "retrieve_allowed"],
            "authorizes_live_attempt": "only_if_gate_empty",
        },
    ]


def _readiness(observation: dict[str, Any]) -> dict[str, Any]:
    readiness: dict[str, Any] = {
        "daemon_recheck_landed": True,
        "source_docker_pull_path_diagnostic_consumed": True,
        "current_docker_context_recorded": True,
        "current_daemon_unavailable_recorded": True,
        "current_api_dashboard_unreachable_recorded": True,
        "remaining_blockers": [
            "docker_daemon_socket_unavailable",
            "buildx_builder_error_due_to_daemon_unavailable",
            "required_image_inventory_not_checkable",
            "acontext_compose_services_not_started",
            "local_acontext_api_unreachable",
            "local_acontext_dashboard_unreachable",
            "readiness_gate_not_rebuilt_empty",
        ],
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    if observation["docker"]["daemon_available"] is True:
        readiness["docker_daemon_available"] = True
    return readiness


def _assert_source_pull_path_still_blocked(source: dict[str, Any]) -> None:
    if source.get("diagnostic_verdict") != "docker_context_available_but_explicit_platform_pull_still_stalls":
        raise CityOpsContractError("source Docker pull-path diagnostic must still be blocked")
    readiness = source.get("readiness", {})
    for flag in (
        "all_required_images_present",
        "compose_services_started",
        "api_reachable_after_diagnostic",
        "dashboard_reachable_after_diagnostic",
        "runtime_parity_proven",
    ):
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"source Docker pull-path diagnostic unexpectedly promoted {flag}")


def _assert_observation_conservative(observation: dict[str, Any]) -> None:
    policy = observation.get("sanitization_policy", {})
    for field in (
        "include_tokens",
        "include_registry_credentials",
        "include_raw_docker_logs",
        "include_home_paths",
        "include_private_operator_context",
    ):
        if policy.get(field) is not False:
            raise CityOpsContractError(f"daemon recheck must not include {field}")
    docker = observation.get("docker", {})
    if docker.get("context") != "desktop-linux":
        raise CityOpsContractError("daemon recheck expects desktop-linux context")
    if docker.get("daemon_available") is not False:
        raise CityOpsContractError("daemon recheck is only valid while Docker daemon is unavailable")
    if observation.get("buildx", {}).get("builder_status") != "error":
        raise CityOpsContractError("daemon recheck expects buildx error while daemon is unavailable")
    inventory = observation.get("image_inventory", {})
    if inventory.get("checked") is not False:
        raise CityOpsContractError("daemon recheck cannot claim image inventory was checked")
    if inventory.get("complete_inventory_verified") is not False:
        raise CityOpsContractError("daemon recheck cannot verify complete image inventory")
    if observation.get("containers", {}).get("acontext_containers_running") is not False:
        raise CityOpsContractError("daemon recheck cannot record running Acontext containers")
    if observation.get("api", {}).get("reachable") is not False:
        raise CityOpsContractError("daemon recheck cannot record reachable API")
    if observation.get("dashboard", {}).get("reachable") is not False:
        raise CityOpsContractError("daemon recheck cannot record reachable dashboard")
    if observation.get("compose_services_started") is not False:
        raise CityOpsContractError("daemon recheck cannot record started Compose services")
    if observation.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("daemon recheck cannot record live Acontext write")
    if observation.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("daemon recheck cannot record live Acontext retrieval")
    if observation.get("readiness_gate_rebuilt_with_empty_blockers") is not False:
        raise CityOpsContractError("daemon recheck cannot record empty readiness gate")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"daemon recheck claim boundary overlap: {sorted(overlap)}")
    if ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("daemon recheck safe claim missing")
    for claim in DAEMON_RECHECK_BLOCKED_CLAIMS:
        if claim not in do_not_claim_yet:
            raise CityOpsContractError(f"daemon recheck blocked claim missing: {claim}")


def _assert_recheck_conservative(recheck: dict[str, Any]) -> None:
    if recheck.get("schema") != ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA:
        raise CityOpsContractError("unexpected daemon recheck schema")
    for section in ("derived_from", "access_policy"):
        payload = recheck[section]
        for key, value in payload.items():
            if isinstance(value, bool) and key not in {"read_only", "requires_admin_context"}:
                if value is not False:
                    raise CityOpsContractError(f"daemon recheck {section}.{key} must remain false")
    readiness = recheck["readiness"]
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"daemon recheck readiness promoted: {flag}")
    if recheck["daemon_status_summary"]["docker_daemon_available"] is not False:
        raise CityOpsContractError("daemon recheck cannot mark Docker daemon available")
    if recheck["daemon_status_summary"]["daemon_unavailable_blocks_live_parity_attempt"] is not True:
        raise CityOpsContractError("daemon recheck must block live parity while daemon is unavailable")
    if recheck.get("recheck_verdict") != "docker_daemon_unavailable_runtime_memory_still_blocked":
        raise CityOpsContractError("unexpected daemon recheck verdict")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
