"""Acontext required-image pull retry observation for City-as-a-Service.

This artifact records the May 28 22:11 EDT bounded retry after Docker/Buildx
recovered locally.  It attempts exactly one required Acontext image pull and
keeps the gate blocked when the retry times out with no local image present.

It does not start Compose services, does not write to or retrieve from
Acontext, does not rebuild the readiness gate, and does not promote customer,
public, dispatch, reputation, payment, production, GPS/raw metadata, authority,
or worker-copyable doctrine claims.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_docker_daemon_recovery_observation import (
    ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME,
    ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA,
    RECOVERY_OBSERVATION_VERDICT,
    load_acontext_docker_daemon_recovery_observation,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SCHEMA = (
    "city_ops.acontext_required_image_pull_retry_observation.v1"
)
ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_FILENAME = (
    "acontext_required_image_pull_retry_observation.json"
)
ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM = (
    "admin_acontext_required_image_pull_retry_observation_landed"
)

PULL_RETRY_OBSERVATION_ID = (
    "execution_market.aas.acontext_required_image_pull_retry_observation."
    "2026_05_28_2211"
)
PULL_RETRY_OBSERVATION_SCOPE = (
    "internal_admin_required_image_pull_retry_only_no_compose_or_live_parity"
)
PULL_RETRY_OBSERVATION_VERDICT = (
    "first_required_image_pull_retry_timed_out_required_images_still_blocked"
)

PULL_RETRY_BLOCKED_CLAIMS = [
    "required_image_pull_retry_completed_first_required_image_pull",
    "required_image_pull_retry_cached_first_required_image",
    "required_image_pull_retry_cached_all_required_images",
    "required_image_pull_retry_started_compose_services",
    "required_image_pull_retry_reached_acontext_api",
    "required_image_pull_retry_reached_acontext_dashboard",
    "required_image_pull_retry_rebuilt_empty_readiness_gate",
    "required_image_pull_retry_authorized_live_parity_attempt",
    "required_image_pull_retry_completed_live_acontext_write",
    "required_image_pull_retry_completed_live_acontext_retrieval",
    "required_image_pull_retry_proved_runtime_parity",
    "required_image_pull_retry_changes_irc_runtime_session_manager",
    "required_image_pull_retry_enables_cross_project_autorouting",
    "required_image_pull_retry_authorizes_customer_copy_delivery_or_publication",
    "required_image_pull_retry_authorizes_public_or_catalog_route",
    "required_image_pull_retry_authorizes_pricing_or_customer_quote",
    "required_image_pull_retry_authorizes_queue_launch_or_dispatch",
    "required_image_pull_retry_authorizes_erc8004_reputation_or_worker_skill_dna",
    "required_image_pull_retry_reverifies_payment_or_production",
    "required_image_pull_retry_allows_exact_gps_or_raw_metadata",
    "required_image_pull_retry_grants_domain_or_emergency_authority",
    "required_image_pull_retry_creates_worker_copyable_doctrine",
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


def build_may28_2211_required_image_pull_retry_observation() -> dict[str, Any]:
    """Return the sanitized current required-image retry facts."""

    return {
        "observation_window": "2026-05-28T22:11:17-04:00/2026-05-28T22:14:17-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": "continue_runtime_truth_prerequisite_activation_after_docker_recovery",
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "commands_observed": [
            "docker image inspect ghcr.io/memodb-io/acontext-ui:latest",
            "docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest",
            "docker images --format repository:tag/id/size | grep required image names",
            "curl --max-time 2 http://localhost:8029/api/v1/health",
            "curl --max-time 2 -I http://localhost:3000",
        ],
        "docker": {
            "context": "desktop-linux",
            "daemon_available": True,
            "client_version": "29.1.3",
            "server_version": "29.1.3",
            "server_os_arch": "linux/arm64",
        },
        "required_images": {
            "source": "acontext_compose_image_pull_attempt_log.REQUIRED_ACONTEXT_IMAGES",
            "all": list(REQUIRED_ACONTEXT_IMAGES),
            "present_before_retry": ["pgvector/pgvector:pg16"],
            "missing_before_retry": [
                image for image in REQUIRED_ACONTEXT_IMAGES if image != "pgvector/pgvector:pg16"
            ],
        },
        "pull_retry": {
            "image": "ghcr.io/memodb-io/acontext-ui:latest",
            "platform": "linux/arm64",
            "timeout_seconds": 180,
            "duration_seconds": 180.01,
            "timed_out": True,
            "exit_code": None,
            "stdout_tail": [],
            "stderr_tail": [],
            "present_after_attempt": False,
        },
        "image_inventory_after_retry": {
            "checked": True,
            "present_required_images": ["pgvector/pgvector:pg16"],
            "missing_required_images": [
                image for image in REQUIRED_ACONTEXT_IMAGES if image != "pgvector/pgvector:pg16"
            ],
            "all_required_images_present": False,
        },
        "containers": {
            "checked": True,
            "acontext_containers_running": False,
        },
        "api": {
            "checked": True,
            "url": "http://localhost:8029/api/v1/health",
            "reachable": False,
            "error_class": "connection_failed_or_connection_refused",
        },
        "dashboard": {
            "checked": True,
            "url": "http://localhost:3000",
            "reachable": False,
            "error_class": "connection_failed_or_connection_refused",
        },
        "compose_services_started": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
        "one_live_parity_attempt_authorized": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_required_image_pull_retry_observation(
    *,
    artifact_dir: str | Path | None = None,
    daemon_recovery_observation: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic required-image pull retry observation."""

    source = daemon_recovery_observation or load_acontext_docker_daemon_recovery_observation(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may28_2211_required_image_pull_retry_observation()
    _assert_daemon_recovery_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM,
            ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *PULL_RETRY_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SCHEMA,
        "observation_id": PULL_RETRY_OBSERVATION_ID,
        "scope": PULL_RETRY_OBSERVATION_SCOPE,
        "source_artifacts": {
            "docker_daemon_recovery_observation": {
                "file": ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_FILENAME],
            "runtime_observation_performed": True,
            "pulls_one_container_image": True,
            "pull_completed": False,
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
        "operator_next_actions": _operator_next_actions(),
        "observation_verdict": PULL_RETRY_OBSERVATION_VERDICT,
        "operator_instruction": (
            "Treat this as a bounded image-pull retry only: Docker stayed available, "
            "but the first required Acontext image timed out and is not cached. Do not "
            "start Compose, rebuild readiness, or attempt live parity until required "
            "images are actually present."
        ),
    }
    _assert_artifact_conservative(artifact, source)
    return artifact


def write_acontext_required_image_pull_retry_observation(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic required-image pull retry observation fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_required_image_pull_retry_observation(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_FILENAME
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_required_image_pull_retry_observation(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted required-image pull retry observation."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifact = json.loads(
        (base_dir / ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source = load_acontext_docker_daemon_recovery_observation(artifact_dir=base_dir)
    _assert_artifact_conservative(artifact, source)
    if artifact != build_acontext_required_image_pull_retry_observation(
        artifact_dir=base_dir,
        daemon_recovery_observation=source,
        observation=artifact["runtime_observation"],
    ):
        raise CityOpsContractError("Acontext required-image pull retry observation drifted")
    return artifact


def _runtime_truth_gates(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "docker_daemon_socket",
            "status": "passed_from_daemon_recovery_observation",
            "passed": observed["docker"]["daemon_available"] is True,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "first_required_image_pull_retry",
            "status": "blocked_retry_timed_out_image_not_present",
            "passed": observed["pull_retry"]["present_after_attempt"] is True,
            "evidence": "pull timed out after bounded window with no local image present",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "all_required_images_present",
            "status": "blocked_missing_required_images",
            "passed": observed["image_inventory_after_retry"]["all_required_images_present"] is True,
            "evidence": observed["image_inventory_after_retry"]["missing_required_images"],
            "authorizes_live_attempt": False,
        },
        {
            "gate": "local_acontext_services",
            "status": "blocked_no_running_acontext_containers_or_health_endpoints",
            "passed": False,
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
        "required_image_pull_retry_observation_landed": True,
        "docker_daemon_recovery_source_verified": True,
        "docker_daemon_available": observed["docker"]["daemon_available"] is True,
        "first_required_image_pull_attempted": True,
        "first_required_image_present": observed["pull_retry"]["present_after_attempt"] is True,
        "all_required_images_present": observed["image_inventory_after_retry"][
            "all_required_images_present"
        ]
        is True,
        "compose_services_started": observed["compose_services_started"] is True,
        "acontext_containers_running": observed["containers"]["acontext_containers_running"] is True,
        "acontext_api_reachable": observed["api"]["reachable"] is True,
        "acontext_dashboard_reachable": observed["dashboard"]["reachable"] is True,
        "readiness_gate_rebuilt_empty": observed["readiness_gate_rebuilt_with_empty_blockers"]
        is True,
        "one_live_parity_attempt_authorized": observed["one_live_parity_attempt_authorized"]
        is True,
        "live_acontext_write_performed": observed["live_acontext_write_performed"] is True,
        "live_acontext_retrieval_performed": observed["live_acontext_retrieval_performed"]
        is True,
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


def _operator_next_actions() -> list[str]:
    return [
        "Resolve the GHCR/layer pull stall for ghcr.io/memodb-io/acontext-ui:latest or provide a trusted preloaded image cache.",
        "Repeat the required-image inventory only after the first image is present locally.",
        "Start local Acontext Compose services only after all required images are present.",
        "Rerun the read-only live preflight and rebuild blocker delta/read surface/gate only after API/dashboard health is green.",
        "Attempt exactly one bounded live write/retrieve parity pass only if the rebuilt gate explicitly authorizes it.",
    ]


def _assert_daemon_recovery_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SCHEMA:
        raise CityOpsContractError("invalid Docker daemon recovery observation schema")
    if source.get("observation_verdict") != RECOVERY_OBSERVATION_VERDICT:
        raise CityOpsContractError("Docker daemon recovery observation verdict drift")
    if ACONTEXT_DOCKER_DAEMON_RECOVERY_OBSERVATION_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Docker daemon recovery observation missing safe claim")
    readiness = source.get("readiness", {})
    if readiness.get("docker_daemon_available") is not True:
        raise CityOpsContractError("source did not prove Docker daemon availability")
    for flag in [
        "required_images_present",
        "compose_services_started",
        "acontext_api_reachable",
        "acontext_dashboard_reachable",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "memory_acontext_parity_ready",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"source promoted later readiness: {flag}")
    _assert_claim_boundaries(
        source.get("claim_boundaries", {}).get("safe_to_claim", []),
        source.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    required = observed.get("required_images", {})
    retry = observed.get("pull_retry", {})
    inventory = observed.get("image_inventory_after_retry", {})
    if observed.get("docker", {}).get("daemon_available") is not True:
        raise CityOpsContractError("Docker daemon must remain available during image retry")
    if retry.get("image") != "ghcr.io/memodb-io/acontext-ui:latest":
        raise CityOpsContractError("unexpected image selected for bounded pull retry")
    if retry.get("timed_out") is not True:
        raise CityOpsContractError("pull retry observation must record timeout")
    if retry.get("present_after_attempt") is not False:
        raise CityOpsContractError("pull retry must not claim image presence")
    if "pgvector/pgvector:pg16" not in required.get("present_before_retry", []):
        raise CityOpsContractError("inventory must preserve the one observed local required image")
    if retry.get("image") not in required.get("missing_before_retry", []):
        raise CityOpsContractError("retried image must have been missing before retry")
    if inventory.get("all_required_images_present") is not False:
        raise CityOpsContractError("all required images must remain blocked")
    if retry.get("image") not in inventory.get("missing_required_images", []):
        raise CityOpsContractError("retried image must remain missing after timeout")
    if observed.get("compose_services_started") is not False:
        raise CityOpsContractError("image retry must not start Compose services")
    if observed.get("containers", {}).get("acontext_containers_running") is not False:
        raise CityOpsContractError("image retry must not start containers")
    if observed.get("api", {}).get("reachable") is not False:
        raise CityOpsContractError("image retry must not reach Acontext API")
    if observed.get("dashboard", {}).get("reachable") is not False:
        raise CityOpsContractError("image retry must not reach Acontext dashboard")
    for flag in [
        "readiness_gate_rebuilt_with_empty_blockers",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]:
        if observed.get(flag) is not False:
            raise CityOpsContractError(f"image retry promoted forbidden runtime flag: {flag}")


def _assert_artifact_conservative(artifact: dict[str, Any], source: dict[str, Any]) -> None:
    if artifact.get("schema") != ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SCHEMA:
        raise CityOpsContractError("invalid required-image pull retry observation schema")
    _assert_daemon_recovery_source(source)
    _assert_observation_conservative(artifact.get("runtime_observation", {}))
    if artifact.get("observation_verdict") != PULL_RETRY_OBSERVATION_VERDICT:
        raise CityOpsContractError("required-image pull retry verdict drift")
    readiness = artifact.get("readiness", {})
    for flag in [
        "first_required_image_present",
        "all_required_images_present",
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
    gates = artifact.get("runtime_truth_gates", [])
    if [gate.get("gate") for gate in gates] != [
        "docker_daemon_socket",
        "first_required_image_pull_retry",
        "all_required_images_present",
        "local_acontext_services",
        "single_live_write_retrieve_parity_attempt",
    ]:
        raise CityOpsContractError("runtime gate order drift")
    if gates[0].get("passed") is not True:
        raise CityOpsContractError("Docker gate should remain passed")
    if any(gate.get("passed") is True for gate in gates[1:]):
        raise CityOpsContractError("image/service/parity gates must remain blocked")
    if any(gate.get("authorizes_live_attempt") is True for gate in gates):
        raise CityOpsContractError("image retry must not authorize live attempt")
    derived = artifact.get("derived_from", {})
    if derived.get("pulls_one_container_image") is not True:
        raise CityOpsContractError("artifact must record the bounded pull attempt")
    for flag in [
        "pull_completed",
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
