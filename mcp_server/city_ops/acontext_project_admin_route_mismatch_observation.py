"""Acontext project-admin route mismatch observation for AAS.

The 3 AM contract-discovery smoke proved the local Acontext API and Swagger
contract were reachable, but it stopped before a live write/retrieve parity
attempt because a project Bearer secret was not available.  The next obvious
safe gate was to create exactly one local project via the documented admin
route, keep the returned project secret in memory only, then create and retrieve
one sanitized session message.

This artifact records the bounded 4 AM attempt at that gate.  It deliberately
keeps all secret values out of the fixture.  The important runtime truth is that
Swagger advertises ``/admin/v1/project`` while the running API returns 404 for
both the raw and basePath-prefixed admin paths, so project-secret acquisition is
still blocked before any live Acontext write can be attempted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_sdk_api_contract_discovery_smoke import (
    ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME,
    ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM,
    ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCHEMA,
    load_acontext_sdk_api_contract_discovery_smoke,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCHEMA = (
    "city_ops.acontext_project_admin_route_mismatch_observation.v1"
)
ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME = (
    "acontext_project_admin_route_mismatch_observation.json"
)
ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM = (
    "admin_acontext_project_admin_route_mismatch_observation_landed"
)
ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_ID = (
    "execution_market.aas.acontext_project_admin_route_mismatch.2026_05_30_0407"
)
ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCOPE = (
    "internal_admin_local_project_secret_gate_probe_no_secret_recording_no_live_write"
)
ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_VERDICT = (
    "swagger_advertises_admin_project_route_but_running_api_returns_404_project_secret_gate_still_blocked"
)

ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_BLOCKED_CLAIMS = [
    "admin_route_mismatch_created_acontext_project",
    "admin_route_mismatch_obtained_or_recorded_project_secret",
    "admin_route_mismatch_created_acontext_session",
    "admin_route_mismatch_stored_live_acontext_message",
    "admin_route_mismatch_retrieved_live_acontext_message",
    "admin_route_mismatch_proved_runtime_parity",
    "admin_route_mismatch_changes_irc_runtime_session_manager",
    "admin_route_mismatch_enables_cross_project_autorouting",
    "admin_route_mismatch_authorizes_customer_copy_delivery_or_publication",
    "admin_route_mismatch_authorizes_public_or_catalog_route",
    "admin_route_mismatch_authorizes_pricing_or_customer_quote",
    "admin_route_mismatch_authorizes_queue_launch_or_dispatch",
    "admin_route_mismatch_authorizes_erc8004_reputation_or_worker_skill_dna",
    "admin_route_mismatch_reverifies_payment_or_production",
    "admin_route_mismatch_allows_exact_gps_or_raw_metadata",
    "admin_route_mismatch_grants_domain_or_emergency_authority",
    "admin_route_mismatch_creates_worker_copyable_doctrine",
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


def build_may30_0407_project_admin_route_mismatch_observation() -> dict[str, Any]:
    """Return sanitized facts from the bounded admin route probe."""

    return {
        "observation_window": "2026-05-30T04:07:00-04:00/2026-05-30T04:13:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "acontext_runtime": {
            "api_base": "http://127.0.0.1:8029",
            "swagger_doc_status_code": 200,
            "swagger_base_path": "/api/v1",
            "swagger_admin_project_route_advertised": True,
            "swagger_admin_project_methods": ["post"],
            "postgres_tables_seen_without_secret_values": [
                "projects",
                "sessions",
                "messages",
            ],
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
        "root_token_probe": {
            "root_token_available_to_local_probe": True,
            "root_token_value_recorded": False,
            "root_token_sent_only_to_localhost": True,
        },
        "admin_project_route_probes": [
            {
                "method": "POST",
                "url_shape": "http://127.0.0.1:8029/admin/v1/project",
                "body_shape": {"configs": {"purpose": "shape_probe", "run_id": "uuid"}},
                "status_code": 404,
                "response_shape": "plain_404_page_not_found",
                "secret_value_recorded": False,
            },
            {
                "method": "POST",
                "url_shape": "http://127.0.0.1:8029/api/v1/admin/v1/project",
                "body_shape": {"configs": {"purpose": "shape_probe", "run_id": "uuid"}},
                "status_code": 404,
                "response_shape": "plain_404_page_not_found",
                "secret_value_recorded": False,
            },
        ],
        "live_parity_attempt": {
            "attempted": False,
            "not_attempted_reason": (
                "the documented local admin project route returned 404 before any project secret could be obtained"
            ),
            "created_project": False,
            "obtained_project_secret_in_memory": False,
            "recorded_project_secret": False,
            "created_session": False,
            "stored_message": False,
            "retrieved_message": False,
            "deleted_test_session": False,
            "deleted_test_project": False,
        },
        "runtime_truth_delta": {
            "previous_gate": "contract_surface_discovered_project_bearer_required",
            "new_blocker": "project_admin_route_mismatch_404",
            "blocker_type": "documented_route_not_mounted_or_not_reachable_in_running_local_api",
            "narrows_next_step": True,
        },
    }


def build_acontext_project_admin_route_mismatch_observation(
    *,
    artifact_dir: str | Path | None = None,
    contract_discovery: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic Acontext project-admin route mismatch artifact."""

    source = contract_discovery or load_acontext_sdk_api_contract_discovery_smoke(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may30_0407_project_admin_route_mismatch_observation()
    _assert_contract_discovery_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM,
            ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        source["claim_boundaries"]["do_not_claim_yet"]
        + ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_BLOCKED_CLAIMS
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCHEMA,
        "observation_id": ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_ID,
        "scope": ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_SCOPE,
        "source_artifacts": {
            "sdk_api_contract_discovery_smoke": {
                "file": ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME],
            "runtime_observation_performed": True,
            "uses_running_local_stack": True,
            "uses_root_token_without_recording_value": True,
            "creates_project_or_session": False,
            "stores_or_retrieves_message": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_VERDICT,
        "readiness": {
            "all_required_images_present": True,
            "compose_services_started": True,
            "acontext_api_health_reachable": True,
            "swagger_contract_reachable": True,
            "contract_surface_discovered": True,
            "admin_project_route_advertised_by_swagger": True,
            "admin_project_route_reachable": False,
            "project_bearer_available_to_probe": False,
            "project_created": False,
            "mutating_write_retrieve_smoke_attempted": False,
            "live_acontext_write_performed": False,
            "live_acontext_retrieval_performed": False,
            "runtime_parity_proven": False,
        },
        "runtime_truth_gates": [
            {
                "gate": "contract_discovery_source_loaded",
                "passed": True,
                "evidence": "prior source discovered the session/message contract and project Bearer requirement",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "root_token_available_without_recording_value",
                "passed": True,
                "evidence": "local env exposed a root token to the probe; the value was not logged or persisted",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "admin_project_route_reachable",
                "passed": False,
                "evidence": "documented /admin/v1/project returned 404 at raw and /api/v1-prefixed paths",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "project_bearer_secret_obtained",
                "passed": False,
                "evidence": "route mismatch prevented project creation and project secret acquisition",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "single_live_write_retrieve_parity_attempt",
                "passed": False,
                "evidence": "not attempted because project Bearer secret was unavailable",
                "authorizes_customer_or_dispatch_claim": False,
            },
        ],
        "operator_guidance": {
            "safe_next_step": (
                "Resolve why the running local API advertises /admin/v1/project in Swagger while returning 404, or identify the supported non-admin project-secret creation path. Only then run the one sanitized write/retrieve parity smoke."
            ),
            "stop_line": (
                "Do not claim Acontext sink readiness, IRC session-manager integration, cross-project autorouting, customer/public delivery, dispatch, reputation, payment, GPS/raw metadata, or worker doctrine from this mismatch observation."
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


def write_acontext_project_admin_route_mismatch_observation(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the Acontext project-admin route mismatch fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME
    artifact = build_acontext_project_admin_route_mismatch_observation(
        artifact_dir=target_dir
    )
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_project_admin_route_mismatch_observation(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the Acontext project-admin route mismatch fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = source_dir / ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact != build_acontext_project_admin_route_mismatch_observation(
        artifact_dir=source_dir
    ):
        raise CityOpsContractError("Acontext project-admin route mismatch fixture drift")
    return artifact


def _assert_contract_discovery_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCHEMA:
        raise CityOpsContractError("source must be SDK/API contract-discovery smoke")
    safe = source.get("claim_boundaries", {}).get("safe_to_claim", [])
    if ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("source missing SDK/API contract-discovery safe claim")
    readiness = source.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_health_reachable",
        "swagger_contract_reachable",
        "contract_surface_discovered",
        "project_bearer_required",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"source must show successful field: {required}")
    for forbidden in [
        "project_bearer_available_to_smoke",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"source promoted forbidden field: {forbidden}")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    runtime = observed.get("acontext_runtime", {})
    root = observed.get("root_token_probe", {})
    probes = observed.get("admin_project_route_probes", [])
    parity = observed.get("live_parity_attempt", {})
    delta = observed.get("runtime_truth_delta", {})
    if runtime.get("swagger_doc_status_code") != 200:
        raise CityOpsContractError("Swagger doc must remain reachable")
    if runtime.get("swagger_base_path") != "/api/v1":
        raise CityOpsContractError("Swagger base path must remain /api/v1")
    if runtime.get("swagger_admin_project_route_advertised") is not True:
        raise CityOpsContractError("admin project route advertisement must be recorded")
    if root.get("root_token_available_to_local_probe") is not True:
        raise CityOpsContractError("root token availability must be recorded")
    if root.get("root_token_value_recorded") is not False:
        raise CityOpsContractError("root token value must not be recorded")
    if len(probes) < 2:
        raise CityOpsContractError("expected raw and basePath admin route probes")
    for probe in probes:
        if probe.get("status_code") != 404:
            raise CityOpsContractError("admin project route mismatch should record 404")
        if probe.get("secret_value_recorded") is not False:
            raise CityOpsContractError("project secret value must never be recorded")
    for forbidden in [
        "attempted",
        "created_project",
        "obtained_project_secret_in_memory",
        "recorded_project_secret",
        "created_session",
        "stored_message",
        "retrieved_message",
    ]:
        if parity.get(forbidden) is not False:
            raise CityOpsContractError(f"parity/mutation flag promoted: {forbidden}")
    if delta.get("new_blocker") != "project_admin_route_mismatch_404":
        raise CityOpsContractError("runtime truth delta must name the 404 route mismatch")


def _assert_artifact_conservative(artifact: dict[str, Any]) -> None:
    readiness = artifact.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_health_reachable",
        "swagger_contract_reachable",
        "contract_surface_discovered",
        "admin_project_route_advertised_by_swagger",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"artifact must record successful field: {required}")
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
            raise CityOpsContractError(f"promoted readiness: {forbidden}")
    if any(artifact.get("access_flags", {}).values()):
        raise CityOpsContractError("admin route mismatch must not enable access flags")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"safe and blocked claim overlap: {sorted(overlap)}")
    required_blocked = set(ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_BLOCKED_CLAIMS)
    if not required_blocked <= set(do_not_claim_yet):
        raise CityOpsContractError("missing admin-route-mismatch blocked claims")
    forbidden_safe_fragments = [
        "created_acontext_project",
        "stored_live_acontext",
        "retrieved_live_acontext",
        "runtime_parity",
        "authorizes_customer",
        "queue_launch",
        "dispatch",
        "worker_skill_dna",
        "gps_or_raw_metadata",
    ]
    for claim in safe_to_claim:
        if any(fragment in claim for fragment in forbidden_safe_fragments):
            raise CityOpsContractError(f"unsafe admin route mismatch safe claim: {claim}")


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
