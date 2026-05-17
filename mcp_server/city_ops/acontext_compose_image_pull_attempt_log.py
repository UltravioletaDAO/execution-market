"""Acontext compose image-pull attempt log for City-as-a-Service.

This artifact records the May 16 23:04 EDT follow-up attempt to pre-pull the
local Acontext Docker Compose images.  The attempt remained blocked: compose
reported all required images as "Pulling", emitted no layer progress, was killed
after a quiet window, and only the pre-existing pgvector image was observed
locally afterward.

It is internal/admin evidence only.  It does not start services, does not write
to or retrieve from Acontext, does not rebuild the runtime-memory gate, and does
not authorize customer/public AAS packaging, dispatch, reputation, payment,
production, GPS/raw metadata, or worker-copyable doctrine claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_runtime_memory_prerequisite_probe import (
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM,
    RUNTIME_MEMORY_PREREQUISITE_PROBE_BLOCKED_CLAIMS,
    load_acontext_runtime_memory_prerequisite_probe,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SCHEMA = (
    "city_ops.acontext_compose_image_pull_attempt_log.v1"
)
ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME = (
    "acontext_compose_image_pull_attempt_log.json"
)
ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM = (
    "admin_acontext_compose_image_pull_attempt_log_landed"
)

COMPOSE_IMAGE_PULL_ATTEMPT_BLOCKED_CLAIMS = [
    *RUNTIME_MEMORY_PREREQUISITE_PROBE_BLOCKED_CLAIMS,
    "compose_image_pull_completed_by_attempt_log",
    "all_required_acontext_images_present_by_attempt_log",
    "acontext_compose_services_started_by_attempt_log",
    "acontext_api_reachable_by_attempt_log",
    "acontext_dashboard_reachable_by_attempt_log",
    "readiness_gate_rebuilt_empty_by_attempt_log",
    "live_acontext_write_completed_by_attempt_log",
    "live_acontext_retrieval_completed_by_attempt_log",
    "runtime_parity_proven_by_attempt_log",
    "customer_visible_aas_packaging_ready_by_attempt_log",
    "public_route_ready_by_attempt_log",
    "operator_queue_launch_ready_by_attempt_log",
    "dispatch_ready_by_attempt_log",
    "erc8004_reputation_ready_by_attempt_log",
    "payment_or_production_reverified_by_attempt_log",
    "gps_or_raw_metadata_release_allowed_by_attempt_log",
    "worker_copyable_doctrine_ready_by_attempt_log",
]

REQUIRED_ACONTEXT_IMAGES = [
    "ghcr.io/memodb-io/acontext-ui:latest",
    "chrislusf/seaweedfs:4.02",
    "pgvector/pgvector:pg16",
    "redis:7.4",
    "rabbitmq:4-management",
    "ghcr.io/memodb-io/acontext-api:latest",
    "amazon/aws-cli:2.32.6",
    "ghcr.io/memodb-io/acontext-core:latest",
    "jaegertracing/all-in-one:1.75.0",
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
    "compose_pull_completed",
    "all_required_images_present",
    "new_required_images_observed_after_attempt",
    "compose_services_started",
    "api_reachable_after_attempt",
    "dashboard_reachable_after_attempt",
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
    "payment_coverage_reverified_by_this_attempt",
    "production_infrastructure_reverified_by_this_attempt",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may16_2304_compose_pull_attempt_observation() -> dict[str, Any]:
    """Return the deterministic May 16 23:04 compose pull attempt observation."""

    return {
        "observation_window": "2026-05-16T23:04:00-04:00/2026-05-16T23:08:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "command": (
            "docker compose -f .docker-compose-1411407133.yaml --env-file .env "
            "pull --ignore-pull-failures"
        ),
        "working_directory": "~/clawd/infra/acontext",
        "compose_file": ".docker-compose-1411407133.yaml",
        "env_file_present": True,
        "required_images_from_compose_config": REQUIRED_ACONTEXT_IMAGES,
        "pull_command_started": True,
        "pull_output_observed": [
            "Image ghcr.io/memodb-io/acontext-core:latest Pulling",
            "Image rabbitmq:4-management Pulling",
            "Image ghcr.io/memodb-io/acontext-api:latest Pulling",
            "Image pgvector/pgvector:pg16 Pulling",
            "Image amazon/aws-cli:2.32.6 Pulling",
            "Image redis:7.4 Pulling",
            "Image ghcr.io/memodb-io/acontext-ui:latest Pulling",
            "Image chrislusf/seaweedfs:4.02 Pulling",
            "Image jaegertracing/all-in-one:1.75.0 Pulling",
        ],
        "pull_completed": False,
        "pull_stopped_by_operator": True,
        "pull_stop_signal": "SIGKILL",
        "quiet_window_after_initial_output_seconds_approx": 180,
        "attempt_duration_seconds_approx": 240,
        "local_images_observed_after_attempt": ["pgvector/pgvector:pg16"],
        "new_required_images_observed_after_attempt": [],
        "services_started": False,
        "api_checked_after_attempt": False,
        "dashboard_checked_after_attempt": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "readiness_gate_rebuilt_with_empty_blockers": False,
    }


def build_acontext_compose_image_pull_attempt_log(
    *,
    artifact_dir: str | Path | None = None,
    prerequisite_probe: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed compose image-pull attempt log."""

    probe = prerequisite_probe or load_acontext_runtime_memory_prerequisite_probe(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may16_2304_compose_pull_attempt_observation()
    _assert_prerequisite_probe_blocked(probe)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *probe["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_SAFE_CLAIM,
            ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *probe["claim_boundaries"]["do_not_claim_yet"],
            *COMPOSE_IMAGE_PULL_ATTEMPT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    log = {
        "schema": ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SCHEMA,
        "attempt_log_id": f"acontext_compose_image_pull_attempt_log:{probe['probe_id']}",
        "source_probe_id": probe["probe_id"],
        "proof_anchor_id": probe["proof_anchor_id"],
        "coordination_session_id": probe["coordination_session_id"],
        "compact_decision_id": probe["compact_decision_id"],
        "review_packet_id": probe["review_packet_id"],
        "packet_id": probe["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_RUNTIME_MEMORY_PREREQUISITE_PROBE_FILENAME],
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
        "pull_attempt_observation": observed,
        "image_inventory": _image_inventory(observed),
        "readiness": _readiness(observed),
        "operator_next_actions": _operator_next_actions(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "attempt_verdict": "compose_image_pull_attempt_still_blocks_acontext_startup",
        "operator_instruction": (
            "Treat this as evidence that the compose image-pull blocker persisted after "
            "the 23:04 local-only attempt. Do not start a live parity attempt until all "
            "required images are present, compose services start healthy, localhost API "
            "and dashboard are reachable, and the readiness gate is rebuilt with empty blockers."
        ),
    }
    _assert_attempt_log_conservative(log)
    return log


def write_acontext_compose_image_pull_attempt_log(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic compose image-pull attempt log."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    attempt_log = build_acontext_compose_image_pull_attempt_log(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME
    path.write_text(json.dumps(attempt_log, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_compose_image_pull_attempt_log(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted compose image-pull attempt log."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        attempt_log = json.load(fh)
    probe = load_acontext_runtime_memory_prerequisite_probe(artifact_dir=base_dir)
    _assert_attempt_log_conservative(attempt_log)
    if attempt_log != build_acontext_compose_image_pull_attempt_log(
        artifact_dir=base_dir, prerequisite_probe=probe
    ):
        raise CityOpsContractError("compose image-pull attempt log drifted from source probe")
    return attempt_log


def _image_inventory(observation: dict[str, Any]) -> dict[str, Any]:
    observed = set(observation["local_images_observed_after_attempt"])
    required = list(observation["required_images_from_compose_config"])
    missing = [image for image in required if image not in observed]
    present = [image for image in required if image in observed]
    return {
        "required_image_count": len(required),
        "present_required_images": present,
        "missing_required_images": missing,
        "missing_required_image_count": len(missing),
        "all_required_images_present": False,
        "new_required_images_observed_after_attempt": [],
        "image_pull_blocker_remains": True,
    }


def _readiness(observation: dict[str, Any]) -> dict[str, Any]:
    readiness: dict[str, Any] = {
        "attempt_log_landed": True,
        "source_prerequisite_probe_consumed": True,
        "required_images_enumerated": True,
        "pull_attempt_recorded": True,
        "remaining_blockers": [
            "compose_image_pull_not_completed",
            "required_acontext_images_missing",
            "acontext_compose_services_not_started",
            "local_acontext_api_not_rechecked_reachable",
            "local_acontext_dashboard_not_rechecked_reachable",
            "readiness_gate_not_rebuilt_empty",
        ],
        "attempt_duration_seconds_approx": observation["attempt_duration_seconds_approx"],
        "quiet_window_after_initial_output_seconds_approx": observation[
            "quiet_window_after_initial_output_seconds_approx"
        ],
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _operator_next_actions() -> list[dict[str, Any]]:
    return [
        {
            "step_id": "pre_pull_with_progress_timeout",
            "action": "Pre-pull each required Acontext image individually with progress output and per-image timeout.",
            "must_record": ["image", "exit_code", "duration_seconds", "last_progress_line"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "start_compose_only_after_images_present",
            "action": "Run compose up only after all nine required images are present locally.",
            "must_record": ["healthy_services", "unhealthy_services", "container_statuses"],
            "authorizes_live_attempt": False,
        },
        {
            "step_id": "rebuild_gate_before_any_parity_write",
            "action": "Rerun read-only preflight and rebuild the readiness gate before any write/retrieve parity attempt.",
            "must_record": ["api_health", "dashboard_health", "empty_blocker_gate"],
            "authorizes_live_attempt": "only_if_gate_empty",
        },
    ]


def _assert_prerequisite_probe_blocked(probe: dict[str, Any]) -> None:
    if probe.get("probe_verdict") != "runtime_memory_prerequisites_still_block_live_parity":
        raise CityOpsContractError("source prerequisite probe must still block live parity")
    readiness = probe.get("readiness", {})
    if readiness.get("ready_to_attempt_live_transport") is not False:
        raise CityOpsContractError("source prerequisite probe promoted live transport readiness")
    if readiness.get("compose_pull_completed") is not False:
        raise CityOpsContractError("source prerequisite probe unexpectedly completed compose pull")


def _assert_observation_conservative(observation: dict[str, Any]) -> None:
    if observation.get("pull_completed") is not False:
        raise CityOpsContractError("attempt log cannot record completed compose pull")
    if observation.get("services_started") is not False:
        raise CityOpsContractError("attempt log cannot record started services")
    if observation.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("attempt log cannot record live Acontext write")
    if observation.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("attempt log cannot record live Acontext retrieval")
    if observation.get("readiness_gate_rebuilt_with_empty_blockers") is not False:
        raise CityOpsContractError("attempt log cannot record empty readiness gate")
    if set(observation.get("new_required_images_observed_after_attempt", [])):
        raise CityOpsContractError("attempt log fixture expects no new required images")
    if observation.get("local_images_observed_after_attempt") != ["pgvector/pgvector:pg16"]:
        raise CityOpsContractError("attempt log fixture expects only pgvector observed locally")
    required = observation.get("required_images_from_compose_config", [])
    if required != REQUIRED_ACONTEXT_IMAGES:
        raise CityOpsContractError("attempt log required image list drifted")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"attempt log claim boundary overlap: {sorted(overlap)}")
    if ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("attempt log safe claim missing")
    for claim in COMPOSE_IMAGE_PULL_ATTEMPT_BLOCKED_CLAIMS:
        if claim not in do_not_claim_yet:
            raise CityOpsContractError(f"attempt log blocked claim missing: {claim}")


def _assert_attempt_log_conservative(attempt_log: dict[str, Any]) -> None:
    if attempt_log.get("schema") != ACONTEXT_COMPOSE_IMAGE_PULL_ATTEMPT_LOG_SCHEMA:
        raise CityOpsContractError("unexpected compose image-pull attempt log schema")
    for section in ("derived_from", "access_policy"):
        payload = attempt_log[section]
        for key, value in payload.items():
            if isinstance(value, bool) and key not in {"read_only", "requires_admin_context"}:
                if value is not False:
                    raise CityOpsContractError(f"attempt log {section}.{key} must remain false")
    readiness = attempt_log["readiness"]
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"attempt log readiness promoted: {flag}")
    inventory = attempt_log["image_inventory"]
    if inventory["all_required_images_present"] is not False:
        raise CityOpsContractError("attempt log cannot mark all images present")
    if inventory["missing_required_image_count"] <= 0:
        raise CityOpsContractError("attempt log must preserve missing required image blocker")
    if attempt_log.get("attempt_verdict") != "compose_image_pull_attempt_still_blocks_acontext_startup":
        raise CityOpsContractError("unexpected compose image-pull attempt verdict")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
