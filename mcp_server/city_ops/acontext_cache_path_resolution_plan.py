"""Acontext cache-path resolution plan for City-as-a-Service.

The May 29 image-cache path probe proved that repeating blind Docker pulls is
no longer useful: Docker stayed available, the first required Acontext image
remained absent, alternate registry/cache tooling was not installed locally, and
Buildx image-index inspection timed out.  This artifact converts that evidence
into a deterministic next-action plan without installing tooling, resetting
Docker Desktop, loading tarballs, starting Compose, writing/retrieving Acontext,
or promoting any customer/public/dispatch/reputation/runtime claims.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_image_cache_path_probe import (
    ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME,
    ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM,
    ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA,
    IMAGE_CACHE_PATH_PROBE_VERDICT,
    load_acontext_image_cache_path_probe,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA = (
    "city_ops.acontext_cache_path_resolution_plan.v1"
)
ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME = (
    "acontext_cache_path_resolution_plan.json"
)
ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM = (
    "admin_acontext_cache_path_resolution_plan_landed"
)

CACHE_PATH_RESOLUTION_PLAN_ID = (
    "execution_market.aas.acontext_cache_path_resolution_plan.2026_05_29_0100"
)
CACHE_PATH_RESOLUTION_PLAN_SCOPE = (
    "internal_admin_cache_path_resolution_plan_only_no_install_no_compose_or_live_parity"
)
CACHE_PATH_RESOLUTION_PLAN_VERDICT = (
    "trusted_registry_client_export_load_path_selected_as_next_changed_cache_path_but_not_executed"
)

CACHE_PATH_RESOLUTION_PLAN_BLOCKED_CLAIMS = [
    "cache_path_resolution_plan_installed_registry_tooling",
    "cache_path_resolution_plan_used_registry_tooling",
    "cache_path_resolution_plan_obtained_trusted_preloaded_tar",
    "cache_path_resolution_plan_configured_registry_mirror",
    "cache_path_resolution_plan_reset_docker_desktop_cache_or_networking",
    "cache_path_resolution_plan_completed_remote_builder_cache_export",
    "cache_path_resolution_plan_pulled_or_loaded_first_required_image",
    "cache_path_resolution_plan_cached_first_required_image",
    "cache_path_resolution_plan_cached_all_required_images",
    "cache_path_resolution_plan_started_compose_services",
    "cache_path_resolution_plan_reached_acontext_api",
    "cache_path_resolution_plan_reached_acontext_dashboard",
    "cache_path_resolution_plan_rebuilt_empty_readiness_gate",
    "cache_path_resolution_plan_authorized_live_parity_attempt",
    "cache_path_resolution_plan_completed_live_acontext_write",
    "cache_path_resolution_plan_completed_live_acontext_retrieval",
    "cache_path_resolution_plan_proved_runtime_parity",
    "cache_path_resolution_plan_changes_irc_runtime_session_manager",
    "cache_path_resolution_plan_enables_cross_project_autorouting",
    "cache_path_resolution_plan_authorizes_customer_copy_delivery_or_publication",
    "cache_path_resolution_plan_authorizes_public_or_catalog_route",
    "cache_path_resolution_plan_authorizes_pricing_or_customer_quote",
    "cache_path_resolution_plan_authorizes_queue_launch_or_dispatch",
    "cache_path_resolution_plan_authorizes_erc8004_reputation_or_worker_skill_dna",
    "cache_path_resolution_plan_reverifies_payment_or_production",
    "cache_path_resolution_plan_allows_exact_gps_or_raw_metadata",
    "cache_path_resolution_plan_grants_domain_or_emergency_authority",
    "cache_path_resolution_plan_creates_worker_copyable_doctrine",
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


def build_acontext_cache_path_resolution_plan(
    *,
    artifact_dir: str | Path | None = None,
    cache_path_probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic cache-path resolution plan artifact."""

    source = cache_path_probe or load_acontext_image_cache_path_probe(
        artifact_dir=artifact_dir
    )
    _assert_probe_source(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM,
            ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *CACHE_PATH_RESOLUTION_PLAN_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    selected = "trusted_registry_client_export_load_path"
    artifact = {
        "schema": ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA,
        "plan_id": CACHE_PATH_RESOLUTION_PLAN_ID,
        "scope": CACHE_PATH_RESOLUTION_PLAN_SCOPE,
        "source_artifacts": {
            "image_cache_path_probe": {
                "file": ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_IMAGE_CACHE_PATH_PROBE_FILENAME],
            "runtime_observation_performed": False,
            "repeats_blind_docker_pull": False,
            "installs_registry_tooling": False,
            "uses_registry_tooling": False,
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
        "resolution_options": _resolution_options(),
        "selected_next_changed_cache_path": selected,
        "selection_reason": (
            "The probe showed no local registry/cache tools and no trusted tar/mirror/remote cache. "
            "A trusted registry-client export/load path is the least destructive changed path because "
            "it can be bounded, logged, and verified by image inventory before Compose is touched."
        ),
        "operator_preflight_checklist": _operator_preflight_checklist(selected),
        "post_selection_gate_order": _post_selection_gate_order(),
        "readiness": _readiness(source),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "plan_verdict": CACHE_PATH_RESOLUTION_PLAN_VERDICT,
        "operator_instruction": (
            "Treat this as a plan, not execution. The next implementation may install/use exactly "
            "one trusted registry client or equivalent trusted cache path, then must rerun image "
            "inventory and stop unless the first required Acontext image is actually present locally."
        ),
    }
    _assert_artifact_conservative(artifact, source)
    return artifact


def write_acontext_cache_path_resolution_plan(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic cache-path resolution plan fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_cache_path_resolution_plan(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def load_acontext_cache_path_resolution_plan(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted cache-path resolution plan."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifact = json.loads(
        (base_dir / ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source = load_acontext_image_cache_path_probe(artifact_dir=base_dir)
    _assert_artifact_conservative(artifact, source)
    if artifact != build_acontext_cache_path_resolution_plan(
        artifact_dir=base_dir, cache_path_probe=source
    ):
        raise CityOpsContractError("Acontext cache-path resolution plan drifted")
    return artifact


def _resolution_options() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "option": "trusted_registry_client_export_load_path",
            "status": "recommended_next_changed_path_not_executed",
            "candidate_tools": ["crane", "oras", "skopeo", "regctl"],
            "why": (
                "Produces a bounded inspect/copy/load path with explicit logs and local image-inventory "
                "verification, without resetting Docker Desktop or trusting an opaque tarball."
            ),
            "requires_operator_approval_before_execution": True,
            "executes_in_this_artifact": False,
            "authorizes_compose_startup": False,
            "authorizes_live_parity": False,
        },
        {
            "rank": 2,
            "option": "trusted_preloaded_image_tar",
            "status": "acceptable_if_source_digest_and_provenance_are_known_not_available_now",
            "why": (
                "Can bypass the Docker pull path, but only if provenance and digests are explicit."
            ),
            "requires_operator_approval_before_execution": True,
            "executes_in_this_artifact": False,
            "authorizes_compose_startup": False,
            "authorizes_live_parity": False,
        },
        {
            "rank": 3,
            "option": "verified_remote_builder_or_cache_export",
            "status": "acceptable_if_existing_trusted_builder_exists_not_available_now",
            "why": (
                "Useful when local Docker pull path stalls, but it adds remote trust and cache-export handling."
            ),
            "requires_operator_approval_before_execution": True,
            "executes_in_this_artifact": False,
            "authorizes_compose_startup": False,
            "authorizes_live_parity": False,
        },
        {
            "rank": 4,
            "option": "registry_mirror_configuration",
            "status": "defer_until_lower_touch_paths_fail",
            "why": (
                "Potentially durable fix, but changes Docker registry routing and should not be first."
            ),
            "requires_operator_approval_before_execution": True,
            "executes_in_this_artifact": False,
            "authorizes_compose_startup": False,
            "authorizes_live_parity": False,
        },
        {
            "rank": 5,
            "option": "docker_desktop_network_or_cache_reset",
            "status": "operator_maintenance_only_last_resort",
            "why": (
                "Most invasive local-maintenance path; can disrupt unrelated containers and should only happen explicitly."
            ),
            "requires_operator_approval_before_execution": True,
            "executes_in_this_artifact": False,
            "authorizes_compose_startup": False,
            "authorizes_live_parity": False,
        },
    ]


def _operator_preflight_checklist(selected: str) -> dict[str, Any]:
    return {
        "selected_path": selected,
        "must_confirm_before_execution": [
            "which exact trusted tool or cache source will be used",
            "how the tool/source was obtained and whether it requires installation",
            "the exact required image list and platform target",
            "where image tar/cache output will be written if any",
            "how local image presence will be verified after the attempt",
            "that Compose startup remains blocked until all required images are present",
        ],
        "first_required_image": "ghcr.io/memodb-io/acontext-ui:latest",
        "platform": "linux/arm64",
        "stop_conditions": [
            "registry-client install or invocation fails",
            "image copy/export/load fails or emits ambiguous provenance",
            "first required image is still absent after the attempt",
            "any API/dashboard/runtime parity claim appears before service health is green",
            "any customer/public/dispatch/reputation/payment/GPS/domain/worker-doctrine claim is introduced",
        ],
    }


def _post_selection_gate_order() -> list[dict[str, Any]]:
    return [
        {
            "gate": "operator_cache_path_selection",
            "status": "selected_for_next_slice_not_executed",
            "passed": True,
            "authorizes_next_gate": "bounded_trusted_registry_client_or_equivalent_cache_attempt",
            "authorizes_compose_startup": False,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "bounded_cache_attempt_execution",
            "status": "pending_separate_execution_artifact",
            "passed": False,
            "authorizes_compose_startup": False,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "first_required_image_inventory",
            "status": "blocked_until_acontext_ui_present_locally",
            "passed": False,
            "authorizes_compose_startup": False,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "all_required_images_inventory",
            "status": "blocked_until_all_required_images_present_locally",
            "passed": False,
            "authorizes_compose_startup": False,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "local_acontext_services_health",
            "status": "blocked_until_compose_started_after_full_image_inventory",
            "passed": False,
            "authorizes_compose_startup": False,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "read_only_preflight_rebuild",
            "status": "blocked_until_api_and_dashboard_health_are_green",
            "passed": False,
            "authorizes_compose_startup": False,
            "authorizes_live_attempt": False,
        },
        {
            "gate": "single_live_write_retrieve_parity_attempt",
            "status": "not_authorized",
            "passed": False,
            "authorizes_compose_startup": False,
            "authorizes_live_attempt": False,
        },
    ]


def _readiness(source: dict[str, Any]) -> dict[str, bool]:
    source_readiness = source.get("readiness", {})
    return {
        "cache_path_resolution_plan_landed": True,
        "image_cache_path_probe_source_verified": True,
        "docker_daemon_available_from_source": source_readiness.get("docker_daemon_available")
        is True,
        "selected_next_changed_cache_path": True,
        "registry_tool_installed": False,
        "registry_tool_used": False,
        "trusted_preloaded_tar_available": False,
        "registry_mirror_configured": False,
        "remote_builder_cache_export_available": False,
        "docker_desktop_cache_or_network_reset_performed": False,
        "first_required_image_present": False,
        "all_required_images_present": False,
        "compose_services_started": False,
        "acontext_api_reachable": False,
        "acontext_dashboard_reachable": False,
        "readiness_gate_rebuilt_empty": False,
        "one_live_parity_attempt_authorized": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
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


def _assert_probe_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_IMAGE_CACHE_PATH_PROBE_SCHEMA:
        raise CityOpsContractError("invalid image-cache path probe schema")
    if source.get("observation_verdict") != IMAGE_CACHE_PATH_PROBE_VERDICT:
        raise CityOpsContractError("image-cache path probe verdict drift")
    if ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("image-cache path probe missing safe claim")
    readiness = source.get("readiness", {})
    if readiness.get("docker_daemon_available") is not True:
        raise CityOpsContractError("source did not preserve Docker daemon availability")
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


def _assert_artifact_conservative(
    artifact: dict[str, Any], source: dict[str, Any]
) -> None:
    if artifact.get("schema") != ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA:
        raise CityOpsContractError("invalid cache-path resolution plan schema")
    _assert_probe_source(source)
    if artifact.get("plan_verdict") != CACHE_PATH_RESOLUTION_PLAN_VERDICT:
        raise CityOpsContractError("cache-path resolution plan verdict drift")
    if artifact.get("selected_next_changed_cache_path") != (
        "trusted_registry_client_export_load_path"
    ):
        raise CityOpsContractError("unexpected cache path selected")
    derived = artifact.get("derived_from", {})
    for flag in [
        "runtime_observation_performed",
        "repeats_blind_docker_pull",
        "installs_registry_tooling",
        "uses_registry_tooling",
        "configures_registry_mirror",
        "loads_prebuilt_image_tar",
        "resets_docker_desktop_cache_or_networking",
        "pulls_container_image",
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
            raise CityOpsContractError(f"derived section promoted forbidden flag: {flag}")
    options = artifact.get("resolution_options", [])
    if [option.get("rank") for option in options] != [1, 2, 3, 4, 5]:
        raise CityOpsContractError("resolution option ranking drift")
    if options[0].get("option") != "trusted_registry_client_export_load_path":
        raise CityOpsContractError("first resolution option drift")
    if any(option.get("executes_in_this_artifact") is not False for option in options):
        raise CityOpsContractError("resolution plan must not execute options")
    if any(option.get("authorizes_live_parity") is not False for option in options):
        raise CityOpsContractError("resolution plan must not authorize live parity")
    gates = artifact.get("post_selection_gate_order", [])
    if [gate.get("gate") for gate in gates] != [
        "operator_cache_path_selection",
        "bounded_cache_attempt_execution",
        "first_required_image_inventory",
        "all_required_images_inventory",
        "local_acontext_services_health",
        "read_only_preflight_rebuild",
        "single_live_write_retrieve_parity_attempt",
    ]:
        raise CityOpsContractError("post-selection gate order drift")
    if gates[0].get("passed") is not True:
        raise CityOpsContractError("selection gate should be passed")
    if any(gate.get("passed") is True for gate in gates[1:]):
        raise CityOpsContractError("post-selection execution gates must remain blocked")
    if any(gate.get("authorizes_live_attempt") is True for gate in gates):
        raise CityOpsContractError("resolution plan must not authorize live attempt")
    readiness = artifact.get("readiness", {})
    for flag in [
        "registry_tool_installed",
        "registry_tool_used",
        "trusted_preloaded_tar_available",
        "registry_mirror_configured",
        "remote_builder_cache_export_available",
        "docker_desktop_cache_or_network_reset_performed",
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
