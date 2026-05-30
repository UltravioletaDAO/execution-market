"""Crane export/load timeout observation for Acontext image caching.

This City-as-a-Service/AAS artifact records the May 29 23:11 EDT Fork A
follow-up after the 7 AM trusted cache-path probe.  A trusted export/load
registry client (`crane`) was installed and used for one bounded digest-pinned
pull attempt.  The pull timed out without creating a tarball or loading the
first required Acontext image, so Compose and live parity remain blocked.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_7am_trusted_cache_path_probe import (
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME,
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM,
    ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA,
    load_acontext_7am_trusted_cache_path_probe,
)
from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_digest_pinned_pull_timeout_observation import (
    FIRST_REQUIRED_IMAGE,
    FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
    FIRST_REQUIRED_IMAGE_CONFIG_DIGEST,
    FIRST_REQUIRED_IMAGE_INDEX_DIGEST,
    FIRST_REQUIRED_IMAGE_REPOSITORY,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCHEMA = (
    "city_ops.acontext_crane_export_load_timeout_observation.v1"
)
ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME = (
    "acontext_crane_export_load_timeout_observation.json"
)
ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM = (
    "admin_acontext_crane_export_load_timeout_observation_landed"
)
ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_ID = (
    "execution_market.aas.acontext_crane_export_load_timeout_observation.2026_05_29_2311"
)
ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCOPE = (
    "internal_admin_crane_export_load_attempt_only_no_compose_or_live_parity"
)
ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_VERDICT = (
    "crane_installed_bounded_digest_pull_timed_out_first_image_still_missing"
)

CRANE_TOOL = {
    "tool": "crane",
    "available": True,
    "path": "/opt/homebrew/bin/crane",
    "version": "0.21.6",
    "install_source": "Homebrew formula crane",
    "export_load_capable_for_local_image_cache": True,
}

ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_BLOCKED_CLAIMS = [
    "crane_export_load_attempt_cached_first_required_image",
    "crane_export_load_attempt_cached_all_required_images",
    "crane_export_load_attempt_created_image_tar",
    "crane_export_load_attempt_loaded_image_into_docker",
    "crane_export_load_attempt_resolved_docker_pull_stall",
    "crane_export_load_attempt_started_compose_services",
    "crane_export_load_attempt_reached_acontext_api",
    "crane_export_load_attempt_reached_acontext_dashboard",
    "crane_export_load_attempt_rebuilt_empty_readiness_gate",
    "crane_export_load_attempt_authorized_live_parity_attempt",
    "crane_export_load_attempt_completed_live_acontext_write",
    "crane_export_load_attempt_completed_live_acontext_retrieval",
    "crane_export_load_attempt_proved_runtime_parity",
    "crane_export_load_attempt_changes_irc_runtime_session_manager",
    "crane_export_load_attempt_enables_cross_project_autorouting",
    "crane_export_load_attempt_authorizes_customer_copy_delivery_or_publication",
    "crane_export_load_attempt_authorizes_public_or_catalog_route",
    "crane_export_load_attempt_authorizes_pricing_or_customer_quote",
    "crane_export_load_attempt_authorizes_queue_launch_or_dispatch",
    "crane_export_load_attempt_authorizes_erc8004_reputation_or_worker_skill_dna",
    "crane_export_load_attempt_reverifies_payment_or_production",
    "crane_export_load_attempt_allows_exact_gps_or_raw_metadata",
    "crane_export_load_attempt_grants_domain_or_emergency_authority",
    "crane_export_load_attempt_creates_worker_copyable_doctrine",
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


def build_may29_2311_crane_export_load_timeout_observation() -> dict[str, Any]:
    """Return sanitized facts from the bounded crane export/load attempt."""

    missing_required_images = [
        image for image in REQUIRED_ACONTEXT_IMAGES if image != "pgvector/pgvector:pg16"
    ]
    return {
        "observation_window": "2026-05-29T23:11:25-04:00/2026-05-29T23:14:25-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": (
            "attempt_fork_a_with_installed_trusted_crane_export_load_cache_path"
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
        "trusted_tool": CRANE_TOOL,
        "commands_observed": [
            "brew install crane",
            "crane version",
            "python subprocess timeout wrapper around crane digest --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest",
            (
                "python subprocess timeout wrapper around crane pull --platform linux/arm64 "
                "ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7 "
                "/tmp/acontext-ui-linux-arm64-ef6bdb2b.tar"
            ),
            "docker image inspect ghcr.io/memodb-io/acontext-ui:latest",
            (
                "docker image inspect ghcr.io/memodb-io/acontext-ui@"
                "sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7"
            ),
        ],
        "changed_cache_path_attempt": {
            "selected_path": "trusted_crane_registry_client_export_load_path",
            "attempted": True,
            "tool": "crane",
            "tool_version": "0.21.6",
            "registry_tool_install_performed": True,
            "digest_lookup_attempted": True,
            "digest_lookup_timeout_seconds": 90,
            "digest_lookup_timed_out": True,
            "digest_lookup_stdout_empty": True,
            "digest_lookup_stderr_empty": True,
            "digest_pinned_crane_pull_attempted": True,
            "digest_pinned_crane_pull_timeout_seconds": 180,
            "digest_pinned_crane_pull_timed_out": True,
            "digest_pinned_crane_pull_stdout_empty": True,
            "digest_pinned_crane_pull_stderr_empty": True,
            "image_tar_path": "/tmp/acontext-ui-linux-arm64-ef6bdb2b.tar",
            "image_tar_created": False,
            "image_tar_size_bytes": 0,
            "image_load_performed": False,
            "docker_tag_performed": False,
            "blind_tag_docker_pull_repeated": False,
            "digest_pinned_docker_pull_repeated": False,
            "compose_started": False,
            "stop_reason": (
                "crane_digest_lookup_and_digest_pinned_pull_timed_out_without_tar_or_local_image"
            ),
        },
        "docker": {
            "context": "desktop-linux",
            "daemon_available": True,
            "server_version": "29.1.3",
        },
        "image_inventory_after_attempt": {
            "checked": True,
            "first_required_image_present_by_tag": False,
            "first_required_image_present_by_digest": False,
            "present_required_images": ["pgvector/pgvector:pg16"],
            "missing_required_images": missing_required_images,
            "all_required_images_present": False,
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
        "readiness_gate_rebuilt_with_empty_blockers": False,
        "one_live_parity_attempt_authorized": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_crane_export_load_timeout_observation(
    *,
    artifact_dir: str | Path | None = None,
    trusted_cache_path_probe: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic crane export/load timeout observation artifact."""

    source = trusted_cache_path_probe or load_acontext_7am_trusted_cache_path_probe(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may29_2311_crane_export_load_timeout_observation()
    _assert_trusted_cache_path_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM,
            ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCHEMA,
        "observation_id": ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_ID,
        "scope": ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_SCOPE,
        "source_artifacts": {
            "trusted_cache_path_probe": {
                "file": ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME],
            "runtime_observation_performed": True,
            "installed_trusted_registry_client": True,
            "attempted_changed_cache_path": True,
            "repeats_blind_docker_pull": False,
            "repeats_digest_pinned_docker_pull": False,
            "starts_compose": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_VERDICT,
        "readiness": {
            "trusted_registry_client_installed": True,
            "trusted_export_load_cache_path_attempted": True,
            "crane_digest_lookup_timed_out": True,
            "crane_digest_pinned_pull_timed_out": True,
            "image_tar_created": False,
            "first_required_image_present": False,
            "all_required_images_present": False,
            "compose_services_started": False,
            "acontext_api_reachable": False,
            "acontext_dashboard_reachable": False,
            "one_live_parity_attempt_authorized": False,
        },
        "runtime_truth_gates": [
            {
                "gate": "trusted_registry_client_installed",
                "passed": True,
                "evidence": "crane 0.21.6 installed via Homebrew and present at /opt/homebrew/bin/crane",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "changed_cache_path_attempt_completed",
                "passed": False,
                "evidence": "crane digest and digest-pinned pull both timed out before creating a tarball",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "first_required_image_cached",
                "passed": False,
                "evidence": "docker inspect by tag and pinned digest remained absent after attempt",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "all_required_images_present",
                "passed": False,
                "evidence": "only pgvector/pgvector:pg16 is known present from required-image inventory",
                "authorizes_live_attempt": False,
            },
            {
                "gate": "single_live_write_retrieve_parity_attempt",
                "passed": False,
                "evidence": "not authorized until required images and local health gates pass",
                "authorizes_live_attempt": False,
            },
        ],
        "operator_guidance": {
            "safe_next_step": (
                "Do not repeat blind Docker pulls or the same crane path. Choose a different trusted acquisition path, "
                "such as a verified preloaded tar/OCI layout, alternate registry mirror, or network fix, then rerun inventory."
            ),
            "stop_line": (
                "Stop unless the exact first required Acontext UI image is present locally by tag or pinned digest."
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


def write_acontext_crane_export_load_timeout_observation(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the crane export/load timeout observation fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME
    artifact = build_acontext_crane_export_load_timeout_observation(artifact_dir=target_dir)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_crane_export_load_timeout_observation(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the crane export/load timeout observation fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = source_dir / ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_OBSERVATION_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact != build_acontext_crane_export_load_timeout_observation(
        artifact_dir=source_dir
    ):
        raise CityOpsContractError("crane export/load timeout observation fixture drift")
    return artifact


def _assert_trusted_cache_path_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA:
        raise CityOpsContractError("source must be 7am trusted cache-path probe")
    safe = source.get("claim_boundaries", {}).get("safe_to_claim", [])
    if ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("source missing trusted cache-path safe claim")
    readiness = source.get("readiness", {})
    if readiness.get("first_required_image_present") is not False:
        raise CityOpsContractError("source must still show first image missing")
    if readiness.get("one_live_parity_attempt_authorized") is not False:
        raise CityOpsContractError("source must not authorize live parity")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    attempt = observed.get("changed_cache_path_attempt", {})
    inventory = observed.get("image_inventory_after_attempt", {})
    if observed.get("trusted_tool", {}).get("tool") != "crane":
        raise CityOpsContractError("observation must identify crane as trusted tool")
    if observed.get("trusted_tool", {}).get("available") is not True:
        raise CityOpsContractError("observation must record crane availability")
    if attempt.get("attempted") is not True:
        raise CityOpsContractError("observation must record attempted changed cache path")
    if attempt.get("digest_pinned_crane_pull_timed_out") is not True:
        raise CityOpsContractError("observation must preserve crane pull timeout")
    if attempt.get("image_tar_created") is not False or attempt.get("image_load_performed") is not False:
        raise CityOpsContractError("observation must not claim tar creation or image load")
    if attempt.get("blind_tag_docker_pull_repeated") is not False:
        raise CityOpsContractError("observation must not repeat blind Docker tag pull")
    if attempt.get("digest_pinned_docker_pull_repeated") is not False:
        raise CityOpsContractError("observation must not repeat digest-pinned Docker pull")
    if attempt.get("compose_started") is not False:
        raise CityOpsContractError("observation must not start Compose")
    if inventory.get("first_required_image_present_by_tag") is not False:
        raise CityOpsContractError("observation must not claim first image by tag")
    if inventory.get("first_required_image_present_by_digest") is not False:
        raise CityOpsContractError("observation must not claim first image by digest")
    if inventory.get("all_required_images_present") is not False:
        raise CityOpsContractError("observation must not claim all images present")
    if observed.get("one_live_parity_attempt_authorized") is not False:
        raise CityOpsContractError("observation must not authorize live parity")


def _assert_artifact_conservative(artifact: dict[str, Any]) -> None:
    readiness = artifact.get("readiness", {})
    if readiness.get("trusted_registry_client_installed") is not True:
        raise CityOpsContractError("artifact must record installed trusted registry client")
    if readiness.get("trusted_export_load_cache_path_attempted") is not True:
        raise CityOpsContractError("artifact must record attempted changed cache path")
    for forbidden in [
        "image_tar_created",
        "first_required_image_present",
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_reachable",
        "acontext_dashboard_reachable",
        "one_live_parity_attempt_authorized",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"promoted readiness: {forbidden}")
    if any(artifact.get("access_flags", {}).values()):
        raise CityOpsContractError("crane timeout observation must not enable access flags")
    gates = artifact.get("runtime_truth_gates", [])
    if any(gate.get("authorizes_live_attempt") for gate in gates):
        raise CityOpsContractError("crane timeout observation must not authorize live attempt")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"safe and blocked claim overlap: {sorted(overlap)}")
    required_blocked = set(ACONTEXT_CRANE_EXPORT_LOAD_TIMEOUT_BLOCKED_CLAIMS)
    if not required_blocked <= set(do_not_claim_yet):
        raise CityOpsContractError("missing crane timeout blocked claims")
    forbidden_safe_fragments = [
        "cached_first_required_image",
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
            raise CityOpsContractError(f"unsafe crane timeout safe claim: {claim}")


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
