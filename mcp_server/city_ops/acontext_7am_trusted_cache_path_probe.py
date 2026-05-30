"""7 AM trusted cache-path probe observation for Acontext.

This City-as-a-Service/AAS artifact records the May 29 07:04 EDT Fork A
cache-path check after the 6 AM final wrap.  The probe intentionally did not
repeat a blind tag pull and did not start Compose.  It verified local trusted
registry/cache tooling and image inventory, then stopped because no installed
export/load-capable registry client was available for the pinned linux/arm64
Acontext UI image.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_digest_pinned_pull_timeout_observation import (
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME,
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
    ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA,
    DIGEST_PINNED_PULL_TIMEOUT_VERDICT,
    FIRST_REQUIRED_IMAGE,
    FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
    FIRST_REQUIRED_IMAGE_CONFIG_DIGEST,
    FIRST_REQUIRED_IMAGE_INDEX_DIGEST,
    FIRST_REQUIRED_IMAGE_REPOSITORY,
    load_acontext_digest_pinned_pull_timeout_observation,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA = (
    "city_ops.acontext_7am_trusted_cache_path_probe.v1"
)
ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME = (
    "acontext_7am_trusted_cache_path_probe.json"
)
ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM = (
    "admin_acontext_7am_trusted_cache_path_probe_landed"
)

ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_ID = (
    "execution_market.aas.acontext_7am_trusted_cache_path_probe.2026_05_29_0704"
)
ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCOPE = (
    "internal_admin_trusted_cache_path_probe_only_no_pull_no_compose_or_live_parity"
)
ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_VERDICT = (
    "no_installed_export_load_capable_registry_client_first_image_still_missing"
)

EXPORT_LOAD_TOOLS = ["crane", "oras", "skopeo", "regctl"]
METADATA_ONLY_TOOLS = ["docker_buildx_imagetools"]

ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_BLOCKED_CLAIMS = [
    "trusted_cache_path_probe_used_crane_oras_skopeo_or_regctl",
    "trusted_cache_path_probe_exported_image_tar_or_oci_layout",
    "trusted_cache_path_probe_loaded_first_required_image",
    "trusted_cache_path_probe_cached_first_required_image",
    "trusted_cache_path_probe_cached_all_required_images",
    "trusted_cache_path_probe_resolved_docker_pull_stall",
    "trusted_cache_path_probe_started_compose_services",
    "trusted_cache_path_probe_reached_acontext_api",
    "trusted_cache_path_probe_reached_acontext_dashboard",
    "trusted_cache_path_probe_rebuilt_empty_readiness_gate",
    "trusted_cache_path_probe_authorized_live_parity_attempt",
    "trusted_cache_path_probe_completed_live_acontext_write",
    "trusted_cache_path_probe_completed_live_acontext_retrieval",
    "trusted_cache_path_probe_proved_runtime_parity",
    "trusted_cache_path_probe_changes_irc_runtime_session_manager",
    "trusted_cache_path_probe_enables_cross_project_autorouting",
    "trusted_cache_path_probe_authorizes_customer_copy_delivery_or_publication",
    "trusted_cache_path_probe_authorizes_public_or_catalog_route",
    "trusted_cache_path_probe_authorizes_pricing_or_customer_quote",
    "trusted_cache_path_probe_authorizes_queue_launch_or_dispatch",
    "trusted_cache_path_probe_authorizes_erc8004_reputation_or_worker_skill_dna",
    "trusted_cache_path_probe_reverifies_payment_or_production",
    "trusted_cache_path_probe_allows_exact_gps_or_raw_metadata",
    "trusted_cache_path_probe_grants_domain_or_emergency_authority",
    "trusted_cache_path_probe_creates_worker_copyable_doctrine",
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


def build_may29_0704_trusted_cache_path_probe_observation() -> dict[str, Any]:
    """Return the sanitized 7 AM trusted cache-path probe facts."""

    missing_required_images = [
        image for image in REQUIRED_ACONTEXT_IMAGES if image != "pgvector/pgvector:pg16"
    ]
    return {
        "observation_window": "2026-05-29T07:03:56-04:00/2026-05-29T07:04:20-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": (
            "attempt_fork_a_by_checking_for_one_installed_trusted_export_load_cache_path"
        ),
        "sanitization_policy": {
            "include_tokens": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "commands_observed": [
            "command -v crane oras skopeo regctl nerdctl docker",
            "docker buildx version",
            "docker context show",
            "docker image inspect ghcr.io/memodb-io/acontext-ui:latest",
            (
                "docker image inspect ghcr.io/memodb-io/acontext-ui@"
                "sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7"
            ),
            "docker image ls --format <repository-tag-id-age-size> filtered to Acontext required images",
        ],
        "pinned_image": {
            "image": FIRST_REQUIRED_IMAGE,
            "repository": FIRST_REQUIRED_IMAGE_REPOSITORY,
            "platform": "linux/arm64",
            "index_digest": FIRST_REQUIRED_IMAGE_INDEX_DIGEST,
            "manifest_digest": FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST,
            "config_digest": FIRST_REQUIRED_IMAGE_CONFIG_DIGEST,
        },
        "trusted_tool_inventory": {
            "export_load_tools": [
                {"tool": tool, "available": False, "path": None}
                for tool in EXPORT_LOAD_TOOLS
            ],
            "metadata_only_tools": [
                {
                    "tool": "docker_buildx_imagetools",
                    "available": True,
                    "path": "/usr/local/bin/docker buildx imagetools",
                    "version": "github.com/docker/buildx v0.30.1-desktop.1",
                    "export_load_capable_for_local_image_cache": False,
                    "reason_not_used": (
                        "imagetools can inspect/copy registry manifests but does not provide a "
                        "bounded local export/load path for the pinned image without changing into "
                        "another pull/build path; the prior metadata inspect path already timed out."
                    ),
                }
            ],
            "other_local_tools_checked": [
                {"tool": "nerdctl", "available": False, "path": None},
                {"tool": "docker", "available": True, "path": "/usr/local/bin/docker"},
            ],
            "trusted_export_load_tool_available": False,
        },
        "changed_cache_path_attempt": {
            "selected_path": "trusted_registry_client_export_load_path",
            "attempted": False,
            "stop_reason": "no_installed_export_load_capable_trusted_registry_client",
            "blind_tag_pull_repeated": False,
            "digest_pinned_docker_pull_repeated": False,
            "registry_tool_install_performed": False,
            "image_blob_download_performed": False,
            "image_tar_or_oci_layout_created": False,
            "image_load_performed": False,
            "compose_started": False,
        },
        "docker": {
            "context": "desktop-linux",
            "daemon_available": True,
            "server_os_arch": "linux/arm64",
        },
        "image_inventory_after_probe": {
            "checked": True,
            "first_required_image_present_by_tag": False,
            "first_required_image_present_by_digest": False,
            "present_required_images": ["pgvector/pgvector:pg16"],
            "missing_required_images": missing_required_images,
            "all_required_images_present": False,
        },
        "containers": {"checked": False, "reason": "compose_start_forbidden_by_probe"},
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


def build_acontext_7am_trusted_cache_path_probe(
    *,
    artifact_dir: str | Path | None = None,
    digest_pinned_observation: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic 7 AM trusted cache-path probe artifact."""

    source = digest_pinned_observation or load_acontext_digest_pinned_pull_timeout_observation(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may29_0704_trusted_cache_path_probe_observation()
    _assert_digest_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
            ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA,
        "observation_id": ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_ID,
        "scope": ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCOPE,
        "source_artifacts": {
            "digest_pinned_pull_timeout_observation": {
                "file": ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_FILENAME],
            "runtime_observation_performed": True,
            "checks_installed_trusted_tools": True,
            "checks_local_image_inventory": True,
            "repeats_blind_docker_pull": False,
            "repeats_digest_pinned_docker_pull": False,
            "installs_registry_tooling": False,
            "uses_export_load_registry_tooling": False,
            "downloads_image_blobs": False,
            "creates_image_tar_or_oci_layout": False,
            "loads_container_image": False,
            "starts_compose_services": False,
            "checks_api_or_dashboard_health": False,
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
        "runtime_observation": observed,
        "readiness": _readiness(observed),
        "runtime_truth_gates": _runtime_truth_gates(observed),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "observation_verdict": ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_VERDICT,
        "operator_instruction": (
            "Stop here: no installed export/load-capable trusted registry client was found. "
            "Do not repeat blind docker pulls, do not start Compose, and do not claim Acontext "
            "API/dashboard/live parity until the first required image is actually present locally."
        ),
        "operator_next_actions": [
            "Use a real trusted export/load-capable registry client or trusted preloaded tar before the next cache attempt.",
            "Preserve the pinned linux/arm64 manifest digest as provenance for any future cache path.",
            "Rerun local image inventory after any future changed cache path.",
            "Start Compose only after all required images are present locally.",
            "Attempt live parity only after API/dashboard health and a rebuilt readiness gate authorize it.",
        ],
    }
    _assert_artifact_conservative(artifact, source)
    return artifact


def write_acontext_7am_trusted_cache_path_probe(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic 7 AM trusted cache-path probe fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_7am_trusted_cache_path_probe(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def load_acontext_7am_trusted_cache_path_probe(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted 7 AM trusted cache-path probe."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifact = json.loads(
        (base_dir / ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source = load_acontext_digest_pinned_pull_timeout_observation(artifact_dir=base_dir)
    _assert_artifact_conservative(artifact, source)
    if artifact != build_acontext_7am_trusted_cache_path_probe(
        artifact_dir=base_dir, digest_pinned_observation=source
    ):
        raise CityOpsContractError("Acontext 7 AM trusted cache-path probe drifted")
    return artifact


def _readiness(observation: dict[str, Any]) -> dict[str, bool]:
    inventory = observation["image_inventory_after_probe"]
    tool_inventory = observation["trusted_tool_inventory"]
    attempt = observation["changed_cache_path_attempt"]
    return {
        "digest_pinned_source_verified": True,
        "trusted_tool_inventory_checked": True,
        "trusted_export_load_tool_available": tool_inventory[
            "trusted_export_load_tool_available"
        ],
        "trusted_export_load_cache_path_attempted": attempt["attempted"],
        "trusted_export_load_cache_path_completed": False,
        "first_required_image_present": inventory["first_required_image_present_by_tag"]
        or inventory["first_required_image_present_by_digest"],
        "all_required_images_present": inventory["all_required_images_present"],
        "compose_services_started": attempt["compose_started"],
        "acontext_api_reachable": False,
        "acontext_dashboard_reachable": False,
        "readiness_gate_rebuilt_empty": observation[
            "readiness_gate_rebuilt_with_empty_blockers"
        ],
        "one_live_parity_attempt_authorized": observation[
            "one_live_parity_attempt_authorized"
        ],
        "live_acontext_write_performed": observation["live_acontext_write_performed"],
        "live_acontext_retrieval_performed": observation[
            "live_acontext_retrieval_performed"
        ],
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
        "erc8004_reputation_ready": False,
        "worker_skill_dna_ready": False,
        "payment_or_production_reverified": False,
        "exact_gps_or_raw_metadata_release_ready": False,
        "domain_authority_ready": False,
        "worker_copyable_doctrine_ready": False,
        "trusted_cache_path_probe_landed": True,
    }


def _runtime_truth_gates(observation: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = observation["image_inventory_after_probe"]
    return [
        {
            "gate": "digest_pinned_source_artifact",
            "passed": True,
            "authorizes_live_attempt": False,
            "status": "passed_source_digest_locked_before_this_probe",
        },
        {
            "gate": "trusted_export_load_tool_inventory",
            "passed": False,
            "authorizes_live_attempt": False,
            "status": "blocked_no_installed_export_load_capable_registry_client",
            "evidence": observation["trusted_tool_inventory"]["export_load_tools"],
        },
        {
            "gate": "changed_cache_path_attempt",
            "passed": False,
            "authorizes_live_attempt": False,
            "status": "not_attempted_no_export_load_tool_present",
            "evidence": observation["changed_cache_path_attempt"]["stop_reason"],
        },
        {
            "gate": "first_required_image_cached",
            "passed": False,
            "authorizes_live_attempt": False,
            "status": "blocked_first_required_image_still_missing",
            "evidence": {
                "by_tag": inventory["first_required_image_present_by_tag"],
                "by_digest": inventory["first_required_image_present_by_digest"],
            },
        },
        {
            "gate": "all_required_images_present",
            "passed": False,
            "authorizes_live_attempt": False,
            "status": "blocked_missing_required_images",
            "evidence": inventory["missing_required_images"],
        },
        {
            "gate": "single_live_write_retrieve_parity_attempt",
            "passed": False,
            "authorizes_live_attempt": False,
            "status": "not_authorized",
        },
    ]


def _assert_digest_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_DIGEST_PINNED_PULL_TIMEOUT_OBSERVATION_SCHEMA:
        raise CityOpsContractError("Acontext 7 AM probe source schema mismatch")
    if source.get("observation_verdict") != DIGEST_PINNED_PULL_TIMEOUT_VERDICT:
        raise CityOpsContractError("Acontext 7 AM probe source verdict mismatch")
    readiness = source.get("readiness", {})
    if not readiness.get("registry_manifest_digest_locked"):
        raise CityOpsContractError("Acontext 7 AM probe source missing digest lock")
    if readiness.get("first_required_image_present"):
        raise CityOpsContractError("Acontext 7 AM probe source unexpectedly has image")
    runtime = source.get("runtime_observation", {})
    manifest = runtime.get("registry_manifest_lock", {})
    if manifest.get("manifest_digest") != FIRST_REQUIRED_IMAGE_ARM64_MANIFEST_DIGEST:
        raise CityOpsContractError("Acontext 7 AM probe source digest mismatch")


def _assert_observation_conservative(observation: dict[str, Any]) -> None:
    tools = observation.get("trusted_tool_inventory", {})
    attempt = observation.get("changed_cache_path_attempt", {})
    inventory = observation.get("image_inventory_after_probe", {})
    if tools.get("trusted_export_load_tool_available") is not False:
        raise CityOpsContractError("Acontext 7 AM probe must not claim export/load tool availability")
    if attempt.get("attempted") is not False:
        raise CityOpsContractError("Acontext 7 AM probe must stop before cache attempt")
    forbidden_true = [
        "blind_tag_pull_repeated",
        "digest_pinned_docker_pull_repeated",
        "registry_tool_install_performed",
        "image_blob_download_performed",
        "image_tar_or_oci_layout_created",
        "image_load_performed",
        "compose_started",
    ]
    for key in forbidden_true:
        if attempt.get(key):
            raise CityOpsContractError(f"Acontext 7 AM probe promoted forbidden action: {key}")
    if inventory.get("first_required_image_present_by_tag"):
        raise CityOpsContractError("Acontext 7 AM probe must not claim tag image presence")
    if inventory.get("first_required_image_present_by_digest"):
        raise CityOpsContractError("Acontext 7 AM probe must not claim digest image presence")
    if inventory.get("all_required_images_present"):
        raise CityOpsContractError("Acontext 7 AM probe must not claim all images present")
    if observation.get("readiness_gate_rebuilt_with_empty_blockers"):
        raise CityOpsContractError("Acontext 7 AM probe must not rebuild readiness")
    if observation.get("one_live_parity_attempt_authorized"):
        raise CityOpsContractError("Acontext 7 AM probe must not authorize live parity")
    if observation.get("live_acontext_write_performed"):
        raise CityOpsContractError("Acontext 7 AM probe must not write live Acontext")
    if observation.get("live_acontext_retrieval_performed"):
        raise CityOpsContractError("Acontext 7 AM probe must not retrieve live Acontext")


def _assert_artifact_conservative(artifact: dict[str, Any], source: dict[str, Any]) -> None:
    _assert_digest_source(source)
    if artifact.get("schema") != ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SCHEMA:
        raise CityOpsContractError("Acontext 7 AM probe schema mismatch")
    if artifact.get("observation_verdict") != ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_VERDICT:
        raise CityOpsContractError("Acontext 7 AM probe verdict mismatch")
    _assert_observation_conservative(artifact.get("runtime_observation", {}))
    derived = artifact.get("derived_from", {})
    forbidden_derived = [
        "repeats_blind_docker_pull",
        "repeats_digest_pinned_docker_pull",
        "installs_registry_tooling",
        "uses_export_load_registry_tooling",
        "downloads_image_blobs",
        "creates_image_tar_or_oci_layout",
        "loads_container_image",
        "starts_compose_services",
        "checks_api_or_dashboard_health",
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
    ]
    for key in forbidden_derived:
        if derived.get(key):
            raise CityOpsContractError(f"Acontext 7 AM probe derived field must stay false: {key}")
    readiness = artifact.get("readiness", {})
    promoted_readiness = [
        "trusted_export_load_tool_available",
        "trusted_export_load_cache_path_attempted",
        "trusted_export_load_cache_path_completed",
        "first_required_image_present",
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_reachable",
        "acontext_dashboard_reachable",
        "readiness_gate_rebuilt_empty",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "memory_acontext_parity_ready",
        "customer_copy_ready",
        "customer_delivery_ready",
        "publication_ready",
        "public_or_catalog_route_ready",
        "pricing_or_customer_quote_ready",
        "operator_queue_launch_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "payment_or_production_reverified",
        "exact_gps_or_raw_metadata_release_ready",
        "domain_authority_ready",
        "worker_copyable_doctrine_ready",
    ]
    for key in promoted_readiness:
        if readiness.get(key):
            raise CityOpsContractError(f"Acontext 7 AM probe promoted readiness: {key}")
    gates = artifact.get("runtime_truth_gates", [])
    if any(gate.get("authorizes_live_attempt") for gate in gates):
        raise CityOpsContractError("Acontext 7 AM probe must not authorize live attempts")
    if set(artifact.get("claim_boundaries", {}).get("safe_to_claim", [])) & set(
        artifact.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    ):
        raise CityOpsContractError("Acontext 7 AM probe claim boundary overlap")
    access = artifact.get("access_policy", {})
    for key in _FALSE_ACCESS_FLAGS:
        if access.get(key):
            raise CityOpsContractError(f"Acontext 7 AM probe promoted access flag: {key}")


def _assert_claim_boundaries(safe: list[str], blocked: list[str]) -> None:
    if ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("Acontext 7 AM probe safe claim missing")
    if set(ACONTEXT_7AM_TRUSTED_CACHE_PATH_PROBE_BLOCKED_CLAIMS) - set(blocked):
        raise CityOpsContractError("Acontext 7 AM probe blocked claims missing")
    if set(safe) & set(blocked):
        raise CityOpsContractError("Acontext 7 AM probe safe/blocked overlap")


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
