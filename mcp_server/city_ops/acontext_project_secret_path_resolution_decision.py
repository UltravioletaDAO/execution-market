"""Acontext project-secret path resolution decision for AAS.

This City-as-a-Service/AAS artifact records the next deterministic slice after
``acontext_project_admin_route_mismatch_observation``. It does not require a
running Acontext stack and does not perform another live probe. Instead, it
turns the known runtime truth into a bounded route/path resolution decision:
Swagger advertises ``POST /admin/v1/project``; the running local API returned
404 for both ``/admin/v1/project`` and ``/api/v1/admin/v1/project``; no project
Bearer secret was acquired; therefore the only safe next step is read-only route
mounting/config inspection or supported non-admin secret-path discovery.

No secret values, project IDs, session IDs, message IDs, raw logs, or private
operator context are recorded here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_project_admin_route_mismatch_observation import (
    ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME,
    ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM,
    ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCHEMA,
    load_acontext_project_admin_route_mismatch_observation,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCHEMA = (
    "city_ops.acontext_project_secret_path_resolution_decision.v1"
)
ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME = (
    "acontext_project_credential_path_resolution_decision.json"
)
ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM = (
    "admin_acontext_project_secret_path_resolution_decision_landed"
)
ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_ID = (
    "execution_market.aas.acontext_project_secret_path_resolution_decision.2026_05_30_0701"
)
ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCOPE = (
    "internal_admin_route_path_resolution_decision_no_live_probe_no_secret_recording_no_write"
)
ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_VERDICT = (
    "project_secret_path_resolution_still_blocked_route_mount_or_supported_non_admin_secret_path_inspection_required"
)
ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_STOP_LINE = (
    "If the project-secret route remains unresolved, stop before any write/retrieve parity, "
    "IRC session-manager mutation, cross-project autorouting, customer/public delivery, "
    "dispatch, reputation, payment, GPS/raw metadata, or worker-doctrine claim."
)

ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_BLOCKED_CLAIMS = [
    "project_secret_path_resolution_created_acontext_project",
    "project_secret_path_resolution_acquired_project_bearer_secret",
    "project_secret_path_resolution_persisted_or_printed_secret",
    "project_secret_path_resolution_created_acontext_session",
    "project_secret_path_resolution_stored_live_acontext_message",
    "project_secret_path_resolution_retrieved_live_acontext_message",
    "project_secret_path_resolution_proved_runtime_parity",
    "project_secret_path_resolution_changes_irc_runtime_session_manager",
    "project_secret_path_resolution_enables_cross_project_autorouting",
    "project_secret_path_resolution_authorizes_customer_copy_delivery_or_publication",
    "project_secret_path_resolution_authorizes_public_or_catalog_route",
    "project_secret_path_resolution_authorizes_pricing_or_customer_quote",
    "project_secret_path_resolution_authorizes_queue_launch_or_dispatch",
    "project_secret_path_resolution_authorizes_reputation_or_worker_skill_dna",
    "project_secret_path_resolution_reverifies_payment_or_production",
    "project_secret_path_resolution_allows_exact_gps_or_raw_metadata",
    "project_secret_path_resolution_grants_domain_or_emergency_authority",
    "project_secret_path_resolution_creates_worker_copyable_doctrine",
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


def build_may30_0701_project_secret_path_resolution_observation() -> dict[str, Any]:
    """Return the bounded project-secret path resolution decision facts."""

    return {
        "observation_window": "2026-05-30T07:01:00-04:00/2026-05-30T07:18:00-04:00",
        "host_scope": "local_artifact_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "does_not_require_live_acontext": True,
        "does_not_repeat_live_probe": True,
        "source_runtime_truth": {
            "swagger_admin_project_route_advertised": True,
            "swagger_admin_project_route": "POST /admin/v1/project",
            "swagger_base_path": "/api/v1",
            "runtime_probe_statuses": [
                {"path_shape": "/admin/v1/project", "method": "POST", "status_code": 404},
                {"path_shape": "/api/v1/admin/v1/project", "method": "POST", "status_code": 404},
            ],
            "project_bearer_secret_acquired": False,
            "project_bearer_secret_recorded": False,
            "live_write_retrieve_attempted": False,
        },
        "sanitization_policy": {
            "include_root_token_value": False,
            "include_project_secret_value": False,
            "include_project_id": False,
            "include_session_id": False,
            "include_message_id": False,
            "include_raw_container_logs": False,
            "include_private_operator_context": False,
            "redact_auth_headers": True,
        },
        "path_resolution_decision": {
            "current_route_state": "unresolved",
            "repeat_known_404_posts": False,
            "create_project": False,
            "request_or_store_project_secret": False,
            "run_write_retrieve_parity_smoke": False,
            "safe_next_paths": [
                {
                    "path": "route_mounting_or_config_inspection",
                    "mode": "read_only",
                    "requires_live_acontext": False,
                    "may_print_or_persist_secret_values": False,
                    "success_condition": (
                        "identify why the advertised admin project route is not mounted or reachable in the running API"
                    ),
                },
                {
                    "path": "supported_non_admin_secret_path_discovery",
                    "mode": "read_only_contract_or_config_discovery",
                    "requires_live_acontext": False,
                    "may_print_or_persist_secret_values": False,
                    "success_condition": (
                        "identify a supported local project-secret creation path without logging the resulting secret"
                    ),
                },
            ],
            "rejected_paths_for_this_slice": [
                {
                    "path": "repeat_raw_or_basepath_admin_project_post",
                    "reason": "source observation already recorded 404 at both known advertised path shapes",
                },
                {
                    "path": "write_retrieve_parity_without_project_bearer",
                    "reason": "prior contract discovery proved project Bearer auth is required",
                },
            ],
            "stop_line": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_STOP_LINE,
        },
    }


def build_acontext_project_secret_path_resolution_decision(
    *,
    artifact_dir: str | Path | None = None,
    route_mismatch: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic Acontext project-secret path resolution artifact."""

    source = route_mismatch or load_acontext_project_admin_route_mismatch_observation(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may30_0701_project_secret_path_resolution_observation()
    _assert_route_mismatch_source(source)
    _assert_observation_conservative(observed)

    inherited_blocked = list(source["claim_boundaries"]["do_not_claim_yet"])
    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM,
            ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        inherited_blocked + ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_BLOCKED_CLAIMS
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet, inherited_blocked)

    artifact = {
        "schema": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCHEMA,
        "observation_id": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_ID,
        "scope": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCOPE,
        "source_artifacts": {
            "project_admin_route_mismatch_observation": {
                "file": ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME],
            "runtime_observation_performed": False,
            "uses_running_local_stack": False,
            "requires_live_acontext": False,
            "creates_project_or_session": False,
            "stores_or_retrieves_message": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_VERDICT,
        "readiness": {
            "all_required_images_present": True,
            "compose_services_started": True,
            "acontext_api_health_reachable_in_source": True,
            "swagger_contract_reachable_in_source": True,
            "admin_project_route_advertised_by_swagger": True,
            "known_admin_project_route_status_404": True,
            "project_secret_path_resolved": False,
            "project_bearer_available_to_probe": False,
            "project_created": False,
            "mutating_write_retrieve_smoke_attempted": False,
            "live_acontext_write_performed": False,
            "live_acontext_retrieval_performed": False,
            "runtime_parity_proven": False,
        },
        "resolution_gates": [
            {
                "gate": "route_mismatch_source_loaded",
                "passed": True,
                "evidence": "source fixture records Swagger advertisement and two 404 runtime probes",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "secret_path_resolved",
                "passed": False,
                "evidence": "no mounted admin route or supported non-admin project-secret path has been identified yet",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "project_bearer_secret_acquired",
                "passed": False,
                "evidence": "secret path remains unresolved and no secret value was printed or persisted",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "single_live_write_retrieve_parity_attempt",
                "passed": False,
                "evidence": "blocked until a scoped project Bearer secret exists in memory",
                "authorizes_customer_or_dispatch_claim": False,
            },
        ],
        "claim_boundary_audit": {
            "inherited_do_not_claim_yet_preserved": True,
            "inherited_do_not_claim_yet": inherited_blocked,
            "inherited_do_not_claim_yet_digest_sha256": _stable_digest(inherited_blocked),
            "new_blocked_claims": list(ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_BLOCKED_CLAIMS),
        },
        "operator_guidance": {
            "safe_next_step": (
                "Inspect route mounting/config or discover a supported non-admin project-secret path without printing or persisting secrets."
            ),
            "stop_line": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
    }
    _assert_artifact_conservative(artifact, inherited_blocked)
    return artifact


def write_acontext_project_secret_path_resolution_decision(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the Acontext project-secret path resolution decision fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME
    artifact = build_acontext_project_secret_path_resolution_decision(artifact_dir=target_dir)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_project_secret_path_resolution_decision(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the Acontext project-secret path resolution fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = source_dir / ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact != build_acontext_project_secret_path_resolution_decision(artifact_dir=source_dir):
        raise CityOpsContractError("Acontext project-secret path resolution fixture drift")
    return artifact


def _assert_route_mismatch_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCHEMA:
        raise CityOpsContractError("source must be project-admin route mismatch observation")
    safe = source.get("claim_boundaries", {}).get("safe_to_claim", [])
    if ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM not in safe:
        raise CityOpsContractError("source missing project-admin route mismatch safe claim")
    readiness = source.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_health_reachable",
        "swagger_contract_reachable",
        "contract_surface_discovered",
        "admin_project_route_advertised_by_swagger",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"source must show successful field: {required}")
    for forbidden in [
        "admin_project_route_reachable",
        "project_bearer_available_to_probe",
        "project_created",
        "mutating_write_retrieve_smoke_attempted",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"source promoted forbidden field: {forbidden}")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    if observed.get("does_not_require_live_acontext") is not True:
        raise CityOpsContractError("resolution decision must be safe without live Acontext")
    if observed.get("does_not_repeat_live_probe") is not True:
        raise CityOpsContractError("resolution decision must not repeat live probes")
    truth = observed.get("source_runtime_truth", {})
    if truth.get("swagger_admin_project_route_advertised") is not True:
        raise CityOpsContractError("source route advertisement must be preserved")
    statuses = truth.get("runtime_probe_statuses", [])
    expected_paths = {"/admin/v1/project", "/api/v1/admin/v1/project"}
    if {status.get("path_shape") for status in statuses} != expected_paths:
        raise CityOpsContractError("must preserve both known admin project path probes")
    if any(status.get("status_code") != 404 for status in statuses):
        raise CityOpsContractError("known admin project path probes must remain 404")
    for forbidden in [
        "project_bearer_secret_acquired",
        "project_bearer_secret_recorded",
        "live_write_retrieve_attempted",
    ]:
        if truth.get(forbidden) is not False:
            raise CityOpsContractError(f"source runtime truth promoted: {forbidden}")
    policy = observed.get("sanitization_policy", {})
    for forbidden in [
        "include_root_token_value",
        "include_project_secret_value",
        "include_project_id",
        "include_session_id",
        "include_message_id",
        "include_raw_container_logs",
        "include_private_operator_context",
    ]:
        if policy.get(forbidden) is not False:
            raise CityOpsContractError(f"sanitization policy promoted: {forbidden}")
    decision = observed.get("path_resolution_decision", {})
    if decision.get("current_route_state") != "unresolved":
        raise CityOpsContractError("route state must remain unresolved")
    for forbidden in [
        "repeat_known_404_posts",
        "create_project",
        "request_or_store_project_secret",
        "run_write_retrieve_parity_smoke",
    ]:
        if decision.get(forbidden) is not False:
            raise CityOpsContractError(f"path resolution decision promoted: {forbidden}")
    stop_line = decision.get("stop_line", "")
    for required in ["route remains unresolved", "write/retrieve parity", "customer/public", "dispatch", "payment"]:
        if required not in stop_line:
            raise CityOpsContractError(f"stop line missing required boundary: {required}")


def _assert_artifact_conservative(artifact: dict[str, Any], inherited_blocked: list[str]) -> None:
    readiness = artifact.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_health_reachable_in_source",
        "swagger_contract_reachable_in_source",
        "admin_project_route_advertised_by_swagger",
        "known_admin_project_route_status_404",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"artifact must record successful field: {required}")
    for forbidden in [
        "project_secret_path_resolved",
        "project_bearer_available_to_probe",
        "project_created",
        "mutating_write_retrieve_smoke_attempted",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"promoted readiness: {forbidden}")
    if any(artifact.get("access_flags", {}).values()):
        raise CityOpsContractError("project-secret path resolution must not enable access flags")
    audit = artifact.get("claim_boundary_audit", {})
    if audit.get("inherited_do_not_claim_yet") != inherited_blocked:
        raise CityOpsContractError("inherited blocked claims were not preserved exactly")
    if audit.get("inherited_do_not_claim_yet_digest_sha256") != _stable_digest(inherited_blocked):
        raise CityOpsContractError("inherited blocked claim digest drift")
    if artifact.get("operator_guidance", {}).get("stop_line") != ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_STOP_LINE:
        raise CityOpsContractError("stop line drift")


def _assert_claim_boundaries(
    safe_to_claim: list[str], do_not_claim_yet: list[str], inherited_blocked: list[str]
) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"safe and blocked claim overlap: {sorted(overlap)}")
    if inherited_blocked != do_not_claim_yet[: len(inherited_blocked)]:
        raise CityOpsContractError("inherited blocked claims must be preserved exactly and first")
    required_blocked = set(ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_BLOCKED_CLAIMS)
    if not required_blocked <= set(do_not_claim_yet):
        raise CityOpsContractError("missing project-secret path resolution blocked claims")
    forbidden_safe_fragments = [
        "created_acontext_project",
        "acquired_project_bearer_secret",
        "persisted_or_printed_secret",
        "stored_live_acontext",
        "retrieved_live_acontext",
        "runtime_parity",
        "authorizes_customer",
        "public_or_catalog",
        "queue_launch",
        "dispatch",
        "reputation",
        "payment_or_production",
        "gps_or_raw_metadata",
        "worker_copyable_doctrine",
    ]
    for claim in safe_to_claim:
        if any(fragment in claim for fragment in forbidden_safe_fragments):
            raise CityOpsContractError(f"unsafe project-secret path resolution safe claim: {claim}")


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
