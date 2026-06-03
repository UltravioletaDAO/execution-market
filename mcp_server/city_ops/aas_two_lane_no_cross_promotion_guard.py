"""Internal/admin AAS two-lane no-cross-promotion guard.

This proof block consumes the no-answer observability rubric and the product-
exposure boundary candidate review gate. It proves that the runtime-memory
observability lane cannot promote Retail Reality product exposure, and the
Retail Reality candidate lane cannot promote runtime-memory wiring. The guard
records no answer or approval, creates no customer/public/worker surface, calls
no Acontext/runtime/session-manager path, emits no reputation or Worker Skill
DNA, and integrates no stopped projects.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_no_answer_observability_rubric_fixture import (
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME,
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM,
    AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SCHEMA,
    NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS,
    load_aas_no_answer_observability_rubric_fixture,
)
from .aas_product_exposure_boundary_candidate_review_gate import (
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME,
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
    AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA,
    ACCESS_FALSE_FLAGS,
    DEFAULT_POSTURE,
    GATE_BLOCKED_CLAIMS,
    GATE_FALSE_FLAGS,
    GATE_STATUS,
    SELECTED_FAMILY_ID,
    build_aas_product_exposure_boundary_candidate_review_gate,
    load_aas_product_exposure_boundary_candidate_review_gate,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SCHEMA = (
    "city_ops.aas_two_lane_no_cross_promotion_guard.v1"
)
AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME = (
    "aas_two_lane_no_cross_promotion_guard.json"
)
AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM = (
    "internal_admin_aas_two_lane_no_cross_promotion_guard_landed"
)
AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_ID = (
    "execution_market.aas.two_lane_no_cross_promotion_guard.2026_06_02_2300"
)
AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_STATUS = (
    "two_internal_admin_lanes_verified_no_cross_promotion_no_answer_no_approval"
)

GUARD_STOP_LINE = (
    "This guard is internal/admin only. A no-answer observability score cannot "
    "approve Retail Reality product exposure, and a selected Retail Reality "
    "candidate cannot approve runtime-memory wiring. It records no operator "
    "answer or approval and authorizes no customer/public/worker surface, "
    "dashboard, public metric, runtime adapter, IRC/session-manager mutation, "
    "Acontext write/retrieval, queue, dispatch, reputation, Worker Skill DNA, "
    "payment/production claim, exact GPS/raw metadata release, private-context "
    "release, authority claim, worker-copyable doctrine, or stopped-project "
    "integration."
)

CROSS_PROMOTION_BLOCKED_CLAIMS = [
    *NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS,
    *GATE_BLOCKED_CLAIMS,
    "two_lane_guard_records_operator_answer",
    "two_lane_guard_records_operator_approval",
    "two_lane_guard_treats_observability_score_as_product_approval",
    "two_lane_guard_treats_product_candidate_selection_as_runtime_approval",
    "two_lane_guard_approves_retail_reality_product_exposure",
    "two_lane_guard_selects_design_only_wiring",
    "two_lane_guard_executes_bounded_activation_test",
    "two_lane_guard_registers_or_enables_runtime_adapter",
    "two_lane_guard_mutates_irc_session_manager",
    "two_lane_guard_writes_or_retrieves_live_acontext",
    "two_lane_guard_creates_dashboard_or_public_metric",
    "two_lane_guard_creates_customer_public_or_worker_surface",
    "two_lane_guard_registers_catalog_pricing_queue_or_dispatch",
    "two_lane_guard_emits_erc8004_reputation_or_worker_skill_dna",
    "two_lane_guard_reverifies_payment_or_production",
    "two_lane_guard_releases_exact_gps_or_raw_metadata",
    "two_lane_guard_releases_private_context",
    "two_lane_guard_grants_domain_authority_claims",
    "two_lane_guard_publishes_worker_copyable_doctrine",
    "two_lane_guard_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(CROSS_PROMOTION_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "score_treated_as_approval",
    "retail_reality_approved",
    "product_exposure_approved",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "dashboard_ready",
    "public_metric_ready",
    "customer_copy_ready",
    "customer_delivery_approved",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}

GUARD_FALSE_FLAGS = {
    "operator_answer_recorded": False,
    "operator_approval_recorded": False,
    "observability_score_treated_as_product_approval": False,
    "product_candidate_selection_treated_as_runtime_approval": False,
    "retail_reality_product_exposure_approved": False,
    "runtime_memory_wiring_approved": False,
    "design_only_wiring_selected": False,
    "bounded_activation_test_selected": False,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "live_acontext_write_or_retrieval_enabled": False,
    "dashboard_created": False,
    "public_metric_created": False,
    "customer_visible": False,
    "public_visible": False,
    "worker_visible": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "queue_launch_ready": False,
    "dispatch_enabled": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_allowed": False,
    "private_context_release_allowed": False,
    "domain_authority_claims_allowed": False,
    "worker_copyable_doctrine_ready": False,
    "stopped_project_integration_ready": False,
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


def _assert_no_answer_rubric_source(rubric: dict[str, Any]) -> None:
    if rubric.get("schema") != AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SCHEMA:
        raise CityOpsContractError("two-lane guard no-answer source schema drift")
    if AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM not in rubric.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("two-lane guard no-answer source safe claim missing")
    safe = set(rubric.get("claim_boundaries", {}).get("safe_to_claim", []))
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"two-lane guard no-answer source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(rubric.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"two-lane guard no-answer source missing blocked claims: {sorted(missing_blocked)}"
        )
    observed = rubric.get("no_answer_observability_rubric", {})
    if observed.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("two-lane guard no-answer source decision drift")
    if observed.get("effective_decision_after_rubric") != "hold_no_runtime_mutation":
        raise CityOpsContractError("two-lane guard no-answer source effective decision drift")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "score_treated_as_approval",
        "dashboard_or_public_metric_authorized_now",
        "runtime_mutation_authorized_now",
    ]:
        if observed.get(key) is not False:
            raise CityOpsContractError(f"two-lane guard no-answer source promoted {key}")
    scoring = rubric.get("scoring_model", {})
    if scoring.get("score_is_internal_admin_only") is not True:
        raise CityOpsContractError("two-lane guard no-answer source score scope drift")
    for key in ["score_is_not_reputation", "score_is_not_worker_skill_dna", "score_is_not_customer_metric"]:
        if scoring.get(key) is not True:
            raise CityOpsContractError(f"two-lane guard no-answer source promoted {key}")
    for key, value in rubric.get("access_flags", {}).items():
        if key == "rubric_fixture_documented":
            if value is not True:
                raise CityOpsContractError("two-lane guard no-answer source missing fixture flag")
            continue
        if value is not False:
            raise CityOpsContractError(f"two-lane guard no-answer source access promoted {key}")


def _assert_candidate_gate_source(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("two-lane guard candidate source schema drift")
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("two-lane guard candidate source status promoted")
    if gate.get("default_posture") != DEFAULT_POSTURE:
        raise CityOpsContractError("two-lane guard candidate source default posture drift")
    if AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM not in gate.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("two-lane guard candidate source safe claim missing")
    safe = set(gate.get("claim_boundaries", {}).get("safe_to_claim", []))
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"two-lane guard candidate source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(gate.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(GATE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"two-lane guard candidate source missing blocked claims: {sorted(missing_blocked)}"
        )
    no_answer = gate.get("no_answer_state", {})
    for key in [
        "explicit_human_operator_answer_present",
        "human_operator_approval_record_present",
        "approval_can_be_inferred_from_candidate_selection",
    ]:
        if no_answer.get(key) is not False:
            raise CityOpsContractError(f"two-lane guard candidate source promoted {key}")
    selection = gate.get("selection_contract", {})
    if selection.get("selected_family_id") != SELECTED_FAMILY_ID:
        raise CityOpsContractError("two-lane guard candidate source selected family drift")
    for key, value in selection.items():
        if key in {"exactly_one_candidate_selected_for_human_review", "selected_family_id", "selected_offer_id"}:
            continue
        if value is not False:
            raise CityOpsContractError(f"two-lane guard candidate source selection promoted {key}")
    access = gate.get("access_policy", {})
    for key, expected in ACCESS_FALSE_FLAGS.items():
        if access.get(key) is not expected:
            raise CityOpsContractError(f"two-lane guard candidate source access promoted {key}")
    for key, expected in GATE_FALSE_FLAGS.items():
        if gate.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"two-lane guard candidate source readiness promoted {key}")


def build_aas_two_lane_no_cross_promotion_guard(
    *,
    artifact_dir: str | Path | None = None,
    no_answer_artifact_dir: str | Path | None = None,
    no_answer_rubric: dict[str, Any] | None = None,
    candidate_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin two-lane cross-promotion guard."""

    product_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    rubric_dir = (
        Path(no_answer_artifact_dir)
        if no_answer_artifact_dir is not None
        else _default_proof_block_dir()
    )
    rubric = no_answer_rubric or load_aas_no_answer_observability_rubric_fixture(
        artifact_dir=rubric_dir
    )
    gate = candidate_gate or load_aas_product_exposure_boundary_candidate_review_gate(
        artifact_dir=product_dir
    )
    _assert_no_answer_rubric_source(rubric)
    _assert_candidate_gate_source(gate)

    safe_to_claim = _dedupe(
        [
            AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM,
            AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
            AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *rubric["claim_boundaries"]["do_not_claim_yet"],
            *gate["claim_boundaries"]["do_not_claim_yet"],
            *CROSS_PROMOTION_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    guard: dict[str, Any] = {
        "schema": AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SCHEMA,
        "guard_id": AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_ID,
        "scope": "internal_admin_two_lane_no_cross_promotion_guard_only",
        "guard_status": AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_STATUS,
        "source_policy": (
            "consume_only_no_answer_observability_rubric_and_product_exposure_candidate_gate"
        ),
        "source_artifacts": {
            "no_answer_observability_rubric": {
                "file": AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME,
                "schema": rubric["schema"],
                "id": rubric["rubric_id"],
                "safe_claim": AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(rubric),
                "effective_decision": rubric["no_answer_observability_rubric"][
                    "effective_decision_after_rubric"
                ],
            },
            "product_exposure_boundary_candidate_review_gate": {
                "file": AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME,
                "schema": gate["schema"],
                "id": gate["gate_id"],
                "safe_claim": AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(gate),
                "selected_family_id": gate["selection_contract"]["selected_family_id"],
            },
        },
        "lane_contracts": [
            {
                "lane": "runtime_memory_no_answer_observability",
                "source_safe_claim": AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM,
                "allowed_output": "internal_admin_boundary_preservation_score_only",
                "may_score_handoff_quality": True,
                "may_approve_product_exposure": False,
                "may_create_customer_public_worker_surface": False,
                "may_select_retail_reality_for_delivery": False,
                "may_register_or_enable_runtime_adapter": False,
                "effective_decision": "hold_no_runtime_mutation",
            },
            {
                "lane": "retail_reality_product_exposure_candidate",
                "source_safe_claim": AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_SAFE_CLAIM,
                "allowed_output": "one_internal_admin_human_review_candidate_only",
                "selected_family_id": SELECTED_FAMILY_ID,
                "may_select_candidate_for_human_review": True,
                "may_infer_approval_from_selection": False,
                "may_approve_runtime_memory_wiring": False,
                "may_register_or_enable_runtime_adapter": False,
                "may_create_customer_public_worker_surface": False,
                "default_posture": DEFAULT_POSTURE,
            },
        ],
        "cross_promotion_matrix": [
            {
                "from_lane": "runtime_memory_no_answer_observability",
                "to_lane": "retail_reality_product_exposure_candidate",
                "forbidden_promotion": "rubric_score_as_product_exposure_approval",
                "promotion_allowed": False,
                "next_required_gate": "separate_retail_reality_answer_or_hold_record",
            },
            {
                "from_lane": "retail_reality_product_exposure_candidate",
                "to_lane": "runtime_memory_no_answer_observability",
                "forbidden_promotion": "candidate_selection_as_runtime_memory_wiring_approval",
                "promotion_allowed": False,
                "next_required_gate": "separate_runtime_memory_operator_answer_record",
            },
        ],
        "no_answer_state": {
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "observability_score_can_approve_product_exposure": False,
            "candidate_selection_can_approve_runtime_memory": False,
            "default_if_no_human_answer": "keep_both_lanes_held_internal_admin_only",
        },
        "allowed_without_human_answer": [
            "carry_both_safe_claims_as_internal_admin_sources",
            "show_no_cross_promotion_guard_to_internal_admins",
            "ask_for_exactly_one_separate_daytime_decision",
            "keep_both_lanes_held_if_no_answer",
        ],
        "forbidden_shortcuts": [
            "do_not_treat_observability_score_as_approval",
            "do_not_treat_candidate_selection_as_approval",
            "do_not_launch_customer_public_worker_surfaces",
            "do_not_register_or_enable_runtime_adapter",
            "do_not_mutate_irc_session_manager",
            "do_not_write_or_retrieve_live_acontext",
            "do_not_emit_reputation_worker_skill_dna_payment_or_dispatch_claims",
            "do_not_release_exact_gps_raw_metadata_private_context_or_authority_claims",
            "do_not_publish_worker_copyable_doctrine",
            "do_not_integrate_stopped_projects",
        ],
        "readiness": {
            "internal_admin_guard_landed": True,
            "no_answer_observability_source_verified": True,
            "product_candidate_source_verified": True,
            "two_lanes_separated": True,
            "default_off_non_authorizing": True,
            **GUARD_FALSE_FLAGS,
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
        "operator_guidance": {
            "stop_line": GUARD_STOP_LINE,
            "one_question_handoff": (
                "Keep both lanes held, create a real Retail Reality answer/hold record, "
                "create a real runtime-memory answer record, or pause AAS proof layering?"
            ),
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_dashboard_spec": True,
        },
        "guard_verdict": (
            "two_lanes_remain_internal_admin_only_no_cross_promotion_no_answer_no_approval_"
            "no_customer_public_worker_runtime_reputation_payment_dispatch_or_stopped_project_promotion"
        ),
    }
    _assert_guard(guard, no_answer_rubric=rubric, candidate_gate=gate)
    return guard


def write_aas_two_lane_no_cross_promotion_guard(
    *,
    artifact_dir: str | Path | None = None,
    no_answer_artifact_dir: str | Path | None = None,
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    guard = build_aas_two_lane_no_cross_promotion_guard(
        artifact_dir=target_dir,
        no_answer_artifact_dir=no_answer_artifact_dir,
    )
    target_path = target_dir / AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME
    target_path.write_text(json.dumps(guard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_aas_two_lane_no_cross_promotion_guard(
    *,
    artifact_dir: str | Path | None = None,
    no_answer_artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    rubric_dir = (
        Path(no_answer_artifact_dir)
        if no_answer_artifact_dir is not None
        else _default_proof_block_dir()
    )
    path = source_dir / AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME
    guard = json.loads(path.read_text(encoding="utf-8"))
    rubric = load_aas_no_answer_observability_rubric_fixture(artifact_dir=rubric_dir)
    gate = load_aas_product_exposure_boundary_candidate_review_gate(artifact_dir=source_dir)
    _assert_guard(guard, no_answer_rubric=rubric, candidate_gate=gate)
    return guard


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"two-lane guard claim overlap: {sorted(overlap)}")
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(f"two-lane guard forbidden safe claims: {sorted(forbidden_safe)}")
    missing_blocked = set(CROSS_PROMOTION_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(f"two-lane guard missing blocked claims: {sorted(missing_blocked)}")


def _assert_guard(
    guard: dict[str, Any],
    *,
    no_answer_rubric: dict[str, Any],
    candidate_gate: dict[str, Any],
) -> None:
    _assert_no_answer_rubric_source(no_answer_rubric)
    _assert_candidate_gate_source(candidate_gate)
    if guard.get("schema") != AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SCHEMA:
        raise CityOpsContractError("two-lane guard schema drift")
    if guard.get("guard_id") != AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_ID:
        raise CityOpsContractError("two-lane guard id drift")
    if guard.get("guard_status") != AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_STATUS:
        raise CityOpsContractError("two-lane guard status promoted")

    sources = guard.get("source_artifacts", {})
    rubric_source = sources.get("no_answer_observability_rubric", {})
    if rubric_source.get("file") != AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME:
        raise CityOpsContractError("two-lane guard no-answer source file drift")
    if rubric_source.get("digest_sha256") != _stable_digest(no_answer_rubric):
        raise CityOpsContractError("two-lane guard no-answer source digest drift")
    candidate_source = sources.get("product_exposure_boundary_candidate_review_gate", {})
    if candidate_source.get("file") != AAS_PRODUCT_EXPOSURE_BOUNDARY_CANDIDATE_REVIEW_GATE_FILENAME:
        raise CityOpsContractError("two-lane guard candidate source file drift")
    if candidate_source.get("digest_sha256") != _stable_digest(candidate_gate):
        raise CityOpsContractError("two-lane guard candidate source digest drift")

    lane_contracts = guard.get("lane_contracts", [])
    if {lane.get("lane") for lane in lane_contracts} != {
        "runtime_memory_no_answer_observability",
        "retail_reality_product_exposure_candidate",
    }:
        raise CityOpsContractError("two-lane guard lane set drift")
    for lane in lane_contracts:
        for key, value in lane.items():
            if key in {
                "lane",
                "source_safe_claim",
                "allowed_output",
                "effective_decision",
                "selected_family_id",
                "default_posture",
            }:
                continue
            if key in {"may_score_handoff_quality", "may_select_candidate_for_human_review"}:
                if value is not True:
                    raise CityOpsContractError(f"two-lane guard lost allowed lane action {key}")
                continue
            if key.startswith("may_") and value is not False:
                raise CityOpsContractError(f"two-lane guard lane promoted {key}")

    matrix = guard.get("cross_promotion_matrix", [])
    if len(matrix) != 2:
        raise CityOpsContractError("two-lane guard cross-promotion matrix count drift")
    for row in matrix:
        if row.get("promotion_allowed") is not False:
            raise CityOpsContractError("two-lane guard cross-promotion allowed")
        if not row.get("next_required_gate"):
            raise CityOpsContractError("two-lane guard cross-promotion gate missing")

    no_answer = guard.get("no_answer_state", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "observability_score_can_approve_product_exposure",
        "candidate_selection_can_approve_runtime_memory",
    ]:
        if no_answer.get(key) is not False:
            raise CityOpsContractError(f"two-lane guard no-answer promoted {key}")

    readiness = guard.get("readiness", {})
    for flag in [
        "internal_admin_guard_landed",
        "no_answer_observability_source_verified",
        "product_candidate_source_verified",
        "two_lanes_separated",
        "default_off_non_authorizing",
    ]:
        if readiness.get(flag) is not True:
            raise CityOpsContractError(f"two-lane guard lost readiness {flag}")
    for flag, expected in GUARD_FALSE_FLAGS.items():
        if readiness.get(flag) is not expected:
            raise CityOpsContractError(f"two-lane guard readiness promoted {flag}")

    boundaries = guard.get("claim_boundaries", {})
    _assert_claim_boundaries(
        boundaries.get("safe_to_claim", []),
        boundaries.get("do_not_claim_yet", []),
    )
    if guard.get("still_blocked_claims") != boundaries.get("do_not_claim_yet"):
        raise CityOpsContractError("two-lane guard blocked claims drift")

    firewall = guard.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"two-lane guard stopped project promoted {key}")
