"""Internal/admin answer schema for the AAS two-lane decision.

This proof block consumes the two-lane no-cross-promotion guard and defines the
exact shape of a future operator answer for the next AAS decision. It records no
answer or approval, keeps both lanes held by default, creates no runtime or
product exposure, emits no reputation or Worker Skill DNA, and integrates no
stopped projects.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_two_lane_no_cross_promotion_guard import (
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM,
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SCHEMA,
    AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_STATUS,
    CROSS_PROMOTION_BLOCKED_CLAIMS,
    GUARD_FALSE_FLAGS,
    load_aas_two_lane_no_cross_promotion_guard,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SCHEMA = (
    "city_ops.aas_two_lane_operator_answer_schema.v1"
)
AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME = (
    "aas_two_lane_operator_answer_schema.json"
)
AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM = (
    "internal_admin_aas_two_lane_operator_answer_schema_landed"
)
AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_ID = (
    "execution_market.aas.two_lane_operator_answer_schema.2026_06_03_0000"
)
AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_STATUS = (
    "schema_only_no_operator_answer_no_approval_both_lanes_held"
)
FUTURE_ANSWER_RECORD_SCHEMA = "city_ops.aas_two_lane_operator_answer_record.v1"
DEFAULT_EFFECTIVE_DECISION = "keep_both_lanes_held_internal_admin_only"

ALLOWED_FUTURE_DECISIONS = [
    "keep_both_lanes_held",
    "create_retail_reality_answer_or_hold_record",
    "create_runtime_memory_operator_answer_record",
    "pause_aas_proof_layering",
]

FUTURE_ANSWER_REQUIRED_FIELDS = [
    "source_guard_id",
    "source_guard_digest_sha256",
    "selected_decision",
    "human_operator_answer_recorded",
    "human_operator_reference",
    "answer_timestamp_utc",
    "answer_scope",
    "approvals_not_granted",
    "still_blocked_claims",
]

ANSWER_SCHEMA_FALSE_FLAGS = {
    "operator_answer_recorded": False,
    "operator_approval_recorded": False,
    "future_answer_record_created": False,
    "retail_reality_answer_or_hold_record_created": False,
    "runtime_memory_operator_answer_record_created": False,
    "retail_reality_product_exposure_approved": False,
    "runtime_memory_wiring_approved": False,
    "design_only_wiring_selected": False,
    "bounded_activation_test_selected": False,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "live_acontext_write_or_retrieval_enabled": False,
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

ANSWER_SCHEMA_BLOCKED_CLAIMS = [
    *CROSS_PROMOTION_BLOCKED_CLAIMS,
    "two_lane_answer_schema_records_operator_answer",
    "two_lane_answer_schema_records_operator_approval",
    "two_lane_answer_schema_creates_future_answer_record",
    "two_lane_answer_schema_creates_retail_reality_answer_or_hold_record",
    "two_lane_answer_schema_creates_runtime_memory_operator_answer_record",
    "two_lane_answer_schema_treats_option_display_as_answer",
    "two_lane_answer_schema_approves_retail_reality_product_exposure",
    "two_lane_answer_schema_approves_runtime_memory_wiring",
    "two_lane_answer_schema_selects_design_only_wiring",
    "two_lane_answer_schema_executes_bounded_activation_test",
    "two_lane_answer_schema_registers_or_enables_runtime_adapter",
    "two_lane_answer_schema_mutates_irc_session_manager",
    "two_lane_answer_schema_writes_or_retrieves_live_acontext",
    "two_lane_answer_schema_creates_customer_public_or_worker_surface",
    "two_lane_answer_schema_registers_catalog_pricing_queue_or_dispatch",
    "two_lane_answer_schema_emits_erc8004_reputation_or_worker_skill_dna",
    "two_lane_answer_schema_reverifies_payment_or_production",
    "two_lane_answer_schema_releases_exact_gps_or_raw_metadata",
    "two_lane_answer_schema_releases_private_context",
    "two_lane_answer_schema_grants_domain_authority_claims",
    "two_lane_answer_schema_publishes_worker_copyable_doctrine",
    "two_lane_answer_schema_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(ANSWER_SCHEMA_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "future_answer_record_created",
    "retail_reality_approved",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "customer_copy_ready",
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


def _assert_source_guard(guard: dict[str, Any]) -> None:
    if guard.get("schema") != AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SCHEMA:
        raise CityOpsContractError("two-lane answer schema source guard schema drift")
    if guard.get("guard_status") != AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_STATUS:
        raise CityOpsContractError("two-lane answer schema source guard status drift")
    if AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM not in guard.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("two-lane answer schema source guard safe claim missing")
    safe = set(guard.get("claim_boundaries", {}).get("safe_to_claim", []))
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"two-lane answer schema source guard forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(guard.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(CROSS_PROMOTION_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"two-lane answer schema source guard missing blocked claims: {sorted(missing_blocked)}"
        )
    no_answer = guard.get("no_answer_state", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "observability_score_can_approve_product_exposure",
        "candidate_selection_can_approve_runtime_memory",
    ]:
        if no_answer.get(key) is not False:
            raise CityOpsContractError(f"two-lane answer schema source guard promoted {key}")
    if no_answer.get("default_if_no_human_answer") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("two-lane answer schema source guard default decision drift")
    readiness = guard.get("readiness", {})
    for key, expected in GUARD_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"two-lane answer schema source guard promoted {key}")
    firewall = guard.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"two-lane answer schema source guard allowed {key}")


def _future_answer_field_contracts(guard: dict[str, Any]) -> list[dict[str, Any]]:
    values = {
        "source_guard_id": guard["guard_id"],
        "source_guard_digest_sha256": _stable_digest(guard),
        "selected_decision": ALLOWED_FUTURE_DECISIONS,
        "human_operator_answer_recorded": True,
        "answer_scope": "one_of_four_two_lane_decisions_only_not_approval",
        "approvals_not_granted": sorted(ANSWER_SCHEMA_FALSE_FLAGS),
        "still_blocked_claims": ANSWER_SCHEMA_BLOCKED_CLAIMS,
    }
    optional = {
        "human_operator_reference": "non_secret_operator_reference_required",
        "answer_timestamp_utc": "required_when_real_answer_record_is_created",
    }
    return [
        {
            "field": field,
            "required_in_future_answer_record": True,
            "expected_value_or_constraint": values.get(field, optional.get(field)),
            "satisfied_by_this_schema": False,
        }
        for field in FUTURE_ANSWER_REQUIRED_FIELDS
    ]


def build_aas_two_lane_operator_answer_schema(
    *,
    artifact_dir: str | Path | None = None,
    source_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic schema for one future two-lane operator answer."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    guard = source_guard or load_aas_two_lane_no_cross_promotion_guard(artifact_dir=source_dir)
    _assert_source_guard(guard)

    safe_to_claim = _dedupe(
        [
            *guard["claim_boundaries"]["safe_to_claim"],
            AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *guard["claim_boundaries"]["do_not_claim_yet"],
            *ANSWER_SCHEMA_BLOCKED_CLAIMS,
        ]
    )

    schema = {
        "schema": AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SCHEMA,
        "schema_id": AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_ID,
        "scope": "internal_admin_schema_for_future_two_lane_operator_answer_only",
        "schema_status": AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_STATUS,
        "source_policy": "consume_only_aas_two_lane_no_cross_promotion_guard_json",
        "source_guard": {
            "file": AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME,
            "schema": guard["schema"],
            "id": guard["guard_id"],
            "safe_claim": AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_SAFE_CLAIM,
            "digest_sha256": _stable_digest(guard),
            "guard_status": guard["guard_status"],
            "default_if_no_human_answer": guard["no_answer_state"][
                "default_if_no_human_answer"
            ],
        },
        "future_answer_record_schema": FUTURE_ANSWER_RECORD_SCHEMA,
        "allowed_future_decisions": [
            {
                "decision": decision,
                "allowed_in_future_record": True,
                "selected_by_this_schema": False,
                "approval_granted_by_this_schema": False,
            }
            for decision in ALLOWED_FUTURE_DECISIONS
        ],
        "future_answer_required_fields": _future_answer_field_contracts(guard),
        "current_values": {
            "operator_answer_recorded": False,
            "operator_approval_recorded": False,
            "selected_decision": None,
            "effective_decision": DEFAULT_EFFECTIVE_DECISION,
            "option_display_is_answer": False,
            "schema_is_approval_record": False,
        },
        "readiness": {
            "internal_admin_answer_schema_landed": True,
            "source_guard_verified": True,
            "future_answer_options_constrained": True,
            "default_off_non_authorizing": True,
            **ANSWER_SCHEMA_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "still_blocked_claims": do_not_claim_yet,
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "operator_guidance": {
            "one_question": (
                "Choose exactly one future record type: keep both lanes held, create a "
                "Retail Reality answer/hold record, create a runtime-memory operator "
                "answer record, or pause AAS proof layering."
            ),
            "answer_must_be_separate_artifact": True,
            "do_not_mutate_this_schema_into_answer": True,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_dashboard_spec": True,
        },
        "schema_verdict": (
            "future_two_lane_answer_shape_defined_no_answer_no_approval_both_lanes_held_"
            "no_customer_public_worker_runtime_reputation_payment_dispatch_or_stopped_project_promotion"
        ),
    }
    _assert_answer_schema(schema, source_guard=guard)
    return schema


def _assert_answer_schema(schema: dict[str, Any], *, source_guard: dict[str, Any]) -> None:
    _assert_source_guard(source_guard)
    if schema.get("schema") != AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SCHEMA:
        raise CityOpsContractError("two-lane answer schema schema drift")
    if schema.get("schema_id") != AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_ID:
        raise CityOpsContractError("two-lane answer schema id drift")
    if schema.get("schema_status") != AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_STATUS:
        raise CityOpsContractError("two-lane answer schema status drift")
    source = schema.get("source_guard", {})
    if source.get("file") != AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_FILENAME:
        raise CityOpsContractError("two-lane answer schema source file drift")
    if source.get("digest_sha256") != _stable_digest(source_guard):
        raise CityOpsContractError("two-lane answer schema source digest drift")
    safe = set(schema.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(schema.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM not in safe:
        raise CityOpsContractError("two-lane answer schema safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"two-lane answer schema forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(ANSWER_SCHEMA_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"two-lane answer schema missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"two-lane answer schema claim overlap: {sorted(overlap)}")
    decisions = schema.get("allowed_future_decisions", [])
    if [item.get("decision") for item in decisions] != ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("two-lane answer schema future decisions drift")
    for item in decisions:
        if item.get("allowed_in_future_record") is not True:
            raise CityOpsContractError("two-lane answer schema decision not future-allowed")
        if item.get("selected_by_this_schema") is not False:
            raise CityOpsContractError("two-lane answer schema selected a decision")
        if item.get("approval_granted_by_this_schema") is not False:
            raise CityOpsContractError("two-lane answer schema granted approval")
    fields = schema.get("future_answer_required_fields", [])
    if [field.get("field") for field in fields] != FUTURE_ANSWER_REQUIRED_FIELDS:
        raise CityOpsContractError("two-lane answer schema required fields drift")
    for field in fields:
        if field.get("required_in_future_answer_record") is not True:
            raise CityOpsContractError("two-lane answer schema future field not required")
        if field.get("satisfied_by_this_schema") is not False:
            raise CityOpsContractError("two-lane answer schema satisfied a future field")
    current = schema.get("current_values", {})
    for key in [
        "operator_answer_recorded",
        "operator_approval_recorded",
        "option_display_is_answer",
        "schema_is_approval_record",
    ]:
        if current.get(key) is not False:
            raise CityOpsContractError(f"two-lane answer schema promoted {key}")
    if current.get("selected_decision") is not None:
        raise CityOpsContractError("two-lane answer schema selected decision")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("two-lane answer schema effective decision drift")
    readiness = schema.get("readiness", {})
    for key, expected in ANSWER_SCHEMA_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"two-lane answer schema promoted readiness {key}")
    if schema.get("still_blocked_claims") != schema.get("claim_boundaries", {}).get(
        "do_not_claim_yet"
    ):
        raise CityOpsContractError("two-lane answer schema blocked claims drift")
    firewall = schema.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"two-lane answer schema allowed {key}")


def write_aas_two_lane_operator_answer_schema(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    schema = build_aas_two_lane_operator_answer_schema(artifact_dir=target_dir)
    target_path = target_dir / AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME
    target_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_aas_two_lane_operator_answer_schema(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME
    schema = json.loads(path.read_text(encoding="utf-8"))
    guard = load_aas_two_lane_no_cross_promotion_guard(artifact_dir=source_dir)
    _assert_answer_schema(schema, source_guard=guard)
    return schema
