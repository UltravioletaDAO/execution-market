"""Acontext Docker-daemon recovery observation for City-as-a-Service.

This artifact records the May 28 07:00 dream-session runtime prerequisite
truth check.  The local Docker daemon was started and Buildx became healthy,
which clears the first prerequisite gate as an observation.  It deliberately
stops before Compose/service startup: no Acontext images are present, no
Acontext containers are running, the API/dashboard are unreachable, no live
Acontext write/retrieve occurred, and no runtime parity or customer/public
readiness is promoted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_next_truth_selector import (
    AAS_NEXT_TRUTH_SELECTOR_FILENAME,
    AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
    AAS_NEXT_TRUTH_SELECTOR_SCHEMA,
    SELECTED_NEXT_TRACK,
    SELECTOR_BLOCKED_CLAIMS,
    SELECTOR_VERDICT,
    load_aas_next_truth_selector,
)
from .aas_system_integration_runtime_truth_queue import (
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME,
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SCHEMA,
    RUNTIME_TRUTH_QUEUE_BLOCKED_CLAIMS,
    RUNTIME_TRUTH_QUEUE_VERDICT,
    load_aas_system_integration_runtime_truth_queue,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA = (
    "city_ops.acontext_docker_daemon_recovery_observation.v1"
)
ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME = (
    "acontext_docker_daemon_recovery_observation.json"
)
ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM = (
    "admin_acontext_docker_daemon_recovery_observation_landed"
)

RECOVERY_OBSERVATION_ID = (
    "execution_market.aas.acontext_docker_daemon_recovery_observation.2026_05_28_0700"
)
RECOVERY_OBSERVATION_SCOPE = (
    "internal_admin_runtime_prerequisite_observation_only_no_compose_or_live_parity"
)
RECOVERY_OBSERVATION_VERDICT = (
    "docker_daemon_recovered_but_acontext_services_and_runtime_parity_still_blocked"
)

RECOVERY_OBSERVATION_BLOCKED_CLAIMS = [
    *RUNTIME_TRUTH_QUEUE_BLOCKED_CLAIMS,
    *SELECTOR_BLOCKED_CLAIMS,
    "docker_daemon_recovery_observation_started_compose_services",
    "docker_daemon_recovery_observation_pulled_required_acontext_images",
    "docker_daemon_recovery_observation_verified_required_images_present",
    "docker_daemon_recovery_observation_reached_acontext_api_or_dashboard",
    "docker_daemon_recovery_observation_rebuilt_empty_readiness_gate",
    "docker_daemon_recovery_observation_authorized_live_parity_attempt",
    "docker_daemon_recovery_observation_completed_live_acontext_write",
    "docker_daemon_recovery_observation_completed_live_acontext_retrieval",
    "docker_daemon_recovery_observation_proved_runtime_parity",
    "docker_daemon_recovery_observation_changes_irc_runtime_session_manager",
    "docker_daemon_recovery_observation_enables_cross_project_autorouting",
    "docker_daemon_recovery_observation_authorizes_customer_copy_delivery_or_publication",
    "docker_daemon_recovery_observation_authorizes_public_or_catalog_route",
    "docker_daemon_recovery_observation_authorizes_pricing_or_customer_quote",
    "docker_daemon_recovery_observation_authorizes_queue_launch_or_dispatch",
    "docker_daemon_recovery_observation_authorizes_erc8004_reputation_or_worker_skill_dna",
    "docker_daemon_recovery_observation_reverifies_payment_or_production",
    "docker_daemon_recovery_observation_allows_exact_gps_or_raw_metadata",
    "docker_daemon_recovery_observation_grants_domain_or_emergency_authority",
    "docker_daemon_recovery_observation_creates_worker_copyable_doctrine",
]

_FALSE_ACCESS_FLAGS = {
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "changes_irc_runtime_session_manager": False,
    "enables_cross_project_autorouting": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "publishes_worker_doctrine": False,
}


def build_may28_0700_docker_daemon_recovery_observation() -> dict[str, Any]:
    """Return the sanitized 7 AM observed runtime-prerequisite facts."""

    return {
        "observation_window": "2026-05-28T07:00:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": "runtime_truth_prerequisite_activation_after_next_truth_selector",
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "commands_observed": [
            "docker context show",
            "docker version --format client/server/os",
            "docker buildx ls | head -8",
            "docker images --format repository:tag/id/size | grep acontext-related patterns",
            "docker ps --format names/status/ports | grep -i acontext",
            "curl --max-time 2 http://localhost:8029/api/v1/health",
            "curl --max-time 2 -I http://localhost:3000",
        ],
        "docker": {
            "context": "desktop-linux",
            "desktop_app_present": True,
            "daemon_start_attempted": True,
            "daemon_available": True,
            "client_version": "29.1.3",
            "server_version": "29.1.3",
            "server_os_arch": "linux/arm64",
            "socket_error_class_after_start": None,
        },
        "buildx": {
            "checked": True,
            "default_builder_status": "running",
            "desktop_linux_builder_status": "running",
            "buildkit_version_observed": "v0.26.2",
            "platforms_include_linux_arm64": True,
            "platforms_include_linux_amd64": True,
        },
        "image_inventory": {
            "checked": True,
            "required_image_count_known_from_prior_diagnostic": True,
            "acontext_related_images_present": False,
            "required_images_present": False,
            "missing_reason": "no_local_acontext_related_images_found_after_daemon_recovery",
        },
        "containers": {
            "checked": True,
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
        "readiness_gate_rebuilt_with_empty_blockers": False,
        "one_live_parity_attempt_authorized": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_docker_daemon_recovery_observation(
    *,
    artifact_dir: str | Path | None = None,
    runtime_queue: dict[str, Any] | None = None,
    next_truth_selector: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic Docker-daemon recovery observation."""

    queue = runtime_queue or load_aas_system_integration_runtime_truth_queue(
        artifact_dir=artifact_dir
    )
    selector = next_truth_selector or load_aas_next_truth_selector(artifact_dir=artifact_dir)
    observed = observation or build_may28_0700_docker_daemon_recovery_observation()
    _assert_runtime_queue_source(queue)
    _assert_next_truth_selector_source(selector)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *queue["claim_boundaries"]["safe_to_claim"],
            *selector["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM,
            AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
            ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *queue["claim_boundaries"]["do_not_claim_yet"],
            *selector["claim_boundaries"]["do_not_claim_yet"],
            *RECOVERY_OBSERVATION_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA,
        "observation_id": RECOVERY_OBSERVATION_ID,
        "scope": RECOVERY_OBSERVATION_SCOPE,
        "source_artifacts": {
            "runtime_truth_queue": {
                "file": AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME,
                "schema": queue["schema"],
                "id": queue["queue_id"],
                "safe_claim": AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(queue),
                "queue_verdict": queue["queue_verdict"],
            },
            "next_truth_selector": {
                "file": AAS_NEXT_TRUTH_SELECTOR_FILENAME,
                "schema": selector["schema"],
                "id": selector["selector_id"],
                "safe_claim": AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
                "digest_sha256": _stable_digest(selector),
                "selector_verdict": selector["selector_verdict"],
                "selected_next_track": selector["selected_next_track"],
            },
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [
                AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME,
                AAS_NEXT_TRUTH_SELECTOR_FILENAME,
            ],
            "runtime_observation_performed": True,
            "starts_docker_desktop": True,
            "pulls_container_images": False,
            "starts_compose_services": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "changes_irc_runtime_session_manager": False,
            "enables_cross_project_autorouting": False,
            "writes_customer_copy": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **_FALSE_ACCESS_FLAGS,
        },
        "runtime_observation": dict(observed),
        "runtime_truth_gates": _runtime_truth_gates(observed),
        "readiness": _readiness(observed),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_next_actions": _operator_next_actions(observed),
        "observation_verdict": RECOVERY_OBSERVATION_VERDICT,
        "operator_instruction": (
            "Treat this as first-gate runtime truth only: Docker/Buildx recovered, "
            "but required Acontext images, services, API/dashboard health, empty gate, "
            "and live write/retrieve parity are still blocked. Continue with image "
            "inventory/pull and service startup in a separate observation before any "
            "live parity attempt."
        ),
    }
    _assert_artifact_conservative(artifact, queue, selector)
    return artifact


def write_acontext_docker_daemon_recovery_observation(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Docker-daemon recovery observation fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_docker_daemon_recovery_observation(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_docker_daemon_recovery_observation(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Docker-daemon recovery observation."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifact = json.loads(
        (base_dir / ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    queue = load_aas_system_integration_runtime_truth_queue(artifact_dir=base_dir)
    selector = load_aas_next_truth_selector(artifact_dir=base_dir)
    _assert_artifact_conservative(artifact, queue, selector)
    if artifact != build_acontext_docker_daemon_recovery_observation(
        artifact_dir=base_dir,
        runtime_queue=queue,
        next_truth_selector=selector,
        observation=artifact["runtime_observation"],
    ):
        raise CityOpsContractError("Acontext Docker daemon recovery observation drifted")
    return artifact


def _runtime_truth_gates(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "docker_daemon_socket",
            "status": "passed_after_local_daemon_start",
            "passed": observed["docker"]["daemon_available"] is True,
            "evidence": "docker server version observed and Buildx builders running",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "required_image_inventory",
            "status": "blocked_missing_required_images",
            "passed": observed["image_inventory"]["required_images_present"] is True,
            "evidence": observed["image_inventory"]["missing_reason"],
            "authorizes_live_attempt": False,
        },
        {
            "gate": "local_acontext_services",
            "status": "blocked_no_running_acontext_containers_or_health_endpoints",
            "passed": (
                observed["containers"]["acontext_containers_running"] is True
                and observed["api"]["reachable"] is True
                and observed["dashboard"]["reachable"] is True
            ),
            "evidence": "API/dashboard connection refused; no Acontext containers running",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "empty_readiness_gate",
            "status": "blocked_until_services_reachable_and_preflight_rerun",
            "passed": observed["readiness_gate_rebuilt_with_empty_blockers"] is True,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "single_live_write_retrieve_parity_attempt",
            "status": "not_authorized",
            "passed": False,
            "authorizes_live_attempt": False,
        },
    ]


def _readiness(observed: dict[str, Any]) -> dict[str, bool]:
    return {
        "docker_daemon_recovery_observation_landed": True,
        "runtime_truth_source_queue_verified": True,
        "next_truth_selector_verified": True,
        "docker_daemon_available": observed["docker"]["daemon_available"] is True,
        "buildx_builder_available": observed["buildx"]["default_builder_status"] == "running",
        "required_image_inventory_checked": observed["image_inventory"]["checked"] is True,
        "required_images_present": observed["image_inventory"]["required_images_present"] is True,
        "compose_services_started": observed["compose_services_started"] is True,
        "acontext_containers_running": observed["containers"]["acontext_containers_running"] is True,
        "acontext_api_reachable": observed["api"]["reachable"] is True,
        "acontext_dashboard_reachable": observed["dashboard"]["reachable"] is True,
        "readiness_gate_rebuilt_empty": observed["readiness_gate_rebuilt_with_empty_blockers"] is True,
        "one_live_parity_attempt_authorized": observed["one_live_parity_attempt_authorized"] is True,
        "live_acontext_write_performed": observed["live_acontext_write_performed"] is True,
        "live_acontext_retrieval_performed": observed["live_acontext_retrieval_performed"] is True,
        "memory_acontext_parity_ready": False,
        "irc_runtime_session_manager_enhanced": False,
        "cross_project_autorouting_ready": False,
        "customer_copy_ready": False,
        "customer_delivery_ready": False,
        "publication_ready": False,
        "public_or_catalog_route_ready": False,
        "pricing_or_customer_quote_ready": False,
        "operator_queue_launch_ready": False,
        "dispatch_ready": False,
        "payment_or_production_reverified": False,
        "erc8004_reputation_ready": False,
        "worker_skill_dna_ready": False,
        "exact_gps_or_raw_metadata_release_ready": False,
        "domain_authority_ready": False,
        "worker_copyable_doctrine_ready": False,
    }


def _operator_next_actions(observed: dict[str, Any]) -> list[str]:
    if observed["image_inventory"]["required_images_present"] is not True:
        return [
            "Complete a trusted Acontext image inventory/pull/cache path while Docker is running.",
            "Only after required images are present, start the local Acontext Compose services and verify API/dashboard health.",
            "Only after API/dashboard health is green, rerun the read-only live preflight and rebuild the blocker delta/read surface/gate.",
            "Attempt exactly one bounded live write/retrieve parity pass only if the rebuilt gate has no blockers and explicitly authorizes it.",
        ]
    return [
        "Start local Acontext Compose services and verify API/dashboard health before any live parity attempt."
    ]


def _assert_runtime_queue_source(queue: dict[str, Any]) -> None:
    if queue.get("schema") != AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SCHEMA:
        raise CityOpsContractError("invalid runtime truth queue schema")
    if queue.get("queue_verdict") != RUNTIME_TRUTH_QUEUE_VERDICT:
        raise CityOpsContractError("runtime truth queue verdict drift")
    if AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM not in queue.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("runtime truth queue missing safe claim")
    for flag in [
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "memory_acontext_parity_ready",
    ]:
        if queue.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"runtime truth queue promoted readiness: {flag}")
    _assert_claim_boundaries(
        queue.get("claim_boundaries", {}).get("safe_to_claim", []),
        queue.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_next_truth_selector_source(selector: dict[str, Any]) -> None:
    if selector.get("schema") != AAS_NEXT_TRUTH_SELECTOR_SCHEMA:
        raise CityOpsContractError("invalid next-truth selector schema")
    if selector.get("selector_verdict") != SELECTOR_VERDICT:
        raise CityOpsContractError("next-truth selector verdict drift")
    if selector.get("selected_next_track") != SELECTED_NEXT_TRACK:
        raise CityOpsContractError("next-truth selector selected wrong track")
    if AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM not in selector.get("claim_boundaries", {}).get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("next-truth selector missing safe claim")
    for flag in [
        "ready_to_attempt_live_transport",
        "live_acontext_write_allowed",
        "live_acontext_retrieve_allowed",
        "runtime_parity_proven",
    ]:
        if selector.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"next-truth selector promoted readiness: {flag}")
    _assert_claim_boundaries(
        selector.get("claim_boundaries", {}).get("safe_to_claim", []),
        selector.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    docker = observed.get("docker", {})
    buildx = observed.get("buildx", {})
    image_inventory = observed.get("image_inventory", {})
    containers = observed.get("containers", {})
    api = observed.get("api", {})
    dashboard = observed.get("dashboard", {})
    if docker.get("daemon_available") is not True:
        raise CityOpsContractError("Docker daemon recovery observation must record daemon availability")
    if buildx.get("default_builder_status") != "running":
        raise CityOpsContractError("Buildx builder must be running after daemon recovery")
    if image_inventory.get("checked") is not True:
        raise CityOpsContractError("image inventory must be checked after daemon recovery")
    if image_inventory.get("required_images_present") is True and image_inventory.get(
        "acontext_related_images_present"
    ) is not True:
        raise CityOpsContractError("required images cannot be present without Acontext image evidence")
    if observed.get("compose_services_started") is True and image_inventory.get(
        "required_images_present"
    ) is not True:
        raise CityOpsContractError("compose services cannot start before required images are present")
    if containers.get("acontext_containers_running") is True and observed.get(
        "compose_services_started"
    ) is not True:
        raise CityOpsContractError("containers cannot run before compose services start")
    if (api.get("reachable") is True or dashboard.get("reachable") is True) and containers.get(
        "acontext_containers_running"
    ) is not True:
        raise CityOpsContractError("API/dashboard cannot be reachable without Acontext containers")
    if observed.get("readiness_gate_rebuilt_with_empty_blockers") is True and not (
        api.get("reachable") is True and dashboard.get("reachable") is True
    ):
        raise CityOpsContractError("empty gate cannot be rebuilt before API/dashboard are reachable")
    if observed.get("one_live_parity_attempt_authorized") is True:
        raise CityOpsContractError("observation must not authorize live parity")
    if observed.get("live_acontext_write_performed") is True:
        raise CityOpsContractError("observation must not perform live write")
    if observed.get("live_acontext_retrieval_performed") is True:
        raise CityOpsContractError("observation must not perform live retrieval")


def _assert_artifact_conservative(
    artifact: dict[str, Any], queue: dict[str, Any], selector: dict[str, Any]
) -> None:
    if artifact.get("schema") != ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA:
        raise CityOpsContractError("invalid Docker daemon recovery observation schema")
    _assert_runtime_queue_source(queue)
    _assert_next_truth_selector_source(selector)
    _assert_observation_conservative(artifact.get("runtime_observation", {}))
    if artifact.get("observation_verdict") != RECOVERY_OBSERVATION_VERDICT:
        raise CityOpsContractError("Docker daemon recovery observation verdict drift")
    readiness = artifact.get("readiness", {})
    for flag in [
        "compose_services_started",
        "acontext_containers_running",
        "acontext_api_reachable",
        "acontext_dashboard_reachable",
        "readiness_gate_rebuilt_empty",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "memory_acontext_parity_ready",
        "customer_delivery_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "exact_gps_or_raw_metadata_release_ready",
        "domain_authority_ready",
        "worker_copyable_doctrine_ready",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"promoted readiness: {flag}")
    if readiness.get("docker_daemon_available") is not True:
        raise CityOpsContractError("Docker daemon availability was not recorded")
    if readiness.get("buildx_builder_available") is not True:
        raise CityOpsContractError("Buildx availability was not recorded")
    gates = artifact.get("runtime_truth_gates", [])
    if [gate.get("gate") for gate in gates] != [
        "docker_daemon_socket",
        "required_image_inventory",
        "local_acontext_services",
        "empty_readiness_gate",
        "single_live_write_retrieve_parity_attempt",
    ]:
        raise CityOpsContractError("runtime gate order drift")
    if gates[0].get("passed") is not True:
        raise CityOpsContractError("Docker gate should be the only passed runtime gate")
    if any(gate.get("passed") is True for gate in gates[1:]):
        raise CityOpsContractError("later runtime gates must remain blocked")
    if any(gate.get("authorizes_live_attempt") is True for gate in gates):
        raise CityOpsContractError("observation must not authorize live attempt")
    derived = artifact.get("derived_from", {})
    for flag in [
        "pulls_container_images",
        "starts_compose_services",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "changes_irc_runtime_session_manager",
        "enables_cross_project_autorouting",
        "writes_customer_copy",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        if derived.get(flag) is not False:
            raise CityOpsContractError(f"derived action promoted: {flag}")
    _assert_claim_boundaries(
        artifact.get("claim_boundaries", {}).get("safe_to_claim", []),
        artifact.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim overlap: {sorted(overlap)}")


def _stable_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
