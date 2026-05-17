"""Acontext registry manifest / Docker pull-stall diagnostic for City-as-a-Service.

This artifact records the May 17 01:02 EDT bounded diagnostic that followed the
individual image-pull timeout probe.  The important distinction is narrow:
GHCR anonymous token + manifest fetches succeeded for the three Acontext images
and advertised linux/arm64 manifests, while Docker Desktop still produced a
silent 45s pull timeout for the first image.

It is internal/admin prerequisite evidence only.  It does not start services,
does not write to or retrieve from Acontext, does not rebuild the readiness gate,
and does not authorize customer/public AAS packaging, dispatch, reputation,
payment, production, GPS/raw metadata, or worker-copyable doctrine claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_individual_image_pull_timeout_probe import (
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME,
    ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM,
    INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_BLOCKED_CLAIMS,
    load_acontext_individual_image_pull_timeout_probe,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SCHEMA = (
    "city_ops.acontext_registry_manifest_pull_stall_diagnostic.v1"
)
ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME = (
    "acontext_registry_manifest_pull_stall_diagnostic.json"
)
ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM = (
    "admin_acontext_registry_manifest_pull_stall_diagnostic_landed"
)

ACONTEXT_GHCR_IMAGES = [
    "ghcr.io/memodb-io/acontext-ui:latest",
    "ghcr.io/memodb-io/acontext-api:latest",
    "ghcr.io/memodb-io/acontext-core:latest",
]

REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_BLOCKED_CLAIMS = [
    *INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_BLOCKED_CLAIMS,
    "registry_manifest_success_implies_docker_pull_success",
    "linux_arm64_manifest_success_implies_local_image_present",
    "docker_desktop_pull_stall_resolved_by_manifest_probe",
    "first_required_image_pulled_by_manifest_diagnostic",
    "all_required_images_attempted_by_manifest_diagnostic",
    "all_required_images_present_by_manifest_diagnostic",
    "compose_services_started_by_manifest_diagnostic",
    "acontext_api_reachable_by_manifest_diagnostic",
    "acontext_dashboard_reachable_by_manifest_diagnostic",
    "readiness_gate_rebuilt_empty_by_manifest_diagnostic",
    "live_acontext_write_completed_by_manifest_diagnostic",
    "live_acontext_retrieval_completed_by_manifest_diagnostic",
    "runtime_parity_proven_by_manifest_diagnostic",
    "customer_visible_aas_packaging_ready_by_manifest_diagnostic",
    "public_route_ready_by_manifest_diagnostic",
    "operator_queue_launch_ready_by_manifest_diagnostic",
    "dispatch_ready_by_manifest_diagnostic",
    "erc8004_reputation_ready_by_manifest_diagnostic",
    "payment_or_production_reverified_by_manifest_diagnostic",
    "gps_or_raw_metadata_release_allowed_by_manifest_diagnostic",
    "worker_copyable_doctrine_ready_by_manifest_diagnostic",
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
    "all_required_images_attempted",
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


def build_may17_0102_registry_manifest_pull_stall_observation() -> dict[str, Any]:
    """Return the deterministic May 17 01:02 registry/pull-stall observation."""

    return {
        "observation_window": "2026-05-17T01:01:51-04:00/2026-05-17T01:03:12-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/infra/acontext",
        "diagnostic_reason": "diagnose_docker_pull_stall_after_individual_image_timeout",
        "docker_environment": {
            "docker_context": "desktop-linux",
            "client_version": "29.1.3",
            "server_version": "29.1.3",
            "server_arch": "arm64",
            "docker_desktop_version": "4.57.0",
        },
        "registry_endpoint_checks": [
            {
                "endpoint": "https://ghcr.io/v2/",
                "method": "HEAD",
                "http_status": 405,
                "reachable": True,
                "meaning": "registry_base_responded_but_does_not_prove_image_pull_success",
            },
            {
                "endpoint": "https://registry-1.docker.io/v2/",
                "method": "HEAD",
                "http_status": 401,
                "reachable": True,
                "meaning": "dockerhub_base_responded_but_does_not_prove_image_pull_success",
            },
            {
                "endpoint": "https://ghcr.io/v2/memodb-io/acontext-ui/manifests/latest",
                "method": "HEAD",
                "http_status": 401,
                "reachable": True,
                "auth_challenge_present": True,
                "meaning": "image_manifest_requires_bearer_token_before_manifest_fetch",
            },
        ],
        "ghcr_manifest_checks": [
            {
                "image": "ghcr.io/memodb-io/acontext-ui:latest",
                "anonymous_bearer_token_received": True,
                "manifest_http_status": 200,
                "media_type": "application/vnd.oci.image.index.v1+json",
                "schema_version": 2,
                "platforms": ["linux/amd64", "linux/arm64", "unknown/unknown", "unknown/unknown"],
                "linux_arm64_manifest_advertised": True,
                "manifest_fetch_succeeded": True,
            },
            {
                "image": "ghcr.io/memodb-io/acontext-api:latest",
                "anonymous_bearer_token_received": True,
                "manifest_http_status": 200,
                "media_type": "application/vnd.oci.image.index.v1+json",
                "schema_version": 2,
                "platforms": ["linux/amd64", "linux/arm64", "unknown/unknown", "unknown/unknown"],
                "linux_arm64_manifest_advertised": True,
                "manifest_fetch_succeeded": True,
            },
            {
                "image": "ghcr.io/memodb-io/acontext-core:latest",
                "anonymous_bearer_token_received": True,
                "manifest_http_status": 200,
                "media_type": "application/vnd.oci.image.index.v1+json",
                "schema_version": 2,
                "platforms": ["linux/amd64", "linux/arm64", "unknown/unknown", "unknown/unknown"],
                "linux_arm64_manifest_advertised": True,
                "manifest_fetch_succeeded": True,
            },
        ],
        "docker_pull_stall_check": {
            "image": "ghcr.io/memodb-io/acontext-ui:latest",
            "command": "docker --debug pull ghcr.io/memodb-io/acontext-ui:latest",
            "timeout_seconds": 45,
            "duration_seconds": 45.01,
            "timed_out": True,
            "exit_code": None,
            "stdout_tail": [],
            "stderr_tail": [],
            "pulled_or_present_after_check": False,
        },
        "local_images_observed_after_diagnostic": ["pgvector/pgvector:pg16"],
        "services_started": False,
        "api_checked_after_diagnostic": False,
        "dashboard_checked_after_diagnostic": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
    }


def build_acontext_registry_manifest_pull_stall_diagnostic(
    *,
    artifact_dir: str | Path | None = None,
    individual_probe: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed registry-manifest / Docker pull-stall diagnostic."""

    source = individual_probe or load_acontext_individual_image_pull_timeout_probe(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may17_0102_registry_manifest_pull_stall_observation()
    _assert_source_probe_still_blocked(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM,
            ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    diagnostic = {
        "schema": ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SCHEMA,
        "diagnostic_id": f"acontext_registry_manifest_pull_stall_diagnostic:{source['probe_id']}",
        "source_probe_id": source["probe_id"],
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "packet_id": source["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME],
            "forbidden_inputs": [
                "raw_transcripts",
                "unreviewed_memory",
                "private_operator_context",
                "freeform_worker_chat",
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
        "diagnostic_observation": observed,
        "registry_manifest_summary": _registry_manifest_summary(observed),
        "docker_pull_stall_summary": _docker_pull_stall_summary(observed),
        "image_inventory": _image_inventory(observed, source),
        "readiness": _readiness(observed),
        "operator_next_actions": _operator_next_actions(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "diagnostic_verdict": "registry_manifests_available_but_docker_pull_still_stalls",
        "operator_instruction": (
            "Treat the GHCR manifests as availability evidence only. They narrow the blocker "
            "away from missing anonymous manifests or missing linux/arm64 indexes, but they do "
            "not prove Docker Desktop can pull layers locally. Keep Acontext startup and live "
            "write/retrieve parity blocked until the Docker pull stall is resolved, all images "
            "are present, API/dashboard health passes, and the readiness gate is rebuilt empty."
        ),
    }
    _assert_diagnostic_conservative(diagnostic)
    return diagnostic


def write_acontext_registry_manifest_pull_stall_diagnostic(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic registry-manifest / pull-stall diagnostic."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    diagnostic = build_acontext_registry_manifest_pull_stall_diagnostic(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME
    path.write_text(json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_registry_manifest_pull_stall_diagnostic(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted registry-manifest / pull-stall diagnostic."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        diagnostic = json.load(fh)
    source = load_acontext_individual_image_pull_timeout_probe(artifact_dir=base_dir)
    _assert_diagnostic_conservative(diagnostic)
    if diagnostic != build_acontext_registry_manifest_pull_stall_diagnostic(
        artifact_dir=base_dir, individual_probe=source
    ):
        raise CityOpsContractError("registry manifest pull-stall diagnostic drifted from source probe")
    return diagnostic


def _registry_manifest_summary(observation: dict[str, Any]) -> dict[str, Any]:
    checks = observation["ghcr_manifest_checks"]
    return {
        "ghcr_image_count": len(checks),
        "manifest_fetch_success_count": sum(1 for row in checks if row["manifest_fetch_succeeded"]),
        "all_ghcr_manifests_fetchable_anonymously": all(
            row["anonymous_bearer_token_received"] and row["manifest_fetch_succeeded"]
            for row in checks
        ),
        "all_ghcr_images_advertise_linux_arm64": all(
            row["linux_arm64_manifest_advertised"] for row in checks
        ),
        "manifest_availability_is_not_pull_success": True,
        "docker_pull_success_proven": False,
    }


def _docker_pull_stall_summary(observation: dict[str, Any]) -> dict[str, Any]:
    pull = observation["docker_pull_stall_check"]
    return {
        "image": pull["image"],
        "timeout_seconds": pull["timeout_seconds"],
        "duration_seconds": pull["duration_seconds"],
        "timed_out_without_output": pull["timed_out"]
        and not pull["stdout_tail"]
        and not pull["stderr_tail"],
        "exit_code": pull["exit_code"],
        "pulled_or_present_after_check": pull["pulled_or_present_after_check"],
        "docker_pull_blocker_remains": True,
    }


def _image_inventory(observation: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    required = source["individual_pull_observation"]["required_images_from_compose_config"]
    observed = set(observation["local_images_observed_after_diagnostic"])
    return {
        "required_image_count": len(required),
        "present_required_images": [image for image in required if image in observed],
        "missing_required_images": [image for image in required if image not in observed],
        "missing_required_image_count": sum(1 for image in required if image not in observed),
        "all_required_images_present": False,
        "image_pull_blocker_remains": True,
    }


def _readiness(observation: dict[str, Any]) -> dict[str, Any]:
    readiness: dict[str, Any] = {
        "diagnostic_landed": True,
        "source_individual_probe_consumed": True,
        "ghcr_manifest_checks_recorded": True,
        "ghcr_manifests_fetchable_anonymously": True,
        "ghcr_linux_arm64_manifests_advertised": True,
        "docker_pull_stall_reproduced": True,
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
            "step_id": "inspect_docker_desktop_layer_pull_path",
            "action": (
                "Capture Docker Desktop/containerd diagnostics for the GHCR layer pull path "
                "without tokens, including daemon events and DNS/proxy errors if available."
            ),
            "must_record": ["daemon_event_window", "containerd_error", "dns_or_proxy_signal"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "retry_first_image_with_explicit_platform_or_mirror",
            "action": (
                "Retry only ghcr.io/memodb-io/acontext-ui:latest with a short bounded timeout, "
                "explicit --platform linux/arm64, or a trusted cache/mirror after the daemon path is understood."
            ),
            "must_record": ["image", "platform", "duration_seconds", "exit_code", "present_after_retry"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "start_compose_only_after_all_images_present",
            "action": "Do not start compose until all nine required images are present locally.",
            "must_record": ["required_image_count", "present_image_count", "missing_images"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "rebuild_gate_before_any_parity_write",
            "action": "Rerun read-only preflight and rebuild the readiness gate before any Acontext write/retrieve parity attempt.",
            "must_record": ["empty_blocker_gate", "write_allowed", "retrieve_allowed"],
            "authorizes_live_attempt": "only_if_gate_empty",
        },
    ]


def _assert_source_probe_still_blocked(source: dict[str, Any]) -> None:
    if source.get("probe_verdict") != "individual_image_pull_probe_still_blocks_acontext_startup":
        raise CityOpsContractError("source individual image pull probe must still block Acontext startup")
    readiness = source.get("readiness", {})
    if readiness.get("all_required_images_present") is not False:
        raise CityOpsContractError("source individual probe unexpectedly has all images")
    if readiness.get("compose_services_started") is not False:
        raise CityOpsContractError("source individual probe unexpectedly started services")


def _assert_observation_conservative(observation: dict[str, Any]) -> None:
    if [row.get("image") for row in observation.get("ghcr_manifest_checks", [])] != ACONTEXT_GHCR_IMAGES:
        raise CityOpsContractError("registry manifest diagnostic GHCR image list drifted")
    for row in observation["ghcr_manifest_checks"]:
        if row.get("manifest_fetch_succeeded") is not True:
            raise CityOpsContractError("registry manifest diagnostic expects manifest fetch success")
        if row.get("linux_arm64_manifest_advertised") is not True:
            raise CityOpsContractError("registry manifest diagnostic expects linux/arm64 manifest")
    pull = observation.get("docker_pull_stall_check", {})
    if pull.get("image") != "ghcr.io/memodb-io/acontext-ui:latest":
        raise CityOpsContractError("registry manifest diagnostic must recheck the first required image")
    if pull.get("timed_out") is not True or pull.get("pulled_or_present_after_check") is not False:
        raise CityOpsContractError("docker pull stall must remain timed out and not pulled")
    if observation.get("local_images_observed_after_diagnostic") != ["pgvector/pgvector:pg16"]:
        raise CityOpsContractError("registry manifest diagnostic expects only pgvector observed locally")
    if observation.get("services_started") is not False:
        raise CityOpsContractError("registry manifest diagnostic cannot record started services")
    if observation.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("registry manifest diagnostic cannot record live Acontext write")
    if observation.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("registry manifest diagnostic cannot record live Acontext retrieval")
    if observation.get("readiness_gate_rebuilt_with_empty_blockers") is not False:
        raise CityOpsContractError("registry manifest diagnostic cannot record empty readiness gate")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"registry manifest diagnostic claim boundary overlap: {sorted(overlap)}")
    if ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("registry manifest diagnostic safe claim missing")
    for claim in REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_BLOCKED_CLAIMS:
        if claim not in do_not_claim_yet:
            raise CityOpsContractError(f"registry manifest diagnostic blocked claim missing: {claim}")


def _assert_diagnostic_conservative(diagnostic: dict[str, Any]) -> None:
    if diagnostic.get("schema") != ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_SCHEMA:
        raise CityOpsContractError("unexpected registry manifest diagnostic schema")
    for section in ("derived_from", "access_policy"):
        payload = diagnostic[section]
        for key, value in payload.items():
            if isinstance(value, bool) and key not in {"read_only", "requires_admin_context"}:
                if value is not False:
                    raise CityOpsContractError(f"registry manifest diagnostic {section}.{key} must remain false")
    readiness = diagnostic["readiness"]
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"registry manifest diagnostic readiness promoted: {flag}")
    if diagnostic["registry_manifest_summary"]["docker_pull_success_proven"] is not False:
        raise CityOpsContractError("manifest checks cannot prove Docker pull success")
    if diagnostic["docker_pull_stall_summary"]["docker_pull_blocker_remains"] is not True:
        raise CityOpsContractError("registry manifest diagnostic must preserve Docker pull blocker")
    if diagnostic["image_inventory"]["all_required_images_present"] is not False:
        raise CityOpsContractError("registry manifest diagnostic cannot mark all images present")
    if diagnostic.get("diagnostic_verdict") != "registry_manifests_available_but_docker_pull_still_stalls":
        raise CityOpsContractError("unexpected registry manifest diagnostic verdict")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
