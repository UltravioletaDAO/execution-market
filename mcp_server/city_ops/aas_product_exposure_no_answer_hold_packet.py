"""Internal/admin AAS product-exposure no-answer hold packet.

This proof slice consumes the latest one-candidate product-exposure review gate
and the Retail Reality hold regression guard. It cross-checks that both sources
refer to the same digest-only boundary while preserving the no-answer default:
no human/operator answer, approval, customer/public/catalog exposure, pricing,
queue, dispatch, reputation, Worker Skill DNA, runtime mutation, payment proof,
GPS/raw metadata release, private-context release, authority claim, or stopped-
project integration is authorized.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_product_exposure_boundary_candidate_review_gate import (
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME,
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA,
    DEFAULT_POSTURE,
    GATE_BLOCKED_CLAIMS,
    GATE_FALSE_FLAGS,
    GATE_ID,
    GATE_STATUS,
    SELECTED_CANDIDATE_KEY,
    SELECTED_FAMILY_ID,
    SELECTED_OFFER_ID,
    load_aas_product_exposure_boundary_candidate_review_gate,
)
from .aas_product_fork_no_answer_pause_board import DEFAULT_DECISION, RUNTIME_DECISION
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError
from .retail_reality_product_exposure_hold_regression_guard import (
    GUARD_BLOCKED_CLAIMS,
    GUARD_FALSE_FLAGS,
    GUARD_ID,
    GUARD_STATUS,
    NEXT_ALLOWED_MOVE as HOLD_GUARD_NEXT_ALLOWED_MOVE,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA,
    load_retail_reality_product_exposure_hold_regression_guard,
)

AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SCHEMA = (
    "city_ops.aas_product_exposure_no_answer_hold_packet.v1"
)
AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_FILENAME = (
    "aas_product_exposure_no_answer_hold_packet.json"
)
AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SAFE_CLAIM = (
    "internal_admin_aas_product_exposure_no_answer_hold_packet_landed"
)

PACKET_ID = "execution_market.aas.product_exposure_no_answer_hold_packet.2026_06_02_2200"
SCOPE = "internal_admin_product_exposure_no_answer_hold_packet_digest_cross_check_only"
PACKET_STATUS = "no_answer_hold_packet_landed_no_approval_no_exposure_no_runtime_mutation"
SOURCE_POLICY = "consume_only_candidate_review_gate_and_retail_hold_guard_json"
PACKET_VERDICT = (
    "candidate_gate_and_hold_guard_reference_same_digest_only_boundary_while_default_hold_remains"
)
NEXT_ALLOWED_MOVE = "wait_for_explicit_human_operator_answer_or_keep_product_exposure_held"

PACKET_FALSE_FLAGS = {
    "human_operator_answer_recorded": False,
    "human_operator_approval_recorded": False,
    "approval_inferred_from_digest_match": False,
    "hold_packet_is_operator_answer": False,
    "selected_boundary_approved": False,
    "product_exposure_approved": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "customer_delivery_approved": False,
    "publication_approved": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_enabled": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "live_acontext_write_or_retrieval_enabled": False,
    "cross_project_autorouting_enabled": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_allowed": False,
    "private_context_release_allowed": False,
    "domain_authority_claims_allowed": False,
    "worker_copyable_doctrine_ready": False,
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

PACKET_BLOCKED_CLAIMS = [
    *GATE_BLOCKED_CLAIMS,
    *GUARD_BLOCKED_CLAIMS,
    "product_exposure_no_answer_hold_packet_records_operator_answer",
    "product_exposure_no_answer_hold_packet_records_operator_approval",
    "product_exposure_no_answer_hold_packet_treats_digest_match_as_approval",
    "product_exposure_no_answer_hold_packet_approves_selected_boundary",
    "product_exposure_no_answer_hold_packet_creates_hold_or_approval_record",
    "product_exposure_no_answer_hold_packet_creates_customer_copy_or_delivery",
    "product_exposure_no_answer_hold_packet_registers_public_catalog_or_pricing_route",
    "product_exposure_no_answer_hold_packet_authorizes_queue_launch_or_dispatch",
    "product_exposure_no_answer_hold_packet_emits_erc8004_reputation_or_worker_skill_dna",
    "product_exposure_no_answer_hold_packet_registers_or_enables_runtime_adapter",
    "product_exposure_no_answer_hold_packet_mutates_irc_session_manager",
    "product_exposure_no_answer_hold_packet_writes_or_retrieves_live_acontext",
    "product_exposure_no_answer_hold_packet_authorizes_cross_project_autorouting",
    "product_exposure_no_answer_hold_packet_reverifies_payment_or_production",
    "product_exposure_no_answer_hold_packet_releases_exact_gps_or_raw_metadata",
    "product_exposure_no_answer_hold_packet_releases_private_context",
    "product_exposure_no_answer_hold_packet_grants_domain_authority_claims",
    "product_exposure_no_answer_hold_packet_creates_worker_copyable_doctrine",
    "product_exposure_no_answer_hold_packet_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(PACKET_BLOCKED_CLAIMS) | {
    "human_answer_recorded",
    "human_approval_recorded",
    "operator_approved",
    "digest_match_approved",
    "selected_boundary_approved",
    "product_exposure_approved",
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
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "cross_project_autorouting_ready",
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


def _selected_candidate(gate: dict[str, Any]) -> dict[str, Any]:
    candidates = gate.get("selected_candidates", [])
    if len(candidates) != 1:
        raise CityOpsContractError("product exposure no-answer hold packet source candidate count drift")
    return candidates[0]


def _assert_candidate_gate_source(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("product exposure no-answer hold packet candidate source schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("product exposure no-answer hold packet candidate source id drift")
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("product exposure no-answer hold packet candidate source promoted")
    if gate.get("default_posture") != DEFAULT_POSTURE:
        raise CityOpsContractError("product exposure no-answer hold packet candidate default posture drift")
    if AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM not in gate.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("product exposure no-answer hold packet candidate safe claim missing")

    safe = set(gate.get("claim_boundaries", {}).get("safe_to_claim", []))
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"product exposure no-answer hold packet candidate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(gate.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(GATE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"product exposure no-answer hold packet candidate missing blocked claims: {sorted(missing_blocked)}"
        )
    if gate.get("still_blocked_claims") != gate.get("claim_boundaries", {}).get("do_not_claim_yet"):
        raise CityOpsContractError("product exposure no-answer hold packet candidate blocked claims drift")

    no_answer = gate.get("no_answer_state", {})
    for key in [
        "explicit_human_operator_answer_present",
        "human_operator_approval_record_present",
        "approval_can_be_inferred_from_candidate_selection",
    ]:
        if no_answer.get(key) is not False:
            raise CityOpsContractError(f"product exposure no-answer hold packet candidate promoted {key}")
    if no_answer.get("default_if_no_human_answer") != DEFAULT_DECISION:
        raise CityOpsContractError("product exposure no-answer hold packet no-answer default drift")
    if no_answer.get("runtime_decision_preserved") != RUNTIME_DECISION:
        raise CityOpsContractError("product exposure no-answer hold packet runtime hold drift")

    candidate = _selected_candidate(gate)
    expected_candidate_fields = {
        "selection_key": SELECTED_CANDIDATE_KEY,
        "candidate_key": SELECTED_FAMILY_ID,
        "package_family_id": SELECTED_FAMILY_ID,
        "offer_id": SELECTED_OFFER_ID,
        "selected_for_human_review": True,
        "selection_purpose": "human_review_candidate_only",
        "default_posture": DEFAULT_POSTURE,
        "selected_for_approval": False,
        "approval_recorded_here": False,
        "customer_or_public_exposure_allowed": False,
        "worker_surface_allowed": False,
        "pricing_queue_dispatch_allowed": False,
        "runtime_mutation_allowed": False,
        "candidate_text_values_visible": False,
    }
    for key, expected in expected_candidate_fields.items():
        if candidate.get(key) != expected:
            raise CityOpsContractError(f"product exposure no-answer hold packet candidate field drift {key}")

    selection = gate.get("selection_contract", {})
    if selection.get("exactly_one_candidate_selected_for_human_review") is not True:
        raise CityOpsContractError("product exposure no-answer hold packet source lost one-candidate contract")
    for key, value in selection.items():
        if key in {"exactly_one_candidate_selected_for_human_review", "selected_family_id", "selected_offer_id"}:
            continue
        if value is not False:
            raise CityOpsContractError(
                f"product exposure no-answer hold packet source selection promoted {key}"
            )

    access = gate.get("access_policy", {})
    if access.get("surface") != "internal_admin_only" or access.get("default_off") is not True:
        raise CityOpsContractError("product exposure no-answer hold packet source access drift")
    for flag, expected in ACCESS_FALSE_FLAGS.items():
        if access.get(flag) is not expected:
            raise CityOpsContractError(f"product exposure no-answer hold packet source access promoted {flag}")

    readiness = gate.get("readiness", {})
    for flag, expected in GATE_FALSE_FLAGS.items():
        if readiness.get(flag) is not expected:
            raise CityOpsContractError(
                f"product exposure no-answer hold packet source readiness promoted {flag}"
            )


def _assert_hold_guard_source(guard: dict[str, Any]) -> None:
    if guard.get("schema") != RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA:
        raise CityOpsContractError("product exposure no-answer hold packet guard source schema drift")
    if guard.get("guard_id") != GUARD_ID:
        raise CityOpsContractError("product exposure no-answer hold packet guard source id drift")
    if guard.get("guard_status") != GUARD_STATUS:
        raise CityOpsContractError("product exposure no-answer hold packet guard source promoted")
    if RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM not in guard.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("product exposure no-answer hold packet guard safe claim missing")
    if guard.get("candidate_count") != 1 or guard.get("candidate_key") != SELECTED_FAMILY_ID:
        raise CityOpsContractError("product exposure no-answer hold packet guard candidate drift")
    if guard.get("candidate_text_values_visible") is not False:
        raise CityOpsContractError("product exposure no-answer hold packet guard leaked candidate text")
    if guard.get("next_allowed_move") != HOLD_GUARD_NEXT_ALLOWED_MOVE:
        raise CityOpsContractError("product exposure no-answer hold packet guard next move drift")
    if guard.get("no_human_answer_default") != "keep_all_product_forks_internal_admin_only":
        raise CityOpsContractError("product exposure no-answer hold packet guard no-answer default drift")

    forbidden_safe = set(guard.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"product exposure no-answer hold packet guard forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(GUARD_BLOCKED_CLAIMS) - set(guard.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"product exposure no-answer hold packet guard missing blocked claims: {sorted(missing_blocked)}"
        )
    if guard.get("still_blocked_claims") != guard.get("do_not_claim_yet"):
        raise CityOpsContractError("product exposure no-answer hold packet guard blocked claims drift")
    for flag, expected in GUARD_FALSE_FLAGS.items():
        if guard.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"product exposure no-answer hold packet guard readiness promoted {flag}")
        if guard.get("regression_assertions", {}).get(flag) is not expected:
            raise CityOpsContractError(f"product exposure no-answer hold packet guard assertion promoted {flag}")


def _assert_sources_align(candidate_gate: dict[str, Any], hold_guard: dict[str, Any]) -> None:
    candidate = _selected_candidate(candidate_gate)
    if (
        candidate.get("selected_text_boundary_digest_sha256")
        != hold_guard.get("source_selected_boundary_digest_sha256")
    ):
        raise CityOpsContractError("product exposure no-answer hold packet selected boundary digest mismatch")
    if candidate.get("candidate_key") != hold_guard.get("candidate_key"):
        raise CityOpsContractError("product exposure no-answer hold packet candidate key mismatch")
    if candidate.get("candidate_text_values_visible") is not False:
        raise CityOpsContractError("product exposure no-answer hold packet candidate text leaked")
    if hold_guard.get("candidate_text_values_visible") is not False:
        raise CityOpsContractError("product exposure no-answer hold packet guard text leaked")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"product exposure no-answer hold packet claim overlap: {sorted(overlap)}"
        )
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"product exposure no-answer hold packet forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PACKET_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"product exposure no-answer hold packet missing blocked claims: {sorted(missing_blocked)}"
        )


def build_aas_product_exposure_no_answer_hold_packet(
    *,
    artifact_dir: str | Path | None = None,
    candidate_gate: dict[str, Any] | None = None,
    hold_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin product-exposure no-answer hold packet."""

    source_gate = candidate_gate or load_aas_product_exposure_boundary_candidate_review_gate(
        artifact_dir=artifact_dir
    )
    source_guard = hold_guard or load_retail_reality_product_exposure_hold_regression_guard(
        artifact_dir=artifact_dir
    )
    _assert_candidate_gate_source(source_gate)
    _assert_hold_guard_source(source_guard)
    _assert_sources_align(source_gate, source_guard)

    safe_to_claim = _dedupe(
        [
            AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
            RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
            AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_gate["claim_boundaries"]["do_not_claim_yet"],
            *source_guard["do_not_claim_yet"],
            *PACKET_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    selected_candidate = _selected_candidate(source_gate)

    packet: dict[str, Any] = {
        "schema": AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SCHEMA,
        "packet_id": PACKET_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "packet_status": PACKET_STATUS,
        "packet_verdict": PACKET_VERDICT,
        "default_decision": DEFAULT_DECISION,
        "runtime_decision": RUNTIME_DECISION,
        "candidate_count": 1,
        "selected_candidate_digest_card": {
            "selection_key": SELECTED_CANDIDATE_KEY,
            "candidate_key": selected_candidate["candidate_key"],
            "offer_id": selected_candidate["offer_id"],
            "selected_for_human_review": True,
            "selected_for_approval": False,
            "approval_recorded_here": False,
            "candidate_text_values_visible": False,
            "customer_or_public_exposure_allowed": False,
            "worker_surface_allowed": False,
            "pricing_queue_dispatch_allowed": False,
            "runtime_mutation_allowed": False,
            "selected_text_boundary_digest_sha256": selected_candidate[
                "selected_text_boundary_digest_sha256"
            ],
        },
        "source_artifacts": {
            "product_exposure_candidate_review_gate": {
                "file": AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME,
                "schema": source_gate["schema"],
                "id": source_gate["gate_id"],
                "safe_claim": AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source_gate),
            },
            "retail_reality_product_exposure_hold_regression_guard": {
                "file": RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME,
                "schema": source_guard["schema"],
                "id": source_guard["guard_id"],
                "safe_claim": RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source_guard),
            },
        },
        "source_alignment": {
            "candidate_gate_and_hold_guard_reference_same_candidate": True,
            "candidate_gate_and_hold_guard_reference_same_selected_boundary_digest": True,
            "digest_match_is_not_approval": True,
            "digest_match_creates_no_hold_record": True,
            "candidate_text_values_visible": False,
        },
        "no_answer_contract": {
            "explicit_human_operator_answer_present": False,
            "human_operator_approval_record_present": False,
            "approval_can_be_inferred_from_candidate_selection": False,
            "approval_can_be_inferred_from_digest_match": False,
            "packet_is_operator_answer": False,
            "default_if_no_human_answer": DEFAULT_DECISION,
            "runtime_decision_preserved": RUNTIME_DECISION,
            "next_allowed_move": NEXT_ALLOWED_MOVE,
        },
        "access_policy": {
            "surface": "internal_admin_only",
            "audience": "human_operator_review_only",
            "requires_admin_context": True,
            "default_off": True,
            "non_authorizing": True,
            **ACCESS_FALSE_FLAGS,
        },
        "readiness": {
            "internal_admin_hold_packet_landed": True,
            "source_candidate_gate_verified": True,
            "source_hold_guard_verified": True,
            "source_boundary_digest_cross_checked": True,
            "default_off_non_authorizing": True,
            **PACKET_FALSE_FLAGS,
        },
        "regression_assertions": dict(PACKET_FALSE_FLAGS),
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
    }
    _assert_hold_packet(packet, candidate_gate=source_gate, hold_guard=source_guard)
    return packet


def write_aas_product_exposure_no_answer_hold_packet(
    artifact_dir: str | Path | None = None,
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_product_exposure_no_answer_hold_packet(artifact_dir=target_dir)
    target_path = target_dir / AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_FILENAME
    target_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_aas_product_exposure_no_answer_hold_packet(
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source_gate = load_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=source_dir)
    source_guard = load_retail_reality_product_exposure_hold_regression_guard(artifact_dir=source_dir)
    _assert_hold_packet(packet, candidate_gate=source_gate, hold_guard=source_guard)
    return packet


def _assert_hold_packet(
    packet: dict[str, Any],
    *,
    candidate_gate: dict[str, Any],
    hold_guard: dict[str, Any],
) -> None:
    _assert_candidate_gate_source(candidate_gate)
    _assert_hold_guard_source(hold_guard)
    _assert_sources_align(candidate_gate, hold_guard)

    if packet.get("schema") != AAS_PRODUCT_EXPOSURE_NO_ANSWER_HOLD_PACKET_SCHEMA:
        raise CityOpsContractError("product exposure no-answer hold packet schema drift")
    if packet.get("packet_id") != PACKET_ID:
        raise CityOpsContractError("product exposure no-answer hold packet id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("product exposure no-answer hold packet scope drift")
    if packet.get("source_policy") != SOURCE_POLICY:
        raise CityOpsContractError("product exposure no-answer hold packet source policy drift")
    if packet.get("packet_status") != PACKET_STATUS:
        raise CityOpsContractError("product exposure no-answer hold packet status promoted")
    if packet.get("packet_verdict") != PACKET_VERDICT:
        raise CityOpsContractError("product exposure no-answer hold packet verdict drift")
    if packet.get("default_decision") != DEFAULT_DECISION:
        raise CityOpsContractError("product exposure no-answer hold packet default decision drift")
    if packet.get("runtime_decision") != RUNTIME_DECISION:
        raise CityOpsContractError("product exposure no-answer hold packet runtime decision drift")
    if packet.get("candidate_count") != 1:
        raise CityOpsContractError("product exposure no-answer hold packet candidate count drift")

    selected = packet.get("selected_candidate_digest_card", {})
    expected_selected = {
        "selection_key": SELECTED_CANDIDATE_KEY,
        "candidate_key": SELECTED_FAMILY_ID,
        "offer_id": SELECTED_OFFER_ID,
        "selected_for_human_review": True,
        "selected_for_approval": False,
        "approval_recorded_here": False,
        "candidate_text_values_visible": False,
        "customer_or_public_exposure_allowed": False,
        "worker_surface_allowed": False,
        "pricing_queue_dispatch_allowed": False,
        "runtime_mutation_allowed": False,
        "selected_text_boundary_digest_sha256": _selected_candidate(candidate_gate)[
            "selected_text_boundary_digest_sha256"
        ],
    }
    if selected != expected_selected:
        raise CityOpsContractError("product exposure no-answer hold packet selected digest card drift")

    sources = packet.get("source_artifacts", {})
    gate_source = sources.get("product_exposure_candidate_review_gate", {})
    if gate_source.get("file") != AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME:
        raise CityOpsContractError("product exposure no-answer hold packet candidate source file drift")
    if gate_source.get("digest_sha256") != _stable_digest(candidate_gate):
        raise CityOpsContractError("product exposure no-answer hold packet candidate source digest drift")
    guard_source = sources.get("retail_reality_product_exposure_hold_regression_guard", {})
    if guard_source.get("file") != RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME:
        raise CityOpsContractError("product exposure no-answer hold packet guard source file drift")
    if guard_source.get("digest_sha256") != _stable_digest(hold_guard):
        raise CityOpsContractError("product exposure no-answer hold packet guard source digest drift")

    alignment = packet.get("source_alignment", {})
    for key in [
        "candidate_gate_and_hold_guard_reference_same_candidate",
        "candidate_gate_and_hold_guard_reference_same_selected_boundary_digest",
        "digest_match_is_not_approval",
        "digest_match_creates_no_hold_record",
    ]:
        if alignment.get(key) is not True:
            raise CityOpsContractError(f"product exposure no-answer hold packet alignment lost {key}")
    if alignment.get("candidate_text_values_visible") is not False:
        raise CityOpsContractError("product exposure no-answer hold packet alignment exposed text")

    no_answer = packet.get("no_answer_contract", {})
    for key in [
        "explicit_human_operator_answer_present",
        "human_operator_approval_record_present",
        "approval_can_be_inferred_from_candidate_selection",
        "approval_can_be_inferred_from_digest_match",
        "packet_is_operator_answer",
    ]:
        if no_answer.get(key) is not False:
            raise CityOpsContractError(f"product exposure no-answer hold packet no-answer promoted {key}")
    if no_answer.get("default_if_no_human_answer") != DEFAULT_DECISION:
        raise CityOpsContractError("product exposure no-answer hold packet no-answer default drift")
    if no_answer.get("runtime_decision_preserved") != RUNTIME_DECISION:
        raise CityOpsContractError("product exposure no-answer hold packet no-answer runtime drift")
    if no_answer.get("next_allowed_move") != NEXT_ALLOWED_MOVE:
        raise CityOpsContractError("product exposure no-answer hold packet next move drift")

    access = packet.get("access_policy", {})
    if access.get("surface") != "internal_admin_only":
        raise CityOpsContractError("product exposure no-answer hold packet access surface drift")
    if access.get("audience") != "human_operator_review_only":
        raise CityOpsContractError("product exposure no-answer hold packet audience drift")
    if access.get("default_off") is not True or access.get("non_authorizing") is not True:
        raise CityOpsContractError("product exposure no-answer hold packet lost default-off posture")
    for flag, expected in ACCESS_FALSE_FLAGS.items():
        if access.get(flag) is not expected:
            raise CityOpsContractError(f"product exposure no-answer hold packet access promoted {flag}")

    readiness = packet.get("readiness", {})
    for flag in [
        "internal_admin_hold_packet_landed",
        "source_candidate_gate_verified",
        "source_hold_guard_verified",
        "source_boundary_digest_cross_checked",
        "default_off_non_authorizing",
    ]:
        if readiness.get(flag) is not True:
            raise CityOpsContractError(f"product exposure no-answer hold packet lost readiness {flag}")
    for flag, expected in PACKET_FALSE_FLAGS.items():
        if readiness.get(flag) is not expected:
            raise CityOpsContractError(f"product exposure no-answer hold packet readiness promoted {flag}")
        if packet.get("regression_assertions", {}).get(flag) is not expected:
            raise CityOpsContractError(f"product exposure no-answer hold packet assertion promoted {flag}")

    boundaries = packet.get("claim_boundaries", {})
    _assert_claim_boundaries(
        boundaries.get("safe_to_claim", []),
        boundaries.get("do_not_claim_yet", []),
    )
    if packet.get("still_blocked_claims") != boundaries.get("do_not_claim_yet"):
        raise CityOpsContractError("product exposure no-answer hold packet blocked claims drift")

    firewall = packet.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"product exposure no-answer hold packet firewall promoted {key}")
