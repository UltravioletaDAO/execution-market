"""Acontext root-prefixed local write/retrieve parity proof for AAS.

This City-as-a-Service/AAS artifact records the first bounded local Acontext
write/retrieve success after the admin project route mismatch. The route
mismatch remains true: Swagger still advertises an admin project route that is
not mounted at either known runtime path. The new discovery is narrower and
more useful: the shipped UI server calls the API with a root-prefixed bearer
header shape, ``Authorization: Bearer sk-ac-${ROOT_API_BEARER_TOKEN}``, and that
same in-memory header shape successfully created a sanitized local session,
stored one sanitized message, and retrieved the same message.

No root token, derived bearer value, project secret, project ID, user ID,
session ID, message ID, raw container logs, private operator context, GPS/raw
metadata, or customer data is persisted here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_project_secret_path_resolution_decision import (
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME,
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM,
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCHEMA,
    load_acontext_project_secret_path_resolution_decision,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCHEMA = (
    "city_ops.acontext_root_prefixed_local_write_retrieve_parity.v1"
)
ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME = (
    "acontext_root_prefixed_local_write_retrieve_parity.json"
)
ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM = (
    "admin_acontext_root_prefixed_local_parity_landed"
)
ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_ID = (
    "execution_market.aas.acontext_root_prefixed_local_write_retrieve_parity.2026_05_31_0307"
)
ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCOPE = (
    "internal_admin_local_acontext_write_retrieve_parity_root_prefixed_auth_no_secret_recording"
)
ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_VERDICT = (
    "local_acontext_write_retrieve_parity_succeeded_with_root_prefixed_bearer_route_mismatch_still_unresolved"
)
ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_STOP_LINE = (
    "Local write/retrieve parity via root-prefixed bearer does not authorize customer/public delivery, "
    "IRC session-manager mutation, cross-project autorouting, dispatch, reputation, payment/production claims, "
    "GPS/raw metadata exposure, private-context release, or worker-copyable doctrine."
)

ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_BLOCKED_CLAIMS = [
    "root_prefixed_local_parity_admin_project_route_resolved",
    "root_prefixed_local_parity_scoped_project_secret_created_or_acquired",
    "root_prefixed_local_parity_persisted_or_printed_root_token_or_bearer",
    "root_prefixed_local_parity_persisted_project_id_user_id_session_id_or_message_id",
    "root_prefixed_local_parity_proves_production_or_remote_acontext",
    "root_prefixed_local_parity_marks_irc_runtime_session_manager_ready",
    "root_prefixed_local_parity_enables_cross_project_autorouting",
    "root_prefixed_local_parity_authorizes_customer_copy_delivery_or_publication",
    "root_prefixed_local_parity_authorizes_public_or_catalog_route",
    "root_prefixed_local_parity_authorizes_pricing_or_customer_quote",
    "root_prefixed_local_parity_authorizes_queue_launch_or_dispatch",
    "root_prefixed_local_parity_authorizes_reputation_or_worker_skill_dna",
    "root_prefixed_local_parity_reverifies_payment_or_production",
    "root_prefixed_local_parity_allows_exact_gps_or_raw_metadata",
    "root_prefixed_local_parity_releases_private_operator_context",
    "root_prefixed_local_parity_grants_domain_or_emergency_authority",
    "root_prefixed_local_parity_creates_worker_copyable_doctrine",
]

_FALSE_ACCESS_FLAGS = {
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "changes_irc_runtime_session_manager": False,
    "enables_cross_project_autorouting": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "releases_private_operator_context": False,
    "publishes_worker_doctrine": False,
}


def build_may31_0307_root_prefixed_local_parity_observation() -> dict[str, Any]:
    """Return the redacted facts from the bounded local write/retrieve smoke."""

    sanitized_message = (
        "Execution Market AAS local parity smoke: sanitized message, no private context."
    )
    return {
        "observation_window": "2026-05-31T03:07:00Z/2026-05-31T03:08:00Z",
        "host_scope": "local_acontext_compose_stack_only_no_external_publish",
        "working_directory": "~/clawd/infra/acontext",
        "api_base": "http://127.0.0.1:8029/api/v1",
        "credential_path_discovery": {
            "source": "compiled_acontext_ui_server_bundle_read_only_inspection",
            "ui_server_auth_header_shape": "Authorization: Bearer sk-ac-${ROOT_API_BEARER_TOKEN}",
            "root_token_value_printed": False,
            "derived_bearer_value_printed": False,
            "derived_bearer_value_persisted": False,
            "scoped_project_secret_created": False,
            "scoped_project_secret_recorded": False,
            "admin_project_route_still_unresolved": True,
        },
        "local_probe": {
            "used_root_prefixed_bearer_in_process_memory_only": True,
            "create_session": {
                "method": "POST",
                "path": "/api/v1/session",
                "status_code": 201,
                "sanitized_user": "em-aas-local-parity-2026-05-31",
                "disable_task_tracking": True,
                "session_id_recorded": False,
                "project_id_recorded": False,
                "user_id_recorded": False,
            },
            "store_message": {
                "method": "POST",
                "path": "/api/v1/session/{redacted_session_id}/messages",
                "status_code": 201,
                "message_id_recorded": False,
                "message_text": sanitized_message,
                "message_contains_private_context": False,
            },
            "retrieve_messages": {
                "method": "GET",
                "path": "/api/v1/session/{redacted_session_id}/messages?limit=5&format=acontext&with_events=true",
                "status_code": 200,
                "retrieved_message_count": 1,
                "retrieved_message_text_matches": True,
                "retrieved_message_meta_matches": True,
                "message_id_recorded": False,
                "session_id_recorded": False,
            },
        },
        "sanitization_policy": {
            "include_root_token_value": False,
            "include_derived_bearer_value": False,
            "include_project_secret_value": False,
            "include_project_id": False,
            "include_user_id": False,
            "include_session_id": False,
            "include_message_id": False,
            "include_raw_container_logs": False,
            "include_private_operator_context": False,
            "include_gps_or_raw_metadata": False,
            "redact_auth_headers": True,
        },
    }


def build_acontext_root_prefixed_local_write_retrieve_parity(
    *,
    artifact_dir: str | Path | None = None,
    path_resolution: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic local Acontext write/retrieve parity artifact."""

    source = path_resolution or load_acontext_project_secret_path_resolution_decision(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may31_0307_root_prefixed_local_parity_observation()
    _assert_path_resolution_source(source)
    _assert_observation_safe_and_successful(observed)

    inherited_blocked = list(source["claim_boundaries"]["do_not_claim_yet"])
    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM,
            ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        inherited_blocked + ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_BLOCKED_CLAIMS
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCHEMA,
        "observation_id": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_ID,
        "scope": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCOPE,
        "source_artifacts": {
            "project_secret_path_resolution_decision": {
                "file": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME],
            "uses_running_local_stack": True,
            "uses_root_prefixed_bearer_in_memory_only": True,
            "creates_project_or_scoped_secret": False,
            "persists_or_prints_secret": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_external_services": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_VERDICT,
        "readiness": {
            "all_required_images_present_in_source": True,
            "compose_services_started_in_source": True,
            "acontext_api_health_reachable_in_source": True,
            "admin_project_route_still_unresolved": True,
            "root_prefixed_bearer_supported_for_local_api": True,
            "sanitized_session_create_status_201": True,
            "sanitized_message_store_status_201": True,
            "sanitized_message_retrieve_status_200": True,
            "retrieved_message_text_matched": True,
            "local_write_retrieve_parity_proven": True,
            "scoped_project_secret_created_or_acquired": False,
            "production_or_remote_acontext_proven": False,
            "irc_runtime_session_manager_ready": False,
            "cross_project_autorouting_ready": False,
            "customer_or_public_delivery_ready": False,
        },
        "parity_gates": [
            {
                "gate": "root_prefixed_bearer_shape_discovered",
                "passed": True,
                "evidence": "compiled UI server bundle constructs Authorization: Bearer sk-ac-${ROOT_API_BEARER_TOKEN}",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "sanitized_session_create",
                "passed": True,
                "evidence": "POST /api/v1/session returned 201 with disable_task_tracking=true",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "sanitized_message_store",
                "passed": True,
                "evidence": "POST /api/v1/session/{redacted_session_id}/messages returned 201",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "sanitized_message_retrieve",
                "passed": True,
                "evidence": "GET /api/v1/session/{redacted_session_id}/messages returned 200 and matched text/meta",
                "authorizes_customer_or_dispatch_claim": False,
            },
        ],
        "claim_boundary_audit": {
            "inherited_do_not_claim_yet_preserved": True,
            "inherited_do_not_claim_yet": inherited_blocked,
            "inherited_do_not_claim_yet_digest_sha256": _stable_digest(inherited_blocked),
            "new_blocked_claims": list(ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_BLOCKED_CLAIMS),
        },
        "operator_guidance": {
            "safe_next_step": (
                "Wire an internal-only Acontext adapter proof that uses in-memory root-prefixed auth, "
                "then run one redacted IRC-session-shaped write/retrieve fixture without customer/public or dispatch claims."
            ),
            "stop_line": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
    }
    _assert_artifact_safe(artifact, inherited_blocked)
    return artifact


def write_acontext_root_prefixed_local_write_retrieve_parity(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the Acontext root-prefixed local parity fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME
    artifact = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=target_dir)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_root_prefixed_local_write_retrieve_parity(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the Acontext root-prefixed local parity fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = source_dir / ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact != build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=source_dir):
        raise CityOpsContractError("Acontext root-prefixed local parity fixture drift")
    return artifact


def _assert_path_resolution_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCHEMA:
        raise CityOpsContractError("source must be project-secret path resolution decision")
    if ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("source missing project-secret path resolution safe claim")
    readiness = source.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "acontext_api_health_reachable_in_source",
        "swagger_contract_reachable_in_source",
        "admin_project_route_advertised_by_swagger",
        "known_admin_project_route_status_404",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"source must show successful field: {required}")
    for forbidden in [
        "project_secret_path_resolved",
        "project_bearer_available_to_probe",
        "project_created",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"source promoted forbidden field: {forbidden}")


def _assert_observation_safe_and_successful(observed: dict[str, Any]) -> None:
    discovery = observed.get("credential_path_discovery", {})
    if discovery.get("ui_server_auth_header_shape") != "Authorization: Bearer sk-ac-${ROOT_API_BEARER_TOKEN}":
        raise CityOpsContractError("must record only the redacted root-prefixed bearer header shape")
    for forbidden in [
        "root_token_value_printed",
        "derived_bearer_value_printed",
        "derived_bearer_value_persisted",
        "scoped_project_secret_created",
        "scoped_project_secret_recorded",
    ]:
        if discovery.get(forbidden) is not False:
            raise CityOpsContractError(f"credential discovery leaked or promoted: {forbidden}")
    if discovery.get("admin_project_route_still_unresolved") is not True:
        raise CityOpsContractError("admin project route mismatch must remain unresolved")

    probe = observed.get("local_probe", {})
    if probe.get("used_root_prefixed_bearer_in_process_memory_only") is not True:
        raise CityOpsContractError("root-prefixed bearer must be in process memory only")
    expected = [
        ("create_session", 201),
        ("store_message", 201),
        ("retrieve_messages", 200),
    ]
    for section, status_code in expected:
        if probe.get(section, {}).get("status_code") != status_code:
            raise CityOpsContractError(f"{section} status drift")
    if probe.get("retrieve_messages", {}).get("retrieved_message_text_matches") is not True:
        raise CityOpsContractError("retrieved message text must match")
    if probe.get("retrieve_messages", {}).get("retrieved_message_meta_matches") is not True:
        raise CityOpsContractError("retrieved message meta must match")

    policy = observed.get("sanitization_policy", {})
    for forbidden in [
        "include_root_token_value",
        "include_derived_bearer_value",
        "include_project_secret_value",
        "include_project_id",
        "include_user_id",
        "include_session_id",
        "include_message_id",
        "include_raw_container_logs",
        "include_private_operator_context",
        "include_gps_or_raw_metadata",
    ]:
        if policy.get(forbidden) is not False:
            raise CityOpsContractError(f"sanitization policy promoted: {forbidden}")


def _assert_artifact_safe(artifact: dict[str, Any], inherited_blocked: list[str]) -> None:
    readiness = artifact.get("readiness", {})
    for required in [
        "root_prefixed_bearer_supported_for_local_api",
        "sanitized_session_create_status_201",
        "sanitized_message_store_status_201",
        "sanitized_message_retrieve_status_200",
        "retrieved_message_text_matched",
        "local_write_retrieve_parity_proven",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"artifact must record successful field: {required}")
    for forbidden in [
        "scoped_project_secret_created_or_acquired",
        "production_or_remote_acontext_proven",
        "irc_runtime_session_manager_ready",
        "cross_project_autorouting_ready",
        "customer_or_public_delivery_ready",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"promoted readiness: {forbidden}")
    if any(artifact.get("access_flags", {}).values()):
        raise CityOpsContractError("local parity must not enable access flags")
    audit = artifact.get("claim_boundary_audit", {})
    if audit.get("inherited_do_not_claim_yet") != inherited_blocked:
        raise CityOpsContractError("inherited blocked claims were not preserved exactly")
    if audit.get("inherited_do_not_claim_yet_digest_sha256") != _stable_digest(inherited_blocked):
        raise CityOpsContractError("inherited blocked claim digest drift")
    if artifact.get("operator_guidance", {}).get("stop_line") != ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_STOP_LINE:
        raise CityOpsContractError("stop line drift")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"safe and blocked claim overlap: {sorted(overlap)}")
    required_blocked = set(ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_BLOCKED_CLAIMS)
    if not required_blocked <= set(do_not_claim_yet):
        raise CityOpsContractError("missing root-prefixed local parity blocked claims")
    forbidden_safe_fragments = [
        "route_resolved",
        "scoped_project_secret",
        "root_token",
        "bearer",
        "production_or_remote",
        "session_manager_ready",
        "autorouting",
        "authorizes_customer",
        "public_or_catalog",
        "queue_launch",
        "dispatch",
        "reputation",
        "payment_or_production",
        "gps_or_raw_metadata",
        "private_operator_context",
        "worker_copyable_doctrine",
    ]
    for claim in safe_to_claim:
        if any(fragment in claim for fragment in forbidden_safe_fragments):
            raise CityOpsContractError(f"unsafe root-prefixed local parity safe claim: {claim}")


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
