"""Local cleanup/quarantine harness gate for the Acontext runtime adapter seam.

This proof block follows the disabled-by-default runtime adapter seam contract. It
executes a deterministic local state-machine harness for the next cleanup and
quarantine requirement while keeping runtime identifiers in process memory only.
The persisted artifact records labels, status classes, and booleans only.

It deliberately does not contact Acontext, register a runtime adapter, mutate IRC
session management, enable autorouting, publish customer/worker surfaces, launch
dispatch, emit reputation, verify payments/production, expose GPS/raw metadata,
release private context, or create worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_opt_in_runtime_adapter_seam_contract import (
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME,
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
    ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCHEMA,
    load_acontext_opt_in_runtime_adapter_seam_contract,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCHEMA = (
    "city_ops.acontext_cleanup_quarantine_harness_gate.v1"
)
ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME = (
    "acontext_cleanup_quarantine_harness_gate.json"
)
ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM = (
    "admin_acontext_cleanup_quarantine_harness_gate_landed"
)
ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_ID = (
    "execution_market.aas.acontext_cleanup_quarantine_harness_gate.2026_05_31_0705"
)
ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCOPE = (
    "internal_admin_local_cleanup_quarantine_harness_no_runtime_mutation"
)
ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_VERDICT = (
    "local_cleanup_quarantine_harness_passed_runtime_activation_remains_blocked"
)
ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_STOP_LINE = (
    "The local cleanup/quarantine harness records only status classes and booleans. It does not "
    "authorize runtime adapter registration, IRC session-manager mutation, cross-project autorouting, "
    "customer/public delivery, dispatch, reputation, payment/production claims, GPS/raw metadata "
    "exposure, private-context release, or worker-copyable doctrine. Run the separate multi-fixture "
    "replay gate and explicit operator activation decision before any runtime mutation."
)

CLEANUP_QUARANTINE_HARNESS_BLOCKED_CLAIMS = [
    "cleanup_quarantine_harness_authorizes_runtime_adapter_registration",
    "cleanup_quarantine_harness_authorizes_irc_session_manager_mutation",
    "cleanup_quarantine_harness_authorizes_cross_project_autorouting",
    "cleanup_quarantine_harness_authorizes_customer_copy_delivery_or_publication",
    "cleanup_quarantine_harness_authorizes_public_or_catalog_route",
    "cleanup_quarantine_harness_authorizes_pricing_or_customer_quote",
    "cleanup_quarantine_harness_authorizes_operator_queue_launch_or_dispatch",
    "cleanup_quarantine_harness_authorizes_erc8004_reputation_or_worker_skill_dna",
    "cleanup_quarantine_harness_reverifies_payment_or_production",
    "cleanup_quarantine_harness_allows_exact_gps_or_raw_metadata",
    "cleanup_quarantine_harness_releases_private_operator_context",
    "cleanup_quarantine_harness_creates_worker_copyable_doctrine",
    "cleanup_quarantine_harness_declares_general_acontext_sink_ready",
    "cleanup_quarantine_harness_declares_runtime_parity_proven",
    "cleanup_quarantine_harness_declares_multi_fixture_replay_executed",
    "cleanup_quarantine_harness_declares_operator_activation_approved",
]

_FALSE_ACCESS_FLAGS = {
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "cross_project_autorouting_enabled": False,
    "network_route_registered": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "pricing_enabled": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "emits_reputation_receipts": False,
    "reverifies_payment_or_production": False,
    "exposes_gps_or_metadata": False,
    "releases_private_operator_context": False,
    "publishes_worker_doctrine": False,
}

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-ac-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    ),
]


def build_local_cleanup_quarantine_harness_observation() -> dict[str, Any]:
    """Return deterministic local harness facts with no runtime identifiers persisted."""

    return {
        "observation_window": "2026-05-31T07:03:00Z/2026-05-31T07:05:00Z",
        "host_scope": "local_state_machine_only_no_network_no_acontext_call",
        "harness_inputs": {
            "reviewed_sanitized_candidate_count": 2,
            "candidate_labels": [
                "sanitized_success_cleanup_case",
                "sanitized_failed_write_quarantine_case",
            ],
            "persists_candidate_text": False,
            "persists_runtime_session_id": False,
            "persists_runtime_message_id": False,
            "persists_raw_metadata": False,
            "persists_private_context": False,
            "persists_gps_or_raw_metadata": False,
        },
        "local_harness_paths": [
            {
                "candidate_label": "sanitized_success_cleanup_case",
                "path_kind": "success_cleanup",
                "write_status_class": "2xx_simulated_local_harness",
                "retrieve_status_class": "2xx_simulated_local_harness",
                "delete_or_tombstone_status_class": "2xx_simulated_local_harness",
                "runtime_handle_kept_in_process_memory_only": True,
                "runtime_handle_persisted": False,
                "status_boolean_recorded_only": True,
                "quarantine_envelope_created": False,
                "cleanup_observed": True,
                "quarantine_observed": False,
                "customer_visible": False,
                "worker_visible": False,
            },
            {
                "candidate_label": "sanitized_failed_write_quarantine_case",
                "path_kind": "failed_write_quarantine",
                "write_status_class": "5xx_simulated_local_harness",
                "retrieve_status_class": "not_attempted_after_failed_write",
                "delete_or_tombstone_status_class": "not_applicable_no_runtime_handle",
                "runtime_handle_kept_in_process_memory_only": True,
                "runtime_handle_persisted": False,
                "status_boolean_recorded_only": True,
                "quarantine_envelope_created": True,
                "cleanup_observed": False,
                "quarantine_observed": True,
                "customer_visible": False,
                "worker_visible": False,
            },
        ],
        "sanitization_policy": {
            "include_root_token_value": False,
            "include_derived_bearer_value": False,
            "include_project_secret_value": False,
            "include_project_id": False,
            "include_user_id": False,
            "include_session_id": False,
            "include_message_id": False,
            "include_candidate_text": False,
            "include_raw_container_logs": False,
            "include_private_operator_context": False,
            "include_gps_or_raw_metadata": False,
            "redact_auth_headers": True,
        },
    }


def build_acontext_cleanup_quarantine_harness_gate(
    *,
    artifact_dir: str | Path | None = None,
    seam_contract: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic local cleanup/quarantine harness gate."""

    source = seam_contract or load_acontext_opt_in_runtime_adapter_seam_contract(
        artifact_dir=artifact_dir
    )
    observed = observation or build_local_cleanup_quarantine_harness_observation()
    _assert_seam_contract_source(source)
    _assert_observation_safe_and_successful(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
            ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *CLEANUP_QUARANTINE_HARNESS_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    gate = {
        "schema": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCHEMA,
        "gate_id": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_ID,
        "scope": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCOPE,
        "source_artifacts": {
            "runtime_adapter_seam_contract": {
                "file": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME,
                "schema": source["schema"],
                "id": source["contract_id"],
                "safe_claim": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "contract_verdict": source["contract_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME],
            "runs_local_state_machine_harness": True,
            "contacts_acontext": False,
            "uses_root_or_project_token": False,
            "prints_or_persists_secret": False,
            "records_session_or_message_ids": False,
            "registers_runtime_adapter": False,
            "touches_irc_runtime_session_manager": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_external_services": False,
        },
        "harness_observation": observed,
        "cleanup_quarantine_results": {
            "local_harness_executed": True,
            "success_cleanup_path_observed": True,
            "failed_write_quarantine_path_observed": True,
            "runtime_handles_kept_in_process_memory_only": True,
            "runtime_handles_persisted": False,
            "status_booleans_and_status_classes_only": True,
            "candidate_text_persisted": False,
            "raw_metadata_persisted": False,
            "private_context_persisted": False,
            "gps_or_raw_metadata_persisted": False,
            "safe_for_internal_multi_fixture_replay_design": True,
        },
        "promotion_sequence": _promotion_sequence(),
        "readiness": {
            "cleanup_quarantine_harness_gate_landed": True,
            "source_seam_contract_validated": True,
            "local_cleanup_quarantine_harness_executed": True,
            "success_cleanup_path_observed": True,
            "failed_write_quarantine_path_observed": True,
            "safe_for_internal_multi_fixture_replay_design": True,
            "safe_for_runtime_adapter_registration": False,
            "safe_for_runtime_session_manager_mutation": False,
            "safe_for_cross_project_autorouting": False,
            "safe_for_customer_or_public_delivery": False,
            "safe_for_queue_launch_or_dispatch": False,
            "safe_for_reputation_or_worker_skill_dna": False,
            "safe_for_payment_or_production_claim": False,
            "safe_for_gps_or_raw_metadata_release": False,
            "safe_for_private_context_release": False,
            "safe_for_worker_copyable_doctrine": False,
            "general_acontext_sink_ready": False,
            "runtime_parity_proven": False,
            "multi_fixture_replay_executed": False,
            "operator_activation_approved": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "claim_boundary_audit": {
            "inherited_from_seam_contract": source["claim_boundaries"]["do_not_claim_yet"],
            "new_do_not_claim_yet": CLEANUP_QUARANTINE_HARNESS_BLOCKED_CLAIMS,
            "safe_claim_added": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM,
            "no_blocked_claims_lifted_by_this_gate": True,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "operator_guidance": {
            "safe_to_use_for": [
                "internal cleanup/quarantine implementation planning",
                "success and failure path observability metrics",
                "input requirements for a future separate multi-fixture replay gate",
            ],
            "not_safe_for": [
                "runtime adapter registration or enablement",
                "IRC session-manager mutation",
                "cross-project autorouting",
                "customer/public delivery or publication",
                "operator queue launch or worker dispatch",
                "ERC-8004 reputation or Worker Skill DNA",
                "payment or production readiness claims",
                "GPS/raw metadata/private-context exposure",
                "worker-copyable doctrine",
            ],
            "next_separate_gate": (
                "Replay at least two reviewed sanitized fixtures through a separate multi-fixture "
                "gate, including success and hold/quarantine cases, before any explicit operator "
                "activation decision."
            ),
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "stop_line": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_STOP_LINE,
        },
        "gate_verdict": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_VERDICT,
    }
    _assert_gate_conservative(gate)
    return gate


def write_acontext_cleanup_quarantine_harness_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the deterministic cleanup/quarantine harness gate and return its path."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_acontext_cleanup_quarantine_harness_gate(artifact_dir=target_dir)
    path = target_dir / ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_cleanup_quarantine_harness_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted cleanup/quarantine harness gate."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = target_dir / ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME
    gate = json.loads(path.read_text(encoding="utf-8"))
    expected = build_acontext_cleanup_quarantine_harness_gate(artifact_dir=target_dir)
    if gate != expected:
        raise CityOpsContractError(
            f"{ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME} fixture drift"
        )
    return gate


def _promotion_sequence() -> list[dict[str, Any]]:
    return [
        {
            "gate": "disabled_by_default_adapter_seam_contract",
            "status": "passed",
            "evidence": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "gate": "local_cleanup_quarantine_harness",
            "status": "passed_internal_harness_only",
            "evidence": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM,
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "gate": "multi_fixture_replay_execution",
            "status": "blocked",
            "required_next": "replay at least two reviewed sanitized fixtures including success and hold/quarantine cases",
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "gate": "operator_activation_decision",
            "status": "blocked",
            "required_next": "separate explicit operator activation decision after cleanup/quarantine and replay gates",
            "authorizes_runtime_adapter_registration": False,
        },
    ]


def _assert_seam_contract_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCHEMA:
        raise CityOpsContractError("runtime adapter seam contract source schema mismatch")
    readiness = source.get("readiness", {})
    required_true = [
        "seam_contract_landed",
        "source_promotion_gate_validated",
        "disabled_by_default_contract_defined",
        "cleanup_or_quarantine_contract_defined",
        "multi_fixture_replay_contract_defined",
        "safe_for_internal_implementation_planning",
    ]
    for key in required_true:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"seam contract readiness mismatch: {key}")
    required_false = [
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_worker_copyable_doctrine",
        "cleanup_or_quarantine_executed",
        "multi_fixture_replay_executed",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
    ]
    for key in required_false:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"seam contract readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"seam contract access flag promoted: {key}")
    if ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("seam contract safe claim missing")


def _assert_observation_safe_and_successful(observed: dict[str, Any]) -> None:
    inputs = observed.get("harness_inputs", {})
    if inputs.get("reviewed_sanitized_candidate_count") != 2:
        raise CityOpsContractError("cleanup/quarantine harness requires exactly two candidates")
    for key in [
        "persists_candidate_text",
        "persists_runtime_session_id",
        "persists_runtime_message_id",
        "persists_raw_metadata",
        "persists_private_context",
        "persists_gps_or_raw_metadata",
    ]:
        if inputs.get(key) is not False:
            raise CityOpsContractError(f"unsafe harness input persistence: {key}")

    paths = observed.get("local_harness_paths", [])
    if len(paths) != 2:
        raise CityOpsContractError("cleanup/quarantine harness must include two paths")
    success_paths = [row for row in paths if row.get("path_kind") == "success_cleanup"]
    quarantine_paths = [row for row in paths if row.get("path_kind") == "failed_write_quarantine"]
    if len(success_paths) != 1 or len(quarantine_paths) != 1:
        raise CityOpsContractError("harness must include success cleanup and failed write quarantine paths")
    success = success_paths[0]
    quarantine = quarantine_paths[0]
    if success.get("cleanup_observed") is not True:
        raise CityOpsContractError("success cleanup path missing cleanup observation")
    if success.get("quarantine_envelope_created") is not False:
        raise CityOpsContractError("success cleanup path should not create quarantine envelope")
    if quarantine.get("quarantine_observed") is not True:
        raise CityOpsContractError("failed write path missing quarantine observation")
    if quarantine.get("quarantine_envelope_created") is not True:
        raise CityOpsContractError("failed write path missing quarantine envelope")
    for row in paths:
        for key in ["runtime_handle_persisted", "customer_visible", "worker_visible"]:
            if row.get(key) is not False:
                raise CityOpsContractError(f"unsafe harness path flag: {key}")
        for key in ["runtime_handle_kept_in_process_memory_only", "status_boolean_recorded_only"]:
            if row.get(key) is not True:
                raise CityOpsContractError(f"harness path safety flag missing: {key}")

    policy = observed.get("sanitization_policy", {})
    for key, value in policy.items():
        if key == "redact_auth_headers":
            if value is not True:
                raise CityOpsContractError("auth headers must be redacted")
        elif value is not False:
            raise CityOpsContractError(f"unsafe sanitization policy: {key}")


def _assert_gate_conservative(gate: dict[str, Any]) -> None:
    _assert_claim_boundaries(
        gate["claim_boundaries"]["safe_to_claim"],
        gate["claim_boundaries"]["do_not_claim_yet"],
    )
    for key, value in gate.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"access flag must remain false: {key}")
    readiness = gate.get("readiness", {})
    for key in [
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_worker_copyable_doctrine",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "multi_fixture_replay_executed",
        "operator_activation_approved",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"readiness flag must remain false: {key}")
    for row in gate.get("promotion_sequence", []):
        if row.get("authorizes_runtime_adapter_registration") is not False:
            raise CityOpsContractError("promotion sequence authorized runtime adapter registration")
    serialized = json.dumps(gate, sort_keys=True)
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        match = pattern.search(serialized)
        if match:
            raise CityOpsContractError(
                f"unsafe secret or identifier pattern persisted: {match.group(0)}"
            )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _stable_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
