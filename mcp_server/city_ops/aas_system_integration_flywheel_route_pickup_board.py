"""Internal/admin pickup board for the AAS system-integration flywheel route handoff.

This module consumes the compact route handoff packet and turns it into a small
operator pickup board. It deliberately does not create another route, customer
copy, public/catalog surface, dispatch path, reputation receipt, live Acontext
runtime claim, payment/production reverification, GPS/raw metadata release,
authority claim, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_system_integration_flywheel_route_handoff_packet import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SCHEMA,
    HANDOFF_BLOCKED_CLAIMS,
    HANDOFF_FALSE_ACCESS_FLAGS,
    HANDOFF_READINESS_FLAGS,
    build_aas_system_integration_flywheel_route_handoff_packet,
    load_aas_system_integration_flywheel_route_handoff_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SCHEMA = (
    "city_ops.aas_system_integration_flywheel_route_pickup_board.v1"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME = (
    "aas_system_integration_flywheel_route_pickup_board.json"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM = (
    "internal_admin_aas_system_integration_flywheel_route_pickup_board_landed"
)

PICKUP_BOARD_ID = "execution_market.aas.system_integration_flywheel.route_pickup_board.2026_05_28_0100"
PICKUP_BOARD_SCOPE = "internal_admin_route_handoff_pickup_board_only_no_route_expansion"
PICKUP_BOARD_STATUS = "three_safe_forks_named_default_stop_no_customer_or_runtime_promotion"
PICKUP_BOARD_VERDICT = "route_handoff_pickup_ready_default_stop_until_operator_or_runtime_truth"
DEFAULT_NEXT_ACTION = "stop_route_expansion_and_wait_for_operator_or_runtime_truth"

PICKUP_BOARD_BLOCKED_CLAIMS = [
    "system_integration_flywheel_route_pickup_board_is_customer_or_public_surface",
    "system_integration_flywheel_route_pickup_board_authorizes_customer_copy",
    "system_integration_flywheel_route_pickup_board_authorizes_customer_delivery",
    "system_integration_flywheel_route_pickup_board_authorizes_publication",
    "system_integration_flywheel_route_pickup_board_registers_catalog_or_public_route",
    "system_integration_flywheel_route_pickup_board_authorizes_pricing_or_customer_quote",
    "system_integration_flywheel_route_pickup_board_authorizes_queue_launch_or_dispatch",
    "system_integration_flywheel_route_pickup_board_authorizes_erc8004_reputation",
    "system_integration_flywheel_route_pickup_board_proves_worker_skill_dna",
    "system_integration_flywheel_route_pickup_board_proves_live_acontext_or_runtime_parity",
    "system_integration_flywheel_route_pickup_board_reverifies_payment_or_production",
    "system_integration_flywheel_route_pickup_board_allows_exact_gps_or_raw_metadata",
    "system_integration_flywheel_route_pickup_board_grants_legal_regulator_notarial_or_custody_authority",
    "system_integration_flywheel_route_pickup_board_grants_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
    "system_integration_flywheel_route_pickup_board_creates_worker_copyable_doctrine",
    "system_integration_flywheel_route_pickup_board_turns_pickup_choice_into_launch_readiness",
]

PICKUP_BOARD_FALSE_ACCESS_FLAGS = {
    **HANDOFF_FALSE_ACCESS_FLAGS,
    "adds_route": False,
    "writes_customer_copy": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "writes_municipal_memory": False,
    "reverifies_payment_coverage": False,
    "reverifies_production_infrastructure": False,
}

PICKUP_BOARD_READINESS_FLAGS = {
    "pickup_board_landed": True,
    "source_handoff_verified": True,
    "safe_forks_named": True,
    "default_stop_selected": True,
    "route_expansion_paused": True,
    "operator_truth_required_for_customer_boundary": True,
    "runtime_truth_required_for_acontext_boundary": True,
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


def build_aas_system_integration_flywheel_route_pickup_board(
    *,
    artifact_dir: str | Path | None = None,
    handoff_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin pickup board over the route handoff."""

    handoff = handoff_packet or load_aas_system_integration_flywheel_route_handoff(
        artifact_dir=artifact_dir
    )
    _assert_source_handoff_contract(handoff)

    safe_to_claim = _dedupe(
        [
            *handoff["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *handoff["claim_boundaries"]["do_not_claim_yet"],
            *HANDOFF_BLOCKED_CLAIMS,
            *PICKUP_BOARD_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    board = {
        "schema": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SCHEMA,
        "board_id": PICKUP_BOARD_ID,
        "scope": PICKUP_BOARD_SCOPE,
        "status": PICKUP_BOARD_STATUS,
        "source_handoff": {
            "file": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME,
            "schema": handoff["schema"],
            "id": handoff["handoff_id"],
            "safe_claim": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
            "digest_sha256": _stable_digest(handoff),
            "handoff_verdict": handoff["handoff_verdict"],
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
            ],
            "consumes_only": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
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
            **PICKUP_BOARD_FALSE_ACCESS_FLAGS,
        },
        "default_next_action": DEFAULT_NEXT_ACTION,
        "safe_fork_cards": _safe_fork_cards(handoff),
        "fork_selection_rules": _fork_selection_rules(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_copy": {
            "headline": "System-integration route proof is picked up; do not expand routes by default.",
            "body": (
                "Use the source handoff as the single pickup artifact. Pick runtime truth only "
                "after Docker/Acontext prerequisites are proven, pick operator truth only after "
                "a real human/operator answer exists, otherwise stop route expansion."
            ),
            "forbidden_summary": (
                "No customer copy, delivery, publication, dispatch, reputation, live Acontext "
                "parity, payment/production proof, GPS/raw metadata, authority, or worker doctrine."
            ),
        },
        "readiness": dict(PICKUP_BOARD_READINESS_FLAGS),
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
        },
        "board_verdict": PICKUP_BOARD_VERDICT,
    }
    _assert_pickup_board_contract(board, handoff)
    return board


def load_aas_system_integration_flywheel_route_handoff(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted route handoff or rebuild it deterministically."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
    if path.exists():
        handoff = load_aas_system_integration_flywheel_route_handoff_packet(
            artifact_dir=base_dir
        )
    else:
        handoff = build_aas_system_integration_flywheel_route_handoff_packet(
            artifact_dir=base_dir
        )
    _assert_source_handoff_contract(handoff)
    return handoff


def load_aas_system_integration_flywheel_route_pickup_board(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted route pickup board fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME
    board = json.loads(path.read_text(encoding="utf-8"))
    handoff = load_aas_system_integration_flywheel_route_handoff(artifact_dir=base_dir)
    _assert_pickup_board_contract(board, handoff)
    return board


def write_aas_system_integration_flywheel_route_pickup_board(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic route pickup board fixture."""

    board = build_aas_system_integration_flywheel_route_pickup_board(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _safe_fork_cards(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    source_route = handoff["source_preflight"]["route_path"]
    source_handoff_id = handoff["handoff_id"]
    return [
        {
            "fork": "default_stop",
            "status": "recommended_until_new_truth_exists",
            "source_handoff_id": source_handoff_id,
            "route_path": source_route,
            "allowed_now": True,
            "creates_new_route": False,
            "customer_visible": False,
            "dispatch_ready": False,
            "runtime_parity_ready": False,
            "operator_truth_required": False,
            "next_artifact": "none_required_stop_marker_is_sufficient",
            "why": "the handoff already proves the internal/admin route boundary and pauses route expansion",
        },
        {
            "fork": "runtime_truth",
            "status": "blocked_until_prerequisites_are_real",
            "source_handoff_id": source_handoff_id,
            "allowed_now": False,
            "creates_new_route": False,
            "customer_visible": False,
            "dispatch_ready": False,
            "runtime_parity_ready": False,
            "operator_truth_required": False,
            "required_before_start": [
                "docker_image_pull_or_local_cache_verified",
                "acontext_api_dashboard_localhost_verified",
                "empty_acontext_readiness_gate_rebuilt",
                "exactly_one_live_write_retrieve_attempt_authorized_by_preflight",
            ],
            "next_artifact": "acontext_runtime_memory_prerequisite_or_live_parity_gate_only",
            "why": "runtime memory must be proven by runtime evidence, not by route handoff structure",
        },
        {
            "fork": "operator_truth",
            "status": "blocked_until_real_human_operator_answer_exists",
            "source_handoff_id": source_handoff_id,
            "allowed_now": False,
            "creates_new_route": False,
            "customer_visible": False,
            "dispatch_ready": False,
            "runtime_parity_ready": False,
            "operator_truth_required": True,
            "required_before_start": [
                "named_boundary_selected",
                "exact_text_or_field_boundary_approved",
                "delivery_path_explicitly_named_or_kept_none",
                "redaction_and_authority_checks_recorded",
            ],
            "next_artifact": "separate_human_operator_decision_record_for_one_exact_boundary",
            "why": "customer exposure needs an explicit operator decision artifact, not route proof reuse",
        },
    ]


def _fork_selection_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule": "no_new_truth_defaults_to_stop",
            "if": "no new runtime evidence and no human/operator answer are present",
            "then": DEFAULT_NEXT_ACTION,
        },
        {
            "rule": "runtime_truth_is_evidence_gated",
            "if": "Docker/Acontext prerequisites are actually green",
            "then": "attempt exactly one live write/retrieve parity pass and record the result separately",
        },
        {
            "rule": "operator_truth_is_decision_gated",
            "if": "Saul or a delegated human/operator gives an explicit boundary answer",
            "then": "create a separate approval or hold record for that exact boundary and delivery path",
        },
        {
            "rule": "route_layers_do_not_create_launch_readiness",
            "if": "the only new artifact is another internal/admin route or board",
            "then": "keep customer, dispatch, reputation, runtime, and authority claims blocked",
        },
    ]


def _assert_source_handoff_contract(handoff: dict[str, Any]) -> None:
    if handoff.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SCHEMA:
        raise CityOpsContractError("invalid source system integration flywheel route handoff schema")
    if AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM not in handoff.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("source route handoff missing safe claim")
    missing_blocked = sorted(
        set(HANDOFF_BLOCKED_CLAIMS)
        - set(handoff.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    )
    if missing_blocked:
        raise CityOpsContractError(f"source route handoff missing blocked claims: {missing_blocked}")
    for flag, expected in HANDOFF_FALSE_ACCESS_FLAGS.items():
        if handoff.get("access_policy", {}).get(flag) is not expected:
            raise CityOpsContractError(f"source route handoff access drift: {flag}")
    for flag, expected in HANDOFF_READINESS_FLAGS.items():
        if handoff.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"source route handoff readiness drift: {flag}")
    _assert_no_claim_overlap(
        handoff.get("claim_boundaries", {}).get("safe_to_claim", []),
        handoff.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_pickup_board_contract(board: dict[str, Any], handoff: dict[str, Any]) -> None:
    if board.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SCHEMA:
        raise CityOpsContractError("invalid system integration flywheel route pickup board schema")
    if board.get("source_handoff", {}).get("id") != handoff.get("handoff_id"):
        raise CityOpsContractError("system integration flywheel route pickup board source drift")
    if board.get("default_next_action") != DEFAULT_NEXT_ACTION:
        raise CityOpsContractError("system integration flywheel route pickup board default action drift")
    derived = board.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("system integration flywheel route pickup board must stay read-only")
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
            raise CityOpsContractError(f"system integration flywheel route pickup board derived drift: {flag}")
    access_policy = board.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("system integration flywheel route pickup board audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("system integration flywheel route pickup board requires admin context")
    for flag, expected in PICKUP_BOARD_FALSE_ACCESS_FLAGS.items():
        if access_policy.get(flag) is not expected:
            raise CityOpsContractError(f"system integration flywheel route pickup board access drift: {flag}")
    for flag, expected in PICKUP_BOARD_READINESS_FLAGS.items():
        if board.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"system integration flywheel route pickup board readiness drift: {flag}")
    fork_cards = board.get("safe_fork_cards", [])
    if [card.get("fork") for card in fork_cards] != [
        "default_stop",
        "runtime_truth",
        "operator_truth",
    ]:
        raise CityOpsContractError("system integration flywheel route pickup board fork order drift")
    if fork_cards[0].get("allowed_now") is not True:
        raise CityOpsContractError("system integration flywheel route pickup board default stop must be allowed")
    for card in fork_cards[1:]:
        if card.get("allowed_now") is not False:
            raise CityOpsContractError("system integration flywheel route pickup board future forks must remain blocked")
    safe_to_claim = board.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = board.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PICKUP_BOARD_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("system integration flywheel route pickup board missing safe claim")
    missing = sorted(set(PICKUP_BOARD_BLOCKED_CLAIMS) - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(f"system integration flywheel route pickup board missing blocked claims: {missing}")
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"system integration flywheel route pickup board claim overlap: {overlap}")


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
