"""Acontext SDK/API contract-discovery smoke observation for AAS.

This City-as-a-Service/AAS artifact records the May 30 3 AM bounded smoke
against the now-running local Acontext stack. It deliberately performs only
read-only contract discovery and authentication-shape checks: health, Swagger,
route inventory, and project-endpoint authorization behavior.

The artifact does not create an Acontext project/session, does not store or
retrieve messages, and does not promote runtime parity. Its job is to narrow the
next safe gate from "is the stack alive?" to "obtain or create a project bearer
secret in a separate controlled slice, then run exactly one write/retrieve
parity test."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_remaining_images_oras_compose_health_observation import (
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME,
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM,
    ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCHEMA,
    load_acontext_remaining_images_oras_compose_health,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCHEMA = (
    "city_ops.acontext_sdk_api_contract_discovery_smoke.v1"
)
ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME = (
    "acontext_sdk_api_contract_discovery_smoke.json"
)
ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM = (
    "admin_acontext_sdk_api_contract_discovery_smoke_landed"
)
ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_ID = (
    "execution_market.aas.acontext_sdk_api_contract_discovery_smoke.2026_05_30_0302"
)
ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCOPE = (
    "internal_admin_read_only_api_contract_discovery_no_project_session_write_or_retrieval"
)
ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_VERDICT = (
    "local_acontext_contract_surface_discovered_project_bearer_gate_blocks_write_retrieve_parity"
)

ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_BLOCKED_CLAIMS = [
    "sdk_api_contract_discovery_created_acontext_project",
    "sdk_api_contract_discovery_obtained_or_persisted_project_secret",
    "sdk_api_contract_discovery_created_acontext_session",
    "sdk_api_contract_discovery_stored_live_acontext_message",
    "sdk_api_contract_discovery_retrieved_live_acontext_message",
    "sdk_api_contract_discovery_proved_runtime_parity",
    "sdk_api_contract_discovery_changes_irc_runtime_session_manager",
    "sdk_api_contract_discovery_enables_cross_project_autorouting",
    "sdk_api_contract_discovery_authorizes_customer_copy_delivery_or_publication",
    "sdk_api_contract_discovery_authorizes_public_or_catalog_route",
    "sdk_api_contract_discovery_authorizes_pricing_or_customer_quote",
    "sdk_api_contract_discovery_authorizes_queue_launch_or_dispatch",
    "sdk_api_contract_discovery_authorizes_erc8004_reputation_or_worker_skill_dna",
    "sdk_api_contract_discovery_reverifies_payment_or_production",
    "sdk_api_contract_discovery_allows_exact_gps_or_raw_metadata",
    "sdk_api_contract_discovery_grants_domain_or_emergency_authority",
    "sdk_api_contract_discovery_creates_worker_copyable_doctrine",
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

_DISCOVERED_RELEVANT_PATHS = {
    "/session": ["get", "post"],
    "/session/{session_id}": ["delete"],
    "/session/{session_id}/messages": ["get", "post"],
    "/session/{session_id}/events": ["get", "post"],
    "/session/{session_id}/flush": ["post"],
    "/session/{session_id}/token_counts": ["get"],
    "/disk": ["get", "post"],
    "/disk/{disk_id}/artifact": ["get", "put", "post", "delete"],
    "/disk/{disk_id}/artifact/grep": ["get"],
    "/agent_skills": ["get", "post"],
    "/learning_spaces": ["get", "post"],
}

_AUTH_PROBES = [
    {"endpoint": "/api/v1/session", "method": "GET", "no_auth_status": 401, "root_token_status": 401},
    {"endpoint": "/api/v1/disk", "method": "GET", "no_auth_status": 401, "root_token_status": 401},
    {
        "endpoint": "/api/v1/project/configs",
        "method": "GET",
        "no_auth_status": 401,
        "root_token_status": 401,
    },
    {"endpoint": "/api/v1/agent_skills", "method": "GET", "no_auth_status": 401, "root_token_status": 401},
    {
        "endpoint": "/api/v1/learning_spaces",
        "method": "GET",
        "no_auth_status": 401,
        "root_token_status": 401,
    },
]


def build_may30_0302_sdk_api_contract_discovery_observation() -> dict[str, Any]:
    """Return sanitized facts from the bounded Acontext API discovery smoke."""

    return {
        "observation_window": "2026-05-30T03:00:51-04:00/2026-05-30T03:03:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "compose_project": "acontext-server",
        "compose_config_file": "~/clawd/infra/acontext/.docker-compose-1411407133.yaml",
        "diagnostic_reason": (
            "perform_one_bounded_sdk_api_contract_discovery_smoke_after_local_acontext_compose_health_passed"
        ),
        "sanitization_policy": {
            "include_tokens": False,
            "include_project_secret_values": False,
            "include_env_file_values": False,
            "include_raw_container_logs": False,
            "include_private_operator_context": False,
            "redact_auth_headers": True,
        },
        "local_stack_recheck": {
            "api_health": {"url": "http://127.0.0.1:8029/health", "status_code": 200, "shape": {"code": 0, "msg": "ok"}},
            "swagger_index": {"url": "http://127.0.0.1:8029/swagger/index.html", "status_code": 200},
            "swagger_doc": {
                "url": "http://127.0.0.1:8029/swagger/doc.json",
                "status_code": 200,
                "base_path": "/api/v1",
                "path_count": 52,
                "security_definition": "BearerAuth Project Bearer token in Authorization header",
            },
            "missing_openapi_locations": [
                {"url": "http://127.0.0.1:8029/openapi.json", "status_code": 404},
                {"url": "http://127.0.0.1:8029/api/v1/openapi.json", "status_code": 404},
            ],
        },
        "sdk_probe": {
            "python_package_importable_in_execution_market_venv": False,
            "package_name": "acontext",
            "error_class": "ModuleNotFoundError",
            "interpreted_as_blocking_sdk_smoke_only_not_blocking_raw_http_contract_discovery": True,
        },
        "contract_surface": {
            "swagger_available": True,
            "base_path": "/api/v1",
            "total_paths": 52,
            "relevant_paths": dict(_DISCOVERED_RELEVANT_PATHS),
            "session_write_contract_seen": True,
            "message_write_contract_seen": True,
            "message_retrieval_contract_seen": True,
            "artifact_disk_contract_seen": True,
            "learning_space_contract_seen": True,
        },
        "auth_gate": {
            "project_bearer_required": True,
            "root_api_bearer_token_value_recorded": False,
            "project_secret_value_available_to_this_smoke": False,
            "root_token_accepted_for_project_endpoints": False,
            "auth_probes": list(_AUTH_PROBES),
            "unauthorized_body_shape": {"code": 401, "msg": "Unauthorized"},
        },
        "mutating_smoke": {
            "attempted": False,
            "not_attempted_reason": (
                "project Bearer secret was not available to the read-only smoke; root token intentionally was not converted into a project secret or used to create a project"
            ),
            "created_project": False,
            "created_session": False,
            "stored_message": False,
            "retrieved_message": False,
        },
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "live_parity_not_attempted_reason": (
            "contract surface is now known, but write/retrieve parity requires a separate controlled gate that obtains or creates a project Bearer secret without leaking it"
        ),
    }


def build_acontext_sdk_api_contract_discovery_smoke(
    *,
    artifact_dir: str | Path | None = None,
    compose_health: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic Acontext SDK/API contract-discovery smoke artifact."""

    source = compose_health or load_acontext_remaining_images_oras_compose_health(artifact_dir=artifact_dir)
    observed = observation or build_may30_0302_sdk_api_contract_discovery_observation()
    _assert_compose_health_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM,
            ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        source["claim_boundaries"]["do_not_claim_yet"]
        + ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_BLOCKED_CLAIMS
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCHEMA,
        "observation_id": ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_ID,
        "scope": ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_SCOPE,
        "source_artifacts": {
            "remaining_images_oras_compose_health": {
                "file": ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME],
            "runtime_observation_performed": True,
            "uses_running_local_stack": True,
            "fetches_swagger_contract": True,
            "probes_project_endpoint_auth_shape": True,
            "uses_or_records_secret_values": False,
            "creates_project_or_session": False,
            "stores_or_retrieves_message": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_VERDICT,
        "readiness": {
            "all_required_images_present": True,
            "compose_services_started": True,
            "acontext_api_health_reachable": True,
            "swagger_contract_reachable": True,
            "python_sdk_importable_in_repo_venv": False,
            "contract_surface_discovered": True,
            "project_bearer_required": True,
            "project_bearer_available_to_smoke": False,
            "mutating_write_retrieve_smoke_attempted": False,
            "live_acontext_write_performed": False,
            "live_acontext_retrieval_performed": False,
            "runtime_parity_proven": False,
        },
        "runtime_truth_gates": [
            {
                "gate": "local_stack_health_recheck",
                "passed": True,
                "evidence": "API /health and Swagger UI/doc endpoints were reachable locally",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "sdk_import_available",
                "passed": False,
                "evidence": "execution-market .venv raised ModuleNotFoundError for package acontext",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "raw_http_contract_surface_discovered",
                "passed": True,
                "evidence": "Swagger doc exposed /api/v1 session, message, disk/artifact, skill, learning-space routes",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "project_bearer_auth_ready",
                "passed": False,
                "evidence": "project endpoints returned 401 without auth and also 401 when probed with root token; a project Bearer secret is a separate prerequisite",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "single_live_write_retrieve_parity_attempt",
                "passed": False,
                "evidence": "not attempted; no project Bearer secret was used or created in this read-only contract discovery slice",
                "authorizes_customer_or_dispatch_claim": False,
            },
        ],
        "operator_guidance": {
            "safe_next_step": (
                "In a separate controlled artifact, obtain or create exactly one local Acontext project Bearer secret without recording the value, then create one test session, store one sanitized message, retrieve it, and delete or quarantine the test object if the API supports cleanup."
            ),
            "stop_line": (
                "Do not claim Acontext sink readiness, IRC session-manager integration, cross-project autorouting, dispatch, reputation, customer copy, or worker doctrine until live write and retrieval both succeed."
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


def write_acontext_sdk_api_contract_discovery_smoke(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the Acontext SDK/API contract-discovery smoke fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME
    artifact = build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=target_dir)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_sdk_api_contract_discovery_smoke(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the Acontext SDK/API contract-discovery smoke fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = source_dir / ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact != build_acontext_sdk_api_contract_discovery_smoke(artifact_dir=source_dir):
        raise CityOpsContractError("Acontext SDK/API contract discovery smoke fixture drift")
    return artifact


def _assert_compose_health_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCHEMA:
        raise CityOpsContractError("source must be remaining-images ORAS Compose health")
    safe = source.get("claim_boundaries", {}).get("safe_to_claim", [])
    if ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM not in safe:
        raise CityOpsContractError("source missing remaining-images Compose health safe claim")
    readiness = source.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_health_reachable",
        "acontext_core_health_reachable",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"source must show successful field: {required}")
    if readiness.get("runtime_parity_proven") is not False:
        raise CityOpsContractError("source must not have runtime parity")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    local = observed.get("local_stack_recheck", {})
    sdk = observed.get("sdk_probe", {})
    contract = observed.get("contract_surface", {})
    auth = observed.get("auth_gate", {})
    mutating = observed.get("mutating_smoke", {})
    if local.get("api_health", {}).get("status_code") != 200:
        raise CityOpsContractError("API health must remain reachable")
    if local.get("swagger_doc", {}).get("status_code") != 200:
        raise CityOpsContractError("Swagger doc must be reachable")
    if local.get("swagger_doc", {}).get("base_path") != "/api/v1":
        raise CityOpsContractError("Swagger base path must be /api/v1")
    if local.get("swagger_doc", {}).get("path_count", 0) < 50:
        raise CityOpsContractError("Swagger path count unexpectedly narrow")
    if sdk.get("python_package_importable_in_execution_market_venv") is not False:
        raise CityOpsContractError("SDK import should remain false for this observation")
    for key in [
        "swagger_available",
        "session_write_contract_seen",
        "message_write_contract_seen",
        "message_retrieval_contract_seen",
    ]:
        if contract.get(key) is not True:
            raise CityOpsContractError(f"missing contract discovery flag: {key}")
    if auth.get("project_bearer_required") is not True:
        raise CityOpsContractError("project Bearer requirement must be recorded")
    if auth.get("root_api_bearer_token_value_recorded") is not False:
        raise CityOpsContractError("root token value must never be recorded")
    if auth.get("project_secret_value_available_to_this_smoke") is not False:
        raise CityOpsContractError("project secret must not be available in this smoke")
    if auth.get("root_token_accepted_for_project_endpoints") is not False:
        raise CityOpsContractError("root token must not be accepted for project endpoints")
    for probe in auth.get("auth_probes", []):
        if probe.get("no_auth_status") != 401 or probe.get("root_token_status") != 401:
            raise CityOpsContractError("auth probe should show 401/401 gate")
    if mutating.get("attempted") is not False:
        raise CityOpsContractError("mutating smoke must not be attempted")
    for forbidden in ["created_project", "created_session", "stored_message", "retrieved_message"]:
        if mutating.get(forbidden) is not False:
            raise CityOpsContractError(f"mutating flag promoted: {forbidden}")
    if observed.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("live write must not be claimed")
    if observed.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("live retrieval must not be claimed")


def _assert_artifact_conservative(artifact: dict[str, Any]) -> None:
    readiness = artifact.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_health_reachable",
        "swagger_contract_reachable",
        "contract_surface_discovered",
        "project_bearer_required",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"artifact must record successful field: {required}")
    for forbidden in [
        "python_sdk_importable_in_repo_venv",
        "project_bearer_available_to_smoke",
        "mutating_write_retrieve_smoke_attempted",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"promoted readiness: {forbidden}")
    if any(artifact.get("access_flags", {}).values()):
        raise CityOpsContractError("contract discovery smoke must not enable access flags")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"safe and blocked claim overlap: {sorted(overlap)}")
    required_blocked = set(ACONTEXT_SDK_API_CONTRACT_DISCOVERY_SMOKE_BLOCKED_CLAIMS)
    if not required_blocked <= set(do_not_claim_yet):
        raise CityOpsContractError("missing contract-discovery blocked claims")
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
            raise CityOpsContractError(f"unsafe contract discovery safe claim: {claim}")


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
