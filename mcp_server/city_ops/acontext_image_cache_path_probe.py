"""Acontext image-cache path probe for City-as-a-Service.

The extended Docker pull proved that GHCR manifests are reachable while Docker
Desktop still cannot cache the first required Acontext image.  This artifact
records the next non-blind-pull probe: whether alternative cache/export tools
are locally available, whether Docker Buildx can at least inspect the image
index, and whether any image or service readiness changed.

It is internal/admin runtime-prerequisite evidence only.  It does not install
registry tooling, reset Docker Desktop, start Compose services, write to or
retrieve from Acontext, rebuild readiness, or promote customer, public,
dispatch, reputation, payment, production, GPS/raw metadata, authority, or
worker-copyable doctrine claims.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_required_image_extended_pull_timeout_observation import (
    ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA,
    EXTENDED_PULL_TIMEOUT_BLOCKED_CLAIMS,
    EXTENDED_PULL_TIMEOUT_VERDICT,
    load_acontext_required_image_extended_pull_timeout_observation,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA = "city_ops.acontext_image_cache_path_probe.v1"
ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME = "acontext_image_cache_path_probe.json"
ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM = (
    "admin_acontext_image_cache_path_probe_landed"
)

IMAGE_CACHE_PATH_PROBE_ID = (
    "execution_market.aas.acontext_image_cache_path_probe.2026_05_29_0005"
)
IMAGE_CACHE_PATH_PROBE_SCOPE = (
    "internal_admin_image_cache_path_probe_only_no_install_no_compose_or_live_parity"
)
IMAGE_CACHE_PATH_PROBE_VERDICT = (
    "alternate_cache_tools_absent_buildx_metadata_path_timed_out_first_image_still_missing"
)

IMAGE_CACHE_PATH_PROBE_BLOCKED_CLAIMS = [
    *EXTENDED_PULL_TIMEOUT_BLOCKED_CLAIMS,
    "image_cache_path_probe_installed_registry_tooling",
    "image_cache_path_probe_configured_registry_mirror",
    "image_cache_path_probe_obtained_trusted_preloaded_tar",
    "image_cache_path_probe_reset_docker_desktop_cache_or_networking",
    "image_cache_path_probe_completed_buildx_imagetools_inspect",
    "image_cache_path_probe_completed_alternate_cache_export",
    "image_cache_path_probe_loaded_first_required_image",
    "image_cache_path_probe_cached_first_required_image",
    "image_cache_path_probe_cached_all_required_images",
    "image_cache_path_probe_started_compose_services",
    "image_cache_path_probe_reached_acontext_api",
    "image_cache_path_probe_reached_acontext_dashboard",
    "image_cache_path_probe_rebuilt_empty_readiness_gate",
    "image_cache_path_probe_authorized_live_parity_attempt",
    "image_cache_path_probe_completed_live_acontext_write",
    "image_cache_path_probe_completed_live_acontext_retrieval",
    "image_cache_path_probe_proved_runtime_parity",
    "image_cache_path_probe_authorizes_customer_copy_delivery_or_publication",
    "image_cache_path_probe_authorizes_public_or_catalog_route",
    "image_cache_path_probe_authorizes_pricing_or_customer_quote",
    "image_cache_path_probe_authorizes_queue_launch_or_dispatch",
    "image_cache_path_probe_authorizes_erc8004_reputation_or_worker_skill_dna",
    "image_cache_path_probe_reverifies_payment_or_production",
    "image_cache_path_probe_allows_exact_gps_or_raw_metadata",
    "image_cache_path_probe_grants_domain_or_emergency_authority",
    "image_cache_path_probe_creates_worker_copyable_doctrine",
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


def build_may29_0005_image_cache_path_probe_observation() -> dict[str, Any]:
    """Return the sanitized May 29 image-cache path probe facts."""

    missing_required_images = [
        image for image in REQUIRED_ACONTEXT_IMAGES if image != "pgvector/pgvector:pg16"
    ]
    alternate_tools = [
        {"tool": "oras", "available": False, "path": None},
        {"tool": "crane", "available": False, "path": None},
        {"tool": "skopeo", "available": False, "path": None},
        {"tool": "regctl", "available": False, "path": None},
        {"tool": "nerdctl", "available": False, "path": None},
    ]
    return {
        "observation_window": "2026-05-29T00:03:44-04:00/2026-05-29T00:05:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": (
            "change_the_image_cache_path_after_extended_docker_pull_timeout_without_starting_compose"
        ),
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "commands_observed": [
            "command -v oras crane skopeo regctl nerdctl",
            "docker buildx imagetools inspect ghcr.io/memodb-io/acontext-ui:latest",
            "docker image inspect ghcr.io/memodb-io/acontext-ui:latest",
            "docker image inspect pgvector/pgvector:pg16",
            "curl --max-time 2 http://localhost:8029/api/v1/health",
            "curl --max-time 2 -I http://localhost:3000",
        ],
        "docker": {
            "context": "desktop-linux",
            "daemon_available": True,
            "server_version": "29.1.3",
            "server_os_arch": "linux/arm64",
            "docker_desktop_version": "4.57.0",
        },
        "required_images": {
            "source": "acontext_compose_image_pull_attempt_log.REQUIRED_ACONTEXT_IMAGES",
            "all": list(REQUIRED_ACONTEXT_IMAGES),
            "present_before_probe": ["pgvector/pgvector:pg16"],
            "missing_before_probe": missing_required_images,
        },
        "alternate_cache_tools": alternate_tools,
        "alternate_cache_tools_available": False,
        "docker_buildx_imagetools_inspect": {
            "image": "ghcr.io/memodb-io/acontext-ui:latest",
            "timeout_seconds": 60,
            "timed_out": True,
            "exit_code": None,
            "stdout_tail": [],
            "stderr_tail": [],
            "produced_metadata": False,
        },
        "cache_path_options": {
            "trusted_preloaded_tar_available": False,
            "registry_mirror_configured": False,
            "remote_builder_cache_export_available": False,
            "docker_desktop_cache_or_network_reset_performed": False,
            "registry_tool_install_performed": False,
        },
        "image_inventory_after_probe": {
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


def build_acontext_image_cache_path_probe(
    *,
    artifact_dir: str | Path | None = None,
    extended_pull_observation: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic image-cache path probe artifact."""

    source = extended_pull_observation or load_acontext_required_image_extended_pull_timeout_observation(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may29_0005_image_cache_path_probe_observation()
    _assert_extended_pull_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
            ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *IMAGE_CACHE_PATH_PROBE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA,
        "observation_id": IMAGE_CACHE_PATH_PROBE_ID,
        "scope": IMAGE_CACHE_PATH_PROBE_SCOPE,
        "source_artifacts": {
            "extended_pull_timeout_observation": {
                "file": ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_FILENAME],
            "runtime_observation_performed": True,
            "repeats_blind_docker_pull": False,
            "checks_alternate_cache_tooling": True,
            "checks_buildx_metadata_path": True,
            "installs_registry_tooling": False,
            "configures_registry_mirror": False,
            "loads_prebuilt_image_tar": False,
            "resets_docker_desktop_cache_or_networking": False,
            "pulls_container_image": False,
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
        "observation_verdict": IMAGE_CACHE_PATH_PROBE_VERDICT,
        "operator_instruction": (
            "Treat this as a cache-path probe only: alternate registry/cache tools are "
            "not installed locally, Docker Buildx did not return image-index metadata in "
            "the bounded window, and the first required Acontext image is still absent. "
            "Do not repeat blind pulls, start Compose, rebuild readiness, or attempt live "
            "parity until a trusted cache path actually makes required images present."
        ),
    }
    _assert_artifact_conservative(artifact, source)
    return artifact


def write_acontext_image_cache_path_probe(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic image-cache path probe fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_image_cache_path_probe(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_image_cache_path_probe(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted image-cache path probe."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifact = json.loads(
        (base_dir / ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME).read_text(encoding="utf-8")
    )
    source = load_acontext_required_image_extended_pull_timeout_observation(
        artifact_dir=base_dir
    )
    _assert_artifact_conservative(artifact, source)
    if artifact != build_acontext_image_cache_path_probe(
        artifact_dir=base_dir,
        extended_pull_observation=source,
        observation=artifact["runtime_observation"],
    ):
        raise CityOpsContractError("Acontext image-cache path probe drifted")
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
            "gate": "alternate_registry_cache_tooling",
            "status": "blocked_no_local_oras_crane_skopeo_regctl_nerdctl",
            "passed": observed["alternate_cache_tools_available"] is True,
            "evidence": observed["alternate_cache_tools"],
            "authorizes_live_attempt": False,
        },
        {
            "gate": "docker_buildx_metadata_path",
            "status": "blocked_imagetools_inspect_timed_out_without_metadata",
            "passed": observed["docker_buildx_imagetools_inspect"]["produced_metadata"] is True,
            "evidence": "bounded buildx imagetools inspect timed out silently",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "first_required_image_cached",
            "status": "blocked_first_required_image_still_missing",
            "passed": "ghcr.io/memodb-io/acontext-ui:latest"
            in observed["image_inventory_after_probe"]["present_required_images"],
            "evidence": observed["image_inventory_after_probe"]["missing_required_images"],
            "authorizes_live_attempt": False,
        },
        {
            "gate": "all_required_images_present",
            "status": "blocked_missing_required_images",
            "passed": observed["image_inventory_after_probe"]["all_required_images_present"] is True,
            "evidence": observed["image_inventory_after_probe"]["missing_required_images"],
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
    first_required_image_present = (
        "ghcr.io/memodb-io/acontext-ui:latest"
        in observed["image_inventory_after_probe"]["present_required_images"]
    )
    return {
        "image_cache_path_probe_landed": True,
        "extended_pull_timeout_source_verified": True,
        "docker_daemon_available": observed["docker"]["daemon_available"] is True,
        "alternate_cache_tools_available": observed["alternate_cache_tools_available"] is True,
        "buildx_imagetools_metadata_available": observed["docker_buildx_imagetools_inspect"][
            "produced_metadata"
        ]
        is True,
        "trusted_preloaded_tar_available": observed["cache_path_options"][
            "trusted_preloaded_tar_available"
        ]
        is True,
        "registry_mirror_configured": observed["cache_path_options"][
            "registry_mirror_configured"
        ]
        is True,
        "remote_builder_cache_export_available": observed["cache_path_options"][
            "remote_builder_cache_export_available"
        ]
        is True,
        "registry_tool_install_performed": observed["cache_path_options"][
            "registry_tool_install_performed"
        ]
        is True,
        "first_required_image_present": first_required_image_present,
        "all_required_images_present": observed["image_inventory_after_probe"][
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
        "Do not repeat blind docker pull attempts: the Docker CLI pull and Buildx metadata path both stalled without caching the first required image.",
        "Pick one changed cache path before the next probe: install/use a trusted registry client, obtain a trusted image tar, configure a registry mirror, reset Docker Desktop networking/cache, or export from a verified remote builder/cache.",
        "After the changed cache path, rerun required-image inventory and require ghcr.io/memodb-io/acontext-ui:latest to be present before touching Compose.",
        "Start local Acontext Compose services only after all required images are present.",
        "Rerun read-only live preflight and rebuild blocker delta/read surface/gate only after API/dashboard health is green.",
        "Attempt exactly one bounded live write/retrieve parity pass only if the rebuilt gate explicitly authorizes it.",
    ]


def _assert_extended_pull_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SCHEMA:
        raise CityOpsContractError("invalid extended pull timeout observation schema")
    if source.get("observation_verdict") != EXTENDED_PULL_TIMEOUT_VERDICT:
        raise CityOpsContractError("extended pull timeout observation verdict drift")
    if ACONTEXT_REQUIRED_IMAGE_EXTENDED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("extended pull timeout observation missing safe claim")
    readiness = source.get("readiness", {})
    if readiness.get("docker_daemon_available") is not True:
        raise CityOpsContractError("source did not preserve Docker daemon availability")
    if readiness.get("ghcr_manifests_reachable") is not True:
        raise CityOpsContractError("source did not preserve GHCR manifest reachability")
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
    if observed.get("docker", {}).get("daemon_available") is not True:
        raise CityOpsContractError("Docker daemon must remain available during cache path probe")
    tools = observed.get("alternate_cache_tools", [])
    if [tool.get("tool") for tool in tools] != ["oras", "crane", "skopeo", "regctl", "nerdctl"]:
        raise CityOpsContractError("alternate cache tool list drift")
    if any(tool.get("available") is True for tool in tools):
        raise CityOpsContractError("cache path probe must not claim registry tooling availability")
    if observed.get("alternate_cache_tools_available") is not False:
        raise CityOpsContractError("alternate cache tools must remain unavailable")
    buildx = observed.get("docker_buildx_imagetools_inspect", {})
    if buildx.get("image") != "ghcr.io/memodb-io/acontext-ui:latest":
        raise CityOpsContractError("unexpected image selected for buildx metadata probe")
    if buildx.get("timeout_seconds") != 60:
        raise CityOpsContractError("buildx metadata probe must use bounded one-minute window")
    if buildx.get("timed_out") is not True:
        raise CityOpsContractError("buildx metadata probe must record timeout")
    if buildx.get("produced_metadata") is not False:
        raise CityOpsContractError("buildx metadata probe must not claim metadata output")
    options = observed.get("cache_path_options", {})
    for flag in [
        "trusted_preloaded_tar_available",
        "registry_mirror_configured",
        "remote_builder_cache_export_available",
        "docker_desktop_cache_or_network_reset_performed",
        "registry_tool_install_performed",
    ]:
        if options.get(flag) is not False:
            raise CityOpsContractError(f"cache path option promoted forbidden flag: {flag}")
    inventory = observed.get("image_inventory_after_probe", {})
    if "pgvector/pgvector:pg16" not in inventory.get("present_required_images", []):
        raise CityOpsContractError("inventory must preserve the one observed local required image")
    if "ghcr.io/memodb-io/acontext-ui:latest" not in inventory.get(
        "missing_required_images", []
    ):
        raise CityOpsContractError("first required Acontext image must remain missing")
    if inventory.get("all_required_images_present") is not False:
        raise CityOpsContractError("all required images must remain blocked")
    if observed.get("compose_services_started") is not False:
        raise CityOpsContractError("cache path probe must not start Compose services")
    if observed.get("containers", {}).get("acontext_containers_running") is not False:
        raise CityOpsContractError("cache path probe must not start containers")
    if observed.get("api", {}).get("reachable") is not False:
        raise CityOpsContractError("cache path probe must not reach Acontext API")
    if observed.get("dashboard", {}).get("reachable") is not False:
        raise CityOpsContractError("cache path probe must not reach Acontext dashboard")
    for flag in [
        "readiness_gate_rebuilt_with_empty_blockers",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]:
        if observed.get(flag) is not False:
            raise CityOpsContractError(f"cache path probe promoted forbidden runtime flag: {flag}")


def _assert_artifact_conservative(artifact: dict[str, Any], source: dict[str, Any]) -> None:
    if artifact.get("schema") != ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA:
        raise CityOpsContractError("invalid image-cache path probe schema")
    _assert_extended_pull_source(source)
    _assert_observation_conservative(artifact.get("runtime_observation", {}))
    if artifact.get("observation_verdict") != IMAGE_CACHE_PATH_PROBE_VERDICT:
        raise CityOpsContractError("image-cache path probe verdict drift")
    readiness = artifact.get("readiness", {})
    for flag in [
        "alternate_cache_tools_available",
        "buildx_imagetools_metadata_available",
        "trusted_preloaded_tar_available",
        "registry_mirror_configured",
        "remote_builder_cache_export_available",
        "registry_tool_install_performed",
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
        "alternate_registry_cache_tooling",
        "docker_buildx_metadata_path",
        "first_required_image_cached",
        "all_required_images_present",
        "local_acontext_services",
        "single_live_write_retrieve_parity_attempt",
    ]:
        raise CityOpsContractError("runtime gate order drift")
    if gates[0].get("passed") is not True:
        raise CityOpsContractError("Docker daemon gate should be passed")
    if any(gate.get("passed") is True for gate in gates[1:]):
        raise CityOpsContractError("cache/image/service/parity gates must remain blocked")
    if any(gate.get("authorizes_live_attempt") is True for gate in gates):
        raise CityOpsContractError("cache path probe must not authorize live attempt")
    derived = artifact.get("derived_from", {})
    if derived.get("repeats_blind_docker_pull") is not False:
        raise CityOpsContractError("artifact must not repeat blind Docker pulls")
    if derived.get("checks_alternate_cache_tooling") is not True:
        raise CityOpsContractError("artifact must record alternate cache tooling check")
    if derived.get("checks_buildx_metadata_path") is not True:
        raise CityOpsContractError("artifact must record buildx metadata path check")
    for flag in [
        "installs_registry_tooling",
        "configures_registry_mirror",
        "loads_prebuilt_image_tar",
        "resets_docker_desktop_cache_or_networking",
        "pulls_container_image",
        "starts_compose_services",
        "writes_live_acontext",
        "retrieves_live_acontext",
    ]:
        if derived.get(flag) is not False:
            raise CityOpsContractError(f"derived section promoted forbidden flag: {flag}")
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
