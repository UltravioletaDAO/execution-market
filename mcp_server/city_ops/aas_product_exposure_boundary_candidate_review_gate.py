"""Internal/admin AAS product-exposure boundary candidate review gate.

This module is the June 2 no-answer product fork: it selects exactly one
existing AAS product-exposure boundary candidate for human review while keeping
all launch/exposure/runtime/payment claims blocked.  It consumes only the
product-fork pause board plus the Retail Reality product-exposure boundary
packet, records no operator answer or approval, creates no customer/public/
worker surface, and leaves every runtime adapter/session-manager path default-
off and non-authorizing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_product_fork_no_answer_pause_board import (
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME,
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM,
    AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SCHEMA,
    DEFAULT_DECISION,
    PAUSE_BLOCKED_CLAIMS,
    PAUSE_BOARD_ID,
    PAUSE_BOARD_STATUS,
    PAUSE_FALSE_FLAGS,
    RUNTIME_DECISION,
    load_aas_product_fork_no_answer_pause_board,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError
from .retail_reality_product_exposure_boundary_packet import (
    PACKET_BLOCKED_CLAIMS,
    PACKET_FALSE_FLAGS,
    PACKET_ID,
    PACKET_STATUS,
    PRODUCT_EXPOSURE_BOUNDARY_KEY,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA,
    load_retail_reality_product_exposure_boundary_packet,
)

AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA = (
    "city_ops.aas_product_exposure_boundary_candidate_review_gate.v1"
)
AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME = (
    "aas_product_exposure_boundary_candidate_review_gate.json"
)
AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM = (
    "internal_admin_aas_product_exposure_boundary_candidate_review_gate_landed"
)

GATE_ID = "execution_market.aas.product_exposure_boundary_candidate_review_gate.2026_06_02_0700"
SCOPE = "internal_admin_one_aas_product_exposure_boundary_candidate_human_review_only"
GATE_STATUS = "one_boundary_candidate_selected_for_human_review_not_answered_not_approved_not_exposed"
SOURCE_POLICY = "consume_only_pause_board_and_retail_boundary_packet_json"
DEFAULT_POSTURE = "default_off_non_authorizing_human_review_candidate_only"
SELECTED_CANDIDATE_KEY = "retail_reality_product_exposure_boundary_human_review_candidate"
SELECTED_FAMILY_ID = "retail_reality_as_a_service"
SELECTED_OFFER_ID = "storefront_hours_availability_check"
HUMAN_REVIEW_QUESTION = (
    "Should this single Retail Reality product-exposure boundary remain held, "
    "or should a separate explicit human/operator approval-or-hold answer be "
    "recorded later?"
)

GATE_FALSE_FLAGS = {
    "human_operator_answer_recorded": False,
    "human_operator_approval_recorded": False,
    "operator_answer_inferred_from_pause_board": False,
    "operator_answer_inferred_from_boundary_packet": False,
    "operator_approval_inferred_from_selection": False,
    "candidate_selected_for_approval": False,
    "candidate_boundary_approved": False,
    "product_exposure_approved": False,
    "design_only_wiring_selected": False,
    "bounded_activation_execution_selected": False,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "live_acontext_write_or_retrieval_enabled": False,
    "cross_project_autorouting_enabled": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "customer_delivery_approved": False,
    "publication_approved": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "public_or_catalog_route_ready": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "public_price_approved": False,
    "customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_enabled": False,
    "autonomous_dispatch_ready": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "worker_copyable_doctrine_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_allowed": False,
    "private_context_release_allowed": False,
    "domain_authority_claims_allowed": False,
    "stopped_project_integration_ready": False,
}

ACCESS_FALSE_FLAGS = {
    "network_route_registered": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "public_visible": False,
    "worker_visible": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "dispatch_enabled": False,
    "writes_customer_copy": False,
    "writes_catalog_copy": False,
    "writes_pricing_quote": False,
    "writes_dispatch_instructions": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "mutates_runtime_adapter_or_session_manager": False,
    "emits_reputation_receipts": False,
    "publishes_worker_doctrine": False,
    "exposes_exact_gps_or_raw_metadata": False,
    "exposes_private_context": False,
}

GATE_BLOCKED_CLAIMS = [
    *PAUSE_BLOCKED_CLAIMS,
    *PACKET_BLOCKED_CLAIMS,
    "product_exposure_candidate_gate_records_operator_answer",
    "product_exposure_candidate_gate_records_operator_approval",
    "product_exposure_candidate_gate_infers_approval_from_selection",
    "product_exposure_candidate_gate_approves_retail_reality_boundary",
    "product_exposure_candidate_gate_selects_design_only_wiring",
    "product_exposure_candidate_gate_executes_bounded_activation",
    "product_exposure_candidate_gate_registers_or_enables_runtime_adapter",
    "product_exposure_candidate_gate_mutates_irc_session_manager",
    "product_exposure_candidate_gate_writes_or_retrieves_live_acontext",
    "product_exposure_candidate_gate_authorizes_cross_project_autorouting",
    "product_exposure_candidate_gate_creates_customer_public_or_worker_surface",
    "product_exposure_candidate_gate_creates_customer_copy_or_delivery",
    "product_exposure_candidate_gate_registers_public_catalog_or_pricing_route",
    "product_exposure_candidate_gate_authorizes_queue_launch_or_dispatch",
    "product_exposure_candidate_gate_emits_erc8004_reputation_or_worker_skill_dna",
    "product_exposure_candidate_gate_reverifies_payment_or_production",
    "product_exposure_candidate_gate_releases_exact_gps_or_raw_metadata",
    "product_exposure_candidate_gate_releases_private_context",
    "product_exposure_candidate_gate_grants_domain_authority_claims",
    "product_exposure_candidate_gate_creates_worker_copyable_doctrine",
    "product_exposure_candidate_gate_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(GATE_BLOCKED_CLAIMS) | {
    "human_answer_recorded",
    "human_approval_recorded",
    "operator_approved",
    "candidate_approved",
    "retail_reality_approved",
    "product_exposure_approved",
    "selected_boundary_approved",
    "design_only_wiring_selected",
    "bounded_activation_executed",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "cross_project_autorouting_ready",
    "customer_copy_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "catalog_visible",
    "pricing_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}



def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()



def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out



def _assert_pause_board_source(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SCHEMA:
        raise CityOpsContractError("product exposure candidate gate pause source schema drift")
    if board.get("pause_board_id") != PAUSE_BOARD_ID:
        raise CityOpsContractError("product exposure candidate gate pause source id drift")
    if board.get("pause_board_status") != PAUSE_BOARD_STATUS:
        raise CityOpsContractError("product exposure candidate gate pause source promoted")
    if board.get("default_decision") != DEFAULT_DECISION:
        raise CityOpsContractError("product exposure candidate gate pause default drift")
    if board.get("runtime_decision") != RUNTIME_DECISION:
        raise CityOpsContractError("product exposure candidate gate runtime decision drift")
    if AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM not in board.get("safe_to_claim", []):
        raise CityOpsContractError("product exposure candidate gate pause safe claim missing")
    forbidden_safe = set(board.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"product exposure candidate gate pause source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PAUSE_BLOCKED_CLAIMS) - set(board.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"product exposure candidate gate pause source missing blocked claims: {sorted(missing_blocked)}"
        )
    if board.get("no_answer_state", {}).get("explicit_human_operator_answer_present") is not False:
        raise CityOpsContractError("product exposure candidate gate pause source records answer")
    if board.get("no_answer_state", {}).get("human_operator_approval_record_present") is not False:
        raise CityOpsContractError("product exposure candidate gate pause source records approval")
    if board.get("no_answer_state", {}).get("retail_reality_is_closest_review_candidate") is not True:
        raise CityOpsContractError("product exposure candidate gate pause source retail candidate drift")
    for flag, expected in PAUSE_FALSE_FLAGS.items():
        if board.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"product exposure candidate gate pause source readiness promoted {flag}"
            )
    rows = board.get("product_family_pause_rows", [])
    if len(rows) != 5:
        raise CityOpsContractError("product exposure candidate gate pause source row count drift")
    retail_rows = [row for row in rows if row.get("family_id") == SELECTED_FAMILY_ID]
    if len(retail_rows) != 1:
        raise CityOpsContractError("product exposure candidate gate must have one retail source row")
    retail_row = retail_rows[0]
    if retail_row.get("rank") != 1:
        raise CityOpsContractError("product exposure candidate gate retail source rank drift")
    for flag in [
        "explicit_human_answer_present",
        "approval_record_present",
        "customer_or_public_surface_allowed",
        "this_pause_board_approves_family",
        "customer_delivery_authorized",
        "publication_authorized",
        "public_or_catalog_route_ready",
        "pricing_or_customer_quote_ready",
        "queue_or_dispatch_ready",
        "reputation_attachment_ready",
        "live_acontext_runtime_parity",
        "exact_gps_or_raw_metadata_release_allowed",
        "worker_copyable_doctrine_ready",
    ]:
        if retail_row.get(flag) is not False:
            raise CityOpsContractError(
                f"product exposure candidate gate retail source row promoted {flag}"
            )



def _assert_boundary_packet_source(packet: dict[str, Any]) -> None:
    if packet.get("schema") != RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA:
        raise CityOpsContractError("product exposure candidate gate boundary source schema drift")
    if packet.get("packet_id") != PACKET_ID:
        raise CityOpsContractError("product exposure candidate gate boundary source id drift")
    if packet.get("packet_status") != PACKET_STATUS:
        raise CityOpsContractError("product exposure candidate gate boundary source promoted")
    if packet.get("product_exposure_boundary_key") != PRODUCT_EXPOSURE_BOUNDARY_KEY:
        raise CityOpsContractError("product exposure candidate gate boundary key drift")
    if RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("product exposure candidate gate boundary safe claim missing")
    safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"product exposure candidate gate boundary source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(PACKET_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"product exposure candidate gate boundary source missing blocked claims: {sorted(missing_blocked)}"
        )
    if packet.get("candidate_count") != 1 or len(packet.get("aas_candidates", [])) != 1:
        raise CityOpsContractError("product exposure candidate gate boundary source candidate count drift")
    candidate = packet["aas_candidates"][0]
    if candidate.get("candidate_key") != SELECTED_FAMILY_ID:
        raise CityOpsContractError("product exposure candidate gate boundary candidate drift")
    if candidate.get("offer_id") != SELECTED_OFFER_ID:
        raise CityOpsContractError("product exposure candidate gate boundary offer drift")
    for key in [
        "candidate_text_values_visible",
        "authorized_delivery_path_recorded",
    ]:
        if candidate.get(key) is not False:
            raise CityOpsContractError(
                f"product exposure candidate gate boundary candidate promoted {key}"
            )
    for flag, expected in PACKET_FALSE_FLAGS.items():
        if packet.get(flag) is not expected:
            raise CityOpsContractError(
                f"product exposure candidate gate boundary source promoted {flag}"
            )
        if packet.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"product exposure candidate gate boundary source readiness promoted {flag}"
            )



def _selected_candidate(boundary_packet: dict[str, Any]) -> dict[str, Any]:
    candidate = boundary_packet["aas_candidates"][0]
    return {
        "selection_key": SELECTED_CANDIDATE_KEY,
        "candidate_key": candidate["candidate_key"],
        "package_family_id": candidate["package_family_id"],
        "offer_id": candidate["offer_id"],
        "source_boundary_packet_id": boundary_packet["packet_id"],
        "source_boundary_packet_digest_sha256": _stable_digest(boundary_packet),
        "product_exposure_boundary_key": boundary_packet["product_exposure_boundary_key"],
        "selected_text_boundary_key": candidate["selected_text_boundary_key"],
        "selected_text_boundary_digest_sha256": candidate["selected_text_boundary_digest_sha256"],
        "candidate_text_field_names": list(candidate["candidate_text_field_names"]),
        "candidate_text_values_visible": False,
        "human_review_status": "pending_human_review_not_answered_not_approved",
        "selection_purpose": "human_review_candidate_only",
        "default_posture": DEFAULT_POSTURE,
        "selected_for_human_review": True,
        "selected_for_approval": False,
        "approval_recorded_here": False,
        "customer_or_public_exposure_allowed": False,
        "worker_surface_allowed": False,
        "pricing_queue_dispatch_allowed": False,
        "runtime_mutation_allowed": False,
        "human_review_question": HUMAN_REVIEW_QUESTION,
    }



def build_aas_product_exposure_boundary_candidate_review_gate(
    *,
    artifact_dir: str | Path | None = None,
    pause_board: dict[str, Any] | None = None,
    boundary_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin one-candidate review gate."""

    source_pause = pause_board or load_aas_product_fork_no_answer_pause_board(
        artifact_dir=artifact_dir
    )
    source_boundary = boundary_packet or load_retail_reality_product_exposure_boundary_packet(
        artifact_dir=artifact_dir
    )
    _assert_pause_board_source(source_pause)
    _assert_boundary_packet_source(source_boundary)

    safe_to_claim = _dedupe(
        [
            AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM,
            RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
            AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_pause["do_not_claim_yet"],
            *source_boundary["claim_boundaries"]["do_not_claim_yet"],
            *GATE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    candidate = _selected_candidate(source_boundary)

    gate: dict[str, Any] = {
        "schema": AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA,
        "gate_id": GATE_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "gate_status": GATE_STATUS,
        "default_posture": DEFAULT_POSTURE,
        "candidate_count": 1,
        "selected_candidates": [candidate],
        "source_artifacts": {
            "product_fork_no_answer_pause_board": {
                "file": AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME,
                "schema": source_pause["schema"],
                "id": source_pause["pause_board_id"],
                "safe_claim": AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source_pause),
                "default_decision": source_pause["default_decision"],
                "runtime_decision": source_pause["runtime_decision"],
            },
            "retail_reality_product_exposure_boundary_packet": {
                "file": RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME,
                "schema": source_boundary["schema"],
                "id": source_boundary["packet_id"],
                "safe_claim": RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source_boundary),
            },
        },
        "no_answer_state": {
            "explicit_human_operator_answer_present": False,
            "human_operator_approval_record_present": False,
            "approval_can_be_inferred_from_candidate_selection": False,
            "default_if_no_human_answer": DEFAULT_DECISION,
            "runtime_decision_preserved": RUNTIME_DECISION,
        },
        "selection_contract": {
            "exactly_one_candidate_selected_for_human_review": True,
            "selected_family_id": SELECTED_FAMILY_ID,
            "selected_offer_id": SELECTED_OFFER_ID,
            "selection_is_approval": False,
            "selection_is_customer_copy": False,
            "selection_is_public_catalog_or_pricing_surface": False,
            "selection_is_worker_surface": False,
            "selection_is_runtime_mutation": False,
            "selection_is_payment_or_production_reverification": False,
            "selection_uses_stopped_project_inputs": False,
        },
        "access_policy": {
            "surface": "internal_admin_only",
            "audience": "human_operator_review_only",
            "requires_admin_context": True,
            "default_off": True,
            "non_authorizing": True,
            **ACCESS_FALSE_FLAGS,
        },
        "allowed_without_human_answer": [
            "keep_candidate_selection_internal_admin_only",
            "show_digest_only_candidate_card_to_internal_admins",
            "wait_for_separate_explicit_operator_answer_or_keep_held",
        ],
        "forbidden_shortcuts": [
            "do_not_record_operator_answer_or_approval",
            "do_not_infer_approval_from_candidate_selection",
            "do_not_select_design_only_wiring",
            "do_not_execute_bounded_activation",
            "do_not_register_or_enable_runtime_adapter",
            "do_not_mutate_irc_session_manager",
            "do_not_write_or_retrieve_live_acontext",
            "do_not_enable_cross_project_autorouting",
            "do_not_create_customer_public_or_worker_surfaces",
            "do_not_create_catalog_pricing_queue_dispatch_reputation_or_worker_skill_dna",
            "do_not_reverify_payment_or_production",
            "do_not_release_exact_gps_raw_metadata_private_context_or_authority_claims",
            "do_not_integrate_stopped_projects",
        ],
        "readiness": {
            "internal_admin_gate_landed": True,
            "source_pause_board_verified": True,
            "source_boundary_packet_verified": True,
            "exactly_one_candidate_selected_for_human_review": True,
            "default_off_non_authorizing": True,
            **GATE_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "still_blocked_claims": do_not_claim_yet,
        "blocked_claim_regression_count": len(do_not_claim_yet),
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "gate_verdict": (
            "one_retail_reality_product_exposure_boundary_candidate_selected_for_internal_"
            "human_review_only_no_answer_no_approval_no_exposure_no_runtime_mutation"
        ),
    }
    _assert_candidate_review_gate(gate, source_pause=source_pause, source_boundary=source_boundary)
    return gate



def write_aas_product_exposure_boundary_candidate_review_gate(
    artifact_dir: str | Path | None = None,
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=target_dir)
    target_path = target_dir / AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME
    target_path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path



def load_aas_product_exposure_boundary_candidate_review_gate(
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME
    gate = json.loads(path.read_text(encoding="utf-8"))
    source_pause = load_aas_product_fork_no_answer_pause_board(artifact_dir=source_dir)
    source_boundary = load_retail_reality_product_exposure_boundary_packet(artifact_dir=source_dir)
    _assert_candidate_review_gate(
        gate,
        source_pause=source_pause,
        source_boundary=source_boundary,
    )
    return gate



def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"product exposure candidate gate claim overlap: {sorted(overlap)}"
        )
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"product exposure candidate gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(GATE_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"product exposure candidate gate missing blocked claims: {sorted(missing_blocked)}"
        )



def _assert_candidate_review_gate(
    gate: dict[str, Any],
    *,
    source_pause: dict[str, Any],
    source_boundary: dict[str, Any],
) -> None:
    _assert_pause_board_source(source_pause)
    _assert_boundary_packet_source(source_boundary)
    if gate.get("schema") != AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("product exposure candidate gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("product exposure candidate gate id drift")
    if gate.get("scope") != SCOPE:
        raise CityOpsContractError("product exposure candidate gate scope drift")
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("product exposure candidate gate status promoted")
    if gate.get("default_posture") != DEFAULT_POSTURE:
        raise CityOpsContractError("product exposure candidate gate default posture drift")
    if gate.get("candidate_count") != 1 or len(gate.get("selected_candidates", [])) != 1:
        raise CityOpsContractError("product exposure candidate gate must select exactly one candidate")
    expected_candidate = _selected_candidate(source_boundary)
    if gate["selected_candidates"][0] != expected_candidate:
        raise CityOpsContractError("product exposure candidate gate selected candidate drift")

    sources = gate.get("source_artifacts", {})
    pause_source = sources.get("product_fork_no_answer_pause_board", {})
    if pause_source.get("file") != AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME:
        raise CityOpsContractError("product exposure candidate gate pause source file drift")
    if pause_source.get("digest_sha256") != _stable_digest(source_pause):
        raise CityOpsContractError("product exposure candidate gate pause source digest drift")
    boundary_source = sources.get("retail_reality_product_exposure_boundary_packet", {})
    if boundary_source.get("file") != RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME:
        raise CityOpsContractError("product exposure candidate gate boundary source file drift")
    if boundary_source.get("digest_sha256") != _stable_digest(source_boundary):
        raise CityOpsContractError("product exposure candidate gate boundary source digest drift")

    no_answer = gate.get("no_answer_state", {})
    for key in [
        "explicit_human_operator_answer_present",
        "human_operator_approval_record_present",
        "approval_can_be_inferred_from_candidate_selection",
    ]:
        if no_answer.get(key) is not False:
            raise CityOpsContractError(f"product exposure candidate gate no-answer promoted {key}")
    if no_answer.get("default_if_no_human_answer") != DEFAULT_DECISION:
        raise CityOpsContractError("product exposure candidate gate no-answer default drift")
    if no_answer.get("runtime_decision_preserved") != RUNTIME_DECISION:
        raise CityOpsContractError("product exposure candidate gate runtime hold drift")

    selection_contract = gate.get("selection_contract", {})
    if selection_contract.get("exactly_one_candidate_selected_for_human_review") is not True:
        raise CityOpsContractError("product exposure candidate gate selection contract lost one candidate")
    if selection_contract.get("selected_family_id") != SELECTED_FAMILY_ID:
        raise CityOpsContractError("product exposure candidate gate selected family drift")
    if selection_contract.get("selected_offer_id") != SELECTED_OFFER_ID:
        raise CityOpsContractError("product exposure candidate gate selected offer drift")
    for key, value in selection_contract.items():
        if key in {
            "exactly_one_candidate_selected_for_human_review",
            "selected_family_id",
            "selected_offer_id",
        }:
            continue
        if value is not False:
            raise CityOpsContractError(
                f"product exposure candidate gate selection contract promoted {key}"
            )

    access = gate.get("access_policy", {})
    if access.get("surface") != "internal_admin_only":
        raise CityOpsContractError("product exposure candidate gate access surface drift")
    if access.get("audience") != "human_operator_review_only":
        raise CityOpsContractError("product exposure candidate gate audience drift")
    if access.get("default_off") is not True or access.get("non_authorizing") is not True:
        raise CityOpsContractError("product exposure candidate gate lost default-off posture")
    for flag, expected in ACCESS_FALSE_FLAGS.items():
        if access.get(flag) is not expected:
            raise CityOpsContractError(
                f"product exposure candidate gate access promoted {flag}"
            )

    readiness = gate.get("readiness", {})
    for flag in [
        "internal_admin_gate_landed",
        "source_pause_board_verified",
        "source_boundary_packet_verified",
        "exactly_one_candidate_selected_for_human_review",
        "default_off_non_authorizing",
    ]:
        if readiness.get(flag) is not True:
            raise CityOpsContractError(f"product exposure candidate gate lost readiness {flag}")
    for flag, expected in GATE_FALSE_FLAGS.items():
        if readiness.get(flag) is not expected:
            raise CityOpsContractError(
                f"product exposure candidate gate readiness promoted {flag}"
            )

    boundaries = gate.get("claim_boundaries", {})
    _assert_claim_boundaries(
        boundaries.get("safe_to_claim", []),
        boundaries.get("do_not_claim_yet", []),
    )
    if gate.get("still_blocked_claims") != boundaries.get("do_not_claim_yet"):
        raise CityOpsContractError("product exposure candidate gate blocked claims drift")

    firewall = gate.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(
                f"product exposure candidate gate stopped project firewall promoted {key}"
            )
