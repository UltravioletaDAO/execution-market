"""Disabled-by-default Acontext runtime adapter seam contract.

This proof block follows the runtime-memory promotion gate. It designs the next
implementation seam for IRC/session-manager memory integration while keeping the
seam disabled by default and preserving all external/product boundaries. The
artifact is a contract only: it does not contact Acontext, register runtime
hooks, mutate IRC session management, replay fixtures, create routes, launch
dispatch, emit reputation, verify payments, expose GPS/raw metadata, release
private context, or publish worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_runtime_memory_promotion_gate import (
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM,
    ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCHEMA,
    load_acontext_runtime_memory_promotion_gate,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCHEMA = (
    "city_ops.acontext_opt_in_runtime_adapter_seam_contract.v1"
)
ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME = (
    "acontext_opt_in_runtime_adapter_seam_contract.json"
)
ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM = (
    "admin_acontext_opt_in_runtime_adapter_seam_contract_landed"
)
ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_ID = (
    "execution_market.aas.acontext_opt_in_runtime_adapter_seam_contract.2026_05_31_0615"
)
ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCOPE = (
    "internal_admin_disabled_by_default_runtime_adapter_seam_contract_no_runtime_mutation"
)
ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_VERDICT = (
    "disabled_by_default_runtime_adapter_seam_contract_defined_without_runtime_mutation"
)
ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_STOP_LINE = (
    "This contract may guide implementation planning only. Do not register the runtime adapter, "
    "mutate IRC session management, enable cross-project autorouting, replay unreviewed fixtures, "
    "publish customer/worker surfaces, launch dispatch, emit reputation, claim payment/production "
    "readiness, expose GPS/raw metadata/private context, or create worker-copyable doctrine until "
    "separate cleanup/quarantine and multi-fixture replay gates pass."
)

RUNTIME_ADAPTER_SEAM_BLOCKED_CLAIMS = [
    "runtime_adapter_seam_authorizes_runtime_registration",
    "runtime_adapter_seam_authorizes_irc_session_manager_mutation",
    "runtime_adapter_seam_authorizes_cross_project_autorouting",
    "runtime_adapter_seam_authorizes_customer_copy_delivery_or_publication",
    "runtime_adapter_seam_authorizes_public_or_catalog_route",
    "runtime_adapter_seam_authorizes_pricing_or_customer_quote",
    "runtime_adapter_seam_authorizes_operator_queue_launch_or_dispatch",
    "runtime_adapter_seam_authorizes_erc8004_reputation_or_worker_skill_dna",
    "runtime_adapter_seam_reverifies_payment_or_production",
    "runtime_adapter_seam_allows_exact_gps_or_raw_metadata",
    "runtime_adapter_seam_releases_private_operator_context",
    "runtime_adapter_seam_creates_worker_copyable_doctrine",
    "runtime_adapter_seam_declares_general_acontext_sink_ready",
    "runtime_adapter_seam_declares_runtime_parity_proven",
    "runtime_adapter_seam_declares_cleanup_or_quarantine_executed",
    "runtime_adapter_seam_declares_multi_fixture_replay_executed",
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
    "cleanup_or_quarantine_executed": False,
    "multi_fixture_replay_executed": False,
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


def build_acontext_opt_in_runtime_adapter_seam_contract(
    *,
    artifact_dir: str | Path | None = None,
    promotion_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic disabled-by-default runtime adapter seam contract."""

    source = promotion_gate or load_acontext_runtime_memory_promotion_gate(
        artifact_dir=artifact_dir
    )
    _assert_promotion_gate_source(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM,
            ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *RUNTIME_ADAPTER_SEAM_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    contract = {
        "schema": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCHEMA,
        "contract_id": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_ID,
        "scope": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SCOPE,
        "source_artifacts": {
            "runtime_memory_promotion_gate": {
                "file": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME,
                "schema": source["schema"],
                "id": source["gate_id"],
                "safe_claim": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "gate_verdict": source["gate_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_FILENAME],
            "reruns_local_acontext": False,
            "uses_root_or_project_token": False,
            "prints_or_persists_secret": False,
            "records_session_or_message_ids": False,
            "registers_runtime_adapter": False,
            "touches_irc_runtime_session_manager": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_external_services": False,
        },
        "contract_principles": {
            "disabled_by_default": True,
            "explicit_operator_activation_required": True,
            "fail_closed_on_missing_cleanup_or_quarantine": True,
            "fail_closed_on_single_fixture_only": True,
            "persist_only_redacted_status_and_boolean_facts": True,
            "no_raw_session_or_message_ids_in_artifacts": True,
            "no_private_context_or_gps_raw_metadata": True,
            "no_customer_or_worker_copy": True,
        },
        "seam_interfaces": {
            "runtime_insertion_point": {
                "name": "irc_session_manager_memory_sink",
                "status": "design_only_not_registered",
                "activation_mode": "operator_opt_in_after_separate_gates",
                "default_enabled": False,
                "accepts_private_context": False,
                "accepts_gps_or_raw_metadata": False,
                "accepts_customer_copy": False,
                "accepts_worker_instruction": False,
            },
            "candidate_input_contract": {
                "required_fields": [
                    "project_key",
                    "surface",
                    "packet_kind",
                    "sanitized_message_text",
                    "sanitized_metadata",
                    "source_fixture_id",
                    "operator_hold_default",
                ],
                "required_boolean_false_fields": [
                    "contains_private_context",
                    "contains_gps_or_raw_metadata",
                    "customer_visible",
                    "worker_visible",
                    "dispatch_enabled",
                    "reputation_enabled",
                    "payment_or_production_claim",
                ],
                "forbidden_fields": [
                    "root_token",
                    "bearer_token",
                    "project_secret",
                    "session_id",
                    "message_id",
                    "gps_coordinates",
                    "raw_metadata",
                    "private_operator_context",
                    "customer_copy",
                    "worker_instruction",
                ],
            },
            "cleanup_or_quarantine_contract": {
                "status": "defined_not_executed",
                "required_before_activation": True,
                "must_keep_runtime_ids_in_process_memory_only": True,
                "must_record_only_status_booleans": True,
                "must_have_quarantine_path_for_failed_write_or_retrieve": True,
                "must_have_explicit_delete_or_tombstone_observation": True,
                "authorizes_runtime_mutation": False,
            },
            "multi_fixture_replay_contract": {
                "status": "defined_not_executed",
                "required_before_activation": True,
                "minimum_reviewed_sanitized_fixtures": 2,
                "must_include_success_and_hold_cases": True,
                "must_reject_any_private_context_or_gps_fixture": True,
                "must_not_infer_general_sink_readiness": True,
                "authorizes_runtime_mutation": False,
            },
            "rollback_controls": {
                "kill_switch_required": True,
                "operator_hold_default": True,
                "customer_or_worker_surface_default": False,
                "dispatch_reputation_payment_default": False,
            },
        },
        "promotion_sequence": _promotion_sequence(),
        "readiness": {
            "seam_contract_landed": True,
            "source_promotion_gate_validated": True,
            "disabled_by_default_contract_defined": True,
            "cleanup_or_quarantine_contract_defined": True,
            "multi_fixture_replay_contract_defined": True,
            "safe_for_internal_implementation_planning": True,
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
            "cleanup_or_quarantine_executed": False,
            "multi_fixture_replay_executed": False,
            "general_acontext_sink_ready": False,
            "runtime_parity_proven": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "claim_boundary_audit": {
            "inherited_from_promotion_gate": source["claim_boundaries"]["do_not_claim_yet"],
            "new_do_not_claim_yet": RUNTIME_ADAPTER_SEAM_BLOCKED_CLAIMS,
            "safe_claim_added": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
            "no_blocked_claims_lifted_by_this_contract": True,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "operator_guidance": {
            "safe_to_use_for": [
                "internal implementation planning for a disabled runtime adapter seam",
                "writing future cleanup/quarantine tests before runtime registration",
                "writing future multi-fixture replay tests before generalized sink claims",
            ],
            "not_safe_for": [
                "registering or enabling the runtime adapter",
                "mutating IRC runtime session management",
                "cross-project autorouting",
                "customer/public delivery or publication",
                "operator queue launch or worker dispatch",
                "ERC-8004 reputation or Worker Skill DNA",
                "payment or production readiness claims",
                "GPS/raw metadata/private-context exposure",
                "worker-copyable doctrine",
            ],
            "next_separate_gate": (
                "Execute cleanup/quarantine proof on reviewed sanitized fixtures while persisting only "
                "status booleans, then run a multi-fixture replay gate; keep the adapter disabled until both pass."
            ),
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "stop_line": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_STOP_LINE,
        },
        "contract_verdict": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_VERDICT,
    }
    _assert_contract_conservative(contract)
    return contract


def write_acontext_opt_in_runtime_adapter_seam_contract(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the deterministic runtime adapter seam contract and return its path."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    contract = build_acontext_opt_in_runtime_adapter_seam_contract(artifact_dir=target_dir)
    path = target_dir / ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME
    path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_opt_in_runtime_adapter_seam_contract(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted runtime adapter seam contract."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = target_dir / ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME
    contract = json.loads(path.read_text(encoding="utf-8"))
    expected = build_acontext_opt_in_runtime_adapter_seam_contract(artifact_dir=target_dir)
    if contract != expected:
        raise CityOpsContractError(
            f"{ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_FILENAME} fixture drift"
        )
    return contract


def _promotion_sequence() -> list[dict[str, Any]]:
    return [
        {
            "gate": "runtime_memory_promotion_gate",
            "status": "passed",
            "evidence": ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM,
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "gate": "disabled_by_default_adapter_seam_contract",
            "status": "passed",
            "evidence": ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_SAFE_CLAIM,
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "gate": "cleanup_or_quarantine_execution",
            "status": "blocked",
            "required_next": "execute reviewed sanitized cleanup/quarantine proof without persisting runtime IDs",
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "gate": "multi_fixture_replay_execution",
            "status": "blocked",
            "required_next": "replay at least two reviewed sanitized fixtures including success and hold cases",
            "authorizes_runtime_adapter_registration": False,
        },
        {
            "gate": "operator_activation_decision",
            "status": "blocked",
            "required_next": "separate explicit operator activation decision after proof gates pass",
            "authorizes_runtime_adapter_registration": False,
        },
    ]


def _assert_promotion_gate_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SCHEMA:
        raise CityOpsContractError("runtime memory promotion gate source schema mismatch")
    readiness = source.get("readiness", {})
    required_true = [
        "promotion_gate_landed",
        "source_runner_fixture_validated",
        "single_redacted_local_runner_succeeded",
        "safe_for_internal_adapter_design",
    ]
    for key in required_true:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"promotion gate readiness mismatch: {key}")
    required_false = [
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
    ]
    for key in required_false:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"promotion gate readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"promotion gate access flag promoted: {key}")
    if ACONTEXT_RUNTIME_MEMORY_PROMOTION_GATE_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("promotion gate safe claim missing")


def _assert_contract_conservative(contract: dict[str, Any]) -> None:
    _assert_claim_boundaries(
        contract["claim_boundaries"]["safe_to_claim"],
        contract["claim_boundaries"]["do_not_claim_yet"],
    )
    for key, value in contract.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"access flag must remain false: {key}")
    readiness = contract.get("readiness", {})
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
        "cleanup_or_quarantine_executed",
        "multi_fixture_replay_executed",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"readiness flag must remain false: {key}")
    for row in contract.get("promotion_sequence", []):
        if row.get("authorizes_runtime_adapter_registration") is not False:
            raise CityOpsContractError("promotion sequence authorized runtime adapter registration")
    serialized = json.dumps(contract, sort_keys=True)
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
