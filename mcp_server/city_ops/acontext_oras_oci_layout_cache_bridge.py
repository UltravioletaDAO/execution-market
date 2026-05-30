"""ORAS OCI-layout cache bridge observation for Acontext image caching.

This City-as-a-Service/AAS artifact records the May 30 midnight follow-up to
the crane timeout observation.  A different trusted registry acquisition path
(`oras copy --to-oci-layout`) successfully materialized the pinned linux/arm64
Acontext UI image into a local OCI layout, loaded it into Docker, and tagged it
as the first required Compose image.  The slice intentionally stops before
pulling/starting the full Acontext stack because the remaining required images
are still not present.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_crane_export_load_timeout_observation import (
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCHEMA,
    load_acontext_crane_export_load_timeout_observation,
)
from .acontext_digest_pinned_pull_timeout_observation import (
    FIRST_REQUIRED_IMAGE,
    FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
    FIRST_REQUIRED_IMAGE_CONFIG_DIGEST,
    FIRST_REQUIRED_IMAGE_INDEX_DIGEST,
    FIRST_REQUIRED_IMAGE_REPOSITORY,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCHEMA = (
    "city_ops.acontext_oras_oci_layout_cache_bridge.v1"
)
ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME = (
    "acontext_oras_oci_layout_cache_bridge.json"
)
ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM = (
    "admin_acontext_oras_oci_layout_cache_bridge_landed"
)
ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_ID = (
    "execution_market.aas.acontext_oras_oci_layout_cache_bridge.2026_05_30_0008"
)
ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCOPE = (
    "internal_admin_oras_oci_layout_cache_bridge_first_image_only_no_compose_or_live_parity"
)
ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_VERDICT = (
    "oras_oci_layout_created_docker_loaded_and_first_required_image_tagged_remaining_images_missing"
)

ORAS_TOOL = {
    "tool": "oras",
    "available": True,
    "path": "/opt/homebrew/bin/oras",
    "version": "1.3.2+Homebrew",
    "install_source": "Homebrew formula oras",
    "oci_layout_capable_for_local_image_cache": True,
}

ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_BLOCKED_CLAIMS = [
    "oras_oci_layout_cache_bridge_cached_all_required_images",
    "oras_oci_layout_cache_bridge_started_compose_services",
    "oras_oci_layout_cache_bridge_reached_acontext_api",
    "oras_oci_layout_cache_bridge_reached_acontext_dashboard",
    "oras_oci_layout_cache_bridge_rebuilt_empty_readiness_gate",
    "oras_oci_layout_cache_bridge_authorized_live_parity_attempt",
    "oras_oci_layout_cache_bridge_completed_live_acontext_write",
    "oras_oci_layout_cache_bridge_completed_live_acontext_retrieval",
    "oras_oci_layout_cache_bridge_proved_runtime_parity",
    "oras_oci_layout_cache_bridge_changes_irc_runtime_session_manager",
    "oras_oci_layout_cache_bridge_enables_cross_project_autorouting",
    "oras_oci_layout_cache_bridge_authorizes_customer_copy_delivery_or_publication",
    "oras_oci_layout_cache_bridge_authorizes_public_or_catalog_route",
    "oras_oci_layout_cache_bridge_authorizes_pricing_or_customer_quote",
    "oras_oci_layout_cache_bridge_authorizes_queue_launch_or_dispatch",
    "oras_oci_layout_cache_bridge_authorizes_erc8004_reputation_or_worker_skill_dna",
    "oras_oci_layout_cache_bridge_reverifies_payment_or_production",
    "oras_oci_layout_cache_bridge_allows_exact_gps_or_raw_metadata",
    "oras_oci_layout_cache_bridge_grants_domain_or_emergency_authority",
    "oras_oci_layout_cache_bridge_creates_worker_copyable_doctrine",
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


def build_may30_0008_oras_oci_layout_cache_bridge_observation() -> dict[str, Any]:
    """Return sanitized facts from the successful ORAS OCI-layout bridge."""

    present_required_images = [
        "ghcr.io/memodb-io/acontext-ui:latest",
        "pgvector/pgvector:pg16",
    ]
    missing_required_images = [
        image for image in REQUIRED_ACONTEXT_IMAGES if image not in present_required_images
    ]
    return {
        "observation_window": "2026-05-30T00:08:00-04:00/2026-05-30T00:15:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": (
            "try_different_trusted_acquisition_path_after_crane_timeout_without_repeating_blind_docker_pull"
        ),
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "pinned_image": {
            "image": FIRST_REQUIRED_IMAGE,
            "repository": FIRST_REQUIRED_IMAGE_REPOSITORY,
            "platform": "linux/arm64",
            "index_digest": FIRST_REQUIRED_IMAGE_INDEX_DIGEST,
            "manifest_digest": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "config_digest": FIRST_REQUIRED_IMAGE_CONFIG_DIGEST,
        },
        "trusted_tool": ORAS_TOOL,
        "commands_observed": [
            "brew install oras",
            "oras version",
            "oras manifest fetch --platform linux/arm64 --format json ghcr.io/memodb-io/acontext-ui:latest",
            (
                "oras pull --platform linux/arm64 --no-tty --output "
                "/tmp/acontext-ui-oras-linux-arm64-ef6bdb2b "
                "ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7"
            ),
            (
                "oras copy --platform linux/arm64 --no-tty --to-oci-layout "
                "ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7 "
                "/tmp/acontext-ui-oras-oci-layout-ef6bdb2b:acontext-ui-linux-arm64"
            ),
            "tar local OCI layout into /tmp/acontext-ui-oras-oci-layout-ef6bdb2b.tar",
            "docker load -i /tmp/acontext-ui-oras-oci-layout-ef6bdb2b.tar",
            "docker tag sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7 ghcr.io/memodb-io/acontext-ui:latest",
            "docker image inspect ghcr.io/memodb-io/acontext-ui:latest",
        ],
        "changed_cache_path_attempt": {
            "selected_path": "trusted_oras_oci_layout_export_load_path",
            "attempted": True,
            "tool": "oras",
            "tool_version": "1.3.2+Homebrew",
            "registry_tool_install_performed": True,
            "manifest_fetch_attempted": True,
            "manifest_fetch_timeout_seconds": 90,
            "manifest_fetch_timed_out": False,
            "manifest_fetch_returncode": 0,
            "manifest_fetch_duration_seconds": 0.491,
            "manifest_digest_matches_expected": True,
            "manifest_layer_count": 10,
            "direct_oras_pull_attempted": True,
            "direct_oras_pull_returncode": 0,
            "direct_oras_pull_downloaded_layers": False,
            "direct_oras_pull_file_count": 0,
            "direct_oras_pull_stdout_note": (
                "Skipped pulling layers without file name in org.opencontainers.image.title; suggested oras copy --to-oci-layout"
            ),
            "oras_copy_to_oci_layout_attempted": True,
            "oras_copy_timeout_seconds": 240,
            "oras_copy_timed_out": False,
            "oras_copy_returncode": 0,
            "oras_copy_duration_seconds": 5.92,
            "oci_layout_path": "/tmp/acontext-ui-oras-oci-layout-ef6bdb2b",
            "oci_layout_created": True,
            "oci_layout_file_count": 14,
            "oci_layout_total_size_bytes": 75494698,
            "oci_layout_manifest_blob_present": True,
            "oci_layout_config_blob_present": True,
            "oci_layout_archive_path": "/tmp/acontext-ui-oras-oci-layout-ef6bdb2b.tar",
            "oci_layout_archive_created": True,
            "docker_load_attempted": True,
            "docker_load_timeout_seconds": 180,
            "docker_load_timed_out": False,
            "docker_load_returncode": 0,
            "docker_load_stdout": "Loaded image: acontext-ui-linux-arm64:latest",
            "docker_local_image_id": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "docker_tag_performed": True,
            "docker_tag_source": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "docker_tag_target": FIRST_REQUIRED_IMAGE,
            "blind_tag_docker_pull_repeated": False,
            "digest_pinned_docker_pull_repeated": False,
            "crane_path_repeated": False,
            "compose_started": False,
            "stop_reason": (
                "first_required_image_loaded_and_tagged_but_remaining_required_images_missing"
            ),
        },
        "docker": {
            "context": "desktop-linux",
            "daemon_available": True,
            "server_version": "29.1.3",
        },
        "image_inventory_after_attempt": {
            "checked": True,
            "first_required_image_present_by_tag": True,
            "first_required_image_present_by_digest_reference": False,
            "first_required_image_local_id": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "present_required_images": present_required_images,
            "missing_required_images": missing_required_images,
            "all_required_images_present": False,
        },
        "api": {
            "checked": False,
            "reachable": False,
            "reason": "not_checked_because_remaining_required_images_missing_and_compose_not_started",
        },
        "dashboard": {
            "checked": False,
            "reachable": False,
            "reason": "not_checked_because_remaining_required_images_missing_and_compose_not_started",
        },
        "readiness_gate_rebuilt_with_empty_blockers": False,
        "one_live_parity_attempt_authorized": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_oras_oci_layout_cache_bridge(
    *,
    artifact_dir: str | Path | None = None,
    crane_timeout_observation: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic ORAS OCI-layout cache bridge artifact."""

    source = crane_timeout_observation or load_acontext_crane_export_load_timeout_observation(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may30_0008_oras_oci_layout_cache_bridge_observation()
    _assert_crane_timeout_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM,
            ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCHEMA,
        "observation_id": ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_ID,
        "scope": ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCOPE,
        "source_artifacts": {
            "crane_export_load_timeout_observation": {
                "file": ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME],
            "runtime_observation_performed": True,
            "installed_alternate_trusted_registry_client": True,
            "attempted_different_cache_path": True,
            "repeats_blind_docker_pull": False,
            "repeats_digest_pinned_docker_pull": False,
            "repeats_crane_path": False,
            "starts_compose": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_VERDICT,
        "readiness": {
            "alternate_trusted_registry_client_installed": True,
            "platform_manifest_resolved": True,
            "oci_layout_created": True,
            "oci_layout_archive_created": True,
            "docker_load_performed": True,
            "first_required_image_present": True,
            "first_required_image_present_by_required_tag": True,
            "first_required_image_present_by_digest_reference": False,
            "all_required_images_present": False,
            "compose_services_started": False,
            "acontext_api_reachable": False,
            "acontext_dashboard_reachable": False,
            "one_live_parity_attempt_authorized": False,
        },
        "runtime_truth_gates": [
            {
                "gate": "alternate_trusted_registry_client_installed",
                "passed": True,
                "evidence": "oras 1.3.2+Homebrew installed and present at /opt/homebrew/bin/oras",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "platform_manifest_resolved",
                "passed": True,
                "evidence": "oras manifest fetch resolved the expected linux/arm64 manifest digest",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "oci_layout_export_created",
                "passed": True,
                "evidence": "oras copy --to-oci-layout created 14 local OCI-layout files totaling 75,494,698 bytes",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "first_required_image_loaded_and_tagged",
                "passed": True,
                "evidence": "docker load succeeded and the local image ID was tagged as ghcr.io/memodb-io/acontext-ui:latest",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "all_required_images_present",
                "passed": False,
                "evidence": "seven required images remain absent from local Docker inventory",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "single_live_write_retrieve_parity_attempt",
                "passed": False,
                "evidence": "not authorized until all required images and local health gates pass",
                "authorizes_live_attempt": False,
            },
        ],
        "operator_guidance": {
            "safe_next_step": (
                "Use the now-proven ORAS OCI-layout method only for the remaining missing images, then rerun image inventory. "
                "Do not start Compose or perform live parity until every required image is present locally."
            ),
            "stop_line": (
                "Stop before Compose, API/dashboard checks, customer copy, dispatch, or live parity while any required image remains missing."
            ),
            "not_customer_copy": True,
            "not_worker_instruction": True,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
    }
    _assert_artifact_conservative(artifact)
    return artifact


def write_acontext_oras_oci_layout_cache_bridge(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the ORAS OCI-layout cache bridge fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME
    artifact = build_acontext_oras_oci_layout_cache_bridge(artifact_dir=target_dir)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_oras_oci_layout_cache_bridge(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the ORAS OCI-layout cache bridge fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = source_dir / ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact != build_acontext_oras_oci_layout_cache_bridge(artifact_dir=source_dir):
        raise CityOpsContractError("ORAS OCI-layout cache bridge fixture drift")
    return artifact


def _assert_crane_timeout_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCHEMA:
        raise CityOpsContractError("source must be crane export/load timeout observation")
    safe = source.get("claim_boundaries", {}).get("safe_to_claim", [])
    if ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM not in safe:
        raise CityOpsContractError("source missing crane timeout safe claim")
    readiness = source.get("readiness", {})
    if readiness.get("first_required_image_present") is not False:
        raise CityOpsContractError("source must still show first image missing")
    if readiness.get("one_live_parity_attempt_authorized") is not False:
        raise CityOpsContractError("source must not authorize live parity")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    attempt = observed.get("changed_cache_path_attempt", {})
    inventory = observed.get("image_inventory_after_attempt", {})
    if observed.get("trusted_tool", {}).get("tool") != "oras":
        raise CityOpsContractError("observation must identify ORAS as trusted tool")
    if observed.get("trusted_tool", {}).get("available") is not True:
        raise CityOpsContractError("observation must record ORAS availability")
    required_true = [
        "attempted",
        "registry_tool_install_performed",
        "manifest_fetch_attempted",
        "manifest_digest_matches_expected",
        "oras_copy_to_oci_layout_attempted",
        "oci_layout_created",
        "oci_layout_archive_created",
        "docker_load_attempted",
        "docker_tag_performed",
    ]
    for field in required_true:
        if attempt.get(field) is not True:
            raise CityOpsContractError(f"observation missing successful ORAS bridge field: {field}")
    for forbidden in [
        "manifest_fetch_timed_out",
        "oras_copy_timed_out",
        "docker_load_timed_out",
        "blind_tag_docker_pull_repeated",
        "digest_pinned_docker_pull_repeated",
        "crane_path_repeated",
        "compose_started",
    ]:
        if attempt.get(forbidden) is not False:
            raise CityOpsContractError(f"observation promoted forbidden field: {forbidden}")
    if inventory.get("first_required_image_present_by_tag") is not True:
        raise CityOpsContractError("observation must prove first image by required tag")
    if inventory.get("all_required_images_present") is not False:
        raise CityOpsContractError("observation must not claim all images present")
    if FIRST_REQUIRED_IMAGE not in inventory.get("present_required_images", []):
        raise CityOpsContractError("first required image missing from present inventory")
    if observed.get("one_live_parity_attempt_authorized") is not False:
        raise CityOpsContractError("observation must not authorize live parity")


def _assert_artifact_conservative(artifact: dict[str, Any]) -> None:
    readiness = artifact.get("readiness", {})
    for required in [
        "alternate_trusted_registry_client_installed",
        "platform_manifest_resolved",
        "oci_layout_created",
        "oci_layout_archive_created",
        "docker_load_performed",
        "first_required_image_present",
        "first_required_image_present_by_required_tag",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"artifact must record successful bridge field: {required}")
    for forbidden in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_reachable",
        "acontext_dashboard_reachable",
        "one_live_parity_attempt_authorized",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"promoted readiness: {forbidden}")
    if any(artifact.get("access_flags", {}).values()):
        raise CityOpsContractError("ORAS cache bridge must not enable access flags")
    gates = artifact.get("runtime_truth_gates", [])
    if any(gate.get("authorizes_live_attempt") for gate in gates):
        raise CityOpsContractError("ORAS cache bridge must not authorize live attempt")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"safe and blocked claim overlap: {sorted(overlap)}")
    required_blocked = set(ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_BLOCKED_CLAIMS)
    if not required_blocked <= set(do_not_claim_yet):
        raise CityOpsContractError("missing ORAS cache bridge blocked claims")
    forbidden_safe_fragments = [
        "cached_all_required_images",
        "started_compose",
        "reached_acontext_api",
        "reached_acontext_dashboard",
        "proved_runtime_parity",
        "authorizes_customer",
        "worker_skill_dna",
    ]
    for claim in safe_to_claim:
        if any(fragment in claim for fragment in forbidden_safe_fragments):
            raise CityOpsContractError(f"unsafe ORAS cache bridge safe claim: {claim}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
