"""Redacted local runner fixture for the internal IRC-shaped Acontext adapter.

This AAS proof block records one bounded live local runner execution against the
Acontext compose stack using the internal IRC-session-shaped adapter contract.
The runner kept the root-prefixed bearer, session ID, and message ID in process
memory only. The persisted artifact records only status codes and sanitized
text/metadata match booleans.

It deliberately does **not** mutate IRC runtime session management, enable
cross-project autorouting, register customer/public routes, launch dispatch,
emit reputation, verify payments, expose GPS/raw metadata, release private
operator context, or publish worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_internal_irc_session_adapter_contract import (
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCHEMA,
    load_acontext_internal_irc_session_adapter_contract,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCHEMA = (
    "city_ops.acontext_internal_irc_session_adapter_runner_fixture.v1"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME = (
    "acontext_internal_irc_session_adapter_runner_fixture.json"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM = (
    "admin_acontext_internal_irc_session_adapter_runner_fixture_landed"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_ID = (
    "execution_market.aas.acontext_internal_irc_session_adapter_runner_fixture.2026_05_31_0405"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCOPE = (
    "internal_admin_local_redacted_irc_session_adapter_runner_no_runtime_mutation"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_VERDICT = (
    "local_redacted_irc_session_adapter_runner_succeeded_without_runtime_mutation"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_STOP_LINE = (
    "The redacted local IRC-shaped Acontext runner succeeded for one sanitized fixture only; "
    "it does not authorize IRC runtime session-manager mutation, cross-project autorouting, "
    "customer/public delivery, dispatch, reputation, payment/production claims, GPS/raw metadata "
    "exposure, private-context release, or worker-copyable doctrine."
)

_LIFTED_SOURCE_BLOCKERS = ["internal_irc_adapter_executed_live_runner_fixture"]

ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_BLOCKED_CLAIMS = [
    "internal_irc_adapter_runner_mutates_irc_runtime_session_manager",
    "internal_irc_adapter_runner_enables_cross_project_autorouting",
    "internal_irc_adapter_runner_authorizes_customer_copy_delivery_or_publication",
    "internal_irc_adapter_runner_authorizes_public_or_catalog_route",
    "internal_irc_adapter_runner_authorizes_pricing_or_customer_quote",
    "internal_irc_adapter_runner_authorizes_queue_launch_or_dispatch",
    "internal_irc_adapter_runner_authorizes_reputation_or_worker_skill_dna",
    "internal_irc_adapter_runner_reverifies_payment_or_production",
    "internal_irc_adapter_runner_allows_exact_gps_or_raw_metadata",
    "internal_irc_adapter_runner_releases_private_operator_context",
    "internal_irc_adapter_runner_grants_domain_or_emergency_authority",
    "internal_irc_adapter_runner_creates_worker_copyable_doctrine",
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

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-ac-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
]


def build_may31_0405_internal_irc_session_adapter_runner_observation() -> dict[str, Any]:
    """Return the redacted facts from the bounded local runner execution."""

    sanitized_message = (
        "Execution Market AAS IRC-shaped adapter runner: sanitized message, no private context."
    )
    return {
        "observation_window": "2026-05-31T04:03:00Z/2026-05-31T04:05:00Z",
        "host_scope": "local_acontext_compose_stack_only_no_external_publish",
        "working_directories": [
            "~/clawd/projects/execution-market",
            "~/clawd/infra/acontext",
        ],
        "api_base": "http://127.0.0.1:8029/api/v1",
        "runner_input": {
            "packet_kind": "irc_session_memory_candidate",
            "message_text": sanitized_message,
            "metadata": {
                "project": "execution-market-aas",
                "surface": "internal_admin_only",
                "packet_kind": "irc_session_memory_candidate",
                "contains_private_context": False,
                "contains_gps_or_raw_metadata": False,
                "customer_visible": False,
                "worker_visible": False,
            },
            "message_format": "openai",
            "session_user_label": "em-aas-irc-adapter-runner-final-2026-05-31",
        },
        "local_runner_probe": {
            "used_root_prefixed_bearer_in_process_memory_only": True,
            "root_token_value_printed": False,
            "derived_bearer_value_printed": False,
            "derived_bearer_value_persisted": False,
            "create_session": {
                "method": "POST",
                "path": "/api/v1/session",
                "status_code": 201,
                "disable_task_tracking": True,
                "session_id_present_in_process_memory": True,
                "session_id_recorded": False,
            },
            "store_message": {
                "method": "POST",
                "path": "/api/v1/session/{redacted_session_id}/messages",
                "status_code": 201,
                "payload_shape": "{blob:{role,content},format:openai,meta:{sanitized_flags}}",
                "message_id_recorded": False,
            },
            "retrieve_messages": {
                "method": "GET",
                "path": "/api/v1/session/{redacted_session_id}/messages?limit=5&format=acontext&with_events=true",
                "status_code": 200,
                "retrieved_message_count_at_least_one": True,
                "retrieved_message_text_matches": True,
                "retrieved_message_meta_matches": True,
                "metadata_match_source": "response.data.metas",
                "session_id_recorded": False,
                "message_id_recorded": False,
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


def build_acontext_internal_irc_session_adapter_runner_fixture(
    *,
    artifact_dir: str | Path | None = None,
    adapter_contract: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic redacted local runner fixture artifact."""

    source = adapter_contract or load_acontext_internal_irc_session_adapter_contract(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may31_0405_internal_irc_session_adapter_runner_observation()
    _assert_adapter_contract_source(source)
    _assert_observation_safe_and_successful(observed)

    inherited_blocked = list(source["claim_boundaries"]["do_not_claim_yet"])
    lifted = [claim for claim in _LIFTED_SOURCE_BLOCKERS if claim in inherited_blocked]
    still_blocked = [claim for claim in inherited_blocked if claim not in lifted]
    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM,
            ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        still_blocked + ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_BLOCKED_CLAIMS
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCHEMA,
        "observation_id": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_ID,
        "scope": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCOPE,
        "source_artifacts": {
            "internal_irc_session_adapter_contract": {
                "file": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME],
            "uses_running_local_stack": True,
            "uses_root_prefixed_bearer_in_memory_only": True,
            "creates_project_or_scoped_secret": False,
            "persists_or_prints_secret": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_external_services": False,
            "mutates_irc_runtime_session_manager": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_VERDICT,
        "readiness": {
            "source_adapter_contract_defined": True,
            "local_runner_fixture_executed": True,
            "sanitized_session_create_status_201": True,
            "sanitized_message_store_status_201": True,
            "sanitized_message_retrieve_status_200": True,
            "retrieved_message_text_matched": True,
            "retrieved_message_meta_matched": True,
            "root_token_or_bearer_recorded": False,
            "session_or_message_id_recorded": False,
            "scoped_project_secret_created_or_acquired": False,
            "production_or_remote_acontext_proven": False,
            "irc_runtime_session_manager_ready": False,
            "cross_project_autorouting_ready": False,
            "customer_or_public_delivery_ready": False,
        },
        "runner_gates": [
            {
                "gate": "source_adapter_contract_ready",
                "passed": True,
                "evidence": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM,
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
                "evidence": "GET messages returned 200 and matched sanitized text plus metadata",
                "authorizes_customer_or_dispatch_claim": False,
            },
        ],
        "claim_boundaries": {
            "do_not_claim_yet": do_not_claim_yet,
            "safe_to_claim": safe_to_claim,
        },
        "claim_boundary_audit": {
            "inherited_do_not_claim_yet": inherited_blocked,
            "lifted_by_this_redacted_local_runner": lifted,
            "still_blocked_from_source": still_blocked,
            "new_do_not_claim_yet": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_BLOCKED_CLAIMS,
            "safe_claim_added": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "operator_guidance": {
            "safe_to_use_for": [
                "internal admin proof that the adapter runner can store/retrieve one sanitized IRC-shaped memory candidate locally",
                "next-step design for an opt-in runtime integration seam",
                "checking that root-prefixed auth, session IDs, and message IDs remain non-persisted",
            ],
            "not_safe_for": [
                "customer/public delivery",
                "IRC runtime session-manager mutation",
                "cross-project autorouting",
                "worker dispatch or queue launch",
                "ERC-8004 reputation or Worker Skill DNA claims",
                "payment or production readiness claims",
                "GPS/raw metadata exposure",
                "worker-copyable doctrine",
            ],
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "safe_next_step": (
                "Design a separate opt-in runtime adapter seam that can read sanitized memory candidates without mutating "
                "the live IRC session manager by default; keep customer/public/dispatch/reputation/payment claims blocked."
            ),
            "stop_line": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_STOP_LINE,
        },
    }
    _assert_artifact_safe(artifact)
    return artifact


def write_acontext_internal_irc_session_adapter_runner_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the deterministic redacted local runner fixture and return its path."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=target_dir)
    path = target_dir / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_internal_irc_session_adapter_runner_fixture(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the redacted local runner fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = target_dir / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    expected = build_acontext_internal_irc_session_adapter_runner_fixture(artifact_dir=target_dir)
    if artifact != expected:
        raise CityOpsContractError(
            f"{ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME} fixture drift"
        )
    return artifact


def _assert_adapter_contract_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCHEMA:
        raise CityOpsContractError("internal IRC adapter contract source schema mismatch")
    readiness = source.get("readiness", {})
    required = {
        "adapter_contract_defined": True,
        "local_runner_fixture_ready_to_execute_next": True,
        "live_runner_executed_in_this_artifact": False,
        "irc_runtime_session_manager_ready": False,
        "cross_project_autorouting_ready": False,
        "customer_or_public_delivery_ready": False,
    }
    for key, expected in required.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"adapter contract readiness mismatch: {key}")


def _assert_observation_safe_and_successful(observed: dict[str, Any]) -> None:
    probe = observed.get("local_runner_probe", {})
    if probe.get("used_root_prefixed_bearer_in_process_memory_only") is not True:
        raise CityOpsContractError("runner must use root-prefixed bearer only in memory")
    for key in ["root_token_value_printed", "derived_bearer_value_printed", "derived_bearer_value_persisted"]:
        if probe.get(key) is not False:
            raise CityOpsContractError(f"runner auth value exposure unsafe: {key}")
    if probe.get("create_session", {}).get("status_code") != 201:
        raise CityOpsContractError("runner create session did not return 201")
    if probe.get("store_message", {}).get("status_code") != 201:
        raise CityOpsContractError("runner store message did not return 201")
    retrieve = probe.get("retrieve_messages", {})
    required_retrieve = {
        "status_code": 200,
        "retrieved_message_count_at_least_one": True,
        "retrieved_message_text_matches": True,
        "retrieved_message_meta_matches": True,
        "session_id_recorded": False,
        "message_id_recorded": False,
    }
    for key, expected in required_retrieve.items():
        if retrieve.get(key) is not expected:
            raise CityOpsContractError(f"runner retrieve mismatch: {key}")

    metadata = observed.get("runner_input", {}).get("metadata", {})
    for key in [
        "contains_private_context",
        "contains_gps_or_raw_metadata",
        "customer_visible",
        "worker_visible",
    ]:
        if metadata.get(key) is not False:
            raise CityOpsContractError(f"runner metadata unsafe: {key}")

    sanitization = observed.get("sanitization_policy", {})
    for key, value in sanitization.items():
        if key.startswith("include_") and value is not False:
            raise CityOpsContractError(f"runner sanitization policy unsafe: {key}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _assert_artifact_safe(artifact: dict[str, Any]) -> None:
    for key, value in artifact.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"access flag must remain false: {key}")
    readiness = artifact.get("readiness", {})
    for key in [
        "root_token_or_bearer_recorded",
        "session_or_message_id_recorded",
        "production_or_remote_acontext_proven",
        "irc_runtime_session_manager_ready",
        "cross_project_autorouting_ready",
        "customer_or_public_delivery_ready",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"readiness flag must remain false: {key}")
    if readiness.get("local_runner_fixture_executed") is not True:
        raise CityOpsContractError("runner fixture execution must be recorded")
    serialized = json.dumps(artifact, sort_keys=True)
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        match = pattern.search(serialized)
        if match:
            raise CityOpsContractError(f"unsafe secret or identifier pattern persisted: {match.group(0)}")


def _stable_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
