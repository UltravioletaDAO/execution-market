"""Individual Acontext image-pull timeout probe for City-as-a-Service.

This artifact records the May 17 00:02 EDT follow-up probe after the compose
image-pull attempt stayed blocked.  The probe tried the first required image
individually with a per-image timeout, observed no Docker progress before the
180s timeout, confirmed registry endpoints were reachable by HTTP, and stopped
before cycling through the remaining images to avoid turning the cron window into
an unbounded pull loop.

It is internal/admin prerequisite evidence only.  It does not start services,
does not write to or retrieve from Acontext, does not rebuild the readiness gate,
and does not authorize customer/public AAS packaging, dispatch, reputation,
payment, production, GPS/raw metadata, or worker-copyable doctrine claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import (
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME,
    ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM,
    COMPOSE_IMAGE_PULL_ATTEMPT_BLOCKED_CLAIMS,
    REQUIRED_ACONTEXT_IMAGES,
    load_acontext_compose_image_pull_attempt_log,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SCHEMA = (
    "city_ops.acontext_individual_image_pull_timeout_probe.v1"
)
ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME = (
    "acontext_individual_image_pull_timeout_probe.json"
)
ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM = (
    "admin_acontext_individual_image_pull_timeout_probe_landed"
)

INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_BLOCKED_CLAIMS = [
    *COMPOSE_IMAGE_PULL_ATTEMPT_BLOCKED_CLAIMS,
    "first_required_image_pulled_by_individual_probe",
    "all_required_images_attempted_by_individual_probe",
    "all_required_images_present_by_individual_probe",
    "docker_registry_reachability_implies_image_availability",
    "compose_services_started_by_individual_probe",
    "acontext_api_reachable_by_individual_probe",
    "acontext_dashboard_reachable_by_individual_probe",
    "readiness_gate_rebuilt_empty_by_individual_probe",
    "live_acontext_write_completed_by_individual_probe",
    "live_acontext_retrieval_completed_by_individual_probe",
    "runtime_parity_proven_by_individual_probe",
    "customer_visible_aas_packaging_ready_by_individual_probe",
    "public_route_ready_by_individual_probe",
    "operator_queue_launch_ready_by_individual_probe",
    "dispatch_ready_by_individual_probe",
    "erc8004_reputation_ready_by_individual_probe",
    "payment_or_production_reverified_by_individual_probe",
    "gps_or_raw_metadata_release_allowed_by_individual_probe",
    "worker_copyable_doctrine_ready_by_individual_probe",
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
    "new_required_images_observed_after_probe",
    "compose_services_started",
    "api_reachable_after_probe",
    "dashboard_reachable_after_probe",
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
    "payment_coverage_reverified_by_this_probe",
    "production_infrastructure_reverified_by_this_probe",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may17_0002_individual_pull_probe_observation() -> dict[str, Any]:
    """Return the deterministic May 17 00:02 individual-pull probe observation."""

    return {
        "observation_window": "2026-05-17T00:02:00-04:00/2026-05-17T00:05:40-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/infra/acontext",
        "probe_reason": "follow_next_safe_action_from_compose_image_pull_attempt_log",
        "required_images_from_compose_config": REQUIRED_ACONTEXT_IMAGES,
        "per_image_timeout_seconds": 180,
        "pull_results": [
            {
                "image": "ghcr.io/memodb-io/acontext-ui:latest",
                "attempted": True,
                "command": "docker pull ghcr.io/memodb-io/acontext-ui:latest",
                "exit_code": None,
                "timed_out": True,
                "duration_seconds": 180.01,
                "last_status_lines": [],
                "pulled_or_present": False,
            },
            {
                "image": "chrislusf/seaweedfs:4.02",
                "attempted": True,
                "command": "docker pull chrislusf/seaweedfs:4.02",
                "exit_code": None,
                "timed_out": False,
                "aborted_by_operator": True,
                "abort_reason": "stopped after first image timeout to avoid an unbounded cron pull loop",
                "last_status_lines": [],
                "pulled_or_present": False,
            },
        ],
        "unattempted_images": [
            "pgvector/pgvector:pg16",
            "redis:7.4",
            "rabbitmq:4-management",
            "ghcr.io/memodb-io/acontext-api:latest",
            "amazon/aws-cli:2.32.6",
            "ghcr.io/memodb-io/acontext-core:latest",
            "jaegertracing/all-in-one:1.75.0",
        ],
        "registry_http_reachability_checks": [
            {
                "endpoint": "https://ghcr.io/v2/",
                "http_status": 405,
                "reachable": True,
                "meaning": "registry_endpoint_responded_but_does_not_prove_image_pull_success",
            },
            {
                "endpoint": "https://registry-1.docker.io/v2/",
                "http_status": 401,
                "reachable": True,
                "meaning": "registry_endpoint_responded_but_does_not_prove_image_pull_success",
            },
        ],
        "local_images_observed_after_probe": ["pgvector/pgvector:pg16"],
        "new_required_images_observed_after_probe": [],
        "services_started": False,
        "api_checked_after_probe": False,
        "dashboard_checked_after_probe": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
    }


def build_acontext_individual_image_pull_timeout_probe(
    *,
    artifact_dir: str | Path | None = None,
    compose_attempt_log: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed individual image-pull timeout probe."""

    source = compose_attempt_log or load_acontext_compose_image_pull_attempt_log(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may17_0002_individual_pull_probe_observation()
    _assert_source_attempt_still_blocked(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM,
            ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    probe = {
        "schema": ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SCHEMA,
        "probe_id": f"acontext_individual_image_pull_timeout_probe:{source['attempt_log_id']}",
        "source_attempt_log_id": source["attempt_log_id"],
        "proof_anchor_id": source["proof_anchor_id"],
        "coordination_session_id": source["coordination_session_id"],
        "compact_decision_id": source["compact_decision_id"],
        "review_packet_id": source["review_packet_id"],
        "packet_id": source["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME],
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
        "individual_pull_observation": observed,
        "pull_progress_summary": _pull_progress_summary(observed),
        "image_inventory": _image_inventory(observed),
        "registry_reachability_summary": _registry_reachability_summary(observed),
        "readiness": _readiness(observed),
        "operator_next_actions": _operator_next_actions(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "probe_verdict": "individual_image_pull_probe_still_blocks_acontext_startup",
        "operator_instruction": (
            "Treat this as evidence that per-image pull probing has started but still did "
            "not clear the image blocker. Registry HTTP responses prove only endpoint "
            "reachability, not image availability. Do not start compose services or live "
            "Acontext parity until all images are present, API/dashboard health passes, and "
            "the readiness gate is rebuilt with empty blockers."
        ),
    }
    _assert_probe_conservative(probe)
    return probe


def write_acontext_individual_image_pull_timeout_probe(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic individual image-pull timeout probe."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    probe = build_acontext_individual_image_pull_timeout_probe(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME
    path.write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_individual_image_pull_timeout_probe(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted individual image-pull timeout probe."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        probe = json.load(fh)
    source = load_acontext_compose_image_pull_attempt_log(artifact_dir=base_dir)
    _assert_probe_conservative(probe)
    if probe != build_acontext_individual_image_pull_timeout_probe(
        artifact_dir=base_dir, compose_attempt_log=source
    ):
        raise CityOpsContractError("individual image-pull timeout probe drifted from source attempt log")
    return probe


def _pull_progress_summary(observation: dict[str, Any]) -> dict[str, Any]:
    results = observation["pull_results"]
    attempted = [row for row in results if row.get("attempted")]
    timed_out = [row["image"] for row in attempted if row.get("timed_out")]
    aborted = [row["image"] for row in attempted if row.get("aborted_by_operator")]
    succeeded = [row["image"] for row in attempted if row.get("pulled_or_present")]
    return {
        "required_image_count": len(observation["required_images_from_compose_config"]),
        "attempted_image_count": len(attempted),
        "unattempted_image_count": len(observation["unattempted_images"]),
        "successful_pull_count": len(succeeded),
        "timed_out_images": timed_out,
        "operator_aborted_images": aborted,
        "all_required_images_attempted": False,
        "all_attempted_images_pulled_or_present": False,
        "per_image_pull_blocker_remains": True,
    }


def _image_inventory(observation: dict[str, Any]) -> dict[str, Any]:
    observed = set(observation["local_images_observed_after_probe"])
    required = list(observation["required_images_from_compose_config"])
    missing = [image for image in required if image not in observed]
    present = [image for image in required if image in observed]
    return {
        "required_image_count": len(required),
        "present_required_images": present,
        "missing_required_images": missing,
        "missing_required_image_count": len(missing),
        "all_required_images_present": False,
        "new_required_images_observed_after_probe": [],
        "image_pull_blocker_remains": True,
    }


def _registry_reachability_summary(observation: dict[str, Any]) -> dict[str, Any]:
    checks = observation["registry_http_reachability_checks"]
    return {
        "checks_recorded": len(checks),
        "all_registry_endpoints_reachable_by_http": all(check["reachable"] for check in checks),
        "reachability_is_not_pull_success": True,
        "image_availability_proven": False,
        "pull_success_proven": False,
    }


def _readiness(observation: dict[str, Any]) -> dict[str, Any]:
    readiness: dict[str, Any] = {
        "probe_landed": True,
        "source_compose_attempt_log_consumed": True,
        "individual_pull_attempt_recorded": True,
        "registry_http_reachability_recorded": True,
        "remaining_blockers": [
            "first_individual_image_pull_timed_out_without_progress",
            "all_required_images_not_attempted_individually",
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
            "step_id": "diagnose_docker_pull_stall",
            "action": "Run a bounded Docker pull diagnostic for the GHCR image that timed out, capturing daemon/network error detail without secrets.",
            "must_record": ["image", "daemon_status", "registry_auth_status", "last_error_or_progress_line"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "retry_remaining_images_only_after_stall_explained",
            "action": "Retry remaining image pulls only with shorter bounded timeouts or an external cache/mirror strategy.",
            "must_record": ["image", "exit_code", "duration_seconds", "present_after_retry"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "start_compose_only_after_images_present",
            "action": "Start compose services only after all nine required images are present locally.",
            "must_record": ["healthy_services", "unhealthy_services", "api_health", "dashboard_health"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "rebuild_gate_before_any_parity_write",
            "action": "Rerun read-only preflight and rebuild the readiness gate before any write/retrieve parity attempt.",
            "must_record": ["empty_blocker_gate", "write_allowed", "retrieve_allowed"],
            "authorizes_live_attempt": "only_if_gate_empty",
        },
    ]


def _assert_source_attempt_still_blocked(source: dict[str, Any]) -> None:
    if source.get("attempt_verdict") != "compose_image_pull_attempt_still_blocks_acontext_startup":
        raise CityOpsContractError("source compose attempt must still block Acontext startup")
    readiness = source.get("readiness", {})
    if readiness.get("compose_pull_completed") is not False:
        raise CityOpsContractError("source compose attempt unexpectedly completed compose pull")
    if readiness.get("all_required_images_present") is not False:
        raise CityOpsContractError("source compose attempt unexpectedly has all images")


def _assert_observation_conservative(observation: dict[str, Any]) -> None:
    if observation.get("required_images_from_compose_config") != REQUIRED_ACONTEXT_IMAGES:
        raise CityOpsContractError("individual pull probe required image list drifted")
    if observation.get("local_images_observed_after_probe") != ["pgvector/pgvector:pg16"]:
        raise CityOpsContractError("individual pull probe expects only pgvector observed locally")
    if set(observation.get("new_required_images_observed_after_probe", [])):
        raise CityOpsContractError("individual pull probe fixture expects no new required images")
    results = observation.get("pull_results", [])
    if not results or results[0].get("image") != REQUIRED_ACONTEXT_IMAGES[0]:
        raise CityOpsContractError("individual pull probe must record the first required image")
    if results[0].get("timed_out") is not True or results[0].get("pulled_or_present") is not False:
        raise CityOpsContractError("first individual pull must remain timed out and not pulled")
    if any(row.get("pulled_or_present") for row in results):
        raise CityOpsContractError("individual pull probe cannot record a successful image pull")
    if observation.get("services_started") is not False:
        raise CityOpsContractError("individual pull probe cannot record started services")
    if observation.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("individual pull probe cannot record live Acontext write")
    if observation.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("individual pull probe cannot record live Acontext retrieval")
    if observation.get("readiness_gate_rebuilt_with_empty_blockers") is not False:
        raise CityOpsContractError("individual pull probe cannot record empty readiness gate")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"individual pull probe claim boundary overlap: {sorted(overlap)}")
    if ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("individual pull probe safe claim missing")
    for claim in INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_BLOCKED_CLAIMS:
        if claim not in do_not_claim_yet:
            raise CityOpsContractError(f"individual pull probe blocked claim missing: {claim}")


def _assert_probe_conservative(probe: dict[str, Any]) -> None:
    if probe.get("schema") != ACONTEXT_INDIVIDUAL_IMAGE_PULL_TIMEOUT_PROBE_SCHEMA:
        raise CityOpsContractError("unexpected individual image-pull timeout probe schema")
    for section in ("derived_from", "access_policy"):
        payload = probe[section]
        for key, value in payload.items():
            if isinstance(value, bool) and key not in {"read_only", "requires_admin_context"}:
                if value is not False:
                    raise CityOpsContractError(f"individual pull probe {section}.{key} must remain false")
    readiness = probe["readiness"]
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"individual pull probe readiness promoted: {flag}")
    inventory = probe["image_inventory"]
    if inventory["all_required_images_present"] is not False:
        raise CityOpsContractError("individual pull probe cannot mark all images present")
    if inventory["missing_required_image_count"] <= 0:
        raise CityOpsContractError("individual pull probe must preserve missing required image blocker")
    progress = probe["pull_progress_summary"]
    if progress["per_image_pull_blocker_remains"] is not True:
        raise CityOpsContractError("individual pull probe must preserve per-image pull blocker")
    registry = probe["registry_reachability_summary"]
    if registry["image_availability_proven"] is not False or registry["pull_success_proven"] is not False:
        raise CityOpsContractError("registry reachability cannot promote image pull success")
    if probe.get("probe_verdict") != "individual_image_pull_probe_still_blocks_acontext_startup":
        raise CityOpsContractError("unexpected individual image-pull timeout probe verdict")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
