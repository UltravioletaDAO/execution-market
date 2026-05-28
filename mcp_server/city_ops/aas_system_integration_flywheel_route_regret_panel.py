"""Internal/admin regret panel for AAS system-integration route layering.

This module consumes the pickup board and records the conservative conclusion:
do not keep adding internal route layers when no new runtime truth or operator
truth exists. It creates no route, customer copy, public/catalog surface,
dispatch path, reputation receipt, live Acontext/runtime claim,
payment/production reverification, GPS/raw metadata release, authority claim, or
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_system_integration_flywheel_route_pickup_board import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SCHEMA,
    DEFAULT_NEXT_ACTION as PICKUP_BOARD_DEFAULT_NEXT_ACTION,
    PICKUP_BOARD_BLOCKED_CLAIMS,
    PICKUP_BOARD_FALSE_ACCESS_FLAGS,
    PICKUP_BOARD_READINESS_FLAGS,
    build_aas_system_integration_flywheel_route_pickup_board,
    load_aas_system_integration_flywheel_route_pickup_board,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA = (
    "city_ops.aas_system_integration_flywheel_route_regret_panel.v1"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME = (
    "aas_system_integration_flywheel_route_regret_panel.json"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM = (
    "internal_admin_aas_system_integration_flywheel_route_regret_panel_landed"
)

REGRET_PANEL_ID = "execution_market.aas.system_integration_flywheel.route_regret_panel.2026_05_28_0200"
REGRET_PANEL_SCOPE = "internal_admin_route_layer_regret_panel_only_no_route_or_customer_promotion"
REGRET_PANEL_STATUS = "extra_route_layering_regretted_default_stop_reaffirmed"
REGRET_PANEL_VERDICT = "stop_internal_route_layering_until_runtime_or_operator_truth_exists"
REGRET_PANEL_DEFAULT_OUTCOME = "regret_more_route_layers_reuse_pickup_board_as_last_artifact"

REGRET_PANEL_BLOCKED_CLAIMS = [
    "system_integration_flywheel_route_regret_panel_is_customer_or_public_surface",
    "system_integration_flywheel_route_regret_panel_authorizes_customer_copy",
    "system_integration_flywheel_route_regret_panel_authorizes_customer_delivery",
    "system_integration_flywheel_route_regret_panel_authorizes_publication",
    "system_integration_flywheel_route_regret_panel_registers_catalog_or_public_route",
    "system_integration_flywheel_route_regret_panel_authorizes_pricing_or_customer_quote",
    "system_integration_flywheel_route_regret_panel_authorizes_queue_launch_or_dispatch",
    "system_integration_flywheel_route_regret_panel_authorizes_erc8004_reputation",
    "system_integration_flywheel_route_regret_panel_proves_worker_skill_dna",
    "system_integration_flywheel_route_regret_panel_proves_live_acontext_or_runtime_parity",
    "system_integration_flywheel_route_regret_panel_reverifies_payment_or_production",
    "system_integration_flywheel_route_regret_panel_allows_exact_gps_or_raw_metadata",
    "system_integration_flywheel_route_regret_panel_grants_legal_regulator_notarial_or_custody_authority",
    "system_integration_flywheel_route_regret_panel_grants_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
    "system_integration_flywheel_route_regret_panel_creates_worker_copyable_doctrine",
    "system_integration_flywheel_route_regret_panel_turns_regret_into_launch_readiness",
    "system_integration_flywheel_route_regret_panel_authorizes_more_route_layers_without_new_truth",
]

REGRET_PANEL_FALSE_ACCESS_FLAGS = {
    **PICKUP_BOARD_FALSE_ACCESS_FLAGS,
    "adds_route": False,
    "writes_customer_copy": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "writes_municipal_memory": False,
    "reverifies_payment_coverage": False,
    "reverifies_production_infrastructure": False,
}

REGRET_PANEL_READINESS_FLAGS = {
    "regret_panel_landed": True,
    "source_pickup_board_verified": True,
    "default_stop_reaffirmed": True,
    "extra_route_layering_stopped": True,
    "new_route_requested": False,
    "runtime_truth_present": False,
    "operator_truth_present": False,
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "public_or_catalog_route_ready": False,
    "pricing_or_customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "live_acontext_runtime_parity_ready": False,
    "payment_or_production_reverified": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "exact_gps_or_raw_metadata_release_ready": False,
    "domain_authority_ready": False,
    "worker_copyable_doctrine_ready": False,
}


def build_aas_system_integration_flywheel_route_regret_panel(
    *,
    artifact_dir: str | Path | None = None,
    pickup_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin regret panel over the pickup board."""

    board = pickup_board or load_aas_system_integration_flywheel_route_pickup_board(
        artifact_dir=artifact_dir
    )
    _assert_source_pickup_board_contract(board)

    safe_to_claim = _dedupe(
        [
            *board["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *board["claim_boundaries"]["do_not_claim_yet"],
            *PICKUP_BOARD_BLOCKED_CLAIMS,
            *REGRET_PANEL_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    panel = {
        "schema": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA,
        "panel_id": REGRET_PANEL_ID,
        "scope": REGRET_PANEL_SCOPE,
        "status": REGRET_PANEL_STATUS,
        "source_pickup_board": {
            "file": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME,
            "schema": board["schema"],
            "id": board["board_id"],
            "safe_claim": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM,
            "digest_sha256": _stable_digest(board),
            "board_verdict": board["board_verdict"],
            "default_next_action": board["default_next_action"],
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME
            ],
            "consumes_only": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME
            ],
            "raw_conversation_reopened": False,
            "raw_worker_evidence_reopened": False,
            "unreviewed_memory_reopened": False,
            "private_operator_context_reopened": False,
            "semantic_reinterpretation_performed": False,
            "adds_route": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "writes_municipal_memory": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "publishes_worker_doctrine": False,
            "exposes_gps_or_metadata": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **REGRET_PANEL_FALSE_ACCESS_FLAGS,
        },
        "default_outcome": REGRET_PANEL_DEFAULT_OUTCOME,
        "regret_checks": _regret_checks(board),
        "allowed_future_work": _allowed_future_work(),
        "forbidden_future_work": _forbidden_future_work(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_copy": {
            "headline": "Stop adding route layers; the pickup board is the last proof-preserving artifact for now.",
            "body": (
                "This panel records the regret check: without new runtime evidence or a real "
                "human/operator boundary answer, another internal/admin route surface would add "
                "ceremony rather than truth. Reuse the pickup board as the handoff and switch "
                "only to runtime-proof or operator-decision work."
            ),
            "forbidden_summary": (
                "No customer copy, delivery, publication, dispatch, reputation, live Acontext "
                "parity, payment/production proof, GPS/raw metadata, authority, worker doctrine, "
                "or more route layers without new truth."
            ),
        },
        "readiness": dict(REGRET_PANEL_READINESS_FLAGS),
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
        },
        "panel_verdict": REGRET_PANEL_VERDICT,
    }
    _assert_regret_panel_contract(panel, board)
    return panel


def load_aas_system_integration_flywheel_route_regret_panel(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted route regret panel fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME
    panel = json.loads(path.read_text(encoding="utf-8"))
    pickup_board = load_aas_system_integration_flywheel_route_pickup_board(
        artifact_dir=base_dir
    )
    _assert_regret_panel_contract(panel, pickup_board)
    return panel


def write_aas_system_integration_flywheel_route_regret_panel(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic route regret panel fixture."""

    panel = build_aas_system_integration_flywheel_route_regret_panel(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME
    path.write_text(json.dumps(panel, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _regret_checks(board: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "check": "source_pickup_board_is_sufficient_handoff",
            "observed": board["board_verdict"],
            "regret": False,
            "decision": "reuse_pickup_board_as_last_route_handoff_artifact",
        },
        {
            "check": "another_route_layer_would_not_add_truth",
            "observed": "no_runtime_truth_and_no_operator_truth_present",
            "regret": True,
            "decision": "do_not_create_more_internal_route_layers_without_new_truth",
        },
        {
            "check": "runtime_path_requires_runtime_evidence",
            "observed": "runtime_truth_fork_blocked_by_pickup_board",
            "regret": False,
            "decision": "only_resume_with_docker_acontext_prerequisite_or_live_parity_gate",
        },
        {
            "check": "operator_path_requires_human_boundary_answer",
            "observed": "operator_truth_fork_blocked_by_pickup_board",
            "regret": False,
            "decision": "only_resume_with_exact_operator_decision_record",
        },
        {
            "check": "customer_promotion_is_not_authorized",
            "observed": "customer_dispatch_reputation_runtime_and_authority_claims_all_blocked",
            "regret": False,
            "decision": "keep_all_customer_public_dispatch_reputation_runtime_and_authority_claims_blocked",
        },
    ]


def _allowed_future_work() -> list[dict[str, Any]]:
    return [
        {
            "track": "runtime_truth",
            "allowed_only_if": [
                "docker_or_local_acontext_prerequisite_proof_exists",
                "single_live_write_retrieve_attempt_scope_is_predeclared",
                "result_is_recorded_as_runtime_evidence_not_route_structure",
            ],
        },
        {
            "track": "operator_truth",
            "allowed_only_if": [
                "one_exact_boundary_is_named",
                "human_or_operator_answer_is_recorded",
                "delivery_path_is_explicitly_allowed_or_kept_none",
                "redaction_authority_and_no_gps_checks_are_recorded",
            ],
        },
        {
            "track": "documentation",
            "allowed_only_if": [
                "it_references_the_pickup_board_or_regret_panel_as_internal_admin_only",
                "it_preserves_all_blocked_customer_runtime_dispatch_reputation_and_authority_claims",
            ],
        },
    ]


def _forbidden_future_work() -> list[str]:
    return [
        "more_internal_route_layers_without_new_runtime_or_operator_truth",
        "customer_copy_from_route_or_pickup_structure_alone",
        "catalog_or_public_route_registration",
        "queue_launch_or_dispatch_enablement",
        "erc8004_reputation_receipts_or_worker_skill_dna_claims",
        "live_acontext_parity_claims_without_a_live_write_retrieve_result",
        "payment_or_production_state_claims_without_fresh_reverification",
        "exact_gps_or_raw_metadata_release",
        "legal_regulator_notarial_custody_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
        "worker_copyable_municipal_doctrine",
    ]


def _assert_source_pickup_board_contract(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SCHEMA:
        raise CityOpsContractError("invalid source system integration flywheel route pickup board schema")
    if AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM not in board.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("source route pickup board missing safe claim")
    missing_blocked = sorted(
        set(PICKUP_BOARD_BLOCKED_CLAIMS)
        - set(board.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    )
    if missing_blocked:
        raise CityOpsContractError(f"source route pickup board missing blocked claims: {missing_blocked}")
    for flag, expected in PICKUP_BOARD_FALSE_ACCESS_FLAGS.items():
        if board.get("access_policy", {}).get(flag) is not expected:
            raise CityOpsContractError(f"source route pickup board access drift: {flag}")
    for flag, expected in PICKUP_BOARD_READINESS_FLAGS.items():
        if board.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"source route pickup board readiness drift: {flag}")
    if board.get("default_next_action") != PICKUP_BOARD_DEFAULT_NEXT_ACTION:
        raise CityOpsContractError("source route pickup board default action drift")
    fork_cards = board.get("safe_fork_cards", [])
    if [card.get("fork") for card in fork_cards] != [
        "default_stop",
        "runtime_truth",
        "operator_truth",
    ]:
        raise CityOpsContractError("source route pickup board fork order drift")
    if fork_cards[0].get("allowed_now") is not True:
        raise CityOpsContractError("source route pickup board default stop must remain allowed")
    for card in fork_cards[1:]:
        if card.get("allowed_now") is not False:
            raise CityOpsContractError("source route pickup board future forks must remain blocked")
    _assert_no_claim_overlap(
        board.get("claim_boundaries", {}).get("safe_to_claim", []),
        board.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_regret_panel_contract(panel: dict[str, Any], board: dict[str, Any]) -> None:
    if panel.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA:
        raise CityOpsContractError("invalid system integration flywheel route regret panel schema")
    if panel.get("source_pickup_board", {}).get("id") != board.get("board_id"):
        raise CityOpsContractError("system integration flywheel route regret panel source drift")
    if panel.get("default_outcome") != REGRET_PANEL_DEFAULT_OUTCOME:
        raise CityOpsContractError("system integration flywheel route regret panel default outcome drift")
    derived = panel.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("system integration flywheel route regret panel must stay read-only")
    for flag in [
        "raw_conversation_reopened",
        "raw_worker_evidence_reopened",
        "unreviewed_memory_reopened",
        "private_operator_context_reopened",
        "semantic_reinterpretation_performed",
        "adds_route",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived.get(flag) is not False:
            raise CityOpsContractError(f"system integration flywheel route regret panel derived drift: {flag}")
    access_policy = panel.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("system integration flywheel route regret panel audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("system integration flywheel route regret panel requires admin context")
    for flag, expected in REGRET_PANEL_FALSE_ACCESS_FLAGS.items():
        if access_policy.get(flag) is not expected:
            raise CityOpsContractError(f"system integration flywheel route regret panel access drift: {flag}")
    for flag, expected in REGRET_PANEL_READINESS_FLAGS.items():
        if panel.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"system integration flywheel route regret panel readiness drift: {flag}")
    checks = panel.get("regret_checks", [])
    if [check.get("check") for check in checks] != [
        "source_pickup_board_is_sufficient_handoff",
        "another_route_layer_would_not_add_truth",
        "runtime_path_requires_runtime_evidence",
        "operator_path_requires_human_boundary_answer",
        "customer_promotion_is_not_authorized",
    ]:
        raise CityOpsContractError("system integration flywheel route regret panel check order drift")
    if checks[1].get("regret") is not True:
        raise CityOpsContractError("system integration flywheel route regret panel must regret extra route layering")
    safe_to_claim = panel.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = panel.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("system integration flywheel route regret panel missing safe claim")
    missing = sorted(set(REGRET_PANEL_BLOCKED_CLAIMS) - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(f"system integration flywheel route regret panel missing blocked claims: {missing}")
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"system integration flywheel route regret panel claim overlap: {overlap}")


def _stable_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
