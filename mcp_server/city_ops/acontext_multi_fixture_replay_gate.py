"""Internal/admin multi-fixture replay gate for the disabled Acontext adapter seam.

This proof block is the next step after the local cleanup/quarantine harness. It
replays reviewed, sanitized fixture outcomes through a deterministic local gate so
operators can see success and hold/quarantine behavior side by side before any
runtime mutation is considered.

It deliberately does not contact Acontext, register a runtime adapter, mutate IRC
session management, enable cross-project autorouting, publish customer/worker
surfaces, launch dispatch, emit reputation, verify payments/production, expose
GPS/raw metadata, release private context, or create worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_cleanup_quarantine_harness_gate import (
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME,
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM,
    ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCHEMA,
    CLEANUP_QUARANTINE_HARNESS_BLOCKED_CLAIMS,
    load_acontext_cleanup_quarantine_harness_gate,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCHEMA = "city_ops.acontext_multi_fixture_replay_gate.v1"
ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME = "acontext_multi_fixture_replay_gate.json"
ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM = (
    "admin_acontext_multi_fixture_replay_gate_landed"
)
ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_ID = (
    "execution_market.aas.acontext_multi_fixture_replay_gate.2026_05_31_0805"
)
ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCOPE = (
    "internal_admin_reviewed_sanitized_multi_fixture_replay_no_runtime_mutation"
)
ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_VERDICT = (
    "multi_fixture_replay_gate_passed_runtime_activation_remains_blocked"
)
ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_STOP_LINE = (
    "The multi-fixture replay gate proves only deterministic local replay over reviewed sanitized "
    "fixtures. It does not authorize runtime adapter registration, IRC session-manager mutation, "
    "cross-project autorouting, customer/public delivery, dispatch, reputation, payment/production "
    "claims, GPS/raw metadata exposure, private-context release, or worker-copyable doctrine. Require "
    "a separate explicit operator activation decision before any runtime mutation."
)

MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS = [
    *CLEANUP_QUARANTINE_HARNESS_BLOCKED_CLAIMS,
    "multi_fixture_replay_authorizes_runtime_adapter_registration",
    "multi_fixture_replay_authorizes_irc_session_manager_mutation",
    "multi_fixture_replay_authorizes_cross_project_autorouting",
    "multi_fixture_replay_authorizes_customer_copy_delivery_or_publication",
    "multi_fixture_replay_authorizes_public_or_catalog_route",
    "multi_fixture_replay_authorizes_pricing_or_customer_quote",
    "multi_fixture_replay_authorizes_operator_queue_launch_or_dispatch",
    "multi_fixture_replay_authorizes_erc8004_reputation_or_worker_skill_dna",
    "multi_fixture_replay_reverifies_payment_or_production",
    "multi_fixture_replay_allows_exact_gps_or_raw_metadata",
    "multi_fixture_replay_releases_private_operator_context",
    "multi_fixture_replay_creates_worker_copyable_doctrine",
    "multi_fixture_replay_declares_general_acontext_sink_ready",
    "multi_fixture_replay_declares_runtime_parity_proven",
    "multi_fixture_replay_declares_operator_activation_approved",
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


def build_reviewed_sanitized_multi_fixture_replay_observation() -> dict[str, Any]:
    """Return deterministic replay facts with no runtime identifiers persisted."""

    return {
        "observation_window": "2026-05-31T08:03:00Z/2026-05-31T08:05:00Z",
        "host_scope": "local_replay_only_no_network_no_acontext_call",
        "fixture_set": {
            "reviewed_sanitized_fixture_count": 3,
            "minimum_required_reviewed_sanitized_fixture_count": 2,
            "includes_success_case": True,
            "includes_hold_or_quarantine_case": True,
            "persists_fixture_payload_text": False,
            "persists_runtime_session_id": False,
            "persists_runtime_message_id": False,
            "persists_raw_metadata": False,
            "persists_private_context": False,
            "persists_gps_or_raw_metadata": False,
        },
        "replay_cases": [
            {
                "fixture_label": "reviewed_sanitized_success_retrieve_case",
                "fixture_family": "runtime_memory_retrieve",
                "expected_outcome": "success_cleanup",
                "observed_outcome": "success_cleanup",
                "status_class_sequence": [
                    "2xx_simulated_local_replay_write",
                    "2xx_simulated_local_replay_retrieve",
                    "2xx_simulated_local_replay_delete_or_tombstone",
                ],
                "operator_result_class": "allow_internal_next_gate_design_only",
                "quarantine_envelope_created": False,
                "hold_record_created": False,
                "cleanup_observed": True,
                "runtime_handle_kept_in_process_memory_only": True,
                "runtime_handle_persisted": False,
                "fixture_payload_persisted": False,
                "customer_visible": False,
                "worker_visible": False,
            },
            {
                "fixture_label": "reviewed_sanitized_failed_write_quarantine_case",
                "fixture_family": "runtime_memory_write",
                "expected_outcome": "quarantine",
                "observed_outcome": "quarantine",
                "status_class_sequence": [
                    "5xx_simulated_local_replay_write",
                    "retrieve_not_attempted_after_failed_write",
                    "delete_not_applicable_no_runtime_handle",
                ],
                "operator_result_class": "hold_for_operator_review",
                "quarantine_envelope_created": True,
                "hold_record_created": True,
                "cleanup_observed": False,
                "runtime_handle_kept_in_process_memory_only": True,
                "runtime_handle_persisted": False,
                "fixture_payload_persisted": False,
                "customer_visible": False,
                "worker_visible": False,
            },
            {
                "fixture_label": "reviewed_sanitized_schema_mismatch_hold_case",
                "fixture_family": "runtime_memory_retrieve",
                "expected_outcome": "hold",
                "observed_outcome": "hold",
                "status_class_sequence": [
                    "2xx_simulated_local_replay_write",
                    "4xx_simulated_local_replay_schema_mismatch",
                    "2xx_simulated_local_replay_delete_or_tombstone",
                ],
                "operator_result_class": "hold_for_schema_review",
                "quarantine_envelope_created": True,
                "hold_record_created": True,
                "cleanup_observed": True,
                "runtime_handle_kept_in_process_memory_only": True,
                "runtime_handle_persisted": False,
                "fixture_payload_persisted": False,
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
            "include_fixture_payload_text": False,
            "include_raw_container_logs": False,
            "include_private_operator_context": False,
            "include_gps_or_raw_metadata": False,
            "redact_auth_headers": True,
        },
    }


def build_acontext_multi_fixture_replay_gate(
    *,
    artifact_dir: str | Path | None = None,
    cleanup_gate: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin multi-fixture replay gate."""

    source = cleanup_gate or load_acontext_cleanup_quarantine_harness_gate(
        artifact_dir=artifact_dir
    )
    observed = observation or build_reviewed_sanitized_multi_fixture_replay_observation()
    _assert_cleanup_gate_source(source)
    _assert_observation_safe_and_complete(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM,
            ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    gate = {
        "schema": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCHEMA,
        "gate_id": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_ID,
        "scope": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCOPE,
        "source_artifacts": {
            "cleanup_quarantine_harness_gate": {
                "file": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME,
                "schema": source["schema"],
                "id": source["gate_id"],
                "safe_claim": ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "gate_verdict": source["gate_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_FILENAME],
            "runs_local_multi_fixture_replay": True,
            "contacts_acontext": False,
            "uses_root_or_project_token": False,
            "prints_or_persists_secret": False,
            "records_session_or_message_ids": False,
            "persists_fixture_payload_text": False,
            "registers_runtime_adapter": False,
            "touches_irc_runtime_session_manager": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_external_services": False,
        },
        "multi_fixture_replay_observation": observed,
        "replay_results": _replay_results(observed),
        "promotion_sequence": _promotion_sequence(),
        "readiness": {
            "multi_fixture_replay_gate_landed": True,
            "source_cleanup_quarantine_gate_validated": True,
            "local_multi_fixture_replay_executed": True,
            "reviewed_sanitized_fixture_count": observed["fixture_set"][
                "reviewed_sanitized_fixture_count"
            ],
            "success_case_replayed": True,
            "hold_or_quarantine_case_replayed": True,
            "safe_for_operator_activation_review_design": True,
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
            "operator_activation_approved": False,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_guidance": {
            "stop_line": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "explicit_operator_activation_decision_before_runtime_mutation",
            "allowed_next_work": [
                "draft_internal_operator_activation_review_request",
                "rerun_runtime_prerequisite_preflight_if_services_change",
                "keep customer dispatch reputation payment GPS private-context and worker-doctrine claims blocked",
            ],
        },
        "gate_verdict": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_VERDICT,
    }
    _assert_gate_conservative(gate, source)
    return gate


def write_acontext_multi_fixture_replay_gate(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic multi-fixture replay gate."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    gate = build_acontext_multi_fixture_replay_gate(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_multi_fixture_replay_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted multi-fixture replay gate."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME
    gate = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_cleanup_quarantine_harness_gate(artifact_dir=base_dir)
    _assert_gate_conservative(gate, source)
    if gate != build_acontext_multi_fixture_replay_gate(
        artifact_dir=base_dir,
        cleanup_gate=source,
        observation=gate["multi_fixture_replay_observation"],
    ):
        raise CityOpsContractError("Acontext multi-fixture replay gate fixture drift")
    return gate


def _replay_results(observation: dict[str, Any]) -> dict[str, Any]:
    cases = observation["replay_cases"]
    return {
        "local_multi_fixture_replay_executed": True,
        "reviewed_sanitized_fixture_count": observation["fixture_set"][
            "reviewed_sanitized_fixture_count"
        ],
        "success_case_count": sum(1 for case in cases if case["observed_outcome"] == "success_cleanup"),
        "hold_case_count": sum(1 for case in cases if case["observed_outcome"] == "hold"),
        "quarantine_case_count": sum(1 for case in cases if case["observed_outcome"] == "quarantine"),
        "all_expected_outcomes_matched": all(
            case["expected_outcome"] == case["observed_outcome"] for case in cases
        ),
        "runtime_handles_kept_in_process_memory_only": all(
            case["runtime_handle_kept_in_process_memory_only"] for case in cases
        ),
        "runtime_handles_persisted": any(case["runtime_handle_persisted"] for case in cases),
        "fixture_payloads_persisted": any(case["fixture_payload_persisted"] for case in cases),
        "customer_visible": any(case["customer_visible"] for case in cases),
        "worker_visible": any(case["worker_visible"] for case in cases),
        "safe_for_operator_activation_review_design": True,
    }


def _promotion_sequence() -> list[dict[str, Any]]:
    return [
        {
            "step": "local_cleanup_quarantine_harness",
            "status": "complete",
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "step": "multi_fixture_replay_gate",
            "status": "complete_internal_admin_only",
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "step": "explicit_operator_activation_decision",
            "status": "required_next_before_any_runtime_mutation",
            "authorizes_runtime_adapter_registration": "only_if_separately_approved_later",
        },
    ]


def _assert_cleanup_gate_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_CLEANUP_QUARANTINE_HARNESS_GATE_SCHEMA:
        raise CityOpsContractError("unexpected cleanup/quarantine harness gate schema")
    if source.get("readiness", {}).get("multi_fixture_replay_executed") is True:
        raise CityOpsContractError("source cleanup gate already claimed replay execution")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source cleanup access flag promoted: {key}")
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
        "operator_activation_approved",
    ]:
        if source.get("readiness", {}).get(key) is not False:
            raise CityOpsContractError(f"source cleanup readiness promoted: {key}")


def _assert_observation_safe_and_complete(observation: dict[str, Any]) -> None:
    fixture_set = observation.get("fixture_set", {})
    if fixture_set.get("reviewed_sanitized_fixture_count", 0) < 2:
        raise CityOpsContractError("multi-fixture replay requires at least two reviewed sanitized fixtures")
    if fixture_set.get("includes_success_case") is not True:
        raise CityOpsContractError("multi-fixture replay missing success case")
    if fixture_set.get("includes_hold_or_quarantine_case") is not True:
        raise CityOpsContractError("multi-fixture replay missing hold or quarantine case")
    for key in [
        "persists_fixture_payload_text",
        "persists_runtime_session_id",
        "persists_runtime_message_id",
        "persists_raw_metadata",
        "persists_private_context",
        "persists_gps_or_raw_metadata",
    ]:
        if fixture_set.get(key) is not False:
            raise CityOpsContractError(f"unsafe replay fixture persistence: {key}")

    cases = observation.get("replay_cases", [])
    if len(cases) < 2:
        raise CityOpsContractError("multi-fixture replay cases below minimum")
    outcomes = {case.get("observed_outcome") for case in cases}
    if "success_cleanup" not in outcomes:
        raise CityOpsContractError("multi-fixture replay missing success cleanup outcome")
    if not ({"hold", "quarantine"} & outcomes):
        raise CityOpsContractError("multi-fixture replay missing hold/quarantine outcome")
    for case in cases:
        if case.get("expected_outcome") != case.get("observed_outcome"):
            raise CityOpsContractError("multi-fixture replay expected/observed outcome mismatch")
        if case.get("runtime_handle_persisted") is not False:
            raise CityOpsContractError("multi-fixture replay persisted runtime handle")
        if case.get("fixture_payload_persisted") is not False:
            raise CityOpsContractError("multi-fixture replay persisted fixture payload")
        if case.get("customer_visible") is not False or case.get("worker_visible") is not False:
            raise CityOpsContractError("multi-fixture replay exposed customer/worker surface")
        if case.get("observed_outcome") in {"hold", "quarantine"}:
            if case.get("hold_record_created") is not True and case.get("quarantine_envelope_created") is not True:
                raise CityOpsContractError("hold/quarantine replay missing hold or quarantine record")

    policy = observation.get("sanitization_policy", {})
    for key, value in policy.items():
        if key.startswith("include_") and value is not False:
            raise CityOpsContractError(f"unsafe replay sanitization policy: {key}")
    serialized = json.dumps(observation).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("multi-fixture replay observation contains secret or identifier pattern")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _assert_gate_conservative(gate: dict[str, Any], source: dict[str, Any]) -> None:
    if gate.get("schema") != ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCHEMA:
        raise CityOpsContractError("unexpected multi-fixture replay gate schema")
    if gate.get("gate_verdict") != ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_VERDICT:
        raise CityOpsContractError("unexpected multi-fixture replay verdict")
    if gate.get("source_artifacts", {}).get("cleanup_quarantine_harness_gate", {}).get("digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("multi-fixture replay source digest mismatch")
    _assert_observation_safe_and_complete(gate.get("multi_fixture_replay_observation", {}))
    results = gate.get("replay_results", {})
    if results.get("success_case_count", 0) < 1:
        raise CityOpsContractError("multi-fixture replay result missing success case")
    if results.get("hold_case_count", 0) + results.get("quarantine_case_count", 0) < 1:
        raise CityOpsContractError("multi-fixture replay result missing hold/quarantine case")
    if results.get("runtime_handles_persisted") is not False:
        raise CityOpsContractError("multi-fixture replay results persisted runtime handle")
    if results.get("fixture_payloads_persisted") is not False:
        raise CityOpsContractError("multi-fixture replay results persisted fixture payload")
    if results.get("customer_visible") is not False or results.get("worker_visible") is not False:
        raise CityOpsContractError("multi-fixture replay results exposed customer/worker surface")

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
        "operator_activation_approved",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"multi-fixture replay readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if gate.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"multi-fixture replay access flag promoted: {key}")
    blocked = set(gate.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if not set(MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS) <= blocked:
        raise CityOpsContractError("multi-fixture replay missing blocked claims")
    if ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM not in gate.get("claim_boundaries", {}).get("safe_to_claim", []):
        raise CityOpsContractError("multi-fixture replay missing safe claim")
    if gate.get("operator_guidance", {}).get("stop_line") != ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_STOP_LINE:
        raise CityOpsContractError("multi-fixture replay stop line drift")
    serialized = json.dumps(gate).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("multi-fixture replay gate contains secret or identifier pattern")


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
