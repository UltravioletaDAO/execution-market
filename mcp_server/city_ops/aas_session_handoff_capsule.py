"""Read-only IRC/session handoff capsule for AAS system integration.

This module turns the conservative next-truth selector and coordination
observability board into a compact pickup capsule that future agents or IRC
handoffs can carry without reopening raw transcripts.  It preserves the four-ID
header, safe/blocked claims, selected next proof, and stop condition.

It is internal/admin-only planning infrastructure: it does not mutate an IRC
runtime session manager, write or retrieve live Acontext memory, register a
customer/public route, enable dispatch, emit reputation receipts, reverify
payment or production, expose GPS/raw metadata, or publish worker-copyable
doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_coordination_observability_success_metrics_board import (
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
    AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA,
    COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    build_aas_coordination_observability_success_metrics_board,
    load_aas_coordination_observability_success_metrics_board,
)
from .aas_next_truth_selector import (
    AAS_NEXT_TRUTH_SELECTOR_FILENAME,
    AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
    AAS_NEXT_TRUTH_SELECTOR_SCHEMA,
    SELECTED_NEXT_PROOF,
    SELECTED_NEXT_TRACK,
    SELECTOR_BLOCKED_CLAIMS,
    build_aas_next_truth_selector,
    load_aas_next_truth_selector,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SESSION_HANDOFF_CAPSULE_SCHEMA = "city_ops.aas_session_handoff_capsule.v1"
AAS_SESSION_HANDOFF_CAPSULE_FILENAME = "aas_session_handoff_capsule.json"
AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM = (
    "internal_admin_aas_session_handoff_capsule_landed"
)

AAS_SESSION_HANDOFF_CAPSULE_ID = (
    "execution_market.aas.session_handoff_capsule.2026_05_29_0300"
)
AAS_SESSION_HANDOFF_CAPSULE_VERDICT = (
    "session_handoff_capsule_ready_for_read_only_pickup_no_runtime_mutation"
)

SESSION_HANDOFF_CAPSULE_BLOCKED_CLAIMS = [
    *COORDINATION_SUCCESS_METRICS_BLOCKED_CLAIMS,
    *SELECTOR_BLOCKED_CLAIMS,
    "session_handoff_capsule_mutates_irc_runtime_session_manager",
    "session_handoff_capsule_reads_or_replays_raw_transcripts",
    "session_handoff_capsule_writes_live_acontext_memory",
    "session_handoff_capsule_retrieves_live_acontext_memory",
    "session_handoff_capsule_proves_memory_acontext_parity",
    "session_handoff_capsule_authorizes_live_parity_attempt",
    "session_handoff_capsule_authorizes_more_route_layers",
    "session_handoff_capsule_authorizes_customer_copy_delivery_or_publication",
    "session_handoff_capsule_authorizes_public_or_catalog_route",
    "session_handoff_capsule_authorizes_operator_queue_launch_or_dispatch",
    "session_handoff_capsule_authorizes_pricing_or_customer_quote",
    "session_handoff_capsule_authorizes_erc8004_reputation_or_worker_skill_dna",
    "session_handoff_capsule_reverifies_payment_or_production",
    "session_handoff_capsule_allows_exact_gps_or_raw_metadata",
    "session_handoff_capsule_grants_domain_or_emergency_authority",
    "session_handoff_capsule_creates_worker_copyable_doctrine",
]

_FALSE_DERIVED_FLAGS = [
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "mutates_irc_runtime_session_manager",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "writes_municipal_memory",
    "writes_customer_copy",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "reverifies_payment_coverage",
    "reverifies_production_infrastructure",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "runtime_session_manager_mutated",
    "raw_transcript_replay_required",
    "live_acontext_memory_integration_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "one_live_parity_attempt_authorized",
    "more_route_layers_allowed",
    "customer_copy_ready",
    "customer_delivery_ready",
    "publication_ready",
    "public_or_catalog_route_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "pricing_or_customer_quote_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_coverage_reverified_by_this_capsule",
    "production_infrastructure_reverified_by_this_capsule",
    "gps_or_metadata_exposure_allowed",
    "domain_or_emergency_authority_ready",
    "worker_copyable_doctrine_ready",
]


def build_aas_session_handoff_capsule(
    *,
    artifact_dir: str | Path | None = None,
    selector: dict[str, Any] | None = None,
    metrics_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic read-only AAS session handoff capsule."""

    source_selector = selector or load_aas_next_truth_selector(artifact_dir=artifact_dir)
    source_board = metrics_board or load_aas_coordination_observability_success_metrics_board(
        artifact_dir=artifact_dir
    )
    _assert_sources_conservative(source_selector, source_board)

    safe_to_claim = _dedupe(
        [
            *source_selector["claim_boundaries"]["safe_to_claim"],
            *source_board["claim_boundaries"]["safe_to_claim"],
            AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
            AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_selector["claim_boundaries"]["do_not_claim_yet"],
            *source_board["claim_boundaries"]["do_not_claim_yet"],
            *SESSION_HANDOFF_CAPSULE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    capsule = {
        "schema": AAS_SESSION_HANDOFF_CAPSULE_SCHEMA,
        "capsule_id": AAS_SESSION_HANDOFF_CAPSULE_ID,
        "scope": "internal_admin_session_handoff_capsule_only_no_runtime_mutation",
        "source_artifacts": _source_artifacts(source_selector, source_board),
        "derived_from": _derived_from(),
        "access_policy": _access_policy(),
        "readiness": _readiness(),
        "four_id_header": _four_id_header(source_board),
        "session_handoff_capsule": _session_handoff_capsule(source_selector, source_board),
        "integration_survival_checks": _integration_survival_checks(),
        "cross_project_decision_support_card": _cross_project_decision_support_card(
            source_selector
        ),
        "success_metric_assertions": _success_metric_assertions(source_board),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "capsule_verdict": AAS_SESSION_HANDOFF_CAPSULE_VERDICT,
        "operator_instruction": (
            "Use this capsule as the first message/header for later AAS IRC or agent "
            "handoffs. Carry the four IDs, one safe claim, sticky blocked claims, the "
            "selected runtime-prerequisite proof, and the stop condition. Do not reopen "
            "raw transcripts, mutate runtime session state, or promote customer, dispatch, "
            "payment, reputation, Acontext parity, GPS/raw metadata, authority, or worker "
            "doctrine claims."
        ),
    }
    _assert_capsule_conservative(capsule, source_selector, source_board)
    return capsule


def write_aas_session_handoff_capsule(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic AAS session handoff capsule fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    capsule = build_aas_session_handoff_capsule(artifact_dir=base_dir)
    path = base_dir / AAS_SESSION_HANDOFF_CAPSULE_FILENAME
    path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_session_handoff_capsule(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted AAS session handoff capsule fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    capsule = json.loads(
        (base_dir / AAS_SESSION_HANDOFF_CAPSULE_FILENAME).read_text(encoding="utf-8")
    )
    selector = load_aas_next_truth_selector(artifact_dir=base_dir)
    board = load_aas_coordination_observability_success_metrics_board(artifact_dir=base_dir)
    _assert_capsule_conservative(capsule, selector, board)
    if capsule != build_aas_session_handoff_capsule(
        artifact_dir=base_dir, selector=selector, metrics_board=board
    ):
        raise CityOpsContractError("AAS session handoff capsule drifted from source artifacts")
    return capsule


def _source_artifacts(selector: dict[str, Any], board: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "file": AAS_NEXT_TRUTH_SELECTOR_FILENAME,
            "schema": selector["schema"],
            "id": selector["selector_id"],
            "safe_claim": AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
            "digest_sha256": _stable_digest(selector),
        },
        {
            "file": AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
            "schema": board["schema"],
            "id": board["board_id"],
            "safe_claim": AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
            "digest_sha256": _stable_digest(board),
        },
    ]


def _derived_from() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "read_only": True,
        "source_artifacts": [
            AAS_NEXT_TRUTH_SELECTOR_FILENAME,
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
        ],
        "consumes_only": [
            AAS_NEXT_TRUTH_SELECTOR_FILENAME,
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_FILENAME,
        ],
        "forbidden_inputs": [
            "raw_transcripts",
            "unreviewed_memory",
            "private_operator_context",
            "freeform_worker_chat",
            "live_acontext_sink_writes",
            "live_acontext_retrievals",
            "payment_processor_probe",
            "production_health_probe",
            "gps_or_raw_metadata_payloads",
            "customer_copy_drafts",
            "worker_instruction_templates",
        ],
    }
    payload.update({flag: False for flag in _FALSE_DERIVED_FLAGS})
    return payload


def _access_policy() -> dict[str, Any]:
    return {
        "surface": "internal_admin_read_only_capsule",
        "customer_visible": False,
        "worker_visible": False,
        "public_route_registered": False,
        "operator_queue_launched": False,
        "dispatch_enabled": False,
        "network_route_registered": False,
        "writes_live_acontext": False,
        "retrieves_live_acontext": False,
        "gps_or_raw_metadata_release_allowed": False,
        "worker_doctrine_publication_allowed": False,
    }


def _readiness() -> dict[str, bool]:
    payload = {
        "session_handoff_capsule_landed": True,
        "selector_consumed": True,
        "coordination_metrics_board_consumed": True,
        "four_id_header_preserved": True,
        "safe_and_blocked_claims_carried_together": True,
        "selected_next_proof_carried": True,
        "stop_condition_carried": True,
        "runtime_truth_prerequisite_track_preserved": True,
    }
    payload.update({flag: False for flag in _FALSE_READINESS_FLAGS})
    return payload


def _four_id_header(board: dict[str, Any]) -> dict[str, str]:
    return {
        "proof_anchor_id": board["proof_anchor_id"],
        "coordination_session_id": board["coordination_session_id"],
        "compact_decision_id": board["compact_decision_id"],
        "review_packet_id": board["review_packet_id"],
    }


def _session_handoff_capsule(
    selector: dict[str, Any], board: dict[str, Any]
) -> dict[str, Any]:
    header = _four_id_header(board)
    return {
        "format": "four_id_header_plus_claim_boundary_footer",
        "header_lines": [f"{key}: {value}" for key, value in header.items()],
        "resume_summary": (
            "AAS coordination structure is sufficient. The next useful move is not "
            "another route layer; it is the runtime prerequisite path selected by the "
            "next-truth selector."
        ),
        "safe_claim_to_carry": AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM,
        "source_safe_claims_to_carry": [
            AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
            AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SAFE_CLAIM,
        ],
        "sticky_blocked_claim_footer": [
            "live_acontext_memory_integration_ready",
            "runtime_parity_proven",
            "irc_session_manager_runtime_enhanced",
            "cross_project_decision_support_customer_ready",
            "agent_observability_live_dashboard_ready",
            "customer_copy_ready",
            "public_or_catalog_route_ready",
            "dispatch_ready",
            "payment_or_production_reverified",
            "erc8004_reputation_ready",
            "worker_skill_dna_ready",
            "exact_gps_or_raw_metadata_release_allowed",
            "worker_copyable_doctrine_ready",
        ],
        "selected_next_track": selector["selected_next_track"],
        "selected_next_proof": selector["selected_next_proof"],
        "one_next_proof_slot": {
            "track": SELECTED_NEXT_TRACK,
            "proof": SELECTED_NEXT_PROOF,
            "authorizes_live_attempt_now": False,
            "requires_empty_readiness_gate_first": True,
        },
        "stop_condition": (
            "Stop if Docker/Acontext prerequisites are still blocked or if no separate "
            "human/operator decision artifact exists; record a blocker observation only."
        ),
        "board_metric_to_watch": "claim_boundary_survival_rate",
    }


def _integration_survival_checks() -> list[dict[str, Any]]:
    return [
        {
            "check": "memory_system_to_acontext",
            "must_survive": ["safe_to_claim", "do_not_claim_yet", "selected_next_proof"],
            "live_runtime_required_before_promotion": True,
            "observed_here": "capsule_shape_only",
        },
        {
            "check": "irc_session_management",
            "must_survive": ["four_id_header", "stop_condition", "sticky_blocked_claim_footer"],
            "runtime_manager_mutated_here": False,
            "observed_here": "read_only_capsule",
        },
        {
            "check": "cross_project_decision_support",
            "must_survive": ["declared_vs_verified_boundary", "one_next_proof_slot"],
            "customer_or_public_route_authorized_here": False,
            "observed_here": "internal_admin_comparison_input",
        },
        {
            "check": "agent_observability_success_metrics",
            "must_survive": ["claim_boundary_survival_rate", "four_id_completeness_rate"],
            "live_dashboard_authorized_here": False,
            "observed_here": "metric_assertion_shape",
        },
    ]


def _cross_project_decision_support_card(selector: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "prefer_runtime_truth_prerequisite_activation_over_more_route_layers",
        "selected_next_track": selector["selected_next_track"],
        "selected_next_proof": selector["selected_next_proof"],
        "comparison_policy": [
            "choose the narrowest proof that reduces runtime uncertainty",
            "do not treat declared payment or infrastructure context as current verification",
            "do not turn cross-family comparison into customer launch doctrine",
            "preserve blocked claims beside every reusable decision object",
        ],
        "customer_launch_readiness": False,
        "autonomous_prioritization_ready": False,
    }


def _success_metric_assertions(board: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric": "aas_handoff_four_id_completeness_rate",
            "observed": True,
            "source": board["board_id"],
            "customer_visible": False,
        },
        {
            "metric": "aas_claim_boundary_survival_rate",
            "observed": True,
            "source": board["board_id"],
            "customer_visible": False,
        },
        {
            "metric": "aas_one_next_proof_slot_survival_rate",
            "observed": True,
            "source": board["board_id"],
            "customer_visible": False,
        },
        {
            "metric": "aas_memory_candidate_retrieval_parity_rate",
            "observed": False,
            "blocked_by": "live_acontext_runtime_parity_not_proven",
            "customer_visible": False,
        },
    ]


def _assert_sources_conservative(selector: dict[str, Any], board: dict[str, Any]) -> None:
    if selector.get("schema") != AAS_NEXT_TRUTH_SELECTOR_SCHEMA:
        raise CityOpsContractError("invalid AAS next-truth selector schema")
    if board.get("schema") != AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_SCHEMA:
        raise CityOpsContractError("invalid AAS coordination metrics board schema")
    if selector.get("selected_next_track") != SELECTED_NEXT_TRACK:
        raise CityOpsContractError("selector selected unexpected next track")
    if selector.get("selected_next_proof") != SELECTED_NEXT_PROOF:
        raise CityOpsContractError("selector selected unexpected next proof")
    if selector.get("readiness", {}).get("more_route_layers_allowed") is not False:
        raise CityOpsContractError("selector promoted forbidden flag: more_route_layers_allowed")
    if selector.get("readiness", {}).get("live_acontext_write_allowed") is not False:
        raise CityOpsContractError("selector promoted forbidden flag: live_acontext_write_allowed")
    if selector.get("readiness", {}).get("runtime_parity_proven") is not False:
        raise CityOpsContractError("selector promoted forbidden flag: runtime_parity_proven")
    for flag in [
        "live_acontext_memory_integration_ready",
        "agent_observability_live_dashboard_ready",
        "success_metrics_public_or_customer_visible",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
    ]:
        if board.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"metrics board promoted forbidden flag: {flag}")


def _assert_capsule_conservative(
    capsule: dict[str, Any], selector: dict[str, Any], board: dict[str, Any]
) -> None:
    _assert_sources_conservative(selector, board)
    if capsule.get("schema") != AAS_SESSION_HANDOFF_CAPSULE_SCHEMA:
        raise CityOpsContractError("invalid AAS session handoff capsule schema")
    if capsule.get("capsule_verdict") != AAS_SESSION_HANDOFF_CAPSULE_VERDICT:
        raise CityOpsContractError("unexpected AAS session handoff capsule verdict")
    if capsule.get("four_id_header") != _four_id_header(board):
        raise CityOpsContractError("AAS session handoff capsule four-ID header drifted")
    if capsule.get("session_handoff_capsule", {}).get("selected_next_track") != SELECTED_NEXT_TRACK:
        raise CityOpsContractError("AAS session handoff capsule lost selected next track")
    if capsule.get("session_handoff_capsule", {}).get("selected_next_proof") != SELECTED_NEXT_PROOF:
        raise CityOpsContractError("AAS session handoff capsule lost selected next proof")
    for section in ["derived_from", "access_policy", "readiness"]:
        for key, value in capsule.get(section, {}).items():
            if key in _FALSE_DERIVED_FLAGS + _FALSE_READINESS_FLAGS and value is not False:
                raise CityOpsContractError(f"AAS session capsule promoted forbidden flag: {key}")
    if capsule["readiness"].get("session_handoff_capsule_landed") is not True:
        raise CityOpsContractError("AAS session handoff capsule not marked landed")
    _assert_claim_boundaries(
        capsule["claim_boundaries"]["safe_to_claim"],
        capsule["claim_boundaries"]["do_not_claim_yet"],
    )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS session handoff capsule claim overlap: {sorted(overlap)}"
        )
    if AAS_SESSION_HANDOFF_CAPSULE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("AAS session handoff capsule safe claim missing")
    for blocked in [
        "session_handoff_capsule_mutates_irc_runtime_session_manager",
        "session_handoff_capsule_proves_memory_acontext_parity",
        "session_handoff_capsule_authorizes_public_or_catalog_route",
        "session_handoff_capsule_authorizes_erc8004_reputation_or_worker_skill_dna",
        "session_handoff_capsule_allows_exact_gps_or_raw_metadata",
        "session_handoff_capsule_creates_worker_copyable_doctrine",
    ]:
        if blocked not in do_not_claim_yet:
            raise CityOpsContractError(f"AAS session handoff capsule missing blocked claim: {blocked}")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
