"""Acontext extended required-image pull timeout observation for City-as-a-Service.

This artifact records the May 28 23:03 EDT longer bounded retry after the
first required Acontext image had already timed out once.  GHCR anonymous
manifest fetches still succeed and advertise linux/arm64 images, but Docker
Desktop does not complete the first image pull inside a ten-minute window and
no Acontext image is cached locally afterward.

It is internal/admin runtime-prerequisite evidence only.  It does not start
Compose services, does not write to or retrieve from Acontext, does not rebuild
the readiness gate, and does not promote customer, public, dispatch,
reputation, payment, production, GPS/raw metadata, authority, or
worker-copyable doctrine claims.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_required_image_pull_retry_observation import (
    ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_FILENAME,
    ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SCHEMA,
    PULL_RETRY_BLOCKED_CLAIMS,
    PULL_RETRY_OBSERVATION_VERDICT,
    load_acontext_required_image_pull_retry_observation,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA = (
    "city_ops.acontext_required_image_extended_pull_timeout_observation.v1"
)
ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME = (
    "acontext_required_image_extended_pull_timeout_observation.json"
)
ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM = (
    "admin_acontext_required_image_extended_pull_timeout_observation_landed"
)

EXTENDED_PULL_TIMEOUT_OBSERVATION_ID = (
    "execution_market.aas.acontext_required_image_extended_pull_timeout_observation."
    "2026_05_28_2303"
)
EXTENDED_PULL_TIMEOUT_SCOPE = (
    "internal_admin_extended_required_image_pull_timeout_only_no_compose_or_live_parity"
)
EXTENDED_PULL_TIMEOUT_VERDICT = (
    "first_required_image_extended_pull_timed_out_manifest_reachable_image_still_missing"
)

EXTENDED_PULL_TIMEOUT_BLOCKED_CLAIMS = [
    *PULL_RETRY_BLOCKED_CLAIMS,
    "extended_pull_timeout_manifest_success_implies_image_cached",
    "extended_pull_timeout_resolves_docker_desktop_pull_stall",
    "extended_pull_timeout_cached_first_required_image",
    "extended_pull_timeout_cached_all_required_images",
    "extended_pull_timeout_started_compose_services",
    "extended_pull_timeout_reached_acontext_api",
    "extended_pull_timeout_reached_acontext_dashboard",
    "extended_pull_timeout_rebuilt_empty_readiness_gate",
    "extended_pull_timeout_authorized_live_parity_attempt",
    "extended_pull_timeout_completed_live_acontext_write",
    "extended_pull_timeout_completed_live_acontext_retrieval",
    "extended_pull_timeout_proved_runtime_parity",
    "extended_pull_timeout_authorizes_customer_copy_delivery_or_publication",
    "extended_pull_timeout_authorizes_public_or_catalog_route",
    "extended_pull_timeout_authorizes_pricing_or_customer_quote",
    "extended_pull_timeout_authorizes_queue_launch_or_dispatch",
    "extended_pull_timeout_authorizes_erc8004_reputation_or_worker_skill_dna",
    "extended_pull_timeout_reverifies_payment_or_production",
    "extended_pull_timeout_allows_exact_gps_or_raw_metadata",
    "extended_pull_timeout_grants_domain_or_emergency_authority",
    "extended_pull_timeout_creates_worker_copyable_doctrine",
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


def build_may28_2303_extended_pull_timeout_observation() -> dict[str, Any]:
    """Return the sanitized May 28 23:03 extended pull timeout facts."""

    return {
        "observation_window": "2026-05-28T23:03:02-04:00/2026-05-28T23:13:02-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": "verify_whether_longer_bounded_pull_unblocks_first_required_acontext_image",
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "commands_observed": [
            "GHCR anonymous token + manifest fetch for acontext-ui/api/core",
            "docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest",
            "docker image inspect ghcr.io/memodb-io/acontext-ui:latest",
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
            "docker_desktop_version": "4.57.0",
        },
        "ghcr_manifest_checks": [
            {
                "image": "ghcr.io/memodb-io/acontext-ui:latest",
                "anonymous_bearer_token_received": True,
                "manifest_http_status": 200,
                "media_type": "application/vnd.oci.image.index.v1+json",
                "platforms": ["linux/amd64", "linux/arm64", "unknown/unknown"],
                "linux_arm64_manifest_advertised": True,
                "manifest_fetch_succeeded": True,
            },
            {
                "image": "ghcr.io/memodb-io/acontext-api:latest",
                "anonymous_bearer_token_received": True,
                "manifest_http_status": 200,
                "media_type": "application/vnd.oci.image.index.v1+json",
                "platforms": ["linux/amd64", "linux/arm64", "unknown/unknown"],
                "linux_arm64_manifest_advertised": True,
                "manifest_fetch_succeeded": True,
            },
            {
                "image": "ghcr.io/memodb-io/acontext-core:latest",
                "anonymous_bearer_token_received": True,
                "manifest_http_status": 200,
                "media_type": "application/vnd.oci.image.index.v1+json",
                "platforms": ["linux/amd64", "linux/arm64", "unknown/unknown"],
                "linux_arm64_manifest_advertised": True,
                "manifest_fetch_succeeded": True,
            },
        ],
        "required_images": {
            "source": "acontext_compose_image_pull_attempt_log.REQUIRED_ACONTEXT_IMAGES",
            "all": list(REQUIRED_ACONTEXT_IMAGES),
            "present_before_extended_pull": ["pgvector/pgvector:pg16"],
            "missing_before_extended_pull": [
                image for image in REQUIRED_ACONTEXT_IMAGES if image != "pgvector/pgvector:pg16"
            ],
        },
        "extended_pull": {
            "image": "ghcr.io/memodb-io/acontext-ui:latest",
            "platform": "linux/arm64",
            "timeout_seconds": 600,
            "duration_seconds": 600.01,
            "timed_out": True,
            "exit_code": None,
            "stdout_tail": [],
            "stderr_tail": [],
            "present_after_attempt": False,
        },
        "image_inventory_after_extended_pull": {
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


def build_acontext_required_image_extended_pull_timeout_observation(
    *,
    artifact_dir: str | Path | None = None,
    pull_retry_observation: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic extended required-image pull timeout observation."""

    source = pull_retry_observation or load_acontext_required_image_pull_retry_observation(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may28_2303_extended_pull_timeout_observation()
    _assert_pull_retry_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM,
            ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *EXTENDED_PULL_TIMEOUT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA,
        "observation_id": EXTENDED_PULL_TIMEOUT_OBSERVATION_ID,
        "scope": EXTENDED_PULL_TIMEOUT_SCOPE,
        "source_artifacts": {
            "required_image_pull_retry_observation": {
                "file": ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_FILENAME],
            "runtime_observation_performed": True,
            "checks_registry_manifests": True,
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
        "observation_verdict": EXTENDED_PULL_TIMEOUT_VERDICT,
        "operator_instruction": (
            "Treat this as a longer bounded pull timeout only: GHCR manifests are "
            "reachable and advertise linux/arm64, but Docker Desktop still did not "
            "cache the first required Acontext image. Do not start Compose, rebuild "
            "readiness, or attempt live parity until required images are actually present."
        ),
    }
    _assert_artifact_conservative(artifact, source)
    return artifact


def write_acontext_required_image_extended_pull_timeout_observation(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic extended pull timeout observation fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_required_image_extended_pull_timeout_observation(
        artifact_dir=base_dir
    )
    path = base_dir / ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_required_image_extended_pull_timeout_observation(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted extended pull timeout observation."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifact = json.loads(
        (base_dir / ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source = load_acontext_required_image_pull_retry_observation(artifact_dir=base_dir)
    _assert_artifact_conservative(artifact, source)
    if artifact != build_acontext_required_image_extended_pull_timeout_observation(
        artifact_dir=base_dir,
        pull_retry_observation=source,
        observation=artifact["runtime_observation"],
    ):
        raise CityOpsContractError("Acontext extended pull timeout observation drifted")
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
            "gate": "ghcr_manifest_reachability",
            "status": "passed_but_not_image_cache_or_runtime_readiness",
            "passed": all(
                check["manifest_fetch_succeeded"] is True
                and check["linux_arm64_manifest_advertised"] is True
                for check in observed["ghcr_manifest_checks"]
            ),
            "authorizes_live_attempt": False,
        },
        {
            "gate": "first_required_image_extended_pull",
            "status": "blocked_extended_pull_timed_out_image_not_present",
            "passed": observed["extended_pull"]["present_after_attempt"] is True,
            "evidence": "ten-minute pull timed out with no local image present",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "all_required_images_present",
            "status": "blocked_missing_required_images",
            "passed": observed["image_inventory_after_extended_pull"][
                "all_required_images_present"
            ]
            is True,
            "evidence": observed["image_inventory_after_extended_pull"]["missing_required_images"],
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
        "required_image_extended_pull_timeout_observation_landed": True,
        "required_image_pull_retry_source_verified": True,
        "docker_daemon_available": observed["docker"]["daemon_available"] is True,
        "ghcr_manifests_reachable": all(
            check["manifest_fetch_succeeded"] is True for check in observed["ghcr_manifest_checks"]
        ),
        "linux_arm64_manifests_advertised": all(
            check["linux_arm64_manifest_advertised"] is True
            for check in observed["ghcr_manifest_checks"]
        ),
        "first_required_image_extended_pull_attempted": True,
        "first_required_image_present": observed["extended_pull"]["present_after_attempt"] is True,
        "all_required_images_present": observed["image_inventory_after_extended_pull"][
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
        "Do not repeat blind Docker pulls without changing the pull path; GHCR manifests are reachable but Docker Desktop still stalls before caching the first image.",
        "Try a different trusted cache path next: preloaded tar, registry mirror, Docker Desktop networking reset, or a verified remote builder/cache that can export the image locally.",
        "Repeat required-image inventory only after ghcr.io/memodb-io/acontext-ui:latest is present locally.",
        "Start local Acontext Compose services only after all required images are present.",
        "Rerun read-only live preflight and rebuild blocker delta/read surface/gate only after API/dashboard health is green.",
        "Attempt exactly one bounded live write/retrieve parity pass only if the rebuilt gate explicitly authorizes it.",
    ]


def _assert_pull_retry_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SCHEMA:
        raise CityOpsContractError("invalid required-image pull retry observation schema")
    if source.get("observation_verdict") != PULL_RETRY_OBSERVATION_VERDICT:
        raise CityOpsContractError("required-image pull retry observation verdict drift")
    if ACONTEXT_REQUIRED_IMAGE_PULL_RETRY_OBSERVATION_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("required-image pull retry observation missing safe claim")
    readiness = source.get("readiness", {})
    if readiness.get("docker_daemon_available") is not True:
        raise CityOpsContractError("source did not preserve Docker daemon availability")
    for flag in [
        "first_required_image_present",
        "all_required_images_present",
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
    pull = observed.get("extended_pull", {})
    inventory = observed.get("image_inventory_after_extended_pull", {})
    if observed.get("docker", {}).get("daemon_available") is not True:
        raise CityOpsContractError("Docker daemon must remain available during extended pull")
    checks = observed.get("ghcr_manifest_checks", [])
    if len(checks) != 3:
        raise CityOpsContractError("extended pull observation must preserve three GHCR checks")
    for check in checks:
        if check.get("manifest_fetch_succeeded") is not True:
            raise CityOpsContractError("GHCR manifest check must be explicit")
        if check.get("linux_arm64_manifest_advertised") is not True:
            raise CityOpsContractError("GHCR manifest check must preserve linux/arm64 support")
    if pull.get("image") != "ghcr.io/memodb-io/acontext-ui:latest":
        raise CityOpsContractError("unexpected image selected for extended pull")
    if pull.get("timeout_seconds") != 600:
        raise CityOpsContractError("extended pull must use the ten-minute bounded window")
    if pull.get("timed_out") is not True:
        raise CityOpsContractError("extended pull observation must record timeout")
    if pull.get("present_after_attempt") is not False:
        raise CityOpsContractError("extended pull must not claim image presence")
    if "pgvector/pgvector:pg16" not in required.get("present_before_extended_pull", []):
        raise CityOpsContractError("inventory must preserve the one observed local required image")
    if pull.get("image") not in required.get("missing_before_extended_pull", []):
        raise CityOpsContractError("extended-pull image must have been missing before retry")
    if inventory.get("all_required_images_present") is not False:
        raise CityOpsContractError("all required images must remain blocked")
    if pull.get("image") not in inventory.get("missing_required_images", []):
        raise CityOpsContractError("extended-pull image must remain missing after timeout")
    if observed.get("compose_services_started") is not False:
        raise CityOpsContractError("extended pull must not start Compose services")
    if observed.get("containers", {}).get("acontext_containers_running") is not False:
        raise CityOpsContractError("extended pull must not start containers")
    if observed.get("api", {}).get("reachable") is not False:
        raise CityOpsContractError("extended pull must not reach Acontext API")
    if observed.get("dashboard", {}).get("reachable") is not False:
        raise CityOpsContractError("extended pull must not reach Acontext dashboard")
    for flag in [
        "readiness_gate_rebuilt_with_empty_blockers",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]:
        if observed.get(flag) is not False:
            raise CityOpsContractError(f"extended pull promoted forbidden runtime flag: {flag}")


def _assert_artifact_conservative(artifact: dict[str, Any], source: dict[str, Any]) -> None:
    if artifact.get("schema") != ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA:
        raise CityOpsContractError("invalid extended pull timeout observation schema")
    _assert_pull_retry_source(source)
    _assert_observation_conservative(artifact.get("runtime_observation", {}))
    if artifact.get("observation_verdict") != EXTENDED_PULL_TIMEOUT_VERDICT:
        raise CityOpsContractError("extended pull timeout verdict drift")
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
    if readiness.get("ghcr_manifests_reachable") is not True:
        raise CityOpsContractError("extended pull should preserve manifest reachability evidence")
    gates = artifact.get("runtime_truth_gates", [])
    if [gate.get("gate") for gate in gates] != [
        "docker_daemon_socket",
        "ghcr_manifest_reachability",
        "first_required_image_extended_pull",
        "all_required_images_present",
        "local_acontext_services",
        "single_live_write_retrieve_parity_attempt",
    ]:
        raise CityOpsContractError("runtime gate order drift")
    if gates[0].get("passed") is not True or gates[1].get("passed") is not True:
        raise CityOpsContractError("Docker and manifest gates should be passed")
    if any(gate.get("passed") is True for gate in gates[2:]):
        raise CityOpsContractError("image/service/parity gates must remain blocked")
    if any(gate.get("authorizes_live_attempt") is True for gate in gates):
        raise CityOpsContractError("extended pull must not authorize live attempt")
    derived = artifact.get("derived_from", {})
    if derived.get("checks_registry_manifests") is not True:
        raise CityOpsContractError("artifact must record registry manifest checks")
    if derived.get("pulls_one_container_image") is not True:
        raise CityOpsContractError("artifact must record the bounded pull attempt")
    if derived.get("pull_completed") is not False:
        raise CityOpsContractError("artifact must not claim pull completion")
    _assert_claim_boundaries(
        artifact.get("claim_boundaries", {}).get("safe_to_claim", []),
        artifact.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_claim_boundaries(safe: list[str], blocked: list[str]) -> None:
    overlap = set(safe) & set(blocked)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
