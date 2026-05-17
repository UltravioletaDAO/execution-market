"""Docker pull-path diagnostic for City-as-a-Service Acontext startup.

This artifact records the May 17 02:00 EDT follow-up after the registry
manifest diagnostic proved GHCR manifests and linux/arm64 indexes were present
but Docker Desktop still stalled on the first Acontext image.

It is internal/admin prerequisite evidence only. It records sanitized Docker
context/buildx facts and one bounded explicit-platform pull retry. It does not
start compose services, does not write to or retrieve from Acontext, does not
rebuild the readiness gate, and does not authorize customer/public AAS
packaging, dispatch, reputation, payment, production, GPS/raw metadata, or
worker-copyable doctrine claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_registry_manifest_pull_stall_diagnostic import (
    ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME,
    ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM,
    REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_BLOCKED_CLAIMS,
    load_acontext_registry_manifest_pull_stall_diagnostic,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SCHEMA = "city_ops.acontext_docker_pull_path_diagnostic.v1"
ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME = "acontext_docker_pull_path_diagnostic.json"
ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM = "admin_acontext_docker_pull_path_diagnostic_landed"

DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS = [
    *REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_BLOCKED_CLAIMS,
    "docker_context_running_implies_image_pull_success",
    "buildx_arm64_platform_support_implies_layer_pull_success",
    "explicit_platform_retry_resolved_pull_stall",
    "docker_pull_path_diagnostic_pulled_first_image",
    "docker_pull_path_diagnostic_cached_all_required_images",
    "compose_services_started_by_docker_pull_path_diagnostic",
    "acontext_api_reachable_by_docker_pull_path_diagnostic",
    "acontext_dashboard_reachable_by_docker_pull_path_diagnostic",
    "readiness_gate_rebuilt_empty_by_docker_pull_path_diagnostic",
    "live_acontext_write_completed_by_docker_pull_path_diagnostic",
    "live_acontext_retrieval_completed_by_docker_pull_path_diagnostic",
    "runtime_parity_proven_by_docker_pull_path_diagnostic",
    "customer_visible_aas_packaging_ready_by_docker_pull_path_diagnostic",
    "public_route_ready_by_docker_pull_path_diagnostic",
    "operator_queue_launch_ready_by_docker_pull_path_diagnostic",
    "dispatch_ready_by_docker_pull_path_diagnostic",
    "erc8004_reputation_ready_by_docker_pull_path_diagnostic",
    "payment_or_production_reverified_by_docker_pull_path_diagnostic",
    "gps_or_raw_metadata_release_allowed_by_docker_pull_path_diagnostic",
    "worker_copyable_doctrine_ready_by_docker_pull_path_diagnostic",
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
    "first_required_image_pulled",
    "all_required_images_present",
    "compose_services_started",
    "api_reachable_after_diagnostic",
    "dashboard_reachable_after_diagnostic",
    "readiness_gate_rebuilt_with_empty_blockers",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_diagnostic",
    "production_infrastructure_reverified_by_this_diagnostic",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may17_0200_docker_pull_path_observation() -> dict[str, Any]:
    """Return the deterministic May 17 02:00 Docker pull-path observation."""

    return {
        "observation_window": "2026-05-17T02:03:00-04:00/2026-05-17T02:04:45-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": "follow_next_safe_action_from_registry_manifest_pull_stall_diagnostic",
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "docker_context_observation": {
            "current_context": "desktop-linux",
            "available_contexts": ["default", "desktop-linux"],
            "docker_endpoint_kinds": ["system_socket", "docker_desktop_user_socket"],
            "context_errors_observed": [],
            "server_version": "29.1.3",
            "server_os": "linux",
            "server_arch": "aarch64",
            "cgroup_version": "2",
            "storage_driver": "overlayfs",
            "context_server_name": "docker-desktop",
        },
        "buildx_observation": {
            "builder_status": "running",
            "buildkit_version": "v0.26.2",
            "advertised_platforms_include_linux_arm64": True,
            "advertised_platforms_include_linux_amd64": True,
            "meaning": "builder/platform support is present but does not prove registry layer pull success",
        },
        "explicit_platform_pull_retry": {
            "image": "ghcr.io/memodb-io/acontext-ui:latest",
            "platform": "linux/arm64",
            "command": "docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest",
            "timeout_seconds": 60,
            "duration_seconds": 60.01,
            "timed_out": True,
            "exit_code": None,
            "stdout_tail": [],
            "stderr_tail": [],
            "pulled_or_present_after_retry": False,
        },
        "local_images_observed_after_diagnostic": ["pgvector/pgvector:pg16"],
        "services_started": False,
        "api_checked_after_diagnostic": False,
        "dashboard_checked_after_diagnostic": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
    }


def build_acontext_docker_pull_path_diagnostic(
    *,
    artifact_dir: str | Path | None = None,
    registry_diagnostic: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed Docker pull-path diagnostic."""

    source = registry_diagnostic or load_acontext_registry_manifest_pull_stall_diagnostic(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may17_0200_docker_pull_path_observation()
    _assert_source_registry_diagnostic_still_blocked(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM,
            ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    diagnostic = {
        "schema": ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SCHEMA,
        "diagnostic_id": f"acontext_docker_pull_path_diagnostic:{source['diagnostic_id']}",
        "source_diagnostic_id": source["diagnostic_id"],
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "packet_id": source["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME],
            "forbidden_inputs": [
                "raw_docker_logs_with_credentials",
                "registry_tokens",
                "private_operator_context",
                "raw_transcripts",
                "unreviewed_memory",
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
            **{flag: False for flag in _FALSE_ACCESS_FLAGS},
        },
        "docker_pull_path_observation": observed,
        "docker_context_summary": _docker_context_summary(observed),
        "explicit_platform_retry_summary": _explicit_platform_retry_summary(observed),
        "image_inventory": _image_inventory(observed),
        "readiness": _readiness(observed),
        "operator_next_actions": _operator_next_actions(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "diagnostic_verdict": "docker_context_available_but_explicit_platform_pull_still_stalls",
        "operator_instruction": (
            "Treat Docker context and buildx platform support as prerequisite availability only. "
            "The explicit linux/arm64 pull retry still timed out without output and did not place "
            "the first GHCR image locally. Keep Acontext startup and live write/retrieve parity "
            "blocked until the pull path is fixed or a trusted image cache/mirror supplies all "
            "required images, services start, API/dashboard health passes, and the readiness gate "
            "is rebuilt empty."
        ),
    }
    _assert_diagnostic_conservative(diagnostic)
    return diagnostic


def write_acontext_docker_pull_path_diagnostic(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic Docker pull-path diagnostic."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    diagnostic = build_acontext_docker_pull_path_diagnostic(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME
    path.write_text(json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_docker_pull_path_diagnostic(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Docker pull-path diagnostic."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        diagnostic = json.load(fh)
    source = load_acontext_registry_manifest_pull_stall_diagnostic(artifact_dir=base_dir)
    _assert_diagnostic_conservative(diagnostic)
    if diagnostic != build_acontext_docker_pull_path_diagnostic(
        artifact_dir=base_dir, registry_diagnostic=source
    ):
        raise CityOpsContractError("Docker pull-path diagnostic drifted from source diagnostic")
    return diagnostic


def _docker_context_summary(observation: dict[str, Any]) -> dict[str, Any]:
    context = observation["docker_context_observation"]
    buildx = observation["buildx_observation"]
    return {
        "docker_context_available": context["current_context"] == "desktop-linux",
        "server_version": context["server_version"],
        "server_arch": context["server_arch"],
        "storage_driver": context["storage_driver"],
        "context_errors_observed": context["context_errors_observed"],
        "buildx_running": buildx["builder_status"] == "running",
        "buildx_linux_arm64_advertised": buildx["advertised_platforms_include_linux_arm64"],
        "context_availability_is_not_pull_success": True,
    }


def _explicit_platform_retry_summary(observation: dict[str, Any]) -> dict[str, Any]:
    retry = observation["explicit_platform_pull_retry"]
    return {
        "image": retry["image"],
        "platform": retry["platform"],
        "timeout_seconds": retry["timeout_seconds"],
        "duration_seconds": retry["duration_seconds"],
        "timed_out_without_output": retry["timed_out"]
        and not retry["stdout_tail"]
        and not retry["stderr_tail"],
        "exit_code": retry["exit_code"],
        "pulled_or_present_after_retry": retry["pulled_or_present_after_retry"],
        "explicit_platform_retry_blocker_remains": True,
    }


def _image_inventory(observation: dict[str, Any]) -> dict[str, Any]:
    observed = set(observation["local_images_observed_after_diagnostic"])
    return {
        "required_image_count": len(REQUIRED_ACONTEXT_IMAGES),
        "present_required_images": [image for image in REQUIRED_ACONTEXT_IMAGES if image in observed],
        "missing_required_images": [image for image in REQUIRED_ACONTEXT_IMAGES if image not in observed],
        "missing_required_image_count": sum(1 for image in REQUIRED_ACONTEXT_IMAGES if image not in observed),
        "all_required_images_present": False,
        "image_pull_blocker_remains": True,
    }


def _readiness(observation: dict[str, Any]) -> dict[str, Any]:
    readiness: dict[str, Any] = {
        "diagnostic_landed": True,
        "source_registry_diagnostic_consumed": True,
        "sanitized_docker_context_recorded": True,
        "sanitized_buildx_platform_recorded": True,
        "explicit_platform_retry_recorded": True,
        "docker_context_available": True,
        "buildx_linux_arm64_advertised": True,
        "explicit_platform_pull_still_timed_out": True,
        "remaining_blockers": [
            "docker_pull_still_times_out_without_output",
            "docker_layer_fetch_or_daemon_path_not_explained",
            "required_acontext_images_missing",
            "acontext_compose_services_not_started",
            "local_acontext_api_not_rechecked_reachable",
            "local_acontext_dashboard_not_rechecked_reachable",
            "readiness_gate_not_rebuilt_empty",
        ],
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _operator_next_actions() -> list[dict[str, Any]]:
    return [
        {
            "step_id": "fix_or_bypass_docker_layer_pull_path",
            "action": (
                "Resolve the GHCR layer pull stall through Docker Desktop/network/containerd settings "
                "or use a trusted pre-populated cache/mirror for the required Acontext images."
            ),
            "must_record": ["change_made", "image_source", "credentials_not_recorded", "present_image_count"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "verify_all_required_images_present",
            "action": "Inspect local image inventory and require all nine Acontext compose images before startup.",
            "must_record": ["required_image_count", "present_required_images", "missing_required_images"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "start_compose_after_inventory_only",
            "action": "Start Acontext compose only after required-image inventory is complete.",
            "must_record": ["compose_command", "service_status", "api_health", "dashboard_health"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "rerun_preflight_and_rebuild_gate",
            "action": "Rerun read-only preflight and rebuild the blocker delta/readiness gate before one parity attempt.",
            "must_record": ["empty_blocker_gate", "write_allowed", "retrieve_allowed"],
            "authorizes_live_attempt": "only_if_gate_empty",
        },
    ]


def _assert_source_registry_diagnostic_still_blocked(source: dict[str, Any]) -> None:
    if source.get("diagnostic_verdict") != "registry_manifests_available_but_docker_pull_still_stalls":
        raise CityOpsContractError("source registry diagnostic must still be a Docker pull stall")
    readiness = source.get("readiness", {})
    if readiness.get("all_required_images_present") is not False:
        raise CityOpsContractError("source registry diagnostic unexpectedly has all images")
    if readiness.get("compose_services_started") is not False:
        raise CityOpsContractError("source registry diagnostic unexpectedly started services")
    if readiness.get("runtime_parity_proven") is not False:
        raise CityOpsContractError("source registry diagnostic unexpectedly proves runtime parity")


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
            raise CityOpsContractError(f"Docker pull-path diagnostic must not include {field}")
    context = observation.get("docker_context_observation", {})
    if context.get("current_context") != "desktop-linux":
        raise CityOpsContractError("Docker pull-path diagnostic expects desktop-linux context")
    if context.get("server_arch") != "aarch64":
        raise CityOpsContractError("Docker pull-path diagnostic expects arm64/aarch64 Docker server")
    if observation.get("buildx_observation", {}).get("advertised_platforms_include_linux_arm64") is not True:
        raise CityOpsContractError("Docker pull-path diagnostic expects buildx linux/arm64 support")
    retry = observation.get("explicit_platform_pull_retry", {})
    if retry.get("image") != "ghcr.io/memodb-io/acontext-ui:latest":
        raise CityOpsContractError("Docker pull-path diagnostic must retry the first required GHCR image")
    if retry.get("platform") != "linux/arm64":
        raise CityOpsContractError("Docker pull-path diagnostic must use explicit linux/arm64 platform")
    if retry.get("timed_out") is not True or retry.get("pulled_or_present_after_retry") is not False:
        raise CityOpsContractError("explicit platform retry must remain timed out and not pulled")
    if observation.get("local_images_observed_after_diagnostic") != ["pgvector/pgvector:pg16"]:
        raise CityOpsContractError("Docker pull-path diagnostic expects only pgvector observed locally")
    if observation.get("services_started") is not False:
        raise CityOpsContractError("Docker pull-path diagnostic cannot record started services")
    if observation.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("Docker pull-path diagnostic cannot record live Acontext write")
    if observation.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("Docker pull-path diagnostic cannot record live Acontext retrieval")
    if observation.get("readiness_gate_rebuilt_with_empty_blockers") is not False:
        raise CityOpsContractError("Docker pull-path diagnostic cannot record empty readiness gate")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"Docker pull-path diagnostic claim boundary overlap: {sorted(overlap)}")
    if ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("Docker pull-path diagnostic safe claim missing")
    for claim in DOCKER_PULL_PATH_DIAGNOSTIC_BLOCKED_CLAIMS:
        if claim not in do_not_claim_yet:
            raise CityOpsContractError(f"Docker pull-path diagnostic blocked claim missing: {claim}")


def _assert_diagnostic_conservative(diagnostic: dict[str, Any]) -> None:
    if diagnostic.get("schema") != ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_SCHEMA:
        raise CityOpsContractError("unexpected Docker pull-path diagnostic schema")
    for section in ("derived_from", "access_policy"):
        payload = diagnostic[section]
        for key, value in payload.items():
            if isinstance(value, bool) and key not in {"read_only", "requires_admin_context"}:
                if value is not False:
                    raise CityOpsContractError(f"Docker pull-path diagnostic {section}.{key} must remain false")
    readiness = diagnostic["readiness"]
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"Docker pull-path diagnostic readiness promoted: {flag}")
    if diagnostic["docker_context_summary"]["context_availability_is_not_pull_success"] is not True:
        raise CityOpsContractError("Docker context availability cannot prove pull success")
    if diagnostic["explicit_platform_retry_summary"]["explicit_platform_retry_blocker_remains"] is not True:
        raise CityOpsContractError("Docker pull-path diagnostic must preserve explicit-platform blocker")
    if diagnostic["image_inventory"]["all_required_images_present"] is not False:
        raise CityOpsContractError("Docker pull-path diagnostic cannot mark all images present")
    if diagnostic.get("diagnostic_verdict") != "docker_context_available_but_explicit_platform_pull_still_stalls":
        raise CityOpsContractError("unexpected Docker pull-path diagnostic verdict")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
