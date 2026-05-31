"""Fail-closed promotion gate after the redacted Acontext IRC adapter runner.

The local runner proved one sanitized IRC-session-shaped memory candidate can be
stored and retrieved from the local Acontext API while keeping bearer values,
session IDs, message IDs, private context, and GPS/raw metadata out of persisted
artifacts.  This module turns that success into the next bounded promotion gate:
what can be used by an internal operator, and what must still stay blocked
before any runtime/session-manager, customer/public, dispatch, reputation,
payment, or worker-doctrine claim.

It consumes only the persisted redacted runner fixture. It does not contact
Acontext, mutate IRC runtime state, create routes, launch dispatch, emit
reputation, reverify production/payments, expose raw metadata, or create
customer/worker copy.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_internal_irc_session_adapter_runner_fixture import (
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM,
    ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCHEMA,
    load_acontext_internal_irc_session_adapter_runner_fixture,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCHEMA = (
    "city_ops.acontext_runtime_memory_promotion_gate.v1"
)
ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME = (
    "acontext_runtime_memory_promotion_gate.json"
)
ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM = (
    "admin_acontext_runtime_memory_promotion_gate_landed"
)
ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_ID = (
    "execution_market.aas.acontext_runtime_memory_promotion_gate.2026_05_31_0525"
)
ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCOPE = (
    "internal_admin_runtime_memory_promotion_gate_no_runtime_mutation"
)
ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_VERDICT = (
    "single_redacted_runner_succeeded_runtime_promotion_remains_blocked"
)
ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_STOP_LINE = (
    "The redacted local runner can inform internal adapter design only; do not mutate IRC runtime "
    "session management, enable cross-project autorouting, publish customer/worker surfaces, launch "
    "dispatch, emit reputation, claim payments/production, expose GPS/raw metadata/private context, "
    "or write worker-copyable doctrine until separate gates pass."
)

PROMOTION_GATE_BLOCKED_CLAIMS = [
    "promotion_gate_authorizes_irc_runtime_session_manager_mutation",
    "promotion_gate_authorizes_cross_project_autorouting",
    "promotion_gate_authorizes_customer_copy_delivery_or_publication",
    "promotion_gate_authorizes_public_or_catalog_route",
    "promotion_gate_authorizes_pricing_or_customer_quote",
    "promotion_gate_authorizes_operator_queue_launch_or_dispatch",
    "promotion_gate_authorizes_erc8004_reputation_or_worker_skill_dna",
    "promotion_gate_reverifies_payment_or_production",
    "promotion_gate_allows_exact_gps_or_raw_metadata",
    "promotion_gate_releases_private_operator_context",
    "promotion_gate_creates_worker_copyable_doctrine",
    "promotion_gate_declares_general_acontext_sink_ready",
    "promotion_gate_declares_runtime_parity_proven",
    "promotion_gate_declares_cleanup_or_quarantine_ready",
    "promotion_gate_declares_multi_fixture_replay_ready",
]

_FALSE_FLAGS = {
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
    "changes_irc_runtime_session_manager": False,
    "enables_cross_project_autorouting": False,
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


def build_acontext_runtime_memory_promotion_gate(
    *,
    artifact_dir: str | Path | None = None,
    runner_fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic fail-closed promotion gate from the runner fixture."""

    source = runner_fixture or load_acontext_internal_irc_session_adapter_runner_fixture(
        artifact_dir=artifact_dir
    )
    _assert_runner_fixture_source(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM,
            ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *PROMOTION_GATE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    gate = {
        "schema": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCHEMA,
        "gate_id": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_ID,
        "scope": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCOPE,
        "source_artifacts": {
            "redacted_runner_fixture": {
                "file": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_FILENAME],
            "reruns_local_acontext": False,
            "uses_root_or_project_token": False,
            "prints_or_persists_secret": False,
            "records_session_or_message_ids": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_external_services": False,
            "mutates_irc_runtime_session_manager": False,
        },
        "promotable_facts": {
            "source_adapter_contract_defined": True,
            "single_local_runner_fixture_executed": True,
            "sanitized_session_create_status_201": True,
            "sanitized_message_store_status_201": True,
            "sanitized_message_retrieve_status_200": True,
            "retrieved_message_text_matched": True,
            "retrieved_message_meta_matched": True,
            "root_token_or_bearer_recorded": False,
            "session_or_message_id_recorded": False,
            "private_context_or_gps_recorded": False,
        },
        "promotion_gates": _promotion_gates(),
        "readiness": {
            "promotion_gate_landed": True,
            "source_runner_fixture_validated": True,
            "single_redacted_local_runner_succeeded": True,
            "safe_for_internal_adapter_design": True,
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
            "cleanup_or_quarantine_ready": False,
            "multi_fixture_replay_ready": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "claim_boundary_audit": {
            "inherited_from_runner_fixture": source["claim_boundaries"]["do_not_claim_yet"],
            "new_do_not_claim_yet": PROMOTION_GATE_BLOCKED_CLAIMS,
            "safe_claim_added": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM,
            "no_blocked_claims_lifted_by_this_gate": True,
        },
        "access_flags": dict(_FALSE_FLAGS),
        "operator_guidance": {
            "safe_to_use_for": [
                "internal adapter design based on one redacted successful runner",
                "daytime pickup sequencing for an opt-in runtime seam",
                "claim-boundary review before any future session-manager mutation",
            ],
            "not_safe_for": [
                "runtime IRC session-manager mutation",
                "cross-project autorouting",
                "customer/public delivery or publication",
                "operator queue launch or worker dispatch",
                "ERC-8004 reputation or Worker Skill DNA",
                "payment or production readiness claims",
                "GPS/raw metadata/private-context exposure",
                "worker-copyable doctrine",
            ],
            "next_separate_gate": (
                "Design an opt-in runtime adapter seam with cleanup/quarantine behavior, replay on more "
                "than one reviewed sanitized fixture, and explicit false defaults for customer/public, "
                "dispatch, reputation, payment, GPS/raw metadata, private-context, and worker-doctrine claims."
            ),
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "stop_line": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_STOP_LINE,
        },
        "gate_verdict": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_VERDICT,
    }
    _assert_gate_conservative(gate)
    return gate


def write_acontext_runtime_memory_promotion_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the deterministic runtime-memory promotion gate and return its path."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_acontext_runtime_memory_promotion_gate(artifact_dir=target_dir)
    path = target_dir / ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_runtime_memory_promotion_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted runtime-memory promotion gate."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = target_dir / ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME
    gate = json.loads(path.read_text(encoding="utf-8"))
    expected = build_acontext_runtime_memory_promotion_gate(artifact_dir=target_dir)
    if gate != expected:
        raise CityOpsContractError(
            f"{ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME} fixture drift"
        )
    return gate


def _promotion_gates() -> list[dict[str, Any]]:
    return [
        {
            "gate": "internal_adapter_contract",
            "status": "passed",
            "evidence": "source runner fixture validated its adapter contract source",
            "authorizes_runtime_promotion": False,
        },
        {
            "gate": "single_redacted_local_runner",
            "status": "passed",
            "evidence": "one sanitized session/message write/retrieve returned 201/201/200 and matched metadata",
            "authorizes_runtime_promotion": False,
        },
        {
            "gate": "cleanup_or_quarantine_policy",
            "status": "blocked",
            "required_next": "prove cleanup/quarantine semantics without persisting session/message IDs",
            "authorizes_runtime_promotion": False,
        },
        {
            "gate": "multi_fixture_replay",
            "status": "blocked",
            "required_next": "repeat with more than one reviewed sanitized fixture before generalized sink claims",
            "authorizes_runtime_promotion": False,
        },
        {
            "gate": "opt_in_irc_runtime_adapter_seam",
            "status": "blocked",
            "required_next": "design a disabled-by-default seam before touching runtime session management",
            "authorizes_runtime_promotion": False,
        },
        {
            "gate": "external_product_surfaces",
            "status": "blocked",
            "required_next": "separate human/operator approval for customer, public, dispatch, reputation, or payment claims",
            "authorizes_runtime_promotion": False,
        },
    ]


def _assert_runner_fixture_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_INTERNAL_IRC_SESSION_ADAPTER_RUNNER_FIXTURE_SCHEMA:
        raise CityOpsContractError("runner fixture source schema mismatch")
    readiness = source.get("readiness", {})
    required_true = [
        "source_adapter_contract_defined",
        "local_runner_fixture_executed",
        "sanitized_session_create_status_201",
        "sanitized_message_store_status_201",
        "sanitized_message_retrieve_status_200",
        "retrieved_message_text_matched",
        "retrieved_message_meta_matched",
    ]
    for key in required_true:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"runner fixture readiness mismatch: {key}")
    required_false = [
        "root_token_or_bearer_recorded",
        "session_or_message_id_recorded",
        "scoped_project_secret_created_or_acquired",
        "production_or_remote_acontext_proven",
        "irc_runtime_session_manager_ready",
        "cross_project_autorouting_ready",
        "customer_or_public_delivery_ready",
    ]
    for key in required_false:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"runner fixture readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"runner fixture access flag promoted: {key}")


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
        "cleanup_or_quarantine_ready",
        "multi_fixture_replay_ready",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"readiness flag must remain false: {key}")
    if readiness.get("single_redacted_local_runner_succeeded") is not True:
        raise CityOpsContractError("single redacted runner success must stay explicit")
    for gate_row in gate.get("promotion_gates", []):
        if gate_row.get("authorizes_runtime_promotion") is not False:
            raise CityOpsContractError("promotion gate authorized runtime promotion")
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
