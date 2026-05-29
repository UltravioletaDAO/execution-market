"""Acontext digest-pinned pull timeout observation for City-as-a-Service.

This artifact records the May 29 02:12 EDT bounded runtime proof after the
cache-path resolution plan selected a trusted registry-client/export-load path.
A direct anonymous GHCR registry API read locked the first required image to a
linux/arm64 manifest digest and layer budget, then a digest-pinned Docker pull
still timed out before caching the image.

It is internal/admin runtime-prerequisite evidence only.  It does not install
registry tooling, configure a mirror, start Compose services, write to or
retrieve from Acontext, rebuild the readiness gate, or promote customer,
public, dispatch, reputation, payment, production, GPS/raw metadata, authority,
or worker-copyable doctrine claims.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_cache_path_resolution_plan import (
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME,
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM,
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA,
    CACHE_PATH_RESOLUTION_PLAN_VERDICT,
    load_acontext_cache_path_resolution_plan,
)
from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA = (
    "city_ops.acontext_digest_pinned_pull_timeout_observation.v1"
)
ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME = (
    "acontext_digest_pinned_pull_timeout_observation.json"
)
ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM = (
    "admin_acontext_digest_pinned_pull_timeout_observation_landed"
)

DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_ID = (
    "execution_market.aas.acontext_digest_pinned_pull_timeout_observation."
    "2026_05_29_0212"
)
DIGEST_PINNED_PULL_TIMEOUT_SCOPE = (
    "internal_admin_digest_pinned_pull_timeout_only_no_install_no_compose_or_live_parity"
)
DIGEST_PINNED_PULL_TIMEOUT_VERDICT = (
    "ghcr_manifest_digest_locked_digest_pinned_docker_pull_timed_out_image_still_missing"
)

FIRST_REQUIRED_IMAGE = "ghcr.io/memodb-io/acontext-ui:latest"
FIRST_REQUIRED_IMAGE_REPOSITORY = "ghcr.io/memodb-io/acontext-ui"
FIRST_REQUIRED_IMAGE_INDEX_DIGEST = (
    "sha256:b303d1f1894bbe356e4f70483c06a7bfe9c38bcf46a5fff5de2d8826e87ef436"
)
FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST = (
    "sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7"
)
FIRST_REQUIRED_IMAGE_CONFIG_DIGEST = (
    "sha256:5a1be63a0fd630cef6fbffea574c6979b0c53920f0ab0f5af0b96c473754a9bc"
)

DIGEST_PINNED_PULL_TIMEOUT_BLOCKED_CLAIMS = [
    "digest_pinned_pull_timeout_installed_registry_tooling",
    "digest_pinned_pull_timeout_used_third_party_registry_client",
    "digest_pinned_pull_timeout_manifest_digest_lock_implies_image_cached",
    "digest_pinned_pull_timeout_resolves_docker_desktop_pull_stall",
    "digest_pinned_pull_timeout_cached_first_required_image",
    "digest_pinned_pull_timeout_cached_all_required_images",
    "digest_pinned_pull_timeout_started_compose_services",
    "digest_pinned_pull_timeout_reached_acontext_api",
    "digest_pinned_pull_timeout_reached_acontext_dashboard",
    "digest_pinned_pull_timeout_rebuilt_empty_readiness_gate",
    "digest_pinned_pull_timeout_authorized_live_parity_attempt",
    "digest_pinned_pull_timeout_completed_live_acontext_write",
    "digest_pinned_pull_timeout_completed_live_acontext_retrieval",
    "digest_pinned_pull_timeout_proved_runtime_parity",
    "digest_pinned_pull_timeout_authorizes_customer_copy_delivery_or_publication",
    "digest_pinned_pull_timeout_authorizes_public_or_catalog_route",
    "digest_pinned_pull_timeout_authorizes_pricing_or_customer_quote",
    "digest_pinned_pull_timeout_authorizes_queue_launch_or_dispatch",
    "digest_pinned_pull_timeout_authorizes_erc8004_reputation_or_worker_skill_dna",
    "digest_pinned_pull_timeout_reverifies_payment_or_production",
    "digest_pinned_pull_timeout_allows_exact_gps_or_raw_metadata",
    "digest_pinned_pull_timeout_grants_domain_or_emergency_authority",
    "digest_pinned_pull_timeout_creates_worker_copyable_doctrine",
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


def build_may29_0212_digest_pinned_pull_timeout_observation() -> dict[str, Any]:
    """Return the sanitized May 29 digest-pinned pull timeout facts."""

    missing_required_images = [
        image for image in REQUIRED_ACONTEXT_IMAGES if image != "pgvector/pgvector:pg16"
    ]
    return {
        "observation_window": "2026-05-29T02:06:33-04:00/2026-05-29T02:12:20-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": (
            "execute_one_bounded_digest_pinned_cache_path_after_manifest_lock_without_starting_compose"
        ),
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "commands_observed": [
            "GHCR anonymous token + OCI index fetch for ghcr.io/memodb-io/acontext-ui:latest",
            "GHCR anonymous linux/arm64 manifest fetch by digest",
            "docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7",
            "docker image inspect ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7",
        ],
        "docker": {
            "context": "desktop-linux",
            "daemon_available": True,
            "server_os_arch": "linux/arm64",
        },
        "registry_manifest_lock": {
            "image": FIRST_REQUIRED_IMAGE,
            "repository": FIRST_REQUIRED_IMAGE_REPOSITORY,
            "tag": "latest",
            "anonymous_bearer_token_received": True,
            "index_http_status": 200,
            "index_media_type": "application/vnd.oci.image.index.v1+json",
            "index_digest": FIRST_REQUIRED_IMAGE_INDEX_DIGEST,
            "index_fetch_duration_seconds": 0.81,
            "platforms": ["linux/amd64", "linux/arm64", "unknown/unknown"],
            "linux_arm64_manifest_advertised": True,
            "linux_arm64_manifest_digest": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "linux_arm64_manifest_size_bytes": 2190,
            "manifest_http_status": 200,
            "manifest_digest": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "config_digest": FIRST_REQUIRED_IMAGE_CONFIG_DIGEST,
            "config_size_bytes": 9279,
            "layer_count": 10,
            "layer_total_size_bytes": 75482880,
            "blob_download_performed": False,
            "image_load_performed": False,
        },
        "required_images": {
            "source": "acontext_compose_image_pull_attempt_log.REQUIRED_ACONTEXT_IMAGES",
            "all": list(REQUIRED_ACONTEXT_IMAGES),
            "present_before_digest_pinned_pull": ["pgvector/pgvector:pg16"],
            "missing_before_digest_pinned_pull": missing_required_images,
        },
        "digest_pinned_pull": {
            "image": FIRST_REQUIRED_IMAGE_REPOSITORY,
            "digest": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "pull_reference": (
                f"{FIRST_REQUIRED_IMAGE_REPOSITORY}@{FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST}"
            ),
            "platform": "linux/arm64",
            "timeout_seconds": 240,
            "duration_seconds": 240.01,
            "timed_out": True,
            "exit_code": None,
            "present_after_attempt": False,
        },
        "image_inventory_after_digest_pinned_pull": {
            "checked": True,
            "present_required_images": ["pgvector/pgvector:pg16"],
            "missing_required_images": missing_required_images,
            "all_required_images_present": False,
        },
        "containers": {
            "checked": True,
            "acontext_containers_running": False,
        },
        "api": {
            "checked": False,
            "reachable": False,
            "reason": "not_checked_because_first_required_image_missing",
        },
        "dashboard": {
            "checked": False,
            "reachable": False,
            "reason": "not_checked_because_first_required_image_missing",
        },
        "registry_tool_install_performed": False,
        "third_party_registry_client_used": False,
        "compose_services_started": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
        "one_live_parity_attempt_authorized": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_digest_pinned_pull_timeout_observation(
    *,
    artifact_dir: str | Path | None = None,
    cache_path_resolution_plan: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic digest-pinned pull timeout observation."""

    source = cache_path_resolution_plan or load_acontext_cache_path_resolution_plan(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may29_0212_digest_pinned_pull_timeout_observation()
    _assert_resolution_plan_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM,
            ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *DIGEST_PINNED_PULL_TIMEOUT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA,
        "observation_id": DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_ID,
        "scope": DIGEST_PINNED_PULL_TIMEOUT_SCOPE,
        "source_artifacts": {
            "cache_path_resolution_plan": {
                "file": ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME,
                "schema": source["schema"],
                "id": source["plan_id"],
                "safe_claim": ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "plan_verdict": source["plan_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME],
            "runtime_observation_performed": True,
            "checks_registry_manifest_by_digest": True,
            "installs_registry_tooling": False,
            "uses_third_party_registry_client": False,
            "configures_registry_mirror": False,
            "downloads_image_blobs_directly": False,
            "loads_prebuilt_image_tar": False,
            "pulls_digest_pinned_container_image": True,
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
        "observation_verdict": DIGEST_PINNED_PULL_TIMEOUT_VERDICT,
        "operator_instruction": (
            "Treat this as a digest lock plus bounded pull timeout only. The registry API can "
            "resolve the linux/arm64 image digest and layer budget, but Docker Desktop still did "
            "not cache the first required image. Do not start Compose, rebuild readiness, or "
            "attempt live parity until the image is actually present locally."
        ),
    }
    _assert_artifact_conservative(artifact, source)
    return artifact


def write_acontext_digest_pinned_pull_timeout_observation(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic digest-pinned pull timeout observation fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_digest_pinned_pull_timeout_observation(
        artifact_dir=base_dir
    )
    path = base_dir / ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_digest_pinned_pull_timeout_observation(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted digest-pinned pull timeout observation."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifact = json.loads(
        (base_dir / ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source = load_acontext_cache_path_resolution_plan(artifact_dir=base_dir)
    _assert_artifact_conservative(artifact, source)
    if artifact != build_acontext_digest_pinned_pull_timeout_observation(
        artifact_dir=base_dir,
        cache_path_resolution_plan=source,
        observation=artifact["runtime_observation"],
    ):
        raise CityOpsContractError("Acontext digest-pinned pull timeout observation drifted")
    return artifact


def _runtime_truth_gates(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "docker_daemon_socket",
            "status": "passed_from_runtime_observation",
            "passed": observed["docker"]["daemon_available"] is True,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "registry_manifest_digest_lock",
            "status": "passed_but_not_image_cache_or_runtime_readiness",
            "passed": observed["registry_manifest_lock"]["linux_arm64_manifest_advertised"] is True
            and observed["registry_manifest_lock"]["manifest_digest"]
            == FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "evidence": {
                "index_digest": observed["registry_manifest_lock"]["index_digest"],
                "manifest_digest": observed["registry_manifest_lock"]["manifest_digest"],
                "layer_total_size_bytes": observed["registry_manifest_lock"][
                    "layer_total_size_bytes"
                ],
            },
            "authorizes_live_attempt": False,
        },
        {
            "gate": "digest_pinned_docker_pull",
            "status": "blocked_digest_pinned_pull_timed_out_image_not_present",
            "passed": observed["digest_pinned_pull"]["present_after_attempt"] is True,
            "evidence": "four-minute digest-pinned pull timed out with no local image present",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "all_required_images_present",
            "status": "blocked_missing_required_images",
            "passed": observed["image_inventory_after_digest_pinned_pull"][
                "all_required_images_present"
            ]
            is True,
            "evidence": observed["image_inventory_after_digest_pinned_pull"][
                "missing_required_images"
            ],
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
        "digest_pinned_pull_timeout_observation_landed": True,
        "cache_path_resolution_plan_source_verified": True,
        "docker_daemon_available": observed["docker"]["daemon_available"] is True,
        "registry_manifest_digest_locked": observed["registry_manifest_lock"]["manifest_digest"]
        == FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
        "linux_arm64_manifest_advertised": observed["registry_manifest_lock"][
            "linux_arm64_manifest_advertised"
        ]
        is True,
        "image_blobs_downloaded_directly": observed["registry_manifest_lock"][
            "blob_download_performed"
        ]
        is True,
        "digest_pinned_pull_attempted": True,
        "digest_pinned_pull_completed": observed["digest_pinned_pull"]["timed_out"] is False,
        "first_required_image_present": observed["digest_pinned_pull"][
            "present_after_attempt"
        ]
        is True,
        "all_required_images_present": observed["image_inventory_after_digest_pinned_pull"][
            "all_required_images_present"
        ]
        is True,
        "compose_services_started": observed["compose_services_started"] is True,
        "acontext_containers_running": observed["containers"]["acontext_containers_running"]
        is True,
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
        "Do not claim the first required image is cached; the digest-pinned Docker pull timed out and image inspect still failed.",
        "Use the locked index and linux/arm64 manifest digests as provenance inputs for the next cache path instead of retrying tag-based pulls.",
        "Pick one changed path next: a trusted registry client copy/load, a trusted preloaded tar with matching digest, a mirror, or Docker Desktop cache/network maintenance.",
        "Repeat required-image inventory only after ghcr.io/memodb-io/acontext-ui is present locally by digest or tag.",
        "Start local Acontext Compose services only after all required images are present.",
        "Attempt exactly one bounded live write/retrieve parity pass only if the rebuilt readiness gate explicitly authorizes it.",
    ]


def _assert_resolution_plan_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA:
        raise CityOpsContractError("invalid cache-path resolution plan schema")
    if source.get("plan_verdict") != CACHE_PATH_RESOLUTION_PLAN_VERDICT:
        raise CityOpsContractError("cache-path resolution plan verdict drift")
    if source.get("selected_next_changed_cache_path") != "trusted_registry_client_export_load_path":
        raise CityOpsContractError("cache-path resolution plan selected unexpected path")
    if ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("cache-path resolution plan missing safe claim")
    readiness = source.get("readiness", {})
    for flag in [
        "registry_tool_installed",
        "registry_tool_used",
        "first_required_image_present",
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_reachable",
        "acontext_dashboard_reachable",
        "one_live_parity_attempt_authorized",
        "memory_acontext_parity_ready",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"source promoted later readiness: {flag}")
    _assert_claim_boundaries(
        source.get("claim_boundaries", {}).get("safe_to_claim", []),
        source.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    manifest = observed.get("registry_manifest_lock", {})
    pull = observed.get("digest_pinned_pull", {})
    inventory = observed.get("image_inventory_after_digest_pinned_pull", {})
    if observed.get("docker", {}).get("daemon_available") is not True:
        raise CityOpsContractError("Docker daemon must remain available during digest-pinned pull")
    if manifest.get("image") != FIRST_REQUIRED_IMAGE:
        raise CityOpsContractError("unexpected manifest-lock image")
    if manifest.get("index_digest") != FIRST_REQUIRED_IMAGE_INDEX_DIGEST:
        raise CityOpsContractError("manifest index digest drift")
    if manifest.get("manifest_digest") != FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST:
        raise CityOpsContractError("linux/arm64 manifest digest drift")
    if manifest.get("config_digest") != FIRST_REQUIRED_IMAGE_CONFIG_DIGEST:
        raise CityOpsContractError("config digest drift")
    if manifest.get("linux_arm64_manifest_advertised") is not True:
        raise CityOpsContractError("manifest lock must preserve linux/arm64 support")
    if manifest.get("layer_count") != 10:
        raise CityOpsContractError("manifest lock must preserve layer count")
    if manifest.get("layer_total_size_bytes") != 75482880:
        raise CityOpsContractError("manifest lock must preserve layer byte budget")
    if manifest.get("blob_download_performed") is not False:
        raise CityOpsContractError("manifest lock must not download blobs directly")
    if manifest.get("image_load_performed") is not False:
        raise CityOpsContractError("manifest lock must not load an image")
    if pull.get("digest") != FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST:
        raise CityOpsContractError("digest-pinned pull must use the locked manifest digest")
    if pull.get("timeout_seconds") != 240:
        raise CityOpsContractError("digest-pinned pull must use the four-minute bounded window")
    if pull.get("timed_out") is not True:
        raise CityOpsContractError("digest-pinned pull observation must record timeout")
    if pull.get("present_after_attempt") is not False:
        raise CityOpsContractError("digest-pinned pull must not claim image presence")
    if "pgvector/pgvector:pg16" not in observed.get("required_images", {}).get(
        "present_before_digest_pinned_pull", []
    ):
        raise CityOpsContractError("inventory must preserve the one observed local required image")
    if FIRST_REQUIRED_IMAGE not in observed.get("required_images", {}).get(
        "missing_before_digest_pinned_pull", []
    ):
        raise CityOpsContractError("first required image must have been missing before retry")
    if inventory.get("all_required_images_present") is not False:
        raise CityOpsContractError("all required images must remain blocked")
    if FIRST_REQUIRED_IMAGE not in inventory.get("missing_required_images", []):
        raise CityOpsContractError("first required image must remain missing after timeout")
    for flag in [
        "registry_tool_install_performed",
        "third_party_registry_client_used",
        "compose_services_started",
        "readiness_gate_rebuilt_with_empty_blockers",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]:
        if observed.get(flag) is not False:
            raise CityOpsContractError(f"digest-pinned pull promoted forbidden flag: {flag}")
    if observed.get("containers", {}).get("acontext_containers_running") is not False:
        raise CityOpsContractError("digest-pinned pull must not start containers")
    if observed.get("api", {}).get("reachable") is not False:
        raise CityOpsContractError("digest-pinned pull must not reach Acontext API")
    if observed.get("dashboard", {}).get("reachable") is not False:
        raise CityOpsContractError("digest-pinned pull must not reach Acontext dashboard")


def _assert_artifact_conservative(artifact: dict[str, Any], source: dict[str, Any]) -> None:
    if artifact.get("schema") != ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA:
        raise CityOpsContractError("invalid digest-pinned pull timeout observation schema")
    _assert_resolution_plan_source(source)
    observed = artifact.get("runtime_observation", {})
    _assert_observation_conservative(observed)
    derived = artifact.get("derived_from", {})
    if derived.get("runtime_observation_performed") is not True:
        raise CityOpsContractError("digest-pinned pull must record runtime observation")
    if derived.get("checks_registry_manifest_by_digest") is not True:
        raise CityOpsContractError("digest-pinned pull must lock registry manifest digest")
    if derived.get("pulls_digest_pinned_container_image") is not True:
        raise CityOpsContractError("digest-pinned pull must record the bounded pull attempt")
    if derived.get("pull_completed") is not False:
        raise CityOpsContractError("digest-pinned pull must not claim completion")
    for flag in [
        "installs_registry_tooling",
        "uses_third_party_registry_client",
        "configures_registry_mirror",
        "downloads_image_blobs_directly",
        "loads_prebuilt_image_tar",
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
            raise CityOpsContractError(f"digest-pinned pull promoted forbidden derived flag: {flag}")
    readiness = artifact.get("readiness", {})
    if readiness.get("registry_manifest_digest_locked") is not True:
        raise CityOpsContractError("digest-pinned pull must preserve manifest digest lock")
    for flag in [
        "image_blobs_downloaded_directly",
        "digest_pinned_pull_completed",
        "first_required_image_present",
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_reachable",
        "acontext_dashboard_reachable",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "memory_acontext_parity_ready",
        "customer_copy_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"digest-pinned pull promoted readiness: {flag}")
    gates = artifact.get("runtime_truth_gates", [])
    if [gate.get("gate") for gate in gates] != [
        "docker_daemon_socket",
        "registry_manifest_digest_lock",
        "digest_pinned_docker_pull",
        "all_required_images_present",
        "local_acontext_services",
        "single_live_write_retrieve_parity_attempt",
    ]:
        raise CityOpsContractError("digest-pinned pull gate order drifted")
    if gates[0].get("passed") is not True or gates[1].get("passed") is not True:
        raise CityOpsContractError("digest-pinned pull must pass only daemon and manifest gates")
    if any(gate.get("passed") is True for gate in gates[2:]):
        raise CityOpsContractError("digest-pinned pull must keep later runtime gates blocked")
    if any(gate.get("authorizes_live_attempt") is not False for gate in gates):
        raise CityOpsContractError("digest-pinned pull must not authorize live attempt")
    access = artifact.get("access_policy", {})
    for flag, expected in _FALSE_ACCESS_FLAGS.items():
        if access.get(flag) is not expected:
            raise CityOpsContractError(f"digest-pinned pull access flag drift: {flag}")
    if ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM not in artifact.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("digest-pinned pull missing safe claim")
    _assert_claim_boundaries(
        artifact.get("claim_boundaries", {}).get("safe_to_claim", []),
        artifact.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _stable_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
