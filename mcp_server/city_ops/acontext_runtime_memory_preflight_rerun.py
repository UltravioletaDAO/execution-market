"""Runtime-memory Acontext preflight rerun bridge for City-as-a-Service.

This artifact captures the May 16 7 AM safe slice: the active City Ops
runner can expose the dedicated Acontext venv's SDK for read-only preflight
work, but local Acontext API/dashboard reachability still blocks the live
write/retrieve parity pass.

It never writes to Acontext, never retrieves from Acontext, never starts a
customer/public route, and never promotes runtime, dispatch, reputation,
payment, production, GPS/raw metadata, or worker-doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_live_preflight import (
    ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM,
    build_acontext_live_preflight_result,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA = (
    "city_ops.acontext_runtime_memory_preflight_rerun.v1"
)
ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME = (
    "acontext_runtime_memory_preflight_rerun.json"
)
ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM = (
    "admin_acontext_runtime_memory_preflight_rerun_landed"
)

RUNTIME_MEMORY_PREFLIGHT_RERUN_BLOCKED_CLAIMS = [
    "acontext_compose_pull_completed_by_runtime_memory_rerun",
    "acontext_services_started_by_runtime_memory_rerun",
    "acontext_api_dashboard_reachable_by_runtime_memory_rerun",
    "acontext_preflight_rebuilt_empty_by_runtime_memory_rerun",
    "acontext_live_parity_attempt_authorized_by_runtime_memory_rerun",
    "acontext_live_write_completed_by_runtime_memory_rerun",
    "acontext_live_retrieval_completed_by_runtime_memory_rerun",
    "acontext_sink_ready_by_runtime_memory_rerun",
    "runtime_parity_proven_by_runtime_memory_rerun",
    "customer_visible_aas_packaging_ready_by_runtime_memory_rerun",
    "public_route_ready_by_runtime_memory_rerun",
    "operator_queue_launch_ready_by_runtime_memory_rerun",
    "autonomous_city_dispatch_ready_by_runtime_memory_rerun",
    "erc8004_reputation_ready_by_runtime_memory_rerun",
    "payment_coverage_reverified_by_runtime_memory_rerun",
    "production_infrastructure_reverified_by_runtime_memory_rerun",
    "exact_gps_or_metadata_exposure_allowed_by_runtime_memory_rerun",
    "worker_copyable_municipal_doctrine_ready_by_runtime_memory_rerun",
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
    "ready_to_attempt_live_transport",
    "preflight_rebuilt_with_empty_blockers",
    "compose_pull_completed",
    "compose_services_started",
    "api_reachable_after_rerun",
    "dashboard_reachable_after_rerun",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_rerun",
    "production_infrastructure_reverified_by_this_rerun",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may16_7am_runtime_memory_preflight_probe() -> dict[str, Any]:
    """Return the deterministic read-only May 16 7 AM preflight probe."""

    return {
        "docker": {
            "checked": True,
            "available": True,
            "exit_code": 0,
            "error": None,
        },
        "python_sdk": {
            "checked": True,
            "package": "acontext",
            "available": True,
            "import_mode": "explicit_venv_site_packages",
            "active_runner_importable": False,
            "explicit_venv_consulted": True,
            "explicit_venv_path": "~/clawd/.venv-acontext",
            "site_packages_path": "~/clawd/.venv-acontext/lib/python3.14/site-packages",
            "path_added_to_sys_path": True,
            "error": None,
        },
        "api": {
            "checked": True,
            "url": "http://localhost:8029/api/v1",
            "reachable": False,
            "status_code": None,
            "error": "connection refused during 7am runtime-memory preflight",
        },
        "dashboard": {
            "checked": True,
            "url": "http://localhost:3000",
            "reachable": False,
            "status_code": None,
            "error": "connection refused during 7am runtime-memory preflight",
        },
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_may16_7am_compose_startup_observation() -> dict[str, Any]:
    """Return the deterministic compose startup observation for this slice."""

    return {
        "observation_window": "2026-05-16T07:00:00-04:00",
        "compose_workdir": "~/clawd/infra/acontext",
        "compose_manifest_found": True,
        "compose_env_file_found": True,
        "docker_daemon_available": True,
        "compose_up_command_started": True,
        "compose_up_command_settled": False,
        "compose_up_stopped_by_operator": True,
        "compose_up_stop_reason": "silent_multi_image_pull_did_not_settle_inside_7am_window",
        "containers_started": False,
        "services_healthy": False,
        "local_acontext_api_reachable_after_startup": False,
        "local_acontext_dashboard_reachable_after_startup": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_runtime_memory_preflight_rerun(
    *,
    artifact_dir: str | Path | None = None,
    preflight: dict[str, Any] | None = None,
    compose_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed runtime-memory preflight rerun artifact."""

    source_preflight = preflight or build_acontext_live_preflight_result(
        artifact_dir=artifact_dir,
        probe=build_may16_7am_runtime_memory_preflight_probe(),
    )
    observed_compose = compose_observation or build_may16_7am_compose_startup_observation()
    _assert_source_preflight_blocked(source_preflight)
    _assert_compose_observation_conservative(observed_compose)

    safe_to_claim = _dedupe(
        [
            *source_preflight["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM,
            ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_preflight["claim_boundaries"]["do_not_claim_yet"],
            *RUNTIME_MEMORY_PREFLIGHT_RERUN_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    readiness = _rerun_readiness(source_preflight, observed_compose)
    rerun = {
        "schema": ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA,
        "rerun_id": f"acontext_runtime_memory_preflight_rerun:{source_preflight['preflight_id']}",
        "source_preflight_id": source_preflight["preflight_id"],
        "proof_anchor_id": source_preflight["proof_anchor_id"],
        "coordination_session_id": source_preflight["coordination_session_id"],
        "compact_decision_id": source_preflight["compact_decision_id"],
        "review_packet_id": source_preflight["review_packet_id"],
        "packet_id": source_preflight["packet_id"],
        "derived_from": {
            "read_only": True,
            "source_schema": source_preflight["schema"],
            "source_verdict": source_preflight["preflight_verdict"],
            "consumes_only": ["acontext_live_preflight_result"],
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
            "semantic_reinterpretation_performed": False,
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
            "network_route_registered": False,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "dispatch_enabled": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "compose_startup_observation": dict(observed_compose),
        "preflight_probe": source_preflight["probe"],
        "runner_bridge": _runner_bridge(source_preflight),
        "current_blockers": list(source_preflight["readiness"].get("blockers", [])),
        "readiness": readiness,
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "rerun_verdict": "runtime_memory_preflight_reran_still_blocked_by_local_services",
        "operator_next_actions": _operator_next_actions(source_preflight),
        "operator_instruction": (
            "Treat this as read-only runtime-memory prerequisite progress only. The "
            "active runner can expose the dedicated Acontext venv for SDK import, "
            "but local API/dashboard blockers remain. Do not run a live write/retrieve "
            "parity pass until a rebuilt preflight has empty blockers and a new gate "
            "explicitly authorizes exactly one attempt."
        ),
    }
    _assert_rerun_conservative(rerun)
    return rerun


def write_acontext_runtime_memory_preflight_rerun(
    *, artifact_dir: str | Path | None = None, preflight: dict[str, Any] | None = None
) -> Path:
    """Persist the runtime-memory preflight rerun artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    rerun = build_acontext_runtime_memory_preflight_rerun(
        artifact_dir=base_dir if preflight is None else None,
        preflight=preflight,
    )
    path = base_dir / ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME
    path.write_text(json.dumps(rerun, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_runtime_memory_preflight_rerun(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the runtime-memory preflight rerun artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        rerun = json.load(fh)
    _assert_rerun_conservative(rerun)
    return rerun


def _runner_bridge(source_preflight: dict[str, Any]) -> dict[str, Any]:
    sdk_probe = source_preflight["probe"]["python_sdk"]
    return {
        "active_runner_importable_without_bridge": bool(
            sdk_probe.get("active_runner_importable")
        ),
        "explicit_venv_consulted": bool(sdk_probe.get("explicit_venv_consulted")),
        "active_runner_can_import_acontext_via_explicit_venv": bool(
            sdk_probe.get("available")
            and sdk_probe.get("import_mode") == "explicit_venv_site_packages"
        ),
        "import_mode": sdk_probe.get("import_mode"),
        "path_added_to_sys_path": bool(sdk_probe.get("path_added_to_sys_path")),
        "authorizes_live_write": False,
        "authorizes_live_retrieve": False,
        "authorizes_runtime_parity_claim": False,
    }


def _rerun_readiness(
    source_preflight: dict[str, Any], compose_observation: dict[str, Any]
) -> dict[str, Any]:
    source = source_preflight["readiness"]
    sdk_probe = source_preflight["probe"]["python_sdk"]
    return {
        "runtime_memory_preflight_rerun_landed": True,
        "read_only_preflight_reran": True,
        "docker_available": bool(source["docker_available"]),
        "active_runner_can_import_acontext_via_explicit_venv": bool(
            sdk_probe.get("available")
            and sdk_probe.get("import_mode") == "explicit_venv_site_packages"
        ),
        "acontext_python_sdk_available": bool(source["acontext_python_sdk_available"]),
        "compose_pull_completed": bool(compose_observation.get("compose_up_command_settled")),
        "compose_services_started": bool(compose_observation.get("containers_started")),
        "api_reachable_after_rerun": bool(source["local_acontext_api_reachable"]),
        "dashboard_reachable_after_rerun": bool(
            source["local_acontext_dashboard_reachable"]
        ),
        "preflight_rebuilt_with_empty_blockers": False,
        "ready_to_attempt_live_transport": False,
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "customer_visible_aas_packaging_ready": False,
        "public_route_ready": False,
        "operator_queue_launch_ready": False,
        "autonomous_dispatch_ready": False,
        "erc8004_reputation_ready": False,
        "payment_coverage_reverified_by_this_rerun": False,
        "production_infrastructure_reverified_by_this_rerun": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
        "remaining_blockers": list(source.get("blockers", [])),
    }


def _operator_next_actions(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = set(source_preflight["readiness"].get("blockers", []))
    actions: list[dict[str, Any]] = []
    if "local_acontext_api_unreachable" in blockers:
        actions.append(
            {
                "action_id": "complete_local_acontext_api_startup",
                "status": "blocked",
                "success_signal": "http://localhost:8029/api/v1 responds to a read-only health probe",
            }
        )
    if "local_acontext_dashboard_unreachable" in blockers:
        actions.append(
            {
                "action_id": "complete_local_acontext_dashboard_startup",
                "status": "blocked",
                "success_signal": "http://localhost:3000 responds to a read-only dashboard probe",
            }
        )
    actions.append(
        {
            "action_id": "rerun_preflight_and_rebuild_gate",
            "status": "next_after_service_health",
            "success_signal": "rebuilt blocker delta/read surface/gate has empty blockers before one live parity attempt",
        }
    )
    return actions


def _assert_source_preflight_blocked(preflight: dict[str, Any]) -> None:
    if preflight.get("schema") != "city_ops.acontext_live_preflight.v1":
        raise CityOpsContractError("runtime-memory rerun requires live preflight source")
    readiness = preflight.get("readiness") or {}
    if readiness.get("ready_to_attempt_live_transport") is not False:
        raise CityOpsContractError("runtime-memory rerun cannot replace live parity pass")
    if not readiness.get("blockers"):
        raise CityOpsContractError("runtime-memory rerun requires remaining blockers")
    for flag in [
        "acontext_sink_ready",
        "runtime_parity_proven",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"runtime-memory rerun source promoted {flag}")
    sdk_probe = preflight.get("probe", {}).get("python_sdk", {})
    if sdk_probe.get("available") is not True:
        raise CityOpsContractError("runtime-memory rerun requires explicit SDK bridge progress")
    if sdk_probe.get("import_mode") != "explicit_venv_site_packages":
        raise CityOpsContractError("runtime-memory rerun requires explicit venv import mode")
    if preflight.get("probe", {}).get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("runtime-memory rerun cannot write live Acontext")
    if preflight.get("probe", {}).get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("runtime-memory rerun cannot retrieve live Acontext")


def _assert_compose_observation_conservative(observation: dict[str, Any]) -> None:
    required = [
        "docker_daemon_available",
        "compose_up_command_started",
        "compose_up_command_settled",
        "containers_started",
        "services_healthy",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]
    missing = [key for key in required if key not in observation]
    if missing:
        raise CityOpsContractError(f"runtime-memory rerun compose observation missing {missing}")
    for flag in [
        "compose_up_command_settled",
        "containers_started",
        "services_healthy",
        "local_acontext_api_reachable_after_startup",
        "local_acontext_dashboard_reachable_after_startup",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    ]:
        if observation.get(flag) is not False:
            raise CityOpsContractError(
                f"runtime-memory rerun compose observation promoted {flag}"
            )


def _assert_rerun_conservative(rerun: dict[str, Any]) -> None:
    if rerun.get("schema") != ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SCHEMA:
        raise CityOpsContractError("runtime-memory rerun schema drift")
    if rerun.get("rerun_verdict") != (
        "runtime_memory_preflight_reran_still_blocked_by_local_services"
    ):
        raise CityOpsContractError("runtime-memory rerun verdict drift")
    for flag in _FALSE_ACCESS_FLAGS:
        if rerun.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"runtime-memory rerun access promoted {flag}")
    for flag in _FALSE_READINESS_FLAGS:
        if rerun.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"runtime-memory rerun readiness promoted {flag}")
    if rerun.get("readiness", {}).get("runtime_memory_preflight_rerun_landed") is not True:
        raise CityOpsContractError("runtime-memory rerun landed flag missing")
    if rerun.get("readiness", {}).get("read_only_preflight_reran") is not True:
        raise CityOpsContractError("runtime-memory rerun read-only flag missing")
    if rerun.get("readiness", {}).get(
        "active_runner_can_import_acontext_via_explicit_venv"
    ) is not True:
        raise CityOpsContractError("runtime-memory rerun SDK bridge flag missing")
    if not rerun.get("current_blockers"):
        raise CityOpsContractError("runtime-memory rerun requires current blockers")
    bridge = rerun.get("runner_bridge", {})
    for flag in [
        "authorizes_live_write",
        "authorizes_live_retrieve",
        "authorizes_runtime_parity_claim",
    ]:
        if bridge.get(flag) is not False:
            raise CityOpsContractError(f"runtime-memory rerun bridge promoted {flag}")
    _assert_claim_boundaries(
        rerun.get("claim_boundaries", {}).get("safe_to_claim", []),
        rerun.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"runtime-memory rerun claim overlap: {overlap}")
    if ACONTEXT_RUNTIME_MEMORY_PREFLIGHT_RERUN_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("runtime-memory rerun safe claim missing")
    missing = sorted(set(RUNTIME_MEMORY_PREFLIGHT_RERUN_BLOCKED_CLAIMS) - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(f"runtime-memory rerun missing blocked claims: {missing}")


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
