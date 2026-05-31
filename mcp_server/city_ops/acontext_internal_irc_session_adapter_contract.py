"""Internal IRC-session-shaped Acontext adapter contract for AAS.

This City-as-a-Service/AAS artifact takes the bounded local Acontext
write/retrieve parity proof and freezes the next safe seam: an internal-only
adapter contract that can turn a redacted IRC-session-shaped packet into the
same local Acontext session/message/retrieval flow.

It deliberately does **not** mutate the IRC runtime session manager, register a
public/customer route, launch dispatch, emit reputation, verify payments, expose
GPS/raw metadata, or publish worker-copyable doctrine. It records only the
adapter shape and guardrails needed for the next local runner fixture.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_root_prefixed_local_write_retrieve_parity import (
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME,
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM,
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCHEMA,
    load_acontext_root_prefixed_local_write_retrieve_parity,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCHEMA = (
    "city_ops.acontext_internal_irc_session_adapter_contract.v1"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME = (
    "acontext_internal_irc_session_adapter_contract.json"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM = (
    "admin_acontext_internal_irc_session_adapter_contract_landed"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_ID = (
    "execution_market.aas.acontext_internal_irc_session_adapter_contract.2026_05_31_0320"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCOPE = (
    "internal_admin_irc_session_shaped_acontext_adapter_contract_no_runtime_mutation"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_VERDICT = (
    "internal_adapter_contract_ready_for_local_redacted_runner_but_not_irc_runtime_mutation"
)
ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_STOP_LINE = (
    "The internal IRC-session-shaped Acontext adapter contract defines a safe local runner shape only; "
    "it does not mutate IRC runtime session management, enable cross-project autorouting, authorize "
    "customer/public delivery, dispatch, reputation, payment/production claims, GPS/raw metadata exposure, "
    "private-context release, or worker-copyable doctrine."
)

ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_BLOCKED_CLAIMS = [
    "internal_irc_adapter_executed_live_runner_fixture",
    "internal_irc_adapter_mutates_irc_runtime_session_manager",
    "internal_irc_adapter_enables_cross_project_autorouting",
    "internal_irc_adapter_authorizes_customer_copy_delivery_or_publication",
    "internal_irc_adapter_authorizes_public_or_catalog_route",
    "internal_irc_adapter_authorizes_pricing_or_customer_quote",
    "internal_irc_adapter_authorizes_queue_launch_or_dispatch",
    "internal_irc_adapter_authorizes_reputation_or_worker_skill_dna",
    "internal_irc_adapter_reverifies_payment_or_production",
    "internal_irc_adapter_allows_exact_gps_or_raw_metadata",
    "internal_irc_adapter_releases_private_operator_context",
    "internal_irc_adapter_grants_domain_or_emergency_authority",
    "internal_irc_adapter_creates_worker_copyable_doctrine",
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
    re.compile(r"bearer\s+sk-ac-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
]


def build_may31_0320_internal_irc_session_adapter_contract_observation() -> dict[str, Any]:
    """Return the deterministic adapter contract for the next safe local runner."""

    return {
        "observation_window": "2026-05-31T03:20:00Z/2026-05-31T03:26:00Z",
        "host_scope": "local_contract_artifact_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "source_parity_required": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME,
        "adapter_contract": {
            "contract_name": "internal_irc_session_to_acontext_local_adapter",
            "mode": "redacted_local_runner_shape_only",
            "auth_strategy": {
                "header_shape": "Authorization: Bearer ***${ROOT_API_BEARER_TOKEN}",
                "root_prefixed_bearer_used_in_process_memory_only": True,
                "may_persist_or_print_root_token": False,
                "may_persist_or_print_derived_bearer": False,
            },
            "input_packet_shape": {
                "packet_kind": "irc_session_memory_candidate",
                "session_handle": "redacted_irc_session_handle",
                "source_channel": "redacted_internal_coordination_channel",
                "source_message_id": "redacted_message_id",
                "actor": "execution-market-aas-internal-runner",
                "message_text": "Execution Market AAS IRC-shaped adapter smoke: sanitized message, no private context.",
                "metadata": {
                    "project": "execution-market-aas",
                    "surface": "internal_admin_only",
                    "contains_private_context": False,
                    "contains_gps_or_raw_metadata": False,
                    "customer_visible": False,
                    "worker_visible": False,
                },
            },
            "endpoint_mapping": [
                {
                    "step": "create_or_reuse_local_acontext_session",
                    "method": "POST",
                    "path": "/api/v1/session",
                    "records_session_id_in_artifact": False,
                    "required_body_fields": ["user", "disable_task_tracking"],
                    "required_body_values": {"disable_task_tracking": True},
                },
                {
                    "step": "store_redacted_irc_session_message",
                    "method": "POST",
                    "path": "/api/v1/session/{redacted_session_id}/messages",
                    "records_message_id_in_artifact": False,
                    "required_body_fields": ["content", "metadata"],
                },
                {
                    "step": "retrieve_redacted_irc_session_message",
                    "method": "GET",
                    "path": "/api/v1/session/{redacted_session_id}/messages?limit=5&format=acontext&with_events=true",
                    "records_message_id_in_artifact": False,
                    "success_condition": "retrieved sanitized text and metadata match the local runner fixture",
                },
            ],
        },
        "runner_policy": {
            "runner_executed_in_this_artifact": False,
            "requires_local_acontext_stack": True,
            "requires_external_network": False,
            "allowed_to_write_only_sanitized_fixture": True,
            "allowed_to_read_private_operator_context": False,
            "allowed_to_touch_customer_routes": False,
            "allowed_to_touch_worker_dispatch": False,
            "allowed_to_mutate_irc_runtime_session_manager": False,
            "allowed_to_emit_reputation": False,
            "allowed_to_reverify_payment_or_production": False,
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


def build_acontext_internal_irc_session_adapter_contract(
    *,
    artifact_dir: str | Path | None = None,
    root_prefixed_parity: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal IRC-session-shaped adapter contract."""

    source = root_prefixed_parity or load_acontext_root_prefixed_local_write_retrieve_parity(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may31_0320_internal_irc_session_adapter_contract_observation()
    _assert_root_prefixed_parity_source(source)
    _assert_observation_safe_contract(observed)

    inherited_blocked = list(source["claim_boundaries"]["do_not_claim_yet"])
    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM,
            ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        inherited_blocked + ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_BLOCKED_CLAIMS
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCHEMA,
        "observation_id": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_ID,
        "scope": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SCOPE,
        "source_artifacts": {
            "root_prefixed_local_parity": {
                "file": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME],
            "uses_running_local_stack": False,
            "requires_running_local_stack_for_next_runner": True,
            "uses_root_prefixed_bearer_in_memory_only": True,
            "creates_project_or_scoped_secret": False,
            "persists_or_prints_secret": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_external_services": False,
            "mutates_irc_runtime_session_manager": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_VERDICT,
        "readiness": {
            "source_local_write_retrieve_parity_proven": True,
            "adapter_contract_defined": True,
            "redacted_irc_session_packet_shape_defined": True,
            "endpoint_mapping_defined": True,
            "local_runner_fixture_ready_to_execute_next": True,
            "live_runner_executed_in_this_artifact": False,
            "scoped_project_secret_created_or_acquired": False,
            "production_or_remote_acontext_proven": False,
            "irc_runtime_session_manager_ready": False,
            "cross_project_autorouting_ready": False,
            "customer_or_public_delivery_ready": False,
        },
        "contract_gates": [
            {
                "gate": "source_local_parity_available",
                "passed": True,
                "evidence": ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM,
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "redacted_input_packet_shape_defined",
                "passed": True,
                "evidence": "input packet uses redacted session/channel/message identifiers and sanitized text",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "endpoint_mapping_matches_local_parity_paths",
                "passed": True,
                "evidence": "adapter maps to POST /api/v1/session, POST messages, and GET messages retrieval",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "runner_policy_blocks_runtime_mutation",
                "passed": True,
                "evidence": "runner_policy.allowed_to_mutate_irc_runtime_session_manager=false",
                "authorizes_customer_or_dispatch_claim": False,
            },
        ],
        "claim_boundaries": {
            "do_not_claim_yet": do_not_claim_yet,
            "safe_to_claim": safe_to_claim,
        },
        "claim_boundary_audit": {
            "inherited_do_not_claim_yet": inherited_blocked,
            "new_do_not_claim_yet": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_BLOCKED_CLAIMS,
            "safe_claim_added": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_SAFE_CLAIM,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "operator_guidance": {
            "safe_to_use_for": [
                "internal admin review of the Acontext adapter shape",
                "preparing the next local redacted runner fixture",
                "checking that IRC-shaped memory candidates remain sanitized before local Acontext writes",
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
                "Execute one local redacted runner fixture against Acontext using this contract, keep bearer/session/message IDs "
                "in memory only, and record only status codes plus sanitized text/meta match booleans."
            ),
            "stop_line": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_STOP_LINE,
        },
    }
    _assert_artifact_safe(artifact)
    return artifact


def write_acontext_internal_irc_session_adapter_contract(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the deterministic adapter contract fixture and return its path."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_acontext_internal_irc_session_adapter_contract(artifact_dir=target_dir)
    path = target_dir / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_internal_irc_session_adapter_contract(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the adapter contract fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = target_dir / ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    expected = build_acontext_internal_irc_session_adapter_contract(artifact_dir=target_dir)
    if artifact != expected:
        raise CityOpsContractError(
            f"{ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_CONTRACT_FILENAME} fixture drift"
        )
    return artifact


def _assert_root_prefixed_parity_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCHEMA:
        raise CityOpsContractError("root-prefixed local parity source schema mismatch")
    readiness = source.get("readiness", {})
    required = {
        "root_prefixed_bearer_supported_for_local_api": True,
        "local_write_retrieve_parity_proven": True,
        "customer_or_public_delivery_ready": False,
        "irc_runtime_session_manager_ready": False,
        "cross_project_autorouting_ready": False,
    }
    for key, expected in required.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"root-prefixed parity readiness mismatch: {key}")


def _assert_observation_safe_contract(observed: dict[str, Any]) -> None:
    auth_strategy = observed.get("adapter_contract", {}).get("auth_strategy", {})
    if auth_strategy.get("header_shape") != "Authorization: Bearer ***${ROOT_API_BEARER_TOKEN}":
        raise CityOpsContractError("adapter auth header must remain redacted")
    for key in ["may_persist_or_print_root_token", "may_persist_or_print_derived_bearer"]:
        if auth_strategy.get(key) is not False:
            raise CityOpsContractError(f"adapter auth strategy unsafe: {key}")

    packet = observed.get("adapter_contract", {}).get("input_packet_shape", {})
    metadata = packet.get("metadata", {})
    for key in [
        "contains_private_context",
        "contains_gps_or_raw_metadata",
        "customer_visible",
        "worker_visible",
    ]:
        if metadata.get(key) is not False:
            raise CityOpsContractError(f"adapter input packet metadata unsafe: {key}")

    runner_policy = observed.get("runner_policy", {})
    must_be_false = [
        "runner_executed_in_this_artifact",
        "requires_external_network",
        "allowed_to_read_private_operator_context",
        "allowed_to_touch_customer_routes",
        "allowed_to_touch_worker_dispatch",
        "allowed_to_mutate_irc_runtime_session_manager",
        "allowed_to_emit_reputation",
        "allowed_to_reverify_payment_or_production",
    ]
    for key in must_be_false:
        if runner_policy.get(key) is not False:
            raise CityOpsContractError(f"adapter runner policy unsafe: {key}")

    if runner_policy.get("allowed_to_write_only_sanitized_fixture") is not True:
        raise CityOpsContractError("adapter runner must only allow sanitized fixture writes")

    sanitization = observed.get("sanitization_policy", {})
    for key, value in sanitization.items():
        if key.startswith("include_") and value is not False:
            raise CityOpsContractError(f"adapter sanitization policy unsafe: {key}")


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
        "live_runner_executed_in_this_artifact",
        "production_or_remote_acontext_proven",
        "irc_runtime_session_manager_ready",
        "cross_project_autorouting_ready",
        "customer_or_public_delivery_ready",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"readiness flag must remain false: {key}")
    serialized = json.dumps(artifact, sort_keys=True)
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        match = pattern.search(serialized)
        if match:
            raise CityOpsContractError(f"unsafe secret or identifier pattern persisted: {match.group(0)}")


def _stable_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
